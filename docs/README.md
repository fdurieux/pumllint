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
- [Pilot kickoff pack](pilot-kickoff-pack.md) — dated operational
  companion (2026-08-11) to the charter: the measured case in
  sponsor-ready sentences (current through W1b and the wild-corpus
  census, each with record and scoping), the 30-minute census
  runbook with first-contact calibration references, the short list
  of organisation-supplied inputs, and the condensed phase/gate
  table.
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
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27) sitting on top of the C4 fit note: the
  whole ecosystem (Structurizr, LikeC4, IcePanel, Mermaid C4, jQAssistant,
  the AI/MCP layer) graded for boundaries, overlap, fit, gap, sense and
  nonsense. The settlement stands; the dated behavioural claims were
  re-run at v0.29.0 and reproduce to the decimal. Motivation up — under
  the codegen profile a well-formed C4 diagram is silent at 100.0 on all
  six dimensions while its arrow-mixed sibling hard-fails with four
  invented blockers. Demand evidence down — the census's 46% C4-macro
  figure and its 45%-of-corpus-is-the-notation's-own-gallery figure are
  nearly the same files, so the trigger gains an exclusion rule. Three
  claim-language corrections, and the position confirmed from a third
  direction: three C4-capable validators, none of them grades.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), third in the ecosystem series. Verdict:
  no pack, no reader, and — unlike C4 — not wait-for-pull but a principled
  no, on two grounds either sufficient: the `.puml` is a *rendering
  exported from a model held elsewhere*, so findings cannot be durably
  acted on; and ArchiMate's rule spec is a legality metamodel every tool
  enforces at authoring time, which is the well-formedness-as-a-type
  anti-goal seen from the far side. The yield is the measurement: native
  ArchiMate is read as 2 lifelines and 1 message out of 9 modelled things,
  typed `sequence`, and scored **Level 4 (Precise) — 93.33/100**.
  Characterizing that closed a defect class across all three notes — a file
  with no type marker is typed `sequence` by one undecorated arrow, which
  makes exactly the 3 elements needed to escape the zero-element honesty
  cap.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), fourth in the series and the most
  emphatic no: no artefact (PlantUML has no BPMN modelled form), no gap
  (`bpmnlint` is architecturally the same product), **no generation step
  to gate** (a `.bpmn` file *is* the implementation, executed by an
  engine), and the repo's own W3 carrier evidence pointing against the one
  remaining fit. The yield is not a market judgment but convergent
  validation nobody solicited: `bpmnlint` independently arrived at the
  same architecture and the same rules — `start-event-required` = ACT001,
  `no-implicit-*` = SEQ001/SEQ010/SEQ101 — and, fifth ecosystem running,
  still does not grade. Completes the agent-strategy quadruple: prevention
  by instruction, verification, prevention by construction, containment.
- [The UML ecosystem, evaluated](uml-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), fifth and last in the series and the only
  one pointing inward: UML is the ecosystem this artefact belongs to by name
  and not by substance. Three layers, one shared — UML defines a metamodel
  (449 metaclass invariants, 425 with OCL); PlantUML borrows the notation and
  implements none of it (607-page reference guide: metamodel 0, semantic 0,
  well-formed 0, OCL 0, XMI 0); pumllint builds its own typed model behind it.
  The claim language audits clean on every axis. The catalog is **86.3%
  not-UML** — 3 rules of 51 restate an OCL invariant. Two inward candidates:
  a `CLS006` needing zero parser work (one UML invariant is a blocker while a
  comparable one draws no finding at all), and the type-fallback class in its
  widest form — nine uncovered diagram types, a two-line file scoring Level 4
  Precise 100/100. Produced by a 14-agent fan-out; all five adversarial
  verifiers returned "refuted", and their corrections are what the note carries.
- [The Mermaid ecosystem, evaluated](mermaid-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), sixth and last in the series and the only
  ecosystem that is a **direct substitute** rather than an adjacent layer.
  Verdict: no sibling stack — the 2026-07-26 parking upgrades from *unqueued
  on cost* to *refused on an occupied niche*. `@mermaid-lint/cli` is a
  near-complete architectural mirror of this tool (config, severities,
  `--fix`, GitHub Action) and lints Markdown fences, the capability this repo
  demand-tested and declined; Mermaid owns the niche the scan measured; and
  W3 ranks the carrier −9.1 pp below PlantUML. Two findings sit
  uncomfortably together and are recorded that way: the **category is
  validated** (mermaid-lint's motivation is this project's thesis in someone
  else's words) and the **niche is contested**. Seventh ecosystem, still no
  grader — now even where two linters compete.
- [The D2 ecosystem, evaluated](d2-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), seventh in the series and the first
  refusal where the linting niche is **open**: D2 is a general graph
  language, not typed notations (one of five packs transfers, and that is a
  floor), and its own roadmap says *"Build a configurable linter."* The
  measurement is the series' sharpest and indicts this tool, not D2 — D2's
  `a -> b: label` is character-identical to PlantUML's, so a D2 sequence
  diagram wrapped in `@startuml` scores **Level 4 (Precise), 99.17, one
  cosmetic finding**, quieter and worse than the Mermaid equivalent. The
  silence is a *designed* behaviour (SEQ001's `only_if_any_declared`), not
  a defect — which gives the type-fallback class a second silencing
  mechanism any fix must be validated against. Eighth ecosystem, no grader.
- [The Structurizr DSL ecosystem, re-examined](structurizr-dsl-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), eighth in the series. The twice-settled
  "no" stands and its *reason* is corrected: Structurizr is not a support
  candidate but a **producer of the artefact pumllint gates** —
  `structurizr-cli export` writes PlantUML in two dialects. Measured on all
  three export shapes: the C4 export lands honestly at Level 1 (confirming
  the C4 note's dated prediction from a new producer); the static export is
  mistyped at Level 3; and the sequence export is typed, parsed and scored
  **correctly at Level 4 — while tripping GEN004 on every participant**,
  because the exporter emits numeric identifiers. The sharpest form of the
  generated-artefact problem in the series: nothing malfunctions, the
  findings are *true*, and their only fix is upstream where Structurizr's
  own `inspect` already runs.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md)
  — dated evaluation (2026-08-27), ninth in the series and the cleanest
  refusal: not a diagram notation (a model+perspectives format for an
  interactive viewer), the **first fully closed commercial ecosystem** in
  the series, and made of YAML — which W3 ranked last of five carriers.
  The yield is not about Ilograph: wrapping YAML in `@startuml` reads the
  **list dash as an arrow** and turns keys into participants, scoring
  **Level 4 (Precise) 99.62** — and the composite *rises* with the volume
  of unrecognized content (99.44 → 99.82 across 3→40 resources). Sixth
  instance of the type-fallback class and the first that **manufactures**
  content rather than dropping it.
- [The Graphviz / DOT ecosystem, evaluated](graphviz-dot-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), tenth and last obvious one in the
  series, and the **first refusal where the repository's own licence
  posture is decisive**: Graphviz relicensed to **EPL 2.0 on 7 March
  2026**, and the never-build names EPL "anywhere in the repo — product
  and lab alike", which closes the `tools/` extras door the knowledge-graph
  note had found open. Three further grounds: **zero of five packs
  transfer** (DOT is a graph language with no diagram types — a first),
  Graphviz sits **underneath** PlantUML as its optional layout engine
  rather than beside it, and the DOT linting niche has been repeatedly
  attempted with nothing sustained. The measurement is the best boundary
  result in the series and the note says why not to trust it: idiomatic
  DOT lands honestly at **Level 1**, but only because of **semicolons**,
  which DOT permits and does not require — drop them and the same graph
  types `sequence` at Level 3, or Level 4 in its undirected form.
- [The SysML ecosystem, evaluated](sysml-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), eleventh in the series and the first
  that **answers a trigger this record already set**: the UML note
  watched for SysML v2 "acquiring a PlantUML-renderable textual form with
  users" and listed it as its only SWOT threat. It had one all along —
  the OMG **pilot implementation renders through PlantUML** — so the
  threat entry is reclassified as a **producer**, and the answer stays
  no. Three measurements: SysML **v2** is the **first notation in the
  series that cannot be misread**, structurally, because its
  relationships are keywords (`connect … to`, `satisfy … by`, `:>`) with
  no relational symbol to fall through on; a SysML **v1 bdd** is the
  first foreign notation to land in a **fully correct parse**, where
  CLS002's four findings are right about the PlantUML and the wrong
  dialect for the model; and the yield — **`pumllint trace` reads
  requirement IDs from notes and titles but not from where SysML puts
  them**, reporting `0/2 covered` and "unlinked" on a diagram that exists
  to record that link. Deliberate and documented, so not a defect — but
  the invariant's cost had never been measured.
- [The Capella / Arcadia ecosystem, evaluated](capella-arcadia-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), twelfth in the series and the first
  refusal argued **against a fit that works**. An Arcadia **Exchange
  Scenario** hand-drawn in PlantUML is typed `sequence`, parsed
  correctly, and scores **Level 4 (Precise) 99.38, exit 0** with only
  cosmetic findings — the eleven-rule sequence pack applying as designed,
  and **SEQ009, false in five previous evaluations, correct here**. The
  first foreign artefact in twelve that pumllint handles well. And it is
  unreachable: **Capella has no PlantUML export**, so the sample had to
  be hand-written. Also: not a producer (recorded as a finding, breaking
  a two-evaluation run); a **third consecutive EPL collision**, restated
  once as a standing structural exclusion from the Eclipse-shaped MBSE
  tool space rather than a third coincidence; and the closest taxonomic
  convergence yet — two of Capella's four validation-rule categories are
  pumllint's dimension names verbatim.
- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), thirteenth in the series and the first
  whose subject is **not a notation, a tool or a product** but a standard
  about the same question this project asks. Three findings.
  **pumllint's unit is precisely the one thing 42010 defines no
  conformance for**: its five claim targets are AD, framework, language,
  viewpoint and model kind, and a `.puml` file is a *view component* —
  so pumllint can neither conform nor fail to, which settles
  "42010-aligned" before it is claimed. **Correspondences are half
  implemented**: XD001–005 *are* correspondence rules, but two views
  sharing nothing score **Level 4 (Precise) 100/100** as a model set —
  and the fix is already on the never-build list as missing-edge
  inference. And **the no-grader streak is reframed**: ISO/IEC/IEEE
  42030, the standard whose whole subject is architecture evaluation,
  declines to define an aggregate verdict — so twelve tools not grading
  may be a considered position rather than an empty niche. Also the first
  ecosystem whose normative text could not be read: paywalled, which is
  an argument against conformance claims users could not audit either.
- [The TOGAF / ADM ecosystem, evaluated](togaf-adm-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), fourteenth in the series, and the one
  that **corrects the record**. The line "Nth ecosystem, no grader",
  carried in thirteen entries, is imprecise as published: TOGAF ships two
  ordinal grading schemes, and **ACMM computes a maturity rating as a
  weighted mean over nine weighted elements plus per-level percentages** —
  which is `scoring.py`'s composite, structurally. The criterion the
  series was really applying is narrower and is now stated: *nothing in
  fourteen ecosystems grades the artefact class pumllint grades — a
  description*; adjacent objects have been graded for decades. That also
  sharpens the ISO 42010 note: the field aggregates over organizations and
  implementations and declines to over descriptions. Separately, the best
  measurement in the series — **three of four TOGAF diagram artifacts land
  in the correct parsed type with no false findings** (use-case → Level 4
  99.31, conceptual data → 98.75, data lifecycle → 99.48), across three
  different packs — while the deepest pack, `sequence`, maps to **none**
  of TOGAF's 32 diagrams.
- [The DoDAF / UAF ecosystem, evaluated](dodaf-uaf-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), fifteenth in the series and the
  **strongest artefact fit yet — the first that is both real and
  reachable**. DoDAF's OV-6c Event-Trace Description is a required model
  "sometimes called sequence diagrams", and the DoD CIO's own page says
  *"DoDAF does not endorse a specific event-trace modeling methodology. An
  OV-6c may be developed using any modeling notation…"* — so **a PlantUML
  sequence diagram is a conformant OV-6c**. Measured on the default
  profile: OV-6c → `sequence`, **Level 4, 99.88, exit 0, one info
  finding**, with the deepest pack applying correctly and **SEQ009 right**
  where it was false in six prior evaluations; OV-6b → `state` 99.92;
  DIV-2 → `class` 99.75. The counterweight is the first *configuration*
  finding in the series: under `--profile codegen` the same file collapses
  to **Level 2, 52.4, four blockers**, because SEQ103 demands
  signature-shaped messages of narrative operational events. And one turn
  after TOGAF, the exact inversion — `sequence` maps to **0** of TOGAF's
  32 diagrams and **3** of DoDAF's 52.
- [The NAF / MODAF ecosystem, evaluated](naf-modaf-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), sixteenth in the series and the first
  run deliberately as a **sibling test**: NAF, MODAF and DoDAF were all
  unified into UAF, so does the DoDAF fit generalize? **It does not.**
  DoDAF freed the *notation*, making a PlantUML sequence diagram a
  conformant OV-6c; NAF frees the *rendering* and constrains the
  **metamodel** to ArchiMate 3.1 or the UAF DMM — so NAF conformance
  lives where pumllint does not look. Measured, and it **inverts**: the
  ArchiMate route (one of NAF's two approved metamodels) scores **89.22
  with four false SEQ009s**, while a bare picture with no metamodel behind
  it scores **100.00 clean** — the NAF-conformant artefact ranks below the
  NAF-meaningless one. Also: **MODAF is withdrawn**, the first dead
  framework in sixteen evaluations, and the empirical case for refusing
  framework-shaped packs — a PlantUML sequence diagram was a MODAF OV-6c
  in 2010 and is a NAF view in 2026, with no code change.
- [The Zachman ecosystem, evaluated](zachman-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), seventeenth in the series and the
  oldest subject in it (1987). The purest **"nothing to lint"** case —
  Zachman is an *ontology, not a methodology*, prescribes no notation, and
  has no artefact a linter could read — but the note is not about the
  refusal. It supplies the vocabulary this project lacked for its own unit
  of analysis: Zachman's cells hold **primitives**, while a PlantUML
  sequence diagram mixes **Who + When + What** and is therefore a
  **composite**, which pumllint scores on the same "Precise" scale as a
  primitive-like class diagram with nothing distinguishing them. The
  contribution is a measurement: **all 51 rules classified by
  interrogative — What 5, How 8, Where 0, Who 13, When 15, Why 1** (plus 9
  artefact-level), so **Who+When carry 67% of the enterprise-facing
  rules**. The first quantitative statement of what pumllint's rules are
  *about* — worth consulting before describing the tool as broad
  enterprise-diagram hygiene.
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
- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md)
  — dated evaluation (2026-08-26): the graph-engineering question run
  through the house triage — sense/nonsense/fit/gap/SWOT for a
  knowledge graph over the diagram model, the rule set, and the
  repository itself. Verdict: the graph already exists (14 of 51 rules
  are graph queries; `trace` is a bipartite graph) and externalizing it
  fails on measured scale (950 elements across the 174-diagram wild
  corpus) and the zero-dependency agreement. Two keepers: the
  cross-artifact-identity arc as a naming device, and a deterministic
  repository link-integrity check — plus a rule-coverage finding the
  lens produced without a graph (DIM-AMB is unreachable for activity
  and use-case diagrams).
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md)
  — dated evaluation (2026-08-27): a shipping external ecosystem —
  OWL ontologies, SHACL shapes and six converters (PlantUML among them)
  lifting architecture sources into one RDF knowledge graph — assessed
  for boundaries, overlap, fit, gap, sense and nonsense against this
  roadmap. Verdict: adjacent and complementary, no build and no
  dependency — the one fit worth having (pumllint in a producer repo,
  before the converter) already ships, and SHACL's binary conformance
  over a tolerant projection cannot reach the defect class this catalog
  exists for. Two measured findings: the ecosystem's own `'!la-`
  annotations are invisible to GEN006, GEN007 and `trace`, and a
  component diagram's zero-element honesty cap turns on a single
  participant keyword. One attractive claim withdrawn — the two
  products' notions of *type* are not commensurable.
- [Cross-diagram relationships in pumllint, evaluated](cross-diagram-relationships-evaluation.md)
  — dated evaluation (2026-08-28), second in the Linked.Archi thread and
  the first pointing at the product's own cross-diagram layer: does
  pumllint lint relationships *between* diagrams, the way Linked.Archi's
  RDF qualified relationships declare them? Verdict: no — the XD pack
  joins entity **nodes** by name-equality and never compares **edges**
  (contradictory relationships across three diagrams draw zero
  cross-diagram findings), and nothing in the model, schemas or CLI has
  a slot for a declared diagram→diagram relation. Four measured gaps:
  the alias is the join key (same display name, different aliases —
  silent); an `!include`d declaration blinds XD001/XD002 **and raises
  the score 72.5 → 87.5**; no namespace means "deliberately different"
  is inexpressible; and `ref over` — the notation's one cross-diagram
  construct, recommended by SEQ006's own message — is dropped by the
  parser. The RDF shape itself is refused on two standing settlements
  (that is Linked.Archi's job); the in-notation half is the already
  recorded Arc C edge-coherence item, which this note supplies with the
  reproducible probe it lacked. One defect found and fixed: RULES.md's
  XD preamble still described the pre-v0.29.0 majority vote.
- [A foreign corpus reads back — the J-F audit](foreign-corpus-audit.md)
  — dated evidence note (2026-08-26): the first time a corpus this
  repository did not author was read for *semantics* rather than
  dialect — a project that adopted the codegen profile, reached Level 5
  100/100, and used it long enough to develop workarounds. Four real
  defects returned, all fixed: a failure-branch lexicon that constrained
  phrasing rather than modelling, a negation form unreachable for
  bracketed guards, a use-case diagram budget still calibrated for
  sequence lifelines (HEAD reddened a corpus the release passed, under
  the same version string), and a lexicon helper whose only lever
  replaced the defaults instead of extending them. Scores, pilot
  artefacts, the dogfooding record and this repo's own lint output are
  byte-identical across both fixes; three further recommendations are
  recorded as gated (Arcs C and D), none queued.
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
- [Cross-diagram identity, worked](xd-identity-demo.md) — the `!include`
  disclosure and the `distinct` option demonstrated on committed files
  ([docs/xd-demo/](xd-demo/)): the runnable companion to the
  cross-diagram relationships evaluation's G3/G4 findings, transcripts
  drift-guarded (`tests/test_xd_demo.py`).
