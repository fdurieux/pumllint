# The store: on-disk layout, schema, read and write semantics

One store root (a directory; `--store` or the universe's `defaults.store`)
holds two independent stores: the **market-data store** (Parquet, this file)
and the **corporate-actions store** (JSON, §8). Requirements: JDL-057,
JDL-058, JDL-059, JDL-060, JDL-061,
JDL-062, JDL-063, JDL-064, JDL-065,
JDL-066, JDL-067, JDL-068,
JDL-069, JDL-070, JDL-141, JDL-040 …
JDL-044.

## 1. Layout

```
{store}/
  market_data/
    exchange={exchange tag}/            # the universe source's `exchange` (eodhd | binance | yahoo | declared)
      symbol={symbol}/                  # the store symbol exactly as declared (e.g. SPLT.US, PAIRUSDT)
        .lock                           # created by the first write; advisory lock target
        year={YYYY}/                    # UTC calendar year of the session date
          data.parquet                  # snappy-compressed Parquet, schema §3
          data.parquet.tmp              # transient: exists only during a write
  corporate_actions/
    splits/{SYMBOL}.json                # §8; '/' in the symbol becomes '_'
    dividends/{SYMBOL}.json
```

* A series is identified by (exchange tag, symbol). Its rows for one calendar
  year live in exactly one `data.parquet`.
* Readers match `year=*/data.parquet` exactly, so a leftover
  `data.parquet.tmp` is never read.
* No other files are written (no manifest, no index, no fsync).

## 2. Write discipline (every writer)

1. Take an exclusive advisory lock (`flock`-style, non-blocking attempts) on
   `{symbol dir}/.lock`, creating the directory and the file (mode 0644) when
   absent. Retry every 0.5 s; after 300 s fail with StoreError
   `{exchange}/{symbol}: another writer holds the store lock after 300s ({lock path})`.
   Hold it across the whole read-modify-write; release by closing.
2. Delete any `year=*/data.parquet.tmp` left by a crashed writer of this series.
3. For each year to write: write the year's rows to `data.parquet.tmp`
   (schema §3, row order as in memory, no index column), then atomically rename
   it onto `data.parquet`.
4. When pruning (overwrite and re-adjustment writes), delete year files whose
   year no longer occurs in the new series — only after step 3 finished for
   every year.

Readers take no lock.

## 3. Schema (21 columns, this order)

| # | column | Parquet type | read back as (pandas 3.0.5) | meaning |
|---|---|---|---|---|
| 1 | `timestamp` | int64 | int64 | Unix epoch **seconds** of the session's 00:00 UTC (see note) |
| 2 | `datetime` | timestamp(ms, tz=UTC) | datetime64[ms, UTC] | the session's 00:00 UTC instant |
| 3 | `open` | double | float64 | split-adjusted open (adjustment.md) |
| 4 | `high` | double | float64 | split-adjusted high |
| 5 | `low` | double | float64 | split-adjusted low |
| 6 | `close` | double | float64 | split-adjusted close |
| 7 | `volume` | double | float64 | split-adjusted (forward) volume |
| 8 | `symbol` | string | str | store symbol |
| 9 | `exchange` | string | str | store partition tag (never the provider name when they differ) |
| 10 | `asset_type` | string | str | declared store asset_type: `stock`, `etf` or `crypto` |
| 11 | `asset_subtype` | string | str | always the empty string |
| 12 | `adjustment_factor` | double | float64 | adjusted_close / close_raw |
| 13 | `open_raw` | double | float64 | as served |
| 14 | `high_raw` | double | float64 | as served |
| 15 | `low_raw` | double | float64 | as served |
| 16 | `close_raw` | double | float64 | as served |
| 17 | `volume_raw` | double | float64 | TRUE raw volume (raw-ized at ingest when served adjusted) |
| 18 | `adjusted_close` | double | float64 | provider's splits+dividends close (audit only) |
| 19 | `cumulative_split_factor` | double | float64 | the CRSP split-only factor (1.0 for pre-adjusted series) |
| 20 | `currency` | string | str | the leg's currency |
| 21 | `price_basis` | string | str | `raw` or `split_adjusted` |

**Timestamp note (JDL-060).** Bar dates are parsed with the format
inferred from the first bar; for date-only text the pinned pandas parses at
microsecond resolution, and the stored `timestamp` is that microsecond count
integer-divided by 10^6, i.e. Unix **seconds** (2024-01-02 → `1704153600`),
although the column is documented upstream as milliseconds. `datetime` is the
same instant at millisecond resolution. A date not in the first bar's format is
a refusal (JDL-061): `unparseable dates cannot be stored: [...]` (at
most the first five offending values, Python list repr), nothing written.

## 4. Building rows from bars

One stored row per bar. Which basis applies, and every formula for the
numeric cells, are defined once in adjustment.md (§1 basis, §3 factor and
volume raw-ization, §4 the adjustment pass, §5 pre-adjusted series); the
cell-by-cell walk-through is seam_frame.md §3. What this file adds:

* `adjusted_close` is the bar's `adjusted_close` value when the bar carries
  that key (a NaN there stays NaN), else its `close`; `adjustment_factor` =
  adjusted_close / close_raw.
* Labels (JDL-062): `symbol`, `exchange` = store coordinates,
  `asset_type` = declared, `asset_subtype` = `""`, `currency` = the leg's,
  `price_basis` = resolved basis.
* A bar date that carries a time of day keeps it (`2024-01-02 10:30:00` →
  `datetime` 10:30 UTC, `timestamp` 1704191400); the program never truncates
  to midnight itself.

## 5. Read semantics (JDL-063, JDL-064)

* **Full read**: concatenate the year files in sorted path order, sort by
  `timestamp` with a stable sort, drop later duplicates of a timestamp, renumber
  `0..n-1`. No year file → zero rows with the 21 columns.
* **Latest session**: the maximum UTC date inside the lexicographically last
  `year=` file (none without files). Used by `load`, by the sync's reapply gate
  and by status.
* **Newest-n sessions**: walk year files newest first until at least n rows
  are in hand; the n most recent distinct UTC dates, ascending (fewer when the
  series is shorter). Used by the tail window.

## 6. Write semantics

| operation | who uses it | rule |
|---|---|---|
| **reconcile** (JDL-065 … JDL-068) | `sync` collector legs | Under the lock. Empty series → write all served rows (every year), no revisions. Otherwise, for each served row whose timestamp is stored: compare `open_raw, high_raw, low_raw, close_raw, volume_raw, adjusted_close` exactly (NaN == NaN); any difference → the served row replaces the stored row whole and one revision per differing column is recorded. Served rows with new timestamps are appended. Stored rows not served are untouched. Nothing replaced and nothing new → no write. Otherwise rewrite only the years of replaced/new rows (no prune). Returns (number of served bars, revisions). |
| **append** (JDL-141) | `load` | Under the lock. Existing ∪ incoming, existing wins on equal timestamps; rewrite only the incoming bars' years. Returns the number of incoming bars. |
| **overwrite** (JDL-070) | `import-csv`, yahoo-csv sync legs | Under the lock. The incoming rows (sorted, first of duplicate timestamps kept) replace the series; every present year written, then stale years pruned. Returns the number of CSV rows read. |
| **re-adjust** (JDL-069) | `adjust`, `load`, `sync` raw legs | Under the lock. Read the whole series (StoreError `nothing stored for {exchange}/{symbol}` when empty), adjust (adjustment.md), and when any cell differs from what was read, rewrite every year with prune; else write nothing. Returns the row count. Refuses split_adjusted series (adjustment.md §5). |

Revision record (JDL-067):
`{"date": "YYYY-MM-DD", "column": "<as-served column>", "stored": <float>, "served": <float>}`,
ordered by served row order, then column order as listed above. `served` is the
value as it would be stored (EODHD volume after raw-ization).

Frozen-first-seen: rows older than the requested window keep their first-seen
values only because the sync never requests them; a provider that serves rows
outside the requested window gets them reconciled like any other row
(JDL-066).

**Immutability.** No operation ever reads main OHLCV to compute main OHLCV: the
mains are always re-derived from `*_raw` (adjustment.md §4). `*_raw` and
`adjusted_close` change only when a reconcile replaces a row, an overwrite
import replaces the series, or an append adds a new timestamp.

## 7. Yahoo CSV import (JDL-070)

Input: a CSV with at least `Date, Open, High, Low, Close, Adj Close, Volume`
(else StoreError `{csv path}: not a 7-column Yahoo CSV, missing [...]`). Each
CSV row becomes the bar `{date: Date, open: Open, high: High, low: Low, close:
Close, adjusted_close: Adj Close, volume: Volume}` → overwrite, price_basis
`split_adjusted`, volume taken as served. Every row is kept (zero volume, NaN
cells). Extra columns are ignored.

## 8. Corporate-actions store (JDL-040 … JDL-044)

Files: `{store}/corporate_actions/{kind}/{SYMBOL}.json`, kind ∈ {`splits`,
`dividends`}, every `/` in SYMBOL replaced by `_`. Written as JSON with 2-space
indentation and a trailing newline, keys in this order:

```json
{
  "symbol": "SPLT.US",
  "exchange": "eodhd",
  "last_updated": "2026-10-23T09:46:26.863322Z",
  "splits": [
    {"date": "2024-01-17", "split": "3.000000/2.000000", "ratio": 1.5},
    {"date": "2024-02-01", "split": "7/1", "ratio": 7.0}
  ]
}
```

(the inner objects are indented like the rest; shown compact here). The
dividends file has the same envelope with `"dividends": [...]` holding the
provider entries verbatim, sorted by date.

* `last_updated` is the **real** wall-clock UTC time of the write, naive ISO
  8601 + `Z`; microseconds appear only when non-zero (JDL-043).
* Both files are written on every actions sync, splits first, by a plain
  truncating write (not atomic, no lock).
* Reading: an absent file is "no events" and "no stamp". The freshness stamp
  is always read from the **splits** file. `ratio` and `date` are read from the
  file; the split string is not re-parsed.
