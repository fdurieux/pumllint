"""The sync ritual: leg selection, per-leg windows, actions gate, reconcile, summary."""
from datetime import datetime, timedelta, timezone

from .actions import CorporateActionsStore, sync_actions
from .store import ParquetStore
from .universe import PROVIDERS

REVISION_ECHO = 10


class SyncError(RuntimeError):
    """A sync or status invocation refused before any leg runs."""


def select_legs(universe, assets=None, providers=None):
    """The ordered legs: enabled asset x enabled source, filtered."""
    names = [asset["name"] for asset in universe["assets"]]
    for name in assets or []:
        if name not in names:
            raise SyncError(f"unknown asset {name!r}; universe has {sorted(names)}")
    for name in providers or []:
        if name not in PROVIDERS:
            raise SyncError(f"unknown provider {name!r}; allowed: {PROVIDERS}")
    legs = []
    for asset in universe["assets"]:
        if not asset["enabled"] or (assets and asset["name"] not in assets):
            continue
        for source in asset["sources"]:
            if not source["enabled"] or (providers and source["provider"] not in providers):
                continue
            collector_source = source["provider"] != "yahoo-csv"
            legs.append({
                "asset": asset["name"],
                "provider": source["provider"],
                "exchange": source["exchange"],
                "symbol": source["symbol"],
                "path": None if collector_source else source["path"],
                "asset_type": asset["asset_type"],
                "currency": asset["currency"],
                "start": source.get("start") if collector_source else None,
                "end": source.get("end") if collector_source else None,
                "actions": source["provider"] == "eodhd" and asset["asset_type"] != "crypto",
            })
    if not legs:
        raise SyncError("selection matched no enabled asset/source legs")
    return legs


def run_date(now=None):
    clock = now if now is not None else datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    return clock.astimezone(timezone.utc).date()


def price_basis(leg):
    if leg["provider"] == "eodhd" and leg["asset_type"] != "crypto":
        return "raw"
    return "split_adjusted"


def fetch_window(leg, store, tail, today):
    """(start, end, series_has_rows) of a collector leg."""
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    has_rows = bool(recent)
    start = recent[0].isoformat() if has_rows else leg["start"]
    end = leg["end"]
    if leg["asset_type"] == "crypto":
        guard = (today - timedelta(days=1)).isoformat()
        end = guard if end is None else min(end, guard)
    return start, end, has_rows


def plan_line(leg, store, tail, today):
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}: "
    if leg["provider"] == "yahoo-csv":
        return head + f"import {leg['path']} (whole file, idempotent)"
    start, end, has_rows = fetch_window(leg, store, tail, today)
    action = "sync-actions + load" if leg["actions"] else "load"
    if has_rows:
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif start is not None:
        window = f"first fill from {start}"
    else:
        window = "first fill, full history"
    if end is not None:
        window += f" to {end}"
    if has_rows and end is not None and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return head + f"{action} ({window})"


class CollectorPool:
    """Collectors built lazily, once per provider; injected ones are used as given."""

    def __init__(self, injected=None, base_url=None):
        self.injected = dict(injected or {})
        self.base_url = base_url
        self.built = {}

    def get(self, provider):
        if provider in self.injected:
            return self.injected[provider]
        if provider not in self.built:
            if provider == "eodhd":
                from .collectors.eodhd import DEFAULT_BASE_URL, EODHDCollector

                self.built[provider] = EODHDCollector(base_url=self.base_url or DEFAULT_BASE_URL)
            elif provider == "binance":
                from .collectors.binance import BinanceCollector

                self.built[provider] = BinanceCollector()
            else:
                raise SyncError(f"no collector for provider {provider!r}")
        return self.built[provider]

    def close(self):
        for collector in self.built.values():
            collector.close()


def run_leg(leg, store, actions_store, pool, tail, today, force_actions):
    """Detail and revisions of one leg; raises on any failure."""
    if leg["provider"] == "yahoo-csv":
        rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                      leg["asset_type"], leg["currency"])
        return f"{rows} row(s) imported", []
    collector = pool.get(leg["provider"])
    detail = ""
    splits = []
    if leg["actions"]:
        stamp = actions_store.last_updated(leg["symbol"])
        if force_actions or stamp is None or stamp.date() < today:
            split_count, dividend_count = sync_actions(collector, actions_store, leg["symbol"])
            detail += f"{split_count} split(s), {dividend_count} dividend(s); "
        else:
            detail += "actions fresh; "
        splits = actions_store.load_splits(leg["symbol"])
    start, end, has_rows = fetch_window(leg, store, tail, today)
    if has_rows and end is not None and start > end:
        detail += (f"end {end} predates the stored tail (from {start}); nothing fetched - a "
                   "pinned window with rows past its end, the fix is the declaration; ")
        bars = []
    else:
        bars = collector.get_eod(leg["symbol"], start, end)
    limit = getattr(collector, "limit", None)
    if not has_rows and leg["start"] is None and limit is not None and len(bars) == limit:
        detail += (f"first fill hit the provider page limit ({len(bars)} bars, no start declared)"
                   " - the series is a trailing window, not history; ")
    basis = price_basis(leg)
    count, revisions = store.reconcile_bars(
        leg["exchange"], leg["symbol"], bars, splits, basis, collector.volume_basis,
        asset_type=leg["asset_type"], currency=leg["currency"])
    if basis == "raw" and store.latest_date(leg["exchange"], leg["symbol"]) is not None:
        store.reapply_adjustment(leg["exchange"], leg["symbol"], splits)
    detail += f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and str(bars[-1]["date"])[:10] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def log_lines(result):
    flag = "ok" if result["ok"] else "FAILED"
    lines = [f"{flag:<8}{result['asset']} {result['exchange']}/{result['symbol']} "
             f"[{result['provider']}]: {result['detail']}"]
    if result["ok"]:
        revisions = result.get("revisions", [])
        for revision in revisions[:REVISION_ECHO]:
            lines.append(f"        revised {revision['date']} {revision['column']}: "
                         f"{revision['stored']:g} -> {revision['served']:g}")
        if len(revisions) > REVISION_ECHO:
            lines.append(f"        ... {len(revisions) - REVISION_ECHO} more revised cell(s)")
    return lines


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False, tail=10,
             force_actions=False, now=None, collectors=None, out=None, base_url=None):
    """Run (or plan) every selected leg; returns (results, ok)."""
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    today = run_date(now)
    legs = select_legs(universe, assets, providers)
    emit = out if out is not None else (lambda line: None)
    store = ParquetStore(store_path)
    if dry_run:
        emit(f"plan for store {store_path!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_line(leg, store, tail, today))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True
    actions_store = CorporateActionsStore(store_path)
    pool = CollectorPool(collectors, base_url)
    results = []
    try:
        for leg in legs:
            try:
                detail, revisions = run_leg(leg, store, actions_store, pool, tail, today,
                                            force_actions)
                result = dict(leg, ok=True, detail=detail, revisions=revisions)
            except Exception as exc:
                result = dict(leg, ok=False, detail=f"{type(exc).__name__}: {exc}", revisions=[])
            results.append(result)
            for line in log_lines(result):
                emit(line)
    finally:
        pool.close()
    failed = sum(1 for result in results if not result["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_path!r}")
    return results, failed == 0


def sync_summary(results, ok):
    """The --summary-json document of a run's results."""
    legs = []
    for result in results:
        revisions = [{"date": revision["date"], "column": revision["column"],
                      "stored": float(revision["stored"]), "served": float(revision["served"])}
                     for revision in result.get("revisions", [])]
        legs.append({"asset": result["asset"], "provider": result["provider"],
                     "exchange": result["exchange"], "symbol": result["symbol"],
                     "ok": bool(result["ok"]), "detail": result["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": 1, "legs_total": len(legs),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": sum(leg["revised_cells"] for leg in legs),
            "ok": bool(ok), "legs": legs}
