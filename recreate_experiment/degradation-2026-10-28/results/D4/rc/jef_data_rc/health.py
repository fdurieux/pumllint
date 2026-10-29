"""Read-only daily health checks: per-source reports, venue pairs, the envelope."""
from __future__ import annotations

import datetime as _dt

import numpy as np

from . import classification
from .actions import CorporateActionsStore
from .store import ParquetStore
from .sync import select_legs, utc_today

DEFAULT_WINDOW = 10
DEFAULT_JUMP_THRESHOLD = 0.40
DEFAULT_STALENESS = 2
DEFAULT_RESOLUTION_WINDOW = 500
DEFAULT_RESOLUTION_K = 0.20
DEFAULT_FLAT_K = 0.25
DEFAULT_GAP_K = 5
DEFAULT_SPREAD_THRESHOLD = 0.005
ACTIONS_STALE_SESSIONS = 2
MIN_RESOLUTION_SESSIONS = 60
WEEKDAY_TYPES = ("stock", "etf")


def expected_sessions(first: _dt.date, second: _dt.date, asset_type: str) -> int:
    """Calendar days strictly between the two dates (weekdays only for stock/etf)."""
    count = 0
    day = first + _dt.timedelta(days=1)
    while day < second:
        if asset_type not in WEEKDAY_TYPES or day.weekday() < 5:
            count += 1
        day += _dt.timedelta(days=1)
    return count


def _row_dates(frame) -> list:
    return [ts.date() for ts in frame["datetime"]]


def _zero_volume_note(volume: np.ndarray, dates: list):
    zero = volume == 0
    n = int(zero.sum())
    if n == 0:
        return None
    best_len, best_start = 0, 0
    run_len, run_start = 0, 0
    for i, flag in enumerate(zero.tolist()):
        if flag:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_len, best_start = run_len, run_start
        else:
            run_len = 0
    note = f"{n} zero-volume row(s), dropped at the seam by pinned policy"
    if best_len > 1:
        note += (f" - largest contiguous run {best_len}, "
                 f"{dates[best_start].isoformat()}..{dates[best_start + best_len - 1].isoformat()}")
    return note


def _post_seam_gap(volume: np.ndarray, close: np.ndarray, dates: list, asset_type: str):
    keep = (volume > 0) & ~np.isnan(close)
    surviving = [d for d, k in zip(dates, keep.tolist()) if k]
    best = None
    for prev, nxt in zip(surviving, surviving[1:]):
        if (nxt - prev).days <= 1:
            continue
        count = expected_sessions(prev, nxt, asset_type)
        if count > 0 and (best is None or count > best[0]):
            best = (count, prev, nxt)
    return best


def _resolution(frame, window: int):
    volume = frame["volume"].to_numpy(dtype=np.float64)
    traded = volume > 0
    values = None
    for column in ("close_raw", "close"):
        series = frame[column].to_numpy(dtype=np.float64)[traded]
        series = series[~np.isnan(series)]
        series = series[series > 0]
        series = series[-window:] if window > 0 else series[:0]
        if len(series):
            values = series
            break
    if values is None or len(values) < MIN_RESOLUTION_SESSIONS:
        return None
    sessions = int(len(values))
    distinct_values = np.unique(values)
    distinct = int(len(distinct_values))
    if distinct > 1:
        ticks = np.diff(distinct_values) / distinct_values[:-1]
        min_tick = float(ticks.min())
    else:
        min_tick = None
    flat = int(np.sum(values[1:] == values[:-1]))
    flat_share = float(flat / (sessions - 1))
    return {"sessions": sessions, "distinct": distinct, "min_tick": min_tick,
            "flat_share": flat_share}


def check_source(leg: dict, *, store: ParquetStore, actions: CorporateActionsStore,
                 today: _dt.date, window: int, jump_threshold: float, staleness: int,
                 resolution_window: int, resolution_k: float, flat_k: float,
                 gap_k: int) -> dict:
    exchange, symbol, asset_type = leg["exchange"], leg["symbol"], leg["asset_type"]
    report = {"asset": leg["asset"], "exchange": exchange, "symbol": symbol,
              "alerts": [], "warnings": [], "notes": []}
    if leg["provider"] == "eodhd":
        verdict, message = classification.compare(exchange, symbol, asset_type)
        report["declared_class_check"] = verdict
        target = report["warnings"] if verdict == "disagree" else report["notes"]
        target.append(f"declared class: {message}")
    last = store.latest_date(exchange, symbol)
    if last is None:
        report["alerts"].append("never filled - no stored rows (jef-data sync first)")
        return report
    frame = store.load(exchange, symbol)
    split_dates: set = set()
    stamp = None
    if leg["actions"]:
        split_dates = {str(e.date) for e in actions.load_splits(symbol)}
        stamp = actions.last_updated(symbol)
    missed = expected_sessions(last, today, asset_type)
    report["last_session"] = last.isoformat()
    report["missed_sessions"] = int(missed)
    report["rows"] = int(len(frame))
    if missed >= staleness:
        report["alerts"].append(
            f"stale: {missed} expected session(s) missing since {last.isoformat()} "
            "(multi-day holidays can trip this - verify before acting)")
    if last == today:
        report["notes"].append(
            "today-dated bar stored (pre-close serve? the next tail-refresh heals it)")
    dates = _row_dates(frame)
    volume = frame["volume"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    note = _zero_volume_note(volume, dates)
    if note:
        report["notes"].append(note)
    gap = _post_seam_gap(volume, close, dates, asset_type)
    if gap is not None and gap[0] >= gap_k:
        report["notes"].append(
            f"post-seam continuity: {gap[0]} expected session(s) absent between "
            f"{gap[1].isoformat()} and {gap[2].isoformat()} - the seam's output splices across "
            "this hole; verify the provider era before modelling (docs/DATA_CONTRACT.md §1)")
    resolution = _resolution(frame, resolution_window)
    if resolution is not None:
        report["resolution"] = resolution
        ratio = resolution["distinct"] / resolution["sessions"]
        if ratio < resolution_k or resolution["flat_share"] > flat_k:
            tick = "n/a" if resolution["min_tick"] is None else f"{resolution['min_tick']:.4%}"
            report["notes"].append(
                f"coarse price resolution: {resolution['distinct']} distinct close(s) in "
                f"{resolution['sessions']} traded session(s), min tick {tick}, "
                f"{resolution['flat_share']:.1%} flat - the provider's quoting grid, verify "
                "before modelling (docs/DATA_CONTRACT.md §7.8)")
    n = len(close)
    for i in range(max(1, n - window), n):
        prev = close[i - 1]
        if prev == 0:
            continue
        move = close[i] / prev - 1.0
        day = dates[i].isoformat()
        if abs(move) > jump_threshold and day not in split_dates:
            report["alerts"].append(
                f"phantom-split-shaped jump {move:+.1%} on {day} with no same-day split event - "
                "check corporate actions (docs/DATA_CONTRACT.md §2)")
    if leg["actions"]:
        if stamp is None:
            report["alerts"].append("corporate actions stale: never synced - run jef-data sync")
        else:
            stamp_day = stamp.astimezone(_dt.timezone.utc).date()
            behind = expected_sessions(stamp_day, today, asset_type)
            if behind >= ACTIONS_STALE_SESSIONS:
                report["alerts"].append(
                    f"corporate actions stale: {behind} refresh session(s) missed since "
                    f"{stamp_day.isoformat()} - run jef-data sync")
    return report


def check_cross_venue(asset: str, leg_a: dict, leg_b: dict, *, store: ParquetStore,
                      window: int, threshold: float, promote: bool) -> dict:
    a = f"{leg_a['exchange']}/{leg_a['symbol']}"
    b = f"{leg_b['exchange']}/{leg_b['symbol']}"
    pair = {"asset": asset, "kind": "cross_venue", "a": a, "b": b, "common_session": None,
            "spread": None, "threshold": threshold, "alerts": [], "warnings": [], "notes": []}
    frame_a = store.load(leg_a["exchange"], leg_a["symbol"])
    frame_b = store.load(leg_b["exchange"], leg_b["symbol"])
    for label, frame in ((a, frame_a), (b, frame_b)):
        if len(frame) == 0:
            pair["notes"].append(f"{label} has no stored rows - spread not measured")
            return pair
    tail_a = frame_a.tail(window) if window > 0 else frame_a.iloc[:0]
    tail_b = frame_b.tail(window) if window > 0 else frame_b.iloc[:0]
    dates_a = _row_dates(tail_a)
    dates_b = _row_dates(tail_b)
    common = set(dates_a) & set(dates_b)
    if not common:
        pair["notes"].append(
            f"no common session in the newest {window} - spread not measured (see the staleness check)")
        return pair
    day = max(common)
    close_a = float([c for d, c in zip(dates_a, tail_a["close"].tolist()) if d == day][-1])
    close_b = float([c for d, c in zip(dates_b, tail_b["close"].tolist()) if d == day][-1])
    mid = (close_a + close_b) / 2
    if mid == 0:
        pair["notes"].append(f"zero mid price on {day.isoformat()} - spread not measured")
        return pair
    spread = abs(close_a - close_b) / mid
    pair["common_session"] = day.isoformat()
    pair["spread"] = float(spread)
    pair["notes"].append(
        f"close spread {spread:.4%} on {day.isoformat()} ({a} {close_a:g} vs {b} {close_b:g})")
    if spread > threshold:
        finding = (f"cross-venue close spread {spread:.4%} on {day.isoformat()} exceeds "
                   f"{threshold:.4%} ({a} {close_a:g} vs {b} {close_b:g}) - feed problem or venue "
                   "distress; verify before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)")
        (pair["alerts"] if promote else pair["warnings"]).append(finding)
    return pair


def status_report(universe: dict, store_path, *, assets=None, providers=None, now=None,
                  window=DEFAULT_WINDOW, jump_threshold=DEFAULT_JUMP_THRESHOLD,
                  staleness=DEFAULT_STALENESS, resolution_window=DEFAULT_RESOLUTION_WINDOW,
                  resolution_k=DEFAULT_RESOLUTION_K, flat_k=DEFAULT_FLAT_K, gap_k=DEFAULT_GAP_K,
                  spread_threshold=DEFAULT_SPREAD_THRESHOLD, spread_alerts=False) -> tuple:
    legs = [leg for leg in select_legs(universe, assets, providers)
            if leg["provider"] != "yahoo-csv"]
    today = utc_today(now)
    store = ParquetStore(store_path)
    actions = CorporateActionsStore(store_path)
    reports = [check_source(leg, store=store, actions=actions, today=today, window=window,
                            jump_threshold=jump_threshold, staleness=staleness,
                            resolution_window=resolution_window, resolution_k=resolution_k,
                            flat_k=flat_k, gap_k=gap_k)
               for leg in legs]
    by_asset: dict = {}
    for leg in legs:
        by_asset.setdefault(leg["asset"], []).append(leg)
    pairs = []
    for asset, group in by_asset.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pairs.append(check_cross_venue(asset, group[i], group[j], store=store,
                                               window=window, threshold=spread_threshold,
                                               promote=spread_alerts))
    alerts = sum(len(r["alerts"]) for r in reports) + sum(len(p["alerts"]) for p in pairs)
    warnings = sum(len(r["warnings"]) for r in reports) + sum(len(p["warnings"]) for p in pairs)
    doc = {"schema_version": 1, "store": str(store_path), "reports": reports, "pairs": pairs,
           "alerts_total": alerts, "warnings_total": warnings}
    return doc, (1 if alerts > 0 else 0)


def render_table(doc: dict) -> list:
    lines = []

    def flag(entry):
        if entry["alerts"]:
            return "ALERT"
        if entry["warnings"]:
            return "WARN "
        return "ok   "

    def findings(entry):
        out = [f"        ALERT {t}" for t in entry["alerts"]]
        out += [f"        WARN  {t}" for t in entry["warnings"]]
        out += [f"        note  {t}" for t in entry["notes"]]
        return out

    for r in doc["reports"]:
        last = r.get("last_session") or "-"
        missed = r["missed_sessions"] if "missed_sessions" in r else "-"
        rows = r.get("rows") or 0
        lines.append(f"{flag(r)} {r['asset']:>6} {r['exchange']}/{r['symbol']}: last {last}, "
                     f"{missed} missed, {rows} row(s)")
        res = r.get("resolution")
        if res is not None:
            tick = "n/a" if res["min_tick"] is None else f"{res['min_tick']:.4%}"
            lines.append(f"        res   {res['distinct']} distinct / {res['sessions']} traded, "
                         f"min tick {tick}, {res['flat_share']:.2%} flat")
        lines.extend(findings(r))
    for p in doc["pairs"]:
        lines.append(f"{flag(p)} {p['asset']:>6} cross-venue {p['a']} vs {p['b']}")
        lines.extend(findings(p))
    summary = f"{len(doc['reports'])} source(s)"
    if doc["pairs"]:
        summary += f", {len(doc['pairs'])} venue pair(s)"
    summary += f", {doc['alerts_total']} alert(s)"
    if doc["warnings_total"]:
        summary += f", {doc['warnings_total']} warning(s)"
    lines.append(summary)
    return lines
