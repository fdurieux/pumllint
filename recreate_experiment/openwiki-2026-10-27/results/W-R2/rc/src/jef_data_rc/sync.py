"""Configured batch acquisition: universe -> legs -> store.

`select_legs()` expands every enabled source of every selected enabled asset
into a leg. `run_sync()` processes legs independently:

* a `yahoo-csv` leg imports its whole file (overwrite, pre-adjusted);
* a collector leg computes a window from local state, fetches bars and
  reconciles them into the store. An empty series starts at the source
  `start` floor; an established one re-fetches its newest `tail` sessions.
  The source `end` caps every fetch, and a declared crypto leg also stops at
  the previous completed UTC day.
* a raw-basis (non-crypto) EODHD leg refreshes corporate actions before its
  bars (once per UTC day unless forced) and re-derives the whole stored
  series afterwards.

A failing leg is recorded and the batch continues; the aggregate `ok` is
false when any leg failed.
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from jef_data_rc.universe import PROVIDERS

DEFAULT_TAIL = 10
MAX_REVISIONS_SHOWN = 10
SUMMARY_SCHEMA_VERSION = 1


class SyncError(ValueError):
    """The selection or run options are invalid."""


@dataclass
class LegResult:
    leg: dict
    ok: bool
    detail: str = ""
    rows: int = 0
    revisions: list[dict] = field(default_factory=list)


@dataclass
class Window:
    start: str | None
    end: str | None
    established: bool
    guard: str | None
    inverted: bool


def leg_label(leg: dict) -> str:
    return f"{leg['asset']} {leg['provider']} {leg['exchange']}/{leg['symbol']}"


def _utc(now: _dt.datetime | None) -> _dt.datetime:
    if now is None:
        return _dt.datetime.now(_dt.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=_dt.timezone.utc)
    return now.astimezone(_dt.timezone.utc)


def select_legs(universe: dict, assets=None, providers=None) -> list[dict]:
    """Every enabled source of every selected enabled asset, in declaration order."""
    assets = list(assets) if assets else []
    providers = list(providers) if providers else []
    names = [a["name"] for a in universe["assets"]]
    unknown_assets = [a for a in assets if a not in names]
    if unknown_assets:
        raise SyncError(
            f"unknown asset(s): {', '.join(unknown_assets)} (known: {', '.join(names)})"
        )
    unknown_providers = [p for p in providers if p not in PROVIDERS]
    if unknown_providers:
        raise SyncError(
            f"unknown provider(s): {', '.join(unknown_providers)} (known: {', '.join(PROVIDERS)})"
        )
    legs: list[dict] = []
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
                "asset_type": asset["asset_type"],
                "currency": src["currency"],
                "start": src["start"],
                "end": src["end"],
                "path": src["path"],
                "actions": src["provider"] == "eodhd" and asset["asset_type"] != "crypto",
            })
    if not legs:
        sel = []
        if assets:
            sel.append(f"asset(s) {', '.join(assets)}")
        if providers:
            sel.append(f"provider(s) {', '.join(providers)}")
        what = " with " + " and ".join(sel) if sel else ""
        raise SyncError(f"no enabled legs selected{what}")
    return legs


def _window(store, leg: dict, tail: int, now: _dt.datetime) -> Window:
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    established = bool(recent)
    start = recent[0] if established else leg["start"]
    end = leg["end"]
    guard = None
    if leg["asset_type"] == "crypto":
        guard = (now.date() - _dt.timedelta(days=1)).isoformat()
        end = min(end, guard) if end else guard
    inverted = bool(established and end is not None and start > end)
    return Window(start, end, established, guard, inverted)


def _window_text(leg: dict, w: Window, tail: int) -> str:
    if w.established:
        text = f"tail from {w.start} (newest {tail} stored session(s))"
    else:
        text = f"first fill from {w.start or 'provider default'}"
    text += f" to {w.end or 'latest'}"
    caps = []
    if leg["end"]:
        caps.append(f"end cap {leg['end']}")
    if w.guard:
        caps.append(f"crypto guard {w.guard}")
    if caps:
        text += f" [{', '.join(caps)}]"
    return text


def _inverted_text(w: Window) -> str:
    return (
        f"no fetch: stored tail begins {w.start}, after the pinned end {w.end}; "
        "rows lie beyond the declared end - review the source bound"
    )


def _plan(store, leg: dict, tail: int, now: _dt.datetime) -> str:
    if leg["provider"] == "yahoo-csv":
        return f"import-csv {leg['path']} (whole file, overwrite)"
    w = _window(store, leg, tail, now)
    action = "sync-actions + load" if leg["actions"] else "load"
    text = f"{action}: {_window_text(leg, w, tail)}"
    if w.inverted:
        text += f"; {_inverted_text(w)}"
    return text


def _make_collector(provider: str):
    if provider == "eodhd":
        from jef_data_rc.collectors.eodhd import EODHDCollector

        return EODHDCollector()
    if provider == "binance":
        from jef_data_rc.collectors.binance import BinanceCollector

        return BinanceCollector()
    raise SyncError(f"no collector for provider {provider!r}")


def _run_leg(store, leg: dict, *, tail: int, force_actions: bool, now: _dt.datetime,
             collector_for: Callable[[str], Any]) -> LegResult:
    from jef_data_rc.actions import ActionsStore, stamp_date, sync_actions

    if leg["provider"] == "yahoo-csv":
        n = store.ingest_yahoo_csv(leg["path"], symbol=leg["symbol"], exchange=leg["exchange"],
                                   asset_type=leg["asset_type"], currency=leg["currency"])
        return LegResult(leg, True, f"imported {n} row(s) from {leg['path']}", rows=n)

    collector = collector_for(leg["provider"])
    w = _window(store, leg, tail, now)
    details: list[str] = []
    splits: list = []
    if leg["provider"] == "eodhd" and leg["actions"]:
        price_basis = "raw"
        actions = ActionsStore(store.root)
        stamped = stamp_date(actions.last_updated(leg["symbol"]))
        if force_actions or stamped is None or stamped < now.date():
            new_splits, dividends = sync_actions(collector, store.root, leg["symbol"],
                                                 exchange=leg["exchange"], now=now)
            details.append(f"actions refreshed ({len(new_splits)} split(s), {len(dividends)} dividend(s))")
        else:
            details.append("actions fresh")
        splits = actions.load_splits(leg["symbol"])
    else:
        price_basis = "split_adjusted"

    if w.inverted:
        bars: list[dict] = []
        details.append(_inverted_text(w))
    else:
        bars = collector.get_eod(leg["symbol"], start=w.start, end=w.end)
        limit = getattr(collector, "limit", None)
        if not w.established and leg["start"] is None and limit and len(bars) == limit:
            details.append(
                f"WARNING: first fill without a declared start returned exactly the page limit "
                f"({limit} bars); this may be only a trailing provider slice - declare a start "
                "and rebuild the partition if full history is required"
            )

    revisions = store.reconcile_bars(
        leg["exchange"], leg["symbol"], bars, asset_type=leg["asset_type"], currency=leg["currency"],
        price_basis=price_basis, splits=splits,
        volume_basis=getattr(collector, "VOLUME_BASIS", "raw"),
    )
    if price_basis == "raw" and store.has_rows(leg["exchange"], leg["symbol"]):
        if store.reapply_adjustment(leg["exchange"], leg["symbol"], splits):
            details.append("re-derived from raw")
    return LegResult(leg, True, "; ".join(details), rows=len(bars), revisions=revisions)


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return repr(value)
    return str(value)


def run_sync(universe: dict, store: str | Path | None = None, *, assets=None, providers=None,
             dry_run: bool = False, tail: int = DEFAULT_TAIL, force_actions: bool = False,
             now: _dt.datetime | None = None, eodhd_collector=None, binance_collector=None,
             out: Callable[[str], Any] | None = print) -> tuple[list[LegResult], bool]:
    """Run (or, with `dry_run`, plan) the selected legs. Returns `(results, ok)`."""
    if out is None:
        out = lambda _line: None  # noqa: E731
    if tail < 1:
        raise SyncError(f"tail must be at least 1 (got {tail})")
    legs = select_legs(universe, assets, providers)
    now = _utc(now)
    store_root = Path(store) if store is not None else Path(universe["defaults"]["store"])

    from jef_data_rc.store import ParquetStore

    pstore = ParquetStore(store_root)

    if dry_run:
        results = []
        for leg in legs:
            plan = _plan(pstore, leg, tail, now)
            out(f"plan   {leg_label(leg)}: {plan}")
            results.append(LegResult(leg, True, plan))
        out(f"dry run: {len(legs)} leg(s) planned, nothing fetched or written -> store {store_root}")
        return results, True

    injected = {"eodhd": eodhd_collector, "binance": binance_collector}
    constructed: dict[str, Any] = {}

    def collector_for(provider: str):
        if injected.get(provider) is not None:
            return injected[provider]
        if provider not in constructed:
            constructed[provider] = _make_collector(provider)
        return constructed[provider]

    results: list[LegResult] = []
    try:
        for leg in legs:
            try:
                res = _run_leg(pstore, leg, tail=tail, force_actions=force_actions, now=now,
                               collector_for=collector_for)
            except Exception as exc:  # each leg's failure is contained
                res = LegResult(leg, False, f"{type(exc).__name__}: {exc}")
                out(f"FAILED {leg_label(leg)}: {res.detail}")
            else:
                line = f"ok     {leg_label(leg)}: {res.rows} row(s), {len(res.revisions)} revision(s)"
                if res.detail:
                    line += f"; {res.detail}"
                out(line)
                for rev in res.revisions[:MAX_REVISIONS_SHOWN]:
                    out(f"       revised {rev['date']} {rev['column']}: "
                        f"{_fmt(rev['stored'])} -> {_fmt(rev['served'])}")
                if len(res.revisions) > MAX_REVISIONS_SHOWN:
                    out(f"       ... {len(res.revisions) - MAX_REVISIONS_SHOWN} more revision(s)")
            results.append(res)
    finally:
        for collector in constructed.values():
            try:
                collector.close()
            except Exception:
                pass
    failed = sum(1 for r in results if not r.ok)
    out(f"{len(results)} leg(s), {failed} failed -> store {store_root}")
    return results, failed == 0


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def sync_summary(results: list[LegResult], ok: bool) -> dict:
    """The JSON document `sync --summary-json` writes."""
    legs = []
    for r in results:
        legs.append({
            "asset": r.leg["asset"],
            "provider": r.leg["provider"],
            "exchange": r.leg["exchange"],
            "symbol": r.leg["symbol"],
            "ok": r.ok,
            "detail": r.detail,
            "rows": r.rows,
            "revised_cells": len(r.revisions),
            "revisions": [
                {k: _json_safe(v) for k, v in rev.items()} for rev in r.revisions
            ],
        })
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "ok": bool(ok),
        "legs_total": len(results),
        "legs_failed": sum(1 for r in results if not r.ok),
        "revised_cells_total": sum(len(r.revisions) for r in results),
        "legs": legs,
    }
