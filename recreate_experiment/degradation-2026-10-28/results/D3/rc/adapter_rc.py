"""Harness adapter: the fixed harness interface mapped onto jef_data_rc."""
from __future__ import annotations

from jef_data_rc import health
from jef_data_rc import sync as _sync
from jef_data_rc.actions import CorporateActionsStore
from jef_data_rc.collectors.base import ReplayTransport
from jef_data_rc.collectors.binance import BinanceCollector
from jef_data_rc.collectors.eodhd import EODHDCollector
from jef_data_rc.store import ParquetStore
from jef_data_rc.store import export_frame as _export_frame
from jef_data_rc.universe import load_universe as _load_universe


def _no_sleep(seconds):
    return None


def make_collector(provider: str, fixture_dir: str, api_key: str = "test-key-not-real"):
    transport = ReplayTransport(fixture_dir)
    if provider == "eodhd":
        return EODHDCollector(api_key=api_key, transport=transport, rate_limit=False, sleep=_no_sleep)
    if provider == "binance":
        return BinanceCollector(transport=transport, rate_limit=False, sleep=_no_sleep)
    raise ValueError(f"no collector for provider {provider!r}")


def load_universe(path):
    return _load_universe(path)


def select_legs(universe, assets=None, providers=None):
    return _sync.select_legs(universe, assets, providers)


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False, tail=10,
             force_actions=False, now=None, collectors=None, out=None):
    return _sync.run_sync(universe, store_path, assets=assets, providers=providers,
                          dry_run=dry_run, tail=tail, force_actions=force_actions, now=now,
                          collectors=collectors, out=out)


def sync_summary(results, ok):
    return _sync.summary(results, ok)


def status_json(universe, store_path, *, assets=None, providers=None, now=None, window=10,
                jump_threshold=0.40, staleness_k=2, resolution_window=500, resolution_k=0.20,
                flat_k=0.25, gap_k=5, spread_threshold=0.005, spread_alerts=False):
    doc = health.run_status(universe, store_path, assets=assets, providers=providers, now=now,
                            window=window, jump_threshold=jump_threshold, staleness_k=staleness_k,
                            resolution_window=resolution_window, resolution_k=resolution_k,
                            flat_k=flat_k, gap_k=gap_k, spread_threshold=spread_threshold,
                            spread_alerts=spread_alerts)
    return doc, health.exit_code(doc)


def export_frame(store_path, exchange, symbol):
    return _export_frame(store_path, exchange, symbol)


def stored_frame(store_path, exchange, symbol):
    return ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path, symbol):
    actions = CorporateActionsStore(store_path)
    return {"splits": actions.raw_splits(symbol), "dividends": actions.load_dividends(symbol),
            "last_updated": actions.stamp_text(symbol)}


def import_csv(store_path, csv_path, exchange, symbol, asset_type, currency="USD"):
    return ParquetStore(store_path).ingest_yahoo_csv(csv_path, exchange, symbol, asset_type, currency)
