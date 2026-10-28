"""The configured batch acquisition path behind ``sync``.

The validated universe is expanded into independent asset/source legs. Per
leg:

* ``yahoo-csv`` imports its whole committed file (overwrite, pre-adjusted);
* collector legs compute a fetch window from local state - the source
  ``start`` floors only a first fill, an established series re-fetches the
  oldest of its newest ``tail`` sessions onward, ``end`` caps every fetch,
  and declared crypto is further capped at the previous completed UTC day;
* a raw-basis EODHD leg (declared type not crypto) refreshes corporate
  actions before bars (once per UTC day unless forced), reconciles the
  window, then re-derives the whole stored series from raw values and
  splits; crypto EODHD and Binance are stored split-adjusted.

A failed leg is recorded and later legs still run; the batch is ``ok`` only
when no leg failed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from jef_data_rc import actions as _actions
from jef_data_rc.store import ParquetStore
from jef_data_rc.universe import PROVIDERS

DEFAULT_TAIL = 10
SUMMARY_SCHEMA_VERSION = 1
MAX_ECHOED_REVISIONS = 10


class SyncError(ValueError):
    """Invalid selection or options; raised before any leg runs."""


@dataclass
class LegResult:
    leg: dict
    ok: bool
    detail: str
    revisions: list = field(default_factory=list)
    bars: int = 0

    @property
    def label(self) -> str:
        return _leg_label(self.leg)


@dataclass
class Window:
    start: date | None
    end: date | None
    has_rows: bool
    guard: date | None
    inverted: bool


def _leg_label(leg: dict) -> str:
    return f"{leg['asset']} {leg['provider']} {leg['exchange']}:{leg['symbol']}"


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def select_legs(universe: dict, assets=None, providers=None) -> list[dict]:
    """Every enabled source of every selected enabled asset, in declared order."""
    names = [a["name"] for a in universe["assets"]]
    if assets:
        unknown = [a for a in assets if a not in names]
        if unknown:
            raise SyncError(
                f"unknown asset(s): {', '.join(unknown)} "
                f"(declared: {', '.join(names)})"
            )
    if providers:
        unknown = [p for p in providers if p not in PROVIDERS]
        if unknown:
            raise SyncError(
                f"unknown provider(s): {', '.join(unknown)} "
                f"(supported: {', '.join(PROVIDERS)})"
            )
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
            legs.append(
                {
                    "asset": asset["name"],
                    "provider": source["provider"],
                    "exchange": source["exchange"],
                    "symbol": source["symbol"],
                    "asset_type": asset["asset_type"],
                    "currency": source["currency"],
                    "start": source["start"],
                    "end": source["end"],
                    "path": source["path"],
                    "actions": (
                        source["provider"] == "eodhd"
                        and asset["asset_type"] != "crypto"
                    ),
                }
            )
    if not legs:
        raise SyncError("the selection matches no enabled legs")
    return legs


def _window(store: ParquetStore, leg: dict, tail: int, now: datetime) -> Window:
    recent = store.recent_dates(leg["exchange"], leg["symbol"], tail)
    has_rows = bool(recent)
    start = recent[0] if has_rows else _as_date(leg["start"])
    end = _as_date(leg["end"])
    guard = None
    if leg["asset_type"] == "crypto":
        guard = now.date() - timedelta(days=1)
        end = guard if end is None else min(end, guard)
    inverted = has_rows and end is not None and start > end
    return Window(start=start, end=end, has_rows=has_rows, guard=guard, inverted=inverted)


def _inverted_detail(window: Window) -> str:
    return (
        f"inverted window: stored tail starts {window.start.isoformat()} after "
        f"the pinned end {window.end.isoformat()} - no fetch (review the "
        "declared end)"
    )


def _plan_line(store: ParquetStore, leg: dict, tail: int, now: datetime) -> str:
    label = _leg_label(leg)
    if leg["provider"] == "yahoo-csv":
        return f"{label}: import-csv {leg['path']} (whole file, overwrite)"
    window = _window(store, leg, tail, now)
    action = "sync-actions + load" if leg["actions"] else "load"
    if window.has_rows:
        span = f"reconcile tail of {tail} session(s) from {window.start.isoformat()}"
    elif window.start is not None:
        span = f"first fill from {window.start.isoformat()}"
    else:
        span = "first fill from the provider's earliest bar"
    span += f" to {window.end.isoformat()}" if window.end is not None else " to latest"
    extras = []
    if leg["end"] is not None:
        extras.append(f"pinned end {leg['end']}")
    if window.guard is not None:
        extras.append(f"crypto completed-day guard {window.guard.isoformat()}")
    line = f"{label}: {action} {span}"
    if extras:
        line += f" ({'; '.join(extras)})"
    if window.inverted:
        line += f" - {_inverted_detail(window)}"
    return line


def _run_leg(store, leg, collector_for, tail, force_actions, now) -> LegResult:
    exchange, symbol = leg["exchange"], leg["symbol"]
    if leg["provider"] == "yahoo-csv":
        rows = store.ingest_yahoo_csv(
            leg["path"],
            exchange=exchange,
            symbol=symbol,
            asset_type=leg["asset_type"],
            currency=leg["currency"],
        )
        return LegResult(leg, True, f"imported {rows} row(s) from {leg['path']}", [], rows)

    collector = collector_for(leg["provider"])
    window = _window(store, leg, tail, now)
    parts = []
    splits = []
    if leg["actions"]:
        price_basis = "raw"
        stamp = _actions.last_updated(store.base, symbol)
        stale = stamp is None
        if not stale:
            try:
                stale = _actions.stamp_date(stamp) < now.date()
            except ValueError:
                stale = True
        if force_actions or stale:
            got_splits, got_divs = _actions.sync_actions(
                collector, store.base, symbol, exchange=exchange, now=now
            )
            parts.append(
                f"actions refreshed ({len(got_splits)} split(s), "
                f"{len(got_divs)} dividend(s))"
            )
        else:
            parts.append("actions fresh")
        splits = _actions.load_splits(store.base, symbol)
    else:
        price_basis = "split_adjusted"

    if window.inverted:
        parts.append(_inverted_detail(window))
        bars = []
    else:
        bars = collector.get_eod(symbol, start=window.start, end=window.end)
        limit = getattr(collector, "page_limit", None)
        if not window.has_rows and leg["start"] is None and limit and len(bars) == limit:
            parts.append(
                f"WARNING: unbounded first fill returned exactly {limit} bars "
                "(the page limit) - possibly only a trailing provider slice; "
                "declare a start and rebuild for full history"
            )
    revisions = store.reconcile_bars(
        exchange,
        symbol,
        bars,
        asset_type=leg["asset_type"],
        currency=leg["currency"],
        price_basis=price_basis,
        volume_basis=getattr(collector, "VOLUME_BASIS", "raw"),
        splits=splits,
    )
    parts.append(f"{len(bars)} bar(s), {len(revisions)} revised cell(s)")
    if price_basis == "raw" and store.latest_date(exchange, symbol) is not None:
        if store.reapply_adjustment(exchange, symbol, splits):
            parts.append("re-derived from raw")
    return LegResult(leg, True, "; ".join(parts), revisions, len(bars))


def _construct(provider: str):
    if provider == "eodhd":
        from jef_data_rc.collectors.eodhd import EODHDCollector

        return EODHDCollector()
    if provider == "binance":
        from jef_data_rc.collectors.binance import BinanceCollector

        return BinanceCollector()
    raise SyncError(f"no collector for provider {provider!r}")


def _discard(_line: str) -> None:
    return None


def run_sync(
    universe: dict,
    *,
    store=None,
    assets=None,
    providers=None,
    tail: int = DEFAULT_TAIL,
    force_actions: bool = False,
    dry_run: bool = False,
    eodhd_collector=None,
    binance_collector=None,
    now: datetime | None = None,
    out=print,
) -> tuple[list[LegResult], bool]:
    legs = select_legs(universe, assets, providers)
    if tail < 1:
        raise SyncError(f"--tail must be at least 1 (got {tail})")
    store_path = store if store is not None else universe["defaults"]["store"]
    pstore = store if isinstance(store, ParquetStore) else ParquetStore(store_path)
    now = _utc_now(now)
    out = out or _discard

    if dry_run:
        for leg in legs:
            out(_plan_line(pstore, leg, tail, now))
        out(f"dry run: {len(legs)} leg(s) planned, nothing fetched or written -> store {pstore.base}")
        return [], True

    injected = {"eodhd": eodhd_collector, "binance": binance_collector}
    constructed: dict = {}

    def collector_for(provider: str):
        if injected.get(provider) is not None:
            return injected[provider]
        if provider not in constructed:
            constructed[provider] = _construct(provider)
        return constructed[provider]

    results: list[LegResult] = []
    try:
        for leg in legs:
            try:
                result = _run_leg(pstore, leg, collector_for, tail, force_actions, now)
            except Exception as exc:  # contained per leg; the batch goes red
                result = LegResult(leg, False, f"{type(exc).__name__}: {exc}", [])
            results.append(result)
            if result.ok:
                out(f"ok     {result.label}: {result.detail}")
                for rev in result.revisions[:MAX_ECHOED_REVISIONS]:
                    out(
                        f"       revised {rev['date']} {rev['column']}: "
                        f"{rev['stored']} -> {rev['served']}"
                    )
                hidden = len(result.revisions) - MAX_ECHOED_REVISIONS
                if hidden > 0:
                    out(f"       ... {hidden} more revised cell(s) in the summary")
            else:
                out(f"FAILED {result.label}: {result.detail}")
    finally:
        for collector in constructed.values():
            try:
                collector.close()
            except Exception:
                pass
    failed = sum(1 for r in results if not r.ok)
    out(f"{len(results)} leg(s), {failed} failed -> store {pstore.base}")
    return results, failed == 0


def sync_summary(results, ok: bool) -> dict:
    """The JSON-safe document ``sync --summary-json`` writes."""
    legs = []
    for result in results:
        legs.append(
            {
                "asset": result.leg["asset"],
                "provider": result.leg["provider"],
                "exchange": result.leg["exchange"],
                "symbol": result.leg["symbol"],
                "ok": bool(result.ok),
                "detail": result.detail,
                "revised_cells": len(result.revisions),
                "revisions": [dict(r) for r in result.revisions],
            }
        )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "legs": len(results),
        "failed": sum(1 for r in results if not r.ok),
        "revised_cells": sum(len(r.revisions) for r in results),
        "ok": bool(ok),
        "results": legs,
    }


def load_symbol(
    store: ParquetStore,
    collector,
    symbol: str,
    *,
    exchange: str = "eodhd",
    asset_type: str,
    currency: str = "USD",
    start=None,
    end=None,
) -> int:
    """Manual incremental EODHD load (append; first stored row wins).

    Without ``start`` an established series resumes the day after its latest
    stored session. A raw-basis series is re-derived afterwards.
    """
    price_basis = "split_adjusted" if asset_type == "crypto" else "raw"
    start = _as_date(start)
    if start is None:
        latest = store.latest_date(exchange, symbol)
        if latest is not None:
            start = latest + timedelta(days=1)
    splits = _actions.load_splits(store.base, symbol) if price_basis == "raw" else []
    bars = collector.get_eod(symbol, start=start, end=_as_date(end))
    store.ingest(
        bars,
        exchange=exchange,
        symbol=symbol,
        asset_type=asset_type,
        currency=currency,
        price_basis=price_basis,
        volume_basis=getattr(collector, "VOLUME_BASIS", "raw"),
        splits=splits,
        mode="append",
    )
    if price_basis == "raw" and store.latest_date(exchange, symbol) is not None:
        store.reapply_adjustment(exchange, symbol, splits)
    return len(bars)
