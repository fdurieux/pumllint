"""The tolerance-based differential between two seam frames."""
from __future__ import annotations

import numpy as np
import pandas as pd

COMPARED_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4
SHOWN_DATES = 5


class DifferentialError(ValueError):
    """A differential with nothing to compare."""


def relative_differences(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        denominator = np.maximum(np.abs(a), np.abs(b))
        denominator = np.where(denominator == 0, 1.0, denominator)
        rel = np.abs(a - b) / denominator
    a_nan, b_nan = np.isnan(a), np.isnan(b)
    rel = np.where(a_nan & b_nan, 0.0, rel)
    rel = np.where(a_nan ^ b_nan, np.inf, rel)
    return rel


def _only_line(label, dates):
    shown = ", ".join(dates[:SHOWN_DATES])
    line = f"only in {label}: {len(dates)} date(s): {shown}"
    if len(dates) > SHOWN_DATES:
        line += f" (+{len(dates) - SHOWN_DATES} more)"
    return line


def differential_report(frame_a, frame_b, label_a, label_b, tolerance=DEFAULT_TOLERANCE):
    """(report lines, ok) of the comparison of two frames aligned on Date."""
    a = frame_a.assign(Date=frame_a["Date"].astype(str)).sort_values("Date", kind="stable")
    b = frame_b.assign(Date=frame_b["Date"].astype(str)).sort_values("Date", kind="stable")
    dates_a, dates_b = set(a["Date"]), set(b["Date"])
    merged = pd.merge(a, b, on="Date", how="inner", suffixes=("_a", "_b"))
    common = len(merged)
    lines = [f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {label_a}, {len(b)} in {label_b}, {common} dates in common"]
    only_a = sorted(dates_a - dates_b)
    only_b = sorted(dates_b - dates_a)
    if only_a:
        lines.append(_only_line(label_a, only_a))
    if only_b:
        lines.append(_only_line(label_b, only_b))
    cells = 0
    days = merged["Date"].tolist()
    for column in COMPARED_COLUMNS:
        values_a = merged[f"{column}_a"].to_numpy(dtype=np.float64)
        values_b = merged[f"{column}_b"].to_numpy(dtype=np.float64)
        rel = relative_differences(values_a, values_b)
        beyond = int((rel > tolerance).sum())
        if beyond == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
            continue
        cells += beyond
        i = int(np.argmax(rel))
        lines.append(f"{column}: {beyond}/{common} beyond tolerance, worst {rel[i]:.3%} on "
                     f"{days[i]} ({label_a}={values_a[i]!r}, {label_b}={values_b[i]!r})")
    unmatched = len(only_a) + len(only_b)
    ok = cells == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched "
                     f"date(s) - review before scale-out")
    return lines, ok
