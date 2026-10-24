# What the kit does not reach: the data lane under coverage

Measured 2026-10-24. The kit's acceptance suite (258 cases, the original
`jef-data` and its `daily.sh` with the kit's externals) ran against the
original under `coverage` 7.17 with branch measurement, the `jef-data`
subprocesses collected through a `coverage.process_startup()` hook. Source:
`src/jef/data` at the experiment's pinned tree. The trace gate says every
requirement is verified; this is the other direction — which code no
requirement's scenario reaches — and the first draft of an unrealised-code
register for one real application. Numbers in `coverage.json` beside this
file.

| measure | value |
|---|---|
| statements | 1520 |
| executed by the suite | 1379 (89.0 %) |
| never executed | 141 |
| branches | 524 |
| branches taken one way only | 49 |

## The 141 unexecuted statements, by class

| class | statements |
|---|---|
| A · live-transport paths: reachable only with the network, never through replay | 40 |
| B · specified, never exercised: the kit states the behaviour and no scenario reaches it | 33 |
| B? · unspecified and unexercised | 1 |
| C · no production caller in the lane: deliberate orphans, test-only helpers, cross-lane API, tooling | 61 |
| D · internal guards the store's own writes make unreachable | 6 |

Reading: **40** statements are the program's live half — HTTP, the
rate limiter, connection-error retries, the `load` and `sync-actions`
commands' happy paths — which replay cannot reach by construction and the
kit specifies without a scenario; the fourth rebuild wrote its own unit
tests for several of them. **33** are behaviour the kit states and no
scenario exercises, the requirement-granular "verified" of `trace` hiding a
clause-level gap: the lock timeout, the leftover-file sweep, the 100-page
refusal, a non-JSON body, the status table's pair lines, the resolution
fallback, two Binance edges, and the whole grammar of `classifications.toml`
whose only production input is the packaged, valid file. **61** have no
caller in the lane at all; one of them, `needs_update`, carries its own
history in a docstring ("NOT A GATE. Do not give this a production caller
again"), the clearest instance in this code of knowledge the code states
and no artefact derived from it carried. **6** are guards the store's
own writes make unreachable. One statement is unspecified as well as
unexercised: a collector returning zero bars, the fourth rebuild's
assumption A-08.

## The register

Class, the statements counted, what the code does there, the requirement
that states it (— when none), and the question or note for the subject
matter expert. Line numbers are those of the pinned tree.

| file | lines | function | class | n | what | requirement | note / question |
|---|---|---|---|---|---|---|---|
| `cli.py` | 113-125 | `load_symbol` | A | 10 | `load`'s ingestion: start after the latest stored session, fetch, append, re-adjust | JDL-141 | none: specified and unreachable through replay |
| `cli.py` | 99 | `load_symbol` | A | 1 | `.CC` symbol with no declaration → crypto, then the live fetch | JDL-142 |  |
| `cli.py` | 141-149 | `cmd_sync_actions` | A | 5 | `sync-actions`'s happy path | JDL-143 |  |
| `cli.py` | 168-169 | `cmd_load` | A | 2 | `load`'s success line | JDL-141 |  |
| `store.py` | 216-218 | `save` | A | 3 | append mode: only `load` uses it | JDL-141 |  |
| `collectors/base.py` | 132-141 | `HttpTransport.request` | A | 5 | the live HTTP transport and its connection-error wrapping | JDL-023 |  |
| `collectors/base.py` | 105, 111, 113-116 | `RateLimiter.acquire` | A | 6 | the daily budget refusal and the per-minute sleep | JDL-023 |  |
| `collectors/base.py` | 253-259 | `get_json` | A | 4 | retry after a connection error (replay never raises one) | JDL-028 |  |
| `sync.py` | 374-376, 403 | `get_collector` | A | 4 | constructing a live Binance collector; closing constructed collectors | JDL-100 |  |
| `store.py` | 189-196 | `_locked` | B | 4 | the 300 s lock wait and its StoreError | JDL-058 | the fourth rebuild unit-tested this with a fake clock; the kit has no scenario |
| `store.py` | 232 | `_sweep_tmp` | B | 1 | removing a leftover `.tmp` year file before a write | JDL-058 | same |
| `collectors/base.py` | 291 | `paginate` | B | 1 | the 100-page refusal | JDL-038 | a fixture set with 101 pages would reach it |
| `collectors/base.py` | 275-276 | `get_json` | B | 2 | a 200 whose body is not JSON | JDL-028 | one fixture |
| `cli.py` | 353, 355 | `cmd_status` | B | 2 | the table's ALERT and WARN lines of a venue pair | JDL-132 | status.feature checks pair findings only in JSON |
| `health.py` | 212 | `measure_resolution` | B | 1 | resolution falling back to `close` when `close_raw` leaves nothing | JDL-122 | needs a series with NaN close_raw |
| `collectors/binance.py` | 58, 70 | `fetch_page` | B | 2 | an empty klines page; a row with close ≤ 0 skipped | JDL-037, JDL-039 |  |
| `cli.py` | 101 | `load_symbol` | B | 1 | an asset_type outside the vocabulary below the parser | JDL-142 (D-03) | the kit says 'reachable only below the CLI' |
| `store.py` | 291 | `ingest_bars` | B? | 1 | a collector that returns zero bars: nothing written, 0 reported | unspecified | the fourth rebuild's assumption A-08; the kit is silent |
| `classification.py` | 74-76, 79, 82, 89, 92, 99, 104-105, 147-148, 152, 156, 161, 167, 200 | `_string, _parse_instrument, load_classifications, compare` | B | 17 | every grammar refusal of classifications.toml and the unmapped vendor type | classifications.toml.md | the CLI loads only the packaged file, which is valid: validation code for a file that cannot be invalid in production |
| `classification.py` | 132-133 | `classifications_text` | B | 2 | loading a classifications file by path | classifications.toml.md | no CLI exposes the path |
| `actions.py` | 156-160 | `needs_update` | C | 5 | wall-clock freshness; its docstring: 'NOT A GATE. Do not give this a production caller again' | — | kept for tests after two production callers were removed on 2026-08-30: a deliberate orphan, and exactly the kind of history the code states but no diagram carries |
| `actions.py` | 163-166 | `list_symbols` | C | 4 | list the symbols with an actions file | — | callers: J-F tests only |
| `store.py` | 116-117 | `symbols` | C | 2 | list a store's symbols for an exchange | — | callers: J-F tests only |
| `collectors/eodhd.py` | 134-137 | `search` | C | 4 | the provider's symbol search | — | callers: one J-F test |
| `collectors/eodhd.py` | 115, 117, 127, 129 | `get_splits, get_dividends` | C | 4 | date-bounded actions requests | JDL-029 | no caller in the lane passes dates |
| `contract.py` | 139-142 | `validate_or_raise` | C | 4 | validate and raise on errors | — | exported by the package, used by J-F tests only |
| `universe.py` | 283-293 | `modeled_source` | C | 11 | the modelled source of an asset | JDL-020 (the rule), no caller here | callers in jef.binning, jef.console, jef.dashboard, jef.api: a cross-lane API, outside this kit's scope by construction |
| `collectors/base.py` | 79-83, 195-219, 222 | `fixture_filename, RecordingTransport` | C | 21 | recording fixtures from live traffic | JDL-024, JDL-025 (the file shape) | used by tools/record_data_fixtures.py and tools/make_synthetic_fixtures.py: the kit describes the files, not the recorder |
| `collectors/base.py` | 182 | `Transport.close` | C | 1 | the base no-op | — |  |
| `differential.py` | 27 | `Report.__str__` | C | 1 |  | — |  |
| `cli.py` | 577 | `` | C | 1 | the `__main__` guard of cli.py | — | |
| `__main__.py` | 1-4 | `` | C | 3 | `python -m jef.data` | — | the console script is the entry the kit specifies |
| `adjust.py` | 85 | `adjust` | D | 1 | refusal when raw columns are missing | adjustment.md §4 (immutability) | internal guard: the store always writes them |
| `store.py` | 210, 212 | `save` | D | 2 | missing store columns; unknown save mode | — | internal guards |
| `store.py` | 302 | `_frame_from_bars` | D | 1 | unknown volume_basis | — | internal guard |
| `health.py` | 127, 189 | `longest_zero_volume_run, _printed_closes` | D | 2 | no zero-volume run; column absent | — | internal guards |

## What this measures and what it does not

- It measures what the kit's scenarios reach, not what the kit states: a
  class-B line is specified and untested, not unspecified.
- Replay fixes the live half out of reach. Class A is a property of the
  oracle's design (no network), not a gap in the kit's knowledge of the code.
- Class C is where the tribal knowledge sits. Each row is a question for the
  SME: deliberate orphan, test helper, cross-lane contract, or dead. The
  code answers one of them itself (`needs_update`); the others it does not.
- Branch partials (49) are not classified here; the per-file list is in
  `coverage.json`.

## Reproduce

```bash
. /path/to/venv-with-original/bin/activate && pip install coverage
SP=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
echo "import coverage; coverage.process_startup()" > $SP/zz_coverage_startup.pth
printf '[run]\nbranch = True\nparallel = True\nsource = jef.data\n' > covrc.ini
cd recreate_experiment/kit
COVERAGE_PROCESS_START=$PWD/../../covrc.ini JDL_UNDER_TEST=jef-data JDL_CHAIN=<daily.sh beside the kit externals> \
  JDL_ADAPTER=adapters.original PYTHONPATH=../harness coverage run --rcfile=... -m pytest -q features/steps
coverage combine --rcfile=... && coverage report --rcfile=... -m
```
