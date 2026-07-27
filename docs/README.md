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
- [Example maturity report](https://fdurieux.github.io/pumllint/example-maturity-report.html)
  — the pilot's Phase-0 artefact: the tool's own score run over the bundled
  `examples/`, published and drift-guarded (`tests/test_pilot_example.py`).
- [Dogfooding: pumllint on its own lint flow](dogfooding.md) — the linter
  applied to [a sequence diagram of its own pipeline](pumllint-lint-flow.puml):
  what held up, and what to watch. The diagram source itself is described
  construct by construct in
  [the annotated walkthrough](pumllint-lint-flow-explained.md).
