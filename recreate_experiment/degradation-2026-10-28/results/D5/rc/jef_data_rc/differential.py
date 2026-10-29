"""Tolerance-based differential of two 7-column EOD frames."""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_TOLERANCE = 1e-4
COMPARED = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def _by_date(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["Date"] = frame["Date"].astype(str)
    frame = frame.sort_values("Date", kind="stable")
    return frame.drop_duplicates("Date", keep="first").set_index("Date")


def differential_report(a: pd.DataFrame, b: pd.DataFrame, label_a: str, label_b: str,
                        tolerance: float = DEFAULT_TOLERANCE):
    """Return (report lines, ok)."""
    da = _by_date(a)
    db = _by_date(b)
    dates_a = set(da.index)
    dates_b = set(db.index)
    common = sorted(dates_a & dates_b)
    lines = [f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {label_a}, {len(b)} in {label_b}, "
             f"{len(common)} dates in common"]
    unmatched = 0
    for label, only in ((label_a, sorted(dates_a - dates_b)), (label_b, sorted(dates_b - dates_a))):
        if not only:
            continue
        unmatched += len(only)
        line = f"only in {label}: {len(only)} date(s): {', '.join(only[:5])}"
        if len(only) > 5:
            line += f" (+{len(only) - 5} more)"
        lines.append(line)
    cells = 0
    for column in COMPARED:
        av = da.loc[common, column].to_numpy(dtype=np.float64) if common else np.array([], dtype=np.float64)
        bv = db.loc[common, column].to_numpy(dtype=np.float64) if common else np.array([], dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            denominator = np.maximum(np.abs(av), np.abs(bv))
            denominator = np.where(denominator == 0, 1.0, denominator)
            rel = np.abs(av - bv) / denominator
        a_nan = np.isnan(av)
        b_nan = np.isnan(bv)
        rel = np.where(a_nan & b_nan, 0.0, rel)
        rel = np.where(a_nan ^ b_nan, np.inf, rel)
        beyond = rel > tolerance
        k = int(beyond.sum())
        if k == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
        else:
            w = int(np.argmax(rel))
            lines.append(f"{column}: {k}/{len(common)} beyond tolerance, worst {rel[w]:.3%} on "
                         f"{common[w]} ({label_a}={av[w]!r}, {label_b}={bv[w]!r})")
        cells += k
    ok = cells == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched date(s)"
                     " - review before scale-out")
    return lines, ok
