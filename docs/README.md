# pumllint documentation

pumllint's documentation is audience-split — pick the guide that matches
why you are here:

| You are… | You want to know… | Read |
|----------|-------------------|------|
| New to all of this — no technical background | What the evidence actually established, from first principles, every term defined | [The evidence, explained from scratch](evidence-explained.md) |
| An IT manager, architecture lead, or sponsor | Why this tool is worth mandating; what the measurable payoff is | [The case for pumllint](case-for-pumllint.md), then [pumllint in the SDLC](value-in-the-sdlc.md), then [Where tooling pays](sdlc-tooling-landscape.md) |
| A DevOps / platform engineer | How to install it and wire it into the pipeline | [Setup and CI integration](setup-and-ci.md) |
| An architect reading the reports, or a modeller whose diagrams get checked | What the findings and maturity levels mean, and how to act on them | [Understanding findings and scores](findings-and-scores.md) |
| A developer extending the linter | How to specify, implement, and test a new rule | [Writing rules](writing-rules.md) |
| A coding agent implementing from diagrams — or the person wiring one up | The score → repair → re-score loop to run before generating code | [Using pumllint from a coding agent](agents.md) |

The management shelf is three documents: the *case* (what the tool is, what
it costs, what the evidence supports), the *SDLC assessment* (where the
value lands across a SAFe Continuous Delivery Pipeline, claim by claim,
with a pilot measurement plan), and the *tooling landscape*
([Where tooling pays](sdlc-tooling-landscape.md): which delivery-tooling
capabilities have outcome evidence at all, what AI changes, and where
pumllint's category sits on a Wardley map of the whole pipeline).

## How this split was chosen

The roles fall out of the product's own delivery arcs (see
[ROADMAP.md](../ROADMAP.md)):

- **Arc D (Evidence engine)** produced the measured maturity→codegen
  relationship — that is the substance of the *management case*.
- **Arc B (Trust & adoption)** produced the baseline/ratchet mode, the GitHub
  Action, pre-commit hooks, the badge and the HTML report — the artefacts the
  *pipeline integrator* wires up and the *report reader* consumes. The HTML
  report exists precisely because the architect/reviewer audience never runs
  CLIs.
- **Arc C (Coverage growth)** grew the rule catalog across diagram types —
  the surface the *diagram author* interacts with.
- **Arc E (Ecosystem)** plus the extensibility architecture (`@register`,
  `catalog.toml`, the executable RULES.md spec) serve the *rule author /
  toolsmith*.

The arcs are delivery phases, not an audience taxonomy — several arcs serve
the same person, and Arc A (scoring integrity) serves all of them invisibly —
but they are a useful cross-check that no audience was forgotten.

## Reference documents (not audience guides)

- [RULES.md](../RULES.md) — the executable rule specification (every rule,
  rationale, Gherkin acceptance criteria).
- [SCORING.md](../SCORING.md) — the maturity model: dimensions, formula,
  levels, caps, calibration notes.
- [EVIDENCE.md](../EVIDENCE.md) — the measured relationship between maturity
  scores and code-generation outcomes; plain-language walkthrough:
  [The evidence, explained from scratch](evidence-explained.md).
- [ROADMAP.md](../ROADMAP.md) — what remains, and the working agreements for
  contributors.
- [Pilot charter (template)](pilot-charter.md) — fill-in-the-blanks plan
  for a first pilot on real diagrams: phases, roles, ADKAR change
  checklist, pre-agreed decision gates; with
  [a starter config](pilot-starter-config.toml) and a read-only dialect
  census (`tools/pilot_census.py`) to run before anything gates.
- [Security & hardening assessment](security-hardening-assessment.md) —
  dated review (2026-07-29, v0.24.0): threat model, verified strengths,
  ranked findings, and the hardening measures deliberately *not* taken,
  with reasons.
- [First contact: the pilot census on a public wild corpus](pilot-census-first-contact.md)
  — dated evidence note (2026-08-11): the read-only dialect census run
  end-to-end on 159 real third-party PlantUML files from five public
  repositories — recognition, maturity and rule-firing numbers, the
  zero-element cap carrying coverage honesty on C4-macro dialects, and
  the scoping (not the pilot organisation's corpus; demand gates
  unchanged).
- [Demand scan: PlantUML in markdown specs](demand-scan-embedded-plantuml.md)
  — dated evidence note (2026-07-26) behind the ROADMAP's
  markdown-extraction settlement: the spec-driven ecosystem's public
  footprint, measured under pre-registered decision rules before anything
  was built.
- [C4-PlantUML pack: fit evaluation](c4-pack-evaluation.md) — dated fit
  note (2026-07-27) behind the ROADMAP's C4 record: why C4 is unusually
  lintable, what v0.23.0 does with C4 input today (measured — Level 1 on
  well-formed C4, sequence mistyping on raw arrows), the candidate rule
  sketch, and the census trigger that would green-light a build.
- [Prose→model→prose pipeline: fit evaluation](prose-pipeline-evaluation.md)
  — dated fit note (2026-07-29) behind the ROADMAP's requirements-pipeline
  record (Arcs G–J): an external reassessment of the round-trip
  requirements-validation idea verified element-by-element against this
  repo — what holds (deterministic back leg, metamodel conformance,
  k-way model diffing; two claims measured as probes), what was
  corrected (stdlib over textX, projection disclosure), and the per-arc
  build triggers.
- [The AI-ready specification stack, evaluated](spec-stack-evaluation.md)
  — dated fit note (2026-07-29): an external recommendation on
  specification artifacts for AI codegen, checked against this repo's
  evidence — it corroborates the plan at nearly every touch point; its
  blind spot (artifacts mandated to exist, never gated) is precisely
  this project's category; records the adopted Arc G refinements, the
  agents.md precedence ladder, and the sequence↔contract candidate.
- [*Situational Awareness*, mapped onto pumllint](aschenbrenner-mapping-evaluation.md)
  — dated evaluation (2026-08-01): an external mapping of
  Aschenbrenner's capability-forecast essay onto this project's thesis,
  verified against the repo record — what holds (artifact-side
  unhobbling, current-band maximum relevance, the governance hedge),
  what was corrected (two untraceable citations, a misnamed harness, a
  premature falsification), and the falsifiable window premise with
  the Arc D harness as its standing instrument.
- [Model verification beyond linting, evaluated](model-verification-evaluation.md)
  — dated evaluation (2026-08-02): an external note proposing formal
  ambitions (deadlock proofs, rule-set consistency proofs,
  well-formedness as a type; TLA+/Alloy; a Lark/ANTLR grammar),
  verified against the repo — the recommendation largely describes the
  shipped architecture, the ambitions fail on oracles or invert the
  linter's job, and the one keeper (a glossary/approved-term rule) is
  recorded with its adopter trigger.
- [Research charter: the minimum sufficient specification stack](research-charter.md)
  — dated reframing record (2026-08-06): the research objective
  ("maximise end-to-end effectiveness") reframed to what can be
  measured and falsified — minimum sufficient information per
  lifecycle hop, carriers at fixed information, gates as risk policy —
  with the wave program (W0–W7), per-wave gates and ceilings, five
  named falsifiers, and the adversarial verification record (17
  findings, all adopted). W0's measurement kits shipped with it
  (`stack_experiment/`).
- [The SDD + generation-manifest recommendation, evaluated](sdd-manifest-evaluation.md)
  — dated fit note (2026-08-10): an external recommendation pairing
  spec-driven development (PlantUML requirements as inputs) with a
  compose-style manifest/lockfile/run-record triad for the generation
  stack, verified element-by-element against the working tree — its
  foundation items already ship (`trace`, config, schema-pinned JSON),
  its compiler analogy is corrected to attribution-not-reproducibility,
  and two candidates are recorded (portable run-record format;
  model→spec change-impact design), nothing queued.
- [The two-stage external project review, evaluated](external-review-evaluation.md)
  — dated evaluation (2026-08-11): an externally authored two-stage
  review of the whole repository (stage 1 at the W1-results state,
  stage 2 after the W2–W4 results landed, before W5), assessed
  claim-by-claim against the md record on
  sense/nonsense/fit/gap/priorities — every checked figure traces
  (zero misquotes), both repo-facing defect findings verified real
  (the Level-5 naming contradiction; EVIDENCE.md's unstated boundary),
  the "target architecture" and closing-lesson claims graded, three
  doc-hygiene and two wave candidates recorded, nothing queued.
- [The two-stage external review, compared run by run](external-review-comparison.md)
  — dated companion note (2026-08-11): the owner's side-by-side
  distillation of the review's two runs (topic table, scores,
  one-line deltas) with a per-row Claude feedback column re-graded
  against the frozen records, the post-Run-2 repository state (W5
  ran the same day; the keystone held), and an overall verdict —
  faithful on facts, errs by attribution and scoping; the ask-loop
  blind spot flagged in both runs.
- [The measured minimum sufficient stack](minimum-sufficient-stack.md)
  — dated consolidation record (2026-08-11, verified): the research
  charter's convergence document — the measured answer to which
  artifacts, which detail, which syntax for the model→code hop,
  consolidated from the five frozen wave records (W1–W5,
  stack_experiment/, ≈$32.65): the contract-led portfolio, the
  per-generator knees and the measured far side, the refuted carrier
  equivalence, silent conflict resolution, and the survives-agency
  verdict — with the falsifier ledger and every published failure
  counted next to the confirmations.
- [Example maturity report](https://fdurieux.github.io/pumllint/example-maturity-report.html)
  — the pilot's Phase-0 artefact: the tool's own score run over the bundled
  `examples/`, published and drift-guarded (`tests/test_pilot_example.py`).
- [Dogfooding: pumllint on its own lint flow](dogfooding.md) — the linter
  applied to [a sequence diagram of its own pipeline](pumllint-lint-flow.puml):
  what held up, and what to watch. The diagram source itself is described
  construct by construct in
  [the annotated walkthrough](pumllint-lint-flow-explained.md).
