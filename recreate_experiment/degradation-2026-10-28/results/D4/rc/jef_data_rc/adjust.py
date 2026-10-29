"""Basis resolution and the pure split-adjustment pass."""
from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np

RAW_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]
PRICE_PAIRS = [("open", "open_raw"), ("high", "high_raw"), ("low", "low_raw"), ("close", "close_raw")]


class AdjustmentRefused(ValueError):
    """An adjustment that must not run."""


class SplitEvent(NamedTuple):
    date: str
    ratio: float
    split_string: str | None = None


def price_basis(provider: str, asset_type: str) -> str:
    if provider == "eodhd" and asset_type != "crypto":
        return "raw"
    return "split_adjusted"


def check_ratios(splits) -> None:
    for event in splits:
        ratio = float(event.ratio)
        if not math.isfinite(ratio) or ratio <= 0:
            raise AdjustmentRefused(f"split {event.date} has degenerate ratio {ratio!r}")


def cumulative_factor(days, splits) -> np.ndarray:
    """Per-row product of the ratios of splits dated strictly after the row's date.

    `days` holds the rows' UTC calendar dates as YYYY-MM-DD text."""
    check_ratios(splits)
    days = np.asarray(days, dtype=object)
    factor = np.ones(len(days), dtype=np.float64)
    for event in splits:
        ratio = np.float64(float(event.ratio))
        before = np.array([d < str(event.date) for d in days], dtype=bool)
        factor = np.where(before, factor * ratio, factor)
    return factor


def utc_days(frame) -> list:
    return frame["datetime"].dt.strftime("%Y-%m-%d").tolist()


def adjust(frame, splits):
    """Re-derive the main OHLCV columns from the *_raw columns and the split events."""
    if "price_basis" in frame.columns:
        foreign = sorted({str(v) for v in frame["price_basis"].tolist()} - {"raw"})
        if foreign:
            raise AdjustmentRefused(
                f"price_basis {foreign} is already adjusted at the provider - applying split "
                "events would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    factor = cumulative_factor(utc_days(frame), splits)
    out = frame.copy()
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        for main, raw in PRICE_PAIRS:
            out[main] = frame[raw].to_numpy(dtype=np.float64) / factor
        out["volume"] = frame["volume_raw"].to_numpy(dtype=np.float64) * factor
    out["cumulative_split_factor"] = factor
    return out
