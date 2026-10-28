"""CRSP-style split-only adjustment as a pure re-derivation.

For a row dated `d`, the cumulative factor is the product of the ratios of
every split whose effective date is strictly after `d`:

    factor(d)      = prod(split.ratio for split if d < split.date)
    price_main(d)  = price_raw(d) / factor(d)
    volume_main(d) = volume_raw(d) * factor(d)

`adjust()` reads only the `*_raw` columns, so applying it again to its own
output yields the same frame. Dividends and the provider `adjustment_factor`
never enter the formula. A frame whose `price_basis` is anything but `raw`
is refused: adjusting a pre-adjusted series would double-adjust it.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from jef_data_rc.actions import SplitEvent, as_split_events, valid_ratio

PRICE_FIELDS = ("open", "high", "low", "close")
RAW_FIELDS = {f: f"{f}_raw" for f in PRICE_FIELDS + ("volume",)}


class AdjustmentError(ValueError):
    """The frame or the split events cannot be adjusted."""


def _checked(splits: Iterable[Any] | None) -> list[SplitEvent]:
    events = as_split_events(splits)
    for e in events:
        if not valid_ratio(e.ratio):
            raise AdjustmentError(f"invalid split ratio {e.ratio!r} on {e.date} ({e.split!r})")
    return events


def row_dates(df: pd.DataFrame) -> np.ndarray:
    """ISO date strings (UTC) for each row of a store frame."""
    if "datetime" not in df.columns:
        raise AdjustmentError("frame has no 'datetime' column")
    dt = pd.to_datetime(df["datetime"], utc=True)
    return dt.dt.strftime("%Y-%m-%d").to_numpy(dtype=object)


def split_factors(dates: Iterable[str], splits: Iterable[Any] | None) -> np.ndarray:
    """Cumulative split factor per ISO date: splits strictly after the date."""
    events = _checked(splits)
    dates = np.asarray(list(dates), dtype=object)
    factor = np.ones(len(dates), dtype="float64")
    for e in events:
        mask = dates < e.date
        factor[mask] = factor[mask] * e.ratio
    return factor


def adjust(df: pd.DataFrame, splits: Iterable[Any] | None) -> pd.DataFrame:
    """Re-derive main OHLCV and `cumulative_split_factor` from raw columns."""
    if "datetime" not in df.columns:
        raise AdjustmentError("cannot adjust: frame has no 'datetime' column")
    missing = [c for c in RAW_FIELDS.values() if c not in df.columns]
    if missing:
        raise AdjustmentError(f"cannot adjust: missing raw column(s): {', '.join(missing)}")
    if "price_basis" in df.columns:
        bases = sorted({str(b) for b in df["price_basis"].dropna().unique()})
        bad = [b for b in bases if b != "raw"]
        if bad or df["price_basis"].isna().any():
            shown = ", ".join(bad) if bad else "null"
            raise AdjustmentError(
                f"refusing to adjust a series with price_basis {shown}: "
                "only raw-basis series can take the split pass (double-adjustment risk)"
            )
    out = df.copy()
    factor = split_factors(row_dates(df), splits)
    for f in PRICE_FIELDS:
        out[f] = df[RAW_FIELDS[f]].to_numpy(dtype="float64") / factor
    out["volume"] = df[RAW_FIELDS["volume"]].to_numpy(dtype="float64") * factor
    out["cumulative_split_factor"] = factor
    return out
