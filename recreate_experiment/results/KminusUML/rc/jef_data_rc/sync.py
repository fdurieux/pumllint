"""Leg selection and the sync ritual over the declarative universe."""
import datetime as _dt

from . import actions, store
from .adjustment import price_basis_for
from .collectors import BinanceCollector, EODHDCollector
from .universe import PROVIDERS

DEFAULT_TAIL = 10
REVISION_ECHO = 10


class SyncError(ValueError):
    """A selection or argument refusal of sync/status."""


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


def utc_today(now=None):
    moment = now if now is not None else _dt.datetime.now(_dt.timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_dt.timezone.utc)
    return moment.astimezone(_dt.timezone.utc).date()


def fetch_window(leg, store_path, tail, today):
    """(has_rows, start, end) of a collector leg's fetch."""
    has_rows = store.latest_session(store_path, leg["exchange"], leg["symbol"]) is not None
    if has_rows:
        start = store.newest_sessions(store_path, leg["exchange"], leg["symbol"], tail)[0]
    else:
        start = leg["start"]
    end = leg["end"]
    if leg["asset_type"] == "crypto":
        guard = (today - _dt.timedelta(days=1)).isoformat()
        end = guard if end is None else min(end, guard)
    return has_rows, start, end


def plan_description(leg, store_path, tail, today):
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{head}: import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    has_rows, start, end = fetch_window(leg, store_path, tail, today)
    if has_rows:
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif start is not None:
        window = f"first fill from {start}"
    else:
        window = "first fill, full history"
    if end is not None:
        window += f" to {end}"
        if has_rows and start is not None and start > end:
            window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{head}: {action} ({window})"


class _Collectors:
    """Constructs each provider's collector at most once per run."""

    def __init__(self, injected, base_url):
        self._injected = dict(injected or {})
        self._built = {}
        self._failed = {}
        self._base_url = base_url

    def get(self, provider):
        if provider in self._injected:
            return self._injected[provider]
        if provider in self._built:
            return self._built[provider]
        if provider in self._failed:
            raise self._failed[provider]
        try:
            if provider == "eodhd":
                collector = EODHDCollector(base_url=self._base_url)
            else:
                collector = BinanceCollector()
        except Exception as exc:
            self._failed[provider] = exc
            raise
        self._built[provider] = collector
        return collector

    def close(self):
        for collector in self._built.values():
            collector.close()


def _run_collector_leg(leg, store_path, tail, force_actions, today, collectors):
    collector = collectors.get(leg["provider"])
    detail = ""
    events = []
    symbol = leg["symbol"]
    if leg["actions"]:
        stamp = actions.stamp_date(store_path, symbol)
        if force_actions or stamp is None or stamp < today:
            n_splits, n_divs = actions.sync_actions(collector, store_path, symbol)
            detail += f"{n_splits} split(s), {n_divs} dividend(s); "
        else:
            detail += "actions fresh; "
        events = actions.read_splits(store_path, symbol)

    has_rows, start, end = fetch_window(leg, store_path, tail, today)
    if has_rows and start is not None and end is not None and start > end:
        bars = []
        detail += (f"end {end} predates the stored tail (from {start}); nothing fetched - "
                   f"a pinned window with rows past its end, the fix is the declaration; ")
    else:
        bars = collector.fetch(symbol, start, end)
        limit = getattr(collector, "limit", None)
        if not has_rows and leg["start"] is None and limit is not None \
                and len(bars) == limit:
            detail += (f"first fill hit the provider page limit ({len(bars)} bars, no start "
                       f"declared) - the series is a trailing window, not history; ")

    basis = price_basis_for(leg["provider"], leg["asset_type"])
    n_bars, revisions = store.reconcile(
        store_path, leg["exchange"], symbol, bars, asset_type=leg["asset_type"],
        currency=leg["currency"], price_basis=basis,
        volume_basis=collector.volume_basis, events=events)
    if basis == "raw" and store.latest_session(store_path, leg["exchange"], symbol):
        store.readjust(store_path, leg["exchange"], symbol, events)
    detail += f"{n_bars} bar(s), {len(revisions)} revised cell(s)"
    if bars and str(bars[-1]["date"])[:10] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def _run_csv_leg(leg, store_path):
    rows = store.overwrite_csv(store_path, leg["path"], leg["exchange"], leg["symbol"],
                               leg["asset_type"], leg["currency"])
    return f"{rows} row(s) imported", []


def run_sync(universe, store_path=None, *, assets=None, providers=None, dry_run=False,
             tail=DEFAULT_TAIL, force_actions=False, now=None, collectors=None, out=None,
             base_url=None):
    """Run (or plan) every selected leg; returns (results, ok)."""
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    legs = select_legs(universe, assets, providers)
    if store_path is None:
        store_path = universe["defaults"]["store"]
    emit = out if out is not None else (lambda line: None)
    today = utc_today(now)

    if dry_run:
        emit(f"plan for store {store_path!r} ({len(legs)} leg(s)):")
        results = []
        for leg in legs:
            emit("  " + plan_description(leg, store_path, tail, today))
            results.append(dict(leg, ok=True, detail="planned"))
        return results, True

    pool = _Collectors(collectors, base_url)
    results = []
    try:
        for leg in legs:
            try:
                if leg["provider"] == "yahoo-csv":
                    detail, revisions = _run_csv_leg(leg, store_path)
                else:
                    detail, revisions = _run_collector_leg(
                        leg, store_path, tail, force_actions, today, pool)
                ok = True
            except Exception as exc:
                detail, revisions, ok = f"{type(exc).__name__}: {exc}", [], False
            results.append(dict(leg, ok=ok, detail=detail, revisions=revisions))
            head = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            if ok:
                emit(f"ok      {head}: {detail}")
                for rev in revisions[:REVISION_ECHO]:
                    emit(f"        revised {rev['date']} {rev['column']}: "
                         f"{rev['stored']:g} -> {rev['served']:g}")
                if len(revisions) > REVISION_ECHO:
                    emit(f"        ... {len(revisions) - REVISION_ECHO} more revised cell(s)")
            else:
                emit(f"FAILED  {head}: {detail}")
    finally:
        pool.close()
    failed = sum(1 for r in results if not r["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_path!r}")
    return results, failed == 0


def summary(results, ok):
    """The --summary-json document of one run."""
    legs = []
    for result in results:
        revisions = [{"date": r["date"], "column": r["column"],
                      "stored": float(r["stored"]), "served": float(r["served"])}
                     for r in result.get("revisions") or []]
        legs.append({"asset": result["asset"], "provider": result["provider"],
                     "exchange": result["exchange"], "symbol": result["symbol"],
                     "ok": result["ok"], "detail": result["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": 1, "legs_total": len(legs),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": sum(leg["revised_cells"] for leg in legs),
            "ok": ok, "legs": legs}
