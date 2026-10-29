"""The sync ritual: leg selection, per-leg acquisition, the run log and summary."""
from __future__ import annotations

from datetime import datetime, timezone

from .actions import CorporateActionsStore, sync_actions
from .store import ParquetStore, resolve_price_basis
from .universe import PROVIDERS

DEFAULT_TAIL = 10
REVISION_ECHO = 10


class SyncError(RuntimeError):
    """A selection or argument the sync refuses."""


def select_legs(universe: dict, assets=None, providers=None) -> list[dict]:
    """Every enabled asset x enabled source, in universe order, filtered."""
    names = [a["name"] for a in universe["assets"]]
    for name in assets or []:
        if name not in names:
            raise SyncError(f"unknown asset {name!r}; universe has {sorted(names)}")
    for provider in providers or []:
        if provider not in PROVIDERS:
            raise SyncError(f"unknown provider {provider!r}; allowed: {list(PROVIDERS)}")
    legs = []
    for asset in universe["assets"]:
        if not asset["enabled"] or (assets and asset["name"] not in assets):
            continue
        for src in asset["sources"]:
            if not src["enabled"] or (providers and src["provider"] not in providers):
                continue
            provider = src["provider"]
            collector_source = provider != "yahoo-csv"
            legs.append({
                "asset": asset["name"],
                "provider": provider,
                "exchange": src["exchange"],
                "symbol": src["symbol"],
                "path": None if collector_source else src["path"],
                "asset_type": asset["asset_type"],
                "currency": src.get("currency", asset["currency"]),
                "start": src.get("start") if collector_source else None,
                "end": src.get("end") if collector_source else None,
                "actions": provider == "eodhd" and asset["asset_type"] != "crypto",
            })
    if not legs:
        raise SyncError("selection matched no enabled asset/source legs")
    return legs


def _today(now) -> "date":
    clock = now if now is not None else datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    return clock.astimezone(timezone.utc).date()


def plan_line(leg: dict, store: ParquetStore, tail: int) -> str:
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{head}: import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    end = leg["end"]
    if recent:
        start = recent[0].isoformat()
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif leg["start"] is not None:
        start = leg["start"]
        window = f"first fill from {start}"
    else:
        start = None
        window = "first fill, full history"
    if end is not None:
        window += f" to {end}"
    if recent and end is not None and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{head}: {action} ({window})"


class _Collectors:
    """Lazily built collectors, at most one per provider per run."""

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
                from .collectors.eodhd import EODHDCollector

                collector = EODHDCollector(base_url=self.base_url)
            elif provider == "binance":
                from .collectors.binance import BinanceCollector

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


def _run_collector_leg(leg, collector, store, actions, tail, today, force_actions):
    exchange, symbol = leg["exchange"], leg["symbol"]
    basis = resolve_price_basis(leg["provider"], leg["asset_type"])
    parts = []
    splits = []
    if leg["actions"]:
        stamp = actions.last_updated(symbol)
        if force_actions or stamp is None or stamp.astimezone(timezone.utc).date() < today:
            n_splits, n_dividends = sync_actions(collector, actions, symbol)
            parts.append(f"{n_splits} split(s), {n_dividends} dividend(s); ")
        else:
            parts.append("actions fresh; ")
        splits = actions.load_splits(symbol)
    recent = store.recent_dates(exchange, symbol, tail)
    filled = bool(recent)
    start = recent[0].isoformat() if filled else leg["start"]
    end = leg["end"]
    if filled and end is not None and start > end:
        bars = []
        parts.append(f"end {end} predates the stored tail (from {start}); nothing fetched - "
                     "a pinned window with rows past its end, the fix is the declaration; ")
    else:
        bars = collector.get_eod(symbol, start, end)
        limit = getattr(collector, "limit", None)
        if not filled and leg["start"] is None and limit is not None and len(bars) == limit:
            parts.append(f"first fill hit the provider page limit ({len(bars)} bars, no start "
                         "declared) - the series is a trailing window, not history; ")
    count, revisions = store.reconcile_bars(
        exchange, symbol, bars, splits, basis, collector.volume_basis,
        asset_type=leg["asset_type"], currency=leg["currency"])
    if basis == "raw" and store.has_rows(exchange, symbol):
        store.reapply_adjustment(exchange, symbol, splits)
    detail = "".join(parts) + f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and str(bars[-1]["date"])[:10] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False,
             tail=DEFAULT_TAIL, force_actions=False, now=None, collectors=None, out=None,
             base_url=None):
    """Run every selected leg; returns (results, ok)."""
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    legs = select_legs(universe, assets, providers)
    today = _today(now)
    emit = out if out is not None else (lambda line: None)
    store_path = str(store_path)
    store = ParquetStore(store_path)
    actions = CorporateActionsStore(store_path)

    if dry_run:
        emit(f"plan for store {store_path!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_line(leg, store, tail))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True

    pool = _Collectors(collectors, base_url)
    results = []
    try:
        for leg in legs:
            try:
                if leg["provider"] == "yahoo-csv":
                    rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                                  leg["asset_type"], leg["currency"])
                    detail, revisions = f"{rows} row(s) imported", []
                else:
                    collector = pool.get(leg["provider"])
                    detail, revisions = _run_collector_leg(leg, collector, store, actions,
                                                           tail, today, force_actions)
                result = dict(leg, ok=True, detail=detail, revisions=revisions)
            except Exception as exc:  # a failed leg never stops the others
                result = dict(leg, ok=False, detail=f"{type(exc).__name__}: {exc}", revisions=[])
            results.append(result)
            head = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            if result["ok"]:
                emit(f"ok      {head}: {result['detail']}")
                for rev in result["revisions"][:REVISION_ECHO]:
                    emit(f"        revised {rev['date']} {rev['column']}: "
                         f"{rev['stored']:g} -> {rev['served']:g}")
                more = len(result["revisions"]) - REVISION_ECHO
                if more > 0:
                    emit(f"        ... {more} more revised cell(s)")
            else:
                emit(f"FAILED  {head}: {result['detail']}")
    finally:
        pool.close()
    failed = sum(1 for r in results if not r["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_path!r}")
    return results, failed == 0


def sync_summary(results, ok) -> dict:
    legs = []
    for result in results:
        revisions = [{"date": r["date"], "column": r["column"], "stored": float(r["stored"]),
                      "served": float(r["served"])} for r in result.get("revisions", [])]
        legs.append({"asset": result["asset"], "provider": result["provider"],
                     "exchange": result["exchange"], "symbol": result["symbol"],
                     "ok": bool(result["ok"]), "detail": result["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": 1, "legs_total": len(legs),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": sum(leg["revised_cells"] for leg in legs),
            "ok": bool(ok), "legs": legs}
