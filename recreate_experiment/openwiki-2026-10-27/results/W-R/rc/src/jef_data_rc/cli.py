"""``jef-data-rc``: the command-line surface of the EOD data layer.

The argparse shell stays thin and imports what a command needs only when
that command runs, so ``validate`` and ``universe`` never load the Parquet
store (pyarrow) or the HTTP stack (requests).

Exit codes: 0 success; 1 a failed verdict or operation (contract errors,
any failed sync leg, any status alert, a differential beyond tolerance, a
store/collector failure); 2 a usage, configuration or selection error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jef_data_rc.universe import ASSET_TYPE_BY_CLASS

ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
CRYPTO_SUFFIX = ".CC"
DEFAULT_STORE = "data"
DEFAULT_TAIL = 10


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _resolve_load_type(symbol: str, asset_type: str | None) -> str:
    """The manual load's declared type: required unless ``.CC`` implies crypto."""
    is_crypto_namespace = symbol.upper().endswith(CRYPTO_SUFFIX)
    if asset_type is None:
        if is_crypto_namespace:
            return "crypto"
        raise ValueError(
            f"--asset-type is required for {symbol} (one of {', '.join(ASSET_TYPES)}); "
            f"only an EODHD {CRYPTO_SUFFIX} symbol implies crypto"
        )
    if is_crypto_namespace and asset_type != "crypto":
        raise ValueError(
            f"{symbol} is in the EODHD {CRYPTO_SUFFIX} crypto namespace but "
            f"--asset-type is {asset_type}"
        )
    return asset_type


# -- commands ---------------------------------------------------------------


def cmd_validate(args) -> int:
    import pandas as pd

    from jef_data_rc.contract import validate

    frame = pd.read_csv(args.csv)
    print(f"{args.csv}: {len(frame)} row(s)")
    report = validate(frame, min_rows=args.min_rows)
    print(report.render())
    return 0 if report.ok else 1


def _render_universe(universe: dict, label: str) -> str:
    defaults = universe["defaults"]
    lines = [f"universe {label}: store {defaults['store']}, currency {defaults['currency']}"]
    for asset in universe["assets"]:
        state = "enabled" if asset["enabled"] else "disabled"
        line = (
            f"{asset['name']:<6} {asset['asset_class']} -> {asset['asset_type']}  "
            f"{asset['currency']}  {state}"
        )
        if asset["threshold"] is not None:
            line += f"  threshold {asset['threshold']:g}"
        lines.append(line)
        live = [s for s in asset["sources"] if s["enabled"]]
        for source in asset["sources"]:
            modeled = source["modeled"] or (
                asset["enabled"] and len(live) == 1 and source is live[0]
            )
            flags = []
            if modeled:
                flags.append("modeled")
            if not source["enabled"]:
                flags.append("disabled")
            row = (
                f"  {source['provider']:<9} {source['exchange']}:{source['symbol']}"
            )
            if source["path"] is not None:
                row += f"  path {source['path']}"
            if source["start"] is not None:
                row += f"  start {source['start']}"
            if source["end"] is not None:
                row += f"  end {source['end']}"
            if flags:
                row += f"  [{', '.join(flags)}]"
            if source["note"]:
                row += f"  # {source['note']}"
            lines.append(row)
    return "\n".join(lines)


def cmd_universe(args) -> int:
    from jef_data_rc.universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
    except UniverseError as exc:
        _err(f"universe: {exc}")
        return 2
    label = args.universe if args.universe is not None else "(packaged)"
    print(_render_universe(universe, label))
    return 0


def cmd_sync_actions(args) -> int:
    from jef_data_rc.actions import sync_actions
    from jef_data_rc.collectors.base import CollectorError
    from jef_data_rc.collectors.eodhd import EODHDCollector, normalize_symbol

    try:
        symbol = normalize_symbol(args.symbol)
        collector = EODHDCollector()
        try:
            splits, dividends = sync_actions(
                collector, args.store, symbol, exchange=args.exchange
            )
        finally:
            collector.close()
    except CollectorError as exc:
        _err(f"sync-actions: {exc}")
        return 1
    print(
        f"{args.exchange}:{symbol}: {len(splits)} split(s), {len(dividends)} "
        f"dividend(s) saved -> store {args.store}"
    )
    return 0


def cmd_load(args) -> int:
    from jef_data_rc.adjust import AdjustmentError
    from jef_data_rc.collectors.base import CollectorError
    from jef_data_rc.collectors.eodhd import EODHDCollector, normalize_symbol
    from jef_data_rc.store import ParquetStore, StoreError
    from jef_data_rc.sync import load_symbol

    try:
        symbol = normalize_symbol(args.symbol)
        asset_type = _resolve_load_type(symbol, args.asset_type)
    except (CollectorError, ValueError) as exc:
        _err(f"load: {exc}")
        return 2
    store = ParquetStore(args.store)
    try:
        collector = EODHDCollector()
        try:
            count = load_symbol(
                store,
                collector,
                symbol,
                exchange=args.exchange,
                asset_type=asset_type,
                currency=args.currency,
                start=args.start,
                end=args.end,
            )
        finally:
            collector.close()
    except (CollectorError, StoreError, AdjustmentError) as exc:
        _err(f"load: {exc}")
        return 1
    basis = "split_adjusted" if asset_type == "crypto" else "raw"
    print(
        f"{args.exchange}:{symbol}: loaded {count} bar(s) as {asset_type} "
        f"({basis}) -> store {args.store}"
    )
    return 0


def cmd_adjust(args) -> int:
    from jef_data_rc.actions import load_splits
    from jef_data_rc.adjust import AdjustmentError
    from jef_data_rc.store import ParquetStore, StoreError

    store = ParquetStore(args.store)
    if store.latest_date(args.exchange, args.symbol) is None:
        _err(f"adjust: no stored rows for {args.exchange}:{args.symbol}")
        return 1
    splits = load_splits(args.store, args.symbol)
    try:
        changed = store.reapply_adjustment(args.exchange, args.symbol, splits)
    except (AdjustmentError, StoreError) as exc:
        _err(f"adjust: {exc}")
        return 1
    state = "re-derived" if changed else "unchanged"
    print(f"{args.exchange}:{args.symbol}: {state} with {len(splits)} split(s)")
    return 0


def cmd_import_csv(args) -> int:
    from jef_data_rc.store import ParquetStore, StoreError

    store = ParquetStore(args.store)
    try:
        rows = store.ingest_yahoo_csv(
            args.csv,
            exchange=args.exchange,
            symbol=args.symbol,
            asset_type=args.asset_type,
            currency=args.currency,
        )
    except (StoreError, ValueError, OSError) as exc:
        _err(f"import-csv: {exc}")
        return 1
    print(
        f"imported {rows} row(s) into {args.exchange}:{args.symbol} "
        f"(split_adjusted) -> store {args.store}"
    )
    return 0


def cmd_export(args) -> int:
    from jef_data_rc.contract import validate
    from jef_data_rc.store import ParquetStore

    store = ParquetStore(args.store)
    frame = store.to_contract_frame(args.exchange, args.symbol)
    if not len(frame):
        _err(f"export: no stored rows for {args.exchange}:{args.symbol}")
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f"wrote {len(frame)} row(s) to {args.output}")
    report = validate(frame)
    print(report.render())
    return 0 if report.ok else 1


def cmd_differential(args) -> int:
    import pandas as pd

    from jef_data_rc.differential import compare_frames
    from jef_data_rc.store import ParquetStore

    store = ParquetStore(args.store)
    frame_a = store.to_contract_frame(args.a_exchange, args.a_symbol)
    label_a = f"{args.a_exchange}:{args.a_symbol}"
    if args.b_csv is not None:
        frame_b = pd.read_csv(args.b_csv)
        label_b = args.b_csv
    else:
        frame_b = store.to_contract_frame(args.b_exchange, args.b_symbol)
        label_b = f"{args.b_exchange}:{args.b_symbol}"
    report = compare_frames(
        frame_a, frame_b, tolerance=args.tolerance, label_a=label_a, label_b=label_b
    )
    text = report.render()
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0 if report.ok else 1


def cmd_sync(args) -> int:
    from jef_data_rc.sync import SyncError, run_sync, sync_summary
    from jef_data_rc.universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
        results, ok = run_sync(
            universe,
            store=args.store,
            assets=args.asset,
            providers=args.provider,
            tail=args.tail,
            force_actions=args.force_actions,
            dry_run=args.dry_run,
            out=print,
        )
    except (UniverseError, SyncError) as exc:
        _err(f"sync: {exc}")
        return 2
    if args.summary_json:
        path = Path(args.summary_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(sync_summary(results, ok), handle, indent=1)
            handle.write("\n")
    return 0 if ok else 1


def cmd_status(args) -> int:
    from jef_data_rc.health import evaluate_status, render_text
    from jef_data_rc.sync import SyncError
    from jef_data_rc.universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
        from jef_data_rc.sync import select_legs

        select_legs(universe, args.asset, args.provider)
    except (UniverseError, SyncError) as exc:
        _err(f"status: {exc}")
        return 2
    document, code = evaluate_status(
        universe,
        args.store,
        assets=args.asset,
        providers=args.provider,
        now=datetime.now(timezone.utc),
        window=args.window,
        jump_threshold=args.jump_threshold,
        staleness_k=args.staleness,
        resolution_window=args.resolution_window,
        resolution_k=args.resolution_k,
        flat_k=args.flat_k,
        gap_k=args.gap_k,
        spread_threshold=args.spread_threshold,
        spread_alerts=args.spread_alerts,
    )
    if args.json:
        print(json.dumps(document, indent=1))
    else:
        print(render_text(document))
    return code


# -- parser -----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    from jef_data_rc import contract, differential, health

    parser = argparse.ArgumentParser(
        prog="jef-data-rc",
        description=(
            "EOD acquisition, local store, split adjustment and store health. "
            "The store is read by jef.binning.loading; this tool owns the "
            "acquisition side of that seam."
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p = sub.add_parser("validate", help="check a CSV against the seven-column EOD contract")
    p.add_argument("csv", help="Date,Open,High,Low,Close,Adj Close,Volume CSV")
    p.add_argument(
        "--min-rows",
        type=int,
        default=contract.DEFAULT_MIN_ROWS,
        help="advisory clean-row minimum (default %(default)s = 720 warm-up + 30 + 365)",
    )
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("universe", help="print the normalized acquisition universe")
    p.add_argument("--universe", default=None, help="universe TOML (default: packaged)")
    p.set_defaults(func=cmd_universe)

    p = sub.add_parser(
        "sync",
        help="acquire every selected universe leg into the local store",
    )
    p.add_argument("--universe", default=None, help="universe TOML (default: packaged)")
    p.add_argument("--store", default=None, help="store root (default: the universe's)")
    p.add_argument("--asset", action="append", default=None, metavar="NAME",
                   help="only this asset (repeatable)")
    p.add_argument("--provider", action="append", default=None, metavar="PROVIDER",
                   help="only this provider: eodhd, binance, yahoo-csv (repeatable)")
    p.add_argument("--tail", type=int, default=DEFAULT_TAIL,
                   help="stored sessions re-fetched and reconciled (default %(default)s)")
    p.add_argument("--force-actions", action="store_true",
                   help="refresh corporate actions even if refreshed today (UTC)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan from local state; no collectors, requests or writes")
    p.add_argument("--summary-json", default=None, metavar="FILE",
                   help="write a machine-readable summary (also on a red run)")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("status", help="offline store health; exit 1 on any alert")
    p.add_argument("--universe", default=None, help="universe TOML (default: packaged)")
    p.add_argument("--store", default=None, help="store root (default: the universe's)")
    p.add_argument("--asset", action="append", default=None, metavar="NAME",
                   help="only this asset (repeatable)")
    p.add_argument("--provider", action="append", default=None, metavar="PROVIDER",
                   help="only this provider (repeatable)")
    p.add_argument("--json", action="store_true", help="print one JSON envelope")
    p.add_argument("--staleness", type=int, default=health.DEFAULT_STALENESS_K,
                   help="missed expected sessions that raise a stale alert (default %(default)s)")
    p.add_argument("--jump-threshold", type=float, default=health.DEFAULT_JUMP_THRESHOLD,
                   help="absolute one-row close return above which an unexplained "
                        "jump alerts (default %(default)s)")
    p.add_argument("--window", type=int, default=health.DEFAULT_WINDOW,
                   help="newest rows scanned for jumps and a common cross-venue "
                        "session (default %(default)s)")
    p.add_argument("--resolution-window", type=int, default=health.DEFAULT_RESOLUTION_WINDOW,
                   help="newest traded sessions measured for price resolution "
                        "(default %(default)s)")
    p.add_argument("--resolution-k", type=float, default=health.DEFAULT_RESOLUTION_K,
                   help="distinct/sessions ratio below which resolution is noted "
                        "(default %(default)s)")
    p.add_argument("--flat-k", type=float, default=health.DEFAULT_FLAT_K,
                   help="flat-close share above which resolution is noted (default %(default)s)")
    p.add_argument("--gap-k", type=int, default=health.DEFAULT_GAP_K,
                   help="post-seam absent expected sessions noted (default %(default)s)")
    p.add_argument("--spread-threshold", type=float, default=health.DEFAULT_SPREAD_THRESHOLD,
                   help="relative cross-venue close spread above which a pair "
                        "finding is raised (default %(default)s)")
    p.add_argument("--spread-alerts", action="store_true",
                   help="promote a spread breach from warning to alert")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync-actions", help="fetch and save one symbol's splits and dividends")
    p.add_argument("--symbol", required=True, help="EODHD symbol, e.g. AAPL.US")
    p.add_argument("--exchange", default="eodhd", help="store exchange tag (default %(default)s)")
    p.add_argument("--store", default=DEFAULT_STORE, help="store root (default %(default)s)")
    p.set_defaults(func=cmd_sync_actions)

    p = sub.add_parser("load", help="manual incremental EODHD load (append)")
    p.add_argument("--symbol", required=True, help="EODHD symbol, e.g. AAPL.US")
    p.add_argument("--asset-type", choices=ASSET_TYPES, default=None,
                   help="declared store type; required unless the symbol is .CC")
    p.add_argument("--exchange", default="eodhd", help="store exchange tag (default %(default)s)")
    p.add_argument("--store", default=DEFAULT_STORE, help="store root (default %(default)s)")
    p.add_argument("--start", default=None, help="first date (default: day after latest stored)")
    p.add_argument("--end", default=None, help="last date")
    p.add_argument("--currency", default="USD", help="currency (default %(default)s)")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("adjust", help="re-derive a raw-basis series from *_raw and stored splits")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd", help="store exchange tag (default %(default)s)")
    p.add_argument("--store", default=DEFAULT_STORE, help="store root (default %(default)s)")
    p.set_defaults(func=cmd_adjust)

    p = sub.add_parser("import-csv", help="import a Yahoo-format pre-adjusted CSV (overwrite)")
    p.add_argument("--csv", required=True, help="Date,Open,High,Low,Close,Adj Close,Volume CSV")
    p.add_argument("--symbol", required=True)
    p.add_argument("--asset-type", choices=ASSET_TYPES, required=True)
    p.add_argument("--exchange", default="yahoo", help="store exchange tag (default %(default)s)")
    p.add_argument("--currency", default="USD", help="currency (default %(default)s)")
    p.add_argument("--store", default=DEFAULT_STORE, help="store root (default %(default)s)")
    p.set_defaults(func=cmd_import_csv)

    p = sub.add_parser(
        "export",
        help="write a stored series as the seven-column contract CSV and validate it",
        description=(
            "Write the seven-column interchange CSV. This is the interoperable "
            "path; the bit-exact consumer path is "
            "jef.binning.loading.load_eod_store, which reads the store directly."
        ),
    )
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd", help="store exchange tag (default %(default)s)")
    p.add_argument("--output", required=True, help="CSV to write")
    p.add_argument("--store", default=DEFAULT_STORE, help="store root (default %(default)s)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("differential", help="compare two series within a relative tolerance")
    p.add_argument("--store", default=DEFAULT_STORE, help="store root (default %(default)s)")
    p.add_argument("--a-exchange", default="eodhd", help="A exchange tag (default %(default)s)")
    p.add_argument("--a-symbol", required=True, help="A symbol")
    p.add_argument("--b-exchange", default="eodhd", help="B exchange tag (default %(default)s)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--b-symbol", default=None, help="B stored symbol")
    group.add_argument("--b-csv", default=None, help="B reference CSV")
    p.add_argument("--tolerance", type=float, default=differential.DEFAULT_TOLERANCE,
                   help="relative tolerance per cell (default %(default)s)")
    p.add_argument("--output", default=None, help="also write the report here")
    p.set_defaults(func=cmd_differential)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
