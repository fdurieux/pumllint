"""The EOD input contract: validation of a 7-column frame."""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close"]
NUMERIC_COLUMNS = PRICE_COLUMNS + ["Volume"]
WARMUP_ROWS = 720
OFFSET = 30
PERIOD = 365
MIN_CLEAN_ROWS = WARMUP_ROWS + OFFSET + PERIOD


class ContractError(ValueError):
    """A frame that cannot be validated at all."""


class ContractReport:
    def __init__(self):
        self.errors = []
        self.notes = []

    @property
    def ok(self):
        return not self.errors

    def lines(self):
        lines = [f"ERROR: {e}" for e in self.errors] + [f"note:  {n}" for n in self.notes]
        return lines or ["contract: clean"]

    def render(self):
        return "\n".join(self.lines())


def validate_frame(frame, min_rows=MIN_CLEAN_ROWS):
    report = ContractReport()
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        report.errors.append(f"missing required columns: {missing}")
        return report
    extra = [c for c in frame.columns if c not in REQUIRED_COLUMNS]
    if extra:
        report.notes.append(
            f"extra columns {extra} are carried through; NaNs in them will drop rows at "
            f"load (the transform drops any-NaN rows)")

    numeric = {}
    non_numeric = []
    for column in NUMERIC_COLUMNS:
        coerced = pd.to_numeric(frame[column], errors="coerce")
        if int(coerced.isna().sum()) > int(frame[column].isna().sum()):
            non_numeric.append(column)
        numeric[column] = coerced
    if non_numeric:
        report.errors.append(f"non-numeric values in {non_numeric}")

    dates = pd.to_datetime(frame["Date"], errors="coerce")
    unparsed = int(dates.isna().sum())
    if unparsed == len(dates):
        report.errors.append("no parseable dates in 'Date'")
        return report
    if unparsed:
        report.notes.append(f"{unparsed} unparseable date(s) - those rows drop at load")
    parsed = dates.dropna()
    duplicates = int(parsed.duplicated().sum())
    if duplicates:
        report.errors.append(f"{duplicates} duplicate date(s) - forbidden by the contract")
    if not parsed.is_monotonic_increasing:
        report.notes.append("dates not sorted ascending - the load transform sorts")

    if non_numeric:
        return report
    values = pd.DataFrame(numeric)
    negative = [c for c in PRICE_COLUMNS if bool((values[c] < 0).any())]
    if negative:
        report.errors.append(f"negative prices in {negative}")
    if bool((values["Volume"] < 0).any()):
        report.errors.append("negative values in Volume")
    inverted = int((values["High"] < values["Low"]).sum())
    if inverted:
        report.errors.append(f"{inverted} row(s) with High < Low")
    zero = int((values["Volume"] == 0).sum())
    if zero:
        report.notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
    numeric_nan = values.isna().any(axis=1)
    nan_rows = int((numeric_nan | frame["Date"].isna()).sum())
    if nan_rows:
        report.notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
    clean = int((dates.notna() & (values["Volume"] != 0) & ~numeric_nan).sum())
    if clean < min_rows:
        report.notes.append(
            f"{clean} clean row(s) < recommended minimum {min_rows} (720 warm-up + 395 "
            f"lags) - the default counter window needs more history (docs/DATA_CONTRACT.md §1)")
    return report
