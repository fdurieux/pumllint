"""Price basis resolution and the pure split-adjustment pass."""
import math
from datetime import date

import numpy as np

RAW_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]
PRICE_PAIRS = [("open", "open_raw"), ("high", "high_raw"), ("low", "low_raw"),
               ("close", "close_raw")]
DERIVED_COLUMNS = ["open", "high", "low", "close", "volume", "cumulative_split_factor"]


class AdjustmentRefused(ValueError):
    """An adjustment that would corrupt the series."""


def resolve_price_basis(provider, asset_type):
    """Basis from the provider and the declared asset_type, never the symbol suffix."""
    if provider == "eodhd" and asset_type != "crypto":
        return "raw"
    return "split_adjusted"


def _event_date(event):
    value = event.date if hasattr(event, "date") else event["date"]
    return value


def _event_ratio(event):
    return event.ratio if hasattr(event, "ratio") else event["ratio"]


def check_ratios(splits):
    for event in splits:
        ratio = _event_ratio(event)
        try:
            bad = not math.isfinite(ratio) or ratio <= 0
        except TypeError:
            bad = True
        if bad:
            raise AdjustmentRefused(f"split {_event_date(event)} has degenerate ratio {ratio!r}")


def _as_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def split_factors(row_dates, splits):
    """Cumulative split factor per row: product of ratios of splits dated strictly after it."""
    check_ratios(splits)
    days = np.array([d.toordinal() for d in row_dates], dtype=np.int64)
    factor = np.ones(len(days), dtype=np.float64)
    for event in splits:
        cutoff = _as_date(_event_date(event)).toordinal()
        mask = days < cutoff
        factor[mask] = factor[mask] * np.float64(_event_ratio(event))
    return factor


def row_dates(frame):
    """UTC calendar date of every row's datetime."""
    return list(frame["datetime"].dt.date)


def adjust(frame, splits):
    """Return a new frame whose mains are re-derived from the *_raw columns and the splits."""
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    if "price_basis" in frame.columns:
        foreign = sorted({str(v) for v in frame["price_basis"]} - {"raw"})
        if foreign:
            raise AdjustmentRefused(
                f"price_basis {foreign} is already adjusted at the provider - applying split "
                f"events would double-adjust (docs/DATA_CONTRACT.md §2)")
    factor = split_factors(row_dates(frame), splits)
    out = frame.copy()
    for main, raw in PRICE_PAIRS:
        out[main] = out[raw].to_numpy(dtype=np.float64) / factor
    out["volume"] = out["volume_raw"].to_numpy(dtype=np.float64) * factor
    out["cumulative_split_factor"] = factor
    return out
