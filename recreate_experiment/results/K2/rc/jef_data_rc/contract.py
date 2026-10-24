"""Validation of a 7-column EOD frame against the input contract."""
from __future__ import annotations

import pandas as pd

REQUIRED = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICES = ["Open", "High", "Low", "Close", "Adj Close"]
NUMERIC = PRICES + ["Volume"]
WARM_UP = 720
OFFSET = 30
PERIOD = 365
MIN_CLEAN_ROWS = WARM_UP + OFFSET + PERIOD


class ContractError(ValueError):
    """A frame that cannot be validated at all."""


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


def validate_frame(frame, min_rows=MIN_CLEAN_ROWS):
    errors = []
    notes = []
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        return ContractReport([f"missing required columns: {missing}"], [])
    extra = [c for c in frame.columns if c not in REQUIRED]
    if extra:
        notes.append(f"extra columns {extra} are carried through; NaNs in them will drop rows "
                     f"at load (the transform drops any-NaN rows)")

    coerced = {}
    non_numeric = []
    for column in NUMERIC:
        values = pd.to_numeric(frame[column], errors="coerce")
        coerced[column] = values
        if int(values.isna().sum()) > int(frame[column].isna().sum()):
            non_numeric.append(column)
    if non_numeric:
        errors.append(f"non-numeric values in {non_numeric}")

    parsed = pd.to_datetime(frame["Date"], errors="coerce")
    unparseable = int(parsed.isna().sum())
    if len(frame) > 0 and unparseable == len(frame):
        errors.append("no parseable dates in 'Date'")
        return ContractReport(errors, notes)
    if unparseable:
        notes.append(f"{unparseable} unparseable date(s) - those rows drop at load")
    valid = parsed.dropna()
    duplicates = int(valid.duplicated().sum())
    if duplicates:
        errors.append(f"{duplicates} duplicate date(s) - forbidden by the contract")
    if not valid.is_monotonic_increasing:
        notes.append("dates not sorted ascending - the load transform sorts")

    if not non_numeric:
        negative = [c for c in PRICES if bool((coerced[c] < 0).any())]
        if negative:
            errors.append(f"negative prices in {negative}")
        if bool((coerced["Volume"] < 0).any()):
            errors.append("negative values in Volume")
        inverted = int((coerced["High"] < coerced["Low"]).sum())
        if inverted:
            errors.append(f"{inverted} row(s) with High < Low")
        zero = int((coerced["Volume"] == 0).sum())
        if zero:
            notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
        nan_rows = int(frame[REQUIRED].isna().any(axis=1).sum())
        if nan_rows:
            notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
        numeric = pd.DataFrame({c: coerced[c] for c in NUMERIC})
        clean_mask = parsed.notna() & (coerced["Volume"] != 0) & ~numeric.isna().any(axis=1)
        clean = int(clean_mask.sum())
        if clean < min_rows:
            notes.append(f"{clean} clean row(s) < recommended minimum {min_rows} (720 warm-up "
                         f"+ 395 lags) - the default counter window needs more history "
                         f"(docs/DATA_CONTRACT.md §1)")
    return ContractReport(errors, notes)
