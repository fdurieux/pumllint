"""The split-only adjustment: mains re-derived from the immutable raw columns."""
from __future__ import annotations

import math

import numpy as np

RAW_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]


class AdjustmentRefused(ValueError):
    """An adjustment that must not run."""


def _event_fields(event):
    if isinstance(event, dict):
        return str(event["date"]), event["ratio"]
    return str(event[0]), event[1]


def check_ratios(splits):
    for event in splits:
        day, ratio = _event_fields(event)
        try:
            value = float(ratio)
        except (TypeError, ValueError):
            raise AdjustmentRefused(f"split {day} has degenerate ratio {ratio!r}") from None
        if not math.isfinite(value) or value <= 0:
            raise AdjustmentRefused(f"split {day} has degenerate ratio {ratio!r}")


def split_factors(days, splits):
    """Cumulative split factor per row; `days` are the rows' UTC dates as YYYY-MM-DD text."""
    check_ratios(splits)
    days = np.asarray(days, dtype=object)
    factors = np.ones(len(days), dtype="float64")
    for event in splits:
        day, ratio = _event_fields(event)
        before = days < day
        factors[before] = factors[before] * np.float64(ratio)
    return factors


def utc_days(datetimes):
    return np.asarray(datetimes.dt.strftime("%Y-%m-%d").tolist(), dtype=object)


def adjust(frame, splits):
    """Return a new frame whose mains are `*_raw` divided (volume: multiplied) by the factor."""
    if "price_basis" in frame.columns:
        non_raw = sorted({str(v) for v in frame["price_basis"].tolist() if v != "raw"})
        if non_raw:
            raise AdjustmentRefused(
                f"price_basis {non_raw} is already adjusted at the provider - applying split "
                f"events would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    factors = split_factors(utc_days(frame["datetime"]), splits)
    out = frame.copy()
    for column in ("open", "high", "low", "close"):
        out[column] = frame[f"{column}_raw"].to_numpy(dtype="float64") / factors
    out["volume"] = frame["volume_raw"].to_numpy(dtype="float64") * factors
    out["cumulative_split_factor"] = factors
    return out
