"""The partitioned Parquet market-data store, its write discipline and the seam projection."""
from __future__ import annotations

import contextlib
import datetime as _dt
import errno
import fcntl
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .adjust import adjust, split_factors

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
DERIVED = ["open", "high", "low", "close", "volume", "cumulative_split_factor"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
EXPORT_COLUMNS = YAHOO_COLUMNS
VOLUME_BASES = ("raw", "split_adjusted")


class StoreError(RuntimeError):
    """A store operation that cannot complete."""


def resolve_price_basis(provider, asset_type):
    """Price basis from the provider and the DECLARED asset_type only."""
    if provider in ("binance", "yahoo-csv"):
        return "split_adjusted"
    if asset_type == "crypto":
        return "split_adjusted"
    return "raw"


def _schema():
    import pyarrow as pa

    fields = []
    for name in COLUMNS:
        if name == "timestamp":
            fields.append(pa.field(name, pa.int64()))
        elif name == "datetime":
            fields.append(pa.field(name, pa.timestamp("ms", tz="UTC")))
        elif name in ("symbol", "exchange", "asset_type", "asset_subtype", "currency",
                      "price_basis"):
            fields.append(pa.field(name, pa.string()))
        else:
            fields.append(pa.field(name, pa.float64()))
    return pa.schema(fields)


def empty_frame():
    return pd.DataFrame(columns=COLUMNS)


def _floats(values):
    return np.array(list(values), dtype="float64")


def _same(a, b):
    if a == b:
        return True
    try:
        return math.isnan(a) and math.isnan(b)
    except TypeError:
        return False


def parse_bar_dates(values):
    """UTC instants, the format inferred from the first value; unparseable -> NaT."""
    series = pd.Series(list(values), dtype=object)
    return pd.to_datetime(series, utc=True, errors="coerce")


def build_rows(bars, *, symbol, exchange, asset_type, currency, price_basis,
               volume_basis, splits):
    """The stored rows for a list of bars (nothing is written here)."""
    if not bars:
        return empty_frame()
    dates = [bar["date"] for bar in bars]
    parsed = parse_bar_dates(dates)
    bad = [value for value, instant in zip(dates, parsed.tolist()) if pd.isna(instant)]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    micros = parsed.dt.as_unit("us").astype("int64").to_numpy()
    timestamps = micros // 10 ** 6
    instants = parsed.dt.as_unit("ms")
    days = np.asarray(parsed.dt.strftime("%Y-%m-%d").tolist(), dtype=object)

    open_raw = _floats(bar["open"] for bar in bars)
    high_raw = _floats(bar["high"] for bar in bars)
    low_raw = _floats(bar["low"] for bar in bars)
    close_raw = _floats(bar["close"] for bar in bars)
    served_volume = _floats(bar["volume"] for bar in bars)
    adjusted_close = _floats(bar["adjusted_close"] if "adjusted_close" in bar else bar["close"]
                             for bar in bars)

    if price_basis == "raw":
        if volume_basis == "split_adjusted":
            factors = split_factors(days, splits)
            with np.errstate(divide="ignore", invalid="ignore"):
                volume_raw = served_volume / factors
        elif volume_basis == "raw":
            volume_raw = served_volume.copy()
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        volume_raw = served_volume.copy()

    with np.errstate(divide="ignore", invalid="ignore"):
        adjustment_factor = adjusted_close / close_raw
    n = len(bars)
    frame = pd.DataFrame({
        "timestamp": timestamps.astype("int64"),
        "datetime": instants.reset_index(drop=True),
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
        "cumulative_split_factor": np.ones(n, dtype="float64"),
        "currency": [currency] * n,
        "price_basis": [price_basis] * n,
    }, columns=COLUMNS)
    if price_basis == "raw":
        frame = adjust(frame, splits)
    return frame


def _dedupe(frame):
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates("timestamp", keep="first")
    return frame.reset_index(drop=True)


def _years(frame):
    return frame["datetime"].dt.year.to_numpy()


class ParquetStore:
    def __init__(self, root, lock_timeout=300.0, lock_poll=0.5):
        self.root = Path(root)
        self.lock_timeout = lock_timeout
        self.lock_poll = lock_poll

    # ------------------------------------------------------------ layout
    def series_dir(self, exchange, symbol):
        return self.root / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def _year_files(self, exchange, symbol):
        directory = self.series_dir(exchange, symbol)
        if not directory.is_dir():
            return []
        return sorted(directory.glob("year=*/data.parquet"), key=lambda p: p.as_posix())

    @contextlib.contextmanager
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
                except OSError as exc:
                    if exc.errno not in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                        raise
                    if time.monotonic() >= deadline:
                        raise StoreError(
                            f"{exchange}/{symbol}: another writer holds the store lock after "
                            f"{self.lock_timeout:g}s ({path})") from None
                    time.sleep(self.lock_poll)
            yield
        finally:
            os.close(fd)

    def _clean_tmp(self, exchange, symbol):
        for tmp in self.series_dir(exchange, symbol).glob("year=*/data.parquet.tmp"):
            tmp.unlink()

    def _write_years(self, exchange, symbol, frame, years, prune):
        import pyarrow as pa
        import pyarrow.parquet as pq

        schema = _schema()
        directory = self.series_dir(exchange, symbol)
        frame_years = _years(frame)
        written = set()
        for year in sorted(set(int(y) for y in years)):
            part = frame[frame_years == year][COLUMNS]
            year_dir = directory / f"year={year}"
            year_dir.mkdir(parents=True, exist_ok=True)
            tmp = year_dir / "data.parquet.tmp"
            table = pa.Table.from_pandas(part, schema=schema, preserve_index=False)
            pq.write_table(table, tmp, compression="snappy")
            os.replace(tmp, year_dir / "data.parquet")
            written.add(year)
        if prune:
            for path in directory.glob("year=*/data.parquet"):
                year = int(path.parent.name.split("=", 1)[1])
                if year not in written:
                    path.unlink()
                    with contextlib.suppress(OSError):
                        path.parent.rmdir()

    # ------------------------------------------------------------ reads
    @staticmethod
    def _read_file(path, columns=None):
        import pyarrow.parquet as pq

        return pq.read_table(path, columns=columns).to_pandas()

    def load(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frames = [self._read_file(path) for path in files]
        frame = pd.concat(frames, ignore_index=True)[COLUMNS]
        return _dedupe(frame)

    def latest_date(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return None
        frame = self._read_file(files[-1], columns=["datetime"])
        if frame.empty:
            return None
        return frame["datetime"].max().date()

    def recent_dates(self, exchange, symbol, n):
        files = self._year_files(exchange, symbol)
        frames = []
        rows = 0
        for path in reversed(files):
            frame = self._read_file(path, columns=["datetime"])
            frames.append(frame)
            rows += len(frame)
            if rows >= n:
                break
        days = set()
        for frame in frames:
            days.update(stamp.date() for stamp in frame["datetime"].tolist())
        return sorted(days)[-n:] if n > 0 else []

    # ------------------------------------------------------------ writes
    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis, *,
                       asset_type, currency):
        """Newest-wins reconcile of served bars; returns (served bar count, revisions)."""
        served = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                            currency=currency, price_basis=price_basis,
                            volume_basis=volume_basis, splits=splits)
        if served.empty:
            return len(bars), []
        with self._lock(exchange, symbol):
            self._clean_tmp(exchange, symbol)
            stored = self.load(exchange, symbol)
            if stored.empty:
                merged = _dedupe(served)
                self._write_years(exchange, symbol, merged, _years(merged), prune=False)
                return len(bars), []
            position = {int(ts): i for i, ts in enumerate(stored["timestamp"].tolist())}
            stored_values = {c: stored[c].tolist() for c in AS_SERVED}
            served_values = {c: served[c].tolist() for c in AS_SERVED}
            served_ts = [int(ts) for ts in served["timestamp"].tolist()]
            served_days = served["datetime"].dt.strftime("%Y-%m-%d").tolist()
            revisions = []
            replaced = {}
            new_rows = []
            for j, ts in enumerate(served_ts):
                i = position.get(ts)
                if i is None:
                    new_rows.append(j)
                    continue
                changed = [c for c in AS_SERVED
                           if not _same(stored_values[c][i], served_values[c][j])]
                if changed:
                    replaced[i] = j
                    for c in changed:
                        revisions.append({"date": served_days[j], "column": c,
                                          "stored": float(stored_values[c][i]),
                                          "served": float(served_values[c][j])})
            if not replaced and not new_rows:
                return len(bars), revisions
            keep = [i for i in range(len(stored)) if i not in replaced]
            incoming = sorted(set(replaced.values()) | set(new_rows))
            merged = pd.concat([stored.iloc[keep], served.iloc[incoming]], ignore_index=True)
            merged = _dedupe(merged)
            touched = _years(served.iloc[incoming])
            self._write_years(exchange, symbol, merged, touched, prune=False)
            return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                    mode="append", *, asset_type, currency):
        """Append (stored rows win on equal timestamps) or overwrite; returns len(bars)."""
        incoming = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                              currency=currency, price_basis=price_basis,
                              volume_basis=volume_basis, splits=splits)
        if incoming.empty and mode == "append":
            return len(bars)
        with self._lock(exchange, symbol):
            self._clean_tmp(exchange, symbol)
            if mode == "overwrite":
                merged = _dedupe(incoming)
                self._write_years(exchange, symbol, merged, _years(merged), prune=True)
                return len(bars)
            stored = self.load(exchange, symbol)
            if stored.empty:
                merged = _dedupe(incoming)
            else:
                known = set(int(ts) for ts in stored["timestamp"].tolist())
                fresh = incoming[[int(ts) not in known for ts in incoming["timestamp"].tolist()]]
                merged = _dedupe(pd.concat([stored, fresh], ignore_index=True))
            self._write_years(exchange, symbol, merged, _years(incoming), prune=False)
            return len(bars)

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD"):
        """Replace the series with a Yahoo 7-column CSV; returns the CSV row count."""
        frame = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in frame.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        bars = [{"date": d, "open": o, "high": h, "low": lo, "close": c, "adjusted_close": ac,
                 "volume": v}
                for d, o, h, lo, c, ac, v in zip(frame["Date"].tolist(), frame["Open"].tolist(),
                                                  frame["High"].tolist(), frame["Low"].tolist(),
                                                  frame["Close"].tolist(),
                                                  frame["Adj Close"].tolist(),
                                                  frame["Volume"].tolist())]
        self.ingest_bars(exchange, symbol, bars, [], "split_adjusted", "raw", mode="overwrite",
                         asset_type=asset_type, currency=currency)
        return len(frame)

    def reapply_adjustment(self, exchange, symbol, splits):
        """Re-derive the mains of the whole series from *_raw; returns the row count."""
        with self._lock(exchange, symbol):
            self._clean_tmp(exchange, symbol)
            stored = self.load(exchange, symbol)
            if stored.empty:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(stored, splits)
            changed = False
            for column in DERIVED:
                before = stored[column].tolist()
                after = adjusted[column].tolist()
                if any(not _same(a, b) for a, b in zip(before, after)):
                    changed = True
                    break
            if changed:
                self._write_years(exchange, symbol, adjusted, _years(adjusted), prune=True)
            return len(stored)


def export_frame(store, exchange, symbol):
    """The 7-column seam frame of a stored series (every stored row, stored order)."""
    if not isinstance(store, ParquetStore):
        store = ParquetStore(store)
    stored = store.load(exchange, symbol)
    dates = stored["datetime"].dt.strftime("%Y-%m-%d")
    volume = stored["volume"].to_numpy(dtype="float64")
    if len(volume) > 0 and np.isfinite(volume).all() and (volume == np.floor(volume)).all():
        volume_column = volume.astype("int64")
    else:
        volume_column = volume
    frame = pd.DataFrame({
        "Date": dates.tolist(),
        "Open": stored["open"].to_numpy(dtype="float64"),
        "High": stored["high"].to_numpy(dtype="float64"),
        "Low": stored["low"].to_numpy(dtype="float64"),
        "Close": stored["close"].to_numpy(dtype="float64"),
        "Adj Close": stored["adjusted_close"].to_numpy(dtype="float64"),
        "Volume": volume_column,
    }, columns=EXPORT_COLUMNS)
    return frame.reset_index(drop=True)
