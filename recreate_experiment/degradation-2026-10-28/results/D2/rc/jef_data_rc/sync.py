"""The universe's acquisition ritual: leg selection, per-leg sync, summary."""
import datetime as _dt

from .actions import CorporateActionsStore, sync_actions
from .universe import PROVIDERS

DEFAULT_TAIL = 10
REVISION_ECHO = 10


class SyncError(RuntimeError):
    """A sync that cannot start: bad tail, unknown filter, empty selection."""


def select_legs(universe, assets=None, providers=None):
    names = [a["name"] for a in universe["assets"]]
    for name in assets or []:
        if name not in names:
            raise SyncError(f"unknown asset {name!r}; universe has {sorted(names)}")
    for provider in providers or []:
        if provider not in PROVIDERS:
            raise SyncError(f"unknown provider {provider!r}; allowed: {PROVIDERS}")
    legs = []
    for asset in universe["assets"]:
        if not asset["enabled"] or (assets and asset["name"] not in assets):
            continue
        for source in asset["sources"]:
            if not source["enabled"] or (providers and source["provider"] not in providers):
                continue
            provider = source["provider"]
            asset_type = asset["asset_type"]
            legs.append({
                "asset": asset["name"],
                "provider": provider,
                "exchange": source["exchange"],
                "symbol": source["symbol"],
                "path": source.get("path"),
                "asset_type": asset_type,
                "currency": asset["currency"],
                "start": source.get("start"),
                "end": source.get("end"),
                "actions": provider == "eodhd" and asset_type != "crypto",
            })
    if not legs:
        raise SyncError("selection matched no enabled asset/source legs")
    return legs


def price_basis(provider, asset_type):
    if provider == "eodhd" and asset_type != "crypto":
        return "raw"
    return "split_adjusted"


def fetch_end(leg, today):
    end = leg["end"]
    if leg["asset_type"] == "crypto":
        guard = (today - _dt.timedelta(days=1)).isoformat()
        end = guard if end is None else min(end, guard)
    return end


def fetch_window(leg, store, tail, today):
    """(start, end, has_rows) of a collector leg's bar fetch."""
    stored = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    has_rows = bool(stored)
    start = stored[0] if has_rows else leg["start"]
    return start, fetch_end(leg, today), has_rows


def plan_line(leg, store, tail, today):
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{head}: import {leg['path']} (whole file, idempotent)"
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
    if has_rows and start is not None and end is not None and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{head}: {action} ({window})"


def _stamp_day(stamp):
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(_dt.timezone.utc)
    return stamp.date()


class _Collectors:
    """One collector per provider per run: injected ones, else built lazily."""

    def __init__(self, injected=None, base_url=None):
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
                raise ValueError(f"no collector for provider {provider!r}")
        except Exception as exc:
            self.failed[provider] = exc
            raise
        self.built[provider] = collector
        return collector

    def close(self):
        for collector in self.built.values():
            collector.close()


def run_collector_leg(leg, collector, store, actions_store, tail, today, force_actions):
    parts = []
    splits = []
    if leg["actions"]:
        stamp = actions_store.last_updated(leg["symbol"])
        if force_actions or stamp is None or _stamp_day(stamp) < today:
            s, d = sync_actions(collector, actions_store, leg["symbol"])
            parts.append(f"{s} split(s), {d} dividend(s); ")
        else:
            parts.append("actions fresh; ")
        splits = actions_store.load_splits(leg["symbol"])
    start, end, has_rows = fetch_window(leg, store, tail, today)
    if has_rows and start is not None and end is not None and start > end:
        bars = []
        parts.append(f"end {end} predates the stored tail (from {start}); nothing fetched - a "
                     "pinned window with rows past its end, the fix is the declaration; ")
    else:
        bars = collector.get_eod(leg["symbol"], start, end)
    limit = getattr(collector, "limit", None)
    if not has_rows and leg["start"] is None and limit is not None and len(bars) == limit:
        parts.append(f"first fill hit the provider page limit ({len(bars)} bars, no start "
                     "declared) - the series is a trailing window, not history; ")
    basis = price_basis(leg["provider"], leg["asset_type"])
    count, revisions = store.reconcile_bars(
        leg["exchange"], leg["symbol"], bars, splits, basis, collector.volume_basis,
        asset_type=leg["asset_type"], currency=leg["currency"])
    if basis == "raw" and store.year_files(leg["exchange"], leg["symbol"]):
        store.reapply_adjustment(leg["exchange"], leg["symbol"], splits)
    detail = "".join(parts) + f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and bars[-1]["date"] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def run_csv_leg(leg, store):
    rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                  leg["asset_type"], leg["currency"])
    return f"{rows} row(s) imported", []


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False,
             tail=DEFAULT_TAIL, force_actions=False, now=None, collectors=None, out=None,
             base_url=None):
    """Run the sync; returns (per-leg results, ok)."""
    from .store import ParquetStore

    emit = out or (lambda line: None)
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    legs = select_legs(universe, assets, providers)
    clock = now or _dt.datetime.now(_dt.timezone.utc)
    today = clock.astimezone(_dt.timezone.utc).date()
    store = ParquetStore(store_path)
    if dry_run:
        emit(f"plan for store {str(store_path)!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_line(leg, store, tail, today))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True
    actions_store = CorporateActionsStore(store_path)
    pool = _Collectors(collectors, base_url)
    results = []
    try:
        for leg in legs:
            try:
                if leg["provider"] == "yahoo-csv":
                    detail, revisions = run_csv_leg(leg, store)
                else:
                    collector = pool.get(leg["provider"])
                    detail, revisions = run_collector_leg(leg, collector, store, actions_store,
                                                          tail, today, force_actions)
                ok = True
            except Exception as exc:
                detail, revisions, ok = f"{type(exc).__name__}: {exc}", [], False
            result = dict(leg, ok=ok, detail=detail, revisions=revisions)
            results.append(result)
            label = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            if ok:
                emit(f"ok      {label}: {detail}")
                for rev in revisions[:REVISION_ECHO]:
                    emit(f"        revised {rev['date']} {rev['column']}: "
                         f"{rev['stored']:g} -> {rev['served']:g}")
                if len(revisions) > REVISION_ECHO:
                    emit(f"        ... {len(revisions) - REVISION_ECHO} more revised cell(s)")
            else:
                emit(f"FAILED  {label}: {detail}")
    finally:
        pool.close()
    failed = sum(1 for r in results if not r["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {str(store_path)!r}")
    return results, failed == 0


def sync_summary(results, ok):
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
