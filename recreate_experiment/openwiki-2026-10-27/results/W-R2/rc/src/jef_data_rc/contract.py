"""The seven-column EOD interchange contract.

`validate()` returns a `ContractReport` and never raises for invalid data.
Errors mean the frame must not proceed to binning; notes describe rows the
downstream load transform will sort or drop, and advisory history length.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("Date", "Open", "High", "Low", "Close", "Adj Close", "Volume")
PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Adj Close")
NUMERIC_COLUMNS = PRICE_COLUMNS + ("Volume",)

WARMUP_ROWS = 720
FORWARD_LAGS = (30, 365)
DEFAULT_MIN_ROWS = WARMUP_ROWS + sum(FORWARD_LAGS)


class ContractError(ValueError):
    """Raised by `validate_or_raise()` when a report has errors."""

    def __init__(self, report: "ContractReport"):
        self.report = report
        super().__init__("; ".join(report.errors))


@dataclass
class ContractReport:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rows: int = 0
    clean_rows: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [f"ERROR: {e}" for e in self.errors]
        lines += [f"note: {n}" for n in self.notes]
        if self.ok:
            lines.append("contract: ok")
        else:
            lines.append(f"contract: FAILED ({len(self.errors)} error(s))")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()


def _parse_dates(values: pd.Series) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(values, errors="coerce")


def validate(df: pd.DataFrame, min_rows: int = DEFAULT_MIN_ROWS) -> ContractReport:
    """Check `df` against the seven-column contract."""
    errors: list[str] = []
    notes: list[str] = []
    rows = int(len(df))

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"missing required column(s): {', '.join(missing)}")
        return ContractReport(errors, notes, rows, 0)

    extra = [str(c) for c in df.columns if c not in REQUIRED_COLUMNS]
    if extra:
        notes.append(
            f"extra column(s) carried through: {', '.join(extra)} "
            "(a null in them also drops its row)"
        )

    numeric: dict[str, pd.Series] = {}
    for col in NUMERIC_COLUMNS:
        raw = df[col]
        coerced = pd.to_numeric(raw, errors="coerce")
        bad = int((coerced.isna() & raw.notna()).sum())
        if bad:
            errors.append(f"{col}: {bad} non-numeric value(s)")
        numeric[col] = coerced.astype("float64")

    dates = _parse_dates(df["Date"])
    parseable = dates.notna()
    n_parseable = int(parseable.sum())
    unparseable = rows - n_parseable
    if rows and n_parseable == 0:
        errors.append("Date: no parseable dates")
    if unparseable:
        notes.append(f"Date: {unparseable} unparseable date(s) will be dropped by the load transform")
    good_dates = dates[parseable]
    dup = int(good_dates.duplicated().sum())
    if dup:
        errors.append(f"Date: {dup} duplicate date(s)")
    if n_parseable > 1 and not good_dates.is_monotonic_increasing:
        notes.append("Date: dates are out of order and will be sorted by the load transform")

    for col in NUMERIC_COLUMNS:
        neg = int((numeric[col] < 0).sum())
        if neg:
            errors.append(f"{col}: {neg} negative value(s)")
    inverted = int((numeric["High"] < numeric["Low"]).sum())
    if inverted:
        errors.append(f"High < Low on {inverted} row(s)")

    zero_volume = numeric["Volume"] == 0
    n_zero = int(zero_volume.sum())
    if n_zero:
        notes.append(f"Volume: {n_zero} zero-volume row(s) will be dropped by the load transform")

    null_frame = pd.DataFrame({c: numeric[c] for c in NUMERIC_COLUMNS})
    for col in extra:
        null_frame[col] = df[col].values
    null_rows = null_frame.isna().any(axis=1).to_numpy()
    n_null = int(null_rows.sum())
    if n_null:
        notes.append(f"{n_null} row(s) containing NaN will be dropped by the load transform")

    clean = parseable.to_numpy() & ~null_rows & ~zero_volume.to_numpy()
    clean_rows = int(np.count_nonzero(clean))
    if clean_rows < min_rows:
        notes.append(
            f"{clean_rows} clean row(s), below the advisory minimum of {min_rows} "
            f"({WARMUP_ROWS} warm-up + {FORWARD_LAGS[0]} + {FORWARD_LAGS[1]} forward lags)"
        )

    return ContractReport(errors, notes, rows, clean_rows)


def validate_or_raise(df: pd.DataFrame, min_rows: int = DEFAULT_MIN_ROWS) -> ContractReport:
    """Return the report, raising `ContractError` only when it has errors."""
    report = validate(df, min_rows=min_rows)
    if not report.ok:
        raise ContractError(report)
    return report
