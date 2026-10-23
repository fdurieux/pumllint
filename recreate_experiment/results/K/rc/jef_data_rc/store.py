"""The partitioned Parquet market-data store."""
from __future__ import annotations

import contextlib
import datetime as _dt
import fcntl
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .adjust import adjust, row_days, split_factors

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
STRING_COLUMNS = ["symbol", "exchange", "asset_type", "asset_subtype", "currency",
                  "price_basis"]
FLOAT_COLUMNS = [c for c in COLUMNS if c not in STRING_COLUMNS + ["timestamp", "datetime"]]
SERVED_COLUMNS = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw",
                  "adjusted_close"]

SCHEMA = pa.schema(
    [("timestamp", pa.int64()), ("datetime", pa.timestamp("ms", tz="UTC"))]
    + [(c, pa.float64()) for c in ["open", "high", "low", "close", "volume"]]
    + [(c, pa.string()) for c in ["symbol", "exchange", "asset_type", "asset_subtype"]]
    + [(c, pa.float64()) for c in ["adjustment_factor", "open_raw", "high_raw", "low_raw",
                                   "close_raw", "volume_raw", "adjusted_close",
                                   "cumulative_split_factor"]]
    + [(c, pa.string()) for c in ["currency", "price_basis"]])

YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
VOLUME_BASES = ("raw", "split_adjusted")
LOCK_TIMEOUT = 300.0
LOCK_POLL = 0.5


class StoreError(RuntimeError):
    """A store operation that cannot proceed."""


def empty_frame():
    data = {}
    for column in COLUMNS:
        if column == "timestamp":
            data[column] = pd.Series([], dtype="int64")
        elif column == "datetime":
            data[column] = pd.Series([], dtype="datetime64[ms, UTC]")
        elif column in STRING_COLUMNS:
            data[column] = pd.Series([], dtype="str")
        else:
            data[column] = pd.Series([], dtype="float64")
    return pd.DataFrame(data, columns=COLUMNS)


def _number(value):
    if value is None:
        return math.nan
    return float(value)


def _floats(values):
    return np.array([_number(v) for v in values], dtype=np.float64)


def _same(a, b):
    if a == b:
        return True
    return isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)


def build_rows(dates, opens, highs, lows, closes, adjusted, volumes, *, symbol, exchange,
               asset_type, currency, price_basis, volume_basis, splits):
    """Stored rows for served values (raw-ized and adjusted per the basis)."""
    if len(dates) == 0:
        return empty_frame()
    parsed = pd.to_datetime(pd.Series(list(dates), dtype=object), utc=True, errors="coerce")
    bad = [dates[i] for i in range(len(dates)) if pd.isna(parsed.iloc[i])]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    timestamp = parsed.astype("int64") // 10 ** 6
    stamp = parsed.dt.as_unit("ms")
    open_raw, high_raw, low_raw = _floats(opens), _floats(highs), _floats(lows)
    close_raw, served_volume, adjusted_close = _floats(closes), _floats(volumes), _floats(adjusted)
    if price_basis == "raw":
        if volume_basis == "split_adjusted":
            volume_raw = served_volume / split_factors(row_days(stamp), splits)
        elif volume_basis == "raw":
            volume_raw = served_volume
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        volume_raw = served_volume
    n = len(dates)
    with np.errstate(divide="ignore", invalid="ignore"):
        adjustment_factor = adjusted_close / close_raw
    frame = pd.DataFrame({
        "timestamp": timestamp.to_numpy(dtype=np.int64),
        "datetime": stamp.reset_index(drop=True),
        "open": open_raw, "high": high_raw, "low": low_raw, "close": close_raw,
        "volume": volume_raw,
        "symbol": pd.Series([symbol] * n, dtype="str"),
        "exchange": pd.Series([exchange] * n, dtype="str"),
        "asset_type": pd.Series([asset_type] * n, dtype="str"),
        "asset_subtype": pd.Series([""] * n, dtype="str"),
        "adjustment_factor": adjustment_factor,
        "open_raw": open_raw, "high_raw": high_raw, "low_raw": low_raw,
        "close_raw": close_raw, "volume_raw": volume_raw, "adjusted_close": adjusted_close,
        "cumulative_split_factor": np.ones(n, dtype=np.float64),
        "currency": pd.Series([currency] * n, dtype="str"),
        "price_basis": pd.Series([price_basis] * n, dtype="str"),
    }, columns=COLUMNS)
    if price_basis == "raw":
        frame = adjust(frame, splits)
    return frame


def rows_from_bars(bars, **labels):
    def column(key):
        return [b.get(key) for b in bars]

    adjusted = [b["adjusted_close"] if "adjusted_close" in b else b.get("close")
                for b in bars]
    return build_rows([b["date"] for b in bars], column("open"), column("high"),
                      column("low"), column("close"), adjusted, column("volume"), **labels)


def _sorted_unique(frame):
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates(subset="timestamp", keep="first")
    return frame.reset_index(drop=True)


def _years(frame):
    return frame["datetime"].dt.tz_convert("UTC").dt.year.to_numpy()


class ParquetStore:
    """Series under {root}/market_data/exchange=X/symbol=Y/year=YYYY/data.parquet."""

    def __init__(self, root, lock_timeout=LOCK_TIMEOUT, lock_poll=LOCK_POLL):
        self.root = str(root)
        self.lock_timeout = lock_timeout
        self.lock_poll = lock_poll

    def series_dir(self, exchange, symbol):
        return Path(self.root) / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def _year_files(self, exchange, symbol):
        directory = self.series_dir(exchange, symbol)
        if not directory.is_dir():
            return []
        return sorted(p for p in directory.glob("year=*/data.parquet") if p.is_file())

    @contextlib.contextmanager
    def _lock(self, exchange, symbol):
        directory = self.series_dir(exchange, symbol)
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / ".lock"
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.monotonic() + self.lock_timeout
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StoreError(
                            f"{exchange}/{symbol}: another writer holds the store lock "
                            f"after {self.lock_timeout:g}s ({lock_path})") from None
                    time.sleep(self.lock_poll)
            for leftover in directory.glob("year=*/data.parquet.tmp"):
                leftover.unlink()
            yield
        finally:
            os.close(fd)

    # ------------------------------------------------------------------ reads
    def load(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        return _sorted_unique(frame)[COLUMNS]

    def latest_date(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return None
        frame = pd.read_parquet(files[-1], columns=["datetime"])
        if len(frame) == 0:
            return None
        return max(_dt.date.fromisoformat(d) for d in row_days(frame["datetime"]))

    def recent_dates(self, exchange, symbol, n):
        files = self._year_files(exchange, symbol)
        days = set()
        rows = 0
        for path in reversed(files):
            frame = pd.read_parquet(path, columns=["datetime"])
            days.update(row_days(frame["datetime"]))
            rows += len(frame)
            if rows >= n:
                break
        return sorted(days)[-n:] if n > 0 else []

    # ----------------------------------------------------------------- writes
    def _write_years(self, exchange, symbol, frame, years, prune=False):
        directory = self.series_dir(exchange, symbol)
        all_years = _years(frame)
        for year in sorted(set(int(y) for y in years)):
            part = frame[all_years == year].reset_index(drop=True)
            target_dir = directory / f"year={year:04d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            tmp = target_dir / "data.parquet.tmp"
            table = pa.Table.from_pandas(part[COLUMNS], schema=SCHEMA, preserve_index=False)
            pq.write_table(table, tmp, compression="snappy")
            os.replace(tmp, target_dir / "data.parquet")
        if prune:
            keep = {f"year={int(y):04d}" for y in set(all_years.tolist())}
            for path in sorted(directory.glob("year=*/data.parquet")):
                if path.parent.name not in keep:
                    path.unlink()
                    with contextlib.suppress(OSError):
                        path.parent.rmdir()

    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                       asset_type, currency):
        """Merge served bars newest-wins; returns (bars handed in, revision records)."""
        served = rows_from_bars(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                                currency=currency, price_basis=price_basis,
                                volume_basis=volume_basis, splits=splits)
        revisions = []
        if len(served) == 0:
            return len(bars), revisions
        with self._lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if len(stored) == 0:
                fresh = _sorted_unique(served)
                self._write_years(exchange, symbol, fresh, _years(fresh))
                return len(bars), revisions
            position = {int(ts): i for i, ts in enumerate(stored["timestamp"].tolist())}
            served_days = row_days(served["datetime"])
            stored_values = {c: stored[c].tolist() for c in SERVED_COLUMNS}
            served_values = {c: served[c].tolist() for c in SERVED_COLUMNS}
            replace = {}
            new_rows = []
            for i, ts in enumerate(served["timestamp"].tolist()):
                j = position.get(int(ts))
                if j is None:
                    new_rows.append(i)
                    continue
                changed = [c for c in SERVED_COLUMNS
                           if not _same(stored_values[c][j], served_values[c][i])]
                if changed:
                    replace[j] = i
                    for c in changed:
                        revisions.append({"date": served_days[i], "column": c,
                                          "stored": float(stored_values[c][j]),
                                          "served": float(served_values[c][i])})
            if not replace and not new_rows:
                return len(bars), revisions
            keep = stored.drop(index=list(replace))
            incoming = served.iloc[sorted(set(replace.values()) | set(new_rows))]
            merged = _sorted_unique(pd.concat([keep, incoming], ignore_index=True))
            touched = served.iloc[sorted(set(replace.values()) | set(new_rows))]
            self._write_years(exchange, symbol, merged, _years(touched))
        return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                    mode="append", asset_type="stock", currency="USD"):
        """Append (stored rows win) or overwrite; returns the number of incoming bars."""
        incoming = rows_from_bars(bars, symbol=symbol, exchange=exchange,
                                  asset_type=asset_type, currency=currency,
                                  price_basis=price_basis, volume_basis=volume_basis,
                                  splits=splits)
        return self._ingest(exchange, symbol, incoming, mode, len(bars))

    def _ingest(self, exchange, symbol, incoming, mode, count):
        if mode == "overwrite":
            with self._lock(exchange, symbol):
                fresh = _sorted_unique(incoming)
                self._write_years(exchange, symbol, fresh, _years(fresh), prune=True)
            return count
        if mode != "append":
            raise StoreError(f"unknown ingest mode {mode!r}")
        if len(incoming) == 0:
            return count
        with self._lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            merged = _sorted_unique(pd.concat([stored, incoming], ignore_index=True)
                                    if len(stored) else incoming)
            self._write_years(exchange, symbol, merged, _years(incoming))
        return count

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD"):
        """Replace the series with a whole Yahoo CSV; returns the CSV row count."""
        frame = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in frame.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        incoming = build_rows(frame["Date"].tolist(), frame["Open"].tolist(),
                              frame["High"].tolist(), frame["Low"].tolist(),
                              frame["Close"].tolist(), frame["Adj Close"].tolist(),
                              frame["Volume"].tolist(), symbol=symbol, exchange=exchange,
                              asset_type=asset_type, currency=currency,
                              price_basis="split_adjusted", volume_basis="raw", splits=[])
        return self._ingest(exchange, symbol, incoming, "overwrite", len(frame))

    def reapply_adjustment(self, exchange, symbol, splits):
        """Re-derive the whole series from *_raw; rewrites only when a value moved."""
        with self._lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if len(stored) == 0:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(stored, splits)
            if not adjusted.equals(stored):
                self._write_years(exchange, symbol, adjusted, _years(adjusted), prune=True)
            return len(stored)


EXPORT_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


def seam_frame(stored):
    """The 7-column seam frame of a stored series."""
    volume = stored["volume"].to_numpy(dtype=np.float64)
    integral = (len(volume) > 0 and bool(np.isfinite(volume).all())
                and bool((volume == np.floor(volume)).all()))
    frame = pd.DataFrame({
        "Date": pd.Series(row_days(stored["datetime"]).tolist(), dtype="str"),
        "Open": stored["open"].to_numpy(dtype=np.float64),
        "High": stored["high"].to_numpy(dtype=np.float64),
        "Low": stored["low"].to_numpy(dtype=np.float64),
        "Close": stored["close"].to_numpy(dtype=np.float64),
        "Adj Close": stored["adjusted_close"].to_numpy(dtype=np.float64),
        "Volume": volume.astype(np.int64) if integral else volume,
    }, columns=EXPORT_COLUMNS)
    return frame


def export_frame(store, exchange, symbol):
    """The seam frame of exchange/symbol; an empty series cannot be exported."""
    stored = store.load(exchange, symbol)
    if len(stored) == 0:
        raise StoreError(f"nothing stored for {exchange}/{symbol}")
    return seam_frame(stored)
