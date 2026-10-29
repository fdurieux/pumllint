"""Tolerance-based comparison of two 7-column frames."""
import numpy as np
import pandas as pd

COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4
SHOWN_DATES = 5


def relative_difference(a, b):
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        denominator = np.maximum(np.abs(a), np.abs(b))
        denominator = np.where(denominator == 0, 1.0, denominator)
        rel = np.abs(a - b) / denominator
    both = np.isnan(a) & np.isnan(b)
    one = np.isnan(a) ^ np.isnan(b)
    rel = np.where(both, 0.0, rel)
    rel = np.where(one, np.inf, rel)
    return rel


def _only_line(label, dates):
    shown = ", ".join(dates[:SHOWN_DATES])
    line = f"only in {label}: {len(dates)} date(s): {shown}"
    if len(dates) > SHOWN_DATES:
        line += f" (+{len(dates) - SHOWN_DATES} more)"
    return line


def differential_report(frame_a, frame_b, label_a, label_b, tolerance=DEFAULT_TOLERANCE):
    """Return (report lines, ok)."""
    a = frame_a.sort_values("Date", kind="stable").reset_index(drop=True)
    b = frame_b.sort_values("Date", kind="stable").reset_index(drop=True)
    a_dates = [str(d) for d in a["Date"].tolist()]
    b_dates = [str(d) for d in b["Date"].tolist()]
    a = a.assign(Date=a_dates)
    b = b.assign(Date=b_dates)
    merged = pd.merge(a[["Date"] + COLUMNS], b[["Date"] + COLUMNS], on="Date", how="inner",
                      suffixes=("__a", "__b"))
    common = len(merged)
    only_a = sorted(set(a_dates) - set(b_dates))
    only_b = sorted(set(b_dates) - set(a_dates))
    lines = [f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {label_a}, {len(b)} in {label_b}, {common} dates in common"]
    if only_a:
        lines.append(_only_line(label_a, only_a))
    if only_b:
        lines.append(_only_line(label_b, only_b))
    cells = 0
    dates = merged["Date"].tolist()
    for column in COLUMNS:
        va = merged[f"{column}__a"].to_numpy(dtype="float64")
        vb = merged[f"{column}__b"].to_numpy(dtype="float64")
        rel = relative_difference(va, vb)
        beyond = int((rel > tolerance).sum())
        if beyond == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
            continue
        cells += beyond
        k = int(np.argmax(rel))
        lines.append(f"{column}: {beyond}/{common} beyond tolerance, worst {rel[k]:.3%} on "
                     f"{dates[k]} ({label_a}={va[k]!r}, {label_b}={vb[k]!r})")
    unmatched = len(only_a) + len(only_b)
    ok = cells == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched date(s) "
                     "- review before scale-out")
    return lines, ok
