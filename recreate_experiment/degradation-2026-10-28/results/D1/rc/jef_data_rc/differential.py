"""Tolerance-based comparison of two 7-column frames aligned on Date."""
import numpy as np

COMPARED = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_TOLERANCE = 1e-4
LISTED_DATES = 5


def relative_differences(a, b):
    with np.errstate(invalid="ignore", divide="ignore"):
        denominator = np.maximum(np.abs(a), np.abs(b))
        denominator = np.where(denominator == 0, 1.0, denominator)
        rel = np.abs(a - b) / denominator
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    rel = np.where(nan_a & nan_b, 0.0, rel)
    rel = np.where(nan_a ^ nan_b, np.inf, rel)
    return rel


def differential_report(frame_a, frame_b, label_a, label_b, tolerance=DEFAULT_TOLERANCE):
    """(report lines, ok) of frame_a against frame_b."""
    sorted_a = frame_a.sort_values("Date", kind="stable")
    sorted_b = frame_b.sort_values("Date", kind="stable")
    by_date_a = sorted_a.drop_duplicates(subset="Date", keep="first").set_index("Date")
    by_date_b = sorted_b.drop_duplicates(subset="Date", keep="first").set_index("Date")
    dates_a, dates_b = set(by_date_a.index), set(by_date_b.index)
    common = sorted(dates_a & dates_b)
    only = [(label_a, sorted(dates_a - dates_b)), (label_b, sorted(dates_b - dates_a))]
    lines = [f"differential: {label_a} vs {label_b} (relative tolerance {tolerance:g})",
             f"rows: {len(frame_a)} in {label_a}, {len(frame_b)} in {label_b}, "
             f"{len(common)} dates in common"]
    for label, dates in only:
        if dates:
            listed = ", ".join(str(day) for day in dates[:LISTED_DATES])
            if len(dates) > LISTED_DATES:
                listed += f" (+{len(dates) - LISTED_DATES} more)"
            lines.append(f"only in {label}: {len(dates)} date(s): {listed}")
    beyond_total = 0
    for column in COMPARED:
        values_a = by_date_a.loc[common, column].to_numpy(dtype="float64") if common \
            else np.array([], dtype="float64")
        values_b = by_date_b.loc[common, column].to_numpy(dtype="float64") if common \
            else np.array([], dtype="float64")
        rel = relative_differences(values_a, values_b)
        beyond = int((rel > tolerance).sum())
        if beyond == 0:
            worst = float(rel.max()) if len(rel) else 0.0
            lines.append(f"{column}: within tolerance (max {worst:.3%})")
        else:
            i = int(np.argmax(rel))
            lines.append(f"{column}: {beyond}/{len(common)} beyond tolerance, worst {rel[i]:.3%} "
                         f"on {common[i]} ({label_a}={values_a[i]!r}, {label_b}={values_b[i]!r})")
        beyond_total += beyond
    unmatched = len(only[0][1]) + len(only[1][1])
    ok = beyond_total == 0 and unmatched == 0
    if ok:
        lines.append("VERDICT: within tolerance, aligned")
    else:
        lines.append(f"VERDICT: {beyond_total} cell(s) beyond tolerance, {unmatched} unmatched "
                     "date(s) - review before scale-out")
    return lines, ok
