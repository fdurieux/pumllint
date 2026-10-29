"""The partitioned Parquet market-data store and the export projection."""
from __future__ import annotations

import datetime as _dt
import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from .adjust import adjust, cumulative_factor

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume",
           "symbol", "exchange", "asset_type", "asset_subtype", "adjustment_factor",
           "open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
FLOAT_COLUMNS = ["open", "high", "low", "close", "volume", "adjustment_factor",
                 "open_raw", "high_raw", "low_raw", "close_raw", "volume_raw",
                 "adjusted_close", "cumulative_split_factor"]
STRING_COLUMNS = ["symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis"]
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
EXPORT_COLUMNS = YAHOO_COLUMNS


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


def empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def _floats(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=np.float64)


def _same(a: float, b: float) -> bool:
    if a != a and b != b:
        return True
    return a == b


def bars_to_frame(bars, *, exchange, symbol, asset_type, currency, price_basis,
                  volume_basis, splits) -> pd.DataFrame:
    """Build stored rows (the 21 columns) from provider bars."""
    dates = pd.Series([b["date"] for b in bars], dtype=object)
    parsed = pd.to_datetime(dates, utc=True, errors="coerce")
    bad = [v for v, ok in zip(dates.tolist(), parsed.notna().tolist()) if not ok]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    frame = pd.DataFrame(index=range(len(bars)))
    frame["timestamp"] = (parsed.astype("int64") // 10**6).to_numpy(dtype=np.int64)
    frame["datetime"] = parsed.astype("datetime64[ms, UTC]")
    open_raw = _floats([b["open"] for b in bars])
    high_raw = _floats([b["high"] for b in bars])
    low_raw = _floats([b["low"] for b in bars])
    close_raw = _floats([b["close"] for b in bars])
    served_volume = _floats([b["volume"] for b in bars])
    adjusted_close = _floats([b["adjusted_close"] if "adjusted_close" in b else b["close"] for b in bars])
    if price_basis == "raw":
        if volume_basis == "split_adjusted":
            days = frame["datetime"].dt.strftime("%Y-%m-%d").tolist()
            factor = cumulative_factor(days, splits)
            with np.errstate(divide="ignore", invalid="ignore"):
                volume_raw = served_volume / factor
        elif volume_basis == "raw":
            volume_raw = served_volume
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        volume_raw = served_volume
    frame["open"] = open_raw
    frame["high"] = high_raw
    frame["low"] = low_raw
    frame["close"] = close_raw
    frame["volume"] = volume_raw
    frame["symbol"] = symbol
    frame["exchange"] = exchange
    frame["asset_type"] = asset_type
    frame["asset_subtype"] = ""
    with np.errstate(divide="ignore", invalid="ignore"):
        frame["adjustment_factor"] = adjusted_close / close_raw
    frame["open_raw"] = open_raw
    frame["high_raw"] = high_raw
    frame["low_raw"] = low_raw
    frame["close_raw"] = close_raw
    frame["volume_raw"] = volume_raw
    frame["adjusted_close"] = adjusted_close
    frame["cumulative_split_factor"] = np.ones(len(bars), dtype=np.float64)
    frame["currency"] = currency
    frame["price_basis"] = price_basis
    frame = frame[COLUMNS]
    if price_basis == "raw":
        frame = adjust(frame, splits)
    return frame


def _sorted_unique(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates(subset="timestamp", keep="first")
    return frame.reset_index(drop=True)


def _years(frame: pd.DataFrame) -> np.ndarray:
    return frame["datetime"].dt.year.to_numpy()


class ParquetStore:
    lock_timeout = 300.0
    lock_poll = 0.5

    def __init__(self, root):
        self.root = Path(root)

    # ------------------------------------------------------------ layout
    def series_dir(self, exchange: str, symbol: str) -> Path:
        return self.root / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def year_files(self, exchange: str, symbol: str) -> list:
        directory = self.series_dir(exchange, symbol)
        if not directory.is_dir():
            return []
        return sorted(directory.glob("year=*/data.parquet"))

    @contextmanager
    def lock(self, exchange: str, symbol: str):
        directory = self.series_dir(exchange, symbol)
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / ".lock"
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StoreError(
                            f"{exchange}/{symbol}: another writer holds the store lock after "
                            f"{self.lock_timeout:g}s ({lock_path})") from None
                    time.sleep(self.lock_poll)
            yield
        finally:
            os.close(fd)

    # ------------------------------------------------------------ reads
    @staticmethod
    def _read_file(path: Path) -> pd.DataFrame:
        import pyarrow.parquet as pq

        return pq.read_table(path).to_pandas()

    def load(self, exchange: str, symbol: str) -> pd.DataFrame:
        files = self.year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frames = [self._read_file(p) for p in files]
        frame = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        return _sorted_unique(frame[COLUMNS])

    def latest_date(self, exchange: str, symbol: str):
        files = self.year_files(exchange, symbol)
        if not files:
            return None
        frame = self._read_file(files[-1])
        if len(frame) == 0:
            return None
        return max(ts.date() for ts in frame["datetime"])

    def recent_dates(self, exchange: str, symbol: str, n: int) -> list:
        files = self.year_files(exchange, symbol)
        frames = []
        rows = 0
        for path in reversed(files):
            frame = self._read_file(path)
            frames.append(frame)
            rows += len(frame)
            if rows >= n:
                break
        days = sorted({ts.date() for frame in frames for ts in frame["datetime"]})
        return days[-n:] if n > 0 else []

    # ------------------------------------------------------------ writes
    def _clear_tmp(self, exchange: str, symbol: str) -> None:
        for path in self.series_dir(exchange, symbol).glob("year=*/data.parquet.tmp"):
            path.unlink()

    def _write_years(self, exchange: str, symbol: str, frame: pd.DataFrame, years,
                     prune: bool = False) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        self._clear_tmp(exchange, symbol)
        schema = _schema()
        frame_years = _years(frame)
        for year in sorted({int(y) for y in years}):
            part = frame[frame_years == year][COLUMNS].reset_index(drop=True)
            directory = self.series_dir(exchange, symbol) / f"year={year:04d}"
            directory.mkdir(parents=True, exist_ok=True)
            tmp = directory / "data.parquet.tmp"
            table = pa.Table.from_pandas(part, schema=schema, preserve_index=False)
            pq.write_table(table, tmp, compression="snappy")
            os.replace(tmp, directory / "data.parquet")
        if prune:
            keep = {int(y) for y in frame_years}
            for path in self.year_files(exchange, symbol):
                year = int(path.parent.name.split("=", 1)[1])
                if year not in keep:
                    path.unlink()

    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                       *, asset_type, currency) -> tuple:
        if not bars:
            return 0, []
        served = bars_to_frame(bars, exchange=exchange, symbol=symbol, asset_type=asset_type,
                               currency=currency, price_basis=price_basis,
                               volume_basis=volume_basis, splits=splits)
        with self.lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if len(stored) == 0:
                served = _sorted_unique(served)
                self._write_years(exchange, symbol, served, set(_years(served)))
                return len(bars), []
            position = {int(ts): i for i, ts in enumerate(stored["timestamp"].tolist())}
            stored_values = {c: stored[c].to_numpy(dtype=np.float64) for c in AS_SERVED}
            served_values = {c: served[c].to_numpy(dtype=np.float64) for c in AS_SERVED}
            served_days = served["datetime"].dt.strftime("%Y-%m-%d").tolist()
            revisions = []
            replaced = {}
            fresh = []
            for i, ts in enumerate(served["timestamp"].tolist()):
                j = position.get(int(ts))
                if j is None:
                    fresh.append(i)
                    continue
                changed = [c for c in AS_SERVED
                           if not _same(stored_values[c][j], served_values[c][i])]
                if changed:
                    replaced[j] = i
                    for c in changed:
                        revisions.append({"date": served_days[i], "column": c,
                                          "stored": float(stored_values[c][j]),
                                          "served": float(served_values[c][i])})
            if not replaced and not fresh:
                return len(bars), revisions
            incoming = served.iloc[sorted(replaced.values()) + fresh]
            kept = stored.drop(index=list(replaced))
            combined = _sorted_unique(pd.concat([kept, incoming], ignore_index=True))
            touched = {int(y) for y in _years(incoming)}
            self._write_years(exchange, symbol, combined, touched)
            return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                    mode: str = "append", *, asset_type, currency) -> int:
        if mode != "append":
            raise StoreError(f"unknown ingest mode {mode!r}")
        if not bars:
            return 0
        incoming = bars_to_frame(bars, exchange=exchange, symbol=symbol, asset_type=asset_type,
                                 currency=currency, price_basis=price_basis,
                                 volume_basis=volume_basis, splits=splits)
        with self.lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if len(stored) == 0:
                combined = _sorted_unique(incoming)
            else:
                combined = _sorted_unique(pd.concat([stored, incoming], ignore_index=True))
            self._write_years(exchange, symbol, combined, set(_years(incoming)))
        return len(bars)

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD") -> int:
        data = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in data.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        bars = [{"date": d, "open": o, "high": h, "low": lo, "close": c,
                 "adjusted_close": a, "volume": v}
                for d, o, h, lo, c, a, v in zip(data["Date"].tolist(), data["Open"].tolist(),
                                                data["High"].tolist(), data["Low"].tolist(),
                                                data["Close"].tolist(), data["Adj Close"].tolist(),
                                                data["Volume"].tolist())]
        frame = bars_to_frame(bars, exchange=exchange, symbol=symbol, asset_type=asset_type,
                              currency=currency, price_basis="split_adjusted",
                              volume_basis="raw", splits=[])
        frame = _sorted_unique(frame)
        with self.lock(exchange, symbol):
            self._write_years(exchange, symbol, frame, set(_years(frame)), prune=True)
        return len(data)

    def reapply_adjustment(self, exchange, symbol, splits) -> int:
        with self.lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if len(stored) == 0:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(stored, splits)
            changed = False
            for column in COLUMNS:
                before = stored[column]
                after = adjusted[column]
                if column in FLOAT_COLUMNS:
                    a = before.to_numpy(dtype=np.float64)
                    b = after.to_numpy(dtype=np.float64)
                    if not np.array_equal(a, b, equal_nan=True):
                        changed = True
                        break
                elif not before.equals(after):
                    changed = True
                    break
            if changed:
                self._write_years(exchange, symbol, adjusted, set(_years(adjusted)), prune=True)
            return len(adjusted)


def export_frame(store: ParquetStore, exchange: str, symbol: str) -> pd.DataFrame:
    frame = store.load(exchange, symbol)
    out = pd.DataFrame({"Date": frame["datetime"].dt.strftime("%Y-%m-%d")})
    out["Open"] = frame["open"].astype("float64")
    out["High"] = frame["high"].astype("float64")
    out["Low"] = frame["low"].astype("float64")
    out["Close"] = frame["close"].astype("float64")
    out["Adj Close"] = frame["adjusted_close"].astype("float64")
    volume = frame["volume"].to_numpy(dtype=np.float64)
    if len(volume) > 0 and bool(np.all(np.isfinite(volume))) and bool(np.all(volume == np.floor(volume))):
        out["Volume"] = volume.astype(np.int64)
    else:
        out["Volume"] = volume
    return out.reset_index(drop=True)
