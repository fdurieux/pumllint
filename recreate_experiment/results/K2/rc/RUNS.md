# Acceptance-suite runs

Command (from OUT/scratch): `JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=OUT/daily-rc.sh JDL_ADAPTER=adapter_rc PYTHONPATH=OUT python -m pytest -q kit/features/steps --basetemp OUT/scratch/btN -p no:cacheprovider`

| run | date (UTC) | result | notes |
|---|---|---|---|
| 1 | 2026-10-23 | 197 passed, 0 failed (197 collected) | first run after ad-hoc checks; nothing to fix |

Runs 2 and 3 were not used: run 1 was fully green, so there was nothing to fix and no code changed afterwards.
