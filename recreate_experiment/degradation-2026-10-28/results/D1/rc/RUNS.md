# Acceptance-suite runs

Command (from `out/`):
`JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=$OUT/daily-rc.sh JDL_ADAPTER=adapter_rc PYTHONPATH=$OUT PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider ../kit/features/steps`
(`-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1` so the run writes nothing into the kit.)

| run | date | passed | failed | total | notes |
|---|---|---|---|---|---|
| 1 | 2026-10-29 | 258 | 0 | 258 | first run after the build; nothing to fix |
| 2 | 2026-10-29 | 258 | 0 | 258 | confirmation run on the cleaned tree (scratch checks removed, assumptions finalised); no code change between runs 1 and 2 |

Run 3 was not used: nothing failed in runs 1 and 2.
