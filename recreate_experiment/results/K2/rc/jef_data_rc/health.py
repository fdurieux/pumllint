"""Read-only daily health: per-source checks, venue pairs and the status document."""
from __future__ import annotations

import datetime as _dt
import math

from .actions import CorporateActionsStore, stamp_utc_date
from .classification import compare
from .store import ParquetStore

WEEKDAY_TYPES = ("stock", "etf")
ACTIONS_STALE_SESSIONS = 2
RESOLUTION_MIN_SESSIONS = 60

DEFAULTS = {"window": 10, "jump_threshold": 0.40, "staleness_k": 2,
            "resolution_window": 500, "resolution_k": 0.20, "flat_k": 0.25, "gap_k": 5,
            "spread_threshold": 0.005, "spread_alerts": False}


def expected_sessions(first, second, asset_type):
    """Calendar days strictly between two dates; Monday-Friday only for stock/etf."""
    count = 0
    day = first + _dt.timedelta(days=1)
    while day < second:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += _dt.timedelta(days=1)
    return count


def _is_nan(value):
    try:
        return math.isnan(value)
    except TypeError:
        return False


def _longest_zero_run(volumes):
    best_len, best_start = 0, None
    run_len, run_start = 0, None
    for i, value in enumerate(volumes):
        if value == 0:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    return best_len, best_start


def _largest_gap(days, volumes, closes, asset_type):
    survivors = [d for d, v, c in zip(days, volumes, closes) if v > 0 and not _is_nan(c)]
    best = None
    for prev, nxt in zip(survivors, survivors[1:]):
        if (nxt - prev).days > 1:
            count = expected_sessions(prev, nxt, asset_type)
            if count > 0 and (best is None or count > best[0]):
                best = (count, prev, nxt)
    return best


def _resolution(closes_raw, closes, volumes, window):
    def candidates(values):
        kept = [v for v, vol in zip(values, volumes)
                if vol > 0 and not _is_nan(v) and v > 0]
        return kept[-window:] if window > 0 else []

    values = candidates(closes_raw)
    if not values:
        values = candidates(closes)
    if len(values) < RESOLUTION_MIN_SESSIONS:
        return None
    sessions = len(values)
    distinct_values = sorted(set(values))
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


def _tick_text(min_tick):
    return "n/a" if min_tick is None else f"{min_tick:.4%}"


def check_source(leg, store, actions_store, today, *, window=10, jump_threshold=0.40,
                 staleness_k=2, resolution_window=500, resolution_k=0.20, flat_k=0.25,
                 gap_k=5):
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    report = {"asset": leg["asset"], "exchange": exchange, "symbol": symbol,
              "alerts": [], "warnings": [], "notes": []}
    alerts, warnings, notes = report["alerts"], report["warnings"], report["notes"]

    if leg["provider"] == "eodhd":
        verdict, message = compare(exchange, symbol, asset_type)
        report["declared_class_check"] = verdict
        (warnings if verdict == "disagree" else notes).append(f"declared class: {message}")

    last = store.latest_date(exchange, symbol)
    if last is None:
        alerts.append("never filled - no stored rows (jef-data sync first)")
        return report
    frame = store.load(exchange, symbol)
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    report["rows"] = len(frame)

    if missed >= staleness_k:
        alerts.append(f"stale: {missed} expected session(s) missing since {last.isoformat()} "
                      f"(multi-day holidays can trip this - verify before acting)")
    if last == today:
        notes.append("today-dated bar stored (pre-close serve? the next tail-refresh heals it)")

    days = [stamp.date() for stamp in frame["datetime"].tolist()]
    volumes = frame["volume"].tolist()
    closes = frame["close"].tolist()
    closes_raw = frame["close_raw"].tolist()

    zero = sum(1 for v in volumes if v == 0)
    if zero > 0:
        text = f"{zero} zero-volume row(s), dropped at the seam by pinned policy"
        length, start = _longest_zero_run(volumes)
        if length > 1:
            text += (f" - largest contiguous run {length}, {days[start].isoformat()}.."
                     f"{days[start + length - 1].isoformat()}")
        notes.append(text)

    gap = _largest_gap(days, volumes, closes, asset_type)
    if gap is not None and gap[0] >= gap_k:
        notes.append(f"post-seam continuity: {gap[0]} expected session(s) absent between "
                     f"{gap[1].isoformat()} and {gap[2].isoformat()} - the seam's output splices "
                     f"across this hole; verify the provider era before modelling "
                     f"(docs/DATA_CONTRACT.md §1)")

    resolution = _resolution(closes_raw, closes, volumes, resolution_window)
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < resolution_k or resolution["flat_share"] > flat_k:
            notes.append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick "
                f"{_tick_text(resolution['min_tick'])}, {resolution['flat_share']:.1%} flat - "
                f"the provider's quoting grid, verify before modelling "
                f"(docs/DATA_CONTRACT.md §7.8)")

    split_days = set()
    if leg["actions"]:
        split_days = {str(event.date) for event in actions_store.load_splits(symbol)}
    n = len(frame)
    for i in range(max(1, n - window), n):
        previous = closes[i - 1]
        if previous == 0:
            continue
        move = closes[i] / previous - 1.0
        if abs(move) > jump_threshold and days[i].isoformat() not in split_days:
            alerts.append(f"phantom-split-shaped jump {move:+.1%} on {days[i].isoformat()} with "
                          f"no same-day split event - check corporate actions "
                          f"(docs/DATA_CONTRACT.md §2)")

    if leg["actions"]:
        stamp = actions_store.last_updated(symbol)
        if stamp is None:
            alerts.append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = stamp_utc_date(stamp)
            missed_refresh = expected_sessions(stamp_day, today, asset_type)
            if missed_refresh >= ACTIONS_STALE_SESSIONS:
                alerts.append(f"corporate actions stale: {missed_refresh} refresh session(s) "
                              f"missed since {stamp_day.isoformat()} - run jef-data sync")
    return report


def check_cross_venue(asset, leg_a, leg_b, store, *, window=10, spread_threshold=0.005,
                      spread_alerts=False):
    label_a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    label_b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    pair = {"asset": asset, "kind": "cross_venue", "a": label_a, "b": label_b,
            "common_session": None, "spread": None, "threshold": spread_threshold,
            "alerts": [], "warnings": [], "notes": []}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((label_a, frame_a), (label_b, frame_b)):
        if frame.empty:
            pair["notes"].append(f"{label} has no stored rows - spread not measured")
            return pair
    tail_a = frame_a.tail(window) if window > 0 else frame_a.iloc[0:0]
    tail_b = frame_b.tail(window) if window > 0 else frame_b.iloc[0:0]
    days_a = [stamp.date() for stamp in tail_a["datetime"].tolist()]
    days_b = [stamp.date() for stamp in tail_b["datetime"].tolist()]
    common = set(days_a) & set(days_b)
    if not common:
        pair["notes"].append(f"no common session in the newest {window} - spread not measured "
                             f"(see the staleness check)")
        return pair
    session = max(common)
    close_a = [c for d, c in zip(days_a, tail_a["close"].tolist()) if d == session][-1]
    close_b = [c for d, c in zip(days_b, tail_b["close"].tolist()) if d == session][-1]
    mid = (close_a + close_b) / 2
    if mid == 0:
        pair["notes"].append(f"zero mid price on {session.isoformat()} - spread not measured")
        return pair
    spread = abs(close_a - close_b) / mid
    pair["common_session"] = session.isoformat()
    pair["spread"] = spread
    sides = f"({label_a} {close_a:g} vs {label_b} {close_b:g})"
    pair["notes"].append(f"close spread {spread:.4%} on {session.isoformat()} {sides}")
    if spread > spread_threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {session.isoformat()} exceeds "
                   f"{spread_threshold:.4%} {sides} - feed problem or venue distress; verify "
                   f"before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (pair["alerts"] if spread_alerts else pair["warnings"]).append(finding)
    return pair


def status_document(universe, store_path, *, assets=None, providers=None, now=None,
                    window=10, jump_threshold=0.40, staleness_k=2, resolution_window=500,
                    resolution_k=0.20, flat_k=0.25, gap_k=5, spread_threshold=0.005,
                    spread_alerts=False):
    """Return (the status envelope, the exit code)."""
    from .sync import select_legs

    legs = select_legs(universe, assets=assets, providers=providers)
    clock = now if now is not None else _dt.datetime.now(_dt.timezone.utc)
    today = clock.astimezone(_dt.timezone.utc).date()
    store = ParquetStore(store_path)
    actions_store = CorporateActionsStore(store_path)
    live = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    reports = [check_source(leg, store, actions_store, today, window=window,
                            jump_threshold=jump_threshold, staleness_k=staleness_k,
                            resolution_window=resolution_window, resolution_k=resolution_k,
                            flat_k=flat_k, gap_k=gap_k)
               for leg in live]
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
    alerts_total = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings_total = (sum(len(r["warnings"]) for r in reports)
                      + sum(len(p["warnings"]) for p in pairs))
    doc = {"schema_version": 1, "store": str(store_path), "reports": reports, "pairs": pairs,
           "alerts_total": alerts_total, "warnings_total": warnings_total}
    return doc, (1 if alerts_total > 0 else 0)


def _flag(entry):
    if entry["alerts"]:
        return "ALERT"
    if entry["warnings"]:
        return "WARN "
    return "ok   "


def render_table(doc):
    lines = []
    for report in doc["reports"]:
        last = report.get("last_session") or "-"
        missed = report["missed_sessions"] if "missed_sessions" in report else "-"
        rows = report.get("rows") or 0
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/"
                     f"{report['symbol']}: last {last}, {missed} missed, {rows} row(s)")
        resolution = report.get("resolution")
        if resolution is not None:
            lines.append(f"        res   {resolution['distinct']} distinct / "
                         f"{resolution['sessions']} traded, min tick "
                         f"{_tick_text(resolution['min_tick'])}, "
                         f"{resolution['flat_share']:.2%} flat")
        lines.extend(_finding_lines(report))
    for pair in doc["pairs"]:
        lines.append(f"{_flag(pair)} {pair['asset']:>6} cross-venue {pair['a']} vs {pair['b']}")
        lines.extend(_finding_lines(pair))
    summary = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        summary += f", {len(doc['pairs'])} venue pair(s)"
    summary += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        summary += f", {doc['warnings_total']} warning(s)"
    lines.append(summary)
    return lines


def _finding_lines(entry):
    out = [f"        ALERT {text}" for text in entry["alerts"]]
    out += [f"        WARN  {text}" for text in entry["warnings"]]
    out += [f"        note  {text}" for text in entry["notes"]]
    return out
