# Definition of done

The build is done when every line below holds. Commands run from `../kit/`
unless stated; `<out>` is your build's directory.

| # | proof | command | expected |
|---|---|---|---|
| 1 | package installs with the pinned dependencies only | `pip install -e <out>` then `pip freeze` | pandas 3.0.5, numpy 2.4.6, requests 2.34.2, pyarrow 25.0.1, nothing else beyond their own dependencies |
| 2 | the console script exists and prints the verbatim help | `COLUMNS=80 jef-data --help` | byte-equal to the first block of `contracts/cli_help.md` (the suite checks all eleven) |
| 3 | the acceptance suite passes, chain included | `JDL_UNDER_TEST=jef-data JDL_CHAIN=<out>/deploy/daily.sh JDL_ADAPTER=jdl_adapter PYTHONPATH=<out> python -m pytest -q features/steps` | `257 passed` — no failures, no skips, no deselection |
| 4 | the decision tables are still complete and the feature still covers them | `python ../harness/dmn_check.py contracts/dmn` and `python ../harness/dmn_coverage.py .` | every table `OK`; `60/63 rows exercised` with the three named exceptions |
| 5 | the property-based invariants hold on your build (needs `hypothesis` in the environment) | `JDL_ADAPTER=jdl_adapter PYTHONPATH=<out>:../harness python -m pytest -q ../harness/invariants` | `6 passed, 1 skipped` (the skip is the differential property, which needs a second implementation) |
| 6 | the end-to-end smoke of the chain's data stage | `jef-data sync --universe contracts/universe.toml --store /tmp/s --dry-run` | the plan, one line per leg, exit 0 |
| 7 | `ASSUMPTIONS.md` exists in `<out>` and every entry is still true of the code | read it | — |

Lines 1–3 are the gate; 4–6 are the checks the kit's own revisions are
held to; 7 is how the next revision of the kit learns what it did not say.

The specification's own gates, which you do not need to run but may:
`pumllint uml --fail-on info -c pumllint.toml` (no findings),
`pumllint score uml --min-level 5 -c pumllint.toml` (Level 5 on all eight),
`pumllint trace uml --requirements requirements.json --features features --fail-on-uncovered --fail-on-unverified -c pumllint.toml`
(163/163 covered, 163/163 verified). `TRACE.md` is the last one's report.

What the suite does not reach, and so what you must test yourself: the
happy path of `jef-data load` (it needs a live EODHD transport; the suite
covers only its refusals — `DECISIONS.md` rows r4 and r5 of
`command_by_store_state`); live rate limiting and retries against real
providers (`contracts/collectors.md` §1, replayed only); the chain against a
real AWS bucket (stubbed in `chain.feature`).
