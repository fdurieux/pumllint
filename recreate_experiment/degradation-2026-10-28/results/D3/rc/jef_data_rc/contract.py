"""Validation of a 7-column EOD frame against the input contract."""
from __future__ import annotations

import pandas as pd

REQUIRED = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
NUMERIC = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICES = ["Open", "High", "Low", "Close", "Adj Close"]
WARMUP_ROWS = 720
OFFSET = 30
PERIOD = 365
MIN_CLEAN_ROWS = WARMUP_ROWS + OFFSET + PERIOD


class ContractError(ValueError):
    """A frame that cannot be validated."""


class ContractReport:
    def __init__(self):
        self.errors: list = []
        self.notes: list = []

    def ok(self) -> bool:
        return not self.errors

    def lines(self) -> list:
        if not self.errors and not self.notes:
            return ["contract: clean"]
        return [f"ERROR: {e}" for e in self.errors] + [f"note:  {n}" for n in self.notes]

    def render(self) -> str:
        return "\n".join(self.lines())


def validate_frame(frame: pd.DataFrame, min_rows: int = MIN_CLEAN_ROWS) -> ContractReport:
    report = ContractReport()
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        report.errors.append(f"missing required columns: {missing}")
        return report
    extra = [c for c in frame.columns if c not in REQUIRED]
    if extra:
        report.notes.append(
            f"extra columns {extra} are carried through; NaNs in them will drop rows at load "
            f"(the transform drops any-NaN rows)")
    numeric = {}
    non_numeric = []
    for column in NUMERIC:
        coerced = pd.to_numeric(frame[column], errors="coerce")
        if int(coerced.isna().sum()) > int(frame[column].isna().sum()):
            non_numeric.append(column)
        numeric[column] = coerced
    if non_numeric:
        report.errors.append(f"non-numeric values in {non_numeric}")
    dates = pd.to_datetime(frame["Date"], errors="coerce")
    parsed = dates.dropna()
    if len(parsed) == 0:
        report.errors.append("no parseable dates in 'Date'")
        return report
    unparseable = int(dates.isna().sum())
    if unparseable:
        report.notes.append(f"{unparseable} unparseable date(s) - those rows drop at load")
    duplicates = int(parsed.duplicated().sum())
    if duplicates:
        report.errors.append(f"{duplicates} duplicate date(s) - forbidden by the contract")
    if not parsed.is_monotonic_increasing:
        report.notes.append("dates not sorted ascending - the load transform sorts")
    if non_numeric:
        return report
    negative = [c for c in PRICES if bool((numeric[c] < 0).any())]
    if negative:
        report.errors.append(f"negative prices in {negative}")
    if bool((numeric["Volume"] < 0).any()):
        report.errors.append("negative values in Volume")
    high_low = int((numeric["High"] < numeric["Low"]).sum())
    if high_low:
        report.errors.append(f"{high_low} row(s) with High < Low")
    zero = int((numeric["Volume"] == 0).sum())
    if zero:
        report.notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
    values = pd.DataFrame(numeric)
    nan_any = values.isna().any(axis=1)
    nan_rows = int((nan_any | frame["Date"].isna()).sum())
    if nan_rows:
        report.notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
    clean = int((dates.notna() & (numeric["Volume"] != 0) & ~nan_any).sum())
    if clean < min_rows:
        report.notes.append(
            f"{clean} clean row(s) < recommended minimum {min_rows} ({WARMUP_ROWS} warm-up + "
            f"{OFFSET + PERIOD} lags) - the default counter window needs more history "
            f"(docs/DATA_CONTRACT.md §1)")
    return report
