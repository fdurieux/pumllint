"""Tolerance-based comparison of two seven-column EOD frames.

Both frames are indexed by ``Date``. Dates present on one side only are
reported. On common dates every ``Open, High, Low, Close, Adj Close, Volume``
cell is compared by relative difference::

    rel = |a - b| / max(|a|, |b|)      (a zero denominator counts as 1.0)

Two NaNs compare equal; a NaN on one side only is an infinite discrepancy.
The verdict passes only with no unmatched dates and no cell beyond the
tolerance.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

COMPARED_COLUMNS = ("Open", "High", "Low", "Close", "Adj Close", "Volume")
DEFAULT_TOLERANCE = 1e-6


@dataclass
class DifferentialReport:
    tolerance: float
    common: int = 0
    only_a: list[str] = field(default_factory=list)
    only_b: list[str] = field(default_factory=list)
    failures: dict[str, dict] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures and not self.only_a and not self.only_b

    def render(self) -> str:
        return "\n".join(self.lines)


def relative_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    with np.errstate(invalid="ignore"):
        denom = np.maximum(np.abs(a), np.abs(b))
        denom = np.where(denom == 0, 1.0, denom)
        rel = np.abs(a - b) / denom
    rel = np.where(nan_a & nan_b, 0.0, rel)
    rel = np.where(nan_a ^ nan_b, np.inf, rel)
    return rel


def _span(dates: list[str]) -> str:
    if not dates:
        return "0"
    if len(dates) == 1:
        return f"1 ({dates[0]})"
    return f"{len(dates)} ({dates[0]} .. {dates[-1]})"


def compare_frames(
    a: pd.DataFrame,
    b: pd.DataFrame,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    label_a: str = "A",
    label_b: str = "B",
) -> DifferentialReport:
    report = DifferentialReport(tolerance=tolerance)
    left = a.assign(Date=a["Date"].astype(str)).set_index("Date")
    right = b.assign(Date=b["Date"].astype(str)).set_index("Date")
    left_dates = set(left.index)
    right_dates = set(right.index)
    common = sorted(left_dates & right_dates)
    report.common = len(common)
    report.only_a = sorted(left_dates - right_dates)
    report.only_b = sorted(right_dates - left_dates)
    report.lines.append(
        f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})"
    )
    report.lines.append(f"aligned dates: {report.common}")
    report.lines.append(f"only in {label_a}: {_span(report.only_a)}")
    report.lines.append(f"only in {label_b}: {_span(report.only_b)}")
    if common:
        left_c = left.loc[common]
        right_c = right.loc[common]
    for col in COMPARED_COLUMNS:
        if not common:
            break
        rel = relative_difference(
            pd.to_numeric(left_c[col], errors="coerce").to_numpy(dtype="float64"),
            pd.to_numeric(right_c[col], errors="coerce").to_numpy(dtype="float64"),
        )
        beyond = rel > tolerance
        n_beyond = int(beyond.sum())
        if n_beyond:
            worst = int(np.argmax(rel))
            report.failures[col] = {
                "cells": n_beyond,
                "worst": float(rel[worst]),
                "worst_date": common[worst],
            }
            report.lines.append(
                f"{col}: {n_beyond} cell(s) beyond tolerance, worst "
                f"{rel[worst]:.6g} on {common[worst]}"
            )
        else:
            report.lines.append(f"{col}: within tolerance")
    report.lines.append("verdict: PASS" if report.ok else "verdict: FAIL")
    return report
