# Degrading the kit (opened 2026-10-28)

A pre-registered intervention on the recreation experiment's kit, testing the
cascade of the Legible systemic model (`../legible-model-review-2026-10-28/`).
The test plants known defects in one layer of the kit at a time, rebuilds
the program from each degraded kit with a fresh agent, and grades the
rebuild against the frozen reference. Read `PREREGISTRATION.md` first: its
§5 is the order of work, and its Results section is the record.

Graded 2026-10-29: six of the fifteen planted defects reached the code, all
six concealed by the arm's own suite and caught by the pristine one; every
outcome is the one the kit's precedence rule gives. Six expectations held,
one split.

| path | what |
|---|---|
| `PREREGISTRATION.md` | question, kit layers, the six arms, defect types and the seeded selection walk, consistency checks, measures G1–G6 and R1–R9, expectations X1–X7, bounds; Results appended below the line |
| `plant/` | the plant bundle as hashed before the first rebuild (`sha256sum plant/SHA256SUMS` gives the pushed value): selection walk, kit patches, mutant patches, observing sets, V results, gate readouts; its `README.md` lists the parts |
| `results/<arm>/` | `rc/`, the rebuild as written (with its `ASSUMPTIONS.md`, `READ.log`, `RUNS.md`); `compare.json`; `m8.txt`; `r4.txt`, the arm's own kit suite; `r5.txt`, the pristine kit suite; `report.md`, the agent's hand-back verbatim; `usage.json`; `RUN.MANIFEST.sha256.json`; `diffs/`, the non-frame artefacts that differ from the reference |
| `results/r6.json` | per defect, the verdict on every observing artefact (`r6.txt`, the summary) |
| `results/grading/` | the grading tools (`grade_ref.sh`, `grade_mut.sh`, `grade_arm.sh`, `r6.py`, `fields.py`, `env.sh`) and their outputs: the reference's manifest check, the null baselines, the D3-W3 field reading |
