"""Tolerance-based comparison of two 7-column EOD frames."""
import numpy as np
import pandas as pd

COMPARED = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4
SHOWN_DATES = 5


def relative_differences(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    with np.errstate(all="ignore"):
        denominator = np.maximum(np.abs(a), np.abs(b))
        denominator = np.where(denominator == 0, 1.0, denominator)
        rel = np.abs(a - b) / denominator
    a_nan = np.isnan(a)
    b_nan = np.isnan(b)
    rel = np.where(a_nan & b_nan, 0.0, rel)
    rel = np.where(a_nan ^ b_nan, np.inf, rel)
    return rel


def differential_report(a, b, a_label, b_label, tolerance=DEFAULT_TOLERANCE):
    """Return (report lines, ok)."""
    a = a.sort_values("Date", kind="stable").reset_index(drop=True)
    b = b.sort_values("Date", kind="stable").reset_index(drop=True)
    a = a.assign(Date=a["Date"].astype(str))
    b = b.assign(Date=b["Date"].astype(str))
    a_dates = set(a["Date"])
    b_dates = set(b["Date"])
    merged = pd.merge(a, b, on="Date", how="inner", suffixes=("_a", "_b"), sort=False)
    common = len(merged)
    lines = [f"differential: {a_label} vs {b_label} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {a_label}, {len(b)} in {b_label}, {common} dates in common"]
    unmatched = 0
    for label, only in ((a_label, sorted(a_dates - b_dates)), (b_label, sorted(b_dates - a_dates))):
        if not only:
            continue
        unmatched += len(only)
        line = f"only in {label}: {len(only)} date(s): {', '.join(only[:SHOWN_DATES])}"
        if len(only) > SHOWN_DATES:
            line += f" (+{len(only) - SHOWN_DATES} more)"
        lines.append(line)
    cells = 0
    dates = merged["Date"].tolist()
    for column in COMPARED:
        a_values = merged[f"{column}_a"].to_numpy(dtype=np.float64)
        b_values = merged[f"{column}_b"].to_numpy(dtype=np.float64)
        rel = relative_differences(a_values, b_values)
        beyond = rel > tolerance
        count = int(beyond.sum())
        if count == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
            continue
        cells += count
        i = int(np.argmax(rel))
        lines.append(
            f"{column}: {count}/{common} beyond tolerance, worst {rel[i]:.3%} on {dates[i]} "
            f"({a_label}={a_values[i]!r}, {b_label}={b_values[i]!r})")
    if cells == 0 and unmatched == 0:
        lines.append("VERDICT: within tolerance, aligned")
        return lines, True
    lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched date(s) - "
                 f"review before scale-out")
    return lines, False
