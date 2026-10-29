# Acceptance-suite runs

Command (from a scratch directory, kit untouched):
`JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=<out>/daily-rc.sh JDL_ADAPTER=adapter_rc PYTHONPATH=<out> PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider <kit>/features/steps`

| run | date (UTC) | collected | passed | failed | notes |
|---|---|---|---|---|---|
| 1 | 2026-10-29 | 256 | 256 | 0 | first run after the build; no fix needed |
| 2 | 2026-10-29 | 256 | 256 | 0 | confirmation on the final tree (code unchanged since run 1; only ASSUMPTIONS/READ.log/RUNS.md edited, caches removed) - checks the timing-dependent TERM scenario is stable |
| 3 | - | - | - | - | not used: nothing left to fix |
