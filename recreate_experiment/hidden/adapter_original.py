"""The subject's adapter: the fixed harness interface mapped onto jef.data.

Glue only - every computation happens inside the subject.
"""
from jef.data import universe as _universe
from jef.data import sync as _sync


class _NoLimit:
    """A rate limiter that never limits (the interface: no rate limiting)."""

    def acquire(self):
        return None


def _no_sleep(_seconds):
    return None


def make_collector(provider, fixture_dir, api_key="test-key-not-real"):
    from jef.data.collectors.base import ReplayTransport

    transport = ReplayTransport(fixture_dir)
    if provider == "eodhd":
        from jef.data.collectors.eodhd import EODHDCollector

        return EODHDCollector(api_key=api_key, transport=transport,
                              rate_limiter=_NoLimit(), sleep=_no_sleep)
    if provider == "binance":
        from jef.data.collectors.binance import BinanceCollector

        return BinanceCollector(transport=transport, rate_limiter=_NoLimit(),
                                sleep=_no_sleep)
    raise ValueError(f"unknown provider {provider!r}")


def load_universe(path):
    return _universe.load_universe(path)


def select_legs(universe, assets=None, providers=None):
    return _sync.select_legs(universe, assets=assets, providers=providers)


def run_sync(universe, store_path, *, assets=None, providers=None,
             dry_run=False, tail=10, force_actions=False, now=None,
             collectors=None, out=None):
    collectors = collectors or {}
    return _sync.run_sync(
        universe, store_path=store_path, assets=assets, providers=providers,
        dry_run=dry_run, eodhd_collector=collectors.get("eodhd"),
        binance_collector=collectors.get("binance"),
        out=out if out is not None else (lambda _line: None),
        tail=tail, force_actions=force_actions, now=now)


def sync_summary(results, ok):
    return _sync.sync_summary(results, ok)


def status_json(universe, store_path, *, assets=None, providers=None,
                now=None, window=10, jump_threshold=0.40, staleness_k=2,
                resolution_window=500, resolution_k=0.20, flat_k=0.25,
                gap_k=5, spread_threshold=0.005, spread_alerts=False):
    """Run the subject's own `status --json` command in-process: the given
    universe object stands in for the file it would load, and `now` stands
    in for the health module's clock. Glue only."""
    import contextlib
    import io
    import json
    from datetime import datetime
    from unittest import mock

    from jef.data import cli, health

    argv = ["status", "--json", "--store", str(store_path),
            "--window", str(window), "--jump-threshold", repr(float(jump_threshold)),
            "--staleness", str(staleness_k),
            "--resolution-window", str(resolution_window),
            "--resolution-k", repr(float(resolution_k)), "--flat-k", repr(float(flat_k)),
            "--gap-k", str(gap_k), "--spread-threshold", repr(float(spread_threshold))]
    for name in assets or ():
        argv += ["--asset", name]
    for name in providers or ():
        argv += ["--provider", name]
    if spread_alerts:
        argv.append("--spread-alerts")

    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz is None else now.astimezone(tz)

    buffer = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("jef.data.universe.load_universe",
                                       lambda path=None: universe))
        if now is not None:
            stack.enter_context(mock.patch.object(health, "datetime", _Clock))
        stack.enter_context(contextlib.redirect_stdout(buffer))
        rc = cli.main(argv)
    return json.loads(buffer.getvalue()), rc


def export_frame(store_path, exchange, symbol):
    from jef.data.store import ParquetStore, to_contract_frame

    return to_contract_frame(ParquetStore(store_path).load(exchange, symbol))


def stored_frame(store_path, exchange, symbol):
    from jef.data.store import ParquetStore

    return ParquetStore(store_path).load(exchange, symbol)


def actions_state(store_path, symbol):
    import json
    import os

    from jef.data.actions import CorporateActionsStore

    store = CorporateActionsStore(store_path)
    state = {"splits": [], "dividends": [], "last_updated": None}
    for kind in ("splits", "dividends"):
        path = store._path(kind, symbol)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
            state[kind] = doc[kind]
            if kind == "splits":
                state["last_updated"] = doc["last_updated"]
    return state


def import_csv(store_path, csv_path, exchange, symbol, asset_type,
               currency="USD"):
    from jef.data.store import ParquetStore

    return ParquetStore(store_path).ingest_yahoo_csv(
        csv_path, exchange, symbol, asset_type=asset_type, currency=currency)
