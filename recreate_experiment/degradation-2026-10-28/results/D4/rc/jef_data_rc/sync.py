"""The sync ritual: leg selection, per-leg acquisition, the run log and summary."""
from __future__ import annotations

import datetime as _dt

from .actions import CorporateActionsStore, sync_actions
from .adjust import price_basis
from .store import ParquetStore
from .universe import PROVIDERS

DEFAULT_TAIL = 10
REVISION_ECHO = 10


class SyncError(RuntimeError):
    """A sync or status selection that cannot run."""


def select_legs(universe: dict, assets=None, providers=None) -> list:
    names = [a["name"] for a in universe["assets"]]
    for name in assets or []:
        if name not in names:
            raise SyncError(f"unknown asset {name!r}; universe has {sorted(names)}")
    for provider in providers or []:
        if provider not in PROVIDERS:
            raise SyncError(f"unknown provider {provider!r}; allowed: {list(PROVIDERS)}")
    legs = []
    for asset in universe["assets"]:
        if not asset["enabled"]:
            continue
        if assets and asset["name"] not in assets:
            continue
        for src in asset["sources"]:
            if not src["enabled"]:
                continue
            if providers and src["provider"] not in providers:
                continue
            legs.append({
                "asset": asset["name"],
                "provider": src["provider"],
                "exchange": src["exchange"],
                "symbol": src["symbol"],
                "path": src.get("path"),
                "asset_type": asset["asset_type"],
                "currency": asset["currency"],
                "start": src.get("start"),
                "end": src.get("end"),
                "actions": src["provider"] == "eodhd" and asset["asset_type"] != "crypto",
            })
    if not legs:
        raise SyncError("selection matched no enabled asset/source legs")
    return legs


def utc_today(now=None) -> _dt.date:
    clock = now if now is not None else _dt.datetime.now(_dt.timezone.utc)
    return clock.astimezone(_dt.timezone.utc).date()


def fetch_window(leg: dict, recent: list, today: _dt.date) -> tuple:
    start = recent[0].isoformat() if recent else leg["start"]
    end = leg["end"]
    if leg["asset_type"] == "crypto":
        guard = (today - _dt.timedelta(days=1)).isoformat()
        end = guard if end is None else min(end, guard)
    return start, end


def _inverted(recent: list, start, end) -> bool:
    return bool(recent) and start is not None and end is not None and start > end


def plan_line(leg: dict, store: ParquetStore, tail: int, today: _dt.date) -> str:
    head = f"{leg['asset']:>6} {leg['exchange']}/{leg['symbol']}"
    if leg["provider"] == "yahoo-csv":
        return f"{head}: import {leg['path']} (whole file, idempotent)"
    action = "sync-actions + load" if leg["actions"] else "load"
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    start, end = fetch_window(leg, recent, today)
    if recent:
        window = f"reconcile tail of {tail} session(s) from {start}"
    elif start is not None:
        window = f"first fill from {start}"
    else:
        window = "first fill, full history"
    if end is not None:
        window += f" to {end}"
    if _inverted(recent, start, end):
        window += " - INVERTED: end predates the stored tail, nothing to fetch"
    return f"{head}: {action} ({window})"


class _Collectors:
    def __init__(self, injected, base_url):
        self.injected = dict(injected or {})
        self.base_url = base_url
        self.built: dict = {}
        self.failed: dict = {}

    def get(self, provider: str):
        if provider in self.injected:
            return self.injected[provider]
        if provider in self.failed:
            raise self.failed[provider]
        if provider not in self.built:
            from .collectors import BinanceCollector, EODHDCollector

            try:
                if provider == "eodhd":
                    self.built[provider] = EODHDCollector(base_url=self.base_url)
                elif provider == "binance":
                    self.built[provider] = BinanceCollector()
                else:
                    raise SyncError(f"no collector for provider {provider!r}")
            except Exception as exc:
                self.failed[provider] = exc
                raise
        return self.built[provider]

    def close(self) -> None:
        for collector in self.built.values():
            collector.close()


def run_leg(leg: dict, *, store: ParquetStore, actions: CorporateActionsStore, collectors,
            tail: int, today: _dt.date, force_actions: bool) -> tuple:
    if leg["provider"] == "yahoo-csv":
        rows = store.ingest_yahoo_csv(leg["path"], leg["exchange"], leg["symbol"],
                                      leg["asset_type"], leg["currency"])
        return f"{rows} row(s) loaded", []
    collector = collectors.get(leg["provider"])
    detail = ""
    splits: list = []
    if leg["actions"]:
        stamp = actions.last_updated(leg["symbol"])
        if force_actions or stamp is None or stamp.astimezone(_dt.timezone.utc).date() < today:
            n_splits, n_dividends = sync_actions(collector, actions, leg["symbol"])
            detail += f"{n_splits} split(s), {n_dividends} dividend(s); "
        else:
            detail += "actions fresh; "
        splits = actions.load_splits(leg["symbol"])
    exchange, symbol = leg["exchange"], leg["symbol"]
    recent = store.recent_dates(exchange, symbol, tail)
    start, end = fetch_window(leg, recent, today)
    if _inverted(recent, start, end):
        detail += (f"end {end} predates the stored tail (from {start}); nothing fetched - a "
                   "pinned window with rows past its end, the fix is the declaration; ")
        bars: list = []
    else:
        bars = collector.get_eod(symbol, start, end)
        limit = getattr(collector, "limit", None)
        if not recent and leg["start"] is None and limit is not None and len(bars) == limit:
            detail += (f"first fill hit the provider page limit ({len(bars)} bars, no start "
                       "declared) - the series is a trailing window, not history; ")
    basis = price_basis(leg["provider"], leg["asset_type"])
    count, revisions = store.reconcile_bars(exchange, symbol, bars, splits, basis,
                                            collector.volume_basis,
                                            asset_type=leg["asset_type"], currency=leg["currency"])
    if basis == "raw" and store.latest_date(exchange, symbol) is not None:
        store.reapply_adjustment(exchange, symbol, splits)
    detail += f"{count} bar(s), {len(revisions)} revised cell(s)"
    if bars and str(bars[-1]["date"])[:10] == today.isoformat():
        detail += "; today-dated bar ingested (pre-close fetch?)"
    return detail, revisions


def run_sync(universe: dict, store_path, *, assets=None, providers=None, dry_run=False,
             tail=DEFAULT_TAIL, force_actions=False, now=None, collectors=None, out=None,
             base_url=None) -> tuple:
    if tail < 1:
        raise SyncError(f"tail must be >= 1 session, got {tail}")
    legs = select_legs(universe, assets, providers)
    today = utc_today(now)
    emit = out if out is not None else (lambda line: None)
    store_text = str(store_path)
    store = ParquetStore(store_path)
    if dry_run:
        emit(f"plan for store {store_text!r} ({len(legs)} leg(s)):")
        for leg in legs:
            emit("  " + plan_line(leg, store, tail, today))
        return [dict(leg, ok=True, detail="planned") for leg in legs], True
    actions = CorporateActionsStore(store_path)
    pool = _Collectors(collectors, base_url)
    results = []
    try:
        for leg in legs:
            label = f"{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]"
            try:
                detail, revisions = run_leg(leg, store=store, actions=actions, collectors=pool,
                                            tail=tail, today=today, force_actions=force_actions)
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                results.append(dict(leg, ok=False, detail=detail, revisions=[]))
                emit(f"FAILED  {label}: {detail}")
                continue
            results.append(dict(leg, ok=True, detail=detail, revisions=revisions))
            emit(f"ok      {label}: {detail}")
            for rev in revisions[:REVISION_ECHO]:
                emit(f"        revised {rev['date']} {rev['column']}: "
                     f"{rev['stored']:g} -> {rev['served']:g}")
            if len(revisions) > REVISION_ECHO:
                emit(f"        ... {len(revisions) - REVISION_ECHO} more revised cell(s)")
    finally:
        pool.close()
    failed = sum(1 for r in results if not r["ok"])
    emit(f"{len(results)} leg(s), {failed} failed -> store {store_text!r}")
    return results, failed == 0


def sync_summary(results: list, ok: bool) -> dict:
    legs = []
    for r in results:
        revisions = [{"date": rev["date"], "column": rev["column"],
                      "stored": float(rev["stored"]), "served": float(rev["served"])}
                     for rev in r.get("revisions", [])]
        legs.append({"asset": r["asset"], "provider": r["provider"], "exchange": r["exchange"],
                     "symbol": r["symbol"], "ok": bool(r["ok"]), "detail": r["detail"],
                     "revised_cells": len(revisions), "revisions": revisions})
    return {"schema_version": 1,
            "legs_total": len(legs),
            "legs_failed": sum(1 for leg in legs if not leg["ok"]),
            "revised_cells_total": sum(leg["revised_cells"] for leg in legs),
            "ok": bool(ok),
            "legs": legs}
