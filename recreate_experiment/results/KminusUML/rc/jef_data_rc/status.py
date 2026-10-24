"""Read-only status checks: per-source verdicts and cross-venue pairs."""
import datetime as _dt

import numpy as np

from . import actions, classification, store
from .sync import select_legs, utc_today

DEFAULTS = {"window": 10, "jump_threshold": 0.40, "staleness_k": 2,
            "resolution_window": 500, "resolution_k": 0.20, "flat_k": 0.25,
            "gap_k": 5, "spread_threshold": 0.005, "spread_alerts": False}
ACTIONS_STALE_K = 2
MIN_RESOLUTION_SESSIONS = 60
WEEKDAY_TYPES = ("stock", "etf")


def expected_sessions(first, second, asset_type):
    """Calendar days strictly between two dates (weekdays only for stock/etf)."""
    a = _dt.date.fromisoformat(str(first))
    b = _dt.date.fromisoformat(str(second))
    count = 0
    day = a + _dt.timedelta(days=1)
    while day < b:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += _dt.timedelta(days=1)
    return count


def _days(frame):
    return [d.strftime("%Y-%m-%d") for d in frame["datetime"]]


def _zero_volume_note(frame, days):
    zero = frame["volume"].to_numpy(dtype="float64") == 0
    total = int(zero.sum())
    if total == 0:
        return None
    best_len, best_start = 0, None
    run_len, run_start = 0, None
    for i, flag in enumerate(zero):
        if flag:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    note = f"{total} zero-volume row(s), dropped at the seam by pinned policy"
    if best_len > 1:
        note += (f" - largest contiguous run {best_len}, {days[best_start]}.."
                 f"{days[best_start + best_len - 1]}")
    return note


def _largest_gap(frame, days, asset_type):
    volume = frame["volume"].to_numpy(dtype="float64")
    close = frame["close"].to_numpy(dtype="float64")
    survivors = [days[i] for i in range(len(days)) if volume[i] > 0 and not np.isnan(close[i])]
    best = None
    for prev, nxt in zip(survivors, survivors[1:]):
        gap_days = (_dt.date.fromisoformat(nxt) - _dt.date.fromisoformat(prev)).days
        if gap_days <= 1:
            continue
        count = expected_sessions(prev, nxt, asset_type)
        if count > 0 and (best is None or count > best[0]):
            best = (count, prev, nxt)
    return best


def _resolution(frame, window):
    traded = frame["volume"].to_numpy(dtype="float64") > 0
    values = None
    for column in ("close_raw", "close"):
        series = frame[column].to_numpy(dtype="float64")[traded]
        series = series[~np.isnan(series)]
        series = series[series > 0]
        series = series[-window:] if window > 0 else series[:0]
        if len(series):
            values = series
            break
    if values is None or len(values) < MIN_RESOLUTION_SESSIONS:
        return None
    sessions = len(values)
    distinct_values = sorted(set(float(v) for v in values))
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


def source_report(leg, store_path, today, opts):
    report = {"asset": leg["asset"], "exchange": leg["exchange"], "symbol": leg["symbol"],
              "alerts": [], "warnings": [], "notes": []}
    if leg["provider"] == "eodhd":
        verdict, message = classification.verdict(leg["exchange"], leg["symbol"],
                                                  leg["asset_type"])
        report["declared_class_check"] = verdict
        target = report["warnings"] if verdict == "disagree" else report["notes"]
        target.append(f"declared class: {message}")

    frame = store.read_series(store_path, leg["exchange"], leg["symbol"])
    if frame.empty:
        report["alerts"].append("never filled - no stored rows (jef-data sync first)")
        return report

    days = _days(frame)
    asset_type = leg["asset_type"]
    last = store.latest_session(store_path, leg["exchange"], leg["symbol"])
    today_text = today.isoformat()
    missed = expected_sessions(last, today_text, asset_type)
    if missed >= opts["staleness_k"]:
        report["alerts"].append(
            f"stale: {missed} expected session(s) missing since {last} (multi-day holidays "
            f"can trip this - verify before acting)")
    if last == today_text:
        report["notes"].append(
            "today-dated bar stored (pre-close serve? the next tail-refresh heals it)")

    note = _zero_volume_note(frame, days)
    if note:
        report["notes"].append(note)

    gap = _largest_gap(frame, days, asset_type)
    if gap is not None and gap[0] >= opts["gap_k"]:
        report["notes"].append(
            f"post-seam continuity: {gap[0]} expected session(s) absent between {gap[1]} "
            f"and {gap[2]} - the seam's output splices across this hole; verify the "
            f"provider era before modelling (docs/DATA_CONTRACT.md §1)")

    resolution = _resolution(frame, opts["resolution_window"])
    if resolution is not None:
        coarse = (resolution["distinct"] / resolution["sessions"] < opts["resolution_k"]
                  or resolution["flat_share"] > opts["flat_k"])
        if coarse:
            tick = ("n/a" if resolution["min_tick"] is None
                    else f"{resolution['min_tick']:.4%}")
            report["notes"].append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick {tick}, "
                f"{resolution['flat_share']:.1%} flat - the provider's quoting grid, verify "
                f"before modelling (docs/DATA_CONTRACT.md §7.8)")

    split_days = set()
    if leg["actions"]:
        split_days = {str(e.date) for e in actions.read_splits(store_path, leg["symbol"])}
    close = frame["close"].to_numpy(dtype="float64")
    n = len(close)
    for i in range(max(1, n - opts["window"]), n):
        previous = close[i - 1]
        if previous == 0:
            continue
        move = float(close[i] / previous - 1.0)
        if abs(move) > opts["jump_threshold"] and days[i] not in split_days:
            report["alerts"].append(
                f"phantom-split-shaped jump {move:+.1%} on {days[i]} with no same-day split "
                f"event - check corporate actions (docs/DATA_CONTRACT.md §2)")

    if leg["actions"]:
        stamp = actions.stamp_date(store_path, leg["symbol"])
        if stamp is None:
            report["alerts"].append("corporate actions stale: never synced - run jef-data sync")
        else:
            behind = expected_sessions(stamp.isoformat(), today_text, asset_type)
            if behind >= ACTIONS_STALE_K:
                report["alerts"].append(
                    f"corporate actions stale: {behind} refresh session(s) missed since "
                    f"{stamp.isoformat()} - run jef-data sync")

    report["last_session"] = last
    report["missed_sessions"] = missed
    report["rows"] = len(frame)
    if resolution is not None:
        report["resolution"] = resolution
    return report


def pair_report(asset, leg_a, leg_b, store_path, opts):
    label_a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    label_b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    threshold = opts["spread_threshold"]
    report = {"asset": asset, "kind": "cross_venue", "a": label_a, "b": label_b,
              "common_session": None, "spread": None, "threshold": threshold,
              "alerts": [], "warnings": [], "notes": []}
    frame_a = store.read_series(store_path, leg_a["exchange"], leg_a["symbol"])
    frame_b = store.read_series(store_path, leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((label_a, frame_a), (label_b, frame_b)):
        if frame.empty:
            report["notes"].append(f"{label} has no stored rows - spread not measured")
            return report
    window = opts["window"]
    tail_a = frame_a.iloc[-window:] if window > 0 else frame_a.iloc[:0]
    tail_b = frame_b.iloc[-window:] if window > 0 else frame_b.iloc[:0]
    days_a = _days(tail_a)
    days_b = _days(tail_b)
    common = set(days_a) & set(days_b)
    if not common:
        report["notes"].append(
            f"no common session in the newest {window} - spread not measured (see the "
            f"staleness check)")
        return report
    session = max(common)
    close_a = float(tail_a["close"].to_numpy(dtype="float64")[
        max(i for i, d in enumerate(days_a) if d == session)])
    close_b = float(tail_b["close"].to_numpy(dtype="float64")[
        max(i for i, d in enumerate(days_b) if d == session)])
    mid = (close_a + close_b) / 2
    if mid == 0:
        report["notes"].append(f"zero mid price on {session} - spread not measured")
        return report
    spread = abs(close_a - close_b) / mid
    report["common_session"] = session
    report["spread"] = spread
    quote = f"({label_a} {close_a:g} vs {label_b} {close_b:g})"
    report["notes"].append(f"close spread {spread:.4%} on {session} {quote}")
    if spread > threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {session} exceeds "
                   f"{threshold:.4%} {quote} - feed problem or venue distress; verify "
                   f"before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (report["alerts"] if opts["spread_alerts"] else report["warnings"]).append(finding)
    return report


def run_status(universe, store_path=None, *, assets=None, providers=None, now=None,
               **options):
    """The status --json document and its exit code."""
    opts = dict(DEFAULTS)
    opts.update(options)
    legs = select_legs(universe, assets, providers)
    if store_path is None:
        store_path = universe["defaults"]["store"]
    today = utc_today(now)
    checked = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    reports = [source_report(leg, store_path, today, opts) for leg in checked]

    by_asset = {}
    for leg in checked:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, asset_legs in by_asset.items():
        if len(asset_legs) < 2:
            continue
        for i in range(len(asset_legs)):
            for j in range(i + 1, len(asset_legs)):
                pairs.append(pair_report(asset, asset_legs[i], asset_legs[j], store_path, opts))

    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    doc = {"schema_version": 1, "store": str(store_path), "reports": reports,
           "pairs": pairs, "alerts_total": alerts, "warnings_total": warnings}
    return doc, (1 if alerts > 0 else 0)


def _flag(item):
    if item["alerts"]:
        return "ALERT"
    if item["warnings"]:
        return "WARN "
    return "ok   "


def _findings(item):
    lines = [f"        ALERT {text}" for text in item["alerts"]]
    lines += [f"        WARN  {text}" for text in item["warnings"]]
    lines += [f"        note  {text}" for text in item["notes"]]
    return lines


def render_table(doc):
    lines = []
    for r in doc["reports"]:
        last = r.get("last_session") or "-"
        missed = r.get("missed_sessions")
        missed = "-" if missed is None else missed
        rows = r.get("rows") or 0
        lines.append(f"{_flag(r)} {r['asset']:>6} {r['exchange']}/{r['symbol']}: last {last}, "
                     f"{missed} missed, {rows} row(s)")
        res = r.get("resolution")
        if res is not None:
            tick = "n/a" if res["min_tick"] is None else f"{res['min_tick']:.4%}"
            lines.append(f"        res   {res['distinct']} distinct / {res['sessions']} "
                         f"traded, min tick {tick}, {res['flat_share']:.2%} flat")
        lines += _findings(r)
    for p in doc["pairs"]:
        lines.append(f"{_flag(p)} {p['asset']:>6} cross-venue {p['a']} vs {p['b']}")
        lines += _findings(p)
    tail = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        tail += f", {len(doc['pairs'])} venue pair(s)"
    tail += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        tail += f", {doc['warnings_total']} warning(s)"
    lines.append(tail)
    return lines
