"""Read-only daily health: per-source checks, venue pairs and the exit code."""
import math
from datetime import timedelta

import numpy as np

from jef_data_rc.actions import CorporateActionsStore
from jef_data_rc.classification import compare
from jef_data_rc.store import ParquetStore
from jef_data_rc.sync import select_legs, utc_today

DEFAULT_STALENESS = 2
DEFAULT_JUMP_THRESHOLD = 0.40
DEFAULT_WINDOW = 10
DEFAULT_RESOLUTION_WINDOW = 500
DEFAULT_RESOLUTION_K = 0.20
DEFAULT_FLAT_K = 0.25
DEFAULT_GAP_K = 5
DEFAULT_SPREAD_THRESHOLD = 0.005
ACTIONS_STALE_SESSIONS = 2
MIN_RESOLUTION_SESSIONS = 60
WEEKDAY_TYPES = ("stock", "etf")


def expected_sessions(after, before, asset_type):
    """Calendar days strictly between two dates; weekdays only for stock and etf."""
    count = 0
    day = after + timedelta(days=1)
    while day < before:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count


def longest_zero_run(volumes):
    """(length, first index, last index) of the earliest longest run of zero volumes."""
    best = (0, None, None)
    run_start = None
    for i, value in enumerate(volumes):
        if value == 0:
            if run_start is None:
                run_start = i
            length = i - run_start + 1
            if length > best[0]:
                best = (length, run_start, i)
        else:
            run_start = None
    return best


def post_seam_gap(days, volumes, closes, asset_type):
    """Largest count of expected sessions between consecutive surviving rows, earliest on ties."""
    surviving = [day for day, volume, close in zip(days, volumes, closes)
                 if volume > 0 and not math.isnan(close)]
    best = None
    for previous, current in zip(surviving, surviving[1:]):
        if (current - previous).days <= 1:
            continue
        count = expected_sessions(previous, current, asset_type)
        if count > 0 and (best is None or count > best[0]):
            best = (count, previous, current)
    return best


def measure_resolution(frame, window):
    traded = frame[frame["volume"].to_numpy(dtype=np.float64) > 0]

    def usable(column):
        values = traded[column].to_numpy(dtype=np.float64)
        values = values[~np.isnan(values)]
        values = values[values > 0]
        return values[-window:] if window > 0 else values[:0]

    values = usable("close_raw")
    if len(values) == 0:
        values = usable("close")
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
    flat_pairs = int(np.sum(values[1:] == values[:-1]))
    flat_share = flat_pairs / (sessions - 1)
    return {"sessions": sessions, "distinct": distinct, "min_tick": min_tick,
            "flat_share": flat_share}


def check_source(leg, store, actions_store, today, *, window, jump_threshold, staleness_k,
                 resolution_window, resolution_k, flat_k, gap_k):
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    report = {"asset": leg["asset"], "exchange": exchange, "symbol": symbol,
              "alerts": [], "warnings": [], "notes": []}
    if leg["provider"] == "eodhd":
        verdict, message = compare(asset_type, exchange, symbol)
        report["declared_class_check"] = verdict
        target = report["warnings"] if verdict == "disagree" else report["notes"]
        target.append(f"declared class: {message}")
    last = store.latest_date(exchange, symbol)
    if last is None:
        report["alerts"].append("never filled - no stored rows (jef-data sync first)")
        return report
    frame = store.load(exchange, symbol)
    days = list(frame["datetime"].dt.date)
    volumes = frame["volume"].to_numpy(dtype=np.float64)
    closes = frame["close"].to_numpy(dtype=np.float64)
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    report["rows"] = len(frame)

    if missed >= staleness_k:
        report["alerts"].append(
            f"stale: {missed} expected session(s) missing since {last.isoformat()} "
            f"(multi-day holidays can trip this - verify before acting)")
    if last == today:
        report["notes"].append(
            "today-dated bar stored (pre-close serve? the next tail-refresh heals it)")

    zeros = int(np.sum(volumes == 0))
    if zeros:
        note = f"{zeros} zero-volume row(s), dropped at the seam by pinned policy"
        length, first, final = longest_zero_run(volumes.tolist())
        if length > 1:
            note += (f" - largest contiguous run {length}, "
                     f"{days[first].isoformat()}..{days[final].isoformat()}")
        report["notes"].append(note)

    gap = post_seam_gap(days, volumes.tolist(), closes.tolist(), asset_type)
    if gap is not None and gap[0] >= gap_k:
        report["notes"].append(
            f"post-seam continuity: {gap[0]} expected session(s) absent between "
            f"{gap[1].isoformat()} and {gap[2].isoformat()} - the seam's output splices across "
            f"this hole; verify the provider era before modelling (docs/DATA_CONTRACT.md §1)")

    resolution = measure_resolution(frame, resolution_window)
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < resolution_k or resolution["flat_share"] > flat_k:
            tick = "n/a" if resolution["min_tick"] is None else f"{resolution['min_tick']:.4%}"
            report["notes"].append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick {tick}, "
                f"{resolution['flat_share']:.1%} flat - the provider's quoting grid, verify "
                f"before modelling (docs/DATA_CONTRACT.md §7.8)")

    split_days = set()
    if leg["actions"]:
        split_days = {str(event.date)[:10] for event in actions_store.load_splits(symbol)}
    n = len(frame)
    for i in range(max(1, n - window), n):
        previous = closes[i - 1]
        if previous == 0:
            continue
        move = closes[i] / previous - 1.0
        if abs(move) > jump_threshold and days[i].isoformat() not in split_days:
            report["alerts"].append(
                f"phantom-split-shaped jump {move:+.1%} on {days[i].isoformat()} with no "
                f"same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)")

    if leg["actions"]:
        stamp = actions_store.last_updated(symbol)
        if stamp is None:
            report["alerts"].append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = stamp.date()
            behind = expected_sessions(stamp_day, today, asset_type)
            if behind >= ACTIONS_STALE_SESSIONS:
                report["alerts"].append(
                    f"corporate actions stale: {behind} refresh session(s) missed since "
                    f"{stamp_day.isoformat()} - run jef-data sync")
    return report


def check_cross_venue(asset, leg_a, leg_b, store, *, window, spread_threshold, spread_alerts):
    a_label = f"{leg_a['exchange']}/{leg_a['symbol']}"
    b_label = f"{leg_b['exchange']}/{leg_b['symbol']}"
    report = {"asset": asset, "kind": "cross_venue", "a": a_label, "b": b_label,
              "common_session": None, "spread": None, "threshold": spread_threshold,
              "alerts": [], "warnings": [], "notes": []}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((a_label, frame_a), (b_label, frame_b)):
        if len(frame) == 0:
            report["notes"].append(f"{label} has no stored rows - spread not measured")
            return report
    tail_a = frame_a.tail(window) if window > 0 else frame_a.iloc[:0]
    tail_b = frame_b.tail(window) if window > 0 else frame_b.iloc[:0]
    days_a = list(tail_a["datetime"].dt.date)
    days_b = list(tail_b["datetime"].dt.date)
    common = set(days_a) & set(days_b)
    if not common:
        report["notes"].append(
            f"no common session in the newest {window} - spread not measured (see the staleness check)")
        return report
    day = max(common)
    close_a = float(tail_a["close"].to_numpy(dtype=np.float64)[
        max(i for i, d in enumerate(days_a) if d == day)])
    close_b = float(tail_b["close"].to_numpy(dtype=np.float64)[
        max(i for i, d in enumerate(days_b) if d == day)])
    mid = (close_a + close_b) / 2
    if mid == 0:
        report["notes"].append(f"zero mid price on {day.isoformat()} - spread not measured")
        return report
    spread = abs(close_a - close_b) / mid
    report["common_session"] = day.isoformat()
    report["spread"] = spread
    sides = f"({a_label} {close_a:g} vs {b_label} {close_b:g})"
    report["notes"].append(f"close spread {spread:.4%} on {day.isoformat()} {sides}")
    if spread > spread_threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {day.isoformat()} exceeds "
                   f"{spread_threshold:.4%} {sides} - feed problem or venue distress; verify "
                   f"before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (report["alerts"] if spread_alerts else report["warnings"]).append(finding)
    return report


def run_status(universe, store_path, *, assets=None, providers=None, now=None,
               window=DEFAULT_WINDOW, jump_threshold=DEFAULT_JUMP_THRESHOLD,
               staleness_k=DEFAULT_STALENESS, resolution_window=DEFAULT_RESOLUTION_WINDOW,
               resolution_k=DEFAULT_RESOLUTION_K, flat_k=DEFAULT_FLAT_K, gap_k=DEFAULT_GAP_K,
               spread_threshold=DEFAULT_SPREAD_THRESHOLD, spread_alerts=False):
    """Return (the status --json document, the exit code)."""
    legs = select_legs(universe, assets, providers)
    today = utc_today(now)
    store = ParquetStore(store_path)
    actions_store = CorporateActionsStore(store_path)
    live = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    reports = [check_source(leg, store, actions_store, today, window=window,
                            jump_threshold=jump_threshold, staleness_k=staleness_k,
                            resolution_window=resolution_window, resolution_k=resolution_k,
                            flat_k=flat_k, gap_k=gap_k) for leg in live]
    by_asset = {}
    for leg in live:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, asset_legs in by_asset.items():
        if len(asset_legs) < 2:
            continue
        for i in range(len(asset_legs)):
            for j in range(i + 1, len(asset_legs)):
                pairs.append(check_cross_venue(asset, asset_legs[i], asset_legs[j], store,
                                               window=window, spread_threshold=spread_threshold,
                                               spread_alerts=spread_alerts))
    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    doc = {"schema_version": 1, "store": str(store_path), "reports": reports, "pairs": pairs,
           "alerts_total": alerts, "warnings_total": warnings}
    return doc, (1 if alerts > 0 else 0)


def _flag(entry):
    if entry["alerts"]:
        return "ALERT"
    if entry["warnings"]:
        return "WARN "
    return "ok   "


def _messages(entry):
    lines = [f"        ALERT {text}" for text in entry["alerts"]]
    lines += [f"        WARN  {text}" for text in entry["warnings"]]
    lines += [f"        note  {text}" for text in entry["notes"]]
    return lines


def render_table(doc):
    lines = []
    for report in doc["reports"]:
        last = report.get("last_session", "-")
        missed = report.get("missed_sessions", "-")
        rows = report.get("rows", 0)
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/"
                     f"{report['symbol']}: last {last}, {missed} missed, {rows} row(s)")
        resolution = report.get("resolution")
        if resolution is not None:
            tick = "n/a" if resolution["min_tick"] is None else f"{resolution['min_tick']:.4%}"
            lines.append(f"        res   {resolution['distinct']} distinct / "
                         f"{resolution['sessions']} traded, min tick {tick}, "
                         f"{resolution['flat_share']:.2%} flat")
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
