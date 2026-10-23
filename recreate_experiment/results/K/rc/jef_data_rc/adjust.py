"""The split adjustment: main columns derived from the raw columns and split events."""
from __future__ import annotations

import math

import numpy as np

RAW_PRICE_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw"]
RAW_COLUMNS = RAW_PRICE_COLUMNS + ["volume_raw"]
MAIN_PRICE_COLUMNS = ["open", "high", "low", "close"]


class AdjustmentRefused(ValueError):
    """An adjustment that must not run."""


def _event_day(event):
    date = event.date
    return date if isinstance(date, str) else date.isoformat()


def check_ratios(splits):
    for event in splits:
        ratio = event.ratio
        if not math.isfinite(ratio) or ratio <= 0:
            raise AdjustmentRefused(f"split {_event_day(event)} has degenerate ratio {ratio!r}")


def split_factors(days, splits):
    """The cumulative split factor of each row, rows given as YYYY-MM-DD strings."""
    check_ratios(splits)
    days = np.asarray(days, dtype=object)
    factors = np.ones(len(days), dtype=np.float64)
    for event in splits:
        before = days < _event_day(event)
        factors = np.where(before, factors * np.float64(event.ratio), factors)
    return factors


def row_days(datetimes):
    """UTC calendar dates (YYYY-MM-DD) of a datetime series."""
    return np.asarray(datetimes.dt.tz_convert("UTC").dt.strftime("%Y-%m-%d").tolist(),
                      dtype=object)


def adjust(frame, splits):
    """A new frame whose main columns are re-derived from *_raw and the split events."""
    if "price_basis" in frame.columns:
        non_raw = sorted({str(v) for v in frame["price_basis"].tolist() if v != "raw"})
        if non_raw:
            raise AdjustmentRefused(
                f"price_basis {non_raw} is already adjusted at the provider - applying "
                f"split events would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    factors = split_factors(row_days(frame["datetime"]), splits)
    out = frame.copy()
    for main, raw in zip(MAIN_PRICE_COLUMNS, RAW_PRICE_COLUMNS):
        out[main] = frame[raw].to_numpy(dtype=np.float64) / factors
    out["volume"] = frame["volume_raw"].to_numpy(dtype=np.float64) * factors
    out["cumulative_split_factor"] = factors
    return out
