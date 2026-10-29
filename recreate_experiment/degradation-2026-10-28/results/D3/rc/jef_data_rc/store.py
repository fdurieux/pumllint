"""The partitioned Parquet market-data store."""
from __future__ import annotations

import contextlib
import fcntl
import os
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .adjust import adjust, session_days, split_factor

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
STRING_COLUMNS = ["symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis"]
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
DERIVED_COLUMNS = ["open", "high", "low", "close", "volume", "cumulative_split_factor"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]

SCHEMA = pa.schema([
    ("timestamp", pa.int64()),
    ("datetime", pa.timestamp("ms", tz="UTC")),
    ("open", pa.float64()), ("high", pa.float64()), ("low", pa.float64()),
    ("close", pa.float64()), ("volume", pa.float64()),
    ("symbol", pa.string()), ("exchange", pa.string()), ("asset_type", pa.string()),
    ("asset_subtype", pa.string()),
    ("adjustment_factor", pa.float64()),
    ("open_raw", pa.float64()), ("high_raw", pa.float64()), ("low_raw", pa.float64()),
    ("close_raw", pa.float64()), ("volume_raw", pa.float64()),
    ("adjusted_close", pa.float64()), ("cumulative_split_factor", pa.float64()),
    ("currency", pa.string()), ("price_basis", pa.string()),
])


class StoreError(RuntimeError):
    """A store operation that cannot proceed."""


def empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def _floats(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=np.float64)


def build_rows(dates, open_, high, low, close, adjusted_close, volume, *, symbol: str,
               exchange: str, asset_type: str, currency: str, price_basis: str,
               volume_basis: str, splits) -> pd.DataFrame:
    """Stored rows for served bars, in served order."""
    dates = list(dates)
    if not dates:
        return empty_frame()
    parsed = pd.to_datetime(pd.Series(dates, dtype=object), utc=True, errors="coerce")
    bad = [d for d, t in zip(dates, parsed) if pd.isna(t)]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    open_raw = _floats(open_)
    high_raw = _floats(high)
    low_raw = _floats(low)
    close_raw = _floats(close)
    served_volume = _floats(volume)
    adj = _floats(adjusted_close)
    stamps = parsed.astype("datetime64[ms, UTC]")
    frame = pd.DataFrame({
        "timestamp": (parsed.astype("int64") // 10**6).to_numpy(dtype=np.int64),
        "datetime": stamps.reset_index(drop=True),
    })
    if price_basis == "raw":
        if volume_basis == "split_adjusted":
            factor = split_factor(session_days(stamps), splits)
            with np.errstate(divide="ignore", invalid="ignore"):
                volume_raw = served_volume / factor
        elif volume_basis == "raw":
            volume_raw = served_volume
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        volume_raw = served_volume
    n = len(dates)
    frame["open"] = open_raw
    frame["high"] = high_raw
    frame["low"] = low_raw
    frame["close"] = close_raw
    frame["volume"] = volume_raw
    frame["symbol"] = [symbol] * n
    frame["exchange"] = [exchange] * n
    frame["asset_type"] = [asset_type] * n
    frame["asset_subtype"] = [""] * n
    with np.errstate(divide="ignore", invalid="ignore"):
        frame["adjustment_factor"] = adj / close_raw
    frame["open_raw"] = open_raw
    frame["high_raw"] = high_raw
    frame["low_raw"] = low_raw
    frame["close_raw"] = close_raw
    frame["volume_raw"] = volume_raw
    frame["adjusted_close"] = adj
    frame["cumulative_split_factor"] = np.ones(n, dtype=np.float64)
    frame["currency"] = [currency] * n
    frame["price_basis"] = [price_basis] * n
    if price_basis == "raw":
        frame = adjust(frame, splits)
    return frame[COLUMNS]


def bars_to_rows(bars, **labels) -> pd.DataFrame:
    return build_rows(
        [b.get("date") for b in bars],
        [b.get("open") for b in bars], [b.get("high") for b in bars],
        [b.get("low") for b in bars], [b.get("close") for b in bars],
        [b["adjusted_close"] if "adjusted_close" in b else b.get("close") for b in bars],
        [b.get("volume") for b in bars], **labels)


def _same(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
        return True
    return a == b


def _years(frame: pd.DataFrame) -> np.ndarray:
    return session_days(frame["datetime"]).astype("datetime64[Y]").astype(int) + 1970


def _table(frame: pd.DataFrame) -> pa.Table:
    arrays = []
    for field in SCHEMA:
        column = frame[field.name]
        if field.name == "datetime":
            arrays.append(pa.array(column.dt.tz_convert("UTC").astype("datetime64[ms, UTC]"),
                                   type=field.type))
        elif field.name in STRING_COLUMNS:
            arrays.append(pa.array([str(v) for v in column.tolist()], type=pa.string()))
        elif field.name == "timestamp":
            arrays.append(pa.array(column.to_numpy(dtype=np.int64), type=pa.int64()))
        else:
            arrays.append(pa.array(column.to_numpy(dtype=np.float64), type=pa.float64()))
    return pa.Table.from_arrays(arrays, schema=SCHEMA)


class ParquetStore:
    def __init__(self, root, lock_timeout: float = 300.0, poll: float = 0.5):
        self.root = Path(root)
        self.lock_timeout = lock_timeout
        self.poll = poll

    # ------------------------------------------------------------ layout
    def series_dir(self, exchange: str, symbol: str) -> Path:
        return self.root / "marketdata" / f"exchange={exchange}" / f"symbol={symbol}"

    def year_files(self, exchange: str, symbol: str) -> list:
        base = self.series_dir(exchange, symbol)
        if not base.is_dir():
            return []
        return sorted(base.glob("year=*/data.parquet"), key=lambda p: p.as_posix())

    @contextlib.contextmanager
    def _lock(self, exchange: str, symbol: str):
        base = self.series_dir(exchange, symbol)
        base.mkdir(parents=True, exist_ok=True)
        path = base / ".lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
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
                            f"{self.lock_timeout:g}s ({path})") from None
                    time.sleep(self.poll)
            yield
        finally:
            os.close(fd)

    def _clear_tmp(self, exchange: str, symbol: str) -> None:
        for leftover in self.series_dir(exchange, symbol).glob("year=*/data.parquet.tmp"):
            leftover.unlink()

    def _write_years(self, exchange: str, symbol: str, frame: pd.DataFrame, years,
                     prune: bool = False) -> None:
        base = self.series_dir(exchange, symbol)
        all_years = _years(frame) if len(frame) else np.array([], dtype=int)
        for year in sorted(set(int(y) for y in years)):
            part = frame[all_years == year]
            target = base / f"year={year}" / "data.parquet"
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name("data.parquet.tmp")
            pq.write_table(_table(part), tmp, compression="snappy")
            os.replace(tmp, target)
        if prune:
            keep = {int(y) for y in all_years}
            for path in self.year_files(exchange, symbol):
                year = int(path.parent.name.split("=", 1)[1])
                if year not in keep:
                    path.unlink()
                    with contextlib.suppress(OSError):
                        path.parent.rmdir()

    # ------------------------------------------------------------ reads
    def load(self, exchange: str, symbol: str) -> pd.DataFrame:
        files = self.year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frames = [pq.ParquetFile(p).read().to_pandas() for p in files]
        frame = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        frame = frame.sort_values("timestamp", kind="stable")
        frame = frame.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
        return frame[COLUMNS]

    def latest_date(self, exchange: str, symbol: str):
        files = self.year_files(exchange, symbol)
        if not files:
            return None
        frame = pq.ParquetFile(files[-1]).read(columns=["datetime"]).to_pandas()
        if not len(frame):
            return None
        day = session_days(frame["datetime"]).max()
        return date.fromisoformat(str(day))

    def recent_dates(self, exchange: str, symbol: str, n: int) -> list:
        days = []
        for path in reversed(self.year_files(exchange, symbol)):
            frame = pq.ParquetFile(path).read(columns=["datetime"]).to_pandas()
            days.extend(str(d) for d in session_days(frame["datetime"]))
            if len(days) >= n:
                break
        distinct = sorted(set(days))
        return [date.fromisoformat(d) for d in distinct[-n:]] if n > 0 else []

    # ------------------------------------------------------------ writes
    def reconcile_bars(self, exchange: str, symbol: str, bars, splits, price_basis: str,
                       volume_basis: str, *, asset_type: str, currency: str) -> tuple:
        served = bars_to_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                              currency=currency, price_basis=price_basis,
                              volume_basis=volume_basis, splits=splits)
        count = len(bars)
        if not len(served):
            return count, []
        with self._lock(exchange, symbol):
            self._clear_tmp(exchange, symbol)
            stored = self.load(exchange, symbol)
            if not len(stored):
                frame = served.sort_values("timestamp", kind="stable")
                frame = frame.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
                self._write_years(exchange, symbol, frame, _years(frame))
                return count, []
            position = {int(ts): i for i, ts in enumerate(stored["timestamp"].tolist())}
            served_days = [str(d) for d in session_days(served["datetime"])]
            revisions = []
            replace = {}
            new_rows = []
            for i in range(len(served)):
                ts = int(served["timestamp"].iloc[i])
                j = position.get(ts)
                if j is None:
                    new_rows.append(i)
                    continue
                changed = []
                for column in AS_SERVED:
                    old = float(stored[column].iloc[j])
                    new = float(served[column].iloc[i])
                    if not _same(old, new):
                        changed.append((column, old, new))
                if changed:
                    replace[j] = i
                    for column, old, new in changed:
                        revisions.append({"date": served_days[i], "column": column,
                                          "stored": old, "served": new})
            if not replace and not new_rows:
                return count, revisions
            keep = [j for j in range(len(stored)) if j not in replace]
            parts = [stored.iloc[keep]]
            touched = list(replace.values()) + new_rows
            parts.append(served.iloc[sorted(touched)])
            merged = pd.concat([p.astype(object) for p in parts], ignore_index=True)
            merged = merged.sort_values("timestamp", kind="stable").reset_index(drop=True)
            merged = _restore_types(merged)
            years = _years(served.iloc[sorted(touched)])
            self._write_years(exchange, symbol, merged, years)
            return count, revisions

    def ingest_bars(self, exchange: str, symbol: str, bars, splits, price_basis: str,
                    volume_basis: str, mode: str = "append", *, asset_type: str,
                    currency: str) -> int:
        incoming = bars_to_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                                currency=currency, price_basis=price_basis,
                                volume_basis=volume_basis, splits=splits)
        if not len(incoming):
            return len(bars)
        with self._lock(exchange, symbol):
            self._clear_tmp(exchange, symbol)
            if mode == "overwrite":
                frame = incoming.sort_values("timestamp", kind="stable")
                frame = frame.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
                self._write_years(exchange, symbol, frame, _years(frame), prune=True)
                return len(bars)
            stored = self.load(exchange, symbol)
            parts = [p.astype(object) for p in (stored, incoming) if len(p)]
            merged = pd.concat(parts, ignore_index=True)
            merged = merged.sort_values("timestamp", kind="stable")
            merged = merged.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
            merged = _restore_types(merged)
            self._write_years(exchange, symbol, merged, _years(incoming))
            return len(bars)

    def ingest_yahoo_csv(self, csv_path, exchange: str, symbol: str, asset_type: str,
                         currency: str = "USD") -> int:
        frame = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in frame.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        rows = build_rows(
            frame["Date"].tolist(), frame["Open"].tolist(), frame["High"].tolist(),
            frame["Low"].tolist(), frame["Close"].tolist(), frame["Adj Close"].tolist(),
            frame["Volume"].tolist(), symbol=symbol, exchange=exchange, asset_type=asset_type,
            currency=currency, price_basis="split_adjusted", volume_basis="raw", splits=[])
        if len(rows):
            rows = rows.sort_values("timestamp", kind="stable")
            rows = rows.drop_duplicates("timestamp", keep="first").reset_index(drop=True)
        with self._lock(exchange, symbol):
            self._clear_tmp(exchange, symbol)
            self._write_years(exchange, symbol, rows, _years(rows) if len(rows) else [], prune=True)
        return len(frame)

    def reapply_adjustment(self, exchange: str, symbol: str, splits) -> int:
        if not self.year_files(exchange, symbol):
            raise StoreError(f"nothing stored for {exchange}/{symbol}")
        with self._lock(exchange, symbol):
            self._clear_tmp(exchange, symbol)
            frame = self.load(exchange, symbol)
            if not len(frame):
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            new = adjust(frame, splits)
            if _changed(frame, new):
                self._write_years(exchange, symbol, new, _years(new), prune=True)
            return len(frame)


def _changed(old: pd.DataFrame, new: pd.DataFrame) -> bool:
    for column in DERIVED_COLUMNS:
        a = old[column].to_numpy(dtype=np.float64)
        b = new[column].to_numpy(dtype=np.float64)
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        if not bool(same.all()):
            return True
    return False


def _restore_types(frame: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"timestamp": frame["timestamp"].astype(np.int64)})
    out["datetime"] = pd.to_datetime(frame["datetime"], utc=True).astype("datetime64[ms, UTC]")
    for column in COLUMNS[2:]:
        if column in STRING_COLUMNS:
            out[column] = [str(v) for v in frame[column].tolist()]
        else:
            out[column] = frame[column].astype(np.float64)
    return out[COLUMNS]


SEAM_COLUMNS = YAHOO_COLUMNS


def seam_frame(stored: pd.DataFrame) -> pd.DataFrame:
    """The 7-column export projection of a stored series."""
    dates = stored["datetime"].dt.strftime("%Y-%m-%d")
    volume = stored["volume"].to_numpy(dtype=np.float64)
    if len(volume) and bool(np.isfinite(volume).all()) and bool((volume == np.floor(volume)).all()):
        volume_column = volume.astype(np.int32)
    else:
        volume_column = volume
    return pd.DataFrame({
        "Date": dates.reset_index(drop=True),
        "Open": stored["open"].to_numpy(dtype=np.float64),
        "High": stored["high"].to_numpy(dtype=np.float64),
        "Low": stored["low"].to_numpy(dtype=np.float64),
        "Close": stored["close"].to_numpy(dtype=np.float64),
        "Adj Close": stored["adjusted_close"].to_numpy(dtype=np.float64),
        "Volume": volume_column,
    })


def export_frame(store_root, exchange: str, symbol: str) -> pd.DataFrame:
    return seam_frame(ParquetStore(store_root).load(exchange, symbol))
