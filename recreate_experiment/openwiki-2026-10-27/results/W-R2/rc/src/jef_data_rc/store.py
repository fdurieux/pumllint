"""Year-partitioned Parquet store of EOD bars.

Layout below the store root:

    market_data/exchange={exchange}/symbol={symbol}/year={year}/data.parquet

Each row keeps the UTC timestamp/datetime, store identity, classification,
currency, the provider-served `*_raw` OHLCV and `adjusted_close` (the audit
and re-derivation inputs), the derived main OHLCV, both factors, and the
`price_basis`. Every mutating operation holds a per-symbol POSIX `flock` on
`{symbol_dir}/.lock` for its whole read-modify-write cycle; readers take no
lock. Each year is written to `data.parquet.tmp` and installed with
`os.replace()`. There is no cross-year transaction and no fsync.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import fcntl
import math
import os
import shutil
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import pyarrow as pa
import pyarrow.parquet as pq

from jef_data_rc.adjust import adjust, split_factors
from jef_data_rc.contract import REQUIRED_COLUMNS

FLOAT_COLUMNS = (
    "open", "high", "low", "close", "volume",
    "open_raw", "high_raw", "low_raw", "close_raw", "volume_raw",
    "adjusted_close", "adjustment_factor", "cumulative_split_factor",
)
STRING_COLUMNS = ("symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis")
COLUMNS = (
    "timestamp", "datetime",
    "open", "high", "low", "close", "volume",
    "symbol", "exchange", "asset_type", "asset_subtype",
    "open_raw", "high_raw", "low_raw", "close_raw", "volume_raw",
    "adjusted_close", "adjustment_factor", "cumulative_split_factor",
    "currency", "price_basis",
)
IDENTITY_COLUMNS = ("open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close")
PRICE_BASES = ("raw", "split_adjusted")
VOLUME_BASES = ("raw", "split_adjusted")

DAY_MS = 86_400_000
LOCK_POLL_SECONDS = 0.5
DEFAULT_LOCK_TIMEOUT = 300.0



class StoreError(RuntimeError):
    """A store operation could not be completed."""


def _date_ms(date: str) -> int:
    d = _dt.date.fromisoformat(str(date)[:10])
    return (d - _dt.date(1970, 1, 1)).days * DAY_MS


def _float(value: Any) -> float:
    if value is None:
        return float("nan")
    return float(value)


def _empty_frame() -> pd.DataFrame:
    data: dict[str, pd.Series] = {
        "timestamp": pd.Series([], dtype="int64"),
        "datetime": pd.Series([], dtype="datetime64[ms, UTC]"),
    }
    for c in COLUMNS[2:]:
        data[c] = pd.Series([], dtype="float64" if c in FLOAT_COLUMNS else object)
    return pd.DataFrame(data)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by timestamp (stable) and keep the first row of each timestamp."""
    out = df.sort_values("timestamp", kind="mergesort")
    out = out.drop_duplicates(subset="timestamp", keep="first")
    return out.reset_index(drop=True)


def _years(df: pd.DataFrame) -> np.ndarray:
    return pd.to_datetime(df["timestamp"].to_numpy(dtype="int64"), unit="ms", utc=True).year.to_numpy()


def _to_table(df: pd.DataFrame) -> pa.Table:
    """Arrow table for a partition; all-null text columns are typed as string."""
    table = pa.Table.from_pandas(df, preserve_index=False)
    for i, f in enumerate(table.schema):
        if pa.types.is_null(f.type):
            want = pa.float64() if f.name in FLOAT_COLUMNS else pa.string()
            table = table.set_column(i, pa.field(f.name, want), table.column(i).cast(want))
    return table


class ParquetStore:
    """Local EOD store rooted at `root`."""

    def __init__(self, root: str | Path, *, clock=time.monotonic, sleep=time.sleep,
                 lock_timeout: float = DEFAULT_LOCK_TIMEOUT):
        self.root = Path(root)
        self._clock = clock
        self._sleep = sleep
        self.lock_timeout = lock_timeout

    # -- layout -------------------------------------------------------------

    def symbol_dir(self, exchange: str, symbol: str) -> Path:
        return self.root / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"

    def year_path(self, exchange: str, symbol: str, year: int) -> Path:
        return self.symbol_dir(exchange, symbol) / f"year={int(year)}" / "data.parquet"

    # -- locking ------------------------------------------------------------

    @contextlib.contextmanager
    def lock(self, exchange: str, symbol: str):
        directory = self.symbol_dir(exchange, symbol)
        directory.mkdir(parents=True, exist_ok=True)
        fd = os.open(directory / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
        try:
            deadline = self._clock() + self.lock_timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (BlockingIOError, PermissionError):
                    if self._clock() >= deadline:
                        raise StoreError(
                            f"timed out after {self.lock_timeout:g}s waiting for the "
                            f"writer lock on {exchange}/{symbol}"
                        ) from None
                    self._sleep(LOCK_POLL_SECONDS)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    # -- reading ------------------------------------------------------------

    def load(self, exchange: str, symbol: str) -> pd.DataFrame:
        """The full stored series, sorted by timestamp, every column included."""
        directory = self.symbol_dir(exchange, symbol)
        files = sorted(directory.glob("year=*/data.parquet"))
        if not files:
            return _empty_frame()
        frames = [pq.read_table(f).to_pandas() for f in files]
        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
        ordered = [c for c in COLUMNS if c in df.columns] + [c for c in df.columns if c not in COLUMNS]
        return df[ordered]

    def has_rows(self, exchange: str, symbol: str) -> bool:
        return not self.load(exchange, symbol).empty

    def session_dates(self, exchange: str, symbol: str) -> list[str]:
        df = self.load(exchange, symbol)
        if df.empty:
            return []
        return list(pd.to_datetime(df["datetime"], utc=True).dt.strftime("%Y-%m-%d"))

    def recent_dates(self, exchange: str, symbol: str, n: int) -> list[str]:
        """The newest `n` stored session dates, ascending."""
        dates = self.session_dates(exchange, symbol)
        return dates[-n:] if n > 0 else []

    def latest_date(self, exchange: str, symbol: str) -> str | None:
        dates = self.recent_dates(exchange, symbol, 1)
        return dates[-1] if dates else None

    # -- row construction ---------------------------------------------------

    def build_rows(self, bars: Iterable[dict], *, exchange: str, symbol: str, asset_type: str,
                   currency: str, price_basis: str, splits: Iterable[Any] | None = (),
                   volume_basis: str = "raw", asset_subtype: str | None = None) -> pd.DataFrame:
        """Turn provider bar dictionaries into full-schema store rows."""
        if price_basis not in PRICE_BASES:
            raise StoreError(f"unknown price_basis {price_basis!r} (expected one of {PRICE_BASES})")
        if volume_basis not in VOLUME_BASES:
            raise StoreError(f"unknown volume_basis {volume_basis!r} (expected one of {VOLUME_BASES})")
        bars = list(bars)
        if not bars:
            return _empty_frame()
        dates = [_dt.date.fromisoformat(str(b["date"])[:10]).isoformat() for b in bars]
        ts = np.array([_date_ms(d) for d in dates], dtype="int64")
        served = {f: np.array([_float(b.get(f)) for b in bars], dtype="float64")
                  for f in ("open", "high", "low", "close", "volume")}
        adj_close = np.array(
            [_float(b["adjusted_close"]) if b.get("adjusted_close") is not None else _float(b.get("close"))
             for b in bars],
            dtype="float64",
        )
        n = len(bars)
        with np.errstate(divide="ignore", invalid="ignore"):
            adjustment_factor = adj_close / served["close"]
        frame = pd.DataFrame({
            "timestamp": ts,
            "datetime": pd.to_datetime(ts, unit="ms", utc=True),
            "open": served["open"].copy(),
            "high": served["high"].copy(),
            "low": served["low"].copy(),
            "close": served["close"].copy(),
            "volume": served["volume"].copy(),
            "symbol": [symbol] * n,
            "exchange": [exchange] * n,
            "asset_type": [asset_type] * n,
            "asset_subtype": [asset_subtype] * n,
            "open_raw": served["open"],
            "high_raw": served["high"],
            "low_raw": served["low"],
            "close_raw": served["close"],
            "volume_raw": served["volume"].copy(),
            "adjusted_close": adj_close,
            "adjustment_factor": adjustment_factor,
            "cumulative_split_factor": np.ones(n, dtype="float64"),
            "currency": [currency] * n,
            "price_basis": [price_basis] * n,
        })
        if price_basis == "raw":
            if volume_basis == "split_adjusted":
                factor = split_factors(dates, splits)
                frame["volume_raw"] = served["volume"] / factor
            frame = adjust(frame, splits)
        return frame[list(COLUMNS)]

    # -- writing ------------------------------------------------------------

    def _sweep_tmp(self, exchange: str, symbol: str) -> None:
        for tmp in self.symbol_dir(exchange, symbol).glob("year=*/data.parquet.tmp"):
            with contextlib.suppress(OSError):
                tmp.unlink()

    def _write_years(self, df: pd.DataFrame, exchange: str, symbol: str,
                     years: Iterable[int] | None, prune: bool) -> None:
        self._sweep_tmp(exchange, symbol)
        df = df[list(COLUMNS)]
        all_years = _years(df) if len(df) else np.array([], dtype=int)
        targets = set(int(y) for y in (all_years if years is None else years))
        for year in sorted(targets):
            part = df[all_years == year]
            if part.empty:
                continue
            final = self.year_path(exchange, symbol, year)
            final.parent.mkdir(parents=True, exist_ok=True)
            tmp = final.with_name("data.parquet.tmp")
            table = _to_table(part.reset_index(drop=True))
            pq.write_table(table, tmp)
            os.replace(tmp, final)
        if prune:
            keep = set(int(y) for y in all_years)
            for path in self.symbol_dir(exchange, symbol).glob("year=*"):
                try:
                    year = int(path.name.split("=", 1)[1])
                except (IndexError, ValueError):
                    continue
                if year not in keep:
                    shutil.rmtree(path, ignore_errors=True)

    def _save_locked(self, df: pd.DataFrame, exchange: str, symbol: str, mode: str) -> int:
        if mode not in ("append", "overwrite"):
            raise StoreError(f"unknown save mode {mode!r}")
        incoming = _normalize(df[list(COLUMNS)])
        if mode == "overwrite":
            self._write_years(incoming, exchange, symbol, None, prune=True)
            return len(incoming)
        existing = self.load(exchange, symbol)
        merged = _normalize(pd.concat([existing[list(COLUMNS)], incoming], ignore_index=True)) \
            if not existing.empty else incoming
        years = set(int(y) for y in _years(incoming)) if len(incoming) else set()
        self._write_years(merged, exchange, symbol, years, prune=False)
        return len(incoming)

    def save(self, df: pd.DataFrame, exchange: str, symbol: str, mode: str = "append") -> int:
        """Persist rows. Append keeps the stored row on a duplicate timestamp and
        rewrites only incoming years; overwrite replaces the series, landing new
        year files before pruning stale ones."""
        if df.empty and mode == "append":
            return 0
        with self.lock(exchange, symbol):
            return self._save_locked(df, exchange, symbol, mode)

    def ingest(self, bars: Iterable[dict], *, exchange: str, symbol: str, asset_type: str,
               currency: str, price_basis: str, splits: Iterable[Any] | None = (),
               volume_basis: str = "raw", mode: str = "append",
               asset_subtype: str | None = None) -> int:
        frame = self.build_rows(bars, exchange=exchange, symbol=symbol, asset_type=asset_type,
                                currency=currency, price_basis=price_basis, splits=splits,
                                volume_basis=volume_basis, asset_subtype=asset_subtype)
        if frame.empty:
            return 0
        return self.save(frame, exchange, symbol, mode=mode)

    def reconcile_bars(self, exchange: str, symbol: str, bars: Iterable[dict], *, asset_type: str,
                       currency: str, price_basis: str, splits: Iterable[Any] | None = (),
                       volume_basis: str = "raw", asset_subtype: str | None = None) -> list[dict]:
        """Newest-wins reconciliation of the supplied window.

        For each supplied timestamp already stored, compare the as-served
        identity (`*_raw` OHLCV and `adjusted_close`); a difference replaces the
        stored row and yields one revision record per changed cell. New
        timestamps append. Timestamps not supplied are untouched. Nothing is
        written when the bars bring neither a change nor a new timestamp.
        """
        bars = list(bars)
        if not bars:
            return []
        with self.lock(exchange, symbol):
            served = _normalize(self.build_rows(
                bars, exchange=exchange, symbol=symbol, asset_type=asset_type, currency=currency,
                price_basis=price_basis, splits=splits, volume_basis=volume_basis,
                asset_subtype=asset_subtype))
            existing = self.load(exchange, symbol)
            if existing.empty:
                self._write_years(served, exchange, symbol, None, prune=False)
                return []
            existing = _normalize(existing[list(COLUMNS)])
            stored_ts = existing["timestamp"].to_numpy(dtype="int64")
            served_ts = served["timestamp"].to_numpy(dtype="int64")
            is_new = ~np.isin(served_ts, stored_ts)
            common = served[~is_new].reset_index(drop=True)
            by_ts = existing.set_index("timestamp")
            aligned = by_ts.loc[common["timestamp"].to_numpy(dtype="int64")].reset_index()
            changed = np.zeros(len(common), dtype=bool)
            diffs: dict[str, np.ndarray] = {}
            for col in IDENTITY_COLUMNS:
                a = aligned[col].to_numpy(dtype="float64")
                b = common[col].to_numpy(dtype="float64")
                d = ~((a == b) | (np.isnan(a) & np.isnan(b)))
                diffs[col] = d
                changed |= d
            revisions: list[dict] = []
            dates = pd.to_datetime(common["timestamp"].to_numpy(dtype="int64"), unit="ms", utc=True) \
                .strftime("%Y-%m-%d")
            for i in np.flatnonzero(changed):
                for col in IDENTITY_COLUMNS:
                    if diffs[col][i]:
                        revisions.append({
                            "date": dates[i],
                            "column": col,
                            "stored": float(aligned[col].iloc[i]),
                            "served": float(common[col].iloc[i]),
                        })
            if not changed.any() and not is_new.any():
                return []
            replaced_ts = common["timestamp"].to_numpy(dtype="int64")[changed]
            keep = existing[~np.isin(stored_ts, replaced_ts)]
            incoming = pd.concat([common[changed], served[is_new]], ignore_index=True)
            merged = _normalize(pd.concat([keep, incoming], ignore_index=True))
            years = set(int(y) for y in _years(incoming))
            self._write_years(merged, exchange, symbol, years, prune=False)
            return revisions

    def ingest_yahoo_csv(self, path: str | Path, *, symbol: str, exchange: str = "yahoo",
                         asset_type: str = "stock", currency: str = "USD",
                         mode: str = "overwrite") -> int:
        """Import a whole Yahoo-format CSV as a pre-adjusted series.

        Zero-volume rows are kept: row-dropping policy belongs to the
        downstream seam, not to persistence.
        """
        df = pd.read_csv(path)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise StoreError(f"{path}: missing Yahoo column(s): {', '.join(missing)}")
        bars = []
        for row in df[list(REQUIRED_COLUMNS)].itertuples(index=False, name=None):
            date, o, h, l, c, adj, v = row
            bars.append({
                "date": _dt.date.fromisoformat(str(date).strip()[:10]).isoformat(),
                "open": float(o), "high": float(h), "low": float(l), "close": float(c),
                "adjusted_close": float(adj), "volume": float(v),
            })
        return self.ingest(bars, exchange=exchange, symbol=symbol, asset_type=asset_type,
                           currency=currency, price_basis="split_adjusted",
                           volume_basis="split_adjusted", mode=mode)

    def reapply_adjustment(self, exchange: str, symbol: str, splits: Iterable[Any] | None) -> bool:
        """Re-derive the whole stored raw-basis series; write only when it changed."""
        with self.lock(exchange, symbol):
            df = self.load(exchange, symbol)
            if df.empty:
                return False
            derived = adjust(df, splits)
            if derived.equals(df):
                return False
            self._write_years(derived, exchange, symbol, None, prune=True)
            return True

    # -- export -------------------------------------------------------------

    def to_contract_frame(self, exchange: str, symbol: str) -> pd.DataFrame:
        """Stored rows as the seven-column interchange frame."""
        df = self.load(exchange, symbol)
        volume = df["volume"].to_numpy(dtype="float64")
        integral = bool(np.all(np.isfinite(volume)) and np.all(np.floor(volume) == volume))
        out = pd.DataFrame({
            "Date": pd.to_datetime(df["datetime"], utc=True).dt.strftime("%Y-%m-%d"),
            "Open": df["open"].to_numpy(dtype="float64"),
            "High": df["high"].to_numpy(dtype="float64"),
            "Low": df["low"].to_numpy(dtype="float64"),
            "Close": df["close"].to_numpy(dtype="float64"),
            "Adj Close": df["adjusted_close"].to_numpy(dtype="float64"),
            "Volume": volume.astype("int64") if integral else volume,
        })
        return out


def is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False
