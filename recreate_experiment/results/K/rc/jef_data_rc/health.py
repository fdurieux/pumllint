"""Read-only status checks: per-source verdicts, venue pairs and the envelope."""
from __future__ import annotations

import datetime as _dt
import math
from pathlib import Path

import numpy as np

from .actions import CorporateActionsStore
from .adjust import row_days
from .classification import check_declared_class
from .store import ParquetStore
from .sync import select_legs

SCHEMA_VERSION = 1
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


def expected_sessions(first, second, asset_type):
    """Calendar days strictly between two dates (weekdays only for stock and etf)."""
    count = 0
    day = first + _dt.timedelta(days=1)
    while day < second:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += _dt.timedelta(days=1)
    return count


def _dates(frame):
    return [_dt.date.fromisoformat(d) for d in row_days(frame["datetime"])]


def longest_zero_run(volume):
    best_len, best_start = 0, None
    run_len, run_start = 0, None
    for i, value in enumerate(volume):
        if value == 0:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    return best_len, best_start


def post_seam_gap(frame, days, asset_type):
    volume = frame["volume"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    survivors = [days[i] for i in range(len(days)) if volume[i] > 0 and not math.isnan(close[i])]
    best = None
    for prev, nxt in zip(survivors, survivors[1:]):
        if (nxt - prev).days > 1:
            count = expected_sessions(prev, nxt, asset_type)
            if count > 0 and (best is None or count > best[0]):
                best = (count, prev, nxt)
    return best


def price_resolution(frame, window):
    traded = frame[frame["volume"].to_numpy(dtype=np.float64) > 0]

    def usable(column):
        values = traded[column].to_numpy(dtype=np.float64)
        values = values[~np.isnan(values)]
        values = values[values > 0]
        keep = max(len(values) - window, 0)
        return values[keep:]

    values = usable("close_raw")
    if len(values) == 0:
        values = usable("close")
    sessions = len(values)
    if sessions < MIN_RESOLUTION_SESSIONS:
        return None
    distinct_values = np.unique(values)
    if len(distinct_values) > 1:
        ticks = np.diff(distinct_values) / distinct_values[:-1]
        min_tick = float(ticks.min())
    else:
        min_tick = None
    flat = int((values[1:] == values[:-1]).sum())
    return {"sessions": int(sessions), "distinct": int(len(distinct_values)),
            "min_tick": min_tick, "flat_share": flat / (sessions - 1)}


def check_source(leg, store, actions, today, *, window, jump_threshold, staleness_k,
                 resolution_window, resolution_k, flat_k, gap_k):
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    alerts, warnings, notes = [], [], []
    report = {"asset": leg["asset"], "exchange": exchange, "symbol": symbol,
              "alerts": alerts, "warnings": warnings, "notes": notes}
    if leg["provider"] == "eodhd":
        verdict, message = check_declared_class(exchange, symbol, asset_type)
        report["declared_class_check"] = verdict
        (warnings if verdict == "disagree" else notes).append(f"declared class: {message}")

    last = store.latest_date(exchange, symbol)
    frame = store.load(exchange, symbol) if last is not None else None
    if last is None or frame is None or len(frame) == 0:
        alerts.append("never filled - no stored rows (jef-data sync first)")
        return report

    days = _dates(frame)
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    report["rows"] = int(len(frame))

    if missed >= staleness_k:
        alerts.append(f"stale: {missed} expected session(s) missing since {last} (multi-day "
                      f"holidays can trip this - verify before acting)")
    if last == today:
        notes.append("today-dated bar stored (pre-close serve? the next tail-refresh heals it)")

    volume = frame["volume"].to_numpy(dtype=np.float64)
    zero = int((volume == 0).sum())
    if zero > 0:
        message = f"{zero} zero-volume row(s), dropped at the seam by pinned policy"
        run_len, run_start = longest_zero_run(volume)
        if run_len > 1:
            message += (f" - largest contiguous run {run_len}, {days[run_start]}.."
                        f"{days[run_start + run_len - 1]}")
        notes.append(message)

    gap = post_seam_gap(frame, days, asset_type)
    if gap is not None and gap[0] >= gap_k:
        notes.append(f"post-seam continuity: {gap[0]} expected session(s) absent between "
                     f"{gap[1]} and {gap[2]} - the seam's output splices across this hole; "
                     f"verify the provider era before modelling (docs/DATA_CONTRACT.md §1)")

    resolution = price_resolution(frame, resolution_window)
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < resolution_k or resolution["flat_share"] > flat_k:
            tick = (f"{resolution['min_tick']:.4%}" if resolution["min_tick"] is not None
                    else "n/a")
            notes.append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick {tick}, "
                f"{resolution['flat_share']:.1%} flat - the provider's quoting grid, verify "
                f"before modelling (docs/DATA_CONTRACT.md §7.8)")

    split_days = set()
    if leg["actions"]:
        split_days = {e.date if isinstance(e.date, _dt.date) else _dt.date.fromisoformat(e.date)
                      for e in actions.load_splits(symbol)}
    close = frame["close"].to_numpy(dtype=np.float64)
    n = len(close)
    for i in range(max(1, n - window), n):
        previous = close[i - 1]
        if previous == 0:
            continue
        move = close[i] / previous - 1.0
        if abs(move) > jump_threshold and days[i] not in split_days:
            alerts.append(f"phantom-split-shaped jump {move:+.1%} on {days[i]} with no "
                          f"same-day split event - check corporate actions "
                          f"(docs/DATA_CONTRACT.md §2)")

    if leg["actions"]:
        stamp = actions.last_updated(symbol)
        if stamp is None:
            alerts.append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = stamp.astimezone(_dt.timezone.utc).date()
            refreshes = expected_sessions(stamp_day, today, asset_type)
            if refreshes >= ACTIONS_STALE_SESSIONS:
                alerts.append(f"corporate actions stale: {refreshes} refresh session(s) missed "
                              f"since {stamp_day} - run jef-data sync")
    return report


def check_cross_venue(asset, leg_a, leg_b, store, *, window, spread_threshold, spread_alerts):
    label_a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    label_b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    alerts, warnings, notes = [], [], []
    pair = {"asset": asset, "kind": "cross_venue", "a": label_a, "b": label_b,
            "common_session": None, "spread": None, "threshold": spread_threshold,
            "alerts": alerts, "warnings": warnings, "notes": notes}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((label_a, frame_a), (label_b, frame_b)):
        if len(frame) == 0:
            notes.append(f"{label} has no stored rows - spread not measured")
            return pair
    tail_a = frame_a.iloc[max(len(frame_a) - window, 0):]
    tail_b = frame_b.iloc[max(len(frame_b) - window, 0):]
    days_a, days_b = _dates(tail_a), _dates(tail_b)
    common = set(days_a) & set(days_b)
    if not common:
        notes.append(f"no common session in the newest {window} - spread not measured (see "
                     f"the staleness check)")
        return pair
    day = max(common)
    close_a = float(tail_a["close"].to_numpy(dtype=np.float64)[
        [i for i, d in enumerate(days_a) if d == day][-1]])
    close_b = float(tail_b["close"].to_numpy(dtype=np.float64)[
        [i for i, d in enumerate(days_b) if d == day][-1]])
    mid = (close_a + close_b) / 2
    if mid == 0:
        notes.append(f"zero mid price on {day} - spread not measured")
        return pair
    spread = abs(close_a - close_b) / mid
    pair["common_session"] = day.isoformat()
    pair["spread"] = spread
    quote = f"({label_a} {close_a:g} vs {label_b} {close_b:g})"
    notes.append(f"close spread {spread:.4%} on {day} {quote}")
    if spread > spread_threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {day} exceeds "
                   f"{spread_threshold:.4%} {quote} - feed problem or venue distress; verify "
                   f"before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (alerts if spread_alerts else warnings).append(finding)
    return pair


def run_status(universe, store_path, *, assets=None, providers=None, now=None,
               window=DEFAULT_WINDOW, jump_threshold=DEFAULT_JUMP_THRESHOLD,
               staleness_k=DEFAULT_STALENESS, resolution_window=DEFAULT_RESOLUTION_WINDOW,
               resolution_k=DEFAULT_RESOLUTION_K, flat_k=DEFAULT_FLAT_K, gap_k=DEFAULT_GAP_K,
               spread_threshold=DEFAULT_SPREAD_THRESHOLD, spread_alerts=False):
    """The status envelope and the exit code it implies."""
    legs = [leg for leg in select_legs(universe, assets, providers)
            if leg["provider"] != "yahoo-csv"]
    clock = now if now is not None else _dt.datetime.now(_dt.timezone.utc)
    today = clock.astimezone(_dt.timezone.utc).date()
    store_label = str(store_path)
    store = ParquetStore(store_label)
    actions = CorporateActionsStore(Path(store_label) / "corporate_actions")
    reports = [check_source(leg, store, actions, today, window=window,
                            jump_threshold=jump_threshold, staleness_k=staleness_k,
                            resolution_window=resolution_window, resolution_k=resolution_k,
                            flat_k=flat_k, gap_k=gap_k)
               for leg in legs]
    by_asset = {}
    for leg in legs:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, asset_legs in by_asset.items():
        for i in range(len(asset_legs)):
            for j in range(i + 1, len(asset_legs)):
                pairs.append(check_cross_venue(asset, asset_legs[i], asset_legs[j], store,
                                               window=window,
                                               spread_threshold=spread_threshold,
                                               spread_alerts=spread_alerts))
    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    doc = {"schema_version": SCHEMA_VERSION, "store": store_label, "reports": reports,
           "pairs": pairs, "alerts_total": alerts, "warnings_total": warnings}
    return doc, (1 if alerts > 0 else 0)


def _flag(item):
    if item["alerts"]:
        return "ALERT"
    if item["warnings"]:
        return "WARN "
    return "ok   "


def _messages(item):
    lines = [f"        ALERT {text}" for text in item["alerts"]]
    lines += [f"        WARN  {text}" for text in item["warnings"]]
    lines += [f"        note  {text}" for text in item["notes"]]
    return lines


def table_lines(doc):
    lines = []
    for report in doc["reports"]:
        last = report.get("last_session") or "-"
        missed = report["missed_sessions"] if "missed_sessions" in report else "-"
        rows = report.get("rows") or 0
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/"
                     f"{report['symbol']}: last {last}, {missed} missed, {rows} row(s)")
        resolution = report.get("resolution")
        if resolution:
            tick = (f"{resolution['min_tick']:.4%}" if resolution["min_tick"] is not None
                    else "n/a")
            lines.append(f"        res   {resolution['distinct']} distinct / "
                         f"{resolution['sessions']} traded, min tick {tick}, "
                         f"{resolution['flat_share']:.2%} flat")
        lines += _messages(report)
    for pair in doc["pairs"]:
        lines.append(f"{_flag(pair)} {pair['asset']:>6} cross-venue {pair['a']} vs {pair['b']}")
        lines += _messages(pair)
    summary = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        summary += f", {len(doc['pairs'])} venue pair(s)"
    summary += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        summary += f", {doc['warnings_total']} warning(s)"
    lines.append(summary)
    return lines
