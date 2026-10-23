"""Basis resolution and the split-only (CRSP-style) adjustment pass."""
import math

import numpy as np

RAW_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]
PRICE_PAIRS = [("open", "open_raw"), ("high", "high_raw"), ("low", "low_raw"),
               ("close", "close_raw")]


class AdjustmentRefused(ValueError):
    """An adjustment that must not run."""


def price_basis_for(provider, asset_type):
    """The stored price basis, from the provider and the DECLARED asset_type."""
    if provider == "eodhd":
        return "split_adjusted" if asset_type == "crypto" else "raw"
    return "split_adjusted"


def validate_events(events):
    for event in events:
        ratio = event.ratio
        try:
            bad = not math.isfinite(ratio) or ratio <= 0
        except TypeError:
            bad = True
        if bad:
            raise AdjustmentRefused(f"split {event.date} has degenerate ratio {ratio!r}")


def cumulative_factors(days, events):
    """Per-row factor: product of ratios of splits dated strictly after the row."""
    validate_events(events)
    days = np.asarray(days, dtype=object)
    factor = np.ones(len(days), dtype="float64")
    for event in events:
        mask = days < event.date
        factor[mask] = factor[mask] * event.ratio
    return factor


def session_days(frame):
    """UTC calendar date of each row's datetime as YYYY-MM-DD text."""
    return [d.strftime("%Y-%m-%d") for d in frame["datetime"]]


def adjust(frame, events):
    """Re-derive the main columns of a raw-basis frame from *_raw and the events."""
    if "price_basis" in frame.columns:
        non_raw = sorted({str(v) for v in frame["price_basis"] if v != "raw"})
        if non_raw:
            raise AdjustmentRefused(
                f"price_basis {non_raw} is already adjusted at the provider - applying "
                f"split events would double-adjust (docs/DATA_CONTRACT.md §2)")
    missing = [c for c in RAW_COLUMNS + ["datetime"] if c not in frame.columns]
    if missing:
        raise AdjustmentRefused(
            f"cannot adjust without immutable raw columns: missing {missing}")
    factor = cumulative_factors(session_days(frame), events)
    out = frame.copy()
    for main, raw in PRICE_PAIRS:
        out[main] = frame[raw].to_numpy(dtype="float64") / factor
    out["volume"] = frame["volume_raw"].to_numpy(dtype="float64") * factor
    out["cumulative_split_factor"] = factor
    return out
