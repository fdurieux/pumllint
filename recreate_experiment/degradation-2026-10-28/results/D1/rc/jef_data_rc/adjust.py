"""The split adjustment: cumulative factor per row and the pure adjustment pass."""
import math

import numpy as np

RAW_PRICE_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw"]
RAW_COLUMNS = RAW_PRICE_COLUMNS + ["volume_raw"]


class AdjustmentRefused(ValueError):
    """An adjustment that must not run (pre-adjusted series, degenerate ratio, no raws)."""


def check_events(splits):
    for event in splits:
        ratio = event.ratio
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) \
                or not math.isfinite(ratio) or ratio <= 0:
            raise AdjustmentRefused(f"split {event.date} has degenerate ratio {ratio!r}")


def factors(days, splits):
    """F(d) per row date: product of the ratios of splits strictly after d, in stored order."""
    check_events(splits)
    out = []
    for day in days:
        factor = 1.0
        for event in splits:
            if day < event.date:
                factor = factor * event.ratio
        out.append(factor)
    return np.array(out, dtype="float64")


def row_days(frame):
    return list(frame["datetime"].dt.date)


def adjust(frame, splits):
    """A new frame whose main OHLCV are re-derived from the raw columns and `splits`."""
    if "price_basis" in frame.columns:
        not_raw = sorted({value for value in frame["price_basis"].tolist() if value != "raw"})
        if not_raw:
            raise AdjustmentRefused(
                f"price_basis {not_raw} is already adjusted at the provider - applying split "
                "events would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [column for column in RAW_COLUMNS + ["datetime"] if column not in frame.columns]
    if missing:
        raise AdjustmentRefused(f"cannot adjust without immutable raw columns: missing {missing}")
    out = frame.copy()
    factor = factors(row_days(frame), splits)
    for column in RAW_PRICE_COLUMNS:
        out[column[:-4]] = frame[column].to_numpy(dtype="float64") / factor
    out["volume"] = frame["volume_raw"].to_numpy(dtype="float64") * factor
    out["cumulative_split_factor"] = factor
    return out
