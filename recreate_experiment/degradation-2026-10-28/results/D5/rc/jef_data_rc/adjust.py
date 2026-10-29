"""The split adjustment: a pure function of the *_raw columns and split events."""
from __future__ import annotations

import math

import numpy as np

RAW_PRICE_COLUMNS = ("open_raw", "high_raw", "low_raw", "close_raw")
REQUIRED = RAW_PRICE_COLUMNS + ("volume_raw", "datetime")


class AdjustmentRefused(ValueError):
    """An adjustment that would corrupt the series."""


def utc_days(datetimes) -> np.ndarray:
    """UTC calendar days of a tz-aware datetime Series, as datetime64[D]."""
    naive = datetimes.dt.tz_convert("UTC").dt.tz_localize(None)
    return naive.to_numpy().astype("datetime64[D]")


def check_ratios(splits) -> None:
    for event in splits:
        ratio = event.ratio
        if not math.isfinite(ratio) or ratio <= 0:
            raise AdjustmentRefused(f"split {event.date} has degenerate ratio {ratio!r}")


def split_factors(days: np.ndarray, splits) -> np.ndarray:
    """Cumulative split factor per row: product of ratios of splits strictly after it."""
    check_ratios(splits)
    factor = np.ones(len(days), dtype=np.float64)
    for event in splits:
        before = days < np.datetime64(event.date, "D")
        factor[before] = factor[before] * np.float64(event.ratio)
    return factor


def adjust(frame, splits):
    """Re-derive main OHLCV and the factor from *_raw; return a new frame."""
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    if "price_basis" in frame.columns:
        bases = sorted({str(v) for v in frame["price_basis"].tolist()} - {"raw"})
        if bases:
            raise AdjustmentRefused(
                f"price_basis {bases} is already adjusted at the provider - applying "
                "split events would double-adjust (docs/DATA_CONTRACT.md §2)")
    check_ratios(splits)
    factor = split_factors(utc_days(frame["datetime"]), splits)
    out = frame.copy()
    for main in ("open", "high", "low", "close"):
        out[main] = out[f"{main}_raw"].to_numpy(dtype=np.float64) / factor
    out["volume"] = out["volume_raw"].to_numpy(dtype=np.float64) * factor
    out["cumulative_split_factor"] = factor
    return out
