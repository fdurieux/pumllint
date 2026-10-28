# M3: inverse coverage (what the wiki states and the kit does not)

Source: `../m1/claims.worksheet.md`, the `in_kit` column. Denominator: the
127 TRUE claims of the M1 sample (all 128 claims were graded). 18 are
`in_kit = NO`. Every NO was checked by searching the kit
(`requirements.json` and `contracts/`, verbatim externals and
`universe.toml` included; `uml/` and `features/` excluded) for the fact.

The 18 claims collapse to 13 distinct facts, because the wiki restates a
fact on more than one page (the quickstart repeats the architecture page).

| fact | claims | kind | what the wiki states | why the kit lacks it |
|---|---|---|---|---|
| F1 | 1, 80 | structure | the distribution discovers only `jef.data*` under `src` | clean-room artefact: `make_clean_room.py`'s `reduced_pyproject` writes that `include` |
| F2 | 2, 92 | structure | the package root exports four names and imports no Parquet or HTTP code | not specified; the kit's author lists `validate_or_raise` as unused code (`../../hidden/NOTES.md`, "Unused code") |
| F3 | 3, 92 | structure | `python -m jef.data` runs the same `main()`; command handlers import lazily | not specified; no kit scenario, adapter or harness step uses `python -m jef.data` |
| F4 | 4 | configuration | dependencies are pandas, numpy, scikit-learn, with no extras; `pyarrow` and `requests` are needed but undeclared | clean-room artefact: the reduced pyproject keeps J-F's core dependencies and drops its extras; the kit's `pins.md` pins `requests` and `pyarrow` |
| F5 | 7 | structure | `jef.binning.loading` is the storage seam; binning stays storage-agnostic | the kit carries the help string naming `load_eod_store` (`cli_help.md`), not the package docstring's design statement |
| F6 | 9, 42, 43 | behaviour | `modeled_source()` picks a sole enabled source implicitly and is the deterministic feeder, while sync acquires every enabled source | the parser rules are JDL-010 and sync's selection is JDL-084; `modeled_source` is in the kit author's unused-code list (no CLI caller) |
| F7 | 47 | behaviour | a universe class correction is not a migration: reconciliation keeps a row whose only change is `asset_type` or `price_basis` | consequence of JDL-065 (the six compared columns, identical rows kept), never drawn |
| F8 | 52 | structure | `HttpTransport` imports `requests` only when constructed | not specified; JDL-023 gives the seam |
| F9 | 70 | behaviour | the three final uploads are sequential, not a transaction; a late failure cannot roll back an earlier upload | consequence of JDL-158 (the uploads, in order, under `set -e`), never drawn |
| F10 | 81 | configuration | scheduling belongs to EventBridge and the task's exit feeds CloudWatch alarms | `daily.sh`'s header comment; the kit's chain is the script's behaviour, not its placement |
| F11 | 103, 112 | structure | the injection seams: `RateLimiter(clock, sleep, utc_today)`, `BaseCollector(transport, rate_limiter, max_retries, backoff, sleep)`, `ParquetStore(lock_timeout, clock, sleep)`, `run_sync(..., now)` | partly: the kit has the store clock, the collector sleep and the run clock, not the rate limiter's clock or UTC-date function |
| F12 | 115 | repository | the checkout has no tests and no test-runner configuration | clean-room artefact: `make_clean_room.py` copies no `tests/` |
| F13 | 127 | behaviour | the store's lock and atomic year-file replace make no cross-file transaction, and the actions JSON gets neither | consequence of JDL-058 (per-file tmp + `os.replace`) and JDL-042 (plain truncating write), never drawn |

By kind, claims (facts): structure 9 (6), behaviour 6 (4), configuration
2 (2), repository 1 (1), naming 0 (0). `repository` is not one of the
pre-registered kinds (structure, naming, behaviour, configuration). It
was added at grading for F12, which describes the checkout rather than
the code.

By origin of the gap, facts:

| origin | facts | claims |
|---|---|---|
| clean-room artefact: true of the subject tree, not of J-F | F1, F4, F12 | 1, 4, 80, 115 |
| consequence of kit requirements, never drawn | F7, F9, F13 | 47, 70, 127 |
| code the kit leaves out on purpose or by scope: unused functions, import mechanics, injection seams, design statements | F2, F3, F5, F6, F8, F10, F11 | 2, 3, 7, 9, 42, 43, 52, 81, 92, 103, 112 |

No fact in the table is a CLI-observable behaviour that a kit requirement
gets wrong or leaves undecided. Three are failure-mode consequences of
requirements the kit states (F7, F9, F13), and a reader of the kit could
draw them. The rest describe the package's shape, its seams or its
deployment placement, which the kit's behavioural scope leaves out.
