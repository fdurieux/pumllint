"""The partitioned Parquet market-data store."""
import contextlib
import fcntl
import math
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from .adjust import adjust, split_factors

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
STRING_COLUMNS = ["symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis"]
FLOAT_COLUMNS = [c for c in COLUMNS if c not in STRING_COLUMNS + ["timestamp", "datetime"]]
AS_SERVED = ["open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"]
DERIVED = ["open", "high", "low", "close", "volume", "cumulative_split_factor"]
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
LOCK_TIMEOUT = 300.0
LOCK_POLL = 0.5


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


def empty_frame():
    return pd.DataFrame(columns=COLUMNS)


def _num(value):
    if value is None:
        return float("nan")
    return float(value)


def _same(a, b):
    a = float(a)
    b = float(b)
    if math.isnan(a) and math.isnan(b):
        return True
    return a == b


def parse_dates(dates):
    """Bar date strings -> (timestamp seconds, datetime[ms, UTC]); refuses unparseable ones."""
    raw = pd.Series(list(dates), dtype=object)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(raw, errors="coerce", utc=True)
    bad = [raw.iloc[i] for i in range(len(raw)) if pd.isna(parsed.iloc[i])]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]!r}")
    micro = parsed.astype("datetime64[us, UTC]")
    timestamp = micro.astype("int64") // 10**6
    return timestamp.to_numpy(dtype="int64"), parsed.astype("datetime64[ms, UTC]")


def build_rows(bars, *, symbol, exchange, asset_type, currency, price_basis, volume_basis,
               splits=()):
    """Stored rows for served bars, in bar order."""
    splits = list(splits)
    timestamp, stamps = parse_dates([bar["date"] for bar in bars])
    open_raw = np.array([_num(b["open"]) for b in bars], dtype="float64")
    high_raw = np.array([_num(b["high"]) for b in bars], dtype="float64")
    low_raw = np.array([_num(b["low"]) for b in bars], dtype="float64")
    close_raw = np.array([_num(b["close"]) for b in bars], dtype="float64")
    served_volume = np.array([_num(b["volume"]) for b in bars], dtype="float64")
    adjusted_close = np.array(
        [_num(b["adjusted_close"]) if "adjusted_close" in b else _num(b["close"]) for b in bars],
        dtype="float64")
    days = stamps.dt.strftime("%Y-%m-%d").tolist()
    if price_basis == "raw":
        if volume_basis == "split_adjusted":
            volume_raw = served_volume / split_factors(days, splits)
        elif volume_basis == "raw":
            volume_raw = served_volume
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
    else:
        volume_raw = served_volume
    with np.errstate(divide="ignore", invalid="ignore"):
        adjustment_factor = adjusted_close / close_raw
    n = len(bars)
    frame = pd.DataFrame({
        "timestamp": timestamp,
        "datetime": stamps.reset_index(drop=True),
        "open": open_raw.copy(), "high": high_raw.copy(), "low": low_raw.copy(),
        "close": close_raw.copy(), "volume": volume_raw.copy(),
        "symbol": [symbol] * n, "exchange": [exchange] * n, "asset_type": [asset_type] * n,
        "asset_subtype": [""] * n,
        "adjustment_factor": adjustment_factor,
        "open_raw": open_raw, "high_raw": high_raw, "low_raw": low_raw, "close_raw": close_raw,
        "volume_raw": volume_raw, "adjusted_close": adjusted_close,
        "cumulative_split_factor": np.ones(n, dtype="float64"),
        "currency": [currency] * n, "price_basis": [price_basis] * n,
    }, columns=COLUMNS)
    if price_basis == "raw":
        frame = adjust(frame, splits)
    return frame


def seam_frame(frame):
    """The 7-column export projection of a stored series."""
    dates = frame["datetime"].dt.strftime("%Y-%m-%d")
    volume = frame["volume"].to_numpy(dtype="float64")
    if len(volume) and bool(np.isfinite(volume).all()) and bool((volume == np.floor(volume)).all()):
        volume = volume.astype("int64")
    return pd.DataFrame({
        "Date": [str(d) for d in dates.tolist()],
        "Open": frame["open"].to_numpy(dtype="float64"),
        "High": frame["high"].to_numpy(dtype="float64"),
        "Low": frame["low"].to_numpy(dtype="float64"),
        "Close": frame["close"].to_numpy(dtype="float64"),
        "Adj Close": frame["adjusted_close"].to_numpy(dtype="float64"),
        "Volume": volume,
    }, columns=YAHOO_COLUMNS)


def _sorted_unique(frame):
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates(subset="timestamp", keep="first")
    return frame.reset_index(drop=True)


def _years(frame):
    return frame["datetime"].dt.year.to_numpy()


class ParquetStore:
    def __init__(self, root, lock_timeout=LOCK_TIMEOUT):
        self.root = Path(root)
        self.lock_timeout = lock_timeout

    def series_dir(self, exchange, symbol):
        return self.root / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def year_files(self, exchange, symbol):
        directory = self.series_dir(exchange, symbol)
        if not directory.is_dir():
            return []
        out = []
        for name in sorted(os.listdir(directory)):
            path = directory / name / "data.parquet"
            if name.startswith("year=") and path.is_file():
                out.append(path)
        return out

    @contextlib.contextmanager
    def lock(self, exchange, symbol):
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
                except OSError:
                    if time.monotonic() >= deadline:
                        raise StoreError(
                            f"{exchange}/{symbol}: another writer holds the store lock after "
                            f"{self.lock_timeout:g}s ({path})") from None
                    time.sleep(LOCK_POLL)
            yield
        finally:
            os.close(fd)

    # ------------------------------------------------------------------ reads
    @staticmethod
    def _read(path):
        return pd.read_parquet(path, engine="pyarrow")

    def load(self, exchange, symbol):
        files = self.year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frame = pd.concat([self._read(p) for p in files], ignore_index=True)
        return _sorted_unique(frame)[COLUMNS]

    def export(self, exchange, symbol):
        return seam_frame(self.load(exchange, symbol))

    def latest_date(self, exchange, symbol):
        files = self.year_files(exchange, symbol)
        if not files:
            return None
        frame = self._read(files[-1])
        if frame.empty:
            return None
        return max(d.date() for d in frame["datetime"])

    def recent_dates(self, exchange, symbol, n):
        frames = []
        count = 0
        for path in reversed(self.year_files(exchange, symbol)):
            frame = self._read(path)
            frames.append(frame)
            count += len(frame)
            if count >= n:
                break
        if not frames:
            return []
        days = set()
        for frame in frames:
            days.update(frame["datetime"].dt.strftime("%Y-%m-%d").tolist())
        return sorted(days)[-n:] if n > 0 else []

    # ------------------------------------------------------------------ writes
    def _write_years(self, exchange, symbol, frame, years, prune=False):
        import pyarrow as pa
        import pyarrow.parquet as pq

        directory = self.series_dir(exchange, symbol)
        for name in os.listdir(directory):
            tmp = directory / name / "data.parquet.tmp"
            if name.startswith("year=") and tmp.exists():
                tmp.unlink()
        schema = _schema()
        all_years = _years(frame)
        for year in sorted(set(int(y) for y in years)):
            rows = frame[all_years == year][COLUMNS].reset_index(drop=True)
            year_dir = directory / f"year={year:04d}"
            year_dir.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(rows, schema=schema, preserve_index=False)
            tmp = year_dir / "data.parquet.tmp"
            pq.write_table(table, tmp, compression="snappy")
            os.replace(tmp, year_dir / "data.parquet")
        if prune:
            keep = {f"year={int(y):04d}" for y in set(all_years.tolist())}
            for name in sorted(os.listdir(directory)):
                if name.startswith("year=") and name not in keep:
                    stale = directory / name / "data.parquet"
                    if stale.exists():
                        stale.unlink()
                    with contextlib.suppress(OSError):
                        (directory / name).rmdir()

    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                       asset_type="stock", currency="USD"):
        """Newest-wins reconcile of served bars; returns (served bar count, revisions)."""
        if not bars:
            return 0, []
        served = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                            currency=currency, price_basis=price_basis,
                            volume_basis=volume_basis, splits=splits)
        with self.lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if stored.empty:
                merged = _sorted_unique(served)
                self._write_years(exchange, symbol, merged, set(_years(merged).tolist()))
                return len(bars), []
            position = {int(ts): i for i, ts in enumerate(stored["timestamp"].tolist())}
            served_days = served["datetime"].dt.strftime("%Y-%m-%d").tolist()
            revisions = []
            replaced = []
            fresh = []
            for j, ts in enumerate(served["timestamp"].tolist()):
                i = position.get(int(ts))
                if i is None:
                    fresh.append(j)
                    continue
                changed = False
                for column in AS_SERVED:
                    old = stored[column].iloc[i]
                    new = served[column].iloc[j]
                    if not _same(old, new):
                        changed = True
                        revisions.append({"date": served_days[j], "column": column,
                                          "stored": float(old), "served": float(new)})
                if changed:
                    replaced.append((i, j))
            if not replaced and not fresh:
                return len(bars), revisions
            keep = stored.drop(index=[i for i, _ in replaced])
            incoming = served.iloc[[j for _, j in replaced] + fresh]
            merged = _sorted_unique(pd.concat([keep, incoming], ignore_index=True))
            touched = set(_years(incoming).tolist())
            self._write_years(exchange, symbol, merged, touched)
            return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis,
                    mode="append", asset_type="stock", currency="USD"):
        """Append (stored rows win) or overwrite a series; returns the incoming bar count."""
        rows = build_rows(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                          currency=currency, price_basis=price_basis,
                          volume_basis=volume_basis, splits=splits) if bars else None
        if mode == "overwrite":
            frame = _sorted_unique(rows) if rows is not None else None
            with self.lock(exchange, symbol):
                if frame is not None and len(frame):
                    self._write_years(exchange, symbol, frame, set(_years(frame).tolist()),
                                      prune=True)
                else:
                    self._prune_all(exchange, symbol)
            return len(bars)
        if mode != "append":
            raise ValueError(f"unknown ingest mode {mode!r}")
        if rows is None:
            return 0
        with self.lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            merged = _sorted_unique(pd.concat([stored, rows], ignore_index=True)) \
                if len(stored) else _sorted_unique(rows)
            self._write_years(exchange, symbol, merged, set(_years(rows).tolist()))
        return len(bars)

    def _prune_all(self, exchange, symbol):
        for path in self.year_files(exchange, symbol):
            path.unlink()
            with contextlib.suppress(OSError):
                path.parent.rmdir()

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD"):
        """Overwrite the series with a Yahoo 7-column CSV; returns the CSV row count."""
        frame = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in frame.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        bars = []
        for record in frame[YAHOO_COLUMNS].itertuples(index=False, name=None):
            date, op, hi, lo, cl, adj, vol = record
            bars.append({"date": date, "open": op, "high": hi, "low": lo, "close": cl,
                         "adjusted_close": adj, "volume": vol})
        self.ingest_bars(exchange, symbol, bars, [], "split_adjusted", "raw", mode="overwrite",
                         asset_type=asset_type, currency=currency)
        return len(frame)

    def reapply_adjustment(self, exchange, symbol, splits):
        """Re-derive the main columns of a raw series; returns its row count."""
        if not self.year_files(exchange, symbol):
            raise StoreError(f"nothing stored for {exchange}/{symbol}")
        with self.lock(exchange, symbol):
            frame = self.load(exchange, symbol)
            if frame.empty:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(frame, splits)
            moved = False
            for column in DERIVED:
                a = frame[column].to_numpy(dtype="float64")
                b = adjusted[column].to_numpy(dtype="float64")
                if not np.array_equal(a, b, equal_nan=True):
                    moved = True
                    break
            if moved:
                self._write_years(exchange, symbol, adjusted, set(_years(adjusted).tolist()),
                                  prune=True)
            return len(frame)
