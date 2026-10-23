# The executable specification (pytest-bdd)

Every scenario is tagged with the requirement ids it verifies (`@JDL-NNN`,
see `../requirements.json`). The suite drives an implementation only through
three seams, chosen by environment variables:

| variable | default | what it names |
|---|---|---|
| `JDL_UNDER_TEST` | `jef-data` | the executable (split like a shell word list, so `python -m mypkg.cli` works); every `When I run "jef-data ..."` step runs it with the scenario's work directory as the current directory and without `EODHD_API_KEY` unless the scenario sets one |
| `JDL_CHAIN` | `deploy/daily.sh` | the daily chain script; `events.sh` and `dashboard.sh` must sit beside it (the given externals). Chain scenarios copy the three files into a scratch directory, mark the chain executable and put recording stubs on `PATH` for `aws`, `jef-data`, `jef-binning`, `timeout`, `curl`, `date` and `python3` |
| `JDL_ADAPTER` | `jdl_adapter` | an importable Python module implementing `../contracts/HARNESS_INTERFACE.md`; used for injected clocks, replayed provider traffic and reading stores back. Its collectors must replay `fixtures/http/<set>` with rate limiting disabled and backoff sleeps suppressed (contracts/fixtures.md §5) |

Run (from anywhere; Python with the pins of `../contracts/pins.md`, plus
pytest and pytest-bdd 8+):

```bash
export JDL_UNDER_TEST="my-jef-data"          # or: "python -m myimpl.cli"
export JDL_CHAIN=/path/to/rebuild/deploy/daily.sh
export JDL_ADAPTER=my_adapter                # importable: put its directory on PYTHONPATH
python -m pytest -q <kit>/features/steps
```

Scenarios need no network; every provider answer comes from
`fixtures/http`. Stores are fresh temporary directories per scenario.

## What each feature covers

| feature | covers |
|---|---|
| `universe.feature` | the packaged universe listing, normalisation of defaults/dates/class map, the refusal of every malformed universe (one Examples row per refusal), the unwrapped missing-file error |
| `collectors.feature` | EODHD bar hygiene (glitch rows, duplicates, ordering), replay identity and its rules, retries and HTTP errors, non-list answers, split-string parsing, Binance klines, paging and the page-limit warning, the missing key, the hand-run `load` declaration refusals and symbol normalisation |
| `actions.feature` | the actions files' envelope and real-clock stamp, dividends verbatim, the once-per-UTC-day gate (same day, previous day, forced), stored splits driving the arithmetic |
| `adjustment.feature` | the two-split equity cell for cell, the dividend ETF, the pre-adjusted crypto series, declared class versus `.CC` suffix, a split learned after the first fill, the `adjust` command (re-derivation, fixed point, refusals), degenerate ratios |
| `store.feature` | the on-disk layout, the read-back schema, tail reconcile and revisions, no phantom revisions, out-of-window rows, the bounded revision echo, CSV import overwrite and its refusals |
| `seam.feature` | the exported frame and its Volume dtype rule, the export CSV, the validation report (every message, the minimum-rows knob) |
| `differential.feature` | the differential report, tolerance, the refusal without a B side |
| `sync.feature` | leg selection and filters, selection refusals of `sync` and `status`, end caps, the inverted window, today-dated bars, the tail window, dry-run plans, independent leg failure, the summary document, CSV legs, default store, cross-year tails |
| `status.feature` | every alert, warning and note at and past its threshold, the class verdicts, the venue-pair spread, the JSON envelope, the table and the exit code |
| `cli.feature` | parser errors (exit 2), import labels; revision 2026-10-23 (closing round): the export of an absent series, the exact parser error output, every `--help` text verbatim (from `../contracts/cli_help.md`, run with `COLUMNS=80`) |
| `decisions.feature` | revision 2026-10-23 (wave 2): one `Rule:` block per DMN table of `../contracts/dmn/`, Examples rows keyed to the tables' rule ids (`row` column or `# dmn-row:` comment; coverage by `harness/dmn_coverage.py`); the differential on an absent side |
| `chain.feature` | stage order and arguments, the publish gate, red stages, the exec guard, the bucket guard, the metadata digest, the TERM trap |

## Fixtures

* `fixtures/http/<set>/` — recorded-fixture files (contracts/fixtures.md);
  synthetic numbers, no resemblance to any market intended.
* `fixtures/universes/` — universe variants (`bad/` holds one malformed
  file per refusal).
* `fixtures/csv/` — Yahoo-style 7-column CSVs for imports, status and
  validation.
* `fixtures/expected/` — expected frames (`columns`, `dtypes`, `data` rows;
  floats are exact float64 values, `datetime` cells ISO 8601 UTC, `text`
  columns compared by value).
