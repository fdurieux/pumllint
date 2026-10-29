"""Validation of a 7-column EOD frame against the input contract."""
from __future__ import annotations

import pandas as pd

REQUIRED = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close"]
NUMERIC_COLUMNS = PRICE_COLUMNS + ["Volume"]
WARMUP_ROWS = 720
OFFSET = 30
PERIOD = 365
RECOMMENDED_MIN_ROWS = WARMUP_ROWS + OFFSET + PERIOD


class ContractError(ValueError):
    """A frame that cannot be checked at all."""


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


def validate_frame(frame: pd.DataFrame, min_rows: int = RECOMMENDED_MIN_ROWS) -> ContractReport:
    report = ContractReport()
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        report.errors.append(f"missing required columns: {missing}")
        return report
    extra = [c for c in frame.columns if c not in REQUIRED]
    if extra:
        report.notes.append(
            f"extra columns {extra} are carried through; NaNs in them will drop rows at load "
            "(the transform drops any-NaN rows)")
    numeric = {c: pd.to_numeric(frame[c], errors="coerce") for c in NUMERIC_COLUMNS}
    non_numeric = [c for c in NUMERIC_COLUMNS
                   if int(numeric[c].isna().sum()) > int(frame[c].isna().sum())]
    if non_numeric:
        report.errors.append(f"non-numeric values in {non_numeric}")
    dates = pd.to_datetime(frame["Date"], errors="coerce")
    parsed = dates.notna()
    if int(parsed.sum()) == 0:
        report.errors.append("no parseable dates in 'Date'")
        return report
    unparseable = int((~parsed).sum())
    if unparseable:
        report.notes.append(f"{unparseable} unparseable date(s) - those rows drop at load")
    valid = dates[parsed]
    duplicates = int(valid.duplicated().sum())
    if duplicates:
        report.errors.append(f"{duplicates} duplicate date(s) - forbidden by the contract")
    if not valid.is_monotonic_increasing:
        report.notes.append("dates not sorted ascending - the load transform sorts")
    if non_numeric:
        return report
    negative = [c for c in PRICE_COLUMNS if bool((numeric[c] < 0).any())]
    if negative:
        report.errors.append(f"negative prices in {negative}")
    volume = numeric["Volume"]
    if bool((volume < 0).any()):
        report.errors.append("negative values in Volume")
    inverted = int((numeric["High"] < numeric["Low"]).sum())
    if inverted:
        report.errors.append(f"{inverted} row(s) with High < Low")
    zero = int((volume == 0).sum())
    if zero:
        report.notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
    values = pd.DataFrame(numeric)
    nan_rows = int((values.isna().any(axis=1) | frame["Date"].isna()).sum())
    if nan_rows:
        report.notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
    clean = int((parsed & (volume != 0) & ~values.isna().any(axis=1)).sum())
    if clean < min_rows:
        report.notes.append(
            f"{clean} clean row(s) < recommended minimum {min_rows} (720 warm-up + 395 lags) - "
            "the default counter window needs more history (docs/DATA_CONTRACT.md §1)")
    return report
