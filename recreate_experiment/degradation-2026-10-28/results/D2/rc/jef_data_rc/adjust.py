"""The split adjustment: a pure function of the *_raw columns and the split events."""
import math

import numpy as np

RAW_PRICE_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw"]
RAW_COLUMNS = RAW_PRICE_COLUMNS + ["volume_raw"]


class AdjustmentRefused(ValueError):
    """An adjustment that would corrupt the series."""


def _event_day(event):
    return event.date.isoformat() if hasattr(event.date, "isoformat") else str(event.date)


def validate_splits(splits):
    for event in splits:
        ratio = event.ratio
        if not math.isfinite(ratio) or ratio <= 0:
            raise AdjustmentRefused(f"split {event.date} has degenerate ratio {ratio!r}")


def split_factors(days, splits):
    """Cumulative split factor per row; `days` are the rows' UTC dates as YYYY-MM-DD."""
    validate_splits(splits)
    days = list(days)
    factors = np.ones(len(days), dtype="float64")
    for event in splits:
        cut = _event_day(event)
        ratio = np.float64(event.ratio)
        for i, day in enumerate(days):
            if day < cut:
                factors[i] = factors[i] * ratio
    return factors


def utc_days(datetimes):
    return datetimes.dt.strftime("%Y-%m-%d").tolist()


def adjust(frame, splits):
    """Return a new frame whose main OHLCV columns are re-derived from *_raw."""
    if "price_basis" in frame.columns:
        non_raw = sorted({str(v) for v in frame["price_basis"].tolist() if v != "raw"})
        if non_raw:
            raise AdjustmentRefused(
                f"price_basis {non_raw} is already adjusted at the provider - applying split "
                "events would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    factors = split_factors(utc_days(frame["datetime"]), splits)
    out = frame.copy()
    for main, raw in (("open", "open_raw"), ("high", "high_raw"), ("low", "low_raw"),
                      ("close", "close_raw")):
        out[main] = frame[raw].to_numpy(dtype="float64") / factors
    out["volume"] = frame["volume_raw"].to_numpy(dtype="float64") * factors
    out["cumulative_split_factor"] = factors
    return out
