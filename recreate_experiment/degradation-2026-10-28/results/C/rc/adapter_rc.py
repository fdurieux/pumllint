"""Harness adapter: maps the fixed harness interface onto jef_data_rc."""
import json

from jef_data_rc import health
from jef_data_rc import sync as _sync
from jef_data_rc import universe as _universe
from jef_data_rc.actions import CorporateActionsStore
from jef_data_rc.collectors.base import ReplayTransport
from jef_data_rc.store import ParquetStore, seam_frame


def _no_sleep(seconds):
    return None


def make_collector(provider, fixture_dir, api_key="test-key-not-real"):
    transport = ReplayTransport(fixture_dir)
    if provider == "eodhd":
        from jef_data_rc.collectors.eodhd import EODHDCollector
        return EODHDCollector(api_key=api_key, transport=transport, rate_limiter=None,
                              sleep=_no_sleep)
    if provider == "binance":
        from jef_data_rc.collectors.binance import BinanceCollector
        return BinanceCollector(transport=transport, rate_limiter=None, sleep=_no_sleep)
    raise ValueError(f"no collector for provider {provider!r}")


def load_universe(path):
    return _universe.load_universe(path)


def select_legs(universe, assets=None, providers=None):
    return _sync.select_legs(universe, assets, providers)


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False, tail=10,
             force_actions=False, now=None, collectors=None, out=None):
    return _sync.run_sync(universe, store_path, assets=assets, providers=providers,
                          dry_run=dry_run, tail=tail, force_actions=force_actions, now=now,
                          collectors=collectors, out=out)


def sync_summary(results, ok):
    return _sync.sync_summary(results, ok)


def status_json(universe, store_path, *, assets=None, providers=None, now=None, window=10,
                jump_threshold=0.40, staleness_k=2, resolution_window=500, resolution_k=0.20,
                flat_k=0.25, gap_k=5, spread_threshold=0.005, spread_alerts=False):
    doc, code = health.run_status(universe, store_path, assets=assets, providers=providers,
                                  now=now, window=window, jump_threshold=jump_threshold,
                                  staleness_k=staleness_k, resolution_window=resolution_window,
                                  resolution_k=resolution_k, flat_k=flat_k, gap_k=gap_k,
                                  spread_threshold=spread_threshold, spread_alerts=spread_alerts)
    return json.loads(json.dumps(doc, indent=1)), code


def export_frame(store_path, exchange, symbol):
    return seam_frame(ParquetStore(store_path).load(exchange, symbol))


def stored_frame(store_path, exchange, symbol):
    return ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path, symbol):
    store = CorporateActionsStore(store_path)
    return {"splits": store.raw_splits(symbol), "dividends": store.load_dividends(symbol),
            "last_updated": store.stamp_text(symbol)}


def import_csv(store_path, csv_path, exchange, symbol, asset_type, currency="USD"):
    return ParquetStore(store_path).ingest_yahoo_csv(csv_path, exchange, symbol, asset_type,
                                                     currency)
