# Refusal catalogue (decision table)

Every error the program raises to the user. "Wrapped" means the command
prints `{command}: {message}` on stderr and exits 1; "traceback" means the
error escapes the command (Python traceback whose last line is
`{module path}.{ErrorClass}: {message}` on stderr, exit 1); "leg" means the
error is contained by the sync: the leg is `FAILED` with detail
`{ErrorClass}: {message}`, the other legs run, the command exits 1.
Template notation: cli.md "General rules". The universe-location prefix
`{where}` is defined in universe.toml.md §4.

## Universe (raised while loading; wrapped by `sync`, `status`, `universe`)

| id | condition | message | req |
|---|---|---|---|
| U-01 | not valid TOML | `{origin}: not valid TOML: {tomllib message}` | JDL-013 |
| U-02 | unknown key at top / defaults / asset / source | `{where}: unknown key(s) {sorted list}; allowed: {sorted list}` | JDL-014 |
| U-03 | `defaults` not a table | `{origin}: [defaults] must be a table` | JDL-015 |
| U-04 | `asset` absent, empty or not an array | `{origin}: no [[asset]] entries` | JDL-015 |
| U-05 | an asset entry not a table | `asset #{n}: must be a table` | JDL-015 |
| U-06 | `source` absent, empty or not an array | `asset '{name}': needs at least one [[asset.source]]` | JDL-015 |
| U-07 | a source entry not a table | `asset '{name}' source #{n}: must be a table` | JDL-015 |
| U-08 | required key absent (name, asset_class, provider, symbol, path for yahoo-csv) | `{where}: missing required key '{key}'` | JDL-016 |
| U-09 | string key empty or not a string (store, currency, name, asset_class, provider, symbol, exchange, note, path) | `{where}: {key} must be a non-empty string, got {value!r}` | JDL-016 |
| U-10 | `enabled` not boolean | `{where}: enabled must be a boolean, got {value!r}` | JDL-016 |
| U-11 | `modeled` not boolean | `{where}: modeled must be a boolean, got {value!r}` | JDL-016 |
| U-12 | `threshold` boolean or non-number | `{where}: threshold must be a number (documentation only), got {value!r}` | JDL-016 |
| U-13 | `start`/`end` not a date | `{where}: {key} must be an ISO date (YYYY-MM-DD), got {value!r}` | JDL-016 |
| U-14 | asset_class unknown | `asset '{name}': unknown asset_class {value!r}; allowed: ['bond_etf', 'crypto', 'stock']` | JDL-017 |
| U-15 | provider unknown | `{where}: unknown provider {value!r}; allowed: ['eodhd', 'binance', 'yahoo-csv']` | JDL-017 |
| U-16 | kind not `eod` | `{where}: kind {value!r} is not supported - only ['eod']; a non-EOD load is a new data contract, not a config value` | JDL-017 |
| U-17 | eodhd symbol without `.` | `{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates and the crypto/raw basis split` | JDL-018 |
| U-18 | start/end on yahoo-csv | `{where}: start/end apply to collector sources only; a CSV import is whole-file` | JDL-019 |
| U-19 | path on eodhd/binance | `{where}: path applies to yahoo-csv sources only` | JDL-019 |
| U-20 | start > end | `{where}: start {start} is after end {end}` | JDL-019 |
| U-21 | modeled source disabled | `asset '{name}': a modeled source must be enabled` | JDL-020 |
| U-22 | ≥ 2 enabled modeled sources | `asset '{name}': exactly one enabled source may be modeled = true, got {k}` | JDL-020 |
| U-23 | enabled asset, ≥ 2 enabled sources, none modeled | `asset '{name}': {k} enabled sources but none marked modeled = true - the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)` | JDL-020 |
| U-24 | enabled asset, no enabled source | `asset '{name}': enabled but has no enabled source - nothing would feed the binning; to pause the asset, set enabled = false on the asset itself` | JDL-020 |
| U-25 | duplicate asset names | `{origin}: duplicate asset name(s) {sorted list}` | JDL-021 |
| U-26 | two assets claim one store coordinate | `{origin}: store series {exchange}/{symbol} is claimed by both {owner!r} and {other!r} - two assets may never write the same partition` | JDL-021 |
| U-27 | explicit universe path missing | traceback `FileNotFoundError: [Errno 2] No such file or directory: '{path}'` | JDL-022 |

## Selection (wrapped by `sync` and `status`)

| id | condition | message | req |
|---|---|---|---|
| S-01 | `sync --tail` < 1 (checked first) | `tail must be >= 1 session, got {tail}` | JDL-087 |
| S-02 | `--asset` names no universe asset | `unknown asset {name!r}; universe has {sorted names}` | JDL-085 |
| S-03 | `--provider` not a provider | `unknown provider {name!r}; allowed: ['eodhd', 'binance', 'yahoo-csv']` | JDL-085 |
| S-04 | no enabled leg survives | `selection matched no enabled asset/source legs` | JDL-085 |

## Leg failures (contained by `sync`; leg FAILED, run red, exit 1)

| id | condition | detail | req |
|---|---|---|---|
| L-01 | EODHD collector without key | `ValueError: EODHD API key required: pass api_key= or set EODHD_API_KEY` (each eodhd leg) | JDL-030 |
| L-02 | replayed request with no fixture | `CollectorError: no recorded fixture for GET {path} {params}` + listing | JDL-026 |
| L-03 | 429/5xx on all 5 attempts | `CollectorError: {label}: HTTP {status} after 5 attempts` | JDL-028 |
| L-04 | network failure on all 5 attempts | `CollectorError: {label}: network failure after 5 attempts: {error}` | JDL-028 |
| L-05 | other non-200 | `CollectorError: {label}: HTTP {status}: {body[:200], token as ***}` | JDL-028 |
| L-06 | 200 but not JSON | `CollectorError: {label}: response is not JSON: {body[:200]}` | JDL-028 |
| L-07 | bars response not a list | `CollectorError: eod {SYM}: expected a JSON list` / `CollectorError: klines {symbol}: expected a JSON list` | JDL-032, JDL-038 |
| L-08 | > 100 Binance pages | `CollectorError: pagination exceeded 100 pages - refusing to truncate silently; raise max_pages if the range is real` | JDL-038 |
| L-09 | bad split string | `ValueError: unparseable split string: {s!r}` / `ValueError: degenerate split string: {s!r}` | JDL-033 |
| L-10 | degenerate stored ratio | `AdjustmentRefused: split {date} has degenerate ratio {ratio!r}` | JDL-052 |
| L-11 | bar date unparseable | `StoreError: unparseable dates cannot be stored: {values}` | JDL-061 |
| L-12 | yahoo-csv file lacks columns | `StoreError: {path}: not a 7-column Yahoo CSV, missing {list}` | JDL-070 |
| L-13 | lock held > 300 s | `StoreError: {exchange}/{symbol}: another writer holds the store lock after 300s ({lock path})` | JDL-058 |
| L-14 | daily request budget spent | `DailyBudgetExhausted: daily API budget of 100000 spent ({date}); the per-minute window cannot lend quota across days` | JDL-023 |
| L-15 | yahoo-csv leg whose `path` does not exist (relative to the working directory) | `FileNotFoundError: [Errno 2] No such file or directory: '{path}'` | JDL-099 |

Not refusals (green, said loudly in the detail): the inverted window
(JDL-095) and the page-limit first fill (JDL-096).

## `load` declaration (wrapped, `load: `)

| id | condition | message | req |
|---|---|---|---|
| D-01 | no `--asset-type`, symbol not `.CC` | `{SYM}: asset_type is required (one of ['crypto', 'etf', 'stock']). The ticker carries no instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly like equities - so the old 'stock' default was a guess written into the store as a fact, and TLT is in this repo's universe as an explicit override because that guess got it wrong. Only EODHD's .CC crypto namespace is evidence enough to infer from` | JDL-142 |
| D-02 | `.CC` symbol declared etf/stock | `{SYM} is in EODHD's .CC crypto namespace but was declared asset_type={T!r}; that combination cannot be true, and guessing either way decides whether split adjustment runs on pre-adjusted prices (docs/DATA_CONTRACT.md §2)` | JDL-142 |
| D-03 | asset_type outside the vocabulary (reachable only below the CLI; the parser's choices catch it first, exit 2) | `unknown asset_type {T!r}; the store vocabulary is ['crypto', 'etf', 'stock'] (derived from the universe's own asset_class map, jef.data.universe.ASSET_TYPE_BY_CLASS)` | JDL-142 |

## Other commands

| id | command | condition | outcome | req |
|---|---|---|---|---|
| X-01 | differential | neither `--b-csv` nor `--b-symbol` | wrapped `differential: pass --b-csv or --b-symbol` | JDL-140 |
| X-02 | adjust | nothing stored | traceback `StoreError: nothing stored for {exchange}/{symbol}` | JDL-069 |
| X-03 | adjust | series is split_adjusted | traceback `AdjustmentRefused: price_basis ['split_adjusted'] is already adjusted at the provider - applying split events would double-adjust (docs/DATA_CONTRACT.md §2)` | JDL-051 |
| X-04 | export | series has no rows | traceback, no file written | JDL-138 |
| X-05 | import-csv | missing columns | traceback `StoreError: {csv}: not a 7-column Yahoo CSV, missing {list}` | JDL-070 |
| X-06 | load, sync-actions | no EODHD key | traceback `ValueError: EODHD API key required: pass api_key= or set EODHD_API_KEY` | JDL-030 |
| X-07 | load | pair symbol of unknown kind | traceback `CollectorError: cannot infer exchange for pair symbol {s!r}` | JDL-031 |
| X-08 | any | bad arguments | parser usage + error on stderr, exit 2 | JDL-133 |
| X-09 | export | series the store does not hold (revision 2026-10-23 (closing round): the exact outcome of X-04) | traceback whose last line is pandas' `AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?` (not a StoreError); exit 1, stdout empty, output file not written | JDL-159 |
| X-11 | differential | a stored side (A, or B via `--b-symbol`) the store does not hold (revision 2026-10-23 (wave 2): found by the DMN command × store-state table, measured on the original) | the same traceback as X-09; exit 1, stdout empty, `--output` file not written | JDL-163 |
| X-10 | any | bad arguments, exact form (revision 2026-10-23 (closing round)) | stderr: `usage: ` + the failing parser's usage, then `{prog}: error: {message}`; unrecognised arguments are reported by the top-level parser; exit 2 (cli.md "Parser surface") | JDL-161 |

## Chain

| id | condition | outcome | req |
|---|---|---|---|
| C-01 | JEF_S3_BUCKET unset/empty in the inner run | shell error ending `JEF_S3_BUCKET must name the venue bucket`, exit 1, nothing run | JDL-151 |
| C-02 | any stage exits non-zero | that stage still emits and puts its ledger lines, then the chain exits with that code; no store/runs publish | JDL-155, JDL-156, JDL-157, JDL-158 |
| C-03 | TERM (hard cap) | emit + put for the current stage with rc 143, exit 143 | JDL-153 |
