"""The jef-data command line."""
import argparse
import datetime as _dt
import json
import sys

import pandas as pd

from . import actions, seam, store, sync
from .adjustment import price_basis_for
from .collectors import EODHDCollector, normalize_eodhd_symbol
from .status import render_table, run_status
from .universe import ASSET_TYPES, UniverseError, load_universe

PROG = "jef-data"


class Refusal(Exception):
    """A refusal the command prints as `{command}: {message}`."""


def _parser():
    parser = argparse.ArgumentParser(
        prog=PROG, description="EOD data acquisition, store and status checks.")
    sub = parser.add_subparsers(dest="command", metavar="command", required=True)

    p = sub.add_parser("validate", help="check a CSV against the EOD input contract")
    p.add_argument("csv")
    p.add_argument("--min-rows", type=int, default=seam.MIN_ROWS)

    p = sub.add_parser("sync-actions", help="sync a symbol's splits and dividends")
    p.add_argument("--symbol", required=True)
    p.add_argument("--store", default="data")
    p.add_argument("--base-url", default=None)

    p = sub.add_parser("load", help="hand-run EODHD bar load into the store")
    p.add_argument("--symbol", required=True)
    p.add_argument("--store", default="data")
    p.add_argument("--from", dest="start", metavar="YYYY-MM-DD", default=None)
    p.add_argument("--to", dest="end", metavar="YYYY-MM-DD", default=None)
    p.add_argument("--asset-type", choices=ASSET_TYPES, default=None)
    p.add_argument("--currency", default="USD")
    p.add_argument("--base-url", default=None)

    p = sub.add_parser("adjust", help="re-derive a raw series from *_raw and stored splits")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--store", default="data")

    p = sub.add_parser("import-csv", help="import a Yahoo 7-column CSV (overwrite)")
    p.add_argument("--csv", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="yahoo")
    p.add_argument("--asset-type", choices=ASSET_TYPES, required=True)
    p.add_argument("--currency", default="USD")
    p.add_argument("--store", default="data")

    p = sub.add_parser("export", help="write a stored series as the 7-column EOD CSV")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--output", required=True)
    p.add_argument("--store", default="data")

    p = sub.add_parser("differential", help="compare a stored series with another source")
    p.add_argument("--a-symbol", required=True)
    p.add_argument("--a-exchange", default="eodhd")
    p.add_argument("--b-symbol", default=None)
    p.add_argument("--b-exchange", default="yahoo")
    p.add_argument("--b-csv", default=None)
    p.add_argument("--tolerance", type=float, default=seam.DEFAULT_TOLERANCE)
    p.add_argument("--output", default=None)
    p.add_argument("--store", default="data")

    p = sub.add_parser("sync", help="run the declarative universe sync")
    p.add_argument("--universe", default=None)
    p.add_argument("--store", default=None)
    p.add_argument("--asset", action="append", default=None)
    p.add_argument("--provider", action="append", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--tail", type=int, default=sync.DEFAULT_TAIL)
    p.add_argument("--force-actions", action="store_true")
    p.add_argument("--base-url", default=None)
    p.add_argument("--summary-json", default=None)

    p = sub.add_parser("status", help="read-only freshness and integrity checks")
    p.add_argument("--universe", default=None)
    p.add_argument("--store", default=None)
    p.add_argument("--asset", action="append", default=None)
    p.add_argument("--provider", action="append", default=None)
    p.add_argument("--staleness", type=int, default=2)
    p.add_argument("--jump-threshold", type=float, default=0.40)
    p.add_argument("--window", type=int, default=10)
    p.add_argument("--resolution-window", type=int, default=500)
    p.add_argument("--resolution-k", type=float, default=0.20)
    p.add_argument("--flat-k", type=float, default=0.25)
    p.add_argument("--gap-k", type=int, default=5)
    p.add_argument("--spread-threshold", type=float, default=0.005)
    p.add_argument("--spread-alerts", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("universe", help="list the declared universe")
    p.add_argument("--universe", default=None)
    return parser


# ------------------------------------------------------------------ commands
def cmd_validate(args):
    frame = pd.read_csv(args.csv)
    print(f"{args.csv}: {len(frame)} rows")
    report = seam.validate(frame, min_rows=args.min_rows)
    for line in report.lines():
        print(line)
    return 0 if report.ok else 1


def cmd_sync_actions(args):
    collector = EODHDCollector(base_url=args.base_url)
    try:
        symbol = normalize_eodhd_symbol(args.symbol)
        n_splits, n_divs = actions.sync_actions(collector, args.store, symbol)
    finally:
        collector.close()
    print(f"{args.symbol}: {n_splits} split(s), {n_divs} dividend(s) -> "
          f"{args.store}/corporate_actions/")
    return 0


def _declared_type(sym, declared):
    crypto_namespace = sym.endswith(".CC")
    if declared is None:
        if not crypto_namespace:
            raise Refusal(
                f"{sym}: asset_type is required (one of {ASSET_TYPES}). The ticker carries "
                f"no instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled "
                f"exactly like equities - so the old 'stock' default was a guess written "
                f"into the store as a fact, and TLT is in this repo's universe as an "
                f"explicit override because that guess got it wrong. Only EODHD's .CC "
                f"crypto namespace is evidence enough to infer from")
        return "crypto"
    if declared not in ASSET_TYPES:
        raise Refusal(
            f"unknown asset_type {declared!r}; the store vocabulary is {ASSET_TYPES} "
            f"(derived from the universe's own asset_class map, "
            f"jef.data.universe.ASSET_TYPE_BY_CLASS)")
    if crypto_namespace and declared != "crypto":
        raise Refusal(
            f"{sym} is in EODHD's .CC crypto namespace but was declared "
            f"asset_type={declared!r}; that combination cannot be true, and guessing "
            f"either way decides whether split adjustment runs on pre-adjusted prices "
            f"(docs/DATA_CONTRACT.md §2)")
    return declared


def cmd_load(args):
    collector = EODHDCollector(base_url=args.base_url)
    try:
        sym = normalize_eodhd_symbol(args.symbol)
        asset_type = _declared_type(sym, args.asset_type)
        basis = price_basis_for("eodhd", asset_type)
        latest = store.latest_session(args.store, "eodhd", sym)
        start = args.start
        if start is None and latest is not None:
            start = (_dt.date.fromisoformat(latest) + _dt.timedelta(days=1)).isoformat()
        bars = collector.eod(sym, start, args.end)
        events = actions.read_splits(args.store, sym) if basis == "raw" else []
        n = store.append(args.store, "eodhd", sym, bars, asset_type=asset_type,
                         currency=args.currency, price_basis=basis,
                         volume_basis=collector.volume_basis, events=events)
        if basis == "raw" and (n > 0 or latest is not None):
            store.readjust(args.store, "eodhd", sym, events)
    finally:
        collector.close()
    print(f"{args.symbol}: {n} bar(s) ingested -> {args.store}/market_data/")
    return 0


def cmd_adjust(args):
    events = actions.read_splits(args.store, args.symbol)
    rows = store.readjust(args.store, args.exchange, args.symbol, events)
    print(f"{args.exchange}/{args.symbol}: {rows} row(s) re-derived from *_raw with "
          f"{len(events)} split(s)")
    return 0


def cmd_import_csv(args):
    rows = store.overwrite_csv(args.store, args.csv, args.exchange, args.symbol,
                               args.asset_type, args.currency)
    print(f"{args.csv}: {rows} row(s) -> {args.store}/market_data/exchange={args.exchange}/"
          f"symbol={args.symbol}/ (price_basis=split_adjusted)")
    return 0


def cmd_export(args):
    stored = store.read_series(args.store, args.exchange, args.symbol)
    if stored.empty:
        raise store.StoreError(f"nothing stored for {args.exchange}/{args.symbol}")
    frame = seam.seam_frame(stored)
    seam.write_csv(frame, args.output)
    print(f"{args.exchange}/{args.symbol}: {len(frame)} row(s) -> {args.output}")
    report = seam.validate(frame)
    for line in report.lines():
        print(line)
    return 0 if report.ok else 1


def cmd_differential(args):
    if args.b_csv is None and args.b_symbol is None:
        raise Refusal("pass --b-csv or --b-symbol")
    a = seam.export_frame(args.store, args.a_exchange, args.a_symbol)
    a_label = f"{args.a_exchange}/{args.a_symbol}"
    if args.b_csv is not None:
        b = pd.read_csv(args.b_csv)
        b_label = args.b_csv
    else:
        b = seam.export_frame(args.store, args.b_exchange, args.b_symbol)
        b_label = f"{args.b_exchange}/{args.b_symbol}"
    lines, ok = seam.differential(a, b, a_label, b_label, tolerance=args.tolerance)
    text = "\n".join(lines)
    print(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if ok else 1


def _load_universe(path):
    try:
        return load_universe(path)
    except UniverseError as exc:
        raise Refusal(str(exc)) from None


def cmd_sync(args):
    universe = _load_universe(args.universe)
    try:
        results, ok = sync.run_sync(
            universe, args.store, assets=args.asset, providers=args.provider,
            dry_run=args.dry_run, tail=args.tail, force_actions=args.force_actions,
            out=print, base_url=args.base_url)
    except sync.SyncError as exc:
        raise Refusal(str(exc)) from None
    if args.summary_json:
        doc = sync.summary(results, ok)
        with open(args.summary_json, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


def cmd_status(args):
    universe = _load_universe(args.universe)
    try:
        doc, rc = run_status(
            universe, args.store, assets=args.asset, providers=args.provider,
            window=args.window, jump_threshold=args.jump_threshold,
            staleness_k=args.staleness, resolution_window=args.resolution_window,
            resolution_k=args.resolution_k, flat_k=args.flat_k, gap_k=args.gap_k,
            spread_threshold=args.spread_threshold, spread_alerts=args.spread_alerts)
    except sync.SyncError as exc:
        raise Refusal(str(exc)) from None
    if args.json:
        print(json.dumps(doc, indent=1))
    else:
        for line in render_table(doc):
            print(line)
    return rc


def cmd_universe(args):
    universe = _load_universe(args.universe)
    for asset in universe["assets"]:
        line = (f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, "
                f"threshold {float(asset['threshold'])})")
        if not asset["enabled"]:
            line += " [disabled]"
        print(line)
        for source in asset["sources"]:
            target = source.get("path") or source["symbol"]
            line = f"  {source['provider']}: {target}"
            if not source["enabled"]:
                line += " [disabled]"
            if source.get("note"):
                line += f" - {source['note']}"
            print(line)
    return 0


COMMANDS = {"validate": cmd_validate, "sync-actions": cmd_sync_actions, "load": cmd_load,
            "adjust": cmd_adjust, "import-csv": cmd_import_csv, "export": cmd_export,
            "differential": cmd_differential, "sync": cmd_sync, "status": cmd_status,
            "universe": cmd_universe}


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except Refusal as exc:
        sys.stdout.flush()
        print(f"{args.command}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
