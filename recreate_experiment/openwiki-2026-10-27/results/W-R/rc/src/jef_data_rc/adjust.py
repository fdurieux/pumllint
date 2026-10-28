"""Split-only (CRSP-style) adjustment as a pure re-derivation.

For a row dated ``d`` the cumulative factor is the product of the ratios of
every split whose effective date is strictly after ``d``::

    factor(d)       = product(split.ratio for split if d < split.date)
    price_main(d)   = price_raw(d) / factor(d)
    volume_main(d)  = volume_raw(d) * factor(d)

A bar dated on a split's effective date already trades on the new basis, so
that split contributes nothing to it. Dividends and the provider
``adjustment_factor`` never enter. ``adjust()`` reads ``*_raw`` and never
writes them, so applying it twice equals applying it once.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

RAW_COLUMNS = ("open_raw", "high_raw", "low_raw", "close_raw", "volume_raw")
PRICE_PAIRS = (
    ("open", "open_raw"),
    ("high", "high_raw"),
    ("low", "low_raw"),
    ("close", "close_raw"),
)
DATE_COLUMN = "datetime"


class AdjustmentError(ValueError):
    """The frame or the split events cannot be adjusted safely."""


def check_splits(splits) -> list:
    ordered = sorted(splits, key=lambda s: s.date)
    for s in ordered:
        ratio = s.ratio
        if not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or ratio <= 0:
            raise AdjustmentError(
                f"invalid split ratio {ratio!r} on {s.date} ({s.split!r})"
            )
    return ordered


def _as_days(values) -> np.ndarray:
    """Calendar dates as ``datetime64[D]``."""
    if isinstance(values, pd.Series) and isinstance(values.dtype, pd.DatetimeTZDtype):
        values = values.dt.tz_convert("UTC").dt.tz_localize(None)
    arr = np.asarray(pd.to_datetime(pd.Series(values)).to_numpy())
    return arr.astype("datetime64[D]")


def split_factors(dates, splits) -> np.ndarray:
    """Cumulative split factor per date (strictly-after rule)."""
    days = _as_days(dates)
    factor = np.ones(len(days), dtype="float64")
    for s in check_splits(splits):
        effective = np.datetime64(s.date.isoformat(), "D")
        factor[days < effective] *= float(s.ratio)
    return factor


def adjust(df: pd.DataFrame, splits) -> pd.DataFrame:
    """Re-derive main OHLCV and ``cumulative_split_factor`` from raw columns."""
    if "price_basis" not in df.columns:
        raise AdjustmentError("frame has no price_basis column; refusing to adjust")
    basis = df["price_basis"]
    if (basis != "raw").any() or basis.isna().any():
        found = sorted({str(v) for v in basis.unique() if v != "raw"})
        raise AdjustmentError(
            "refusing to split-adjust a series whose price_basis is not raw "
            f"(found {', '.join(found)}): it would be double-adjusted"
        )
    missing = [c for c in RAW_COLUMNS + (DATE_COLUMN,) if c not in df.columns]
    if missing:
        raise AdjustmentError(
            f"frame lacks required column(s) for adjustment: {', '.join(missing)}"
        )
    out = df.copy()
    factor = split_factors(out[DATE_COLUMN], splits)
    for main, raw in PRICE_PAIRS:
        out[main] = out[raw].to_numpy(dtype="float64") / factor
    out["volume"] = out["volume_raw"].to_numpy(dtype="float64") * factor
    out["cumulative_split_factor"] = factor
    return out
