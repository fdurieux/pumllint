"""Tolerance-based comparison of two seven-column EOD frames.

Frames are aligned on `Date`. On common dates every OHLCV cell is compared
by relative difference |a - b| / max(|a|, |b|) (a zero denominator counts as
1.0); two NaNs are equal, a one-sided NaN is an infinite discrepancy. The
verdict is ok only with no out-of-tolerance cell AND no unmatched date.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

COMPARE_COLUMNS = ("Open", "High", "Low", "Close", "Adj Close", "Volume")
DEFAULT_TOLERANCE = 1e-6


@dataclass
class DifferentialReport:
    ok: bool
    a_label: str
    b_label: str
    tolerance: float
    common: int
    only_a: list[str] = field(default_factory=list)
    only_b: list[str] = field(default_factory=list)
    failures: dict[str, tuple[int, str, float]] = field(default_factory=dict)
    passing: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"differential: A={self.a_label} B={self.b_label} tolerance={self.tolerance:g}",
            f"aligned dates: {self.common}",
        ]
        if self.only_a:
            lines.append(f"dates only in A: {len(self.only_a)} ({self.only_a[0]}..{self.only_a[-1]})")
        if self.only_b:
            lines.append(f"dates only in B: {len(self.only_b)} ({self.only_b[0]}..{self.only_b[-1]})")
        if self.passing:
            lines.append(f"within tolerance: {', '.join(self.passing)}")
        for col, (count, date, worst) in self.failures.items():
            lines.append(f"beyond tolerance: {col}: {count} cell(s), worst {worst:.6g} on {date}")
        lines.append("verdict: ok" if self.ok else "verdict: DIFFERENT")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()


def _date_index(df: pd.DataFrame) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(df["Date"], errors="coerce")
    as_text = df["Date"].astype(str)
    return pd.Series(np.where(parsed.notna(), parsed.dt.strftime("%Y-%m-%d"), as_text), index=df.index)


def relative_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = np.maximum(np.abs(a), np.abs(b))
        denom = np.where(denom == 0, 1.0, denom)
        rel = np.abs(a - b) / denom
    both_nan = np.isnan(a) & np.isnan(b)
    one_nan = np.isnan(a) ^ np.isnan(b)
    rel = np.where(both_nan, 0.0, rel)
    rel = np.where(one_nan, np.inf, rel)
    return rel


def differential(a: pd.DataFrame, b: pd.DataFrame, tolerance: float = DEFAULT_TOLERANCE,
                 a_label: str = "A", b_label: str = "B") -> DifferentialReport:
    a = a.copy()
    b = b.copy()
    a.index = _date_index(a)
    b.index = _date_index(b)
    a = a[~a.index.duplicated(keep="first")]
    b = b[~b.index.duplicated(keep="first")]
    a_dates, b_dates = set(a.index), set(b.index)
    common = sorted(a_dates & b_dates)
    only_a = sorted(a_dates - b_dates)
    only_b = sorted(b_dates - a_dates)
    failures: dict[str, tuple[int, str, float]] = {}
    passing: list[str] = []
    for col in COMPARE_COLUMNS:
        if col not in a.columns or col not in b.columns:
            failures[col] = (len(common), common[0] if common else "-", float("inf"))
            continue
        va = pd.to_numeric(a.loc[common, col], errors="coerce").to_numpy(dtype="float64")
        vb = pd.to_numeric(b.loc[common, col], errors="coerce").to_numpy(dtype="float64")
        rel = relative_difference(va, vb)
        bad = rel > tolerance
        if bad.any():
            worst_i = int(np.argmax(np.where(bad, rel, -1.0)))
            failures[col] = (int(bad.sum()), common[worst_i], float(rel[worst_i]))
        else:
            passing.append(col)
    ok = not failures and not only_a and not only_b
    return DifferentialReport(ok, a_label, b_label, tolerance, len(common), only_a, only_b,
                              failures, passing)
