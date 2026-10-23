"""The exported seam frame, the EOD input-contract validation and the differential."""
import warnings

import numpy as np
import pandas as pd

from .store import read_series

REQUIRED = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
NUMERIC = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICES = ["Open", "High", "Low", "Close", "Adj Close"]
WARMUP_ROWS = 720
OFFSET = 30
PERIOD = 365
MIN_ROWS = WARMUP_ROWS + OFFSET + PERIOD
DEFAULT_TOLERANCE = 1e-4


# ------------------------------------------------------------------ export
def seam_frame(stored):
    """Project stored rows onto the 7-column EOD frame."""
    volume = stored["volume"].to_numpy(dtype="float64")
    if len(volume) > 0 and np.isfinite(volume).all() and (volume == np.floor(volume)).all():
        volume = volume.astype("int64")
    return pd.DataFrame({
        "Date": pd.Series([d.strftime("%Y-%m-%d") for d in stored["datetime"]],
                          dtype="str"),
        "Open": stored["open"].to_numpy(dtype="float64"),
        "High": stored["high"].to_numpy(dtype="float64"),
        "Low": stored["low"].to_numpy(dtype="float64"),
        "Close": stored["close"].to_numpy(dtype="float64"),
        "Adj Close": stored["adjusted_close"].to_numpy(dtype="float64"),
        "Volume": volume,
    })


def export_frame(store, exchange, symbol):
    return seam_frame(read_series(store, exchange, symbol))


def write_csv(frame, path):
    frame.to_csv(path, index=False)


# ------------------------------------------------------------------ validation
class Report:
    def __init__(self, errors, notes):
        self.errors = errors
        self.notes = notes

    @property
    def ok(self):
        return not self.errors

    def lines(self):
        lines = [f"ERROR: {e}" for e in self.errors] + [f"note:  {n}" for n in self.notes]
        return lines or ["contract: clean"]


def _parse_dates(values):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(values, errors="coerce")


def validate(frame, min_rows=MIN_ROWS):
    errors, notes = [], []
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        errors.append(f"missing required columns: {missing}")
        return Report(errors, notes)
    extra = [c for c in frame.columns if c not in REQUIRED]
    if extra:
        notes.append(f"extra columns {extra} are carried through; NaNs in them will drop "
                     f"rows at load (the transform drops any-NaN rows)")

    numeric = {}
    non_numeric = []
    for col in NUMERIC:
        coerced = pd.to_numeric(frame[col], errors="coerce")
        if int(coerced.isna().sum()) > int(frame[col].isna().sum()):
            non_numeric.append(col)
        numeric[col] = coerced
    if non_numeric:
        errors.append(f"non-numeric values in {non_numeric}")

    parsed = _parse_dates(frame["Date"])
    parsed_ok = parsed.notna()
    if not parsed_ok.any():
        errors.append("no parseable dates in 'Date'")
        return Report(errors, notes)
    unparsed = int((~parsed_ok).sum())
    if unparsed:
        notes.append(f"{unparsed} unparseable date(s) - those rows drop at load")
    good = parsed[parsed_ok]
    dupes = int(good.duplicated().sum())
    if dupes:
        errors.append(f"{dupes} duplicate date(s) - forbidden by the contract")
    if not good.is_monotonic_increasing:
        notes.append("dates not sorted ascending - the load transform sorts")

    if not non_numeric:
        negative = [c for c in PRICES if bool((numeric[c] < 0).any())]
        if negative:
            errors.append(f"negative prices in {negative}")
        if bool((numeric["Volume"] < 0).any()):
            errors.append("negative values in Volume")
        inverted = int((numeric["High"] < numeric["Low"]).sum())
        if inverted:
            errors.append(f"{inverted} row(s) with High < Low")
        zero = int((numeric["Volume"] == 0).sum())
        if zero:
            notes.append(f"{zero} zero-volume row(s) - dropped at load by policy")
        numeric_nan = pd.concat([numeric[c].isna() for c in NUMERIC], axis=1).any(axis=1)
        nan_rows = int((numeric_nan | frame["Date"].isna()).sum())
        if nan_rows:
            notes.append(f"{nan_rows} row(s) with NaN - dropped at load")
        clean = int((parsed_ok & (numeric["Volume"] != 0) & ~numeric_nan).sum())
        if clean < min_rows:
            notes.append(
                f"{clean} clean row(s) < recommended minimum {min_rows} "
                f"({WARMUP_ROWS} warm-up + {OFFSET + PERIOD} lags) - the default counter "
                f"window needs more history (docs/DATA_CONTRACT.md §1)")
    return Report(errors, notes)


# ------------------------------------------------------------------ differential
def differential(a, b, a_label, b_label, tolerance=DEFAULT_TOLERANCE):
    """Tolerance-based cell comparison on identical Date strings; (lines, ok)."""
    a = a.sort_values("Date", kind="stable").reset_index(drop=True)
    b = b.sort_values("Date", kind="stable").reset_index(drop=True)
    a_dates = set(a["Date"])
    b_dates = set(b["Date"])
    merged = a.merge(b, on="Date", how="inner", suffixes=("_a", "_b"))
    common = len(merged)
    lines = [f"differential: {a_label} vs {b_label} (relative tolerance {tolerance:g})",
             f"rows: {len(a)} in {a_label}, {len(b)} in {b_label}, {common} dates in common"]
    unmatched = 0
    for label, only in ((a_label, sorted(a_dates - b_dates)),
                        (b_label, sorted(b_dates - a_dates))):
        if only:
            unmatched += len(only)
            listed = ", ".join(only[:5])
            if len(only) > 5:
                listed += f" (+{len(only) - 5} more)"
            lines.append(f"only in {label}: {len(only)} date(s): {listed}")
    cells = 0
    dates = list(merged["Date"])
    for col in NUMERIC:
        av = merged[f"{col}_a"].to_numpy(dtype="float64")
        bv = merged[f"{col}_b"].to_numpy(dtype="float64")
        with np.errstate(divide="ignore", invalid="ignore"):
            denom = np.maximum(np.abs(av), np.abs(bv))
            denom = np.where(denom == 0, 1.0, denom)
            rel = np.abs(av - bv) / denom
        a_nan = np.isnan(av)
        b_nan = np.isnan(bv)
        rel = np.where(a_nan & b_nan, 0.0, np.where(a_nan ^ b_nan, np.inf, rel))
        beyond = int((rel > tolerance).sum())
        if beyond == 0:
            worst = rel.max() if len(rel) else 0.0
            lines.append(f"{col}: within tolerance (max {worst:.3%})")
        else:
            w = int(np.argmax(rel))
            lines.append(f"{col}: {beyond}/{common} beyond tolerance, worst {rel[w]:.3%} "
                         f"on {dates[w]} ({a_label}={av[w]!r}, {b_label}={bv[w]!r})")
        cells += beyond
    ok = cells == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {cells} cell(s) beyond tolerance, {unmatched} unmatched "
                     f"date(s) - review before scale-out")
    return lines, ok
