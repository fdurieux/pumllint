# Acceptance-suite runs

Command (from a scratch directory outside the kit):

```
PYTHONDONTWRITEBYTECODE=1 JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=<out>/daily-rc.sh \
JDL_ADAPTER=adapter_rc PYTHONPATH=<out> python -m pytest -q -p no:cacheprovider <kit>/features/steps
```

| run | passed | failed | errors | total | notes |
|---|---|---|---|---|---|
| 1 | 258 | 0 | 0 | 258 | first run of the complete build |
| 2 | 258 | 0 | 0 | 258 | regression check after a non-functional refactor of `load` (collector closed once on every path); no failure to fix after run 1 |

Run 3 was not used: run 1 and run 2 were both fully green, and nothing changed afterwards.
