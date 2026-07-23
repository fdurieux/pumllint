# pumllint roadmap

Status baseline: **v0.5.0** (2026-07-22) shipped the complete SCORING.md
maturity model — scorer, gap reports, `score --min-level` CI gate, integrity
caps C1–C7, XD cross-diagram pack — calibrated (SCORING.md §9), frozen behind
golden tests, and empirically characterized (EVIDENCE.md: fidelity
correlation r ≈ 0.49, sharp degradation below Level 2). **v0.6.0**
(2026-07-23) added Arc A's model-set aggregate score and Arc B's
baseline/ratchet mode; **v0.7.0** (2026-07-23) added trend/delta reporting
and the shields.io badge; **v0.8.0** (2026-07-23) added the composite GitHub
Action and pre-commit hooks; **v0.9.0** (2026-07-23) opened Arc C with the
class-diagram parser and CLS pack; **v0.10.0** (2026-07-23) added the
state-diagram parser and STA pack; **v0.11.0** (2026-07-23) closed the base
catalog with UC003 (35/35 rules implemented). This file tracks what remains,
grouped into arcs. Keep it updated as items land.

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
- [x] Packaging *(0.8.0)*: composite GitHub Action (`action.yml`, inputs
  mirroring the CLI, installs from the pinned ref) and pre-commit hooks
  (`.pre-commit-hooks.yaml`: `pumllint`, `pumllint-score`); both dogfooded
  in tests.yml and drift-guarded by tests/test_packaging.py.
- [ ] HTML report (single self-contained file) for architect-facing reviews.

## Arc C — Coverage growth

- [x] **CLS pack + class-diagram parser** *(0.9.0)* — `parser/class_.py`
  (classifiers, brace-body members, relations with multiplicities; typed by
  classifier declarations and `<|` generalization arrows, never re-typing
  other forms) + CLS001–005. Note: the corpus still has no class-diagram
  fixtures, so the golden contract does not yet cover CLS scoring — extend
  `tools/gen_corpus.py` and re-freeze deliberately when it should.
- [x] **STA pack + state-diagram parser** *(0.10.0)* — `parser/state.py`
  (declarations, composite bodies with a container stack, `[*]` endpoints;
  typed by the `state` keyword and `[*]`, never re-typing other forms) +
  STA001–003. Same corpus caveat as CLS: no state fixtures in the golden
  contract yet.
- [x] UC003 *(0.11.0)* — usecase links now carry label/arrow (`UseCaseLink`,
  tuple-unpack compatible), endpoints typed by syntax (`(X)` usecase, `:X:`
  actor), reversed arrows normalized; direction judged via actor
  connectivity, only when exactly one endpoint is actor-connected.
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
- Recommended next: Arc B is done except the HTML report (architect-facing;
  wait for pull or pair it with a real need). Arc C's new-parser work is done
  (CLS 0.9.0, STA 0.10.0, UC003 0.11.0 — full base catalog); what remains is
  thickening DIM-TRC/DIM-RDB (which touches dimension weights — re-read
  SCORING.md §9 and re-calibrate deliberately) and growing DIM-CON
  cross-type. Consider adding class/state/usecase fixtures to the corpus
  (gen_corpus.py) with a conscious golden re-freeze before or alongside the
  thickening work.
