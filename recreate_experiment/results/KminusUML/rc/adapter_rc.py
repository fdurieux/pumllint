"""Harness adapter: maps the fixed harness interface onto jef_data_rc."""
import json

from jef_data_rc import actions, collectors, seam, status, store, sync, universe


def make_collector(provider, fixture_dir, api_key="test-key-not-real"):
    transport = collectors.ReplayTransport(fixture_dir)
    no_sleep = lambda seconds: None  # noqa: E731
    if provider == "eodhd":
        return collectors.EODHDCollector(api_key=api_key, transport=transport,
                                         rate_limit=False, sleep=no_sleep)
    if provider == "binance":
        return collectors.BinanceCollector(transport=transport, rate_limit=False,
                                           sleep=no_sleep)
    raise ValueError(f"unknown provider {provider!r}")


def load_universe(path):
    return universe.load_universe(path)


def select_legs(universe_doc, assets=None, providers=None):
    return sync.select_legs(universe_doc, assets, providers)


def run_sync(universe_doc, store_path, *, assets=None, providers=None, dry_run=False,
             tail=10, force_actions=False, now=None, collectors=None, out=None):
    return sync.run_sync(universe_doc, store_path, assets=assets, providers=providers,
                         dry_run=dry_run, tail=tail, force_actions=force_actions, now=now,
                         collectors=collectors, out=out)


def sync_summary(results, ok):
    return sync.summary(results, ok)


def status_json(universe_doc, store_path, *, assets=None, providers=None, now=None,
                window=10, jump_threshold=0.40, staleness_k=2, resolution_window=500,
                resolution_k=0.20, flat_k=0.25, gap_k=5, spread_threshold=0.005,
                spread_alerts=False):
    doc, rc = status.run_status(
        universe_doc, store_path, assets=assets, providers=providers, now=now,
        window=window, jump_threshold=jump_threshold, staleness_k=staleness_k,
        resolution_window=resolution_window, resolution_k=resolution_k, flat_k=flat_k,
        gap_k=gap_k, spread_threshold=spread_threshold, spread_alerts=spread_alerts)
    return json.loads(json.dumps(doc, indent=1)), rc


def export_frame(store_path, exchange, symbol):
    return seam.export_frame(store_path, exchange, symbol)


def stored_frame(store_path, exchange, symbol):
    return store.read_series(store_path, exchange, symbol)


def actions_state(store_path, symbol):
    return actions.state(store_path, symbol)


def import_csv(store_path, csv_path, exchange, symbol, asset_type, currency="USD"):
    return store.overwrite_csv(store_path, csv_path, exchange, symbol, asset_type, currency)
