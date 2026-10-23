"""Harness adapter: the fixed comparison interface mapped onto jef_data_rc."""
from __future__ import annotations

import json

from jef_data_rc import health, store as _store, sync as _sync, universe as _universe
from jef_data_rc.actions import CorporateActionsStore
from jef_data_rc.collectors.base import RateLimiter, ReplayTransport
from jef_data_rc.collectors.binance import BinanceCollector
from jef_data_rc.collectors.eodhd import EODHDCollector


def _no_sleep(seconds):
    return None


def make_collector(provider, fixture_dir, api_key="test-key-not-real"):
    transport = ReplayTransport(fixture_dir)
    limiter = RateLimiter(enabled=False)
    if provider == "eodhd":
        return EODHDCollector(api_key=api_key, transport=transport, rate_limiter=limiter,
                              sleep=_no_sleep)
    if provider == "binance":
        return BinanceCollector(transport=transport, rate_limiter=limiter, sleep=_no_sleep)
    raise ValueError(f"no collector for provider {provider!r}")


def load_universe(path):
    return _universe.load_universe(path)


def select_legs(universe, assets=None, providers=None):
    return _sync.select_legs(universe, assets=assets, providers=providers)


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
    doc, rc = health.status_document(
        universe, store_path, assets=assets, providers=providers, now=now, window=window,
        jump_threshold=jump_threshold, staleness_k=staleness_k,
        resolution_window=resolution_window, resolution_k=resolution_k, flat_k=flat_k,
        gap_k=gap_k, spread_threshold=spread_threshold, spread_alerts=spread_alerts)
    return json.loads(json.dumps(doc, indent=1)), rc


def export_frame(store_path, exchange, symbol):
    return _store.export_frame(_store.ParquetStore(store_path), exchange, symbol)


def stored_frame(store_path, exchange, symbol):
    return _store.ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path, symbol):
    actions = CorporateActionsStore(store_path)
    return {"splits": actions.raw_items("splits", symbol),
            "dividends": actions.raw_items("dividends", symbol),
            "last_updated": actions.stamp_text(symbol)}


def import_csv(store_path, csv_path, exchange, symbol, asset_type, currency="USD"):
    return _store.ParquetStore(store_path).ingest_yahoo_csv(csv_path, exchange, symbol,
                                                            asset_type, currency)
