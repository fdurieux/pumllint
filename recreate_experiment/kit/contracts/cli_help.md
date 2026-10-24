# `--help` output, verbatim (revision 2026-10-23 (closing round))

Requirement JDL-162. Each block is exactly what the subject prints on stdout for the command in its heading, captured with `COLUMNS=80` (identical to running with no terminal and `COLUMNS` unset); the command exits 0 and prints nothing on stderr. Every block ends with a newline that the fence hides. The help depends on the terminal width (argparse wraps at `COLUMNS` - 2), so the scenarios run with `COLUMNS=80`. The parser declaration that produces these texts is cli.md "Parser surface".

## `jef-data --help`

```text
usage: jef-data [-h]
                {validate,sync-actions,load,adjust,import-csv,export,differential,sync,status,universe}
                ...

Command-line driver for the data layer (jef-data). Subcommands by phase
(docs/DATA_LOADER_PLAN.md §4): D1 validate; D2 sync-actions; D4 load / adjust
/ import-csv / export; D5 differential; D6 universe; D7 sync (the whole
configured universe in one command, ordering ritual included - see
jef.data.sync and src/jef/data/universe.toml). Like jef-binning, this is a
thin argparse shell over importable functions; anything network- or Parquet-
touching imports its module lazily so the core install (no [data] extra) can
still run `jef-data validate`.

positional arguments:
  {validate,sync-actions,load,adjust,import-csv,export,differential,sync,status,universe}
    validate            check a 7-column EOD CSV against docs/DATA_CONTRACT.md
    sync-actions        fetch splits + dividends from EODHD into the actions
                        store (needs EODHD_API_KEY; run BEFORE load)
    load                fetch EOD history from EODHD into the Parquet store
                        (incremental; needs EODHD_API_KEY; sync-actions first)
    adjust              re-derive main OHLCV from *_raw + stored splits
                        (offline, idempotent; also the repair path)
    import-csv          import a Yahoo 7-column CSV verbatim
                        (price_basis=split_adjusted; offline)
    export              store -> 7-column contract CSV (values identical; the
                        bit-exact consumer path is
                        jef.binning.loading.load_eod_store)
    differential        tolerance-based comparison of two series (store vs
                        store, or store vs a 7-column CSV) - the cross-
                        provider gate; exit 1 on findings
    sync                run the whole universe's acquisition ritual from the
                        config (per raw-basis symbol: sync-actions BEFORE
                        load; tail-refresh reconcile once a series exists,
                        crypto end-guarded at the previous UTC day; EODHD legs
                        need EODHD_API_KEY)
    status              read-only daily health: staleness, phantom-split scan,
                        actions freshness, today-dated bars, price resolution,
                        and the cross-venue close spread for multi-feed assets
                        (offline, no key; exit 1 on any alert - the scheduler
                        chain is sync && status)
    universe            show the configured universe (assets, sources,
                        thresholds; the D6 pilot by default)

options:
  -h, --help            show this help message and exit
```

## `jef-data validate --help`

```text
usage: jef-data validate [-h] [--min-rows MIN_ROWS] csv

positional arguments:
  csv                  CSV in the Yahoo 7-column schema

options:
  -h, --help           show this help message and exit
  --min-rows MIN_ROWS  advisory minimum clean-row count
```

## `jef-data sync-actions --help`

```text
usage: jef-data sync-actions [-h] --symbol SYMBOL [--store STORE]
                             [--base-url BASE_URL]

options:
  -h, --help           show this help message and exit
  --symbol SYMBOL      e.g. AAPL.US
  --store STORE        store root (default: data/, gitignored)
  --base-url BASE_URL
```

## `jef-data load --help`

```text
usage: jef-data load [-h] --symbol SYMBOL [--store STORE] [--from FROM]
                     [--to TO] [--asset-type {crypto,etf,stock}]
                     [--currency CURRENCY] [--base-url BASE_URL]

options:
  -h, --help            show this help message and exit
  --symbol SYMBOL
  --store STORE
  --from FROM           YYYY-MM-DD (default: incremental from the last stored
                        session)
  --to TO
  --asset-type {crypto,etf,stock}
                        required, except for EODHD .CC symbols (the crypto
                        namespace is evidence); a ticker is not
  --currency CURRENCY
  --base-url BASE_URL
```

## `jef-data adjust --help`

```text
usage: jef-data adjust [-h] --symbol SYMBOL [--exchange EXCHANGE]
                       [--store STORE]

options:
  -h, --help           show this help message and exit
  --symbol SYMBOL
  --exchange EXCHANGE
  --store STORE
```

## `jef-data import-csv --help`

```text
usage: jef-data import-csv [-h] --csv CSV --symbol SYMBOL
                           [--exchange EXCHANGE] --asset-type
                           {crypto,etf,stock} [--currency CURRENCY]
                           [--store STORE]

options:
  -h, --help            show this help message and exit
  --csv CSV
  --symbol SYMBOL
  --exchange EXCHANGE
  --asset-type {crypto,etf,stock}
                        required: a Yahoo CSV carries no instrument type
  --currency CURRENCY
  --store STORE
```

## `jef-data export --help`

```text
usage: jef-data export [-h] --symbol SYMBOL [--exchange EXCHANGE] --output
                       OUTPUT [--store STORE]

options:
  -h, --help           show this help message and exit
  --symbol SYMBOL
  --exchange EXCHANGE
  --output OUTPUT
  --store STORE
```

## `jef-data differential --help`

```text
usage: jef-data differential [-h] --a-symbol A_SYMBOL
                             [--a-exchange A_EXCHANGE] [--b-symbol B_SYMBOL]
                             [--b-exchange B_EXCHANGE] [--b-csv B_CSV]
                             [--tolerance TOLERANCE] [--output OUTPUT]
                             [--store STORE]

options:
  -h, --help            show this help message and exit
  --a-symbol A_SYMBOL
  --a-exchange A_EXCHANGE
  --b-symbol B_SYMBOL
  --b-exchange B_EXCHANGE
  --b-csv B_CSV         compare against a CSV instead of a stored series
  --tolerance TOLERANCE
                        relative tolerance per cell (default 1e-4)
  --output OUTPUT       also write the report here
  --store STORE
```

## `jef-data sync --help`

```text
usage: jef-data sync [-h] [--universe UNIVERSE] [--store STORE]
                     [--asset ASSET] [--provider PROVIDER] [--dry-run]
                     [--tail TAIL] [--force-actions] [--base-url BASE_URL]
                     [--summary-json PATH]

options:
  -h, --help           show this help message and exit
  --universe UNIVERSE  universe TOML (default: the packaged
                       src/jef/data/universe.toml)
  --store STORE        store root (default: the universe's defaults.store)
  --asset ASSET        limit to this asset name (repeatable)
  --provider PROVIDER  limit to this provider (repeatable), e.g. --provider
                       eodhd where Binance is unreachable
  --dry-run            plan from local store state only - no network, no key
                       needed
  --tail TAIL          tail-refresh window in sessions, minimum 1
                       (docs/DATA_CONTRACT.md §7.2; default 10): newest-wins
                       inside, frozen-first-seen outside
  --force-actions      sync corporate actions even when fresh (override the
                       once-per-UTC-day gate)
  --base-url BASE_URL  EODHD base URL override
  --summary-json PATH  write the per-leg results as JSON (the event ledger's
                       stage_outcome diagnostics, Arc A A3(a)); written on red
                       runs too
```

## `jef-data status --help`

```text
usage: jef-data status [-h] [--universe UNIVERSE] [--store STORE]
                       [--asset ASSET] [--provider PROVIDER]
                       [--staleness STALENESS]
                       [--jump-threshold JUMP_THRESHOLD] [--window WINDOW]
                       [--resolution-window RESOLUTION_WINDOW]
                       [--resolution-k RESOLUTION_K] [--flat-k FLAT_K]
                       [--gap-k GAP_K] [--spread-threshold SPREAD_THRESHOLD]
                       [--spread-alerts] [--json]

options:
  -h, --help            show this help message and exit
  --universe UNIVERSE   universe TOML (default: the packaged one)
  --store STORE         store root (default: the universe's defaults.store)
  --asset ASSET         limit to this asset name (repeatable)
  --provider PROVIDER   limit to this provider (repeatable)
  --staleness STALENESS
                        alert at this many missed expected sessions
                        (docs/DATA_CONTRACT.md §7.4; default 2)
  --jump-threshold JUMP_THRESHOLD
                        phantom-split one-day |return| alert threshold
                        (default 0.40)
  --window WINDOW       newest sessions scanned for jumps, and for the cross-
                        venue common session (default 10)
  --resolution-window RESOLUTION_WINDOW
                        newest TRADED sessions measured for price resolution -
                        zero-volume rows drop first, like the seam
                        (docs/DATA_CONTRACT.md §7.8; default 500)
  --resolution-k RESOLUTION_K
                        note a coarse quoting grid below this distinct-
                        close/session ratio (default 0.20)
  --flat-k FLAT_K       note a coarse/frozen feed above this share of sessions
                        whose close did not move (default 0.25)
  --gap-k GAP_K         note a post-seam continuity gap at or above this many
                        absent expected sessions (default 5, calibrated: the
                        largest true US closure since 1962 measures 4 -
                        2001-09-10..17 - so the market itself never notes; a
                        provider data hole does, however it is served)
  --spread-threshold SPREAD_THRESHOLD
                        cross-venue close-spread WARN threshold for assets
                        with 2+ live feeds (Arc X X1; default 0.005 = 0.5%,
                        calibrated on the committed fixtures -
                        docs/CROSS_VENUE_PLAN.md)
  --spread-alerts       promote a cross-venue spread breach from a warning to
                        an ALERT, so it joins the exit-1 contract (off by
                        default: it compares a CROSS-CHECK leg, and exit 1
                        stops the venue's day before it publishes anything)
  --json                machine-readable report instead of the table
```

## `jef-data universe --help`

```text
usage: jef-data universe [-h] [--universe UNIVERSE]

options:
  -h, --help           show this help message and exit
  --universe UNIVERSE  universe TOML (default: packaged)
```
