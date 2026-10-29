# Acceptance-suite runs

| run | date | command | collected | passed | failed |
|---|---|---|---|---|---|
| 1 | 2026-10-29 | `JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=out/daily-rc.sh JDL_ADAPTER=adapter_rc PYTHONPATH=out python -m pytest -q -p no:cacheprovider kit/features/steps` | 258 | 258 | 0 |

Run 1 notes: all scenarios green on the first run; three RuntimeWarnings from a
0/0 `adjustment_factor` on zero-close CSV rows (stderr noise only).
| 2 | 2026-10-29 | same command, after silencing 0/0 division warnings and accepting date-time text as a Binance start/end | 258 | 258 | 0 |

Run 2 notes: all green, no warnings. Run 3 was not used: nothing left that the
suite shows to fix.
