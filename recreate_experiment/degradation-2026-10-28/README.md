# Degrading the kit (opened 2026-10-28)

A pre-registered intervention on the recreation experiment's kit, testing the
cascade of the Legible systemic model (`../legible-model-review-2026-10-28/`).
The test plants known defects in one layer of the kit at a time, rebuilds
the program from each degraded kit with a fresh agent, and grades the
rebuild against the frozen reference. Read `PREREGISTRATION.md` first: its
§5 is the order of work, and its Results section is the record.

| path | what |
|---|---|
| `PREREGISTRATION.md` | question, kit layers, the six arms, defect types and the seeded selection walk, consistency checks, measures G1–G6 and R1–R9, expectations X1–X7, bounds; Results appended below the line |
| `plant/` | the plant bundle: selection walk, kit patches, mutant patches, observing sets, V results; committed at grading, hash pushed before the first rebuild |
| `results/<arm>/` | each rebuild as written, its grading and provenance; absent until the arm runs |
