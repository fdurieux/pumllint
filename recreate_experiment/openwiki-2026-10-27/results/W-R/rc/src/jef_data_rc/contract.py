"""The seven-column EOD interchange contract.

``validate()`` never raises on bad data: it returns a ``ContractReport``
whose *errors* mean the frame must not reach the binning seam, and whose
*notes* describe what the seam's load transform will do (sort, drop) or an
advisory shortfall of clean history.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np  # noqa: F401  (pandas numeric backend)
import pandas as pd

REQUIRED_COLUMNS = ("Date", "Open", "High", "Low", "Close", "Adj Close", "Volume")
PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Adj Close")
NUMERIC_COLUMNS = PRICE_COLUMNS + ("Volume",)

WARMUP_ROWS = 720
FORWARD_LAGS = (30, 365)
DEFAULT_MIN_ROWS = WARMUP_ROWS + sum(FORWARD_LAGS)  # 1115


class ContractError(ValueError):
    """Raised by ``validate_or_raise`` when a frame has contract errors."""

    def __init__(self, report: "ContractReport"):
        self.report = report
        super().__init__("; ".join(report.errors))


@dataclass
class ContractReport:
    rows: int = 0
    clean_rows: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def lines(self) -> list[str]:
        out = [f"ERROR: {msg}" for msg in self.errors]
        out += [f"note: {msg}" for msg in self.notes]
        verdict = "contract OK" if self.ok else "contract FAILED"
        out.append(
            f"{verdict} ({len(self.errors)} error(s), {len(self.notes)} note(s), "
            f"{self.clean_rows} clean row(s))"
        )
        return out

    def render(self) -> str:
        return "\n".join(self.lines())


def validate(df: pd.DataFrame, min_rows: int = DEFAULT_MIN_ROWS) -> ContractReport:
    report = ContractReport(rows=int(len(df)))
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        report.errors.append(f"missing required column(s): {', '.join(missing)}")
        return report

    extra = [str(c) for c in df.columns if c not in REQUIRED_COLUMNS]
    if extra:
        report.notes.append(
            f"extra column(s) carried through by the loader: {', '.join(extra)} "
            "(their nulls also drop rows)"
        )

    numeric = {}
    for col in NUMERIC_COLUMNS:
        original = df[col]
        coerced = pd.to_numeric(original, errors="coerce")
        newly = int((original.notna() & coerced.isna()).sum())
        if newly:
            report.errors.append(f"{col}: {newly} non-numeric value(s)")
        numeric[col] = coerced.astype("float64")

    dates = pd.to_datetime(df["Date"], errors="coerce")
    parseable = dates.notna()
    n_parseable = int(parseable.sum())
    if n_parseable == 0:
        report.errors.append("no parseable dates")
    unparseable = int((~parseable).sum())
    if unparseable and n_parseable:
        report.notes.append(
            f"{unparseable} unparseable date(s): the loader drops those rows"
        )
    if n_parseable:
        dup = int(dates[parseable].duplicated().sum())
        if dup:
            report.errors.append(f"{dup} duplicate date(s)")
        valid = dates[parseable]
        if not valid.is_monotonic_increasing:
            report.notes.append("dates are out of order: the loader sorts them")

    for col in NUMERIC_COLUMNS:
        negative = int((numeric[col] < 0).sum())
        if negative:
            report.errors.append(f"{col}: {negative} negative value(s)")

    inverted = int((numeric["High"] < numeric["Low"]).sum())
    if inverted:
        report.errors.append(f"{inverted} row(s) with High < Low")

    zero_volume = numeric["Volume"] == 0
    n_zero = int(zero_volume.sum())
    if n_zero:
        report.notes.append(f"{n_zero} zero-volume row(s): the loader drops them")

    frame = df.drop(columns=["Date"])
    for col in NUMERIC_COLUMNS:
        frame[col] = numeric[col]
    has_null = frame.isna().any(axis=1)
    n_null = int(has_null.sum())
    if n_null:
        report.notes.append(
            f"{n_null} row(s) containing NaN: the loader drops them"
        )

    clean = parseable & ~zero_volume & ~has_null
    report.clean_rows = int(clean.sum())
    if report.clean_rows < min_rows:
        report.notes.append(
            f"{report.clean_rows} clean row(s), below the advisory minimum of "
            f"{min_rows} ({WARMUP_ROWS} warm-up + "
            f"{' + '.join(str(x) for x in FORWARD_LAGS)} forward lags)"
        )
    return report


def validate_or_raise(df: pd.DataFrame, min_rows: int = DEFAULT_MIN_ROWS) -> ContractReport:
    report = validate(df, min_rows=min_rows)
    if not report.ok:
        raise ContractError(report)
    return report


__all__ = [
    "REQUIRED_COLUMNS",
    "DEFAULT_MIN_ROWS",
    "ContractError",
    "ContractReport",
    "validate",
    "validate_or_raise",
]
