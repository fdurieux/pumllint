"""Tolerance-based comparison of two 7-column EOD frames."""
from __future__ import annotations

import numpy as np
import pandas as pd

COMPARED = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4


def relative_differences(a, b):
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        denominator = np.maximum(np.abs(a), np.abs(b))
        denominator = np.where(denominator == 0, 1.0, denominator)
        rel = np.abs(a - b) / denominator
    a_nan = np.isnan(a)
    b_nan = np.isnan(b)
    rel = np.where(a_nan & b_nan, 0.0, rel)
    rel = np.where(a_nan ^ b_nan, np.inf, rel)
    return rel


def _dates(frame):
    return [str(d) for d in frame["Date"].tolist()]


def differential_report(frame_a, frame_b, label_a, label_b, tolerance=DEFAULT_TOLERANCE):
    """Return (report lines, ok)."""
    a = frame_a.sort_values("Date", kind="stable").reset_index(drop=True)
    b = frame_b.sort_values("Date", kind="stable").reset_index(drop=True)
    a = a.assign(Date=_dates(a))
    b = b.assign(Date=_dates(b))
    dates_a = set(a["Date"])
    dates_b = set(b["Date"])
    merged = a[["Date"] + COMPARED].merge(b[["Date"] + COMPARED], on="Date", how="inner",
                                          suffixes=("_a", "_b"))
    common = len(merged)
    lines = [f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {label_a}, {len(b)} in {label_b}, {common} dates in common"]
    unmatched = 0
    for label, only in ((label_a, sorted(dates_a - dates_b)), (label_b, sorted(dates_b - dates_a))):
        if only:
            unmatched += len(only)
            line = f"only in {label}: {len(only)} date(s): {', '.join(only[:5])}"
            if len(only) > 5:
                line += f" (+{len(only) - 5} more)"
            lines.append(line)
    cells = 0
    days = merged["Date"].tolist()
    for column in COMPARED:
        va = merged[f"{column}_a"].to_numpy(dtype="float64")
        vb = merged[f"{column}_b"].to_numpy(dtype="float64")
        rel = relative_differences(va, vb)
        beyond = rel > tolerance
        count = int(beyond.sum())
        if count == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
        else:
            w = int(np.argmax(rel))
            lines.append(f"{column}: {count}/{common} beyond tolerance, worst {rel[w]:.3%} on "
                         f"{days[w]} ({label_a}={va[w]!r}, {label_b}={vb[w]!r})")
            cells += count
    if cells == 0 and unmatched == 0:
        lines.append("VERDICT: within tolerance, aligned")
        ok = True
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched date(s) "
                     f"- review before scale-out")
        ok = False
    return lines, ok


def read_csv_frame(path):
    return pd.read_csv(path)
