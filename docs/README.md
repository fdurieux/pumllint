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

The shelf shares one market picture — the positioning quadrant, scored
against the published rubric in
[Positioning pumllint](positioning-quadrant.md):

![Positioning quadrant of diagram-as-code checkers: the Leaders quadrant
is empty; pumllint sits deep in Visionaries; the incumbents cluster in
Challengers](positioning-quadrant.svg)

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
- [The FEAF / Gartner EA ecosystem, evaluated](feaf-gartner-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), eighteenth in the series and the first
  whose two halves are **opposites**. **FEAF** confirms a mapping the
  series had only inferred: its artifact table publishes each artifact's
  DoDAF equivalent, so **D-8 Event Sequence Diagram *is* DoDAF SvcV-10c**
  by FEAF's own account — the framework-to-framework half of the
  TOGAF/DoDAF/NAF mapping method, externally corroborated. D-8, D-7 and
  D-1 all score **Level 4, 100.00, zero findings** — and the note is
  explicit that this is inflated by naming the samples, so it is *not*
  comparable with DoDAF's 99.75–99.92. **Gartner** is the first
  *commercial advisory practice* in the series and supplies **the first
  genuine market headwind in eighteen notes**: its published position is
  that architecture documentation fails on **relevance, not
  incoherence** — and pumllint measures incoherence. Both readings are
  recorded and neither adopted; the threats column stays open. Also: the
  graded-object tally reaches four (organization, implementation,
  business service, vendor) and **none of them is a description**.
- [The ArchiMate viewpoints ecosystem, evaluated](archimate-viewpoints-ecosystem-evaluation.md)
  — dated evaluation (2026-08-28), nineteenth in the series and a
  **narrowing return** to the third note's subject: ArchiMate the
  *notation* was settled then; this is its **viewpoint mechanism**. The
  note was opened to test whether viewpoint conformance is mechanically
  checkable, and **its own research refuted the hypothesis**: no normative
  rule makes a view's conformance to its viewpoint a requirement, the 25
  example viewpoints are informative, and Archi itself applies a
  **graded response** — palette filtering, ghosting, an opt-in validation
  warning — while **hard-blocking illegal relationships**: the ecosystem's
  own calibration, and the third note's N2.
  Measured with the series' first **controlled experiment**: two views
  identical but for element type — one conformant, one violating — give
  **byte-identical output**, under both profiles, and with a fictitious
  viewpoint name. The one new measurement amends a standing candidate:
  the third note's arrow table has two outcomes, and ArchiMate's
  **realization** glyph `..|>` adds a third — typed **`class`, 99.31, and
  completely silent**, because `<|`/`|>` are type markers in their own
  right (`parser/class_.py:67`).
- [The C4 viewpoints / notation ecosystem, evaluated](c4-viewpoints-notation-evaluation.md)
  — dated evaluation (2026-08-28), twentieth in the series and the second
  **narrowing return** in two turns. The C4 settlement is unchanged (*fit
  verified, wait for census pull*); the contribution is a **reason**. The
  C4 note measured its 21-item checklist as ~40% mechanizable and put the
  rest down to "the rendered picture" — true but incomplete. C4's own
  notation page says **"The C4 model is notation independent, and doesn't
  prescribe any particular notation"** and **"all diagrams should have a
  key/legend"**: C4's guidance is picture-heavy *because* it refuses to
  specify a notation, so the source-checkable residue is small
  **structurally**, and no parser work moves it. Measured: the legend is
  invisible in **both** spellings — yet `parser/sequence.py:91-92` already
  tokenises `legend`/`endlegend` and swallows it as "display furniture",
  so the recorded legend candidate needs no parser work for that
  spelling. It also recorded a second instance of a pattern —
  *"viewpoint-shaped mechanisms are guidance, not contracts"* — which the
  Structurizr viewpoints note **withdrew** the following day as
  generalized from n = 2. The ecosystem-scoped facts stand (C4 defines no
  conformance for its four levels, as ArchiMate defines none for its 25
  viewpoints); the law does not, and the replacement predictor is
  **derived views vs drawn views**.
- [The Structurizr DSL viewpoints ecosystem, evaluated](structurizr-viewpoints-evaluation.md)
  — dated evaluation (2026-08-29), twenty-first in the series and the
  third **narrowing return** in three turns. The eighth note's settlement
  is unchanged; the contribution is a **correction to the two notes before
  this one**. *"Viewpoint-shaped mechanisms are guidance, not contracts"*
  was generalized from n=2 and is **withdrawn**: Structurizr's views take
  a typed scope argument and derive their content from the model, and the
  C4 evaluation had recorded Structurizr preventing abstraction mixing
  *"by construction"* since 2026-08-27 — a row both notes cited without
  noticing it refuted them. The replacement predictor is **derived views
  vs drawn views**: where content is derived from a typed model by scope,
  conformance is not unenforced but **vacuous**. The practical rule is
  unchanged with two different reasons — inventing an obligation
  (ArchiMate, C4) versus checking a **tautology** (Structurizr). Measured:
  container and component views export indistinguishably, **harmlessly**;
  and the view key *does* survive in `@startuml(id=…)`, landing in
  `diagram.name` verbatim as `'(id=Containers)'`.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md)
  — dated evaluation (2026-08-29), twenty-second in the series. The fourth
  note's settlement (2026-08-27) is unchanged — no BPMN support, same four
  grounds — and this one **executes the paired run that note deferred**
  for want of a Node toolchain. `bpmnlint` 11.13.0 and
  `bpmnlint-plugin-camunda-compat` 2.59.2 installed and **run**. Three
  corrections follow. `conditional-flows` is **not** ACT003: it enforces
  *consistency* (fires only once conditions have been started), where
  ACT003 enforces *completeness* — subsumption, not equivalence. The rule
  count was 27, not "~25", and `global` — filed as infrastructure — is the
  one rule mapping to **three** pumllint principles at once. And the
  claim that the BPMN ecosystem has **no ambiguity dimension is false**,
  and was false six weeks before it was written: Camunda's plugin has
  shipped `agent-tool-documentation`, `agent-tool-output-key` and
  `agent-fromai-contract` since 2026-07-15, whose stated rationale is that
  *an LLM reads the text*. A consumption step appeared in BPMN and the
  ecosystem grew this project's dimension to gate it — **validation, not
  an opening**, since the vendor owning the runtime filled it. Also
  measured: the DIM-AMB residual that gates the ACT-pack positioning note
  (a vague activity diagram scores 100/100 with DIM-AMB weighted 0.25 and
  penalised 0).
- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md)
  — dated evaluation (2026-08-29), twenty-third in the series and BPMN's
  sibling. **No**, on five grounds, and the strongest is that this project
  fenced DMN off from its own best evidence in advance. DMN is *"a
  graphical notation and an expression language"* — twenty-two prior notes
  were about diagrams, and here the substance is a table of FEEL
  expressions under a hit policy. Its interesting properties —
  completeness, overlap, masking — are **decidable, and belong to a
  solver**, which is why the ecosystem's linter is vestigial (`dmnlint`
  1.0.0, **two** DRD-graph rules, measured **silent on a table with both
  canonical defects**) while the analysers and modelers do the work.
  Measured here: a PlantUML `switch` with a real overlap and a real gap
  scores **Level 4 (Precise) — 100/100**; the same decision table is
  **byte-identical to absent** whether pasted into a `legend` or a `note`;
  but the two are *not* equally invisible — `trace` reports **3/3 covered
  from a note, 0/3 from a legend**, a documented consequence of the single
  carrier set. And W1b's emphatic decision-table result (+40.9 pp pooled,
  the only component whose removal hurts) was pre-registered as licensing
  **"none about DMN or any unmeasured carrier"**.
- [The FEEL expression language ecosystem, evaluated](feel-expression-language-evaluation.md)
  — dated evaluation (2026-08-29), twenty-fourth and a narrowing return on
  the DMN note. **No — and decided by a measurement rather than by scope**,
  because FEEL is the only subject in the series with a named counterpart
  inside this project's catalogue: SEQ105's class is
  `MachineEvaluableGuards`. Read precisely, SEQ105 is two membership tests
  against a five-word lexicon, not an evaluability check. Fed to `feelin`
  7.0.1, **four of those five phrases parse cleanly as valid FEEL** — only
  `if needed` fails, and only because `if` is a keyword. **A real parser
  would lose 4 of the rule's 5 findings.** Across eleven guards with both
  sides executed the two standards agree on 5 and disagree on 6 (SEQ105
  stricter on 4, FEEL stricter on 2) — orthogonal, not ordered — and the
  case that matters most, `the customer is probably eligible`, **passes
  both**. Also: `feelin` parses that phrase as one multi-word name while
  Camunda's engine docs forbid whitespace in names, so "validate it with
  FEEL" does not name a single behaviour.
- [The Spectral / OpenAPI ecosystem, evaluated](spectral-openapi-ecosystem-evaluation.md)
  — dated evaluation (2026-08-29), twenty-fifth, and the one with the
  least distance to travel: Spectral is **the tool this project's
  positioning case names as its own precedent**, and that claim had never
  been executed. **It survives contact** — configuration, presets, four
  severities, a fail gate, an extension surface and the summary line all
  map across. **The grading gap is confirmed on the closest peer there is,
  and starker than anywhere else: `spectral --help` lists one subcommand,
  `lint`** — no place in the CLI where an aggregate could live. Recorded
  deliberately **two-sided**, since an empty slot beside a mature peer can
  mean the maturity model is the differentiator *or* that nobody wanted a
  number. The one real architectural difference is a trade-off, not a gap:
  **Spectral's rules are data** (a JSONPath plus one of thirteen
  functions), **ours are code** — and none of those thirteen can express
  call/reply pairing or cross-file identity, because an OpenAPI document
  is a *tree* and a sequence diagram is a *trace*.
- [The prose-linting ecosystem, evaluated](prose-linting-ecosystem-evaluation.md)
  — dated evaluation (2026-08-29), twenty-sixth and the follow-on to the
  FEEL note, which recorded a prose-guard hole and refused to invent a
  mechanism. **Does the field that specialises in hedges already have
  one? No — and the negative is the finding.** `proselint` 0.16.0's
  *entire* `hedging` check is three phrases and its `weasel_words` check
  is the single word `very`: **four items against pumllint's seventy**.
  `write-good` with every check on flags `the customer is probably
  eligible` only as E-Prime. Across eight labels the two ecosystems are
  **disjoint** — the prose linters fire on none of the six DIM-AMB
  targets and vice versa. The one intersection is a collision: proselint
  says replace `...` with `…`, and **SEQ106 fires at blocker on both
  spellings**, because the defect is the omission, not the glyph. So
  **DIM-AMB is not a reimplementation of prose linting**: those tools
  check free-running English for style, this checks a label in a named
  slot for specificity sufficient to generate from.
- [The Gherkin / Cucumber ecosystem, evaluated](gherkin-cucumber-ecosystem-evaluation.md)
  — dated evaluation (2026-08-29), twenty-seventh, and the first whose
  subject is **already inside the project**: RULES.md's Gherkin blocks
  become 43 feature files and 122 scenarios, CI-gated for staleness. So
  the questions are inward-facing. **The method turned on ourselves:
  `gherkin-lint` reports 562 findings on our own corpus under its
  defaults and zero once the project's real conventions are declared** —
  not one was a defect. The lesson transfers: *a linter run without its
  configuration measures whose defaults you inherited, not quality* — and
  **pumllint's defaults are equally opinionated**. Also: a
  **linter-vitality pattern** reaching its third instance — parser alive,
  standalone linter stale (`@cucumber/gherkin` v42 shipped 2026-08-05;
  `gherkin-lint` last shipped 2023-12-20) — with **BPMN as the
  counter-example that explains it**: `bpmnlint` is embedded in the
  modeler. Stated as a predictor, with the uncomfortable implication for
  a standalone CLI faced rather than buried.
- [The ADR / arc42 ecosystem, evaluated](adr-arc42-ecosystem-evaluation.md)
  — dated evaluation (2026-08-29), twenty-eighth, and the second subject
  already inside the project — ADRs are named in the catalogue (GEN007,
  DIM-TRC) and in the CLI's own help. **Nothing to adopt, and the note
  found a defect instead.** `trace --requirements-scan` builds an **empty
  inventory** against both dominant ADR conventions — adr-tools and MADR
  keep the identifier in the *filename*, and `scan_inventory` matches
  against file **contents only** — then reports the diagram's correct
  `ADR-0001` references as *"a typo, or the inventory is stale"*. With
  `--fail-on-unknown-ref` it **exits 1 on correct input**. A control
  layout that spells the ID in the body scans fine, so the feature works
  on a convention almost nobody uses. **Both repairs have since shipped**
  — `scan_inventory` matches filenames as well as contents, and an empty
  inventory now draws a stderr warning naming the source and the pattern,
  exit code unmoved — **and implementing them corrected the note**: the
  proposed filename fix does *not* rescue the bare-number layouts, because
  `ADR-\d+` matches neither their body nor their filename. The note
  carries that correction inline.
- [Semgrep and rules-as-data, evaluated](semgrep-rules-as-data-evaluation.md)
  — dated evaluation (2026-08-29), twenty-ninth and a narrowing return on
  the Spectral note, whose boundary rested on a 13-function library and so
  invited the objection *the limit is Spectral's vocabulary, not
  rules-as-data*. **Semgrep answers it**: rules are data but the
  vocabulary is a pattern language with metavariables, and generic mode
  runs on `.puml`. Measured on a four-rung ladder up this project's own
  rule classes — **lexical works; file-scope absence, identity
  correlation and cross-file identity do not** (2 findings where 1 is
  correct, twice). **The boundary is state, not vocabulary**:
  `pattern-not-inside` scopes to a region enclosing the match, never the
  file, so "no `participant … as $X` anywhere" is not expressible.
  Consequence: the Spectral note's declarative-rule-layer candidate is
  **narrowed, not closed**. *(Corrected by the policy-as-code note: the
  narrowing to "the lexical tier and nothing above it" is too strong — a
  checkov YAML policy expresses declaration-versus-use in data, because it
  is evaluated against a resolved graph rather than text positions.)*
- [The policy-as-code ecosystem, evaluated](policy-as-code-ecosystem-evaluation.md)
  — dated evaluation (2026-08-29), thirtieth. **No adoption — and it
  corrects the note before it.** The Semgrep note concluded a declarative
  rule layer was "viable for the lexical tier and nothing above it"; a
  checkov custom policy in **pure YAML** expresses `cond_type: connection`
  and discriminates a resource that references a security group from one
  that does not — **SEQ001's exact shape, in data**. The real boundary is
  not data-vs-code but **what the rule is evaluated against**: text
  positions versus a **resolved graph**. Also measured: checkov's
  `--create-baseline`/`--baseline` is **pumllint's ratchet, independently
  arrived at** — but it ratchets a *finding set* where we ratchet a
  *level*, because it computes none, so the grading gap reappears as a
  missing **axis** rather than a missing report. **OPA/Rego/Conftest were
  not run** — the engine's download resolves to a GitHub release asset —
  so nothing here is a claim about Rego.
- [The TLA+ / Alloy ecosystem, evaluated](tlaplus-alloy-ecosystem-evaluation.md)
  — dated evaluation (2026-08-30), thirty-first. TLA+/Alloy were **already
  settled** in 2026-08-02's model-verification note, which examined
  *sequence* diagrams; this asks what it did not, about **state**
  diagrams. **Neither tool was run** — absent from every package registry
  — so the executed substance is the pumllint side. Measured: STA002
  catches **in-degree zero** but is silent on a **disconnected island**
  and on a **sink**. The island is **not a gap** — the docstring and
  RULES.md both say in-degree only, a line drawn on purpose. The
  contribution is a distinction: *"deadlock-freedom is a category error"*
  is scoped to sequence diagrams, where PlantUML supplies no concurrency
  semantics — but a **state machine's transition graph is declared
  verbatim**, so reachability from `[*]` invents nothing. **Decidable,
  yes; desirable, unestablished** — an absorbing terminal state is a
  legitimate model. Two candidates recorded, neither proposed as a build.
- [The Mermaid ecosystem, re-examined](mermaid-ecosystem-reexamined.md)
  — dated evaluation (2026-08-30), thirty-second and the **second
  re-examination**. The sixth note said in its own bounds that **no
  Mermaid tool was executed**, and its candidate 2 asked for a re-check;
  both linters were installed and run. **Unlike the BPMN re-examination,
  the convergence claim survives**: all eight semantic rules fire with
  matching names. **One correction** — the documented suppression form is
  rejected in practice; `mermaid-lint` **requires a justification** at the
  suppression site. **One sharpening** — `duplicate-ids` is the *only*
  error-severity semantic rule, so the tool rates identity above
  everything else it checks, a third instance of that pattern across four
  artefact classes. And new to the record: **the aggregate does double
  duty** — `100/100 (3 suppressed)` is a disclosure channel that only
  exists because there is a score to annotate.
- [The D2 ecosystem, re-examined](d2-ecosystem-reexamined.md)
  — dated evaluation (2026-08-30), thirty-third and the **third
  re-examination**, picked by the bounds scan because the seventh note's
  refusal rested partly on a claim about D2's own tooling. **Ground (3) is
  corrected, and the correction cuts *against* the refusal.** D2's
  compiler (run via the WASM build) rejects syntax errors and unknown
  shape keywords but **accepts every semantic defect tested** — self-loop,
  duplicate connection, unlabelled connection, which are SEQ006 and SEQ005
  on the PlantUML side. So D2 ships more *syntax* tooling; **the semantic
  gap is the same size, not narrower.** The refusal stands on grounds (1)
  and (2) — and **(2) is now load-bearing and fragile**, resting on
  upstream's stated intention to build a linter. Also corrects the bounds
  scan's own D2 row: `@terrastruct/d2` is a WASM library, not the CLI, so
  **registry presence is not runnability**.
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
- [Positioning pumllint — the quadrant and the wheel](positioning-quadrant.md)
  — dated positioning note (2026-08-28): two hand-authored figures with
  every placement derived from a published rule. A Gartner-style quadrant
  of the diagram-as-code checking field
  ([the figure](positioning-quadrant.svg)): eight tools, an
  eight-criterion rubric, and an **empty Leaders quadrant** — the
  incumbents execute and stop at findings, the visionaries carry the
  semantic layer without the adoption, and pumllint holds the vision edge
  alone from below the execution midline, scored with the same candour
  the ecosystem series applies to everyone else. And the SAFe DevOps
  wheel ([the figure](safe-devops-wheel.svg)): the Continuous Delivery
  Pipeline's four aspects with the SDLC assessment's sixteen claim marks
  reproduced exactly, and the validator field placed upstream and
  downstream — the gating pattern the pipeline already trusts for code,
  containers and infrastructure, argued back to the design artefact they
  all descend from.
