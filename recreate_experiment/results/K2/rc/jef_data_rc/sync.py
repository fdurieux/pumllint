"""The acquisition ritual: leg selection, the per-leg sync and the run summary."""
from __future__ import annotations

import datetime as _dt

from .actions import CorporateActionsStore, stamp_utc_date, sync_actions
from .store import ParquetStore, resolve_price_basis
from .universe import PROVIDERS

DEFAULT_TAIL = 10
REVISION_ECHO = 10


class SyncError(RuntimeError):
    """A sync or status invocation refused before any leg runs."""


def select_legs(universe, assets=None, providers=None):
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
            collector = source["provider"] != "yahoo-csv"
            legs.append({
                "asset": asset["name"],
                "provider": source["provider"],
                "exchange": source["exchange"],
                "symbol": source["symbol"],
                "path": None if collector else source["path"],
                "asset_type": asset["asset_type"],
                "currency": asset["currency"],
                "start": source.get("start") if collector else None,
                "end": source.get("end") if collector else None,
                "actions": source["provider"] == "eodhd" and asset["asset_type"] != "crypto",
            })
    if not legs:
        raise SyncError("selection matched no enabled asset/source legs")
    return legs


def fetch_end(leg, today):
    candidates = []
    if leg["end"]:
        candidates.append(leg["end"])
    if leg["asset_type"] == "crypto":
        candidates.append((today - _dt.timedelta(days=1)).isoformat())
    return min(candidates) if candidates else None


def fetch_window(leg, store, tail, today):
    """(has stored rows, fetch start, fetch end)."""
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    if recent:
        start = recent[0].isoformat()
    else:
        start = leg["start"]
    return bool(recent), start, fetch_end(leg, today)


def plan_description(leg, store, tail, today):
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{head}: import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    has_rows, start, end = fetch_window(leg, store, tail, today)
    if has_rows:
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif leg["start"]:
        window = f"first fill from {leg['start']}"
    else:
        window = "first fill, full history"
    if end:
        window += f" to {end}"
    if has_rows and end and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{head}: {action} ({window})"


def run_leg(leg, collector, store, actions_store, tail, today, force_actions):
    """One collector leg; returns (detail, revisions)."""
    exchange, symbol = leg["exchange"], leg["symbol"]
    detail = ""
    splits = []
    if leg["actions"]:
        stamp = actions_store.last_updated(symbol)
        if force_actions or stamp is None or stamp_utc_date(stamp) < today:
            n_splits, n_dividends = sync_actions(collector, actions_store, symbol)
            detail += f"{n_splits} split(s), {n_dividends} dividend(s); "
        else:
            detail += "actions fresh; "
        splits = actions_store.load_splits(symbol)
    has_rows, start, end = fetch_window(leg, store, tail, today)
    if has_rows and end is not None and start is not None and start > end:
        bars = []
        detail += (f"end {end} predates the stored tail (from {start}); nothing fetched - a "
                   f"pinned window with rows past its end, the fix is the declaration; ")
    else:
        bars = collector.get_eod(symbol, start, end)
        limit = getattr(collector, "limit", None)
        if not has_rows and leg["start"] is None and limit is not None and len(bars) == limit:
            detail += (f"first fill hit the provider page limit ({len(bars)} bars, no start "
                       f"declared) - the series is a trailing window, not history; ")
    price_basis = resolve_price_basis(leg["provider"], leg["asset_type"])
    count, revisions = store.reconcile_bars(
        exchange, symbol, bars, splits, price_basis, collector.volume_basis,
        asset_type=leg["asset_type"], currency=leg["currency"])
    if price_basis == "raw" and store.latest_date(exchange, symbol) is not None:
        store.reapply_adjustment(exchange, symbol, splits)
    detail += f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and str(bars[-1]["date"])[:10] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def _construct(provider, base_url):
    if provider == "eodhd":
        from .collectors.eodhd import EODHDCollector

        return EODHDCollector(base_url=base_url)
    from .collectors.binance import BinanceCollector

    return BinanceCollector()


def run_sync(universe, store_path, *, assets=None, providers=None, dry_run=False,
             tail=DEFAULT_TAIL, force_actions=False, now=None, collectors=None, out=None,
             base_url=None):
    """Run the ritual over the selected legs; returns (results, ok)."""
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    legs = select_legs(universe, assets=assets, providers=providers)
    clock = now if now is not None else _dt.datetime.now(_dt.timezone.utc)
    today = clock.astimezone(_dt.timezone.utc).date()
    emit = out if out is not None else (lambda line: None)
    store = ParquetStore(store_path)
    actions_store = CorporateActionsStore(store_path)

    if dry_run:
        emit(f"plan for store {store_path!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_description(leg, store, tail, today))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True

    injected = dict(collectors or {})
    built = {}

    def collector_for(provider):
        if provider in injected:
            return injected[provider]
        if provider not in built:
            built[provider] = _construct(provider, base_url)
        return built[provider]

    results = []
    try:
        for leg in legs:
            try:
                if leg["provider"] == "yahoo-csv":
                    rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                                  leg["asset_type"], leg["currency"])
                    detail, revisions = f"{rows} row(s) imported", []
                else:
                    collector = collector_for(leg["provider"])
                    detail, revisions = run_leg(leg, collector, store, actions_store, tail,
                                                today, force_actions)
                ok = True
            except Exception as exc:
                ok, detail, revisions = False, f"{type(exc).__name__}: {exc}", []
            results.append(dict(leg, ok=ok, detail=detail, revisions=revisions))
            head = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            if ok:
                emit(f"ok      {head}: {detail}")
                for revision in revisions[:REVISION_ECHO]:
                    emit(f"        revised {revision['date']} {revision['column']}: "
                         f"{revision['stored']:g} -> {revision['served']:g}")
                if len(revisions) > REVISION_ECHO:
                    emit(f"        ... {len(revisions) - REVISION_ECHO} more revised cell(s)")
            else:
                emit(f"FAILED  {head}: {detail}")
    finally:
        for collector in built.values():
            try:
                collector.close()
            except Exception:
                pass
    failed = sum(1 for r in results if not r["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_path!r}")
    return results, failed == 0


def sync_summary(results, ok):
    legs = []
    for result in results:
        revisions = [{"date": r["date"], "column": r["column"], "stored": float(r["stored"]),
                      "served": float(r["served"])} for r in result.get("revisions", [])]
        legs.append({"asset": result["asset"], "provider": result["provider"],
                     "exchange": result["exchange"], "symbol": result["symbol"],
                     "ok": result["ok"], "detail": result["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": 1, "legs_total": len(legs),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": sum(leg["revised_cells"] for leg in legs),
            "ok": bool(ok), "legs": legs}
