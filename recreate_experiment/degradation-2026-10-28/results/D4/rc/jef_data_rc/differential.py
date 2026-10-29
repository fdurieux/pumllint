"""Tolerance-based comparison of two 7-column frames."""
from __future__ import annotations

import numpy as np
import pandas as pd

COMPARED = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4


def relative_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = np.maximum(np.abs(a), np.abs(b))
        denom = np.where(denom == 0, 1.0, denom)
        rel = np.abs(a - b) / denom
    a_nan = np.isnan(a)
    b_nan = np.isnan(b)
    rel = np.where(a_nan & b_nan, 0.0, rel)
    rel = np.where(a_nan ^ b_nan, np.inf, rel)
    return rel


def differential_report(a: pd.DataFrame, b: pd.DataFrame, a_label: str, b_label: str,
                        tolerance: float = DEFAULT_TOLERANCE) -> tuple:
    a = a.sort_values("Date", kind="stable").reset_index(drop=True)
    b = b.sort_values("Date", kind="stable").reset_index(drop=True)
    a_dates = set(a["Date"].tolist())
    b_dates = set(b["Date"].tolist())
    common = a_dates & b_dates
    lines = [f"differential: {a_label} vs {b_label} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {a_label}, {len(b)} in {b_label}, {len(common)} dates in common"]
    unmatched = 0
    for label, only in ((a_label, sorted(a_dates - b_dates)), (b_label, sorted(b_dates - a_dates))):
        if only:
            unmatched += len(only)
            line = f"only in {label}: {len(only)} date(s): {', '.join(str(d) for d in only[:5])}"
            if len(only) > 5:
                line += f" (+{len(only) - 5} more)"
            lines.append(line)
    merged = pd.merge(a, b, on="Date", how="inner", suffixes=("_a", "_b"), sort=True)
    cells = 0
    n_common = len(common)
    for column in COMPARED:
        av = merged[f"{column}_a"].astype("float64").to_numpy()
        bv = merged[f"{column}_b"].astype("float64").to_numpy()
        rel = pd.Series(relative_difference(av, bv), dtype="float64")
        beyond = rel > tolerance
        k = int(beyond.sum())
        if k:
            worst = int(np.argmax(rel.to_numpy()))
            lines.append(
                f"{column}: {k}/{n_common} beyond tolerance, worst {rel.iloc[worst]:.3%} on "
                f"{merged['Date'].iloc[worst]} ({a_label}={av[worst]!r}, {b_label}={bv[worst]!r})")
        else:
            lines.append(f"{column}: within tolerance (max {rel.max():.3%})")
        cells += k
    ok = cells == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched date(s) - "
                     "review before scale-out")
    return "\n".join(lines), ok
