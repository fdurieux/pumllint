"""Validation of a 7-column EOD frame against the input contract."""
import warnings

import pandas as pd

REQUIRED = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
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
        if not self.errors and not self.notes:
            return ["contract: clean"]
        return [f"ERROR: {e}" for e in self.errors] + [f"note:  {n}" for n in self.notes]

    def render(self):
        return "\n".join(self.lines())


def _parse_dates(values):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(values, errors="coerce")


def validate_frame(frame, min_rows=MIN_CLEAN_ROWS):
    errors, notes = [], []
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        return ContractReport([f"missing required columns: {missing}"], [])
    extra = [c for c in frame.columns if c not in REQUIRED]
    if extra:
        notes.append(f"extra columns {extra} are carried through; NaNs in them will drop rows "
                     "at load (the transform drops any-NaN rows)")
    numeric = {}
    non_numeric = []
    for column in NUMERIC_COLUMNS:
        coerced = pd.to_numeric(frame[column], errors="coerce")
        if int(coerced.isna().sum()) > int(frame[column].isna().sum()):
            non_numeric.append(column)
        numeric[column] = coerced
    if non_numeric:
        errors.append(f"non-numeric values in {non_numeric}")
    dates = _parse_dates(frame["Date"])
    parsed = dates.dropna()
    if len(parsed) == 0:
        errors.append("no parseable dates in 'Date'")
        return ContractReport(errors, notes)
    unparseable = int(dates.isna().sum())
    if unparseable:
        notes.append(f"{unparseable} unparseable date(s) - those rows drop at load")
    duplicates = int(parsed.duplicated().sum())
    if duplicates:
        errors.append(f"{duplicates} duplicate date(s) - forbidden by the contract")
    if not parsed.is_monotonic_increasing:
        notes.append("dates not sorted ascending - the load transform sorts")
    if not non_numeric:
        negative = [c for c in PRICE_COLUMNS if bool((numeric[c] < 0).any())]
        if negative:
            errors.append(f"negative prices in {negative}")
        if bool((numeric["Volume"] < 0).any()):
            errors.append("negative values in Volume")
        high_low = int((numeric["High"] < numeric["Low"]).sum())
        if high_low:
            errors.append(f"{high_low} row(s) with High < Low")
        zero = int((numeric["Volume"] == 0).sum())
        if zero:
            notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
        any_nan = frame["Date"].isna()
        for column in NUMERIC_COLUMNS:
            any_nan = any_nan | numeric[column].isna()
        nan_rows = int(any_nan.sum())
        if nan_rows:
            notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
        numeric_nan = numeric[NUMERIC_COLUMNS[0]].isna()
        for column in NUMERIC_COLUMNS[1:]:
            numeric_nan = numeric_nan | numeric[column].isna()
        clean = int((dates.notna() & (numeric["Volume"] != 0) & ~numeric_nan).sum())
        if clean < min_rows:
            notes.append(f"{clean} clean row(s) < recommended minimum {min_rows} "
                         f"({WARMUP_ROWS} warm-up + {OFFSET + PERIOD} lags) - the default counter "
                         "window needs more history (docs/DATA_CONTRACT.md §1)")
    return ContractReport(errors, notes)
