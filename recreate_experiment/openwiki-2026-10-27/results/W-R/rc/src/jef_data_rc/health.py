"""Offline, read-only health of the local EOD store.

Severity contract: an **alert** makes ``status`` exit 1; **warnings** and
**notes** stay visible but exit 0. Model-feed integrity and freshness are
alerts; classification disagreement and a cross-venue spread breach are
warnings (a breach becomes an alert only when promotion is requested);
series characteristics are notes.

All timing uses the current UTC date. Expected sessions are counted strictly
between the last stored date and today: weekdays for ``stock``/``etf``,
every calendar day for every other type. There is no holiday calendar.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from itertools import combinations

import numpy as np
import pandas as pd

from jef_data_rc import actions as _actions
from jef_data_rc import classification as _classification

SCHEMA_VERSION = 1
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

NEVER_FILLED = "never filled - no stored rows (jef-data sync first)"


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def expected_sessions_between(asset_type: str, last: date, today: date) -> list[date]:
    """Expected session dates strictly between ``last`` and ``today``."""
    out = []
    day = last + timedelta(days=1)
    weekday_only = asset_type in WEEKDAY_TYPES
    while day < today:
        if not weekday_only or day.weekday() < 5:
            out.append(day)
        day += timedelta(days=1)
    return out


def count_expected_sessions(asset_type: str, last: date, today: date) -> int:
    """``len(expected_sessions_between(...))`` without building the list."""
    if today <= last + timedelta(days=1):
        return 0
    if asset_type in WEEKDAY_TYPES:
        return int(
            np.busday_count(
                np.datetime64(last + timedelta(days=1), "D"),
                np.datetime64(today, "D"),
            )
        )
    return (today - last).days - 1


def _gap_counts(asset_type: str, days: np.ndarray) -> np.ndarray:
    """Expected sessions strictly between each adjacent pair of dates."""
    if len(days) < 2:
        return np.zeros(0, dtype="int64")
    begin = days[:-1] + np.timedelta64(1, "D")
    end = days[1:]
    if asset_type in WEEKDAY_TYPES:
        counts = np.busday_count(begin, end)
    else:
        counts = (end - begin).astype("int64")
    return np.maximum(counts, 0)


def _days(frame: pd.DataFrame) -> np.ndarray:
    moments = frame["datetime"]
    if isinstance(moments.dtype, pd.DatetimeTZDtype):
        moments = moments.dt.tz_convert("UTC").dt.tz_localize(None)
    return moments.to_numpy().astype("datetime64[D]")


def _iso(day) -> str:
    return str(np.datetime64(day, "D"))


def _label(leg: dict) -> str:
    return f"{leg['exchange']}:{leg['symbol']}"


def _zero_volume_note(volume: np.ndarray, days: np.ndarray) -> str | None:
    zero = volume == 0
    n_zero = int(zero.sum())
    if not n_zero:
        return None
    best_len, best_start, run_len, run_start = 0, 0, 0, 0
    for i, flag in enumerate(zero):
        if flag:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    text = f"{n_zero} zero-volume row(s), dropped at the seam"
    if best_len > 1:
        text += (
            f"; longest consecutive run {best_len} rows "
            f"{_iso(days[best_start])}..{_iso(days[best_start + best_len - 1])} "
            "(one splice)"
        )
    return text


def _post_seam_gap(frame: pd.DataFrame, days: np.ndarray, asset_type: str):
    volume = frame["volume"].to_numpy(dtype="float64")
    close = frame["close"].to_numpy(dtype="float64")
    keep = (volume > 0) & ~np.isnan(close)
    survivors = days[keep]
    gaps = _gap_counts(asset_type, survivors)
    if not len(gaps):
        return None
    i = int(np.argmax(gaps))
    return int(gaps[i]), survivors[i], survivors[i + 1]


def price_resolution(frame: pd.DataFrame, window: int) -> dict | None:
    """Distinct closes, smallest relative step and flat share, or None."""
    volume = frame["volume"].to_numpy(dtype="float64")
    traded = volume > 0
    raw = frame["close_raw"].to_numpy(dtype="float64") if "close_raw" in frame else None
    prices = None
    basis = None
    if raw is not None:
        usable = traded & ~np.isnan(raw) & (raw > 0)
        if usable.any():
            prices, basis = raw[usable], "close_raw"
    if prices is None:
        main = frame["close"].to_numpy(dtype="float64")
        usable = traded & ~np.isnan(main) & (main > 0)
        prices, basis = main[usable], "close"
    prices = prices[-window:] if window > 0 else prices[:0]
    sessions = int(len(prices))
    if sessions < RESOLUTION_MIN_SESSIONS:
        return None
    uniq = np.unique(prices)
    distinct = int(len(uniq))
    if distinct > 1:
        min_rel_step = float(np.min(np.diff(uniq) / uniq[:-1]))
    else:
        min_rel_step = None
    flat_share = float(np.count_nonzero(prices[1:] == prices[:-1]) / (sessions - 1))
    return {
        "sessions": sessions,
        "distinct": distinct,
        "distinct_ratio": distinct / sessions,
        "min_rel_step": min_rel_step,
        "flat_share": flat_share,
        "price": basis,
    }


def check_source(
    store,
    leg: dict,
    *,
    now: datetime | None = None,
    window: int = DEFAULT_WINDOW,
    jump_threshold: float = DEFAULT_JUMP_THRESHOLD,
    staleness_k: int = DEFAULT_STALENESS_K,
    resolution_window: int = DEFAULT_RESOLUTION_WINDOW,
    resolution_k: float = DEFAULT_RESOLUTION_K,
    flat_k: float = DEFAULT_FLAT_K,
    gap_k: int = DEFAULT_GAP_K,
    actions_missed_k: int = DEFAULT_ACTIONS_MISSED_K,
    evidence: dict | None = None,
) -> dict:
    """One source leg's report: alerts, warnings, notes and measurements."""
    now = _utc_now(now)
    today = now.date()
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    report = {
        "asset": leg["asset"],
        "exchange": exchange,
        "symbol": symbol,
        "alerts": [],
        "warnings": [],
        "notes": [],
    }

    if leg["provider"] == "eodhd":
        if evidence is None:
            evidence = _classification.load_classifications()
        check = _classification.compare(evidence, exchange, symbol, asset_type)
        report["declared_class_check"] = check
        message = _classification.describe(check, exchange, symbol)
        if check["verdict"] == "disagree":
            report["warnings"].append(message)
        else:
            report["notes"].append(message)

    last = store.latest_date(exchange, symbol)
    if last is None:
        report["alerts"].append(NEVER_FILLED)
        return report

    missed = count_expected_sessions(asset_type, last, today)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    if missed >= staleness_k:
        report["alerts"].append(
            f"stale - {missed} expected session(s) missed since {last.isoformat()} "
            f"(threshold {staleness_k}); verify a multi-day market holiday before "
            "acting"
        )
    if last == today:
        report["notes"].append(
            f"latest session {last.isoformat()} is today (UTC): possibly a "
            "pre-close serve that the next tail refresh replaces"
        )

    frame = store.load(exchange, symbol)
    report["rows"] = int(len(frame))
    days = _days(frame)

    note = _zero_volume_note(frame["volume"].to_numpy(dtype="float64"), days)
    if note:
        report["notes"].append(note)

    gap = _post_seam_gap(frame, days, asset_type)
    if gap is not None and gap[0] >= gap_k:
        report["notes"].append(
            f"post-seam gap: {gap[0]} expected session(s) absent between "
            f"{_iso(gap[1])} and {_iso(gap[2])} (threshold {gap_k})"
        )

    resolution = price_resolution(frame, resolution_window)
    if resolution is not None:
        report["resolution"] = resolution
        coarse = resolution["distinct_ratio"] < resolution_k
        flat = resolution["flat_share"] > flat_k
        if coarse or flat:
            report["notes"].append(
                f"coarse price resolution: {resolution['distinct']} distinct "
                f"close(s) in {resolution['sessions']} session(s) (ratio "
                f"{resolution['distinct_ratio']:.3f}, threshold {resolution_k:g}), "
                f"flat share {resolution['flat_share']:.3f} (threshold {flat_k:g})"
                " - review before modelling"
            )

    splits = _actions.load_splits(store.base, symbol)
    split_days = {s.date for s in splits}
    close = frame["close"].to_numpy(dtype="float64")
    start = max(1, len(close) - window)
    for i in range(start, len(close)):
        prev, cur = close[i - 1], close[i]
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = cur / prev - 1.0
        if not np.isfinite(ret) or not abs(ret) > jump_threshold:
            continue
        day = date.fromisoformat(_iso(days[i]))
        if day in split_days:
            continue
        report["alerts"].append(
            f"phantom split? close moved {ret:+.2%} on {day.isoformat()} with no "
            f"same-day split saved (threshold {jump_threshold:g}); check the "
            "action record and provider history"
        )

    if leg.get("actions"):
        stamp = _actions.last_updated(store.base, symbol)
        stamp_day = None
        if stamp is not None:
            try:
                stamp_day = _actions.stamp_date(stamp)
            except ValueError:
                stamp_day = None
        if stamp_day is None:
            report["alerts"].append(
                "corporate actions never refreshed - no split-file last_updated "
                "stamp (jef-data sync first)"
            )
        else:
            missed_refresh = count_expected_sessions(asset_type, stamp_day, today)
            if missed_refresh >= actions_missed_k:
                report["alerts"].append(
                    f"corporate actions stale - {missed_refresh} refresh "
                    f"session(s) missed since {stamp_day.isoformat()} (threshold "
                    f"{actions_missed_k})"
                )
    return report


def check_cross_venue(
    store,
    asset: str,
    leg_a: dict,
    leg_b: dict,
    *,
    window: int = DEFAULT_WINDOW,
    threshold: float = DEFAULT_SPREAD_THRESHOLD,
    promote_to_alert: bool = False,
) -> dict:
    """Relative close spread of two stored feeds on their newest common date."""
    label_a, label_b = _label(leg_a), _label(leg_b)
    pair = {
        "kind": "cross_venue",
        "asset": asset,
        "a": label_a,
        "b": label_b,
        "common_session": None,
        "spread": None,
        "threshold": threshold,
        "alerts": [],
        "warnings": [],
        "notes": [],
    }
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((label_a, frame_a), (label_b, frame_b)):
        if not len(frame):
            pair["notes"].append(f"spread not measured - {label} has no stored rows")
            return pair
    recent_a = frame_a.tail(window) if window > 0 else frame_a.iloc[:0]
    recent_b = frame_b.tail(window) if window > 0 else frame_b.iloc[:0]
    days_a = _days(recent_a)
    days_b = _days(recent_b)
    common = np.intersect1d(days_a, days_b)
    if not len(common):
        pair["notes"].append(
            f"spread not measured - no common session in the newest {window} "
            "row(s) of both feeds (check staleness)"
        )
        return pair
    day = common.max()
    pair["common_session"] = _iso(day)
    close_a = float(recent_a["close"].to_numpy(dtype="float64")[days_a == day][-1])
    close_b = float(recent_b["close"].to_numpy(dtype="float64")[days_b == day][-1])
    midpoint = (close_a + close_b) / 2
    if midpoint == 0:
        pair["notes"].append(
            f"spread not measured on {_iso(day)} - zero midpoint "
            f"({label_a} {close_a:g}, {label_b} {close_b:g})"
        )
        return pair
    spread = abs(close_a - close_b) / ((close_a + close_b) / 2)
    pair["spread"] = spread
    pair["notes"].append(
        f"close spread {spread:.4%} on {_iso(day)}: {label_a} {close_a:g} vs "
        f"{label_b} {close_b:g}"
    )
    if spread > threshold:
        message = (
            f"close spread {spread:.4%} exceeds {threshold:.2%} on {_iso(day)} - "
            "a feed may be wrong or a venue distressed (not a trading signal)"
        )
        (pair["alerts"] if promote_to_alert else pair["warnings"]).append(message)
    return pair


def status_report(
    legs: list[dict],
    store,
    *,
    store_label=None,
    now: datetime | None = None,
    window: int = DEFAULT_WINDOW,
    jump_threshold: float = DEFAULT_JUMP_THRESHOLD,
    staleness_k: int = DEFAULT_STALENESS_K,
    resolution_window: int = DEFAULT_RESOLUTION_WINDOW,
    resolution_k: float = DEFAULT_RESOLUTION_K,
    flat_k: float = DEFAULT_FLAT_K,
    gap_k: int = DEFAULT_GAP_K,
    spread_threshold: float = DEFAULT_SPREAD_THRESHOLD,
    spread_alerts: bool = False,
) -> dict:
    """The schema-versioned envelope ``status --json`` prints."""
    now = _utc_now(now)
    live = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    evidence = None
    reports = []
    for leg in live:
        if leg["provider"] == "eodhd" and evidence is None:
            evidence = _classification.load_classifications()
        reports.append(
            check_source(
                store,
                leg,
                now=now,
                window=window,
                jump_threshold=jump_threshold,
                staleness_k=staleness_k,
                resolution_window=resolution_window,
                resolution_k=resolution_k,
                flat_k=flat_k,
                gap_k=gap_k,
                evidence=evidence,
            )
        )
    groups: dict[str, list[dict]] = {}
    for leg in live:
        groups.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, group in groups.items():
        if len(group) < 2:
            continue
        for leg_a, leg_b in combinations(group, 2):
            pairs.append(
                check_cross_venue(
                    store,
                    asset,
                    leg_a,
                    leg_b,
                    window=window,
                    threshold=spread_threshold,
                    promote_to_alert=spread_alerts,
                )
            )
    findings = reports + pairs
    return {
        "schema_version": SCHEMA_VERSION,
        "store": str(store_label if store_label is not None else store.base),
        "reports": reports,
        "pairs": pairs,
        "alerts_total": sum(len(r["alerts"]) for r in findings),
        "warnings_total": sum(len(r["warnings"]) for r in findings),
    }


def status_exit_code(document: dict) -> int:
    return 1 if document["alerts_total"] else 0


def evaluate_status(universe: dict, store_path=None, *, assets=None, providers=None, **knobs):
    """Select legs, evaluate the store, and return ``(document, exit_code)``."""
    from jef_data_rc.store import ParquetStore
    from jef_data_rc.sync import select_legs

    legs = select_legs(universe, assets, providers)
    path = store_path if store_path is not None else universe["defaults"]["store"]
    document = status_report(legs, ParquetStore(path), store_label=path, **knobs)
    return document, status_exit_code(document)


def render_text(document: dict) -> str:
    lines = []
    for report in document["reports"]:
        label = "ALERT" if report["alerts"] else "WARN" if report["warnings"] else "ok"
        head = f"{label:<5} {report['asset']:<6} {report['exchange']}:{report['symbol']}"
        if "last_session" in report:
            head += (
                f"  last {report['last_session']}  missed "
                f"{report['missed_sessions']}  rows {report['rows']}"
            )
        lines.append(head)
        res = report.get("resolution")
        if res is not None:
            step = "n/a" if res["min_rel_step"] is None else f"{res['min_rel_step']:.6f}"
            lines.append(
                f"      resolution: {res['sessions']} sessions, {res['distinct']} "
                f"distinct ({res['distinct_ratio']:.3f}), min step {step}, flat "
                f"{res['flat_share']:.3f}"
            )
        lines += [f"      ALERT: {m}" for m in report["alerts"]]
        lines += [f"      WARN:  {m}" for m in report["warnings"]]
        lines += [f"      note:  {m}" for m in report["notes"]]
    for pair in document["pairs"]:
        label = "ALERT" if pair["alerts"] else "WARN" if pair["warnings"] else "ok"
        head = f"{label:<5} {pair['asset']:<6} {pair['a']} vs {pair['b']}"
        if pair["spread"] is not None:
            head += f"  spread {pair['spread']:.4%} on {pair['common_session']}"
        lines.append(head)
        lines += [f"      ALERT: {m}" for m in pair["alerts"]]
        lines += [f"      WARN:  {m}" for m in pair["warnings"]]
        lines += [f"      note:  {m}" for m in pair["notes"]]
    summary = f"{len(document['reports'])} source(s)"
    if document["pairs"]:
        summary += f", {len(document['pairs'])} venue pair(s)"
    summary += (
        f", {document['alerts_total']} alert(s), "
        f"{document['warnings_total']} warning(s) -> store {document['store']}"
    )
    lines.append(summary)
    return "\n".join(lines)
