"""Harness adapter: maps the fixed harness interface onto jef_data_rc.

Glue only; every result comes from the package's own API.
"""

from __future__ import annotations

from jef_data_rc.actions import ActionsStore
from jef_data_rc.collectors.base import RateLimiter, ReplayTransport
from jef_data_rc.health import build_status
from jef_data_rc.store import ParquetStore
from jef_data_rc.sync import run_sync as _run_sync
from jef_data_rc.sync import select_legs as _select_legs
from jef_data_rc.sync import sync_summary as _sync_summary
from jef_data_rc.universe import load_universe as _load_universe

_UNLIMITED = 10 ** 15


def _no_sleep(_seconds: float) -> None:
    return None


def make_collector(provider: str, fixture_dir: str, api_key: str = "test-key-not-real") -> object:
    transport = ReplayTransport(fixture_dir)
    limiter = RateLimiter(per_minute=_UNLIMITED, daily_budget=_UNLIMITED, sleep=_no_sleep)
    if provider == "eodhd":
        from jef_data_rc.collectors.eodhd import EODHDCollector

        return EODHDCollector(api_key=api_key, transport=transport, rate_limiter=limiter, sleep=_no_sleep)
    if provider == "binance":
        from jef_data_rc.collectors.binance import BinanceCollector

        return BinanceCollector(transport=transport, rate_limiter=limiter, sleep=_no_sleep)
    raise ValueError(f"unknown provider {provider!r}")


def load_universe(path: str | None) -> object:
    return _load_universe(path)


def select_legs(universe, assets=None, providers=None) -> list[dict]:
    return _select_legs(universe, assets, providers)


def run_sync(universe, store_path: str, *, assets=None, providers=None, dry_run=False, tail=10,
             force_actions=False, now=None, collectors=None, out=None) -> tuple[list, bool]:
    collectors = collectors or {}
    return _run_sync(
        universe, store_path, assets=assets, providers=providers, dry_run=dry_run, tail=tail,
        force_actions=force_actions, now=now, eodhd_collector=collectors.get("eodhd"),
        binance_collector=collectors.get("binance"), out=out,
    )


def sync_summary(results, ok) -> dict:
    return _sync_summary(results, ok)


def status_json(universe, store_path: str, *, assets=None, providers=None, now=None, window=10,
                jump_threshold=0.40, staleness_k=2, resolution_window=500, resolution_k=0.20,
                flat_k=0.25, gap_k=5, spread_threshold=0.005, spread_alerts=False) -> tuple[dict, int]:
    return build_status(
        universe, store_path, assets=assets, providers=providers, now=now, window=window,
        jump_threshold=jump_threshold, staleness_k=staleness_k, resolution_window=resolution_window,
        resolution_k=resolution_k, flat_k=flat_k, gap_k=gap_k, spread_threshold=spread_threshold,
        spread_alerts=spread_alerts,
    )


def export_frame(store_path: str, exchange: str, symbol: str):
    return ParquetStore(store_path).to_contract_frame(exchange, symbol)


def stored_frame(store_path: str, exchange: str, symbol: str):
    return ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path: str, symbol: str) -> dict:
    actions = ActionsStore(store_path)
    return {
        "splits": actions.split_entries(symbol),
        "dividends": actions.load_dividends(symbol),
        "last_updated": actions.last_updated(symbol),
    }


def import_csv(store_path: str, csv_path: str, exchange: str, symbol: str, asset_type: str,
               currency: str = "USD") -> int:
    return ParquetStore(store_path).ingest_yahoo_csv(
        csv_path, symbol=symbol, exchange=exchange, asset_type=asset_type, currency=currency,
    )
