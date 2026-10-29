"""The EOD input contract: validation of a 7-column frame and its report."""
import pandas as pd

REQUIRED = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICES = ["Open", "High", "Low", "Close", "Adj Close"]
NUMERIC = PRICES + ["Volume"]
WARMUP_ROWS = 720
OFFSET_ROWS = 30
PERIOD_ROWS = 365
MIN_ROWS = WARMUP_ROWS + OFFSET_ROWS + PERIOD_ROWS


class ContractError(ValueError):
    """A frame that cannot be validated at all."""


class ContractReport:
    def __init__(self):
        self.errors = []
        self.notes = []

    def ok(self):
        return not self.errors

    def lines(self):
        if not self.errors and not self.notes:
            return ["contract: clean"]
        return [f"ERROR: {error}" for error in self.errors] + \
               [f"note:  {note}" for note in self.notes]


def validate_frame(frame, min_rows=MIN_ROWS):
    report = ContractReport()
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        report.errors.append(f"missing required columns: {missing}")
        return report
    extra = [column for column in frame.columns if column not in REQUIRED]
    if extra:
        report.notes.append(f"extra columns {extra} are carried through; NaNs in them will drop "
                            "rows at load (the transform drops any-NaN rows)")
    numeric = {}
    non_numeric = []
    for column in NUMERIC:
        coerced = pd.to_numeric(frame[column], errors="coerce")
        if int(coerced.isna().sum()) > int(frame[column].isna().sum()):
            non_numeric.append(column)
        numeric[column] = coerced
    if non_numeric:
        report.errors.append(f"non-numeric values in {non_numeric}")

    parsed = pd.to_datetime(frame["Date"], errors="coerce")
    unparseable = int(parsed.isna().sum())
    if unparseable == len(frame):
        report.errors.append("no parseable dates in 'Date'")
        return report
    if unparseable:
        report.notes.append(f"{unparseable} unparseable date(s) - those rows drop at load")
    valid = parsed.dropna()
    duplicates = int(valid.duplicated().sum())
    if duplicates:
        report.errors.append(f"{duplicates} duplicate date(s) - forbidden by the contract")
    if not valid.is_monotonic_increasing:
        report.notes.append("dates not sorted ascending - the load transform sorts")

    if not non_numeric:
        negative = [column for column in PRICES if bool((numeric[column] < 0).any())]
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
        nan_numeric = pd.concat([numeric[column].isna() for column in NUMERIC], axis=1).any(axis=1)
        nan_rows = int((nan_numeric | frame["Date"].isna()).sum())
        if nan_rows:
            report.notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
        clean = int((parsed.notna() & (numeric["Volume"] != 0) & ~nan_numeric).sum())
        if clean < min_rows:
            report.notes.append(
                f"{clean} clean row(s) < recommended minimum {min_rows} (720 warm-up + 395 lags)"
                " - the default counter window needs more history (docs/DATA_CONTRACT.md §1)")
    return report
