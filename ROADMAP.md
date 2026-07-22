# pumllint roadmap

Status baseline: **v0.5.0** (2026-07-22) shipped the complete SCORING.md
maturity model — scorer, gap reports, `score --min-level` CI gate, integrity
caps C1–C7, XD cross-diagram pack — calibrated (SCORING.md §9), frozen behind
golden tests, and empirically characterized (EVIDENCE.md: fidelity
correlation r ≈ 0.49, sharp degradation below Level 2). **v0.6.0**
(2026-07-23) added Arc A's model-set aggregate score and Arc B's
baseline/ratchet mode; **v0.7.0** (2026-07-23) added trend/delta reporting
and the shields.io badge. This file tracks what remains, grouped into arcs.
Keep it updated as items land.

## Arc A — Integrity (done)

- [x] **Model-set aggregate score** *(0.6.0)* — `aggregate_scores()` folds
  per-diagram results into a `ModelSetResult` (worst level +
  element-weighted composite, SCORING.md §3); text and json reporters emit
  it. `--min-level` gates on the model-set level by construction (set level
  = worst diagram level).

## Arc B — Trust & adoption (highest-value next arc)

- [x] **Baseline/ratchet mode** *(0.6.0)* — `pumllint score --baseline
  maturity.json` records per-diagram levels on first run, then fails CI only
  on *regression*; `--update-baseline` accepts the status quo
  (`pumllint/baseline.py`).
- [x] Trend/delta reporting *(0.7.0)* — ratchet-compare runs annotate the
  text report ("Level 3 → 4 since last baseline", "new since baseline") per
  diagram and for the model set; json adds `baseline: {level, delta}`.
- [x] Badge output *(0.7.0)* — `-f badge` emits shields.io endpoint JSON for
  the model-set level (SVG deemed unnecessary: shields renders styling from
  the endpoint; revisit only on demand).
- [ ] Packaging: a GitHub Action and a pre-commit hook wrapping
  `pumllint` / `pumllint score`.
- [ ] HTML report (single self-contained file) for architect-facing reviews.

## Arc C — Coverage growth

- [ ] **CLS pack + class-diagram parser** — specs already written as skipped
  features (CLS001–005 in RULES.md); class diagrams are where the codegen
  story is strongest (types, multiplicities → DIM-CMP).
- [ ] **STA pack + state-diagram parser** — STA001–003, same situation.
- [ ] UC003 — needs include/extend parsing in the usecase parser.
- [ ] **Thicken DIM-TRC** (deferred from calibration decision 10c): owner
  tag, requirement/ADR-link rules in the GEN pack. Removes the 2-rule
  thin-dimension caveat; revisit dimension weights (SCORING.md §9) after.
- [ ] **Thicken DIM-RDB**: message-count, note-density, diagram-size rules.
- [ ] Grow DIM-CON beyond the sequence-only XD pack into cross-*type* entity
  identity (same entity in sequence vs class vs activity diagrams).

## Arc D — Evidence engine (core done; optional deepening)

EVIDENCE.md delivered the measured maturity→codegen relationship. Only if
marketing claims need escalation:

- [ ] Complexity-normalized fidelity (kills the synthetic-diagram confound
  where trivial diagrams score near-perfect fidelity regardless of maturity).
- [ ] More scenario families beyond order_payment/credit_intake; larger n
  per diagram (current n=3 leaves ±8 noise on per-diagram means).
- [ ] Multiple generator and judge models (current: Opus 4.8 gen, Sonnet 5
  judge; remember the ~15-point self-judging bias — always judge
  independently).

## Arc E — Ecosystem (demand-driven; wait for pull)

- [ ] `pumllint fix` — auto-remediation for mechanical findings (declare
  implicit participants, add titles, name diagrams).
- [ ] LSP server / IDE integration for inline findings.
- [ ] JSON schema for the report formats (lint + maturity).
- [ ] Real SonarQube plugin with measures (replacing the synthetic-issue
  workaround in the sonar reporter).

## Working agreements (read before picking anything up)

- Scores are a public contract: any change that shifts corpus scores must be
  deliberate — the golden test enforces it; re-freeze consciously with
  `python tools/calibrate.py --freeze tests/golden_scores.json`.
- Claim language is settled (SCORING.md §9): Level 5 is "method-convention
  complete", never "guaranteed generation-ready"; the evidence-backed pitch
  is the correlation and the below-Level-2 cliff.
- The zero-dependency promise holds: product code and its tests must run
  under `python tests/run_tests.py` with the stdlib only.
- Recommended next release (0.8.0): Arc B's packaging — the GitHub Action
  and pre-commit hook wrapping `pumllint` / `pumllint score`. With the
  ratchet, deltas, and badge in place, packaging is what turns adoption from
  "copy this CI snippet" into one line of config. The HTML report can ride
  along or wait for pull.
