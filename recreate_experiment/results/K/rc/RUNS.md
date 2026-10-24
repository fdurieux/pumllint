# Acceptance-suite runs

| run | passed | failed | total | notes |
|---|---|---|---|---|
| 1 | 175 | 3 | 178 | the three failures were the metadata-digest chain scenario (all three Examples rows): the chain's `python3 -c` programs spanned several lines, which the recording stub logs as extra call lines |
| 2 | 178 | 0 | 178 | after making the chain's two metadata parses single-line `python3 -c` programs (plus two changes no scenario exercises: no RuntimeWarning on a 0/0 adjustment factor, and an empty CSV overwrite prunes the series) |
| 3 | - | - | - | not used: run 2 was fully green |
