"""The partitioned Parquet market-data store: layout, locking, read and write semantics."""
import fcntl
import math
import os
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from .adjust import adjust, factors

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
STRING_COLUMNS = ["symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis"]
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


class StoreError(RuntimeError):
    """A store operation that cannot proceed."""


def _schema():
    import pyarrow as pa

    fields = []
    for column in COLUMNS:
        if column == "timestamp":
            fields.append((column, pa.int64()))
        elif column == "datetime":
            fields.append((column, pa.timestamp("ms", tz="UTC")))
        elif column in STRING_COLUMNS:
            fields.append((column, pa.string()))
        else:
            fields.append((column, pa.float64()))
    return pa.schema(fields)


def _number(value):
    if value is None:
        return math.nan
    return float(value)


def _same(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return a == b


def empty_frame():
    return pd.DataFrame(columns=COLUMNS)


class ParquetStore:
    """One store root's market data, one Parquet file per series and UTC year."""

    def __init__(self, root, lock_timeout=300.0, poll=0.5):
        self.root = str(root)
        self.lock_timeout = lock_timeout
        self.poll = poll

    # ---------------------------------------------------------------- layout
    def series_dir(self, exchange, symbol):
        return Path(self.root) / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def _year_files(self, exchange, symbol):
        return sorted(self.series_dir(exchange, symbol).glob("year=*/data.parquet"),
                      key=lambda path: str(path))

    @contextmanager
    def _locked(self, exchange, symbol):
        directory = self.series_dir(exchange, symbol)
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / ".lock"
        handle = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + self.lock_timeout
        try:
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StoreError(
                            f"{exchange}/{symbol}: another writer holds the store lock after "
                            f"{self.lock_timeout:g}s ({lock_path})") from None
                    time.sleep(self.poll)
            yield
        finally:
            os.close(handle)

    # ---------------------------------------------------------------- reads
    @staticmethod
    def _read_file(path):
        import pyarrow.parquet as pq

        return pq.ParquetFile(path).read().to_pandas()

    def load(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frames = [self._read_file(path) for path in files]
        frame = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
        frame = frame.sort_values("timestamp", kind="stable")
        frame = frame.drop_duplicates(subset="timestamp", keep="first")
        return frame.reset_index(drop=True)[COLUMNS]

    def latest_date(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return None
        frame = self._read_file(files[-1])
        if frame.empty:
            return None
        return max(frame["datetime"].dt.date)

    def recent_dates(self, exchange, symbol, n):
        rows = []
        for path in reversed(self._year_files(exchange, symbol)):
            frame = self._read_file(path)
            rows.extend(frame["datetime"].dt.date)
            if len(rows) >= n:
                break
        newest = sorted(set(rows), reverse=True)[:n]
        return sorted(newest)

    # ---------------------------------------------------------------- rows
    def build_rows(self, bars, exchange, symbol, asset_type, currency, price_basis,
                   volume_basis, splits=()):
        """Stored rows for served bars (basis-resolved, raw-ized, adjusted, labelled)."""
        splits = list(splits)
        count = len(bars)
        texts = [bar["date"] for bar in bars]
        parsed = pd.to_datetime(pd.Series(texts, dtype=object), utc=True, errors="coerce")
        bad = [text for text, value in zip(texts, parsed) if pd.isna(value)]
        if bad:
            raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
        parsed = parsed.dt.as_unit("us")
        frame = pd.DataFrame(index=pd.RangeIndex(count))
        frame["timestamp"] = (parsed.astype("int64") // 10 ** 6).astype("int64")
        frame["datetime"] = parsed.dt.as_unit("ms")
        served = {key: np.array([_number(bar.get(key)) for bar in bars], dtype="float64")
                  for key in ("open", "high", "low", "close", "volume")}
        adjusted_close = np.array(
            [_number(bar["adjusted_close"]) if "adjusted_close" in bar else _number(bar.get("close"))
             for bar in bars], dtype="float64")
        for key in ("open", "high", "low", "close"):
            frame[f"{key}_raw"] = served[key]
        if price_basis == "raw":
            if volume_basis == "split_adjusted":
                factor = factors(list(frame["datetime"].dt.date), splits)
                frame["volume_raw"] = served["volume"] / factor
            elif volume_basis == "raw":
                frame["volume_raw"] = served["volume"]
            else:
                raise StoreError(f"unknown volume_basis {volume_basis!r}")
        else:
            frame["volume_raw"] = served["volume"]
        frame["adjusted_close"] = adjusted_close
        with np.errstate(divide="ignore", invalid="ignore"):
            frame["adjustment_factor"] = adjusted_close / served["close"]
        labels = {"symbol": symbol, "exchange": exchange, "asset_type": asset_type,
                  "asset_subtype": "", "currency": currency, "price_basis": price_basis}
        for column, value in labels.items():
            frame[column] = pd.Series([value] * count, index=frame.index, dtype="str")
        if price_basis == "raw":
            for column in ("open", "high", "low", "close", "volume", "cumulative_split_factor"):
                frame[column] = np.nan
            frame = adjust(frame, splits)
        else:
            frame["open"] = frame["open_raw"]
            frame["high"] = frame["high_raw"]
            frame["low"] = frame["low_raw"]
            frame["close"] = frame["close_raw"]
            frame["volume"] = frame["volume_raw"]
            frame["cumulative_split_factor"] = 1.0
        return frame[COLUMNS]

    # ---------------------------------------------------------------- writes
    def _write_years(self, exchange, symbol, frame, years, prune):
        import pyarrow as pa
        import pyarrow.parquet as pq

        directory = self.series_dir(exchange, symbol)
        for leftover in directory.glob("year=*/data.parquet.tmp"):
            leftover.unlink()
        schema = _schema()
        row_years = frame["datetime"].dt.year if len(frame) else pd.Series([], dtype="int64")
        for year in sorted(years):
            rows = frame[(row_years == year).to_numpy()].reset_index(drop=True)
            year_dir = directory / f"year={year:04d}"
            year_dir.mkdir(parents=True, exist_ok=True)
            tmp = year_dir / "data.parquet.tmp"
            table = pa.Table.from_pandas(rows[COLUMNS], schema=schema, preserve_index=False)
            pq.write_table(table, tmp, compression="snappy")
            os.replace(tmp, year_dir / "data.parquet")
        if prune:
            keep = {f"year={year:04d}" for year in years}
            for path in directory.glob("year=*/data.parquet"):
                if path.parent.name not in keep:
                    path.unlink()

    @staticmethod
    def _years(frame):
        if not len(frame):
            return set()
        return {int(year) for year in frame["datetime"].dt.year}

    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                       asset_type="stock", currency="USD"):
        """Newest-wins merge of served bars; returns (served bar count, revisions)."""
        incoming = self.build_rows(bars, exchange, symbol, asset_type, currency, price_basis,
                                   volume_basis, splits)
        with self._locked(exchange, symbol):
            existing = self.load(exchange, symbol)
            if existing.empty:
                if len(incoming):
                    self._write_years(exchange, symbol, incoming, self._years(incoming),
                                      prune=False)
                return len(bars), []
            position = {int(ts): i for i, ts in enumerate(existing["timestamp"].tolist())}
            stored_values = {column: existing[column].tolist() for column in AS_SERVED}
            served_values = {column: incoming[column].tolist() for column in AS_SERVED}
            served_days = [day.isoformat() for day in incoming["datetime"].dt.date]
            revisions = []
            replaced = []
            taken = []
            for j, ts in enumerate(incoming["timestamp"].tolist()):
                i = position.get(int(ts))
                if i is None:
                    taken.append(j)
                    continue
                changed = False
                for column in AS_SERVED:
                    stored = stored_values[column][i]
                    served = served_values[column][j]
                    if not _same(stored, served):
                        changed = True
                        revisions.append({"date": served_days[j], "column": column,
                                          "stored": float(stored), "served": float(served)})
                if changed:
                    replaced.append(i)
                    taken.append(j)
            if not taken:
                return len(bars), revisions
            chosen = incoming.iloc[taken]
            kept = existing.drop(index=replaced)
            merged = pd.concat([kept, chosen], ignore_index=True)
            merged = merged.sort_values("timestamp", kind="stable").reset_index(drop=True)
            self._write_years(exchange, symbol, merged, self._years(chosen), prune=False)
            return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                    mode="append", asset_type="stock", currency="USD"):
        """Append (existing rows win) or overwrite (incoming replaces the series)."""
        incoming = self.build_rows(bars, exchange, symbol, asset_type, currency, price_basis,
                                   volume_basis, splits)
        if mode == "overwrite":
            incoming = incoming.sort_values("timestamp", kind="stable")
            incoming = incoming.drop_duplicates(subset="timestamp", keep="first")
            incoming = incoming.reset_index(drop=True)
            with self._locked(exchange, symbol):
                self._write_years(exchange, symbol, incoming, self._years(incoming), prune=True)
            return len(bars)
        with self._locked(exchange, symbol):
            existing = self.load(exchange, symbol)
            if existing.empty:
                merged = incoming
            else:
                merged = pd.concat([existing, incoming], ignore_index=True)
            merged = merged.drop_duplicates(subset="timestamp", keep="first")
            merged = merged.sort_values("timestamp", kind="stable").reset_index(drop=True)
            if len(incoming):
                self._write_years(exchange, symbol, merged, self._years(incoming), prune=False)
        return len(bars)

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD"):
        """Overwrite exchange/symbol with a Yahoo 7-column CSV; returns the CSV row count."""
        frame = pd.read_csv(csv_path)
        missing = [column for column in YAHOO_COLUMNS if column not in frame.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        bars = [{"date": date, "open": o, "high": h, "low": low, "close": c,
                 "adjusted_close": adj, "volume": v}
                for date, o, h, low, c, adj, v in zip(
                    frame["Date"].tolist(), frame["Open"].tolist(), frame["High"].tolist(),
                    frame["Low"].tolist(), frame["Close"].tolist(), frame["Adj Close"].tolist(),
                    frame["Volume"].tolist())]
        self.ingest_bars(exchange, symbol, bars, [], "split_adjusted", "raw", mode="overwrite",
                         asset_type=asset_type, currency=currency)
        return len(frame)

    def reapply_adjustment(self, exchange, symbol, splits):
        """Re-derive the mains of a raw series from its raws; rewrite only on change."""
        with self._locked(exchange, symbol):
            frame = self.load(exchange, symbol)
            if frame.empty:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(frame, list(splits))
            if not adjusted.equals(frame):
                self._write_years(exchange, symbol, adjusted, self._years(adjusted), prune=True)
            return len(frame)


def seam_frame(frame):
    """The 7-column export projection of a stored series."""
    dates = frame["datetime"].dt.strftime("%Y-%m-%d")
    volume = frame["volume"].astype("float64")
    values = volume.to_numpy()
    if len(values) and np.isfinite(values).all() and (np.floor(values) == values).all():
        volume = volume.astype("int64")
    out = pd.DataFrame({
        "Date": dates,
        "Open": frame["open"].astype("float64"),
        "High": frame["high"].astype("float64"),
        "Low": frame["low"].astype("float64"),
        "Close": frame["close"].astype("float64"),
        "Adj Close": frame["adjusted_close"].astype("float64"),
        "Volume": volume,
    })
    return out.reset_index(drop=True)
