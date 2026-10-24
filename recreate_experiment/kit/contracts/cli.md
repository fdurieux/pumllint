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
  non-ASCII characters are escaped (`§` → `\u00a7`), floats in shortest
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
traceback, exit 1, F not written. (Revision 2026-10-23 (closing round): the traceback's last
line is exactly `AttributeError: Can only use .dt accessor with datetimelike
values. Did you mean: 'at'?` — requirement JDL-159, refusals.md
X-09.)

## differential

`jef-data differential --a-symbol S [--a-exchange eodhd] [--b-symbol S2]
[--b-exchange yahoo] [--b-csv F] [--tolerance 0.0001] [--output F2] [--store data]`

A = seam frame of a-exchange/S, label `{a-exchange}/{S}`. B = CSV F (label F)
when `--b-csv` is given, else seam frame of b-exchange/S2 (label
`{b-exchange}/{S2}`); neither → `differential: pass --b-csv or --b-symbol`,
exit 1. Prints the report (requirement JDL-083); with `--output` also
writes it plus a newline to F2. Exit 0 when the verdict is `within
tolerance, aligned`, else 1. A stored side the store does not hold (A, or
B via `--b-symbol`) → the traceback of export's X-09, exit 1, nothing on
stdout, F2 not written (revision 2026-10-23 (wave 2): requirement JDL-163,
refusals.md X-11).

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

<!-- revision 2026-10-23 (closing round): generated section, do not edit by hand -->

## Parser surface (revision 2026-10-23 (closing round))

Requirements JDL-160, JDL-161, JDL-162. This section fixes the declaration of the parser so that `--help` (contracts/cli_help.md) and the usage line of a parser error are reproducible byte for byte with Python's `argparse` under the pins (CPython 3.12, default `HelpFormatter`, terminal width 80: `COLUMNS=80`, or no terminal and `COLUMNS` unset).

### Top-level parser

| property | value |
|---|---|
| prog | `jef-data` (set explicitly, so it does not depend on how the program is launched) |
| description | the CLI module's docstring, quoted below; the default formatter reflows it |
| usage / epilog | not set (usage generated; no epilog) |
| formatter | the default `HelpFormatter` |
| `-h, --help` | the default help action |
| subcommands | one subparsers group: dest `command`, required, **no metavar, no title, no help** (so usage and help list the choices in braces); subcommands added in the order `validate`, `sync-actions`, `load`, `adjust`, `import-csv`, `export`, `differential`, `sync`, `status`, `universe` |
| subcommand parsers | created with a `help` string only: **no description**, no epilog; their prog is `jef-data <name>` |

The description (verbatim, including its line breaks, which the formatter reflows):

```text
Command-line driver for the data layer (jef-data).

Subcommands by phase (docs/DATA_LOADER_PLAN.md §4): D1 validate;
D2 sync-actions; D4 load / adjust / import-csv / export; D5 differential;
D6 universe; D7 sync (the whole configured universe in one command,
ordering ritual included - see jef.data.sync and src/jef/data/universe.toml).

Like jef-binning, this is a thin argparse shell over importable functions;
anything network- or Parquet-touching imports its module lazily so the core
install (no [data] extra) can still run `jef-data validate`.
```

### Subcommand help strings (shown in the top-level `--help`)

| subcommand | help |
|---|---|
| `validate` | `check a 7-column EOD CSV against docs/DATA_CONTRACT.md` |
| `sync-actions` | `fetch splits + dividends from EODHD into the actions store (needs EODHD_API_KEY; run BEFORE load)` |
| `load` | `fetch EOD history from EODHD into the Parquet store (incremental; needs EODHD_API_KEY; sync-actions first)` |
| `adjust` | `re-derive main OHLCV from *_raw + stored splits (offline, idempotent; also the repair path)` |
| `import-csv` | `import a Yahoo 7-column CSV verbatim (price_basis=split_adjusted; offline)` |
| `export` | `store -> 7-column contract CSV (values identical; the bit-exact consumer path is jef.binning.loading.load_eod_store)` |
| `differential` | `tolerance-based comparison of two series (store vs store, or store vs a 7-column CSV) - the cross-provider gate; exit 1 on findings` |
| `sync` | `run the whole universe's acquisition ritual from the config (per raw-basis symbol: sync-actions BEFORE load; tail-refresh reconcile once a series exists, crypto end-guarded at the previous UTC day; EODHD legs need EODHD_API_KEY)` |
| `status` | `read-only daily health: staleness, phantom-split scan, actions freshness, today-dated bars, price resolution, and the cross-venue close spread for multi-feed assets (offline, no key; exit 1 on any alert - the scheduler chain is sync && status)` |
| `universe` | `show the configured universe (assets, sources, thresholds; the D6 pilot by default)` |

### Options of each subcommand

Metavar as printed: the upper-cased dest unless the table names one; an option with choices prints its choices in braces. `help` is shown after argparse's `%` interpolation (a literal `%` is written `%%` in an argparse help string, e.g. the `0.5%%` of `--spread-threshold`). Options appear in usage and help in table order.

#### `validate` (prog `jef-data validate`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `(positional)` | `csv` | `csv` | store | str | None | yes | — | `CSV in the Yahoo 7-column schema` |
| `--min-rows` | `min_rows` | `MIN_ROWS` | store | `int` | `1115` | no | — | `advisory minimum clean-row count` |

#### `sync-actions` (prog `jef-data sync-actions`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--symbol` | `symbol` | `SYMBOL` | store | str | None | yes | — | `e.g. AAPL.US` |
| `--store` | `store` | `STORE` | store | str | `data` | no | — | `store root (default: data/, gitignored)` |
| `--base-url` | `base_url` | `BASE_URL` | store | str | `https://eodhd.com/api` | no | — | — |

#### `load` (prog `jef-data load`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--symbol` | `symbol` | `SYMBOL` | store | str | None | yes | — | — |
| `--store` | `store` | `STORE` | store | str | `data` | no | — | — |
| `--from` | `from` | `FROM` | store | str | None | no | — | `YYYY-MM-DD (default: incremental from the last stored session)` |
| `--to` | `to` | `TO` | store | str | None | no | — | — |
| `--asset-type` | `asset_type` | `{crypto,etf,stock}` | store | str | None | no | `crypto,etf,stock` | `required, except for EODHD .CC symbols (the crypto namespace is evidence); a ticker is not` |
| `--currency` | `currency` | `CURRENCY` | store | str | `USD` | no | — | — |
| `--base-url` | `base_url` | `BASE_URL` | store | str | `https://eodhd.com/api` | no | — | — |

#### `adjust` (prog `jef-data adjust`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--symbol` | `symbol` | `SYMBOL` | store | str | None | yes | — | — |
| `--exchange` | `exchange` | `EXCHANGE` | store | str | `eodhd` | no | — | — |
| `--store` | `store` | `STORE` | store | str | `data` | no | — | — |

#### `import-csv` (prog `jef-data import-csv`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--csv` | `csv` | `CSV` | store | str | None | yes | — | — |
| `--symbol` | `symbol` | `SYMBOL` | store | str | None | yes | — | — |
| `--exchange` | `exchange` | `EXCHANGE` | store | str | `yahoo` | no | — | — |
| `--asset-type` | `asset_type` | `{crypto,etf,stock}` | store | str | None | yes | `crypto,etf,stock` | `required: a Yahoo CSV carries no instrument type` |
| `--currency` | `currency` | `CURRENCY` | store | str | `USD` | no | — | — |
| `--store` | `store` | `STORE` | store | str | `data` | no | — | — |

#### `export` (prog `jef-data export`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--symbol` | `symbol` | `SYMBOL` | store | str | None | yes | — | — |
| `--exchange` | `exchange` | `EXCHANGE` | store | str | `eodhd` | no | — | — |
| `--output` | `output` | `OUTPUT` | store | str | None | yes | — | — |
| `--store` | `store` | `STORE` | store | str | `data` | no | — | — |

#### `differential` (prog `jef-data differential`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--a-symbol` | `a_symbol` | `A_SYMBOL` | store | str | None | yes | — | — |
| `--a-exchange` | `a_exchange` | `A_EXCHANGE` | store | str | `eodhd` | no | — | — |
| `--b-symbol` | `b_symbol` | `B_SYMBOL` | store | str | None | no | — | — |
| `--b-exchange` | `b_exchange` | `B_EXCHANGE` | store | str | `yahoo` | no | — | — |
| `--b-csv` | `b_csv` | `B_CSV` | store | str | None | no | — | `compare against a CSV instead of a stored series` |
| `--tolerance` | `tolerance` | `TOLERANCE` | store | `float` | `0.0001` | no | — | `relative tolerance per cell (default 1e-4)` |
| `--output` | `output` | `OUTPUT` | store | str | None | no | — | `also write the report here` |
| `--store` | `store` | `STORE` | store | str | `data` | no | — | — |

#### `sync` (prog `jef-data sync`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--universe` | `universe` | `UNIVERSE` | store | str | None | no | — | `universe TOML (default: the packaged src/jef/data/universe.toml)` |
| `--store` | `store` | `STORE` | store | str | None | no | — | `store root (default: the universe's defaults.store)` |
| `--asset` | `asset` | `ASSET` | append (repeatable) | str | None | no | — | `limit to this asset name (repeatable)` |
| `--provider` | `provider` | `PROVIDER` | append (repeatable) | str | None | no | — | `limit to this provider (repeatable), e.g. --provider eodhd where Binance is unreachable` |
| `--dry-run` | `dry_run` | `(none)` | store_true | — | `False` | no | — | `plan from local store state only - no network, no key needed` |
| `--tail` | `tail` | `TAIL` | store | `int` | `10` | no | — | `tail-refresh window in sessions, minimum 1 (docs/DATA_CONTRACT.md §7.2; default 10): newest-wins inside, frozen-first-seen outside` |
| `--force-actions` | `force_actions` | `(none)` | store_true | — | `False` | no | — | `sync corporate actions even when fresh (override the once-per-UTC-day gate)` |
| `--base-url` | `base_url` | `BASE_URL` | store | str | None | no | — | `EODHD base URL override` |
| `--summary-json` | `summary_json` | `PATH` | store | str | None | no | — | `write the per-leg results as JSON (the event ledger's stage_outcome diagnostics, Arc A A3(a)); written on red runs too` |

#### `status` (prog `jef-data status`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--universe` | `universe` | `UNIVERSE` | store | str | None | no | — | `universe TOML (default: the packaged one)` |
| `--store` | `store` | `STORE` | store | str | None | no | — | `store root (default: the universe's defaults.store)` |
| `--asset` | `asset` | `ASSET` | append (repeatable) | str | None | no | — | `limit to this asset name (repeatable)` |
| `--provider` | `provider` | `PROVIDER` | append (repeatable) | str | None | no | — | `limit to this provider (repeatable)` |
| `--staleness` | `staleness` | `STALENESS` | store | `int` | `2` | no | — | `alert at this many missed expected sessions (docs/DATA_CONTRACT.md §7.4; default 2)` |
| `--jump-threshold` | `jump_threshold` | `JUMP_THRESHOLD` | store | `float` | `0.4` | no | — | `phantom-split one-day |return| alert threshold (default 0.40)` |
| `--window` | `window` | `WINDOW` | store | `int` | `10` | no | — | `newest sessions scanned for jumps, and for the cross-venue common session (default 10)` |
| `--resolution-window` | `resolution_window` | `RESOLUTION_WINDOW` | store | `int` | `500` | no | — | `newest TRADED sessions measured for price resolution - zero-volume rows drop first, like the seam (docs/DATA_CONTRACT.md §7.8; default 500)` |
| `--resolution-k` | `resolution_k` | `RESOLUTION_K` | store | `float` | `0.2` | no | — | `note a coarse quoting grid below this distinct-close/session ratio (default 0.20)` |
| `--flat-k` | `flat_k` | `FLAT_K` | store | `float` | `0.25` | no | — | `note a coarse/frozen feed above this share of sessions whose close did not move (default 0.25)` |
| `--gap-k` | `gap_k` | `GAP_K` | store | `int` | `5` | no | — | `note a post-seam continuity gap at or above this many absent expected sessions (default 5, calibrated: the largest true US closure since 1962 measures 4 - 2001-09-10..17 - so the market itself never notes; a provider data hole does, however it is served)` |
| `--spread-threshold` | `spread_threshold` | `SPREAD_THRESHOLD` | store | `float` | `0.005` | no | — | `cross-venue close-spread WARN threshold for assets with 2+ live feeds (Arc X X1; default 0.005 = 0.5%, calibrated on the committed fixtures - docs/CROSS_VENUE_PLAN.md)` |
| `--spread-alerts` | `spread_alerts` | `(none)` | store_true | — | `False` | no | — | `promote a cross-venue spread breach from a warning to an ALERT, so it joins the exit-1 contract (off by default: it compares a CROSS-CHECK leg, and exit 1 stops the venue's day before it publishes anything)` |
| `--json` | `json` | `(none)` | store_true | — | `False` | no | — | `machine-readable report instead of the table` |

#### `universe` (prog `jef-data universe`)

| option | dest | metavar shown | action | type | default | required | choices | help |
|---|---|---|---|---|---|---|---|---|
| `-h, --help` | `help` | `(none)` | help | — | — | no | — | `show this help message and exit` |
| `--universe` | `universe` | `UNIVERSE` | store | str | None | no | — | `universe TOML (default: packaged)` |

### Parser errors

A parse failure prints, on stderr, `usage: ` followed by the failing parser's formatted usage (wrapped at the terminal width), then `{prog}: error: {message}`, and exits 2; stdout stays empty. Arguments no parser recognises are reported by the top-level parser even after a valid subcommand, so they print the TOP-LEVEL usage and `jef-data: error: unrecognized arguments: ...`. Examples (80 columns):

```text
$ jef-data
usage: jef-data [-h]
                {validate,sync-actions,load,adjust,import-csv,export,differential,sync,status,universe}
                ...
jef-data: error: the following arguments are required: command

$ jef-data export --symbol X
usage: jef-data export [-h] --symbol SYMBOL [--exchange EXCHANGE] --output
                       OUTPUT [--store STORE]
jef-data export: error: the following arguments are required: --output
```

<!-- end of the revision 2026-10-23 (closing round) generated section -->
