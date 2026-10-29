"""The split adjustment: main OHLCV re-derived from the *_raw columns and split events."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

RAW_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]
PRICE_COLUMNS = ["open", "high", "low", "close"]


class AdjustmentRefused(ValueError):
    """An adjustment that must not run."""


def check_ratios(splits) -> None:
    for event in splits:
        ratio = event.ratio
        if not (isinstance(ratio, (int, float)) and math.isfinite(ratio) and ratio > 0):
            raise AdjustmentRefused(f"split {event.date.isoformat()} has degenerate ratio {ratio!r}")


def session_days(datetimes: pd.Series) -> np.ndarray:
    """UTC calendar dates of a tz-aware datetime column, as datetime64[D]."""
    values = pd.Series(datetimes).dt.tz_convert("UTC").dt.tz_localize(None)
    return values.to_numpy().astype("datetime64[D]")


def split_factor(days: np.ndarray, splits) -> np.ndarray:
    """Cumulative split factor per row: product of ratios of splits dated strictly after it."""
    check_ratios(splits)
    factor = np.ones(len(days), dtype=np.float64)
    for event in splits:
        mask = days < np.datetime64(event.date.isoformat(), "D")
        factor[mask] = factor[mask] * float(event.ratio)
    return factor


def adjust(frame: pd.DataFrame, splits) -> pd.DataFrame:
    """A new frame with open/high/low/close/volume and the factor derived from raw."""
    if "price_basis" in frame.columns:
        bases = sorted({str(v) for v in frame["price_basis"].tolist() if str(v) != "raw"})
        if bases:
            raise AdjustmentRefused(
                f"price_basis {bases} is already adjusted at the provider - applying split events "
                f"would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    out = frame.copy()
    factor = split_factor(session_days(frame["datetime"]), splits)
    factor32 = factor.astype(np.float32)
    for column in PRICE_COLUMNS:
        raw32 = frame[f"{column}_raw"].to_numpy(dtype=np.float64).astype(np.float32)
        out[column] = (raw32 / factor32).astype(np.float64)
    out["volume"] = frame["volume_raw"].to_numpy(dtype=np.float64) * factor
    out["cumulative_split_factor"] = factor
    return out
