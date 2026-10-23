# Acceptance-suite runs

Command (each run): `JDL_UNDER_TEST=jef-data-rc JDL_CHAIN=OUT/daily-rc.sh
JDL_ADAPTER=adapter_rc PYTHONPATH=OUT python -m pytest -q -p no:cacheprovider
--basetemp=OUT/scratch/runN <kit>/features/steps` (178 scenarios collected).

Before run 1, while building, four ad-hoc `-k` subsets of at most a third of
the suite each were run (universe/legs 47, collectors 38, actions/adjustment
45 — all passed; one 63-test selection was refused by my own cap before
running). They are listed here so the run count is not understated.

| run | passed | failed | notes |
|---|---|---|---|
| 1 | 175 | 3 | the three metadata-digest chain examples: multi-line `python3 -c` programs split the stub's one-call-per-line log |
| 2 | 178 | 0 | after making the metadata `python3 -c` programs single-line (stdin-fed) and having every store writer take the series lock even for zero bars |

Run 3 was not used: nothing changed after run 2.
