"""The partitioned market-data store: Parquet year files per (exchange, symbol)."""
import contextlib
import fcntl
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .adjustment import adjust, cumulative_factors

SCHEMA = pa.schema([
    ("timestamp", pa.int64()),
    ("datetime", pa.timestamp("ms", tz="UTC")),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.float64()),
    ("symbol", pa.string()),
    ("exchange", pa.string()),
    ("asset_type", pa.string()),
    ("asset_subtype", pa.string()),
    ("adjustment_factor", pa.float64()),
    ("open_raw", pa.float64()),
    ("high_raw", pa.float64()),
    ("low_raw", pa.float64()),
    ("close_raw", pa.float64()),
    ("volume_raw", pa.float64()),
    ("adjusted_close", pa.float64()),
    ("cumulative_split_factor", pa.float64()),
    ("currency", pa.string()),
    ("price_basis", pa.string()),
])
COLUMNS = SCHEMA.names
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
DERIVED = ["open", "high", "low", "close", "volume", "cumulative_split_factor"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
LOCK_TIMEOUT = 300
LOCK_POLL = 0.5


class StoreError(RuntimeError):
    """A store operation that cannot proceed."""


# ------------------------------------------------------------------ layout
def series_dir(store, exchange, symbol):
    return Path(store) / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"


def _year_files(sdir):
    if not sdir.is_dir():
        return []
    return sorted(sdir.glob("year=*/data.parquet"))


def empty_frame():
    return SCHEMA.empty_table().to_pandas()


def _read_file(path):
    return pq.read_table(path).to_pandas()


def read_series(store, exchange, symbol):
    """The full stored series: year files in path order, sorted, de-duplicated."""
    files = _year_files(series_dir(store, exchange, symbol))
    if not files:
        return empty_frame()
    frames = [_read_file(path) for path in files]
    frame = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates(subset="timestamp", keep="first")
    return frame.reset_index(drop=True)[COLUMNS]


def _days(series):
    return [d.strftime("%Y-%m-%d") for d in series]


def latest_session(store, exchange, symbol):
    """Max UTC date inside the lexicographically last year file, or None."""
    files = _year_files(series_dir(store, exchange, symbol))
    if not files:
        return None
    frame = _read_file(files[-1])
    if frame.empty:
        return None
    return frame["datetime"].max().strftime("%Y-%m-%d")


def newest_sessions(store, exchange, symbol, n):
    """The n most recent distinct UTC session dates, ascending."""
    files = _year_files(series_dir(store, exchange, symbol))
    frames = []
    rows = 0
    for path in reversed(files):
        frame = _read_file(path)
        frames.append(frame)
        rows += len(frame)
        if rows >= n:
            break
    days = set()
    for frame in frames:
        days.update(_days(frame["datetime"]))
    return sorted(days)[-n:] if n > 0 else []


# ------------------------------------------------------------------ building rows
def parse_bar_dates(dates):
    """Parse bar dates as UTC instants in the format inferred from the first one."""
    values = pd.Index(list(dates), dtype=object)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(values, utc=True, errors="coerce")
    bad = [value for value, moment in zip(values, parsed) if pd.isna(moment)]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    return parsed


def build_rows(dates, opens, highs, lows, closes, adjusted, volumes, *, symbol,
               exchange, asset_type, currency, price_basis, volume_basis, events):
    """Stored rows for served bars (columns of equal length)."""
    dates = list(dates)
    n = len(dates)
    if n == 0:
        return empty_frame()
    parsed = parse_bar_dates(dates)
    days = list(parsed.strftime("%Y-%m-%d"))
    o = np.asarray(opens, dtype="float64")
    h = np.asarray(highs, dtype="float64")
    lo = np.asarray(lows, dtype="float64")
    c = np.asarray(closes, dtype="float64")
    adj = np.asarray(adjusted, dtype="float64")
    vol = np.asarray(volumes, dtype="float64")

    if price_basis == "raw":
        factor = cumulative_factors(days, events)
        if volume_basis == "split_adjusted":
            v_raw = vol / factor
        elif volume_basis == "raw":
            v_raw = vol
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        v_raw = vol

    with np.errstate(divide="ignore", invalid="ignore"):
        adj_factor = adj / c

    frame = pd.DataFrame({
        "timestamp": np.asarray(parsed.asi8 // 10**6, dtype="int64"),
        "datetime": parsed.as_unit("ms"),
        "open": o.copy(), "high": h.copy(), "low": lo.copy(), "close": c.copy(),
        "volume": v_raw.copy(),
        "symbol": pd.Series([symbol] * n, dtype="str"),
        "exchange": pd.Series([exchange] * n, dtype="str"),
        "asset_type": pd.Series([asset_type] * n, dtype="str"),
        "asset_subtype": pd.Series([""] * n, dtype="str"),
        "adjustment_factor": adj_factor,
        "open_raw": o, "high_raw": h, "low_raw": lo, "close_raw": c,
        "volume_raw": v_raw, "adjusted_close": adj,
        "cumulative_split_factor": np.ones(n, dtype="float64"),
        "currency": pd.Series([currency] * n, dtype="str"),
        "price_basis": pd.Series([price_basis] * n, dtype="str"),
    })
    if price_basis == "raw":
        frame = adjust(frame, events)
    return frame[COLUMNS]


def rows_from_bars(bars, **labels):
    """Stored rows for collector bars (dicts with date/open/high/low/close/volume)."""
    return build_rows(
        [bar["date"] for bar in bars],
        [bar["open"] for bar in bars],
        [bar["high"] for bar in bars],
        [bar["low"] for bar in bars],
        [bar["close"] for bar in bars],
        [bar["adjusted_close"] if "adjusted_close" in bar else bar["close"]
         for bar in bars],
        [bar["volume"] for bar in bars],
        **labels)


# ------------------------------------------------------------------ writing
@contextlib.contextmanager
def _series_lock(sdir, exchange, symbol):
    sdir.mkdir(parents=True, exist_ok=True)
    lock_path = sdir / ".lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + LOCK_TIMEOUT
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise StoreError(
                        f"{exchange}/{symbol}: another writer holds the store lock after "
                        f"{LOCK_TIMEOUT}s ({lock_path})") from None
                time.sleep(LOCK_POLL)
        yield
    finally:
        os.close(fd)


def _clean_tmp(sdir):
    for leftover in sdir.glob("year=*/*.tmp"):
        leftover.unlink()


def _years(frame):
    return set(int(y) for y in frame["datetime"].dt.year)


def _write_years(sdir, frame, years):
    year_of = frame["datetime"].dt.year
    for year in sorted(years):
        part = frame[year_of == year].reset_index(drop=True)
        ydir = sdir / f"year={year:04d}"
        ydir.mkdir(parents=True, exist_ok=True)
        tmp = ydir / "data.parquet.tmp"
        table = pa.Table.from_pandas(part[COLUMNS], schema=SCHEMA, preserve_index=False)
        pq.write_table(table, tmp, compression="snappy")
        os.replace(tmp, ydir / "data.parquet")


def _prune(sdir, keep_years):
    for path in _year_files(sdir):
        year = int(path.parent.name.split("=", 1)[1])
        if year not in keep_years:
            path.unlink()
            with contextlib.suppress(OSError):
                path.parent.rmdir()


def _sorted_unique(frame):
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates(subset="timestamp", keep="first")
    return frame.reset_index(drop=True)


def _same(a, b):
    return a == b or (a != a and b != b)


def reconcile(store, exchange, symbol, bars, **labels):
    """Newest-wins reconcile of served bars into a series; returns (bars, revisions)."""
    incoming = rows_from_bars(bars, symbol=symbol, exchange=exchange, **labels)
    sdir = series_dir(store, exchange, symbol)
    with _series_lock(sdir, exchange, symbol):
        _clean_tmp(sdir)
        stored = read_series(store, exchange, symbol)
        if stored.empty:
            merged = _sorted_unique(incoming)
            if len(merged):
                _write_years(sdir, merged, _years(merged))
            return len(bars), []

        position = {int(ts): i for i, ts in enumerate(stored["timestamp"])}
        stored_values = {col: stored[col].to_numpy() for col in AS_SERVED}
        served_values = {col: incoming[col].to_numpy() for col in AS_SERVED}
        served_ts = incoming["timestamp"].to_numpy()
        served_days = _days(incoming["datetime"])
        served_years = incoming["datetime"].dt.year.to_numpy()

        revisions = []
        replaced = {}
        new_rows = []
        touched = set()
        for j in range(len(incoming)):
            i = position.get(int(served_ts[j]))
            if i is None:
                new_rows.append(j)
                touched.add(int(served_years[j]))
                continue
            changed = [col for col in AS_SERVED
                       if not _same(stored_values[col][i], served_values[col][j])]
            if not changed:
                continue
            for col in changed:
                revisions.append({"date": served_days[j], "column": col,
                                  "stored": float(stored_values[col][i]),
                                  "served": float(served_values[col][j])})
            replaced[i] = j
            touched.add(int(served_years[j]))

        if not replaced and not new_rows:
            return len(bars), revisions
        keep = stored.drop(index=list(replaced))
        taken = incoming.iloc[sorted(set(replaced.values())) + new_rows]
        merged = _sorted_unique(pd.concat([keep, taken], ignore_index=True))
        _write_years(sdir, merged, touched)
        return len(bars), revisions


def append(store, exchange, symbol, bars, **labels):
    """Existing rows win on equal timestamps; only the incoming years are rewritten."""
    incoming = rows_from_bars(bars, symbol=symbol, exchange=exchange, **labels)
    sdir = series_dir(store, exchange, symbol)
    with _series_lock(sdir, exchange, symbol):
        _clean_tmp(sdir)
        stored = read_series(store, exchange, symbol)
        merged = incoming if stored.empty else pd.concat([stored, incoming],
                                                          ignore_index=True)
        merged = _sorted_unique(merged)
        if len(incoming):
            _write_years(sdir, merged, _years(incoming))
    return len(bars)


def overwrite_csv(store, csv_path, exchange, symbol, asset_type, currency="USD"):
    """Replace a series with a Yahoo 7-column CSV; returns the CSV row count."""
    frame = pd.read_csv(csv_path)
    missing = [c for c in YAHOO_COLUMNS if c not in frame.columns]
    if missing:
        raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
    rows = build_rows(
        list(frame["Date"]), frame["Open"].to_numpy(), frame["High"].to_numpy(),
        frame["Low"].to_numpy(), frame["Close"].to_numpy(),
        frame["Adj Close"].to_numpy(), frame["Volume"].to_numpy(),
        symbol=symbol, exchange=exchange, asset_type=asset_type, currency=currency,
        price_basis="split_adjusted", volume_basis="raw", events=[])
    rows = _sorted_unique(rows)
    sdir = series_dir(store, exchange, symbol)
    with _series_lock(sdir, exchange, symbol):
        _clean_tmp(sdir)
        years = _years(rows)
        _write_years(sdir, rows, years)
        _prune(sdir, years)
    return len(frame)


def readjust(store, exchange, symbol, events):
    """Re-derive a raw series' main columns from *_raw; returns the row count."""
    sdir = series_dir(store, exchange, symbol)
    with _series_lock(sdir, exchange, symbol):
        _clean_tmp(sdir)
        frame = read_series(store, exchange, symbol)
        if frame.empty:
            raise StoreError(f"nothing stored for {exchange}/{symbol}")
        adjusted = adjust(frame, events)
        changed = any(
            not np.array_equal(frame[col].to_numpy(dtype="float64"),
                               adjusted[col].to_numpy(dtype="float64"), equal_nan=True)
            for col in DERIVED)
        if changed:
            years = _years(adjusted)
            _write_years(sdir, adjusted, years)
            _prune(sdir, years)
        return len(frame)
