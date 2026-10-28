"""Harness adapter for jef_data_rc.

Glue only: each function maps the harness's fixed interface onto the
package's own API and computes nothing itself. Store-touching modules are
imported inside the functions that need them.
"""
from __future__ import annotations


def _no_sleep(_seconds) -> None:
    return None


def _discard(_line) -> None:
    return None


def make_collector(provider: str, fixture_dir: str, api_key: str = "test-key-not-real"):
    from jef_data_rc.collectors.base import RateLimiter, ReplayTransport

    transport = ReplayTransport(fixture_dir)
    limiter = RateLimiter(per_minute=10**12, daily_budget=10**15, sleep=_no_sleep)
    if provider == "eodhd":
        from jef_data_rc.collectors.eodhd import EODHDCollector

        return EODHDCollector(
            api_key=api_key, transport=transport, rate_limiter=limiter, sleep=_no_sleep
        )
    if provider == "binance":
        from jef_data_rc.collectors.binance import BinanceCollector

        return BinanceCollector(transport=transport, rate_limiter=limiter, sleep=_no_sleep)
    raise ValueError(f"unknown provider {provider!r}")


def load_universe(path=None):
    from jef_data_rc.universe import load_universe as _load

    return _load(path)


def select_legs(universe, assets=None, providers=None):
    from jef_data_rc.sync import select_legs as _select

    return _select(universe, assets, providers)


def run_sync(
    universe,
    store_path,
    *,
    assets=None,
    providers=None,
    dry_run=False,
    tail=10,
    force_actions=False,
    now=None,
    collectors=None,
    out=None,
):
    from jef_data_rc.sync import run_sync as _run

    collectors = collectors or {}
    return _run(
        universe,
        store=store_path,
        assets=assets,
        providers=providers,
        tail=tail,
        force_actions=force_actions,
        dry_run=dry_run,
        eodhd_collector=collectors.get("eodhd"),
        binance_collector=collectors.get("binance"),
        now=now,
        out=out if out is not None else _discard,
    )


def sync_summary(results, ok):
    from jef_data_rc.sync import sync_summary as _summary

    return _summary(results, ok)


def status_json(
    universe,
    store_path,
    *,
    assets=None,
    providers=None,
    now=None,
    window=10,
    jump_threshold=0.40,
    staleness_k=2,
    resolution_window=500,
    resolution_k=0.20,
    flat_k=0.25,
    gap_k=5,
    spread_threshold=0.005,
    spread_alerts=False,
):
    from jef_data_rc.health import evaluate_status

    return evaluate_status(
        universe,
        store_path,
        assets=assets,
        providers=providers,
        now=now,
        window=window,
        jump_threshold=jump_threshold,
        staleness_k=staleness_k,
        resolution_window=resolution_window,
        resolution_k=resolution_k,
        flat_k=flat_k,
        gap_k=gap_k,
        spread_threshold=spread_threshold,
        spread_alerts=spread_alerts,
    )


def export_frame(store_path, exchange, symbol):
    from jef_data_rc.store import ParquetStore

    return ParquetStore(store_path).to_contract_frame(exchange, symbol)


def stored_frame(store_path, exchange, symbol):
    from jef_data_rc.store import ParquetStore

    return ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path, symbol):
    from jef_data_rc.actions import read_document

    splits = read_document(store_path, "splits", symbol) or {}
    dividends = read_document(store_path, "dividends", symbol) or {}
    return {
        "splits": list(splits.get("splits", [])),
        "dividends": list(dividends.get("dividends", [])),
        "last_updated": splits.get("last_updated"),
    }


def import_csv(store_path, csv_path, exchange, symbol, asset_type, currency="USD"):
    from jef_data_rc.store import ParquetStore

    return ParquetStore(store_path).ingest_yahoo_csv(
        csv_path,
        exchange=exchange,
        symbol=symbol,
        asset_type=asset_type,
        currency=currency,
    )
