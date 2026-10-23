"""The jef-data command line."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

import pandas as pd

from . import health
from .actions import CorporateActionsStore, sync_actions
from .collectors.eodhd import DEFAULT_BASE_URL, EODHDCollector, normalize_symbol
from .contract import MIN_CLEAN_ROWS, validate_frame
from .differential import DEFAULT_TOLERANCE, differential_report
from .store import ParquetStore, export_frame
from .sync import DEFAULT_TAIL, SyncError, run_sync, sync_summary
from .universe import ASSET_TYPES, UniverseError, listing_lines, load_universe

PROG = "jef-data"


class DeclarationRefused(ValueError):
    """A hand-run load whose declaration cannot be trusted."""


class _Refusal(Exception):
    def __init__(self, command, message):
        super().__init__(message)
        self.command = command
        self.message = message


def _out(line=""):
    sys.stdout.write(f"{line}\n")


def build_parser():
    parser = argparse.ArgumentParser(prog=PROG, description="EOD data layer")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p = sub.add_parser("validate", help="validate a CSV against the EOD input contract")
    p.add_argument("csv")
    p.add_argument("--min-rows", type=int, default=MIN_CLEAN_ROWS)

    p = sub.add_parser("sync-actions", help="sync a symbol's splits and dividends")
    p.add_argument("--symbol", required=True)
    p.add_argument("--store", default="data")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)

    p = sub.add_parser("load", help="hand-run EODHD load of one symbol")
    p.add_argument("--symbol", required=True)
    p.add_argument("--store", default="data")
    p.add_argument("--from", dest="start", default=None)
    p.add_argument("--to", dest="end", default=None)
    p.add_argument("--asset-type", choices=ASSET_TYPES, default=None)
    p.add_argument("--currency", default="USD")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)

    p = sub.add_parser("adjust", help="re-derive a series from its raw columns")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--store", default="data")

    p = sub.add_parser("import-csv", help="import a Yahoo CSV as a whole series")
    p.add_argument("--csv", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="yahoo")
    p.add_argument("--asset-type", choices=ASSET_TYPES, required=True)
    p.add_argument("--currency", default="USD")
    p.add_argument("--store", default="data")

    p = sub.add_parser("export", help="write a series' seam frame as CSV")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--output", required=True)
    p.add_argument("--store", default="data")

    p = sub.add_parser("differential", help="compare two series within a tolerance")
    p.add_argument("--a-symbol", required=True)
    p.add_argument("--a-exchange", default="eodhd")
    p.add_argument("--b-symbol", default=None)
    p.add_argument("--b-exchange", default="yahoo")
    p.add_argument("--b-csv", default=None)
    p.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    p.add_argument("--output", default=None)
    p.add_argument("--store", default="data")

    p = sub.add_parser("sync", help="run the universe's acquisition legs")
    p.add_argument("--universe", default=None)
    p.add_argument("--store", default=None)
    p.add_argument("--asset", action="append", default=None)
    p.add_argument("--provider", action="append", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--tail", type=int, default=DEFAULT_TAIL)
    p.add_argument("--force-actions", action="store_true")
    p.add_argument("--base-url", default=None)
    p.add_argument("--summary-json", default=None)

    p = sub.add_parser("status", help="read-only health verdicts of the store")
    p.add_argument("--universe", default=None)
    p.add_argument("--store", default=None)
    p.add_argument("--asset", action="append", default=None)
    p.add_argument("--provider", action="append", default=None)
    p.add_argument("--staleness", type=int, default=health.DEFAULT_STALENESS)
    p.add_argument("--jump-threshold", type=float, default=health.DEFAULT_JUMP_THRESHOLD)
    p.add_argument("--window", type=int, default=health.DEFAULT_WINDOW)
    p.add_argument("--resolution-window", type=int, default=health.DEFAULT_RESOLUTION_WINDOW)
    p.add_argument("--resolution-k", type=float, default=health.DEFAULT_RESOLUTION_K)
    p.add_argument("--flat-k", type=float, default=health.DEFAULT_FLAT_K)
    p.add_argument("--gap-k", type=int, default=health.DEFAULT_GAP_K)
    p.add_argument("--spread-threshold", type=float, default=health.DEFAULT_SPREAD_THRESHOLD)
    p.add_argument("--spread-alerts", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("universe", help="list the universe")
    p.add_argument("--universe", default=None)
    return parser


def _universe(command, path):
    try:
        return load_universe(path)
    except UniverseError as exc:
        raise _Refusal(command, str(exc)) from None


def cmd_validate(args):
    frame = pd.read_csv(args.csv)
    _out(f"{args.csv}: {len(frame)} rows")
    report = validate_frame(frame, min_rows=args.min_rows)
    _out(report.render())
    return 0 if report.ok else 1


def cmd_sync_actions(args):
    collector = EODHDCollector(base_url=args.base_url)
    try:
        symbol = normalize_symbol(args.symbol)
        store = CorporateActionsStore(Path(args.store) / "corporate_actions")
        n_splits, n_dividends = sync_actions(collector, store, symbol)
    finally:
        collector.close()
    _out(f"{args.symbol}: {n_splits} split(s), {n_dividends} dividend(s) -> "
         f"{args.store}/corporate_actions/")
    return 0


def resolve_declaration(symbol, asset_type):
    """The store asset_type of a hand-run load, or DeclarationRefused."""
    in_cc = symbol.endswith(".CC")
    if asset_type is None:
        if not in_cc:
            raise DeclarationRefused(
                f"{symbol}: asset_type is required (one of {ASSET_TYPES}). The ticker carries "
                f"no instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly "
                f"like equities - so the old 'stock' default was a guess written into the "
                f"store as a fact, and TLT is in this repo's universe as an explicit override "
                f"because that guess got it wrong. Only EODHD's .CC crypto namespace is "
                f"evidence enough to infer from")
        return "crypto"
    if asset_type not in ASSET_TYPES:
        raise DeclarationRefused(
            f"unknown asset_type {asset_type!r}; the store vocabulary is {ASSET_TYPES} "
            f"(derived from the universe's own asset_class map, "
            f"jef.data.universe.ASSET_TYPE_BY_CLASS)")
    if in_cc and asset_type != "crypto":
        raise DeclarationRefused(
            f"{symbol} is in EODHD's .CC crypto namespace but was declared "
            f"asset_type={asset_type!r}; that combination cannot be true, and guessing either "
            f"way decides whether split adjustment runs on pre-adjusted prices "
            f"(docs/DATA_CONTRACT.md §2)")
    return asset_type


def cmd_load(args):
    collector = EODHDCollector(base_url=args.base_url)
    try:
        symbol = normalize_symbol(args.symbol)
        try:
            asset_type = resolve_declaration(symbol, args.asset_type)
        except DeclarationRefused as exc:
            raise _Refusal("load", str(exc)) from None
        basis = "split_adjusted" if asset_type == "crypto" else "raw"
        store = ParquetStore(args.store)
        actions = CorporateActionsStore(Path(args.store) / "corporate_actions")
        latest = store.latest_date("eodhd", symbol)
        if args.start:
            start = args.start
        elif latest is not None:
            start = (latest + _dt.timedelta(days=1)).isoformat()
        else:
            start = None
        bars = collector.get_eod(symbol, start, args.end)
        splits = actions.load_splits(symbol) if basis == "raw" else []
        count = store.ingest_bars("eodhd", symbol, bars, splits, basis,
                                  collector.volume_basis, mode="append",
                                  asset_type=asset_type, currency=args.currency)
        if basis == "raw" and (count > 0 or latest is not None):
            store.reapply_adjustment("eodhd", symbol, splits)
    finally:
        collector.close()
    _out(f"{args.symbol}: {count} bar(s) ingested -> {args.store}/market_data/")
    return 0


def cmd_adjust(args):
    store = ParquetStore(args.store)
    actions = CorporateActionsStore(Path(args.store) / "corporate_actions")
    splits = actions.load_splits(args.symbol)
    rows = store.reapply_adjustment(args.exchange, args.symbol, splits)
    _out(f"{args.exchange}/{args.symbol}: {rows} row(s) re-derived from *_raw with "
         f"{len(splits)} split(s)")
    return 0


def cmd_import_csv(args):
    store = ParquetStore(args.store)
    rows = store.ingest_yahoo_csv(args.csv, args.exchange, args.symbol, args.asset_type,
                                  args.currency)
    _out(f"{args.csv}: {rows} row(s) -> {args.store}/market_data/exchange={args.exchange}/"
         f"symbol={args.symbol}/ (price_basis=split_adjusted)")
    return 0


def cmd_export(args):
    frame = export_frame(ParquetStore(args.store), args.exchange, args.symbol)
    frame.to_csv(args.output, index=False)
    _out(f"{args.exchange}/{args.symbol}: {len(frame)} row(s) -> {args.output}")
    report = validate_frame(frame)
    _out(report.render())
    return 0 if report.ok else 1


def cmd_differential(args):
    if args.b_csv is None and args.b_symbol is None:
        raise _Refusal("differential", "pass --b-csv or --b-symbol")
    store = ParquetStore(args.store)
    frame_a = export_frame(store, args.a_exchange, args.a_symbol)
    label_a = f"{args.a_exchange}/{args.a_symbol}"
    if args.b_csv is not None:
        frame_b = pd.read_csv(args.b_csv)
        label_b = args.b_csv
    else:
        frame_b = export_frame(store, args.b_exchange, args.b_symbol)
        label_b = f"{args.b_exchange}/{args.b_symbol}"
    lines, ok = differential_report(frame_a, frame_b, label_a, label_b, args.tolerance)
    text = "\n".join(lines)
    _out(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if ok else 1


def write_summary(path, results, ok):
    doc = sync_summary(results, ok)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def cmd_sync(args):
    universe = _universe("sync", args.universe)
    store = args.store if args.store is not None else universe["defaults"]["store"]
    try:
        results, ok = run_sync(universe, store, assets=args.asset, providers=args.provider,
                               dry_run=args.dry_run, tail=args.tail,
                               force_actions=args.force_actions, out=_out,
                               base_url=args.base_url)
    except SyncError as exc:
        raise _Refusal("sync", str(exc)) from None
    if args.summary_json:
        write_summary(args.summary_json, results, ok)
    return 0 if ok else 1


def cmd_status(args):
    universe = _universe("status", args.universe)
    store = args.store if args.store is not None else universe["defaults"]["store"]
    try:
        doc, rc = health.run_status(
            universe, store, assets=args.asset, providers=args.provider,
            window=args.window, jump_threshold=args.jump_threshold,
            staleness_k=args.staleness, resolution_window=args.resolution_window,
            resolution_k=args.resolution_k, flat_k=args.flat_k, gap_k=args.gap_k,
            spread_threshold=args.spread_threshold, spread_alerts=args.spread_alerts)
    except SyncError as exc:
        raise _Refusal("status", str(exc)) from None
    if args.json:
        _out(json.dumps(doc, indent=1))
    else:
        for line in health.table_lines(doc):
            _out(line)
    return rc


def cmd_universe(args):
    universe = _universe("universe", args.universe)
    for line in listing_lines(universe):
        _out(line)
    return 0


COMMANDS = {"validate": cmd_validate, "sync-actions": cmd_sync_actions, "load": cmd_load,
            "adjust": cmd_adjust, "import-csv": cmd_import_csv, "export": cmd_export,
            "differential": cmd_differential, "sync": cmd_sync, "status": cmd_status,
            "universe": cmd_universe}


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except _Refusal as refusal:
        sys.stdout.flush()
        sys.stderr.write(f"{refusal.command}: {refusal.message}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
