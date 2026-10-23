# Corporate-actions arithmetic: basis resolution and the split adjustment

Requirements: JDL-045, JDL-046, JDL-047, JDL-048,
JDL-049, JDL-050, JDL-051, JDL-052,
JDL-053, JDL-054, JDL-055,
JDL-056; split parsing JDL-033.

All arithmetic is IEEE-754 binary64 (float64), performed in exactly the order
written here. Exactness matters: the harness compares stored cells bit for bit.

## 1. Basis resolution (decided once per write, never configurable)

### Price basis

| provider | declared asset_class → asset_type | price_basis | split events applied |
|---|---|---|---|
| `eodhd` | `stock` → `stock` | `raw` | yes (stored splits of the symbol) |
| `eodhd` | `bond_etf` → `etf` | `raw` | yes |
| `eodhd` | `crypto` → `crypto` | `split_adjusted` | never |
| `binance` | any | `split_adjusted` | never |
| `yahoo-csv` (and `import-csv`) | any | `split_adjusted` | never |
| `load` (hand-run, EODHD) | the `--asset-type` declaration (cli.md) | `split_adjusted` for `crypto`, else `raw` | yes for raw |

The symbol suffix never decides the basis: `X.CC` declared `stock` is raw and
actions-eligible; `WEIRD.XX` declared `crypto` is pre-adjusted.

### Volume basis

| price_basis | collector volume basis | stored `volume_raw` |
|---|---|---|
| `raw` | EODHD: `split_adjusted` | served volume ÷ F (raw-ized, §3) |
| `raw` | `raw` (any other collector) | served volume |
| `split_adjusted` | any | served volume (the collector's basis is not consulted) |

## 2. Split events

A split event is `(date, ratio, split string)`: `date` is the effective date
(the first session at the new basis); `ratio` = new shares / old shares. From
the provider string `NEW/OLD` (two float fields separated by exactly one `/`):
`4/1` → 4.0, `7.000000/1.000000` → 7.0, `3.000000/2.000000` → 1.5,
`1/10` → 0.1 (a reverse split). A string that does not split into two floats
fails with `unparseable split string: '<s>'`; a zero on either side with
`degenerate split string: '<s>'` (both ValueError, which fails the sync leg).

Events are stored sorted ascending by date and applied in that stored order.

## 3. The factor

For a row with UTC calendar date `d`:

```
F(d) = 1.0
for each split event e in stored order:
    if d < e.date:            # strictly before: a row ON e.date is already at the new basis
        F(d) = F(d) * e.ratio
```

A ratio that is non-finite or ≤ 0 refuses the whole adjustment:
`split {date} has degenerate ratio {ratio!r}` (AdjustmentRefused).

### Raw-ization of served EODHD volume (raw basis only)

```
volume_raw = served_volume / F(d)          # F from the splits known at ingest
```

## 4. The adjustment pass (pure)

Input: a frame holding `open_raw, high_raw, low_raw, close_raw, volume_raw,
datetime` (+ any other columns) and the split events. Output: a new frame;
every other column is carried unchanged.

```
open  = open_raw  / F(d)
high  = high_raw  / F(d)
low   = low_raw   / F(d)
close = close_raw / F(d)
volume = volume_raw * F(d)
cumulative_split_factor = F(d)
```

Properties that follow and are observable:

* **Fixed point** — adjusting the stored series again with the same events
  changes nothing (and the store then writes nothing).
* **Re-derivation** — after the event list changes (a split synced later, or
  an events file edited), every main column of the whole series is recomputed
  from `*_raw`; `volume_raw` itself is NOT recomputed for rows outside a
  reconcile, so a split that was unknown at a row's ingest leaves that row's
  `volume_raw` at the value raw-ized with the old factor (§6 example 3).
* **No compounding** — the mains are never read.
* **Dividends never enter** (JDL-050).

Refusals: any `price_basis` value other than `raw` in the frame →
`price_basis ['split_adjusted'] is already adjusted at the provider - applying
split events would double-adjust (docs/DATA_CONTRACT.md §2)` (the bracket lists
the sorted non-raw values); a missing raw column or `datetime` →
`cannot adjust without immutable raw columns: missing [...]`.

## 5. Pre-adjusted series

price_basis `split_adjusted`: mains = `*_raw` = served values, volume = served,
`cumulative_split_factor` = 1.0, and the adjustment pass refuses the series
forever (the `adjust` command fails with the refusal above).

## 6. Worked examples (synthetic, the scenarios' fixtures)

### Example 1 — two-split equity `SPLT.US`, rows on and around the split dates

Events: 2024-01-17 ratio 1.5 (`3.000000/2.000000`), 2024-02-01 ratio 7.0 (`7/1`).

| date | F | close_raw | close = close_raw/F | served vol | volume_raw = vol/F | volume = volume_raw×F |
|---|---|---|---|---|---|---|
| 2024-01-02 | 10.5 | 210.0 | 20.0 | 100000 | 9523.809523809523 | 99999.99999999999 |
| 2024-01-16 | 10.5 | 215.25 | 20.5 | 110000 | 10476.190476190477 | 110000.00000000001 |
| 2024-01-17 (on split 1) | 7.0 | 143.85 | 20.55 | 111000 | 15857.142857142857 | 111000.0 |
| 2024-01-31 | 7.0 | 147.35 | 21.05 | 121000 | 17285.714285714286 | 121000.0 |
| 2024-02-01 (on split 2) | 1.0 | 21.1 | 21.1 | 122000 | 122000.0 | 122000.0 |

The factor is `1.0 × 1.5 × 7.0`, multiplied in that order.

### Example 2 — ETF with dividends, no splits `DIVY.US`

No split events: F = 1.0 on every row, mains = raws, `cumulative_split_factor`
= 1.0, price_basis `raw` (an ETF is raw basis even without splits). Three
dividends are stored verbatim and change nothing; the provider's
`adjusted_close` (lower than close before each dividend) is carried, and
`adjustment_factor` = adjusted_close / close_raw (e.g. 94.37 / 95.0 =
0.9933684210526317 on 2024-03-01).

### Example 3 — a split synced after the first fill

First fill knew only the 3:2 split (row 2024-01-02: F = 1.5, `volume_raw` =
100000 / 1.5 = 66666.66666666667). A later run learns the 7:1 split and
re-adjusts the whole series with both: row 2024-01-02 now has F = 10.5, close
= 210.0 / 10.5 = 20.0, and volume = 66666.66666666667 × 10.5 = 700000.0 —
seven times the served value, because that row's `volume_raw` was raw-ized
with the old factor and lies outside the tail window that the second run
re-fetched. Rows inside the tail (2024-01-30, 2024-01-31) are re-served, their
`volume_raw` revised (120000 → 17142.85714285714) and their volume correct.
This is why corporate actions must be synced before the first load of a
split-history symbol.
