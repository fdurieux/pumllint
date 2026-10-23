# The command line: `jef-data`

Console script `jef-data` (also runnable as a module), an argparse-style
parser with ten subcommands. Requirements: JDL-133 … JDL-145,
JDL-131, JDL-132, JDL-103, JDL-104.

General rules:

* Exit codes: **0** success; **1** a finding (validation errors, differential
  findings, status alerts, failed sync legs), a wrapped refusal, or any
  unhandled error (Python traceback on stderr); **2** an argument error from the
  parser (usage text + `jef-data <cmd>: error: ...` on stderr).
* A *wrapped refusal* prints exactly `{command}: {message}` on stderr, nothing
  on stdout, exit 1 (`{command}` ∈ `sync`, `status`, `universe`, `load`,
  `differential`). Everything else that goes wrong is unwrapped (traceback).
* Every line below goes to stdout unless stated otherwise.
* JSON documents are written with Python's `json` defaults otherwise:
  non-ASCII characters are escaped (`§` → `§`), floats in shortest
  round-trip form, `NaN` for NaN.
* `{x!r}` means Python repr; `{x:g}`, `{x:.4%}`, `{x:+.1%}`, `{x:>6}` are Python
  format specifications (`:g` = 6 significant digits, trailing zeros removed;
  `.4%` = ×100 with 4 decimals and `%`; `>6` = right-aligned in 6 columns).

## validate

`jef-data validate CSV [--min-rows N]` (N: int, default 1115)

Reads CSV with default CSV parsing. Prints `{CSV}: {n} rows` (always
`rows`), then the validation report (seam_frame.md §4). Exit 0 if no error
else 1.

## sync-actions

`jef-data sync-actions --symbol S [--store data] [--base-url https://eodhd.com/api]`

Constructs the EODHD collector (key from EODHD_API_KEY; missing → traceback,
exit 1), syncs S's corporate actions (store.md §8), closes the collector,
prints `{S}: {k} split(s), {d} dividend(s) -> {store}/corporate_actions/`,
exit 0.

## load

`jef-data load --symbol S [--store data] [--from YYYY-MM-DD] [--to YYYY-MM-DD]
[--asset-type {crypto,etf,stock}] [--currency USD] [--base-url https://eodhd.com/api]`

1. Construct the EODHD collector (missing key → traceback, exit 1).
2. Normalise S (collectors.md §2) → SYM; `.CC` suffix = crypto namespace.
3. Declaration: none + not `.CC` → refusal; none + `.CC` → crypto;
   `.CC` + not crypto → refusal (refusals.md R-LOAD-*). Basis: crypto →
   `split_adjusted`, else `raw`.
4. Start = `--from`, else (series exchange tag `eodhd`, symbol SYM has rows)
   the day after its latest stored session, else none; end = `--to`.
5. Fetch bars; read stored splits (raw basis only); append them (store.md §6,
   EODHD volume raw-ized for raw basis); when raw and (bars were ingested or
   the series already had rows) re-adjust the whole series.
6. Print `{S}: {n} bar(s) ingested -> {store}/market_data/`, exit 0.

Refusals print `load: {message}` (exit 1) after closing the collector and
before any fetch or write.

## adjust

`jef-data adjust --symbol S [--exchange eodhd] [--store data]`

Re-adjusts exchange/S with the stored splits of S (store.md §6). Prints
`{exchange}/{S}: {rows} row(s) re-derived from *_raw with {k} split(s)`, exit
0. Empty series (StoreError) or split_adjusted series (AdjustmentRefused) →
traceback, exit 1.

## import-csv

`jef-data import-csv --csv F --symbol S [--exchange yahoo] --asset-type {crypto,etf,stock} [--currency USD] [--store data]`

Imports F (store.md §7) into exchange/S. Prints
`{F}: {rows} row(s) -> {store}/market_data/exchange={exchange}/symbol={S}/ (price_basis=split_adjusted)`,
exit 0. Missing columns → traceback (StoreError), exit 1.

## export

`jef-data export --symbol S [--exchange eodhd] --output F [--store data]`

Writes the seam frame (seam_frame.md) of exchange/S to F (header, no index),
prints `{exchange}/{S}: {n} row(s) -> {F}` then the validation report of the
frame, exit 0 if the report has no error else 1. A series with no rows →
traceback, exit 1, F not written.

## differential

`jef-data differential --a-symbol S [--a-exchange eodhd] [--b-symbol S2]
[--b-exchange yahoo] [--b-csv F] [--tolerance 0.0001] [--output F2] [--store data]`

A = seam frame of a-exchange/S, label `{a-exchange}/{S}`. B = CSV F (label F)
when `--b-csv` is given, else seam frame of b-exchange/S2 (label
`{b-exchange}/{S2}`); neither → `differential: pass --b-csv or --b-symbol`,
exit 1. Prints the report (requirement JDL-083); with `--output` also
writes it plus a newline to F2. Exit 0 when the verdict is `within
tolerance, aligned`, else 1.

## sync

`jef-data sync [--universe P] [--store P] [--asset A]... [--provider P]...
[--dry-run] [--tail N (int, default 10)] [--force-actions] [--base-url URL]
[--summary-json PATH]`

* `--universe` default: the packaged universe; `--store` default: the
  universe's `defaults.store`; `--asset`/`--provider` repeatable filters.
* Output: the run log (requirement JDL-103) or the dry-run plan
  (JDL-104, JDL-105). Example (real run):

```
ok      SPLT eodhd/SPLT.US [eodhd]: actions fresh; 11 bar(s), 3 revised cell(s)
        revised 2024-02-08 close_raw: 21.35 -> 21.31
        revised 2024-02-08 adjusted_close: 21.2432 -> 21.2
        revised 2024-02-09 volume_raw: 128000 -> 777777
1 leg(s), 0 failed -> store 'data'
```

  Dry run:

```
plan for store 'dstore' (4 leg(s)):
    CSVA yahoo/CSVA: import t.csv (whole file, idempotent)
      EQ eodhd/EQ.US: sync-actions + load (first fill from 2024-01-02 to 2024-03-01)
      CC eodhd/CC-USD.CC: load (first fill, full history to 2026-10-22)
      CC binance/CCUSDT: load (first fill, full history to 2026-10-22)
```

* `--summary-json PATH`: after the run returns (green, red or dry run), write
  the summary document (sync_summary.schema.json) with `indent=1`,
  `sort_keys=True`, then `\n`. Not written on a refusal.
* Exit: 0 when every leg is ok, 1 when any leg failed; refusals
  (`sync: {message}`, exit 1): universe errors, filter errors, `tail must be
  >= 1 session, got {N}`.

## status

`jef-data status [--universe P] [--store P] [--asset A]... [--provider P]...
[--staleness 2] [--jump-threshold 0.40] [--window 10] [--resolution-window 500]
[--resolution-k 0.20] [--flat-k 0.25] [--gap-k 5] [--spread-threshold 0.005]
[--spread-alerts] [--json]`

(int: staleness, window, resolution-window, gap-k; float: the others.) The
corporate-actions freshness threshold (2 refresh sessions) is not a flag.

* `--json`: print the envelope (status.schema.json) with `indent=1`, keys in
  schema order (not sorted).
* Otherwise the table (requirement JDL-132). Example:

```
ALERT     EQ eodhd/EQ.US: last -, - missed, 0 row(s)
        ALERT never filled - no stored rows (jef-data sync first)
        note  declared class: no vendor classification recorded - run tools/record_classifications.py
ok        CC cross-venue eodhd/CC-USD.CC vs binance/CCUSDT
        note  eodhd/CC-USD.CC has no stored rows - spread not measured
3 source(s), 1 venue pair(s), 3 alert(s)
```

  (`ok   ` and `WARN ` are padded to 5 characters; the asset is right-aligned
  in 6; a measured resolution adds `        res   {distinct} distinct /
  {sessions} traded, min tick {min_tick:.4%} or n/a, {flat_share:.2%} flat`
  right after the source line.)
* Exit 1 iff alerts_total > 0. Refusals: `status: {message}`, exit 1.

## universe

`jef-data universe [--universe P]` — prints the listing of
universe.toml.md §6, exit 0; refusals `universe: {message}`, exit 1.
