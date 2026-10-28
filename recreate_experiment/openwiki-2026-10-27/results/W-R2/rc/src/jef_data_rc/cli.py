"""`jef-data-rc` command line.

A thin argparse shell: modules that need Parquet or HTTP support are imported
only inside the command that uses them, so `validate` works without loading
the persistence or network stack.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_STORE = "data"


def _err(prefix: str, exc: BaseException | str) -> None:
    print(f"{prefix}: {exc}", file=sys.stderr)


# -- manual-load helpers ------------------------------------------------------

def _asset_types() -> list[str]:
    from jef_data_rc.universe import ASSET_TYPE_BY_CLASS

    return sorted(set(ASSET_TYPE_BY_CLASS.values()))


def resolve_load_asset_type(symbol: str, asset_type: str | None) -> str:
    """The declared type for a one-off EODHD load.

    `--asset-type` is required unless the symbol is in EODHD's `.CC` crypto
    namespace; a `.CC` symbol declared non-crypto is refused.
    """
    is_cc = symbol.upper().endswith(".CC")
    if asset_type is None:
        if is_cc:
            return "crypto"
        raise ValueError(
            f"--asset-type is required for {symbol} (one of: {', '.join(_asset_types())}); "
            "only an EODHD .CC symbol implies crypto"
        )
    if asset_type not in _asset_types():
        raise ValueError(f"unknown asset type {asset_type!r} (one of: {', '.join(_asset_types())})")
    if is_cc and asset_type != "crypto":
        raise ValueError(f"{symbol} is in the EODHD .CC crypto namespace but was declared {asset_type!r}")
    return asset_type


# -- commands -----------------------------------------------------------------

def cmd_validate(args) -> int:
    import pandas as pd

    from jef_data_rc.contract import validate

    try:
        df = pd.read_csv(args.csv)
    except (OSError, ValueError) as exc:
        _err("validate", exc)
        return 2
    report = validate(df, min_rows=args.min_rows)
    print(f"{args.csv}: {len(df)} row(s)")
    print(report.render())
    return 0 if report.ok else 1


def _fmt_source(src: dict) -> str:
    flags = []
    if src["modeled"]:
        flags.append("modeled")
    if not src["enabled"]:
        flags.append("disabled")
    parts = [f"{src['provider']:<9}", f"{src['exchange']}/{src['symbol']}"]
    if src["path"]:
        parts.append(f"path={src['path']}")
    if src["start"]:
        parts.append(f"start={src['start']}")
    if src["end"]:
        parts.append(f"end={src['end']}")
    parts.append(f"kind={src['kind']}")
    parts.append(f"currency={src['currency']}")
    if flags:
        parts.append(f"[{', '.join(flags)}]")
    if src["note"]:
        parts.append(f"# {src['note']}")
    return "    " + "  ".join(parts)


def cmd_universe(args) -> int:
    from jef_data_rc.universe import UniverseError, load_universe, modeled_source

    try:
        universe = load_universe(args.universe)
    except UniverseError as exc:
        _err("universe", exc)
        return 2
    d = universe["defaults"]
    print(f"universe: {args.universe or 'packaged universe.toml'}")
    print(f"defaults: store={d['store']} currency={d['currency']}")
    for asset in universe["assets"]:
        head = (f"{asset['name']:<6} class={asset['asset_class']} type={asset['asset_type']} "
                f"currency={asset['currency']}")
        if asset["threshold"] is not None:
            head += f" threshold={asset['threshold']:g}"
        if not asset["enabled"]:
            head += " [disabled]"
        else:
            _a, src = modeled_source(universe, asset["name"])
            head += f" modeled={src['exchange']}/{src['symbol']}"
        print(head)
        for src in asset["sources"]:
            print(_fmt_source(src))
    print(f"{len(universe['assets'])} asset(s), "
          f"{sum(len(a['sources']) for a in universe['assets'])} source(s)")
    return 0


def cmd_sync(args) -> int:
    from jef_data_rc.sync import SyncError, run_sync, sync_summary
    from jef_data_rc.universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
        results, ok = run_sync(
            universe, args.store, assets=args.asset, providers=args.provider,
            dry_run=args.dry_run, tail=args.tail, force_actions=args.force_actions,
        )
    except (UniverseError, SyncError) as exc:
        _err("sync", exc)
        return 2
    if args.summary_json:
        path = Path(args.summary_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sync_summary(results, ok), indent=1) + "\n", encoding="utf-8")
    return 0 if ok else 1


def cmd_status(args) -> int:
    from jef_data_rc.health import build_status, render_text
    from jef_data_rc.sync import SyncError
    from jef_data_rc.universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
        from jef_data_rc.sync import select_legs

        select_legs(universe, args.asset, args.provider)
    except (UniverseError, SyncError) as exc:
        _err("status", exc)
        return 2
    envelope, code = build_status(
        universe, args.store, assets=args.asset, providers=args.provider,
        window=args.window, jump_threshold=args.jump_threshold, staleness_k=args.staleness,
        resolution_window=args.resolution_window, resolution_k=args.resolution_k,
        flat_k=args.flat_k, gap_k=args.gap_k, spread_threshold=args.spread_threshold,
        spread_alerts=args.spread_alerts,
    )
    if args.json:
        print(json.dumps(envelope, indent=1))
    else:
        print(render_text(envelope))
    return code


def cmd_sync_actions(args) -> int:
    from jef_data_rc.actions import sync_actions
    from jef_data_rc.collectors.base import CollectorError
    from jef_data_rc.collectors.eodhd import EODHDCollector

    try:
        collector = EODHDCollector()
    except CollectorError as exc:
        _err("sync-actions", exc)
        return 1
    try:
        splits, dividends = sync_actions(collector, args.store, args.symbol, exchange=args.exchange)
    except Exception as exc:
        _err("sync-actions", exc)
        return 1
    finally:
        collector.close()
    print(f"{args.symbol}: {len(splits)} split(s), {len(dividends)} dividend(s) "
          f"-> {Path(args.store) / 'corporate_actions'}")
    return 0


def cmd_load(args) -> int:
    from jef_data_rc.actions import ActionsStore
    from jef_data_rc.collectors.base import CollectorError
    from jef_data_rc.collectors.eodhd import EODHDCollector, normalize_symbol
    from jef_data_rc.store import ParquetStore

    try:
        symbol = normalize_symbol(args.symbol)
        asset_type = resolve_load_asset_type(symbol, args.asset_type)
    except (ValueError, CollectorError) as exc:
        _err("load", exc)
        return 2
    price_basis = "split_adjusted" if asset_type == "crypto" else "raw"
    try:
        collector = EODHDCollector()
    except CollectorError as exc:
        _err("load", exc)
        return 1
    actions = ActionsStore(args.store)
    splits = actions.load_splits(symbol) if price_basis == "raw" else []
    if price_basis == "raw" and actions.last_updated(symbol) is None:
        print(f"note: no saved corporate actions for {symbol}; run `sync-actions --symbol {symbol}` "
              "before a first raw-basis load", file=sys.stderr)
    store = ParquetStore(args.store)
    try:
        bars = collector.get_eod(symbol, start=args.start, end=args.end)
        n = store.ingest(bars, exchange=args.exchange, symbol=symbol, asset_type=asset_type,
                         currency=args.currency, price_basis=price_basis, splits=splits,
                         volume_basis=collector.VOLUME_BASIS, mode="append")
        if price_basis == "raw" and store.has_rows(args.exchange, symbol):
            store.reapply_adjustment(args.exchange, symbol, splits)
    except Exception as exc:
        _err("load", exc)
        return 1
    finally:
        collector.close()
    print(f"loaded {n} bar(s) into {args.exchange}/{symbol} ({asset_type}, {price_basis})")
    return 0


def cmd_adjust(args) -> int:
    from jef_data_rc.actions import ActionsStore
    from jef_data_rc.adjust import AdjustmentError
    from jef_data_rc.store import ParquetStore, StoreError

    store = ParquetStore(args.store)
    if not store.has_rows(args.exchange, args.symbol):
        _err("adjust", f"no stored rows for {args.exchange}/{args.symbol} in {args.store}")
        return 1
    splits = ActionsStore(args.store).load_splits(args.symbol)
    try:
        changed = store.reapply_adjustment(args.exchange, args.symbol, splits)
    except (AdjustmentError, StoreError) as exc:
        _err("adjust", exc)
        return 1
    state = "re-derived" if changed else "unchanged"
    print(f"{args.exchange}/{args.symbol}: {state} from raw columns and {len(splits)} split(s)")
    return 0


def cmd_import_csv(args) -> int:
    from jef_data_rc.store import ParquetStore

    store = ParquetStore(args.store)
    try:
        n = store.ingest_yahoo_csv(args.csv, symbol=args.symbol, exchange=args.exchange,
                                   asset_type=args.asset_type, currency=args.currency)
    except Exception as exc:
        _err("import-csv", exc)
        return 1
    print(f"imported {n} row(s) from {args.csv} into {args.exchange}/{args.symbol} (split_adjusted)")
    return 0


def cmd_export(args) -> int:
    from jef_data_rc.contract import validate
    from jef_data_rc.store import ParquetStore

    store = ParquetStore(args.store)
    frame = store.to_contract_frame(args.exchange, args.symbol)
    if frame.empty:
        _err("export", f"no stored rows for {args.exchange}/{args.symbol} in {args.store}")
        return 1
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    print(f"wrote {len(frame)} row(s) to {out}")
    report = validate(frame)
    print(report.render())
    return 0 if report.ok else 1


def cmd_differential(args) -> int:
    import pandas as pd

    from jef_data_rc.differential import differential
    from jef_data_rc.store import ParquetStore

    store = ParquetStore(args.store)
    a = store.to_contract_frame(args.a_exchange, args.a_symbol)
    a_label = f"{args.a_exchange}/{args.a_symbol}"
    if args.b_csv:
        try:
            b = pd.read_csv(args.b_csv)
        except (OSError, ValueError) as exc:
            _err("differential", exc)
            return 2
        b_label = args.b_csv
    else:
        b = store.to_contract_frame(args.b_exchange, args.b_symbol)
        b_label = f"{args.b_exchange}/{args.b_symbol}"
    report = differential(a, b, tolerance=args.tolerance, a_label=a_label, b_label=b_label)
    text = report.render()
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote differential report to {out}")
        print(text.splitlines()[-1])
    else:
        print(text)
    return 0 if report.ok else 1


# -- parser -------------------------------------------------------------------

def _add_selection(p: argparse.ArgumentParser) -> None:
    p.add_argument("--universe", default=None, metavar="PATH",
                   help="universe TOML (default: the packaged universe.toml)")
    p.add_argument("--store", default=None,
                   help="store root (default: the universe's defaults.store)")
    p.add_argument("--asset", action="append", default=None, metavar="NAME",
                   help="select an asset (repeatable)")
    p.add_argument("--provider", action="append", default=None, metavar="NAME",
                   help="select a provider: eodhd, binance, yahoo-csv (repeatable)")


def build_parser() -> argparse.ArgumentParser:
    from jef_data_rc.contract import DEFAULT_MIN_ROWS
    from jef_data_rc.differential import DEFAULT_TOLERANCE
    from jef_data_rc.health import (
        DEFAULT_FLAT_K, DEFAULT_GAP_K, DEFAULT_JUMP_THRESHOLD, DEFAULT_RESOLUTION_K,
        DEFAULT_RESOLUTION_WINDOW, DEFAULT_SPREAD_THRESHOLD, DEFAULT_STALENESS_K, DEFAULT_WINDOW,
    )
    from jef_data_rc.sync import DEFAULT_TAIL

    parser = argparse.ArgumentParser(
        prog="jef-data-rc",
        description="EOD acquisition, local store, adjustment and health for the JEF data layer.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("validate", help="validate a seven-column EOD CSV against the contract")
    p.add_argument("csv", metavar="CSV")
    p.add_argument("--min-rows", type=int, default=DEFAULT_MIN_ROWS,
                   help=f"advisory clean-row minimum (default {DEFAULT_MIN_ROWS} = 720 + 30 + 365)")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("universe", help="print the normalized configured assets and sources")
    p.add_argument("--universe", default=None, metavar="PATH",
                   help="universe TOML (default: the packaged universe.toml)")
    p.set_defaults(func=cmd_universe)

    p = sub.add_parser("sync", help="acquire every selected configured leg into the store")
    _add_selection(p)
    p.add_argument("--tail", type=int, default=DEFAULT_TAIL,
                   help=f"stored sessions re-fetched for an established series (default {DEFAULT_TAIL})")
    p.add_argument("--force-actions", action="store_true",
                   help="refresh corporate actions even if refreshed today (UTC)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan from local state; no collector, request or write")
    p.add_argument("--summary-json", default=None, metavar="FILE",
                   help="write a machine-readable run summary (also on a failed run)")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("status", help="offline store-health gate (exit 1 on alerts)")
    _add_selection(p)
    p.add_argument("--json", action="store_true", help="print one schema-versioned JSON envelope")
    p.add_argument("--staleness", type=int, default=DEFAULT_STALENESS_K,
                   help=f"missed expected sessions that alert (default {DEFAULT_STALENESS_K})")
    p.add_argument("--jump-threshold", type=float, default=DEFAULT_JUMP_THRESHOLD,
                   help=f"absolute one-row close return that alerts without a same-day split "
                        f"(default {DEFAULT_JUMP_THRESHOLD})")
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                   help=f"newest rows scanned for jumps and cross-venue dates (default {DEFAULT_WINDOW})")
    p.add_argument("--resolution-window", type=int, default=DEFAULT_RESOLUTION_WINDOW,
                   help=f"traded sessions measured for price resolution (default {DEFAULT_RESOLUTION_WINDOW})")
    p.add_argument("--resolution-k", type=float, default=DEFAULT_RESOLUTION_K,
                   help=f"distinct/session ratio below which resolution is noted (default {DEFAULT_RESOLUTION_K})")
    p.add_argument("--flat-k", type=float, default=DEFAULT_FLAT_K,
                   help=f"flat-close share above which resolution is noted (default {DEFAULT_FLAT_K})")
    p.add_argument("--gap-k", type=int, default=DEFAULT_GAP_K,
                   help=f"post-seam absent expected sessions noted (default {DEFAULT_GAP_K})")
    p.add_argument("--spread-threshold", type=float, default=DEFAULT_SPREAD_THRESHOLD,
                   help=f"relative cross-venue close spread flagged (default {DEFAULT_SPREAD_THRESHOLD})")
    p.add_argument("--spread-alerts", action="store_true",
                   help="promote a spread breach from warning to alert")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync-actions", help="fetch and persist a symbol's splits and dividends (EODHD)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_sync_actions)

    p = sub.add_parser("load", help="manual incremental EODHD ingestion (append)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--asset-type", default=None, choices=_asset_types(),
                   help="required unless the symbol is an EODHD .CC crypto symbol")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--currency", default="USD")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("adjust", help="re-derive main OHLCV from stored raw columns and splits (offline)")
    p.add_argument("--exchange", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_adjust)

    p = sub.add_parser("import-csv", help="import a Yahoo-format pre-adjusted CSV (overwrite)")
    p.add_argument("--csv", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--asset-type", required=True, choices=_asset_types())
    p.add_argument("--exchange", default="yahoo")
    p.add_argument("--currency", default="USD")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_import_csv)

    p = sub.add_parser(
        "export",
        help="write a stored series as the seven-column contract CSV and validate it",
        description=("Write a stored series as the seven-column interchange CSV, then validate it. "
                     "The bit-exact consumer path is jef.binning.loading.load_eod_store, which reads "
                     "the store directly; this export is the interoperable representation."),
    )
    p.add_argument("--exchange", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("differential", help="compare a stored series with another series or a CSV")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.add_argument("--a-exchange", required=True)
    p.add_argument("--a-symbol", required=True)
    p.add_argument("--b-exchange", default=None)
    p.add_argument("--b-symbol", default=None)
    p.add_argument("--b-csv", default=None)
    p.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                   help=f"relative tolerance per cell (default {DEFAULT_TOLERANCE:g})")
    p.add_argument("--output", default=None)
    p.set_defaults(func=cmd_differential, _parser=p)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    if args.command == "differential":
        has_store_b = args.b_exchange is not None or args.b_symbol is not None
        if args.b_csv and has_store_b:
            args._parser.error("use either --b-csv or --b-exchange/--b-symbol, not both")
        if not args.b_csv and not (args.b_exchange and args.b_symbol):
            args._parser.error("B needs --b-csv or both --b-exchange and --b-symbol")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
