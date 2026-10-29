"""Read-only daily health checks of the stored series and the venue pairs."""
import datetime as _dt
import math

import numpy as np

WEEKDAY_TYPES = ("stock", "etf")
STALENESS_K = 2
JUMP_THRESHOLD = 0.40
WINDOW = 10
RESOLUTION_WINDOW = 500
RESOLUTION_MIN_SESSIONS = 60
RESOLUTION_K = 0.20
FLAT_K = 0.25
GAP_K = 5
SPREAD_THRESHOLD = 0.005
ACTIONS_STALE_SESSIONS = 2


def expected_sessions(first, second, asset_type):
    """Calendar days strictly between two dates, weekdays only for stock/etf."""
    count = 0
    day = first + _dt.timedelta(days=1)
    while day < second:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += _dt.timedelta(days=1)
    return count


def _utc_day(stamp):
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(_dt.timezone.utc)
    return stamp.date()


def _days(frame):
    return [d.date() for d in frame["datetime"]]


def _zero_volume_note(volumes, days):
    zero = volumes == 0
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
        first = days[best_start].isoformat()
        last = days[best_start + best_len - 1].isoformat()
        note += f" - largest contiguous run {best_len}, {first}..{last}"
    return note


def _post_seam_gap(volumes, closes, days, asset_type):
    keep = [i for i in range(len(days)) if volumes[i] > 0 and not math.isnan(closes[i])]
    best = None
    for prev, nxt in zip(keep, keep[1:]):
        a, b = days[prev], days[nxt]
        if (b - a).days <= 1:
            continue
        count = expected_sessions(a, b, asset_type)
        if count > 0 and (best is None or count > best[0]):
            best = (count, a, b)
    return best


def _resolution(frame, window):
    volumes = frame["volume"].to_numpy(dtype="float64")
    traded = volumes > 0

    def usable(column):
        values = frame[column].to_numpy(dtype="float64")[traded]
        values = values[~np.isnan(values)]
        return values[values > 0]

    values = usable("close_raw")[-window:] if window > 0 else np.array([])
    if len(values) == 0:
        values = usable("close")[-window:] if window > 0 else np.array([])
    sessions = len(values)
    if sessions < RESOLUTION_MIN_SESSIONS:
        return None
    distinct_values = np.unique(values)
    distinct = len(distinct_values)
    min_tick = None
    if distinct > 1:
        steps = (distinct_values[1:] - distinct_values[:-1]) / distinct_values[:-1]
        min_tick = float(steps.min())
    flat = int((values[1:] == values[:-1]).sum())
    flat_share = flat / (sessions - 1)
    return {"sessions": sessions, "distinct": distinct, "min_tick": min_tick,
            "flat_share": float(flat_share)}


def _tick(min_tick):
    return "n/a" if min_tick is None else f"{min_tick:.4%}"


def check_source(leg, store, actions_store, evidence, today, *, window=WINDOW,
                 jump_threshold=JUMP_THRESHOLD, staleness_k=STALENESS_K,
                 resolution_window=RESOLUTION_WINDOW, resolution_k=RESOLUTION_K,
                 flat_k=FLAT_K, gap_k=GAP_K):
    from .classification import compare

    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    alerts, warnings, notes = [], [], []
    report = {"asset": leg["asset"], "exchange": exchange, "symbol": symbol,
              "alerts": alerts, "warnings": warnings, "notes": notes}
    if leg["provider"] == "eodhd":
        verdict, message = compare(evidence, exchange, symbol, asset_type)
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
                      "(multi-day holidays can trip this - verify before acting)")
    if last == today:
        notes.append("today-dated bar stored (pre-close serve? the next tail-refresh heals it)")
    days = _days(frame)
    volumes = frame["volume"].to_numpy(dtype="float64")
    closes = frame["close"].to_numpy(dtype="float64")
    zero_note = _zero_volume_note(volumes, days)
    if zero_note:
        notes.append(zero_note)
    gap = _post_seam_gap(volumes, closes, days, asset_type)
    if gap is not None and gap[0] >= gap_k:
        notes.append(f"post-seam continuity: {gap[0]} expected session(s) absent between "
                     f"{gap[1].isoformat()} and {gap[2].isoformat()} - the seam's output splices "
                     "across this hole; verify the provider era before modelling "
                     "(docs/DATA_CONTRACT.md §1)")
    resolution = _resolution(frame, resolution_window)
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < resolution_k or resolution["flat_share"] > flat_k:
            notes.append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick "
                f"{_tick(resolution['min_tick'])}, {resolution['flat_share']:.1%} flat - the "
                "provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8)")
    split_days = set()
    if leg["actions"]:
        split_days = {event.date for event in actions_store.load_splits(symbol)}
    n = len(frame)
    for i in range(max(1, n - window), n):
        previous = closes[i - 1]
        if previous == 0:
            continue
        move = closes[i] / previous - 1.0
        if abs(move) > jump_threshold and days[i] not in split_days:
            alerts.append(f"phantom-split-shaped jump {move:+.1%} on {days[i].isoformat()} with no "
                          "same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)")
    if leg["actions"]:
        stamp = actions_store.last_updated(symbol)
        if stamp is None:
            alerts.append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = _utc_day(stamp)
            missed_refresh = expected_sessions(stamp_day, today, asset_type)
            if missed_refresh >= ACTIONS_STALE_SESSIONS:
                alerts.append(f"corporate actions stale: {missed_refresh} refresh session(s) missed "
                              f"since {stamp_day.isoformat()} - run jef-data sync")
    return report


def check_cross_venue(asset, leg_a, leg_b, store, *, window=WINDOW,
                      spread_threshold=SPREAD_THRESHOLD, spread_alerts=False):
    label_a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    label_b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    alerts, warnings, notes = [], [], []
    report = {"asset": asset, "kind": "cross_venue", "a": label_a, "b": label_b,
              "common_session": None, "spread": None, "threshold": spread_threshold,
              "alerts": alerts, "warnings": warnings, "notes": notes}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((label_a, frame_a), (label_b, frame_b)):
        if len(frame) == 0:
            notes.append(f"{label} has no stored rows - spread not measured")
            return report
    tail_a = frame_a.iloc[-window:] if window > 0 else frame_a.iloc[0:0]
    tail_b = frame_b.iloc[-window:] if window > 0 else frame_b.iloc[0:0]
    days_a = _days(tail_a)
    days_b = _days(tail_b)
    common = sorted(set(days_a) & set(days_b))
    if not common:
        notes.append(f"no common session in the newest {window} - spread not measured "
                     "(see the staleness check)")
        return report
    day = common[-1]
    close_a = float(tail_a["close"].to_numpy(dtype="float64")[[i for i, d in enumerate(days_a) if d == day][-1]])
    close_b = float(tail_b["close"].to_numpy(dtype="float64")[[i for i, d in enumerate(days_b) if d == day][-1]])
    mid = (close_a + close_b) / 2
    if mid == 0:
        notes.append(f"zero mid price on {day.isoformat()} - spread not measured")
        return report
    spread = abs(close_a - close_b) / mid
    report["common_session"] = day.isoformat()
    report["spread"] = spread
    pair_text = f"({label_a} {close_a:g} vs {label_b} {close_b:g})"
    notes.append(f"close spread {spread:.4%} on {day.isoformat()} {pair_text}")
    if spread > spread_threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {day.isoformat()} exceeds "
                   f"{spread_threshold:.4%} {pair_text} - feed problem or venue distress; verify "
                   "before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (alerts if spread_alerts else warnings).append(finding)
    return report


def run_status(universe, store_path, *, assets=None, providers=None, now=None, **knobs):
    """Return (status document, exit code)."""
    from .actions import CorporateActionsStore
    from .classification import load_classifications
    from .store import ParquetStore
    from .sync import select_legs

    legs = select_legs(universe, assets, providers)
    clock = now or _dt.datetime.now(_dt.timezone.utc)
    today = clock.astimezone(_dt.timezone.utc).date()
    store = ParquetStore(store_path)
    actions_store = CorporateActionsStore(store_path)
    evidence = load_classifications()
    window = knobs.get("window", WINDOW)
    checked = [leg for leg in legs if leg["provider"] != "yahoo-csv"]
    reports = [check_source(leg, store, actions_store, evidence, today,
                            window=window,
                            jump_threshold=knobs.get("jump_threshold", JUMP_THRESHOLD),
                            staleness_k=knobs.get("staleness_k", STALENESS_K),
                            resolution_window=knobs.get("resolution_window", RESOLUTION_WINDOW),
                            resolution_k=knobs.get("resolution_k", RESOLUTION_K),
                            flat_k=knobs.get("flat_k", FLAT_K),
                            gap_k=knobs.get("gap_k", GAP_K))
               for leg in checked]
    by_asset = {}
    for leg in checked:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, asset_legs in by_asset.items():
        for i in range(len(asset_legs)):
            for j in range(i + 1, len(asset_legs)):
                pairs.append(check_cross_venue(
                    asset, asset_legs[i], asset_legs[j], store, window=window,
                    spread_threshold=knobs.get("spread_threshold", SPREAD_THRESHOLD),
                    spread_alerts=knobs.get("spread_alerts", False)))
    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    doc = {"schema_version": 1, "store": str(store_path), "reports": reports, "pairs": pairs,
           "alerts_total": alerts, "warnings_total": warnings}
    return doc, 1 if alerts > 0 else 0


def _flag(item):
    if item["alerts"]:
        return "ALERT"
    if item["warnings"]:
        return "WARN "
    return "ok   "


def _messages(item):
    return ([f"        ALERT {m}" for m in item["alerts"]]
            + [f"        WARN  {m}" for m in item["warnings"]]
            + [f"        note  {m}" for m in item["notes"]])


def table_lines(doc):
    lines = []
    for report in doc["reports"]:
        last = report.get("last_session") or "-"
        missed = report["missed_sessions"] if "missed_sessions" in report else "-"
        rows = report.get("rows") or 0
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/{report['symbol']}: "
                     f"last {last}, {missed} missed, {rows} row(s)")
        resolution = report.get("resolution")
        if resolution:
            lines.append(f"        res   {resolution['distinct']} distinct / {resolution['sessions']} "
                         f"traded, min tick {_tick(resolution['min_tick'])}, "
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
