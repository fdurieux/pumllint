"""Tolerance-based comparison of two 7-column frames aligned on Date."""
from __future__ import annotations

import numpy as np
import pandas as pd

VALUE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4


def relative_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    out = np.empty(len(a), dtype=np.float64)
    for k in range(len(a)):
        x, y = a[k], b[k]
        x_nan, y_nan = bool(np.isnan(x)), bool(np.isnan(y))
        if x_nan and y_nan:
            out[k] = 0.0
        elif x_nan or y_nan:
            out[k] = np.inf
        else:
            denominator = max(abs(x), abs(y))
            if denominator == 0:
                denominator = 1.0
            out[k] = abs(x - y) / denominator
    return out


def _dates(frame: pd.DataFrame) -> list:
    return [str(v) for v in frame["Date"].tolist()]


def differential_report(frame_a: pd.DataFrame, label_a: str, frame_b: pd.DataFrame, label_b: str,
                        tolerance: float = DEFAULT_TOLERANCE) -> tuple:
    """(report lines, ok)."""
    a = frame_a.assign(Date=_dates(frame_a)).sort_values("Date", kind="stable").reset_index(drop=True)
    b = frame_b.assign(Date=_dates(frame_b)).sort_values("Date", kind="stable").reset_index(drop=True)
    dates_a = a["Date"].tolist()
    dates_b = b["Date"].tolist()
    set_a, set_b = set(dates_a), set(dates_b)
    common = sorted(set_a & set_b)
    lines = [f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {label_a}, {len(b)} in {label_b}, {len(common)} dates in common"]
    unmatched = 0
    for label, mine, other in ((label_a, set_a, set_b), (label_b, set_b, set_a)):
        only = sorted(mine - other)
        if only:
            unmatched += len(only)
            line = f"only in {label}: {len(only)} date(s): {', '.join(only[:5])}"
            if len(only) > 5:
                line += f" (+{len(only) - 5} more)"
            lines.append(line)
    left = a.drop_duplicates("Date", keep="first").set_index("Date").loc[common]
    right = b.drop_duplicates("Date", keep="first").set_index("Date").loc[common]
    cells = 0
    for column in VALUE_COLUMNS:
        va = left[column].to_numpy(dtype=np.float64)
        vb = right[column].to_numpy(dtype=np.float64)
        rel = relative_difference(va, vb)
        beyond = rel > tolerance
        k = int(beyond.sum())
        if k == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
        else:
            cells += k
            idx = int(np.argmax(rel))
            lines.append(f"{column}: {k}/{len(common)} beyond tolerance, worst {rel[idx]:.3%} on "
                         f"{common[idx]} ({label_a}={va[idx]!r}, {label_b}={vb[idx]!r})")
    ok = cells == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched date(s) - "
                     f"review before scale-out")
    return lines, ok
