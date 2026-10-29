"""Read-only daily health: per-source checks, cross-venue pairs, the envelope and the table."""
from datetime import timedelta

import numpy as np

from .actions import CorporateActionsStore
from .classification import compare, load_classifications
from .store import ParquetStore
from .sync import run_date, select_legs

ACTIONS_STALE_SESSIONS = 2
RESOLUTION_MIN_SESSIONS = 60
WEEKDAY_TYPES = ("stock", "etf")


def expected_sessions(first, second, asset_type):
    """Calendar days strictly between two dates (weekdays only for stock and etf)."""
    count = 0
    day = first + timedelta(days=1)
    while day < second:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count


def longest_zero_run(zero, days):
    best = (0, None, None)
    run_start = None
    for i, flag in enumerate(zero):
        if flag:
            if run_start is None:
                run_start = i
            length = i - run_start + 1
            if length > best[0]:
                best = (length, days[run_start], days[i])
        else:
            run_start = None
    return best


def post_seam_gap(frame, asset_type):
    volume = frame["volume"].to_numpy(dtype="float64")
    close = frame["close"].to_numpy(dtype="float64")
    keep = (volume > 0) & ~np.isnan(close)
    days = [day for day, flag in zip(frame["datetime"].dt.date, keep) if flag]
    best = None
    for previous, following in zip(days, days[1:]):
        if (following - previous).days > 1:
            count = expected_sessions(previous, following, asset_type)
            if count > 0 and (best is None or count > best[0]):
                best = (count, previous, following)
    return best


def measure_resolution(frame, window):
    traded = frame[frame["volume"].to_numpy(dtype="float64") > 0]
    values = None
    for column in ("close_raw", "close"):
        series = traded[column].astype("float64")
        series = series[series.notna() & (series > 0)]
        series = series.tail(window) if window > 0 else series.iloc[0:0]
        if len(series):
            values = [float(value) for value in series.tolist()]
            break
    if values is None or len(values) < RESOLUTION_MIN_SESSIONS:
        return None
    sessions = len(values)
    distinct = sorted(set(values))
    ticks = [(distinct[k + 1] - distinct[k]) / distinct[k] for k in range(len(distinct) - 1)]
    flat = sum(1 for k in range(1, sessions) if values[k] == values[k - 1])
    return {"sessions": sessions, "distinct": len(distinct),
            "min_tick": min(ticks) if ticks else None,
            "flat_share": flat / (sessions - 1)}


def _tick(min_tick):
    return "n/a" if min_tick is None else f"{min_tick:.4%}"


def check_source(leg, store, actions, evidence, today, knobs):
    report = {"asset": leg["asset"], "exchange": leg["exchange"], "symbol": leg["symbol"],
              "alerts": [], "warnings": [], "notes": []}
    alerts, warnings, notes = report["alerts"], report["warnings"], report["notes"]
    if leg["provider"] == "eodhd":
        verdict, message = compare(evidence, leg["exchange"], leg["symbol"], leg["asset_type"])
        report["declared_class_check"] = verdict
        (warnings if verdict == "disagree" else notes).append(f"declared class: {message}")
    last = store.latest_date(leg["exchange"], leg["symbol"])
    if last is None:
        alerts.append("never filled - no stored rows (jef-data sync first)")
        return report
    frame = store.load(leg["exchange"], leg["symbol"])
    asset_type = leg["asset_type"]
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    report["rows"] = len(frame)

    if missed >= knobs["staleness_k"]:
        alerts.append(f"stale: {missed} expected session(s) missing since {last} (multi-day "
                      "holidays can trip this - verify before acting)")
    if last == today:
        notes.append("today-dated bar stored (pre-close serve? the next tail-refresh heals it)")

    days = list(frame["datetime"].dt.date)
    zero = frame["volume"].to_numpy(dtype="float64") == 0
    zero_count = int(zero.sum())
    if zero_count:
        message = f"{zero_count} zero-volume row(s), dropped at the seam by pinned policy"
        length, first, final = longest_zero_run(zero, days)
        if length > 1:
            message += f" - largest contiguous run {length}, {first}..{final}"
        notes.append(message)

    gap = post_seam_gap(frame, asset_type)
    if gap is not None and gap[0] >= knobs["gap_k"]:
        notes.append(f"post-seam continuity: {gap[0]} expected session(s) absent between {gap[1]} "
                     f"and {gap[2]} - the seam's output splices across this hole; verify the "
                     "provider era before modelling (docs/DATA_CONTRACT.md §1)")

    resolution = measure_resolution(frame, knobs["resolution_window"])
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < knobs["resolution_k"] or resolution["flat_share"] > knobs["flat_k"]:
            notes.append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick "
                f"{_tick(resolution['min_tick'])}, {resolution['flat_share']:.1%} flat - the "
                "provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8)")

    split_days = {event.date for event in actions.load_splits(leg["symbol"])} \
        if leg["actions"] else set()
    closes = frame["close"].to_numpy(dtype="float64")
    count = len(closes)
    for i in range(max(1, count - knobs["window"]), count):
        previous = closes[i - 1]
        if previous == 0:
            continue
        move = closes[i] / previous - 1.0
        if abs(move) > knobs["jump_threshold"] and days[i] not in split_days:
            alerts.append(f"phantom-split-shaped jump {move:+.1%} on {days[i]} with no same-day "
                          "split event - check corporate actions (docs/DATA_CONTRACT.md §2)")

    if leg["actions"]:
        stamp = actions.last_updated(leg["symbol"])
        if stamp is None:
            alerts.append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = stamp.date()
            missed_refresh = expected_sessions(stamp_day, today, asset_type)
            if missed_refresh >= ACTIONS_STALE_SESSIONS:
                alerts.append(f"corporate actions stale: {missed_refresh} refresh session(s) "
                              f"missed since {stamp_day} - run jef-data sync")
    return report


def check_cross_venue(asset, leg_a, leg_b, store, knobs):
    label_a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    label_b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    pair = {"asset": asset, "kind": "cross_venue", "a": label_a, "b": label_b,
            "common_session": None, "spread": None, "threshold": knobs["spread_threshold"],
            "alerts": [], "warnings": [], "notes": []}
    frames = []
    for label, leg in ((label_a, leg_a), (label_b, leg_b)):
        frame = store.load(leg["exchange"], leg["symbol"])
        if frame.empty:
            pair["notes"].append(f"{label} has no stored rows - spread not measured")
            return pair
        frames.append(frame)
    window = knobs["window"]
    tails = []
    for frame in frames:
        tail = frame.tail(window) if window > 0 else frame.iloc[0:0]
        tails.append((list(tail["datetime"].dt.date), tail["close"].to_numpy(dtype="float64")))
    common = set(tails[0][0]) & set(tails[1][0])
    if not common:
        pair["notes"].append(f"no common session in the newest {window} - spread not measured "
                             "(see the staleness check)")
        return pair
    day = max(common)
    close_a, close_b = (float(closes[len(days) - 1 - days[::-1].index(day)])
                        for days, closes in tails)
    mid = (close_a + close_b) / 2
    if mid == 0:
        pair["notes"].append(f"zero mid price on {day} - spread not measured")
        return pair
    spread = abs(close_a - close_b) / mid
    pair["common_session"] = day.isoformat()
    pair["spread"] = spread
    quote = f"({label_a} {close_a:g} vs {label_b} {close_b:g})"
    pair["notes"].append(f"close spread {spread:.4%} on {day} {quote}")
    if spread > knobs["spread_threshold"]:
        finding = (f"cross-venue close spread {spread:.4%} on {day} exceeds "
                   f"{knobs['spread_threshold']:.4%} {quote} - feed problem or venue distress; "
                   "verify before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (pair["alerts"] if knobs["spread_alerts"] else pair["warnings"]).append(finding)
    return pair


def status_document(universe, store_path, *, assets=None, providers=None, now=None, window=10,
                    jump_threshold=0.40, staleness_k=2, resolution_window=500, resolution_k=0.20,
                    flat_k=0.25, gap_k=5, spread_threshold=0.005, spread_alerts=False):
    """The status envelope (status --json) for the selected legs."""
    knobs = {"window": window, "jump_threshold": jump_threshold, "staleness_k": staleness_k,
             "resolution_window": resolution_window, "resolution_k": resolution_k,
             "flat_k": flat_k, "gap_k": gap_k, "spread_threshold": spread_threshold,
             "spread_alerts": spread_alerts}
    legs = select_legs(universe, assets, providers)
    today = run_date(now)
    store = ParquetStore(store_path)
    actions = CorporateActionsStore(store_path)
    evidence = load_classifications()
    live = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    reports = [check_source(leg, store, actions, evidence, today, knobs) for leg in live]
    groups = {}
    for leg in live:
        groups.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, group in groups.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pairs.append(check_cross_venue(asset, group[i], group[j], store, knobs))
    everything = reports + pairs
    return {"schema_version": 1, "store": str(store_path), "reports": reports, "pairs": pairs,
            "alerts_total": sum(len(item["alerts"]) for item in everything),
            "warnings_total": sum(len(item["warnings"]) for item in everything)}


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
    """The status table, one string per line."""
    lines = []
    for report in doc["reports"]:
        last = report.get("last_session", "-")
        missed = report.get("missed_sessions", "-")
        rows = report.get("rows", 0)
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/"
                     f"{report['symbol']}: last {last}, {missed} missed, {rows} row(s)")
        resolution = report.get("resolution")
        if resolution is not None:
            lines.append(f"        res   {resolution['distinct']} distinct / "
                         f"{resolution['sessions']} traded, min tick "
                         f"{_tick(resolution['min_tick'])}, {resolution['flat_share']:.2%} flat")
        lines.extend(_findings(report))
    for pair in doc["pairs"]:
        lines.append(f"{_flag(pair)} {pair['asset']:>6} cross-venue {pair['a']} vs {pair['b']}")
        lines.extend(_findings(pair))
    summary = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        summary += f", {len(doc['pairs'])} venue pair(s)"
    summary += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        summary += f", {doc['warnings_total']} warning(s)"
    lines.append(summary)
    return lines
