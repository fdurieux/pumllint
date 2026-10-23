"""The sync ritual: leg selection, per-leg acquisition, containment and reporting."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from .actions import CorporateActionsStore, sync_actions
from .store import ParquetStore
from .universe import PROVIDERS

DEFAULT_TAIL = 10
REVISIONS_ECHOED = 10
SUMMARY_SCHEMA_VERSION = 1


class SyncError(RuntimeError):
    """A sync or status invocation refused before any leg runs."""


def select_legs(universe, assets=None, providers=None):
    """Enabled asset x enabled source legs, filtered, in universe order."""
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


def price_basis(provider, asset_type):
    if provider == "eodhd" and asset_type != "crypto":
        return "raw"
    return "split_adjusted"


def fetch_end(leg, today):
    ends = []
    if leg["end"]:
        ends.append(leg["end"])
    if leg["asset_type"] == "crypto":
        ends.append((today - _dt.timedelta(days=1)).isoformat())
    return min(ends) if ends else None


def fetch_window(leg, store, tail, today):
    """(stored tail dates, fetch start, fetch end) of a collector leg."""
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    start = recent[0] if recent else leg["start"]
    return recent, start, fetch_end(leg, today)


def plan_description(leg, store, tail, today):
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}: "
    if leg["provider"] == "yahoo-csv":
        return head + f"import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    recent, start, end = fetch_window(leg, store, tail, today)
    if recent:
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif start:
        window = f"first fill from {start}"
    else:
        window = "first fill, full history"
    if end:
        window += f" to {end}"
    if recent and end and start > end:
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return head + f"{action} ({window})"


def default_collector(provider, base_url=None):
    if provider == "eodhd":
        from .collectors.eodhd import DEFAULT_BASE_URL, EODHDCollector

        return EODHDCollector(base_url=base_url or DEFAULT_BASE_URL)
    if provider == "binance":
        from .collectors.binance import BinanceCollector

        return BinanceCollector()
    raise SyncError(f"no collector for provider {provider!r}")


def _collector_leg(leg, collector, store, actions, tail, today, force_actions):
    detail = ""
    splits = []
    symbol = leg["symbol"]
    if leg["actions"]:
        stamp = actions.last_updated(symbol)
        if force_actions or stamp is None or stamp.astimezone(_dt.timezone.utc).date() < today:
            n_splits, n_dividends = sync_actions(collector, actions, symbol)
            detail += f"{n_splits} split(s), {n_dividends} dividend(s); "
        else:
            detail += "actions fresh; "
        splits = actions.load_splits(symbol)
    recent, start, end = fetch_window(leg, store, tail, today)
    if recent and start and end and start > end:
        bars = []
        detail += (f"end {end} predates the stored tail (from {start}); nothing fetched - a "
                   f"pinned window with rows past its end, the fix is the declaration; ")
    else:
        bars = collector.get_eod(symbol, start, end)
        limit = getattr(collector, "limit", None)
        if not recent and not leg["start"] and limit is not None and len(bars) == limit:
            detail += (f"first fill hit the provider page limit ({len(bars)} bars, no start "
                       f"declared) - the series is a trailing window, not history; ")
    basis = price_basis(leg["provider"], leg["asset_type"])
    count, revisions = store.reconcile_bars(
        leg["exchange"], symbol, bars, splits, basis, collector.volume_basis,
        leg["asset_type"], leg["currency"])
    if basis == "raw" and store.latest_date(leg["exchange"], symbol) is not None:
        store.reapply_adjustment(leg["exchange"], symbol, splits)
    detail += f"{count} bar(s), {len(revisions)} revised cell(s)"
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
    clock = now if now is not None else _dt.datetime.now(_dt.timezone.utc)
    today = clock.astimezone(_dt.timezone.utc).date()
    emit = out if out is not None else (lambda line: None)
    store_label = str(store_path)
    store = ParquetStore(store_label)
    actions = CorporateActionsStore(Path(store_label) / "corporate_actions")

    if dry_run:
        emit(f"plan for store {store_label!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_description(leg, store, tail, today))
            results.append({**leg, "ok": True, "detail": "planned"})
        return results, True

    injected = dict(collectors or {})
    built = {}

    def collector_for(provider):
        if provider in injected:
            return injected[provider]
        if provider not in built:
            try:
                built[provider] = default_collector(provider, base_url)
            except Exception as exc:
                built[provider] = exc
        made = built[provider]
        if isinstance(made, Exception):
            raise made
        return made

    results = []
    failed = 0
    try:
        for leg in legs:
            tag = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            try:
                if leg["provider"] == "yahoo-csv":
                    rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                                  leg["asset_type"], leg["currency"])
                    detail, revisions = f"{rows} row(s) imported", []
                else:
                    collector = collector_for(leg["provider"])
                    detail, revisions = _collector_leg(leg, collector, store, actions, tail,
                                                       today, force_actions)
            except Exception as exc:
                failed += 1
                detail = f"{type(exc).__name__}: {exc}"
                results.append({**leg, "ok": False, "detail": detail, "revisions": []})
                emit(f"FAILED  {tag}: {detail}")
                continue
            results.append({**leg, "ok": True, "detail": detail, "revisions": revisions})
            emit(f"ok      {tag}: {detail}")
            for revision in revisions[:REVISIONS_ECHOED]:
                emit(f"        revised {revision['date']} {revision['column']}: "
                     f"{revision['stored']:g} -> {revision['served']:g}")
            if len(revisions) > REVISIONS_ECHOED:
                emit(f"        ... {len(revisions) - REVISIONS_ECHOED} more revised cell(s)")
    finally:
        for made in built.values():
            if not isinstance(made, Exception):
                made.close()
    emit(f"{len(legs)} leg(s), {failed} failed -> store {store_label!r}")
    return results, failed == 0


def sync_summary(results, ok):
    """The --summary-json document of a sync run."""
    legs = []
    total = 0
    for result in results:
        revisions = [{"date": r["date"], "column": r["column"], "stored": float(r["stored"]),
                      "served": float(r["served"])} for r in result.get("revisions", [])]
        total += len(revisions)
        legs.append({"asset": result["asset"], "provider": result["provider"],
                     "exchange": result["exchange"], "symbol": result["symbol"],
                     "ok": bool(result["ok"]), "detail": result["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": SUMMARY_SCHEMA_VERSION, "legs_total": len(legs),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": total, "ok": bool(ok), "legs": legs}
