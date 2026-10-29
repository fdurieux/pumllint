"""Harness adapter: maps the fixed harness interface onto jef_data_rc."""
import json

from jef_data_rc.actions import CorporateActionsStore
from jef_data_rc.collectors.binance import BinanceCollector
from jef_data_rc.collectors.eodhd import EODHDCollector
from jef_data_rc.collectors.transport import ReplayTransport
from jef_data_rc.health import status_document
from jef_data_rc.store import ParquetStore, seam_frame
from jef_data_rc.sync import run_sync as _run_sync
from jef_data_rc.sync import select_legs as _select_legs
from jef_data_rc.sync import sync_summary as _sync_summary
from jef_data_rc.universe import load_universe as _load_universe


def _no_sleep(seconds):
    return None


def make_collector(provider, fixture_dir, api_key="test-key-not-real"):
    transport = ReplayTransport(fixture_dir)
    if provider == "eodhd":
        return EODHDCollector(api_key=api_key, transport=transport, sleep=_no_sleep,
                              rate_limit=False)
    if provider == "binance":
        return BinanceCollector(transport=transport, sleep=_no_sleep, rate_limit=False)
    raise ValueError(f"unknown provider {provider!r}")


def load_universe(path):
    return _load_universe(path)


def select_legs(universe, assets=None, providers=None):
    return _select_legs(universe, assets, providers)


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False, tail=10,
             force_actions=False, now=None, collectors=None, out=None):
    return _run_sync(universe, store_path, assets=assets, providers=providers, dry_run=dry_run,
                     tail=tail, force_actions=force_actions, now=now, collectors=collectors,
                     out=out)


def sync_summary(results, ok):
    return _sync_summary(results, ok)


def status_json(universe, store_path, *, assets=None, providers=None, now=None, window=10,
                jump_threshold=0.40, staleness_k=2, resolution_window=500, resolution_k=0.20,
                flat_k=0.25, gap_k=5, spread_threshold=0.005, spread_alerts=False):
    doc = status_document(universe, store_path, assets=assets, providers=providers, now=now,
                          window=window, jump_threshold=jump_threshold, staleness_k=staleness_k,
                          resolution_window=resolution_window, resolution_k=resolution_k,
                          flat_k=flat_k, gap_k=gap_k, spread_threshold=spread_threshold,
                          spread_alerts=spread_alerts)
    parsed = json.loads(json.dumps(doc, indent=1))
    return parsed, 1 if parsed["alerts_total"] > 0 else 0


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
