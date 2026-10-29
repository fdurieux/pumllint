"""Read-only daily health: per-source checks, venue pairs, the envelope and the table."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np

from . import classification
from .actions import CorporateActionsStore
from .store import ParquetStore
from .sync import select_legs

WEEKDAY_TYPES = ("stock", "etf")
ACTIONS_STALE_SESSIONS = 2
MIN_RESOLUTION_SESSIONS = 60

DEFAULTS = {"window": 10, "jump_threshold": 0.40, "staleness_k": 2, "resolution_window": 500,
            "resolution_k": 0.20, "flat_k": 0.25, "gap_k": 5, "spread_threshold": 0.005,
            "spread_alerts": False}


def expected_sessions(first: date, second: date, asset_type: str) -> int:
    """Sessions strictly after first and strictly before second (no holiday calendar)."""
    begin = first + timedelta(days=1)
    if second <= begin:
        return 0
    if asset_type in WEEKDAY_TYPES:
        return int(np.busday_count(np.datetime64(begin, "D"), np.datetime64(second, "D")))
    return (second - begin).days


def _today(now) -> date:
    clock = now if now is not None else datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    return clock.astimezone(timezone.utc).date()


def _days(frame) -> list:
    return [s.tz_convert("UTC").date() for s in frame["datetime"]]


def _zero_volume_note(volume, days):
    zero = volume == 0
    count = int(zero.sum())
    if not count:
        return None
    best_len, best_start = 0, None
    run_len, run_start = 0, None
    for i, flag in enumerate(zero.tolist()):
        if flag:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    note = f"{count} zero-volume row(s), dropped at the seam by pinned policy"
    if best_len > 1:
        note += (f" - largest contiguous run {best_len}, {days[best_start].isoformat()}.."
                 f"{days[best_start + best_len - 1].isoformat()}")
    return note


def _post_seam_gap(volume, close, days, asset_type):
    keep = [i for i in range(len(days)) if volume[i] > 0 and not np.isnan(close[i])]
    best = None
    for prev, nxt in zip(keep, keep[1:]):
        a, b = days[prev], days[nxt]
        if (b - a).days <= 1:
            continue
        missing = expected_sessions(a, b, asset_type)
        if missing > 0 and (best is None or missing > best[0]):
            best = (missing, a, b)
    return best


def _resolution(frame, volume, window):
    traded = volume > 0

    def series(column):
        values = frame[column].to_numpy(dtype=np.float64)[traded]
        values = values[~np.isnan(values)]
        values = values[values > 0]
        return values[-window:] if window > 0 else values[:0]

    values = series("close_raw")
    if not len(values):
        values = series("close")
    if len(values) < MIN_RESOLUTION_SESSIONS:
        return None
    sessions = len(values)
    distinct_values = sorted(set(values.tolist()))
    distinct = len(distinct_values)
    if distinct > 1:
        min_tick = min((distinct_values[k + 1] - distinct_values[k]) / distinct_values[k]
                       for k in range(distinct - 1))
    else:
        min_tick = None
    flat_pairs = sum(1 for k in range(sessions - 1) if values[k + 1] == values[k])
    flat_share = flat_pairs / (sessions - 1)
    return {"sessions": sessions, "distinct": distinct, "min_tick": min_tick,
            "flat_share": flat_share}


def _tick(min_tick) -> str:
    return "n/a" if min_tick is None else f"{min_tick:.4%}"


def check_source(leg, store, actions, evidence, today, knobs) -> dict:
    report = {"asset": leg["asset"], "exchange": leg["exchange"], "symbol": leg["symbol"],
              "alerts": [], "warnings": [], "notes": []}
    alerts, warnings, notes = report["alerts"], report["warnings"], report["notes"]
    if leg["provider"] == "eodhd":
        verdict, message = classification.compare(evidence, leg["exchange"], leg["symbol"],
                                                  leg["asset_type"])
        report["declared_class_check"] = verdict
        (warnings if verdict == "disagree" else notes).append(f"declared class: {message}")
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    last = store.latest_date(exchange, symbol)
    if last is None:
        alerts.append("never filled - no stored rows (jef-data sync first)")
        return report
    frame = store.load(exchange, symbol)
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    report["rows"] = len(frame)
    days = _days(frame)
    volume = frame["volume"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)

    if missed >= knobs["staleness_k"]:
        alerts.append(f"stale: {missed} expected session(s) missing since {last.isoformat()} "
                      "(multi-day holidays can trip this - verify before acting)")
    if last == today:
        notes.append("today-dated bar stored (pre-close serve? the next tail-refresh heals it)")
    zero_note = _zero_volume_note(volume, days)
    if zero_note:
        notes.append(zero_note)
    gap = _post_seam_gap(volume, close, days, asset_type)
    if gap is not None and gap[0] >= knobs["gap_k"]:
        notes.append(f"post-seam continuity: {gap[0]} expected session(s) absent between "
                     f"{gap[1].isoformat()} and {gap[2].isoformat()} - the seam's output "
                     "splices across this hole; verify the provider era before modelling "
                     "(docs/DATA_CONTRACT.md §1)")
    resolution = _resolution(frame, volume, knobs["resolution_window"])
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < knobs["resolution_k"] or resolution["flat_share"] > knobs["flat_k"]:
            notes.append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick "
                f"{_tick(resolution['min_tick'])}, {resolution['flat_share']:.1%} flat - the "
                "provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8)")
    split_days = set()
    if leg["actions"]:
        split_days = {event.date for event in actions.load_splits(symbol)}
    n = len(frame)
    for i in range(max(1, n - knobs["window"]), n):
        previous = close[i - 1]
        if previous == 0:
            continue
        move = close[i] / previous - 1.0
        if abs(move) > knobs["jump_threshold"] and days[i] not in split_days:
            alerts.append(f"phantom-split-shaped jump {move:+.1%} on {days[i].isoformat()} with "
                          "no same-day split event - check corporate actions "
                          "(docs/DATA_CONTRACT.md §2)")
    if leg["actions"]:
        stamp = actions.last_updated(symbol)
        if stamp is None:
            alerts.append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = stamp.astimezone(timezone.utc).date()
            behind = expected_sessions(stamp_day, today, asset_type)
            if behind >= ACTIONS_STALE_SESSIONS:
                alerts.append(f"corporate actions stale: {behind} refresh session(s) missed "
                              f"since {stamp_day.isoformat()} - run jef-data sync")
    return report


def check_cross_venue(asset, leg_a, leg_b, store, knobs) -> dict:
    a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    threshold = knobs["spread_threshold"]
    pair = {"asset": asset, "kind": "cross_venue", "a": a, "b": b, "common_session": None,
            "spread": None, "threshold": threshold, "alerts": [], "warnings": [], "notes": []}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((a, frame_a), (b, frame_b)):
        if frame.empty:
            pair["notes"].append(f"{label} has no stored rows - spread not measured")
            return pair
    window = knobs["window"]
    tail_a = frame_a.tail(window) if window > 0 else frame_a.iloc[:0]
    tail_b = frame_b.tail(window) if window > 0 else frame_b.iloc[:0]
    days_a = _days(tail_a)
    days_b = _days(tail_b)
    common = set(days_a) & set(days_b)
    if not common:
        pair["notes"].append(f"no common session in the newest {window} - spread not measured "
                             "(see the staleness check)")
        return pair
    day = max(common)
    close_a = float(tail_a["close"].to_numpy(dtype=np.float64)[
        [i for i, d in enumerate(days_a) if d == day][-1]])
    close_b = float(tail_b["close"].to_numpy(dtype=np.float64)[
        [i for i, d in enumerate(days_b) if d == day][-1]])
    mid = (close_a + close_b) / 2
    if mid == 0:
        pair["notes"].append(f"zero mid price on {day.isoformat()} - spread not measured")
        return pair
    spread = abs(close_a - close_b) / mid
    pair["common_session"] = day.isoformat()
    pair["spread"] = spread
    pair["notes"].append(f"close spread {spread:.4%} on {day.isoformat()} "
                         f"({a} {close_a:g} vs {b} {close_b:g})")
    if spread > threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {day.isoformat()} exceeds "
                   f"{threshold:.4%} ({a} {close_a:g} vs {b} {close_b:g}) - feed problem or "
                   "venue distress; verify before acting, never trade it "
                   "(docs/EVALUATION_CROSS_EXCHANGE.md)")
        (pair["alerts"] if knobs["spread_alerts"] else pair["warnings"]).append(finding)
    return pair


def status_report(universe, store_path, *, assets=None, providers=None, now=None, **knobs):
    """The status envelope and the exit code it implies."""
    settings = dict(DEFAULTS)
    settings.update({k: v for k, v in knobs.items() if v is not None})
    legs = [leg for leg in select_legs(universe, assets, providers)
            if leg["provider"] != "yahoo-csv"]
    today = _today(now)
    store_path = str(store_path)
    store = ParquetStore(store_path)
    actions = CorporateActionsStore(store_path)
    evidence = classification.load_packaged()
    reports = [check_source(leg, store, actions, evidence, today, settings) for leg in legs]
    by_asset = {}
    for leg in legs:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, group in by_asset.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pairs.append(check_cross_venue(asset, group[i], group[j], store, settings))
    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    doc = {"schema_version": 1, "store": store_path, "reports": reports, "pairs": pairs,
           "alerts_total": alerts, "warnings_total": warnings}
    return doc, (1 if alerts > 0 else 0)


def _flag(item) -> str:
    if item["alerts"]:
        return "ALERT"
    if item["warnings"]:
        return "WARN "
    return "ok   "


def _messages(item) -> list[str]:
    return ([f"        ALERT {t}" for t in item["alerts"]]
            + [f"        WARN  {t}" for t in item["warnings"]]
            + [f"        note  {t}" for t in item["notes"]])


def render_table(doc) -> list[str]:
    lines = []
    for report in doc["reports"]:
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/"
                     f"{report['symbol']}: last {report.get('last_session', '-')}, "
                     f"{report.get('missed_sessions', '-')} missed, "
                     f"{report.get('rows', 0)} row(s)")
        resolution = report.get("resolution")
        if resolution is not None:
            lines.append(f"        res   {resolution['distinct']} distinct / "
                         f"{resolution['sessions']} traded, min tick "
                         f"{_tick(resolution['min_tick'])}, {resolution['flat_share']:.2%} flat")
        lines.extend(_messages(report))
    for pair in doc["pairs"]:
        lines.append(f"{_flag(pair)} {pair['asset']:>6} cross-venue {pair['a']} vs {pair['b']}")
        lines.extend(_messages(pair))
    summary = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        summary += f", {len(doc['pairs'])} venue pair(s)"
    summary += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        summary += f", {doc['warnings_total']} warning(s)"
    lines.append(summary)
    return lines
