# pumllint documentation

pumllint serves four distinct audiences. Each gets its own guide — pick the
one that matches why you are here:

| You are… | You want to know… | Read |
|----------|-------------------|------|
| An IT manager, architecture lead, or sponsor | Why this tool is worth mandating; what the measurable payoff is | [The case for pumllint](case-for-pumllint.md), then [pumllint in the SDLC](value-in-the-sdlc.md) |
| A DevOps / platform engineer | How to install it and wire it into the pipeline | [Setup and CI integration](setup-and-ci.md) |
| An architect reading the reports, or a modeller whose diagrams get checked | What the findings and maturity levels mean, and how to act on them | [Understanding findings and scores](findings-and-scores.md) |
| A developer extending the linter | How to specify, implement, and test a new rule | [Writing rules](writing-rules.md) |

The management shelf is two documents: the *case* (what the tool is, what
it costs, what the evidence supports) and the *SDLC assessment* (where the
value lands across a SAFe Continuous Delivery Pipeline, claim by claim,
with a pilot measurement plan).

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
  scores and code-generation fidelity.
- [ROADMAP.md](../ROADMAP.md) — what remains, and the working agreements for
  contributors.
- [Example maturity report](https://fdurieux.github.io/pumllint/example-maturity-report.html)
  — the pilot's Phase-0 artefact: the tool's own score run over the bundled
  `examples/`, published and drift-guarded (`tests/test_pilot_example.py`).
