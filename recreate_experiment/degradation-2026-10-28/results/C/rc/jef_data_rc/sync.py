"""The universe's acquisition ritual: leg selection, windows, actions gate, reconcile."""
from datetime import datetime, timedelta, timezone

from jef_data_rc.actions import CorporateActionsStore, sync_actions
from jef_data_rc.adjust import resolve_price_basis
from jef_data_rc.collectors import VOLUME_BASIS
from jef_data_rc.store import ParquetStore
from jef_data_rc.universe import PROVIDERS

DEFAULT_TAIL = 10
REVISIONS_ECHOED = 10


class SyncError(RuntimeError):
    """A selection or run parameter the sync refuses."""


def select_legs(universe, assets=None, providers=None):
    """Every enabled asset x enabled source, filtered, in universe order."""
    names = [asset["name"] for asset in universe["assets"]]
    for name in assets or []:
        if name not in names:
            raise SyncError(f"unknown asset {name!r}; universe has {sorted(names)}")
    for provider in providers or []:
        if provider not in PROVIDERS:
            raise SyncError(f"unknown provider {provider!r}; allowed: {PROVIDERS}")
    legs = []
    for asset in universe["assets"]:
        if not asset["enabled"]:
            continue
        if assets and asset["name"] not in assets:
            continue
        for source in asset["sources"]:
            if not source["enabled"]:
                continue
            if providers and source["provider"] not in providers:
                continue
            legs.append({
                "asset": asset["name"],
                "provider": source["provider"],
                "exchange": source["exchange"],
                "symbol": source["symbol"],
                "path": source.get("path"),
                "asset_type": asset["asset_type"],
                "currency": asset["currency"],
                "start": source.get("start"),
                "end": source.get("end"),
                "actions": source["provider"] == "eodhd" and asset["asset_type"] != "crypto",
            })
    if not legs:
        raise SyncError("selection matched no enabled asset/source legs")
    return legs


def utc_today(now=None):
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).date()


def fetch_end(leg, today):
    """The earlier of the universe end and, for a declared crypto, the end-guard."""
    candidates = []
    if leg["end"]:
        candidates.append(leg["end"])
    if leg["asset_type"] == "crypto":
        candidates.append((today - timedelta(days=1)).isoformat())
    return min(candidates) if candidates else None


def plan_line(leg, store, tail, today):
    asset = f"{leg['asset']:>6}"
    where = f"{leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{asset} {where}: import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    end = fetch_end(leg, today)
    if recent:
        start = recent[0].isoformat()
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif leg["start"]:
        start = leg["start"]
        window = f"first fill from {start}"
    else:
        start = None
        window = "first fill, full history"
    if end:
        window += f" to {end}"
    if recent and end and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{asset} {where}: {action} ({window})"


class _Collectors:
    """Constructs each provider's collector at most once per run."""

    def __init__(self, injected, base_url):
        self.injected = dict(injected or {})
        self.base_url = base_url
        self.built = {}
        self.failed = {}

    def get(self, provider):
        if provider in self.injected:
            return self.injected[provider]
        if provider in self.built:
            return self.built[provider]
        if provider in self.failed:
            raise self.failed[provider]
        try:
            if provider == "eodhd":
                from jef_data_rc.collectors.eodhd import DEFAULT_BASE_URL, EODHDCollector
                collector = EODHDCollector(base_url=self.base_url or DEFAULT_BASE_URL)
            elif provider == "binance":
                from jef_data_rc.collectors.binance import BinanceCollector
                collector = BinanceCollector()
            else:
                raise SyncError(f"no collector for provider {provider!r}")
        except Exception as exc:
            self.failed[provider] = exc
            raise
        self.built[provider] = collector
        return collector

    def close(self):
        for collector in self.built.values():
            collector.close()


def _volume_basis(provider, collectors):
    collector = collectors.injected.get(provider) or collectors.built.get(provider)
    if collector is not None:
        return collector.volume_basis
    return VOLUME_BASIS[provider]


def run_collector_leg(leg, collectors, store, actions_store, tail, today, force_actions):
    """One eodhd/binance leg; returns (detail, revisions)."""
    exchange, symbol = leg["exchange"], leg["symbol"]
    parts = []
    splits = []
    if leg["actions"]:
        stamp = actions_store.last_updated(symbol)
        if force_actions or stamp is None or stamp.date() < today:
            count_splits, count_dividends = sync_actions(collectors.get("eodhd"), actions_store, symbol)
            parts.append(f"{count_splits} split(s), {count_dividends} dividend(s); ")
        else:
            parts.append("actions fresh; ")
        splits = actions_store.load_splits(symbol)
    recent = store.recent_dates(exchange, symbol, tail)
    has_rows = bool(recent)
    start = recent[0].isoformat() if has_rows else leg["start"]
    end = fetch_end(leg, today)
    if has_rows and end and start > end:
        bars = []
        parts.append(f"end {end} predates the stored tail (from {start}); nothing fetched - "
                     f"a pinned window with rows past its end, the fix is the declaration; ")
    else:
        collector = collectors.get(leg["provider"])
        bars = collector.get_eod(symbol, start, end)
        limit = getattr(collector, "limit", None)
        if not has_rows and not leg["start"] and limit is not None and len(bars) == limit:
            parts.append(f"first fill hit the provider page limit ({len(bars)} bars, no start "
                         f"declared) - the series is a trailing window, not history; ")
    basis = resolve_price_basis(leg["provider"], leg["asset_type"])
    count, revisions = store.reconcile_bars(
        exchange, symbol, bars, splits, basis, _volume_basis(leg["provider"], collectors),
        asset_type=leg["asset_type"], currency=leg["currency"])
    if basis == "raw" and store.has_rows(exchange, symbol):
        store.reapply_adjustment(exchange, symbol, splits)
    detail = "".join(parts) + f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and str(bars[-1]["date"])[:10] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def run_csv_leg(leg, store):
    rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                  leg["asset_type"], leg["currency"])
    return f"{rows} row(s) imported", []


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False,
             tail=DEFAULT_TAIL, force_actions=False, base_url=None, now=None, collectors=None,
             out=None):
    """Run every selected leg; returns (results, ok)."""
    emit = out if out is not None else (lambda line: None)
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    today = utc_today(now)
    legs = select_legs(universe, assets, providers)
    store = ParquetStore(store_path)
    actions_store = CorporateActionsStore(store_path)

    if dry_run:
        emit(f"plan for store {store_path!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_line(leg, store, tail, today))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True

    pool = _Collectors(collectors, base_url)
    results = []
    try:
        for leg in legs:
            try:
                if leg["provider"] == "yahoo-csv":
                    detail, revisions = run_csv_leg(leg, store)
                else:
                    detail, revisions = run_collector_leg(leg, pool, store, actions_store,
                                                          tail, today, force_actions)
                ok = True
            except Exception as exc:
                detail, revisions, ok = f"{type(exc).__name__}: {exc}", [], False
            results.append(dict(leg, ok=ok, detail=detail, revisions=revisions))
            where = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            if ok:
                emit(f"ok      {where}: {detail}")
                for revision in revisions[:REVISIONS_ECHOED]:
                    emit(f"        revised {revision['date']} {revision['column']}: "
                         f"{revision['stored']:g} -> {revision['served']:g}")
                more = len(revisions) - REVISIONS_ECHOED
                if more > 0:
                    emit(f"        ... {more} more revised cell(s)")
            else:
                emit(f"FAILED  {where}: {detail}")
    finally:
        pool.close()
    failed = sum(1 for result in results if not result["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_path!r}")
    return results, failed == 0


def sync_summary(results, ok):
    """The --summary-json document: two renderings of one set of facts."""
    legs = []
    for result in results:
        revisions = [{"date": r["date"], "column": r["column"], "stored": float(r["stored"]),
                      "served": float(r["served"])} for r in result.get("revisions", [])]
        legs.append({"asset": result["asset"], "provider": result["provider"],
                     "exchange": result["exchange"], "symbol": result["symbol"],
                     "ok": result["ok"], "detail": result["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": 1, "legs_total": len(results),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": sum(leg["revised_cells"] for leg in legs),
            "ok": bool(ok), "legs": legs}
