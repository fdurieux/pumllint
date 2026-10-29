# Acceptance-suite runs

Command (from a scratch directory outside the kit):

    JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=<out>/daily-rc.sh JDL_ADAPTER=adapter_rc \
    PYTHONPATH=<out> PYTHONDONTWRITEBYTECODE=1 \
    python -m pytest -q -p no:cacheprovider <kit>/features/steps

| run | passed | failed | errors | total | notes |
|---|---|---|---|---|---|
| 1 | 258 | 0 | 0 | 258 | first run after the build; nothing to fix |
| 2 | 258 | 0 | 0 | 258 | confirmation after the one post-run-1 change (`daily-rc.sh` splits JEF_ASSETS with `read -d ''`) |
| 3 | — | — | — | — | not used: run 2 was fully green, nothing left for the suite to show |
