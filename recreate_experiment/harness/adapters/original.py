"""Harness adapter for the SUBJECT (J-F's jef.data). Glue only: maps the fixed
interface in HARNESS_INTERFACE.md onto the subject's own API."""
from dataclasses import asdict, is_dataclass


def _rate_limiter():
    from jef.data.collectors import RateLimiter
    return RateLimiter(per_minute=10**6, daily_budget=10**9)


def make_collector(provider, fixture_dir, api_key="test-key-not-real"):
    from jef.data.collectors import ReplayTransport
    transport = ReplayTransport(str(fixture_dir))
    if provider == "eodhd":
        from jef.data.collectors.eodhd import EODHDCollector
        return EODHDCollector(api_key=api_key, transport=transport,
                              rate_limiter=_rate_limiter())
    if provider == "binance":
        from jef.data.collectors.binance import BinanceCollector
        return BinanceCollector(transport=transport, rate_limiter=_rate_limiter())
    raise ValueError(provider)


def load_universe(path):
    from jef.data.universe import load_universe
    return load_universe(path)


def select_legs(universe, assets=None, providers=None):
    from jef.data.sync import select_legs
    return select_legs(universe, assets=assets, providers=providers)


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False,
             tail=10, force_actions=False, now=None, collectors=None, out=None):
    from jef.data.sync import run_sync as _run
    c = collectors or {}
    return _run(universe, store_path=store_path, assets=assets, providers=providers,
                dry_run=dry_run, eodhd_collector=c.get("eodhd"),
                binance_collector=c.get("binance"), tail=tail,
                force_actions=force_actions, now=now,
                out=out if out is not None else (lambda *_: None))


def sync_summary(results, ok):
    from jef.data.sync import sync_summary
    return sync_summary(results, ok)


def status_json(universe, store_path, *, assets=None, providers=None, now=None,
                window=10, jump_threshold=0.40, staleness_k=2, resolution_window=500,
                resolution_k=0.20, flat_k=0.25, gap_k=5, spread_threshold=0.005,
                spread_alerts=False):
    from jef.data.actions import CorporateActionsStore
    from jef.data.health import check_cross_venue, check_source, multi_feed_legs
    from jef.data.store import ParquetStore
    from jef.data.sync import select_legs
    legs = select_legs(universe, assets=assets, providers=providers)
    store = ParquetStore(store_path)
    actions_store = CorporateActionsStore(store_path)
    live = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    reports = [check_source(store, actions_store, leg, now=now, window=window,
                            jump_threshold=jump_threshold, staleness_k=staleness_k,
                            resolution_window=resolution_window,
                            resolution_k=resolution_k, flat_k=flat_k, gap_k=gap_k)
               for leg in live]
    pairs = []
    for asset, asset_legs in multi_feed_legs(live).items():
        pairs.extend(check_cross_venue(store, asset, asset_legs, window=window,
                                       threshold=spread_threshold,
                                       promote_to_alert=spread_alerts))
    alerts = sum(len(r["alerts"]) for r in reports + pairs)
    warnings = sum(len(r.get("warnings", ())) for r in reports + pairs)
    doc = {"schema_version": 1, "store": str(store_path), "reports": reports,
           "pairs": pairs, "alerts_total": alerts, "warnings_total": warnings}
    return doc, (1 if alerts else 0)


def export_frame(store_path, exchange, symbol):
    from jef.data.store import ParquetStore, to_contract_frame
    return to_contract_frame(ParquetStore(store_path).load(exchange, symbol))


def stored_frame(store_path, exchange, symbol):
    from jef.data.store import ParquetStore
    return ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path, symbol):
    from jef.data.actions import CorporateActionsStore
    s = CorporateActionsStore(store_path)
    # The stored fields as the file holds them (HARNESS_INTERFACE.md): the
    # splits file's key is `split`; SplitEvent's dataclass field is
    # `split_string`. Until 2026-10-23 (wave 2) this returned the dataclass
    # fields, the `split`/`split_string` ambiguity recorded under M6post.
    import json, os
    path = s._path("splits", symbol)
    stamp = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            stamp = json.load(f)["last_updated"]      # the stored text, e.g. "...Z"
    splits = [dict(item) for item in s._load("splits", "splits", symbol)]
    return {"splits": splits, "dividends": list(s.load_dividends(symbol)),
            "last_updated": stamp}


def import_csv(store_path, csv_path, exchange, symbol, asset_type, currency="USD"):
    from jef.data.store import ParquetStore
    return ParquetStore(store_path).ingest_yahoo_csv(
        csv_path, exchange, symbol, asset_type=asset_type, currency=currency)
