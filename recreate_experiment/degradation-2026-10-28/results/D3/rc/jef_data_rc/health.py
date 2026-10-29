"""Read-only daily health checks: per-source reports and cross-venue pairs."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np

from .actions import CorporateActionsStore
from .adjust import session_days
from .classification import compare
from .store import ParquetStore
from .sync import select_legs

DEFAULTS = {"window": 10, "jump_threshold": 0.40, "staleness_k": 2, "resolution_window": 500,
            "resolution_k": 0.20, "flat_k": 0.25, "gap_k": 5, "spread_threshold": 0.005,
            "spread_alerts": False}
ACTIONS_STALE_SESSIONS = 2
MIN_RESOLUTION_SESSIONS = 60
WEEKDAY_TYPES = ("stock", "etf")


def expected_sessions(first: date, second: date, asset_type: str) -> int:
    """Calendar days strictly between two dates, weekdays only for stock and etf."""
    count = 0
    day = first + timedelta(days=1)
    while day < second:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count


def _today(now) -> date:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.date()
    return now.astimezone(timezone.utc).date()


def _stamp_date(stamp: datetime) -> date:
    if stamp.tzinfo is None:
        return stamp.date()
    return stamp.astimezone(timezone.utc).date()


def _longest_zero_run(volume: np.ndarray):
    best_len, best_start = 0, None
    run_len, run_start = 0, None
    for i, v in enumerate(volume):
        if v == 0:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    return best_len, best_start


def measure_resolution(frame, window: int):
    volume = frame["volume"].to_numpy(dtype=np.float64)
    traded = volume > 0

    def pick(column):
        values = frame[column].to_numpy(dtype=np.float64)[traded]
        values = values[~np.isnan(values)]
        values = values[values > 0]
        return values[-window:] if window > 0 else values[:0]

    values = pick("close_raw")
    if len(values) == 0:
        values = pick("close")
    if len(values) < MIN_RESOLUTION_SESSIONS:
        return None
    sessions = int(len(values))
    distinct_values = np.unique(values)
    distinct = int(len(distinct_values))
    if distinct > 1:
        with np.errstate(divide="ignore", invalid="ignore"):
            ticks = (distinct_values[1:] - distinct_values[:-1]) / distinct_values[:-1]
        min_tick = float(ticks.min())
    else:
        min_tick = None
    flat_pairs = int((values[1:] == values[:-1]).sum())
    flat_share = flat_pairs / (sessions - 1)
    return {"sessions": sessions, "distinct": distinct, "min_tick": min_tick,
            "flat_share": float(flat_share)}


def _tick_text(min_tick) -> str:
    return "n/a" if min_tick is None else f"{min_tick:.4%}"


def check_source(leg: dict, store: ParquetStore, actions: CorporateActionsStore, today: date,
                 knobs: dict) -> dict:
    report = {"asset": leg["asset"], "exchange": leg["exchange"], "symbol": leg["symbol"],
              "alerts": [], "warnings": [], "notes": []}
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    if leg["provider"] == "eodhd":
        verdict, message = compare(exchange, symbol, asset_type)
        report["declared_class_check"] = verdict
        if verdict == "disagree":
            report["warnings"].append(f"declared class: {message}")
        else:
            report["notes"].append(f"declared class: {message}")
    last = store.latest_date(exchange, symbol)
    if last is None:
        report["alerts"].append("never filled - no stored rows (jef-data sync first)")
        return report
    frame = store.load(exchange, symbol)
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = missed
    report["rows"] = int(len(frame))
    if missed >= knobs["staleness_k"]:
        report["alerts"].append(
            f"stale: {missed} expected session(s) missing since {last.isoformat()} "
            f"(multi-day holidays can trip this - verify before acting)")
    if last == today:
        report["notes"].append("today-dated bar stored (pre-close serve? the next tail-refresh heals it)")

    days = [str(d) for d in session_days(frame["datetime"])]
    volume = frame["volume"].to_numpy(dtype=np.float64)
    zeros = int((volume == 0).sum())
    if zeros:
        note = f"{zeros} zero-volume row(s), dropped at the seam by pinned policy"
        run_len, run_start = _longest_zero_run(volume)
        if run_len > 1:
            note += f" - largest contiguous run {run_len}, {days[run_start]}..{days[run_start + run_len - 1]}"
        report["notes"].append(note)

    close = frame["close"].to_numpy(dtype=np.float64)
    surviving = [days[i] for i in range(len(days)) if volume[i] > 0 and not np.isnan(close[i])]
    gap = None
    for prev, nxt in zip(surviving, surviving[1:]):
        d0, d1 = date.fromisoformat(prev), date.fromisoformat(nxt)
        if (d1 - d0).days <= 1:
            continue
        count = expected_sessions(d0, d1, asset_type)
        if count > 0 and (gap is None or count > gap[0]):
            gap = (count, prev, nxt)
    if gap is not None and gap[0] >= knobs["gap_k"]:
        report["notes"].append(
            f"post-seam continuity: {gap[0]} expected session(s) absent between {gap[1]} and {gap[2]} - "
            f"the seam's output splices across this hole; verify the provider era before modelling "
            f"(docs/DATA_CONTRACT.md §1)")

    resolution = measure_resolution(frame, knobs["resolution_window"])
    if resolution is not None:
        report["resolution"] = resolution
        if (resolution["distinct"] / resolution["sessions"] < knobs["resolution_k"]
                or resolution["flat_share"] > knobs["flat_k"]):
            report["notes"].append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick {_tick_text(resolution['min_tick'])}, "
                f"{resolution['flat_share']:.1%} flat - the provider's quoting grid, verify before "
                f"modelling (docs/DATA_CONTRACT.md §7.8)")

    split_days = set()
    if leg["actions"]:
        split_days = {e.date.isoformat() for e in actions.load_splits(symbol)}
    n = len(frame)
    for i in range(max(1, n - knobs["window"]), n):
        previous = close[i - 1]
        if previous == 0:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            move = close[i] / previous - 1.0
        if abs(move) > knobs["jump_threshold"] and days[i] not in split_days:
            report["alerts"].append(
                f"phantom-split-shaped jump {move:+.1%} on {days[i]} with no same-day split event - "
                f"check corporate actions (docs/DATA_CONTRACT.md §2)")

    if leg["actions"]:
        stamp = actions.last_updated(symbol)
        if stamp is None:
            report["alerts"].append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = _stamp_date(stamp)
            sessions = expected_sessions(stamp_day, today, asset_type)
            if sessions >= ACTIONS_STALE_SESSIONS:
                report["alerts"].append(
                    f"corporate actions stale: {sessions} refresh session(s) missed since "
                    f"{stamp_day.isoformat()} - run jef-data sync")
    return report


def check_cross_venue(asset: str, leg_a: dict, leg_b: dict, store: ParquetStore, knobs: dict) -> dict:
    a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    threshold = knobs["spread_threshold"]
    pair = {"asset": asset, "kind": "cross_venue", "a": a, "b": b, "common_session": None,
            "spread": None, "threshold": threshold, "alerts": [], "warnings": [], "notes": []}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((a, frame_a), (b, frame_b)):
        if not len(frame):
            pair["notes"].append(f"{label} has no stored rows - spread not measured")
            return pair
    window = knobs["window"]
    tail_a = frame_a.iloc[-window:] if window > 0 else frame_a.iloc[:0]
    tail_b = frame_b.iloc[-window:] if window > 0 else frame_b.iloc[:0]
    days_a = [str(d) for d in session_days(tail_a["datetime"])] if len(tail_a) else []
    days_b = [str(d) for d in session_days(tail_b["datetime"])] if len(tail_b) else []
    common = set(days_a) & set(days_b)
    if not common:
        pair["notes"].append(f"no common session in the newest {window} - spread not measured "
                             f"(see the staleness check)")
        return pair
    day = max(common)
    close_a = float(tail_a["close"].to_numpy(dtype=np.float64)[[i for i, d in enumerate(days_a) if d == day][-1]])
    close_b = float(tail_b["close"].to_numpy(dtype=np.float64)[[i for i, d in enumerate(days_b) if d == day][-1]])
    mid = (close_a + close_b) / 2
    if mid == 0:
        pair["notes"].append(f"zero mid price on {day} - spread not measured")
        return pair
    spread = abs(close_a - close_b) / mid
    pair["common_session"] = day
    pair["spread"] = spread
    pair["notes"].append(f"close spread {spread:.4%} on {day} ({a} {close_a:g} vs {b} {close_b:g})")
    if spread > threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {day} exceeds {threshold:.4%} "
                   f"({a} {close_a:g} vs {b} {close_b:g}) - feed problem or venue distress; verify "
                   f"before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        if knobs["spread_alerts"]:
            pair["alerts"].append(finding)
        else:
            pair["warnings"].append(finding)
    return pair


def run_status(universe: dict, store_path, *, assets=None, providers=None, now=None, **knobs) -> dict:
    settings = dict(DEFAULTS)
    settings.update({k: v for k, v in knobs.items() if v is not None})
    today = _today(now)
    legs = [leg for leg in select_legs(universe, assets, providers) if leg["provider"] != "yahoo-csv"]
    store = ParquetStore(store_path)
    actions = CorporateActionsStore(store_path)
    reports = [check_source(leg, store, actions, today, settings) for leg in legs]
    by_asset: dict = {}
    for leg in legs:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, asset_legs in by_asset.items():
        if len(asset_legs) < 2:
            continue
        for i in range(len(asset_legs)):
            for j in range(i + 1, len(asset_legs)):
                pairs.append(check_cross_venue(asset, asset_legs[i], asset_legs[j], store, settings))
    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    return {"schema_version": 1, "store": str(store_path), "reports": reports, "pairs": pairs,
            "alerts_total": alerts, "warnings_total": warnings}


def exit_code(doc: dict) -> int:
    return 1 if doc["alerts_total"] > 0 else 0


def _flag(item: dict) -> str:
    if item["alerts"]:
        return "ALERT"
    if item["warnings"]:
        return "WARN "
    return "ok   "


def _findings(item: dict) -> list:
    lines = [f"        ALERT {text}" for text in item["alerts"]]
    lines += [f"        WARN  {text}" for text in item["warnings"]]
    lines += [f"        note  {text}" for text in item["notes"]]
    return lines


def table_lines(doc: dict) -> list:
    lines = []
    for report in doc["reports"]:
        lines.append(f"{_flag(report)} {report['asset']:>6} {report['exchange']}/{report['symbol']}: "
                     f"last {report.get('last_session', '-')}, {report.get('missed_sessions', '-')} missed, "
                     f"{report.get('rows', 0)} row(s)")
        resolution = report.get("resolution")
        if resolution is not None:
            lines.append(f"        res   {resolution['distinct']} distinct / {resolution['sessions']} traded, "
                         f"min tick {_tick_text(resolution['min_tick'])}, {resolution['flat_share']:.2%} flat")
        lines += _findings(report)
    for pair in doc["pairs"]:
        lines.append(f"{_flag(pair)} {pair['asset']:>6} cross-venue {pair['a']} vs {pair['b']}")
        lines += _findings(pair)
    tail = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        tail += f", {len(doc['pairs'])} venue pair(s)"
    tail += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        tail += f", {doc['warnings_total']} warning(s)"
    lines.append(tail)
    return lines
