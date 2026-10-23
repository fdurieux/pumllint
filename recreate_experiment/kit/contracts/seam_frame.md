# The exported frame (the seam frame) and how a bar becomes it

The program's output to its downstream consumer is the **seam frame**: the
7-column EOD frame that `jef-data export` writes as CSV and that the harness
function `export_frame` returns before CSV. This file fixes its shape and the
transform that produces it, step by step, from a provider bar.

Requirements: JDL-071, JDL-072, JDL-073,
JDL-074, JDL-075; validation of the frame JDL-076 …
JDL-081.

## 1. Columns, dtypes, order

| # | Column | dtype | Source in the stored row (store.md §3) |
|---|---|---|---|
| 1 | `Date` | text (`str`) | UTC calendar date of `datetime`, formatted `YYYY-MM-DD` |
| 2 | `Open` | float64 | `open` (the adjusted main column) |
| 3 | `High` | float64 | `high` |
| 4 | `Low` | float64 | `low` |
| 5 | `Close` | float64 | `close` |
| 6 | `Adj Close` | float64 | `adjusted_close` (the provider's splits+dividends close) |
| 7 | `Volume` | int64 **or** float64 | `volume` (the adjusted main column) |

* Rows: exactly the stored rows of the series, in stored order (ascending
  `timestamp`, store.md §5), index `0..n-1`. Nothing is dropped, filtered,
  re-sorted or de-duplicated here.
* `Volume` dtype rule (JDL-072): int64 when the series has at least
  one row and **every** volume is finite and has no fractional part; otherwise
  float64 with the values untouched. One volume of `99999.99999999999` (see the
  worked example) makes the whole column float64.
* An empty series cannot be exported (the command fails, see cli.md `export`).
* In the CSV written by `export`, a NaN cell is an empty field and floats use
  the shortest repr that round-trips (`100000.0`, `19.84952380952381`).

## 2. The transform, step by step

A bar travels through four representations. Each step is defined in exactly one
contract; this section strings them together.

1. **Provider bar** (collectors.md §3 / §4): `{date, open, high, low, close,
   adjusted_close, volume}` as served.
2. **Basis resolution** (adjustment.md §1): the store decides `price_basis`
   (`raw` or `split_adjusted`) from provider + declared asset_type, and whether
   volume must be raw-ized (EODHD volume is served split-adjusted).
3. **Stored row** (store.md §3 and adjustment.md §2-§4):
   `*_raw` = as served (volume raw-ized when required), main OHLCV derived from
   `*_raw` and the split events, `cumulative_split_factor`, `adjusted_close`,
   `adjustment_factor`, `timestamp`, `datetime`, labels.
4. **Seam frame** (§1 above): the projection of the stored row.

## 3. Worked example (synthetic equity `SPLT.US`, two splits)

Declared `asset_class = "stock"` → asset_type `stock`, provider `eodhd` →
price_basis `raw`, collector volume basis `split_adjusted` → volume raw-ized.

Split events stored for the symbol (adjustment.md §2):

| date | split | ratio |
|---|---|---|
| 2024-01-17 | `3.000000/2.000000` | 1.5 |
| 2024-02-01 | `7/1` | 7.0 |

Factor F per row (product of ratios of splits strictly after the row's date,
multiplied left to right in stored order starting from 1.0):

| row date | splits after it | F |
|---|---|---|
| 2024-01-02 … 2024-01-16 | both | 1.0 × 1.5 × 7.0 = 10.5 |
| 2024-01-17 (on split 1) … 2024-01-31 | 7:1 only | 7.0 |
| 2024-02-01 (on split 2) onwards | none | 1.0 |

### Row 2024-01-02

Provider bar: `{"date": "2024-01-02", "open": 207.9, "high": 212.1, "low":
205.8, "close": 210.0, "adjusted_close": 19.9, "volume": 100000}`

| Step | Cell | Value (exact float64 repr) |
|---|---|---|
| store | `timestamp` | `1704153600` (Unix **seconds** of 2024-01-02T00:00Z, store.md §3) |
| store | `datetime` | `2024-01-02 00:00:00+00:00` |
| store | `open_raw`, `high_raw`, `low_raw`, `close_raw` | `207.9`, `212.1`, `205.8`, `210.0` |
| store | `volume_raw` | 100000 / 10.5 = `9523.809523809523` |
| store | `cumulative_split_factor` | `10.5` |
| store | `open`, `high`, `low`, `close` | 207.9/10.5 = `19.8`, `20.2`, `19.6`, `20.0` |
| store | `volume` | 9523.809523809523 × 10.5 = `99999.99999999999` |
| store | `adjusted_close` | `19.9` |
| store | `adjustment_factor` | 19.9 / 210.0 = `0.09476190476190476` |
| seam | `Date, Open, High, Low, Close, Adj Close, Volume` | `2024-01-02, 19.8, 20.2, 19.6, 20.0, 19.9, 99999.99999999999` |

### Row 2024-01-17 (dated ON the 3:2 split)

Provider bar: open 142.41, high 145.29, low 140.97, close 143.85,
adjusted_close 20.4473, volume 111000. F = 7.0 (the 3:2 split does not count).

`volume_raw` = 111000/7 = `15857.142857142857`, `volume` = `111000.0`,
`open` = `20.344285714285714`, `high` = `20.755714285714284`, `low` =
`20.138571428571428`, `close` = `20.55`, `adjustment_factor` =
`0.14214320472714634`.

### Row 2024-02-01 (dated ON the 7:1 split)

F = 1.0: every main column equals its raw twin (`21.1` close, `122000.0`
volume), `adjustment_factor` = 20.9945 / 21.1 = `0.9949999999999999`.

Because row 2024-01-02's volume is non-integral, the exported `Volume` column of
`SPLT.US` is float64; the ETF example (`DIVY.US`, no splits, F = 1.0 on every
row) exports int64.

## 4. Validation of the frame

`jef-data validate` (on a CSV) and `jef-data export` (on the frame it just
wrote) run the same validation. The checks, their messages and their order are
requirements JDL-076, JDL-077, JDL-078, JDL-079,
JDL-080; the rendering is JDL-081. In run order:

1. required columns present (else one error, stop);
2. extra columns (note);
3. numeric coercion of Open, High, Low, Close, Adj Close, Volume (one error
   listing the non-numeric columns);
4. Date parsing (error and stop when none parses; note for some);
5. duplicate parsed dates (error);
6. ascending order of parsed dates (note);
7. only when no column is non-numeric: negative prices (error), negative
   Volume (error), High < Low (error), zero-volume rows (note), NaN rows
   (note), clean-row count below the minimum (note).

Errors render first, then notes (`ERROR: ` / `note:  `), or `contract: clean`.

## 5. What the downstream seam does with it (prose only)

The consumer of this frame lives outside the program (JDL-074). As
the validation notes announce, it sorts by date, drops unparseable dates,
drops zero-volume rows and drops any row with a NaN. The program does **not**
apply this policy anywhere in the export; the status command emulates the
zero-volume/NaN drop for its resolution and continuity measurements only
(status requirements JDL-122, JDL-120).
