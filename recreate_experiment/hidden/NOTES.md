# Reverse-engineering notes (hidden; never part of the kit)

Subject: `jef.data` 0.6.0 (`jef-data`), `deploy/daily.sh`, read from the
subject tree only. Kit built from `hidden/kit_src` by `hidden/tools/build_kit.py`
(which renders `{{requirement-key}}` into `JDL-NNN`); requirements from
`hidden/tools/reqs_part*.py`; fixtures from `hidden/tools/gen_fixtures.py`;
expected frames recorded from the subject by `hidden/tools/make_expected.py`
(after cross-checking the arithmetic by hand in contracts/adjustment.md and
seam_frame.md).

## What was hard

1. **Float exactness.** The harness compares cells bit for bit, so every
   formula had to be stated with its operation order: volume raw-ization
   (`served / F`, then `volume_raw * F`) is not invertible
   (100000 / 10.5 * 10.5 = 99999.99999999999), and that single cell flips the
   exported Volume dtype of the whole series to float64. The split factor is a
   left-to-right product in stored order starting at 1.0. I designed the
   SPLT fixture (ratios 1.5 and 7) so these effects are visible.
2. **The clock split.** `run_sync(now=...)` drives the window, the guard, the
   gate and the today check, but the corporate-actions stamp is written by
   `actions._utc_now_iso()` because `sync._run_leg` calls `sync_actions`
   without `now`. A second injected-clock run therefore always finds the
   (real-clock, 2026) stamp "fresh" for any injected 2024 date. Scenarios rely
   on this (it is the logic), and pre-written stamps are used where a
   specific gate outcome is needed.
3. **Mutant m1 is store-invisible.** Moving the bar fetch before the actions
   refresh leaves every stored cell identical (splits are still read after
   the refresh). Only failure ordering observes it, hence the two scenarios
   built for it (404 after a good refresh; splits 503 + bars 404).
4. **pumllint detection.** A component diagram without an `interface` is
   parsed as a sequence diagram; `database` declarations do the same. The
   transport seam is modelled as an interface, which is also the truth.
5. **Status through the adapter.** The CLI has no clock switch; the subject
   adapter runs the real `status --json` command in-process with the health
   module's clock patched and the universe object substituted, so the
   document and exit code are the command's own (no re-implementation).

## Places where the comment says one thing and the logic another (kit states the logic)

* `store.SCHEMA` / `_utc_midnight_ms` docstrings: `timestamp` is "Unix ms";
  under the pins (pandas 3.0.5 parses date-only strings at microsecond
  resolution) the code's `// 10**6` yields Unix **seconds**
  (2024-01-02 → 1704153600). Requirement st-timestamp, basis logic.
* `_utc_midnight_ms` says "at the 00:00-UTC day boundary": a date string with
  a time of day keeps it (no truncation). Kit says so (store.md §4).
* `ingest_yahoo_csv` docstring: "Every row is kept" — duplicate Date rows are
  dropped by `_normalize` (first kept) while the reported row count includes
  them (yahoo_small.csv: reports 5, stores 4). Kit states both.
* `sync.run_sync` docstring: `now` drives "the end-guard and the gate" — true
  for the gate's comparison, but the stamp the gate later reads is real-clock.
* `health` docstring lists "actions_missed_k (default 2)" as a knob; the CLI
  never exposes it (fixed 2), the harness interface neither.
* `adjust` module docstring: "Dividends never enter" — consistent with logic.
* `sync` module docstring: "constructs no collectors" on dry-run — consistent.

## Behaviour that depends on something the code does not show

* **Python / library versions**: `tomllib` error texts (toml_syntax example),
  argparse error texts (cli.feature asserts only exit 2 + "usage:"/"error:"),
  numpy 2's scalar repr `np.float64(10.5)` inside the differential report,
  pandas 3's `str` dtype for text columns and its datetime-resolution
  inference (the seconds timestamp), pandas' CSV float formatting, the
  `UserWarning` pandas prints to stderr for un-inferable date formats in
  `validate` (not asserted).
* **Provider behaviour**: EODHD serving split-adjusted volume with raw prices
  is stated by a comment ("measured at the 2026-08-16 live re-record"); the
  code encodes it as `VOLUME_BASIS = "split_adjusted"`. Frozen-first-seen
  history depends on providers honouring `from`; the store reconciles any row
  it is served (scenario "outside the requested window").
* **Real clock**: the actions stamp; the status CLI (table scenarios use 2099
  data and future stamps so they stay clock-independent until 2099); the
  CLI dry-run for crypto legs (only used with non-crypto legs).
* **Network**: `load`, `sync-actions` happy paths, the live transport, the
  rate limiter (1000/60 s, 100000/day), the HTTP timeout (30 s), connection
  retries, non-JSON bodies, the >100-page refusal, the 300 s lock timeout
  cannot be reached through the fixed harness (replay never raises
  connection errors and always returns JSON). The requirements carrying them
  (col-transport, col-retry, col-errors, col-binance-pages, st-atomic,
  cli-load, cli-sync-actions) are verified only in their observable parts;
  see "Partially verified" below.
* **Packaged evidence**: the status declared-class check always reads the
  packaged classifications.toml; the `unmapped` verdict is unreachable with
  it (no vendor type outside Common Stock/ETF/Currency), so that branch of
  stat-class-verdicts is specified but not exercised.
* **Chain environment**: the chain's line number in bash's `${VAR:?}`
  message differs per script (scenario asserts the message tail only);
  `timeout`, `date`, `curl`, `aws`, `python3` are stubbed; `$0` is the path
  the chain is invoked with (scenarios invoke it by absolute path).

## Partially verified requirements (honest list)

| requirement | verified part | not verifiable through the harness |
|---|---|---|
| col-transport | replay transport rules (content keys, recursion, manifest.json skipped) | live requests session, 30 s timeout, rate limiter, daily budget |
| col-retry | 5 attempts on a 503 (message), retry on 429/5xx | backoff durations (sleeps suppressed by contract), connection-error retries |
| col-errors | HTTP N after 5 attempts; HTTP 404 body; not-a-list | network failure text; non-JSON body (replay always JSON); redaction |
| col-binance-pages | two pages, short-page stop, not-a-list | >100 pages refusal (needs 100 000 rows) |
| col-fixture-file | a self-check of the kit's own fixture corpus against the naming/content rule | the implementation's recorder (no harness function records) |
| st-atomic | no `.tmp` left, `.lock` present | the lock wait/timeout |
| cli-load | declaration refusals, normalisation, key-first construction, no write on refusal | fetch window, append mode, re-adjustment (network) |
| cli-sync-actions | key required | the happy path (network) |
| stat-class-verdicts | agree, disagree, not_comparable, no_evidence | unmapped (unreachable with the packaged file) |
| cli-load-decl | D-01, D-02 | D-03 (argparse choices catch it first) |

## Judgement calls

1. "The load transform" of seam_frame.md: the downstream seam
   (`jef.binning.loading`) is absent; I specified the transform the program
   owns (bar → stored row → exported frame, with a worked example) and
   recorded the seam's own drop policy as the single prose-basis requirement
   (seam-load-policy).
2. Expected frames were recorded from the subject (calibration) rather than
   computed by an independent implementation; their key cells are restated
   by hand in contracts and in scenario tables.
3. Mutant m1 implemented as a pure reorder of the fetch (the literal reading
   of "fetches bars BEFORE its corporate-actions refresh"); the alternative
   (moving the reconcile too) would also be caught by the volume cells.
4. The rate limiter, transport timeout and lock timeout were folded into
   existing requirements (col-transport, st-atomic) rather than given
   requirements no scenario can verify.
5. `st-append` (the hand-run load's append mode) was folded into cli-load for
   the same reason.
6. Chain scenarios stub `python3` but delegate `python3 -c` to the real
   interpreter so the metadata parsing in the prologue is exercised; the
   externals are copied verbatim beside the chain and their resulting calls
   (`python3 -m jef.events emit ...`, `aws s3 cp ...`) are asserted as the
   observable form of the chain's calls into them.
7. Status knob defaults are restated in cli.md (the CLI reference) although
   their numbers live in single requirements — the contract file is the CLI
   surface, the requirements cite each other by id.
8. Scenario count is 95 (pumllint's count) against a 60–90 target: I merged
   several scenarios into outlines and stopped where merging would hide what a
   scenario proves.

## Unused code (no CLI caller; not specified beyond a mention)

`CorporateActionsStore.needs_update` (explicitly "not a gate", regression
baseline only), `list_symbols`, `EODHDCollector.search` and `EXCHANGE_MAP`,
`universe.modeled_source`, `PILOT_UNIVERSE`, `contract.validate_or_raise`,
`ParquetStore.symbols`, `RecordingTransport` (specified as the recorder in
fixtures.md because the task asks for recorder-grade exactness).

## Scenario corrections made during calibration (all were my errors)

* adjustment.feature "declared class decides": I wrote CCSTK 2024-05-03 close
  6.75; the served close is 12.5, 12.5 / 2.0 = 6.25. Arithmetic slip.
* sync.feature "dry run plans every leg shape": my plan.toml gave DIVY two
  enabled sources without a modeled marker; the parser refuses that
  (uni-err-modeled). Fixture error; marked one source modeled.
* sync.feature "CLI dry run uses the default store" and "cross-year tail":
  padded SMALL (5 chars) as if 4 under `{asset:>6}`. Scenario typo.
* status.feature "resolution reads the provider's own print": divided the
  tick by the upper value; the logic (and my own requirement text) divides by
  d[k]. Arithmetic slip; 0.0049504950495049506.
* status.feature "status table": two padding miscounts and a guessed min tick
  (0.5051%, not 0.6536%). Scenario errors.
* Harness wiring: a step-pattern collision ('has no field' vs 'has no
  {kind}') and an empty-stdout step; an empty-value regex for the key step.
None of the corrections changed my reading of the code; no requirement
statement had to change because of a failing scenario.

## Calibration summary

* Subject: 178/178 test cases pass (95 scenarios incl. 23 outlines).
* m1 (fetch before the actions refresh): 2 failed — the two failure-ordering
  scenarios of collectors.feature. m2 (no crypto end-guard): 11 failed.
  Details in MUTANTS.md.
* Gates: lint 0 findings at info; score Level 5 on all 8 diagrams; trace
  158/158 covered and verified. Output in GATES.md.

## Housekeeping disclosure

Until late in the work, pytest's default `--basetemp` (under
`/tmp/pytest-of-root`) and `tempfile.mkdtemp()` (system temp, removed after
use) held scenario stores; no file there was read by me, but pytest manages
(lists/rotates) its own numbered directories there. From the final
calibration on, `hidden/run_suite.sh` passes `--basetemp` inside
`hidden/scratch/` and `make_expected.py` creates its temp directory there.
Running the subject's console script would have written `__pycache__` into
the read-only subject tree; every run set `PYTHONDONTWRITEBYTECODE=1`.

Subject-tree integrity check (end of work): no source file of the subject
was modified. Bytecode files for eleven modules (actions, adjust,
classification, differential, health, store, sync, collectors/*) had appeared
in the subject's `__pycache__` directories, all stamped 09:49:24 within 60 ms;
the burst does not match any single command of mine (every invocation I made
set `PYTHONDONTWRITEBYTECODE=1`, and no command of mine imports all of those
modules at once), so I cannot attribute it. I deleted exactly those files,
restoring the tree's original file set (only the five `.pyc` files present at
the start remain).
