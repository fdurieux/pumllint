"""Command-line driver for the data layer (jef-data).

Subcommands by phase (docs/DATA_LOADER_PLAN.md §4): D1 validate;
D2 sync-actions; D4 load / adjust / import-csv / export; D5 differential;
D6 universe; D7 sync (the whole configured universe in one command,
ordering ritual included - see jef.data.sync and src/jef/data/universe.toml).

Like jef-binning, this is a thin argparse shell over importable functions;
anything network- or Parquet-touching imports its module lazily so the core
install (no [data] extra) can still run `jef-data validate`.
"""
import argparse
import datetime as _dt
import json
import sys

ASSET_TYPE_CHOICES = ["crypto", "etf", "stock"]
DEFAULT_BASE_URL = "https://eodhd.com/api"


def build_parser():
    parser = argparse.ArgumentParser(prog="jef-data", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="check a 7-column EOD CSV against docs/DATA_CONTRACT.md")
    p.add_argument("csv", help="CSV in the Yahoo 7-column schema")
    p.add_argument("--min-rows", type=int, default=1115, help="advisory minimum clean-row count")

    p = sub.add_parser("sync-actions", help="fetch splits + dividends from EODHD into the actions "
                       "store (needs EODHD_API_KEY; run BEFORE load)")
    p.add_argument("--symbol", required=True, help="e.g. AAPL.US")
    p.add_argument("--store", default="data", help="store root (default: data/, gitignored)")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)

    p = sub.add_parser("load", help="fetch EOD history from EODHD into the Parquet store "
                       "(incremental; needs EODHD_API_KEY; sync-actions first)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--store", default="data")
    p.add_argument("--from", help="YYYY-MM-DD (default: incremental from the last stored session)")
    p.add_argument("--to")
    p.add_argument("--asset-type", choices=ASSET_TYPE_CHOICES,
                   help="required, except for EODHD .CC symbols (the crypto namespace is "
                        "evidence); a ticker is not")
    p.add_argument("--currency", default="USD")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)

    p = sub.add_parser("adjust", help="re-derive main OHLCV from *_raw + stored splits (offline, "
                       "idempotent; also the repair path)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--store", default="data")

    p = sub.add_parser("import-csv", help="import a Yahoo 7-column CSV verbatim "
                       "(price_basis=split_adjusted; offline)")
    p.add_argument("--csv", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="yahoo")
    p.add_argument("--asset-type", required=True, choices=ASSET_TYPE_CHOICES,
                   help="required: a Yahoo CSV carries no instrument type")
    p.add_argument("--currency", default="USD")
    p.add_argument("--store", default="data")

    p = sub.add_parser("export", help="store -> 7-column contract CSV (values identical; the "
                       "bit-exact consumer path is jef.binning.loading.load_eod_store)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--exchange", default="eodhd")
    p.add_argument("--output", required=True)
    p.add_argument("--store", default="data")

    p = sub.add_parser("differential", help="tolerance-based comparison of two series (store vs "
                       "store, or store vs a 7-column CSV) - the cross-provider gate; exit 1 on "
                       "findings")
    p.add_argument("--a-symbol", required=True)
    p.add_argument("--a-exchange", default="eodhd")
    p.add_argument("--b-symbol")
    p.add_argument("--b-exchange", default="yahoo")
    p.add_argument("--b-csv", help="compare against a CSV instead of a stored series")
    p.add_argument("--tolerance", type=float, default=0.0001,
                   help="relative tolerance per cell (default 1e-4)")
    p.add_argument("--output", help="also write the report here")
    p.add_argument("--store", default="data")

    p = sub.add_parser("sync", help="run the whole universe's acquisition ritual from the config "
                       "(per raw-basis symbol: sync-actions BEFORE load; tail-refresh reconcile "
                       "once a series exists, crypto end-guarded at the previous UTC day; EODHD "
                       "legs need EODHD_API_KEY)")
    p.add_argument("--universe", help="universe TOML (default: the packaged "
                   "src/jef/data/universe.toml)")
    p.add_argument("--store", help="store root (default: the universe's defaults.store)")
    p.add_argument("--asset", action="append", help="limit to this asset name (repeatable)")
    p.add_argument("--provider", action="append", help="limit to this provider (repeatable), "
                   "e.g. --provider eodhd where Binance is unreachable")
    p.add_argument("--dry-run", action="store_true",
                   help="plan from local store state only - no network, no key needed")
    p.add_argument("--tail", type=int, default=10,
                   help="tail-refresh window in sessions, minimum 1 (docs/DATA_CONTRACT.md "
                        "§7.2; default 10): newest-wins inside, frozen-first-seen outside")
    p.add_argument("--force-actions", action="store_true",
                   help="sync corporate actions even when fresh (override the once-per-UTC-day "
                        "gate)")
    p.add_argument("--base-url", help="EODHD base URL override")
    p.add_argument("--summary-json", metavar="PATH",
                   help="write the per-leg results as JSON (the event ledger's stage_outcome "
                        "diagnostics, Arc A A3(a)); written on red runs too")

    p = sub.add_parser("status", help="read-only daily health: staleness, phantom-split scan, "
                       "actions freshness, today-dated bars, price resolution, and the "
                       "cross-venue close spread for multi-feed assets (offline, no key; exit 1 "
                       "on any alert - the scheduler chain is sync && status)")
    p.add_argument("--universe", help="universe TOML (default: the packaged one)")
    p.add_argument("--store", help="store root (default: the universe's defaults.store)")
    p.add_argument("--asset", action="append", help="limit to this asset name (repeatable)")
    p.add_argument("--provider", action="append", help="limit to this provider (repeatable)")
    p.add_argument("--staleness", type=int, default=2,
                   help="alert at this many missed expected sessions (docs/DATA_CONTRACT.md "
                        "§7.4; default 2)")
    p.add_argument("--jump-threshold", type=float, default=0.4,
                   help="phantom-split one-day |return| alert threshold (default 0.40)")
    p.add_argument("--window", type=int, default=10,
                   help="newest sessions scanned for jumps, and for the cross-venue common "
                        "session (default 10)")
    p.add_argument("--resolution-window", type=int, default=500,
                   help="newest TRADED sessions measured for price resolution - zero-volume rows "
                        "drop first, like the seam (docs/DATA_CONTRACT.md §7.8; default 500)")
    p.add_argument("--resolution-k", type=float, default=0.2,
                   help="note a coarse quoting grid below this distinct-close/session ratio "
                        "(default 0.20)")
    p.add_argument("--flat-k", type=float, default=0.25,
                   help="note a coarse/frozen feed above this share of sessions whose close did "
                        "not move (default 0.25)")
    p.add_argument("--gap-k", type=int, default=5,
                   help="note a post-seam continuity gap at or above this many absent expected "
                        "sessions (default 5, calibrated: the largest true US closure since 1962 "
                        "measures 4 - 2001-09-10..17 - so the market itself never notes; a "
                        "provider data hole does, however it is served)")
    p.add_argument("--spread-threshold", type=float, default=0.005,
                   help="cross-venue close-spread WARN threshold for assets with 2+ live feeds "
                        "(Arc X X1; default 0.005 = 0.5%%, calibrated on the committed fixtures "
                        "- docs/CROSS_VENUE_PLAN.md)")
    p.add_argument("--spread-alerts", action="store_true",
                   help="promote a cross-venue spread breach from a warning to an ALERT, so it "
                        "joins the exit-1 contract (off by default: it compares a CROSS-CHECK "
                        "leg, and exit 1 stops the venue's day before it publishes anything)")
    p.add_argument("--json", action="store_true", help="machine-readable report instead of the table")

    p = sub.add_parser("universe", help="show the configured universe (assets, sources, "
                       "thresholds; the D6 pilot by default)")
    p.add_argument("--universe", help="universe TOML (default: packaged)")
    return parser


def _out(line=""):
    print(line, flush=True)


def _refuse(command, message):
    print(f"{command}: {message}", file=sys.stderr, flush=True)
    return 1


def cmd_validate(args):
    import pandas as pd

    from .contract import validate_frame

    frame = pd.read_csv(args.csv)
    _out(f"{args.csv}: {len(frame)} rows")
    report = validate_frame(frame, args.min_rows)
    _out(report.render())
    return 0 if report.ok() else 1


def cmd_sync_actions(args):
    from .actions import CorporateActionsStore, sync_actions
    from .collectors.eodhd import EODHDCollector, normalize_symbol

    collector = EODHDCollector(base_url=args.base_url)
    try:
        symbol = normalize_symbol(args.symbol)
        splits, dividends = sync_actions(collector, CorporateActionsStore(args.store), symbol)
    finally:
        collector.close()
    _out(f"{args.symbol}: {splits} split(s), {dividends} dividend(s) -> {args.store}/corporate_actions/")
    return 0


def cmd_load(args):
    from .actions import CorporateActionsStore
    from .collectors.eodhd import EODHDCollector, normalize_symbol
    from .store import ParquetStore
    from .universe import DeclarationRefused, declare_asset_type

    collector = EODHDCollector(base_url=args.base_url)
    try:
        symbol = normalize_symbol(args.symbol)
        try:
            asset_type = declare_asset_type(symbol, args.asset_type)
        except DeclarationRefused as exc:
            collector.close()
            return _refuse("load", exc)
        basis = "split_adjusted" if asset_type == "crypto" else "raw"
        store = ParquetStore(args.store)
        start = getattr(args, "from")
        latest = store.latest_date("eodhd", symbol)
        had_rows = latest is not None
        if start is None and had_rows:
            start = (latest + _dt.timedelta(days=1)).isoformat()
        bars = collector.get_eod(symbol, start, args.to)
        splits = CorporateActionsStore(args.store).load_splits(symbol) if basis == "raw" else []
        count = store.ingest_bars("eodhd", symbol, bars, splits, basis, collector.volume_basis,
                                  mode="append", asset_type=asset_type, currency=args.currency)
        if basis == "raw" and (count > 0 or had_rows):
            store.reapply_adjustment("eodhd", symbol, splits)
    finally:
        collector.close()
    _out(f"{args.symbol}: {count} bar(s) ingested -> {args.store}/market_data/")
    return 0


def cmd_adjust(args):
    from .actions import CorporateActionsStore
    from .store import ParquetStore

    splits = CorporateActionsStore(args.store).load_splits(args.symbol)
    rows = ParquetStore(args.store).reapply_adjustment(args.exchange, args.symbol, splits)
    _out(f"{args.exchange}/{args.symbol}: {rows} row(s) re-derived from *_raw with "
         f"{len(splits)} split(s)")
    return 0


def cmd_import_csv(args):
    from .store import ParquetStore

    rows = ParquetStore(args.store).ingest_yahoo_csv(args.csv, args.exchange, args.symbol,
                                                     args.asset_type, args.currency)
    _out(f"{args.csv}: {rows} row(s) -> {args.store}/market_data/exchange={args.exchange}/"
         f"symbol={args.symbol}/ (price_basis=split_adjusted)")
    return 0


def cmd_export(args):
    from .contract import validate_frame
    from .store import ParquetStore

    frame = ParquetStore(args.store).export(args.exchange, args.symbol)
    frame.to_csv(args.output, index=False)
    _out(f"{args.exchange}/{args.symbol}: {len(frame)} row(s) -> {args.output}")
    report = validate_frame(frame)
    _out(report.render())
    return 0 if report.ok() else 1


def cmd_differential(args):
    import pandas as pd

    from .differential import differential_report
    from .store import ParquetStore

    if not args.b_csv and not args.b_symbol:
        return _refuse("differential", "pass --b-csv or --b-symbol")
    store = ParquetStore(args.store)
    frame_a = store.export(args.a_exchange, args.a_symbol)
    label_a = f"{args.a_exchange}/{args.a_symbol}"
    if args.b_csv:
        frame_b = pd.read_csv(args.b_csv)
        label_b = args.b_csv
    else:
        frame_b = store.export(args.b_exchange, args.b_symbol)
        label_b = f"{args.b_exchange}/{args.b_symbol}"
    lines, ok = differential_report(frame_a, frame_b, label_a, label_b, args.tolerance)
    text = "\n".join(lines)
    _out(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if ok else 1


def cmd_sync(args):
    from .sync import SyncError, run_sync, sync_summary
    from .universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
    except UniverseError as exc:
        return _refuse("sync", exc)
    store = args.store or universe["defaults"]["store"]
    try:
        results, ok = run_sync(universe, store, assets=args.asset, providers=args.provider,
                               dry_run=args.dry_run, tail=args.tail,
                               force_actions=args.force_actions, out=_out,
                               base_url=args.base_url)
    except SyncError as exc:
        return _refuse("sync", exc)
    if args.summary_json:
        with open(args.summary_json, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(sync_summary(results, ok), indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


def cmd_status(args):
    from .health import run_status, table_lines
    from .sync import SyncError
    from .universe import UniverseError, load_universe

    try:
        universe = load_universe(args.universe)
    except UniverseError as exc:
        return _refuse("status", exc)
    store = args.store or universe["defaults"]["store"]
    try:
        doc, rc = run_status(universe, store, assets=args.asset, providers=args.provider,
                             window=args.window, jump_threshold=args.jump_threshold,
                             staleness_k=args.staleness, resolution_window=args.resolution_window,
                             resolution_k=args.resolution_k, flat_k=args.flat_k,
                             gap_k=args.gap_k, spread_threshold=args.spread_threshold,
                             spread_alerts=args.spread_alerts)
    except SyncError as exc:
        return _refuse("status", exc)
    if args.json:
        _out(json.dumps(doc, indent=1))
    else:
        for line in table_lines(doc):
            _out(line)
    return rc


def cmd_universe(args):
    from .universe import UniverseError, listing, load_universe

    try:
        universe = load_universe(args.universe)
    except UniverseError as exc:
        return _refuse("universe", exc)
    for line in listing(universe):
        _out(line)
    return 0


COMMANDS = {
    "validate": cmd_validate, "sync-actions": cmd_sync_actions, "load": cmd_load,
    "adjust": cmd_adjust, "import-csv": cmd_import_csv, "export": cmd_export,
    "differential": cmd_differential, "sync": cmd_sync, "status": cmd_status,
    "universe": cmd_universe,
}


def main(argv=None):
    args = build_parser().parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
