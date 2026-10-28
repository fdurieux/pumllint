"""The local, year-partitioned EOD store.

Market bars live at::

    market_data/exchange={exchange}/symbol={symbol}/year={year}/data.parquet

Each row keeps three value sets: the model-facing main OHLCV, the provider's
as-served ``*_raw`` OHLCV plus ``adjusted_close`` (the audit trail and the
adjustment input), and the store-derived split state
(``cumulative_split_factor``, ``price_basis``).

Every mutating operation holds a per-symbol ``fcntl.flock`` on
``{symbol_dir}/.lock`` across its read-modify-write cycle; readers take no
lock. Each year is written to ``data.parquet.tmp`` and installed with
``os.replace``, so a lock-free reader never sees a torn year file. There is
no cross-year transaction and no fsync.
"""
from __future__ import annotations

import fcntl
import math
import os
import shutil
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from jef_data_rc.adjust import adjust, split_factors
from jef_data_rc.contract import REQUIRED_COLUMNS

COLUMNS = (
    "timestamp",
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
    "exchange",
    "asset_type",
    "asset_subtype",
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "volume_raw",
    "adjusted_close",
    "adjustment_factor",
    "cumulative_split_factor",
    "currency",
    "price_basis",
)

# The as-served identity that decides whether a re-fetched bar is a revision.
IDENTITY_COLUMNS = (
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "volume_raw",
    "adjusted_close",
)

PRICE_BASES = ("raw", "split_adjusted")
VOLUME_BASES = ("raw", "split_adjusted")

DATA_FILE = "data.parquet"
TMP_FILE = "data.parquet.tmp"
LOCK_FILE = ".lock"
LOCK_POLL_SECONDS = 0.5
DEFAULT_LOCK_TIMEOUT = 300.0

_MS_PER_DAY = 86_400_000
_EPOCH = date(1970, 1, 1)


class StoreError(RuntimeError):
    """A store operation could not be completed."""


def _bar_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _same(a, b) -> bool:
    a_nan = a is None or (isinstance(a, float) and math.isnan(a))
    b_nan = b is None or (isinstance(b, float) and math.isnan(b))
    if a_nan or b_nan:
        return a_nan and b_nan
    return a == b


def _json_value(value):
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) else value


_STRING_COLUMNS = frozenset(
    {"symbol", "exchange", "asset_type", "asset_subtype", "currency", "price_basis"}
)


def _empty_frame() -> pd.DataFrame:
    data = {}
    for c in COLUMNS:
        if c == "timestamp":
            data[c] = pd.Series([], dtype="int64")
        elif c == "datetime":
            data[c] = pd.Series([], dtype="datetime64[ns, UTC]")
        elif c in _STRING_COLUMNS:
            data[c] = pd.Series([], dtype=object)
        else:
            data[c] = pd.Series([], dtype="float64")
    return pd.DataFrame(data)


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    """First row per timestamp wins, ascending timestamps, schema order."""
    frame = frame.drop_duplicates(subset="timestamp", keep="first")
    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return frame[list(COLUMNS)]


def _years(frame: pd.DataFrame) -> pd.Series:
    return frame["datetime"].dt.year


class ParquetStore:
    def __init__(
        self,
        base="data",
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        self.base = Path(base)
        self.lock_timeout = float(lock_timeout)
        self._clock = clock
        self._sleep = sleep

    # -- layout -------------------------------------------------------------

    def symbol_dir(self, exchange: str, symbol: str) -> Path:
        return (
            self.base / "market_data" / f"exchange={exchange}" / f"symbol={symbol}"
        )

    def _year_files(self, exchange: str, symbol: str) -> list[tuple[int, Path]]:
        sdir = self.symbol_dir(exchange, symbol)
        if not sdir.is_dir():
            return []
        found = []
        for ydir in sdir.glob("year=*"):
            path = ydir / DATA_FILE
            try:
                year = int(ydir.name.split("=", 1)[1])
            except ValueError:
                continue
            if path.is_file():
                found.append((year, path))
        return sorted(found)

    # -- reads (lock-free) --------------------------------------------------

    def load(self, exchange: str, symbol: str) -> pd.DataFrame:
        files = self._year_files(exchange, symbol)
        if not files:
            return _empty_frame()
        frames = [
            pq.read_table(str(path), partitioning=None).to_pandas() for _, path in files
        ]
        frame = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        return frame.sort_values("timestamp", kind="stable").reset_index(drop=True)

    def recent_dates(self, exchange: str, symbol: str, n: int) -> list[date]:
        """The newest ``n`` stored session dates, oldest first."""
        if n < 1:
            return []
        stamps: list[int] = []
        for _, path in reversed(self._year_files(exchange, symbol)):
            column = pq.read_table(
                str(path), columns=["timestamp"], partitioning=None
            ).to_pandas()["timestamp"]
            stamps = sorted(set(int(v) for v in column) | set(stamps))
            if len(stamps) >= n:
                break
        newest = stamps[-n:]
        return [_EPOCH.fromordinal(_EPOCH.toordinal() + ms // _MS_PER_DAY) for ms in newest]

    def latest_date(self, exchange: str, symbol: str) -> date | None:
        recent = self.recent_dates(exchange, symbol, 1)
        return recent[-1] if recent else None

    # -- locking and writes -------------------------------------------------

    @contextmanager
    def _lock(self, exchange: str, symbol: str):
        sdir = self.symbol_dir(exchange, symbol)
        sdir.mkdir(parents=True, exist_ok=True)
        lock_path = sdir / LOCK_FILE
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            deadline = self._clock() + self.lock_timeout
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if self._clock() >= deadline:
                        raise StoreError(
                            f"timed out after {self.lock_timeout:g}s waiting for "
                            f"the writer lock {lock_path}"
                        ) from None
                    self._sleep(LOCK_POLL_SECONDS)
            try:
                yield sdir
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _write_years(self, sdir: Path, frame: pd.DataFrame, *, prune: bool) -> None:
        written: set[int] = set()
        if len(frame):
            for year, part in frame.groupby(_years(frame), sort=True):
                ydir = sdir / f"year={int(year)}"
                ydir.mkdir(parents=True, exist_ok=True)
                tmp = ydir / TMP_FILE
                table = pa.Table.from_pandas(
                    part.reset_index(drop=True), preserve_index=False
                )
                pq.write_table(table, str(tmp))
                os.replace(tmp, ydir / DATA_FILE)
                written.add(int(year))
        if prune:
            for ydir in sdir.glob("year=*"):
                try:
                    year = int(ydir.name.split("=", 1)[1])
                except ValueError:
                    continue
                if year not in written:
                    shutil.rmtree(ydir, ignore_errors=True)
        for leftover in sdir.glob(f"year=*/{TMP_FILE}"):
            try:
                leftover.unlink()
            except OSError:
                pass

    def _merge_years(self, sdir: Path, existing: pd.DataFrame, incoming: pd.DataFrame) -> None:
        """Rewrite only the years ``incoming`` touches; existing rows first."""
        years = set(int(y) for y in _years(incoming))
        keep = existing[_years(existing).isin(years)] if len(existing) else existing
        parts = [f for f in (keep, incoming) if len(f)]
        combined = _normalize(
            pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
        )
        self._write_years(sdir, combined, prune=False)

    def save(self, frame: pd.DataFrame, exchange: str, symbol: str, mode: str = "append") -> int:
        if mode not in ("append", "overwrite"):
            raise StoreError(f"unknown save mode {mode!r}")
        incoming = _normalize(frame)
        with self._lock(exchange, symbol) as sdir:
            if mode == "overwrite":
                self._write_years(sdir, incoming, prune=True)
            elif len(incoming):
                existing = self.load(exchange, symbol)
                self._merge_years(sdir, existing, incoming)
        return int(len(incoming))

    # -- bar ingestion ------------------------------------------------------

    def bars_to_frame(
        self,
        bars,
        *,
        exchange: str,
        symbol: str,
        asset_type: str,
        currency: str = "USD",
        price_basis: str = "raw",
        volume_basis: str = "raw",
        splits=(),
        asset_subtype=None,
    ) -> pd.DataFrame:
        if price_basis not in PRICE_BASES:
            raise StoreError(f"unknown price_basis {price_basis!r}")
        if volume_basis not in VOLUME_BASES:
            raise StoreError(f"unknown volume_basis {volume_basis!r}")
        bars = list(bars)
        if not bars:
            return _empty_frame()
        days = [_bar_date(b["date"]) for b in bars]
        ts = np.array(
            [(d.toordinal() - _EPOCH.toordinal()) * _MS_PER_DAY for d in days],
            dtype="int64",
        )
        moments = pd.to_datetime(ts, unit="ms", utc=True).astype("datetime64[ns, UTC]")

        def column(key):
            return np.array([float(b[key]) for b in bars], dtype="float64")

        open_raw = column("open")
        high_raw = column("high")
        low_raw = column("low")
        close_raw = column("close")
        served_volume = column("volume")
        adjusted_close = np.array(
            [
                float(b["adjusted_close"])
                if b.get("adjusted_close") is not None
                else float(b["close"])
                for b in bars
            ],
            dtype="float64",
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            adjustment_factor = adjusted_close / close_raw
        n = len(bars)
        if price_basis == "raw" and volume_basis == "split_adjusted":
            volume_raw = served_volume / split_factors(days, splits)
        else:
            volume_raw = served_volume
        frame = pd.DataFrame(
            {
                "timestamp": ts,
                "datetime": moments,
                "open": open_raw,
                "high": high_raw,
                "low": low_raw,
                "close": close_raw,
                "volume": volume_raw,
                "symbol": [symbol] * n,
                "exchange": [exchange] * n,
                "asset_type": [asset_type] * n,
                "asset_subtype": [asset_subtype] * n,
                "open_raw": open_raw,
                "high_raw": high_raw,
                "low_raw": low_raw,
                "close_raw": close_raw,
                "volume_raw": volume_raw,
                "adjusted_close": adjusted_close,
                "adjustment_factor": adjustment_factor,
                "cumulative_split_factor": np.ones(n, dtype="float64"),
                "currency": [currency] * n,
                "price_basis": [price_basis] * n,
            }
        )
        if price_basis == "raw":
            frame = adjust(frame, splits)
        return frame

    def ingest(
        self,
        bars,
        *,
        exchange: str,
        symbol: str,
        asset_type: str,
        currency: str = "USD",
        price_basis: str = "raw",
        volume_basis: str = "raw",
        splits=(),
        mode: str = "append",
    ) -> int:
        frame = self.bars_to_frame(
            bars,
            exchange=exchange,
            symbol=symbol,
            asset_type=asset_type,
            currency=currency,
            price_basis=price_basis,
            volume_basis=volume_basis,
            splits=splits,
        )
        if not len(frame) and mode == "append":
            return 0
        return self.save(frame, exchange, symbol, mode=mode)

    def reconcile_bars(
        self,
        exchange: str,
        symbol: str,
        bars,
        *,
        asset_type: str,
        currency: str = "USD",
        price_basis: str = "raw",
        volume_basis: str = "raw",
        splits=(),
    ) -> list[dict]:
        """Newest-wins for the supplied timestamps only.

        A supplied timestamp already stored is replaced when any as-served
        identity value differs; one revision record per changed cell is
        returned. New timestamps append. Timestamps not supplied are never
        touched. Nothing is written when nothing changed.
        """
        served = self.bars_to_frame(
            bars,
            exchange=exchange,
            symbol=symbol,
            asset_type=asset_type,
            currency=currency,
            price_basis=price_basis,
            volume_basis=volume_basis,
            splits=splits,
        )
        if not len(served):
            return []
        served = _normalize(served)
        with self._lock(exchange, symbol) as sdir:
            existing = self.load(exchange, symbol)
            stored = {}
            if len(existing):
                for row in existing[["timestamp", *IDENTITY_COLUMNS, "datetime"]].itertuples(index=False):
                    stored[int(row[0])] = row
            revisions: list[dict] = []
            changed: list[int] = []
            novel: list[int] = []
            for row in served[["timestamp", *IDENTITY_COLUMNS, "datetime"]].itertuples(index=False):
                ts = int(row[0])
                old = stored.get(ts)
                if old is None:
                    novel.append(ts)
                    continue
                cells = []
                for i, col in enumerate(IDENTITY_COLUMNS, start=1):
                    if not _same(old[i], row[i]):
                        cells.append(
                            {
                                "date": row[-1].strftime("%Y-%m-%d"),
                                "column": col,
                                "stored": _json_value(old[i]),
                                "served": _json_value(row[i]),
                            }
                        )
                if cells:
                    changed.append(ts)
                    revisions.extend(cells)
            if not changed and not novel:
                return []
            replace = set(changed) | set(novel)
            keep = existing[~existing["timestamp"].isin(changed)] if len(existing) else existing
            incoming = served[served["timestamp"].isin(replace)]
            self._merge_years(sdir, keep, incoming)
        return revisions

    def ingest_yahoo_csv(
        self,
        path,
        *,
        exchange: str = "yahoo",
        symbol: str,
        asset_type: str,
        currency: str = "USD",
        mode: str = "overwrite",
    ) -> int:
        """Import a Yahoo-format seven-column CSV as a split-adjusted series."""
        frame = pd.read_csv(path)
        missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise StoreError(
                f"{path}: missing Yahoo column(s): {', '.join(missing)}"
            )
        dates = pd.to_datetime(frame["Date"]).dt.strftime("%Y-%m-%d")
        bars = [
            {
                "date": d,
                "open": o,
                "high": h,
                "low": low,
                "close": c,
                "adjusted_close": a,
                "volume": v,
            }
            for d, o, h, low, c, a, v in zip(
                dates,
                frame["Open"],
                frame["High"],
                frame["Low"],
                frame["Close"],
                frame["Adj Close"],
                frame["Volume"],
            )
        ]
        return self.ingest(
            bars,
            exchange=exchange,
            symbol=symbol,
            asset_type=asset_type,
            currency=currency,
            price_basis="split_adjusted",
            volume_basis="split_adjusted",
            mode=mode,
        )

    def reapply_adjustment(self, exchange: str, symbol: str, splits) -> bool:
        """Re-derive the whole stored series; write only if it changed."""
        with self._lock(exchange, symbol) as sdir:
            existing = self.load(exchange, symbol)
            if not len(existing):
                return False
            derived = adjust(existing, splits)
            if derived.equals(existing):
                return False
            self._write_years(sdir, _normalize(derived), prune=True)
        return True

    # -- interchange --------------------------------------------------------

    def to_contract_frame(self, exchange: str, symbol: str) -> pd.DataFrame:
        """The seven-column ``Date..Volume`` frame, every stored row kept."""
        frame = self.load(exchange, symbol)
        if not len(frame):
            empty = {c: pd.Series([], dtype="float64") for c in REQUIRED_COLUMNS}
            empty["Date"] = pd.Series([], dtype=object)
            empty["Volume"] = pd.Series([], dtype="int64")
            return pd.DataFrame(empty)
        volume = frame["volume"].astype("float64")
        values = volume.to_numpy()
        if np.isfinite(values).all() and (values == np.floor(values)).all():
            volume = volume.astype("int64")
        return pd.DataFrame(
            {
                "Date": frame["datetime"].dt.strftime("%Y-%m-%d"),
                "Open": frame["open"].astype("float64"),
                "High": frame["high"].astype("float64"),
                "Low": frame["low"].astype("float64"),
                "Close": frame["close"].astype("float64"),
                "Adj Close": frame["adjusted_close"].astype("float64"),
                "Volume": volume,
            }
        )
