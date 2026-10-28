"""Offline, read-only health checks over the local store.

Severity contract: an ALERT (modeled-feed integrity or freshness, or a
spread breach explicitly promoted) makes `status` exit 1; WARNINGS
(classification disagreement, ordinary cross-venue spread breach) and NOTES
(measurements, historical-series characteristics) never change the exit code.
Nothing here fetches, repairs or writes.
"""

from __future__ import annotations

import datetime as _dt
import itertools
from typing import Iterable

import numpy as np
import pandas as pd

WEEKDAY_TYPES = frozenset({"stock", "etf"})

DEFAULT_WINDOW = 10
DEFAULT_JUMP_THRESHOLD = 0.40
DEFAULT_STALENESS_K = 2
DEFAULT_RESOLUTION_WINDOW = 500
DEFAULT_RESOLUTION_K = 0.20
DEFAULT_FLAT_K = 0.25
DEFAULT_GAP_K = 5
DEFAULT_SPREAD_THRESHOLD = 0.005
DEFAULT_ACTIONS_MISSED_K = 2
RESOLUTION_MIN_SESSIONS = 60
STATUS_SCHEMA_VERSION = 1

NEVER_FILLED = "never filled - no stored rows (jef-data sync first)"


def _as_date(value) -> _dt.date:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    return _dt.date.fromisoformat(str(value)[:10])


def expected_sessions_between(asset_type: str, last, today) -> list[_dt.date]:
    """Expected session dates strictly between `last` and `today`.

    Stocks and ETFs expect weekdays (no holiday calendar); every other type
    expects every calendar day.
    """
    last = _as_date(last)
    today = _as_date(today)
    days = []
    d = last + _dt.timedelta(days=1)
    weekdays_only = asset_type in WEEKDAY_TYPES
    while d < today:
        if not weekdays_only or d.weekday() < 5:
            days.append(d)
        d += _dt.timedelta(days=1)
    return days


def _count_between(asset_type: str, a: _dt.date, b: _dt.date) -> int:
    if b <= a:
        return 0
    if asset_type in WEEKDAY_TYPES:
        return int(np.busday_count(a + _dt.timedelta(days=1), b))
    return (b - a).days - 1


def _dates(df: pd.DataFrame) -> list[str]:
    return list(pd.to_datetime(df["datetime"], utc=True).dt.strftime("%Y-%m-%d"))


def _label(leg: dict) -> str:
    return f"{leg['exchange']}/{leg['symbol']}"


def _utc_now(now: _dt.datetime | None) -> _dt.datetime:
    if now is None:
        return _dt.datetime.now(_dt.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=_dt.timezone.utc)
    return now.astimezone(_dt.timezone.utc)


def _zero_volume(df: pd.DataFrame, dates: list[str]) -> str | None:
    zero = (df["volume"].to_numpy(dtype="float64") == 0)
    count = int(zero.sum())
    if not count:
        return None
    best_len, best_start, run_len, run_start = 0, 0, 0, 0
    for i, z in enumerate(zero):
        if z:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    text = f"zero-volume rows: {count}"
    if best_len > 1:
        text += (f"; longest consecutive run {best_len} row(s) "
                 f"{dates[best_start]}..{dates[best_start + best_len - 1]} "
                 "(the seam drops them together: one splice)")
    return text


def _seam_gap(df: pd.DataFrame, dates: list[str], asset_type: str, gap_k: int) -> str | None:
    volume = df["volume"].to_numpy(dtype="float64")
    close = df["close"].to_numpy(dtype="float64")
    keep = (volume > 0) & ~np.isnan(close)
    survivors = [_as_date(d) for d, k in zip(dates, keep) if k]
    best, at = 0, None
    for a, b in zip(survivors, survivors[1:]):
        gap = _count_between(asset_type, a, b)
        if gap > best:
            best, at = gap, (a, b)
    if at is not None and best >= gap_k:
        return (f"post-seam gap: {best} expected session(s) absent between "
                f"{at[0].isoformat()} and {at[1].isoformat()} after the seam drops "
                f"zero-volume/null rows (note at {gap_k})")
    return None


def _resolution(df: pd.DataFrame, resolution_window: int) -> dict | None:
    traded = df[df["volume"].to_numpy(dtype="float64") > 0]
    raw = traded["close_raw"].to_numpy(dtype="float64") if "close_raw" in traded else np.array([])
    usable = ~np.isnan(raw) & (raw > 0) if raw.size else np.array([], dtype=bool)
    if usable.any():
        basis, values = "close_raw", raw[usable]
    else:
        main = traded["close"].to_numpy(dtype="float64")
        basis, values = "close", main[~np.isnan(main) & (main > 0)]
    values = values[-resolution_window:] if resolution_window > 0 else values[:0]
    n = int(values.size)
    if n < RESOLUTION_MIN_SESSIONS:
        return None
    distinct_values = np.unique(values)
    distinct = int(distinct_values.size)
    steps = np.diff(distinct_values) / distinct_values[:-1]
    min_step = float(steps.min()) if steps.size else None
    flat = float(np.count_nonzero(values[1:] == values[:-1]) / (n - 1))
    return {
        "basis": basis,
        "sessions": n,
        "distinct": distinct,
        "distinct_ratio": distinct / n,
        "min_step": min_step,
        "flat_share": flat,
    }


def check_source(store, leg: dict, *, now: _dt.datetime | None = None, evidence: dict | None = None,
                 window: int = DEFAULT_WINDOW, jump_threshold: float = DEFAULT_JUMP_THRESHOLD,
                 staleness_k: int = DEFAULT_STALENESS_K,
                 resolution_window: int = DEFAULT_RESOLUTION_WINDOW,
                 resolution_k: float = DEFAULT_RESOLUTION_K, flat_k: float = DEFAULT_FLAT_K,
                 gap_k: int = DEFAULT_GAP_K, actions_missed_k: int = DEFAULT_ACTIONS_MISSED_K) -> dict:
    """Per-source health report for one live leg."""
    from jef_data_rc.actions import ActionsStore, stamp_date
    from jef_data_rc.classification import DISAGREE, compare, describe, load_classifications

    today = _utc_now(now).date()
    report: dict = {
        "asset": leg["asset"],
        "exchange": leg["exchange"],
        "symbol": leg["symbol"],
        "alerts": [],
        "warnings": [],
        "notes": [],
    }
    if leg["provider"] == "eodhd":
        if evidence is None:
            evidence = load_classifications()
        check = compare(evidence, leg["exchange"], leg["symbol"], leg["asset_type"])
        report["declared_class_check"] = check
        text = describe(check, leg["exchange"], leg["symbol"])
        (report["warnings"] if check["verdict"] == DISAGREE else report["notes"]).append(text)

    df = store.load(leg["exchange"], leg["symbol"])
    if df.empty:
        report["alerts"].append(NEVER_FILLED)
        return report

    dates = _dates(df)
    last = dates[-1]
    missed = expected_sessions_between(leg["asset_type"], last, today)
    report["last_session"] = last
    report["missed_sessions"] = len(missed)
    report["rows"] = int(len(df))
    if len(missed) >= staleness_k:
        report["alerts"].append(
            f"stale: {len(missed)} expected session(s) missed since {last} (alert at {staleness_k}); "
            "verify a multi-day market holiday before acting"
        )
    if last == today.isoformat():
        report["notes"].append(
            f"latest session {last} is dated today: possibly a pre-close/intraday serve "
            "that the next tail refresh replaces"
        )

    zero = _zero_volume(df, dates)
    if zero:
        report["notes"].append(zero)
    seam = _seam_gap(df, dates, leg["asset_type"], gap_k)
    if seam:
        report["notes"].append(seam)
    res = _resolution(df, resolution_window)
    if res is not None:
        report["resolution"] = res
        if res["distinct_ratio"] < resolution_k or res["flat_share"] > flat_k:
            step = "n/a" if res["min_step"] is None else f"{res['min_step']:.6g}"
            report["notes"].append(
                f"coarse price resolution ({res['basis']}): {res['distinct']} distinct close(s) over "
                f"{res['sessions']} traded session(s) (ratio {res['distinct_ratio']:.3f}, note below "
                f"{resolution_k}), flat share {res['flat_share']:.3f} (note above {flat_k}), "
                f"smallest step {step} - review before modelling"
            )

    actions = ActionsStore(store.root)
    split_dates = {s.date for s in actions.load_splits(leg["symbol"])}
    recent = df.tail(window) if window > 0 else df.iloc[0:0]
    closes = recent["close"].to_numpy(dtype="float64")
    recent_dates = dates[len(dates) - len(recent):]
    for i in range(1, len(closes)):
        prev, cur = closes[i - 1], closes[i]
        if not np.isfinite(prev) or prev == 0 or not np.isfinite(cur):
            continue
        ret = (cur - prev) / prev
        if abs(ret) > jump_threshold and recent_dates[i] not in split_dates:
            report["alerts"].append(
                f"phantom-split-shaped jump: close {ret:+.2%} on {recent_dates[i]} "
                f"(threshold {jump_threshold:.0%}) with no split saved for that day"
            )

    if leg.get("actions"):
        stamp = actions.last_updated(leg["symbol"])
        stamped = stamp_date(stamp)
        if stamped is None:
            report["alerts"].append(
                "corporate actions never refreshed: no split-file last_updated stamp (jef-data sync first)"
            )
        else:
            missed_refresh = expected_sessions_between(leg["asset_type"], stamped, today)
            if len(missed_refresh) >= actions_missed_k:
                report["alerts"].append(
                    f"corporate actions stale: {len(missed_refresh)} refresh session(s) missed since "
                    f"{stamped.isoformat()} (alert at {actions_missed_k})"
                )
    return report


def check_cross_venue(store, leg_a: dict, leg_b: dict, *, window: int = DEFAULT_WINDOW,
                      threshold: float = DEFAULT_SPREAD_THRESHOLD,
                      promote_to_alert: bool = False) -> dict:
    """Close spread of two live feeds of one asset on their newest common session."""
    pair: dict = {
        "kind": "cross_venue",
        "asset": leg_a["asset"],
        "a": _label(leg_a),
        "b": _label(leg_b),
        "common_session": None,
        "spread": None,
        "threshold": threshold,
        "alerts": [],
        "warnings": [],
        "notes": [],
    }
    fa = store.load(leg_a["exchange"], leg_a["symbol"])
    fb = store.load(leg_b["exchange"], leg_b["symbol"])
    missing = [lbl for lbl, f in ((pair["a"], fa), (pair["b"], fb)) if f.empty]
    if missing:
        pair["notes"].append(f"spread not measured: no stored rows for {', '.join(missing)}")
        return pair
    ta = fa.tail(window) if window > 0 else fa.iloc[0:0]
    tb = fb.tail(window) if window > 0 else fb.iloc[0:0]
    da, db = _dates(ta), _dates(tb)
    common = sorted(set(da) & set(db))
    if not common:
        pair["notes"].append(
            f"spread not measured: no common session in the newest {window} row(s) of each feed "
            "- check staleness"
        )
        return pair
    day = common[-1]
    pair["common_session"] = day
    ca = float(ta["close"].to_numpy(dtype="float64")[da.index(day)])
    cb = float(tb["close"].to_numpy(dtype="float64")[db.index(day)])
    if (ca + cb) / 2 == 0:
        pair["notes"].append(f"spread not measured: zero midpoint on {day}")
        return pair
    spread = abs(ca - cb) / ((ca + cb) / 2)
    pair["spread"] = spread
    pair["notes"].append(
        f"spread {spread:.4%} on {day}: {pair['a']} close {ca:g} vs {pair['b']} close {cb:g}"
    )
    if spread > threshold:
        text = (f"cross-venue spread {spread:.4%} exceeds {threshold:.4%} on {day}: a feed may be "
                "wrong or a venue distressed (not a trading signal)")
        (pair["alerts"] if promote_to_alert else pair["warnings"]).append(text)
    return pair


def build_status(universe: dict, store_path=None, *, assets=None, providers=None,
                 now: _dt.datetime | None = None, window: int = DEFAULT_WINDOW,
                 jump_threshold: float = DEFAULT_JUMP_THRESHOLD, staleness_k: int = DEFAULT_STALENESS_K,
                 resolution_window: int = DEFAULT_RESOLUTION_WINDOW,
                 resolution_k: float = DEFAULT_RESOLUTION_K, flat_k: float = DEFAULT_FLAT_K,
                 gap_k: int = DEFAULT_GAP_K, spread_threshold: float = DEFAULT_SPREAD_THRESHOLD,
                 spread_alerts: bool = False) -> tuple[dict, int]:
    """The `status --json` envelope and the exit code (1 iff any alert)."""
    from pathlib import Path

    from jef_data_rc.classification import load_classifications
    from jef_data_rc.store import ParquetStore
    from jef_data_rc.sync import select_legs

    legs = select_legs(universe, assets, providers)
    store_root = Path(store_path) if store_path is not None else Path(universe["defaults"]["store"])
    store = ParquetStore(store_root)
    now = _utc_now(now)
    live = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    evidence = load_classifications() if any(l["provider"] == "eodhd" for l in live) else {}
    reports = [
        check_source(store, leg, now=now, evidence=evidence, window=window,
                     jump_threshold=jump_threshold, staleness_k=staleness_k,
                     resolution_window=resolution_window, resolution_k=resolution_k,
                     flat_k=flat_k, gap_k=gap_k)
        for leg in live
    ]
    by_asset: dict[str, list[dict]] = {}
    for leg in live:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset_legs in by_asset.values():
        if len(asset_legs) < 2:
            continue
        for a, b in itertools.combinations(asset_legs, 2):
            pairs.append(check_cross_venue(store, a, b, window=window, threshold=spread_threshold,
                                           promote_to_alert=spread_alerts))
    alerts_total = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings_total = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    envelope = {
        "schema_version": STATUS_SCHEMA_VERSION,
        "store": str(store_root),
        "reports": reports,
        "pairs": pairs,
        "alerts_total": alerts_total,
        "warnings_total": warnings_total,
    }
    return envelope, (1 if alerts_total else 0)


def _lead(item: dict) -> str:
    if item["alerts"]:
        return "ALERT"
    if item["warnings"]:
        return "WARN"
    return "ok"


def _findings(item: dict) -> Iterable[str]:
    for a in item["alerts"]:
        yield f"      ALERT: {a}"
    for w in item["warnings"]:
        yield f"      WARN: {w}"
    for n in item["notes"]:
        yield f"      note: {n}"


def render_text(envelope: dict) -> str:
    lines = [f"store: {envelope['store']}"]
    for r in envelope["reports"]:
        head = f"{_lead(r):<5} {r['asset']:<6} {r['exchange']}/{r['symbol']}"
        if "last_session" in r:
            head += f"  last {r['last_session']}  missed {r['missed_sessions']}  rows {r['rows']}"
        else:
            head += "  no rows"
        lines.append(head)
        res = r.get("resolution")
        if res is not None:
            step = "n/a" if res["min_step"] is None else f"{res['min_step']:.6g}"
            lines.append(
                f"      resolution ({res['basis']}): {res['sessions']} session(s), "
                f"{res['distinct']} distinct ({res['distinct_ratio']:.3f}), "
                f"flat share {res['flat_share']:.3f}, smallest step {step}"
            )
        lines.extend(_findings(r))
    for p in envelope["pairs"]:
        spread = "n/a" if p["spread"] is None else f"{p['spread']:.4%}"
        lines.append(
            f"{_lead(p):<5} {p['asset']:<6} {p['a']} vs {p['b']}  "
            f"session {p['common_session'] or 'n/a'}  spread {spread}  threshold {p['threshold']:.4%}"
        )
        lines.extend(_findings(p))
    summary = f"{len(envelope['reports'])} source(s)"
    if envelope["pairs"]:
        summary += f", {len(envelope['pairs'])} venue pair(s)"
    summary += f": {envelope['alerts_total']} alert(s), {envelope['warnings_total']} warning(s)"
    lines.append(summary)
    return "\n".join(lines)
