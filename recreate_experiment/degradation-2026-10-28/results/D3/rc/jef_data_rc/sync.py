"""The sync ritual: legs from the universe, per-leg acquisition, the run log and summary."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .actions import CorporateActionsStore, sync_actions
from .store import ParquetStore
from .universe import PROVIDERS

REVISION_ECHO = 10
DEFAULT_TAIL = 10


class SyncError(RuntimeError):
    """A selection or run parameter that matches no work."""


def select_legs(universe: dict, assets=None, providers=None) -> list:
    names = [a["name"] for a in universe["assets"]]
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


def resolve_basis(provider: str, asset_type: str) -> str:
    if provider == "eodhd" and asset_type != "crypto":
        return "raw"
    return "split_adjusted"


def fetch_end(leg: dict, today) -> str | None:
    end = leg["end"]
    if leg["asset_type"] == "crypto":
        guard = (today - timedelta(days=1)).isoformat()
        end = guard if end is None else min(end, guard)
    return end


def plan_line(leg: dict, store: ParquetStore, tail: int, today) -> str:
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{head}: import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    if recent:
        start = recent[0].isoformat()
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif leg["start"]:
        start = leg["start"]
        window = f"first fill from {start}"
    else:
        start = None
        window = "first fill, full history"
    end = fetch_end(leg, today)
    if end:
        window += f" to {end}"
    if recent and end and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{head}: {action} ({window})"


class _Collectors:
    """Builds each provider's collector once, on first need."""

    def __init__(self, injected=None, base_url=None):
        self.injected = dict(injected or {})
        self.base_url = base_url
        self.built: dict = {}

    def get(self, provider: str):
        if provider in self.injected:
            return self.injected[provider]
        if provider not in self.built:
            if provider == "eodhd":
                from .collectors.eodhd import EODHDCollector

                self.built[provider] = EODHDCollector(base_url=self.base_url)
            else:
                from .collectors.binance import BinanceCollector

                self.built[provider] = BinanceCollector()
        return self.built[provider]

    def close(self) -> None:
        for collector in self.built.values():
            collector.close()


def _run_collector_leg(leg, store, actions, collectors, tail, today, force_actions):
    exchange, symbol = leg["exchange"], leg["symbol"]
    collector = collectors.get(leg["provider"])
    recent = store.recent_dates(exchange, symbol, tail)
    start = recent[0].isoformat() if recent else leg["start"]
    end = fetch_end(leg, today)
    detail = ""
    splits = []
    if leg["actions"]:
        stamp = actions.last_updated(symbol)
        if force_actions or stamp is None or _utc_date(stamp) < today:
            n_splits, n_divs = sync_actions(collector, actions, symbol)
            detail += f"{n_splits} split(s), {n_divs} dividend(s); "
        else:
            detail += "actions fresh; "
        splits = actions.load_splits(symbol)
    if recent and end is not None and start > end:
        bars = []
        detail += (f"end {end} predates the stored tail (from {start}); nothing fetched - a pinned "
                   f"window with rows past its end, the fix is the declaration; ")
    else:
        bars = collector.get_eod(symbol, start, end)
    limit = getattr(collector, "limit", None)
    if not recent and leg["start"] is None and limit is not None and len(bars) == limit:
        detail += (f"first fill hit the provider page limit ({len(bars)} bars, no start declared) - "
                   f"the series is a trailing window, not history; ")
    basis = resolve_basis(leg["provider"], leg["asset_type"])
    count, revisions = store.reconcile_bars(
        exchange, symbol, bars, splits, basis, collector.volume_basis,
        asset_type=leg["asset_type"], currency=leg["currency"])
    if basis == "raw" and store.latest_date(exchange, symbol) is not None:
        store.reapply_adjustment(exchange, symbol, splits)
    detail += f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and bars[-1].get("date") == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def _utc_date(stamp: datetime):
    if stamp.tzinfo is None:
        return stamp.date()
    return stamp.astimezone(timezone.utc).date()


def _today(now):
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.date()
    return now.astimezone(timezone.utc).date()


def run_sync(universe: dict, store_path, *, assets=None, providers=None, dry_run: bool = False,
             tail: int = DEFAULT_TAIL, force_actions: bool = False, now=None, collectors=None,
             base_url=None, out=None) -> tuple:
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    emit = out if out is not None else (lambda line: None)
    today = _today(now)
    legs = select_legs(universe, assets, providers)
    store = ParquetStore(store_path)
    if dry_run:
        emit(f"plan for store {store_path!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_line(leg, store, tail, today))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True

    actions = CorporateActionsStore(store_path)
    pool = _Collectors(collectors, base_url)
    results = []
    try:
        for leg in legs:
            head = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            try:
                if leg["provider"] == "yahoo-csv":
                    rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                                  leg["asset_type"], leg["currency"])
                    detail, revisions = f"{rows} row(s) imported", []
                else:
                    detail, revisions = _run_collector_leg(leg, store, actions, pool, tail, today,
                                                           force_actions)
            except Exception as exc:  # a leg failure is contained
                detail = f"{type(exc).__name__}: {exc}"
                results.append(dict(leg, ok=False, detail=detail, revisions=[]))
                emit(f"FAILED  {head}: {detail}")
                continue
            results.append(dict(leg, ok=True, detail=detail, revisions=revisions))
            emit(f"ok      {head}: {detail}")
            for revision in revisions[:REVISION_ECHO]:
                emit(f"        revised {revision['date']} {revision['column']}: "
                     f"{revision['stored']:g} -> {revision['served']:g}")
            if len(revisions) > REVISION_ECHO:
                emit(f"        ... {len(revisions) - REVISION_ECHO} more revised cell(s)")
    finally:
        pool.close()
    failed = sum(1 for r in results if not r["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_path!r}")
    return results, failed == 0


def summary(results, ok) -> dict:
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
