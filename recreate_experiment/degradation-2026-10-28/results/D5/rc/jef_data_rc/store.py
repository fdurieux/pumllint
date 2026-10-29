"""The partitioned Parquet market-data store and the seam-frame export."""
from __future__ import annotations

import fcntl
import os
import time
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from .adjust import adjust, split_factors

COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol",
           "exchange", "asset_type", "asset_subtype", "adjustment_factor", "open_raw",
           "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close",
           "cumulative_split_factor", "currency", "price_basis"]
STRING_COLUMNS = ("symbol", "exchange", "asset_type", "asset_subtype", "currency",
                  "price_basis")
COMPARE_COLUMNS = ("open_raw", "high_raw", "low_raw", "close_raw", "volume_raw",
                   "adjusted_close")
DERIVED_COLUMNS = ("open", "high", "low", "close", "volume", "cumulative_split_factor")
YAHOO_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
SEAM_COLUMNS = YAHOO_COLUMNS
LOCK_TIMEOUT = 300.0
LOCK_POLL = 0.5


class StoreError(RuntimeError):
    """A store operation that cannot proceed."""


def resolve_price_basis(provider: str, asset_type: str) -> str:
    """Basis from the provider and the declared asset_type, never the suffix."""
    if provider == "eodhd":
        return "split_adjusted" if asset_type == "crypto" else "raw"
    return "split_adjusted"


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
    return np.array([np.nan if v is None else float(v) for v in values], dtype=np.float64)


def _parse_dates(values) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(pd.Series(values, dtype=object), utc=True, errors="coerce")


def bars_to_frame(bars, *, symbol, exchange, asset_type, currency, price_basis,
                  volume_basis, splits) -> pd.DataFrame:
    """One stored row per bar, every cell derived per the basis rules."""
    bars = list(bars)
    dates = [bar["date"] for bar in bars]
    parsed = _parse_dates(dates)
    bad = [value for value, stamp in zip(dates, parsed.tolist()) if pd.isna(stamp)]
    if bad:
        raise StoreError(f"unparseable dates cannot be stored: {bad[:5]}")
    parsed = parsed.astype("datetime64[us, UTC]")
    timestamp = parsed.astype("int64").to_numpy(dtype=np.int64) // 10 ** 6
    stamp_ms = parsed.astype("datetime64[ms, UTC]").reset_index(drop=True)

    open_raw = _floats(bar["open"] for bar in bars)
    high_raw = _floats(bar["high"] for bar in bars)
    low_raw = _floats(bar["low"] for bar in bars)
    close_raw = _floats(bar["close"] for bar in bars)
    served_volume = _floats(bar["volume"] for bar in bars)
    adjusted_close = _floats(bar["adjusted_close"] if "adjusted_close" in bar else bar["close"]
                             for bar in bars)
    with np.errstate(divide="ignore", invalid="ignore"):
        adjustment_factor = adjusted_close / close_raw

    n = len(bars)
    frame = pd.DataFrame({
        "timestamp": pd.Series(timestamp, dtype="int64"),
        "datetime": stamp_ms,
        "open": open_raw.copy(), "high": high_raw.copy(), "low": low_raw.copy(),
        "close": close_raw.copy(), "volume": served_volume.copy(),
        "symbol": [symbol] * n, "exchange": [exchange] * n,
        "asset_type": [asset_type] * n, "asset_subtype": [""] * n,
        "adjustment_factor": adjustment_factor,
        "open_raw": open_raw, "high_raw": high_raw, "low_raw": low_raw,
        "close_raw": close_raw, "volume_raw": served_volume.copy(),
        "adjusted_close": adjusted_close,
        "cumulative_split_factor": np.ones(n, dtype=np.float64),
        "currency": [currency] * n, "price_basis": [price_basis] * n,
    }, columns=COLUMNS)
    if price_basis == "raw":
        if volume_basis == "split_adjusted":
            days = stamp_ms.dt.tz_localize(None).to_numpy().astype("datetime64[D]")
            factor = split_factors(days, splits)
            frame["volume_raw"] = served_volume / factor
        elif volume_basis == "raw":
            frame["volume_raw"] = served_volume
        else:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
        frame = adjust(frame, splits)
    return frame


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values("timestamp", kind="stable")
    frame = frame.drop_duplicates("timestamp", keep="first")
    return frame.reset_index(drop=True)


def _same(a, b) -> bool:
    a = float(a)
    b = float(b)
    return a == b or (a != a and b != b)


def seam_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """The 7-column EOD projection of a stored series (no load policy)."""
    dates = frame["datetime"].dt.strftime("%Y-%m-%d")
    volume = frame["volume"].to_numpy(dtype=np.float64)
    if len(volume) and np.isfinite(volume).all() and (np.floor(volume) == volume).all():
        volume = volume.astype(np.int64)
    return pd.DataFrame({
        "Date": dates.reset_index(drop=True),
        "Open": frame["open"].to_numpy(dtype=np.float64),
        "High": frame["high"].to_numpy(dtype=np.float64),
        "Low": frame["low"].to_numpy(dtype=np.float64),
        "Close": frame["close"].to_numpy(dtype=np.float64),
        "Adj Close": frame["adjusted_close"].to_numpy(dtype=np.float64),
        "Volume": volume,
    }, columns=SEAM_COLUMNS)


class ParquetStore:
    def __init__(self, root, lock_timeout: float = LOCK_TIMEOUT):
        self.root = str(root)
        self.lock_timeout = lock_timeout

    # ------------------------------------------------------------ layout
    def series_dir(self, exchange, symbol) -> Path:
        return Path(self.root) / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def _year_files(self, exchange, symbol) -> list:
        directory = self.series_dir(exchange, symbol)
        if not directory.is_dir():
            return []
        return sorted(directory.glob("year=*/data.parquet"), key=lambda p: str(p))

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

    # ------------------------------------------------------------ reads
    @staticmethod
    def _read_file(path) -> pd.DataFrame:
        import pyarrow.parquet as pq

        return pq.ParquetFile(str(path)).read().to_pandas()

    def load(self, exchange, symbol) -> pd.DataFrame:
        files = self._year_files(exchange, symbol)
        if not files:
            return empty_frame()
        frame = pd.concat([self._read_file(p) for p in files], ignore_index=True)
        return _normalise(frame)[COLUMNS]

    def has_rows(self, exchange, symbol) -> bool:
        return bool(self._year_files(exchange, symbol))

    def latest_date(self, exchange, symbol):
        files = self._year_files(exchange, symbol)
        if not files:
            return None
        import pyarrow.parquet as pq

        stamps = pq.ParquetFile(str(files[-1])).read(columns=["datetime"]).to_pandas()["datetime"]
        if stamps.empty:
            return None
        return stamps.max().tz_convert("UTC").date()

    def recent_dates(self, exchange, symbol, n) -> list:
        import pyarrow.parquet as pq

        days = []
        for path in reversed(self._year_files(exchange, symbol)):
            stamps = pq.ParquetFile(str(path)).read(columns=["datetime"]).to_pandas()["datetime"]
            days.extend(s.tz_convert("UTC").date() for s in stamps)
            if len(days) >= n:
                break
        return sorted(set(days))[-n:] if n > 0 else []

    # ------------------------------------------------------------ writes
    def _write_years(self, exchange, symbol, frame, years, prune):
        import pyarrow as pa
        import pyarrow.parquet as pq

        directory = self.series_dir(exchange, symbol)
        for leftover in directory.glob("year=*/data.parquet.tmp"):
            leftover.unlink()
        schema = _schema()
        year_of = frame["datetime"].dt.year
        for year in sorted(years):
            part = frame[year_of == year][COLUMNS].reset_index(drop=True)
            year_dir = directory / f"year={int(year):04d}"
            year_dir.mkdir(parents=True, exist_ok=True)
            tmp = year_dir / "data.parquet.tmp"
            table = pa.Table.from_pandas(part, schema=schema, preserve_index=False)
            pq.write_table(table, str(tmp), compression="snappy")
            os.replace(tmp, year_dir / "data.parquet")
        if prune:
            present = {int(y) for y in year_of.unique()}
            for path in directory.glob("year=*/data.parquet"):
                if int(path.parent.name.split("=", 1)[1]) not in present:
                    path.unlink()

    def reconcile_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis, *,
                       asset_type, currency):
        """Newest-wins reconcile of served bars; returns (served bar count, revisions)."""
        bars = list(bars)
        incoming = bars_to_frame(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                                 currency=currency, price_basis=price_basis,
                                 volume_basis=volume_basis, splits=splits)
        with self._lock(exchange, symbol):
            stored = self.load(exchange, symbol)
            if stored.empty:
                if len(incoming):
                    fresh = _normalise(incoming)
                    self._write_years(exchange, symbol, fresh,
                                      set(fresh["datetime"].dt.year.tolist()), prune=False)
                return len(bars), []
            position = {int(ts): j for j, ts in enumerate(stored["timestamp"].tolist())}
            stored_values = {c: stored[c].to_numpy(dtype=np.float64) for c in COMPARE_COLUMNS}
            served_values = {c: incoming[c].to_numpy(dtype=np.float64) for c in COMPARE_COLUMNS}
            served_days = incoming["datetime"].dt.strftime("%Y-%m-%d").tolist()
            served_ts = incoming["timestamp"].tolist()
            revisions = []
            replaced = {}
            fresh_rows = []
            for i, ts in enumerate(served_ts):
                j = position.get(int(ts))
                if j is None:
                    fresh_rows.append(i)
                    continue
                differing = [c for c in COMPARE_COLUMNS
                             if not _same(stored_values[c][j], served_values[c][i])]
                if not differing:
                    continue
                if j not in replaced:
                    replaced[j] = i
                for column in differing:
                    revisions.append({"date": served_days[i], "column": column,
                                      "stored": float(stored_values[column][j]),
                                      "served": float(served_values[column][i])})
            if not replaced and not fresh_rows:
                return len(bars), revisions
            taken = list(replaced.values()) + fresh_rows
            kept = stored.drop(index=list(replaced))
            merged = _normalise(pd.concat([kept, incoming.iloc[taken]], ignore_index=True))
            years = set(incoming.iloc[taken]["datetime"].dt.year.tolist())
            self._write_years(exchange, symbol, merged, years, prune=False)
            return len(bars), revisions

    def ingest_bars(self, exchange, symbol, bars, splits, price_basis, volume_basis, *,
                    asset_type, currency, mode="append"):
        """Append (stored rows win) or overwrite; returns the incoming bar count."""
        bars = list(bars)
        incoming = bars_to_frame(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                                 currency=currency, price_basis=price_basis,
                                 volume_basis=volume_basis, splits=splits)
        if mode == "overwrite":
            self._overwrite(exchange, symbol, incoming)
            return len(bars)
        if mode != "append":
            raise StoreError(f"unknown ingest mode {mode!r}")
        with self._lock(exchange, symbol):
            if not len(incoming):
                return 0
            stored = self.load(exchange, symbol)
            if stored.empty:
                merged = _normalise(incoming)
            else:
                merged = _normalise(pd.concat([stored, incoming], ignore_index=True))
            years = set(incoming["datetime"].dt.year.tolist())
            self._write_years(exchange, symbol, merged, years, prune=False)
        return len(bars)

    def _overwrite(self, exchange, symbol, incoming):
        fresh = _normalise(incoming)
        with self._lock(exchange, symbol):
            self._write_years(exchange, symbol, fresh,
                              set(fresh["datetime"].dt.year.tolist()), prune=True)

    def ingest_yahoo_csv(self, csv_path, exchange, symbol, asset_type, currency="USD") -> int:
        """Replace the series with a Yahoo 7-column CSV; returns the CSV row count."""
        table = pd.read_csv(csv_path)
        missing = [c for c in YAHOO_COLUMNS if c not in table.columns]
        if missing:
            raise StoreError(f"{csv_path}: not a 7-column Yahoo CSV, missing {missing}")
        bars = [{"date": d, "open": o, "high": h, "low": lo, "close": c,
                 "adjusted_close": a, "volume": v}
                for d, o, h, lo, c, a, v in zip(
                    table["Date"].tolist(), table["Open"].tolist(), table["High"].tolist(),
                    table["Low"].tolist(), table["Close"].tolist(),
                    table["Adj Close"].tolist(), table["Volume"].tolist())]
        incoming = bars_to_frame(bars, symbol=symbol, exchange=exchange, asset_type=asset_type,
                                 currency=currency, price_basis="split_adjusted",
                                 volume_basis="raw", splits=[])
        self._overwrite(exchange, symbol, incoming)
        return len(table)

    def reapply_adjustment(self, exchange, symbol, splits) -> int:
        """Re-derive the whole series from *_raw; rewrite only when a value moved."""
        with self._lock(exchange, symbol):
            frame = self.load(exchange, symbol)
            if frame.empty:
                raise StoreError(f"nothing stored for {exchange}/{symbol}")
            adjusted = adjust(frame, splits)
            moved = False
            for column in DERIVED_COLUMNS:
                a = frame[column].to_numpy(dtype=np.float64)
                b = adjusted[column].to_numpy(dtype=np.float64)
                if not ((a == b) | (np.isnan(a) & np.isnan(b))).all():
                    moved = True
                    break
            if moved:
                self._write_years(exchange, symbol, adjusted,
                                  set(adjusted["datetime"].dt.year.tolist()), prune=True)
            return len(frame)
