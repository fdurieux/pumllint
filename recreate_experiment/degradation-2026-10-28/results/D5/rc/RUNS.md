# Acceptance-suite runs

Command (from a scratch directory, PYTHONPATH = out/):
`JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=out/daily-rc.sh JDL_ADAPTER=adapter_rc python -m pytest -q -p no:cacheprovider kit/features/steps`

| run | passed | failed | total | notes |
|---|---|---|---|---|
| 1 | 256 | 0 | 256 | first run after the initial build |
| 2 | 256 | 0 | 256 | after splitting JEF_ASSETS on all whitespace in the chain (no suite failure to fix) |

Run 3 was not used: runs 1 and 2 were fully green and no change was pending.
