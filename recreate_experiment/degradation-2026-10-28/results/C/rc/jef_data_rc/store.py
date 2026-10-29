"""The partitioned Parquet market-data store and the seam export projection."""
import fcntl
import math
import os
import time
import warnings
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from jef_data_rc.adjust import DERIVED_COLUMNS, adjust, split_factors

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
FLOAT_COLUMNS = ["open", "high", "low", "close", "volume", "adjustment_factor", "open_raw",
                 "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
                 "cumulative_split_factor"]
STRING_COLUMNS = ["symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis"]
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
SEAM_COLUMNS = YAHOO_COLUMNS

LOCK_TIMEOUT = 300.0
LOCK_POLL = 0.5


class StoreError(RuntimeError):
    """A store operation that cannot proceed."""


def _schema():
    import pyarrow as pa
    fields = []
    for name in COLUMNS:
        if name == "timestamp":
            fields.append((name, pa.int64()))
        elif name == "datetime":
            fields.append((name, pa.timestamp("ms", tz="UTC")))
        elif name in STRING_COLUMNS:
            fields.append((name, pa.string()))
        else:
            fields.append((name, pa.float64()))
    return pa.schema(fields)


def empty_frame():
    """The zero-row read-back of a series with no year file."""
    return pd.DataFrame(columns=COLUMNS)


def parse_bar_dates(values):
    """Parse bar dates as UTC instants (format inferred from the first); refuse any that fail."""
    series = pd.Series(list(values), dtype=object)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(series, utc=True, errors="coerce")
    bad = [value for value, moment in zip(values, parsed) if pd.isna(moment)]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    micro = parsed.dt.as_unit("us").astype("int64").to_numpy()
    timestamp = micro // 10**6
    moments = parsed.dt.as_unit("ms").reset_index(drop=True)
    return timestamp.astype(np.int64), moments


def _floats(bars, key):
    return np.array([bar[key] for bar in bars], dtype=np.float64)


def build_rows(bars, *, symbol, exchange, asset_type, currency, price_basis, volume_basis,
               splits):
    """Stored rows (the 21 columns) for a list of provider bars."""
    n = len(bars)
    if n == 0:
        frame = pd.DataFrame({name: pd.Series([], dtype="float64") for name in COLUMNS})
        frame["timestamp"] = pd.Series([], dtype="int64")
        frame["datetime"] = pd.Series([], dtype="datetime64[ms, UTC]")
        for name in STRING_COLUMNS:
            frame[name] = pd.Series([], dtype=object)
        return frame[COLUMNS]
    timestamp, moments = parse_bar_dates([bar["date"] for bar in bars])
    open_raw = _floats(bars, "open")
    high_raw = _floats(bars, "high")
    low_raw = _floats(bars, "low")
    close_raw = _floats(bars, "close")
    served_volume = _floats(bars, "volume")
    adjusted_close = np.array([bar["adjusted_close"] if "adjusted_close" in bar else bar["close"]
                               for bar in bars], dtype=np.float64)
    with np.errstate(all="ignore"):
        adjustment_factor = adjusted_close / close_raw
    days = list(moments.dt.date)
    if price_basis == "raw":
        factor = split_factors(days, splits)
        if volume_basis == "split_adjusted":
            volume_raw = served_volume / factor
        elif volume_basis == "raw":
            volume_raw = served_volume
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        volume_raw = served_volume
    frame = pd.DataFrame({
        "timestamp": timestamp,
        "datetime": moments,
        "open": open_raw.copy(),
        "high": high_raw.copy(),
        "low": low_raw.copy(),
        "close": close_raw.copy(),
        "volume": volume_raw.copy(),
        "symbol": [symbol] * n,
        "exchange": [exchange] * n,
        "asset_type": [asset_type] * n,
        "asset_subtype": [""] * n,
        "adjustment_factor": adjustment_factor,
        "open_raw": open_raw,
        "high_raw": high_raw,
        "low_raw": low_raw,
        "close_raw": close_raw,
        "volume_raw": volume_raw,
        "adjusted_close": adjusted_close,
        "cumulative_split_factor": np.ones(n, dtype=np.float64),
        "currency": [currency] * n,
        "price_basis": [price_basis] * n,
    })
    if price_basis == "raw":
        frame = adjust(frame, splits)
    return frame[COLUMNS]


def _years(frame):
    if len(frame) == 0:
        return set()
    return set(int(y) for y in frame["datetime"].dt.year)


def _same(a, b):
    if a == b:
        return True
    try:
        return math.isnan(a) and math.isnan(b)
    except TypeError:
        return False


def _arrays_equal(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return a.shape == b.shape and bool(np.array_equal(a, b, equal_nan=True))


class ParquetStore:
    """Series under {root}/market_data/exchange=E/symbol=S/year=YYYY/data.parquet."""

    def __init__(self, root, lock_timeout=LOCK_TIMEOUT):
        self.root = str(root)
        self.lock_timeout = lock_timeout

    def series_dir(self, exchange, symbol):
        return Path(self.root) / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def year_files(self, exchange, symbol):
        return sorted(self.series_dir(exchange, symbol).glob("year=*/data.parquet"))

    @contextmanager
    def _lock(self, exchange, symbol):
        directory = self.series_dir(exchange, symbol)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / ".lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + self.lock_timeout
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StoreError(
                            f"{exchange}/{symbol}: another writer holds the store lock after "
                            f"{self.lock_timeout:g}s ({path})") from None
                    time.sleep(LOCK_POLL)
            yield
        finally:
            os.close(fd)

    def _drop_tmp(self, exchange, symbol):
        for leftover in self.series_dir(exchange, symbol).glob("year=*/data.parquet.tmp"):
            leftover.unlink()

    def _write_years(self, exchange, symbol, frame, years, prune=False):
        import pyarrow as pa
        import pyarrow.parquet as pq
        schema = _schema()
        directory = self.series_dir(exchange, symbol)
        year_of = frame["datetime"].dt.year
        for year in sorted(years):
            rows = frame[year_of == year][COLUMNS].reset_index(drop=True)
            target_dir = directory / f"year={year}"
            target_dir.mkdir(parents=True, exist_ok=True)
            tmp = target_dir / "data.parquet.tmp"
            table = pa.Table.from_pandas(rows, schema=schema, preserve_index=False)
            pq.write_table(table, tmp, compression="snappy")
            os.replace(tmp, target_dir / "data.parquet")
        if prune:
            keep = {f"year={year}" for year in years}
            for path in self.year_files(exchange, symbol):
                if path.parent.name not in keep:
                    path.unlink()
                    try:
                        path.parent.rmdir()
                    except OSError:
                        pass

    def load(self, exchange, symbol):
        files = self.year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frame = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True)
        frame = frame.sort_values("timestamp", kind="stable")
        frame = frame.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
        return frame[COLUMNS]

    def latest_date(self, exchange, symbol):
        files = self.year_files(exchange, symbol)
        if not files:
            return None
        frame = pd.read_parquet(files[-1], columns=["datetime"])
        if len(frame) == 0:
            return None
        return max(frame["datetime"].dt.date)

    def recent_dates(self, exchange, symbol, n):
        collected = []
        for path in reversed(self.year_files(exchange, symbol)):
            frame = pd.read_parquet(path, columns=["datetime"])
            collected.extend(frame["datetime"].dt.date)
            if len(collected) >= n:
                break
        return sorted(set(collected))[-n:] if collected else []

    def has_rows(self, exchange, symbol):
        return self.latest_date(exchange, symbol) is not None

    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis, *,
                       asset_type, currency):
        """Newest-wins merge of served bars; returns (served bar count, revisions)."""
        incoming = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                              currency=currency, price_basis=price_basis,
                              volume_basis=volume_basis, splits=splits)
        incoming = incoming.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
        with self._lock(exchange, symbol):
            self._drop_tmp(exchange, symbol)
            stored = self.load(exchange, symbol)
            if len(stored) == 0:
                if len(incoming):
                    ordered = incoming.sort_values("timestamp", kind="stable").reset_index(drop=True)
                    self._write_years(exchange, symbol, ordered, _years(ordered))
                return len(bars), []
            position = {int(ts): i for i, ts in enumerate(stored["timestamp"].tolist())}
            stored_values = {c: stored[c].to_numpy(dtype=np.float64) for c in AS_SERVED}
            served_values = {c: incoming[c].to_numpy(dtype=np.float64) for c in AS_SERVED}
            served_days = [d.isoformat() for d in incoming["datetime"].dt.date]
            replaced = []
            fresh = []
            revisions = []
            for k, ts in enumerate(incoming["timestamp"].tolist()):
                j = position.get(int(ts))
                if j is None:
                    fresh.append(k)
                    continue
                changed = False
                for column in AS_SERVED:
                    old = stored_values[column][j]
                    new = served_values[column][k]
                    if not _same(old, new):
                        changed = True
                        revisions.append({"date": served_days[k], "column": column,
                                          "stored": float(old), "served": float(new)})
                if changed:
                    replaced.append((j, k))
            if not replaced and not fresh:
                return len(bars), revisions
            drop = {j for j, _ in replaced}
            keep = stored.drop(index=sorted(drop))
            take = sorted([k for _, k in replaced] + fresh)
            arriving = incoming.iloc[take]
            merged = pd.concat([keep, arriving], ignore_index=True)
            merged = merged.sort_values("timestamp", kind="stable").reset_index(drop=True)
            self._write_years(exchange, symbol, merged, _years(arriving))
            return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                    mode="append", *, asset_type, currency):
        """Append served bars; stored rows win on equal timestamps."""
        if mode != "append":
            raise StoreError(f"unknown ingest mode {mode!r}")
        incoming = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                              currency=currency, price_basis=price_basis,
                              volume_basis=volume_basis, splits=splits)
        with self._lock(exchange, symbol):
            self._drop_tmp(exchange, symbol)
            stored = self.load(exchange, symbol)
            if len(incoming) == 0:
                return len(bars)
            parts = [incoming] if len(stored) == 0 else [stored, incoming]
            merged = pd.concat(parts, ignore_index=True)
            merged = merged.sort_values("timestamp", kind="stable")
            merged = merged.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
            self._write_years(exchange, symbol, merged, _years(incoming))
            return len(bars)

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD"):
        """Replace the series with a 7-column Yahoo CSV; returns the CSV row count."""
        table = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in table.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        columns = {c: table[c].tolist() for c in YAHOO_COLUMNS}
        bars = [{"date": columns["Date"][i], "open": columns["Open"][i],
                 "high": columns["High"][i], "low": columns["Low"][i],
                 "close": columns["Close"][i], "adjusted_close": columns["Adj Close"][i],
                 "volume": columns["Volume"][i]} for i in range(len(table))]
        rows = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                          currency=currency, price_basis="split_adjusted", volume_basis="raw",
                          splits=[])
        rows = rows.sort_values("timestamp", kind="stable")
        rows = rows.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
        with self._lock(exchange, symbol):
            self._drop_tmp(exchange, symbol)
            self._write_years(exchange, symbol, rows, _years(rows), prune=True)
        return len(table)

    def reapply_adjustment(self, exchange, symbol, splits):
        """Re-derive the mains of a raw series from *_raw; rewrite only when a value moved."""
        with self._lock(exchange, symbol):
            self._drop_tmp(exchange, symbol)
            frame = self.load(exchange, symbol)
            if len(frame) == 0:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(frame, splits)
            moved = any(not _arrays_equal(frame[c], adjusted[c]) for c in DERIVED_COLUMNS)
            if moved:
                self._write_years(exchange, symbol, adjusted, _years(adjusted), prune=True)
            return len(frame)


def seam_frame(stored):
    """Project stored rows onto the 7-column EOD frame (no filtering, stored order)."""
    volume = stored["volume"].to_numpy(dtype=np.float64)
    frame = pd.DataFrame({
        "Date": stored["datetime"].dt.strftime("%Y-%m-%d"),
        "Open": stored["open"].astype("float64"),
        "High": stored["high"].astype("float64"),
        "Low": stored["low"].astype("float64"),
        "Close": stored["close"].astype("float64"),
        "Adj Close": stored["adjusted_close"].astype("float64"),
    })
    integral = (len(volume) > 0 and bool(np.all(np.isfinite(volume)))
                and bool(np.all(volume == np.floor(volume))))
    if integral:
        frame["Volume"] = pd.Series(volume.astype(np.int64), index=frame.index)
    else:
        frame["Volume"] = pd.Series(volume, index=frame.index)
    return frame[SEAM_COLUMNS]


def export_series(store, exchange, symbol):
    return seam_frame(store.load(exchange, symbol))


def utc_dates(frame):
    return list(frame["datetime"].dt.date)


def iso(day):
    return day.isoformat() if isinstance(day, date) else str(day)
