"""Validation of a 7-column EOD frame against the input contract."""
import warnings

import pandas as pd

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close"]
NUMERIC_COLUMNS = PRICE_COLUMNS + ["Volume"]
WARMUP_ROWS = 720
OFFSET = 30
PERIOD = 365
MIN_CLEAN_ROWS = WARMUP_ROWS + OFFSET + PERIOD


class ContractError(ValueError):
    """A frame that cannot be validated."""


class ContractReport:
    def __init__(self, errors=None, notes=None):
        self.errors = list(errors or [])
        self.notes = list(notes or [])

    def ok(self):
        return not self.errors

    def lines(self):
        out = [f"ERROR: {e}" for e in self.errors] + [f"note:  {n}" for n in self.notes]
        return out or ["contract: clean"]

    def render(self):
        return "\n".join(self.lines())


def _parse_dates(column):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(column, errors="coerce")


def validate_frame(frame, min_rows=MIN_CLEAN_ROWS):
    report = ContractReport()
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        report.errors.append(f"missing required columns: {missing}")
        return report
    extra = [c for c in frame.columns if c not in REQUIRED_COLUMNS]
    if extra:
        report.notes.append(
            f"extra columns {extra} are carried through; NaNs in them will drop rows at load "
            f"(the transform drops any-NaN rows)")

    numeric = {}
    non_numeric = []
    for column in NUMERIC_COLUMNS:
        coerced = pd.to_numeric(frame[column], errors="coerce")
        if int(coerced.isna().sum()) > int(frame[column].isna().sum()):
            non_numeric.append(column)
        numeric[column] = coerced
    if non_numeric:
        report.errors.append(f"non-numeric values in {non_numeric}")

    dates = _parse_dates(frame["Date"])
    unparsed = int(dates.isna().sum())
    if unparsed == len(frame):
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
    negative = [c for c in PRICE_COLUMNS if bool((numeric[c] < 0).any())]
    if negative:
        report.errors.append(f"negative prices in {negative}")
    if bool((numeric["Volume"] < 0).any()):
        report.errors.append("negative values in Volume")
    inverted = int((numeric["High"] < numeric["Low"]).sum())
    if inverted:
        report.errors.append(f"{inverted} row(s) with High < Low")
    zero = int((numeric["Volume"] == 0).sum())
    if zero:
        report.notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
    values = pd.DataFrame(numeric)
    nan_any = values.isna().any(axis=1) | frame["Date"].isna().to_numpy()
    nan_rows = int(nan_any.sum())
    if nan_rows:
        report.notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
    clean = int((dates.notna() & (numeric["Volume"] != 0) & ~values.isna().any(axis=1)).sum())
    if clean < min_rows:
        report.notes.append(
            f"{clean} clean row(s) < recommended minimum {min_rows} (720 warm-up + 395 lags) - "
            f"the default counter window needs more history (docs/DATA_CONTRACT.md §1)")
    return report
