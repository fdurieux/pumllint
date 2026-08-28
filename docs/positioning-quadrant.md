# Positioning pumllint — the quadrant and the wheel

*Dated positioning note, 2026-08-28, written against `51bc97d` (v0.30.0).
The question as posed: a Gartner-style quadrant positioning pumllint
against the tools in its playing field, and a SAFe DevOps wheel placing
pumllint among the validators upstream and downstream of it. Both figures
are hand-authored SVGs; every dot position and every claim mark is derived
from a rule stated in this document, so the placements can be audited and
re-derived, which is the only way a vendor's self-drawn quadrant deserves
to be read.*

**The picture up front: the Leaders quadrant is empty.** Scored against
the rubric below, no checker of diagram-as-code artefacts yet pairs a
graded verdict with an installed base. The incumbents — PlantUML's own
`-checkonly`, Structurizr DSL, D2, `bpmnlint` — execute well and stop at
syntax, inspections or findings; the visionaries — pumllint and
`@mermaid-lint/cli` — carry the semantic rule layer but not yet the
adoption. pumllint holds the far edge of the vision axis alone, on the
strength of the one layer nobody else has built (a maturity score, gap
reports, a ratchet, traceability), and sits below the execution midline
for reasons this project states about itself: deliberately 0.x, adoption
unproven, evidence still being accumulated. A chart that placed pumllint
top-right would be marketing; this one is the same candour the
[ecosystem series](mermaid-ecosystem-evaluation.md) applies to everyone
else, applied to the home team.

## 1. What this is, and is not

This is a **self-assessment in the form of a Gartner-style quadrant**. It
is not a Gartner artefact: "Magic Quadrant" is Gartner, Inc.'s trademarked
research format, produced by independent analysts against proprietary
criteria; nothing here is theirs, and the resemblance is layout, not
authority. Where Gartner's axes are judged, these are computed: two 0–20
sums over eight published criteria, boundaries at the midlines, no
weighting. The rubric is this note's own construction and can be argued
with — that is what publishing it is for.

One boundary holds throughout, inherited from the
[UML evaluation's claim-language audit](uml-ecosystem-evaluation.md):
**pumllint is a PlantUML linter, not a "diagram linter"**. The field
charted here is *checkers of diagram-as-code artefacts*, and every tool in
it — pumllint included — gates exactly one notation. The chart compares
category peers across notations; it does not imply any tool covers a
neighbour's artefact.

## 2. The field

![Positioning quadrant of diagram-as-code checkers: the Leaders quadrant
is empty; pumllint sits deep in Visionaries; the incumbents cluster in
Challengers](positioning-quadrant.svg)

**Included**: tools whose job is to deterministically check a textual
diagram-as-code artefact — eight dots, one per tool. The two closest are
already on this project's record: `@mermaid-lint/cli` is *"a
near-complete architectural mirror of pumllint"* and `bpmnlint`
*"architecturally the same product"*
([Mermaid](mermaid-ecosystem-evaluation.md),
[BPMN](bpmn-ecosystem-evaluation.md) evaluations). Structurizr DSL enters
with a dagger: the [Structurizr
evaluation](structurizr-dsl-ecosystem-evaluation.md) reclassified it as a
*producer* of the artefact pumllint gates, so it is scored here on its
checking layer only (`structurizr-cli validate` and its 26 named
inspections), with the caveat in §4 about what its model-first design
does to that layer's size.

**Excluded**: rendering-focused CI actions (they draw, they don't check);
editor plugins as such (an integration channel, not a checker); model-side
validators of non-diagram artefacts (SHACL, Archi, SDMetrics — different
artefact class); Spectral (the proven pattern for *API* contracts that
[the case document](case-for-pumllint.md) cites, but its artefact is an
OpenAPI description, not a diagram — it reappears in Part 2 where it
belongs); and MermaidGuard plus `mermaid-check`, two further Mermaid
checkers surfaced by a 2026-08-28 web search whose facts could not be
verified beyond search summaries — an unverifiable dot is worse than a
named exclusion.

## 3. The rubric

**Completeness of vision** — how much of "artefact quality" the tool's
model covers. Four criteria, 0–5 each:

- **V1 — syntax validity.** Does passing the tool certify the artefact
  parses? 5 = the tool is, or defers to, the notation's authoritative
  acceptor.
- **V2 — style & hygiene rule layer.** Configurable rules beyond parsing:
  per-rule severities, profiles/presets, inline suppressions, autofix,
  extensibility.
- **V3 — semantic & model consistency.** Rules about what the artefact
  *means*: balanced lifecycles, one-entity-one-identity across a model
  set, and the content of labels rather than their presence.
- **V4 — governance & measurement.** A verdict above the finding list:
  levels or scores, gap reports, baseline/ratchet, requirement
  traceability, audit-ready evidence.

**Ability to execute** — whether the tool delivers that vision at scale.
Four criteria, 0–5 each:

- **E1 — maturity & stability.** Age, versioning, stated compatibility
  contracts.
- **E2 — adoption & reach.** Observed installed base, and the footprint of
  the artefact class the tool can actually gate.
- **E3 — integrations.** CI, pre-commit, editors, dashboards.
- **E4 — sustaining backing.** Who keeps it alive: company, foundation,
  ecosystem, individual.

## 4. The scores

| Tool (notation) | V1 | V2 | V3 | V4 | **Vision** | E1 | E2 | E3 | E4 | **Execute** | Lands in |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| **pumllint** (PlantUML) | 4 | 5 | 5 | 5 | **19** | 2 | 1 | 4 | 2 | **9** | Visionaries |
| PlantUML `-checkonly` | 5 | 0 | 0 | 0 | **5** | 5 | 5 | 4 | 4 | **18** | Challengers |
| `bpmnlint` (BPMN) | 3 | 4 | 3 | 0 | **10** | 4 | 4 | 4 | 4 | **16** | on the Leaders line |
| Structurizr DSL † | 5 | 2 | 2 | 0 | **9** | 5 | 3 | 4 | 4 | **16** | Challengers |
| D2 compile + `fmt` | 5 | 1 | 0 | 0 | **6** | 4 | 3 | 3 | 5 | **15** | Challengers |
| `@mermaid-lint/cli` | 5 | 4 | 2 | 0 | **11** | 2 | 3 | 3 | 1 | **9** | Visionaries |
| LikeC4 | 4 | 1 | 2 | 0 | **7** | 3 | 2 | 3 | 2 | **10** | on the Challengers line |
| `@probelabs/maid` (Mermaid) | 3 | 2 | 1 | 0 | **6** | 1 | 3 | 2 | 1 | **7** | Niche Players |

† producer of the artefact class, scored on its checking layer only.

The cells that decide the chart, argued:

- **pumllint V3=5, V4=5, alone in both.** The content-level semantic rules
  (vagueness and prose lexicons, guard evaluability, elision markers —
  SEQ103/105/106/109) and the cross-diagram identity pack (XD001–XD005)
  have no counterpart in any tool here: `mermaid-lint` checks that a label
  *exists*, pumllint also checks what it *says*
  ([Mermaid evaluation §3.1](mermaid-ecosystem-evaluation.md)). V4 is the
  series' refrain — seventeen ecosystems evaluated, *"no checker of this
  artefact class produces a level, a gap report, a ratchet or an
  aggregate"* — plus traceability (`trace`), SonarQube export, and a
  [measured maturity↔codegen-fidelity relationship](evidence-explained.md)
  behind the score. V1=4, not 5: the built-in parser is pumllint's own;
  authoritative syntax certification is available but optional
  (`--check-syntax` invokes the real PlantUML).
- **pumllint E1=2, E2=1, and this row is the point of the exercise.** The
  project is deliberately 0.x — 1.0 waits on *"evidence that the score
  contract survives contact with a foreign corpus"*, not on features — and
  its adoption is a pilot programme, not an installed base. Writing those
  two numbers higher would contradict the project's own README. E3=4 is
  earned (GitHub Action, two pre-commit hooks, SonarQube generic import,
  five reporters); the missing point is editor-time integration, which
  `bpmnlint` has and pumllint does not.
- **PlantUML `-checkonly` is the mirror image.** Its acceptance *defines*
  valid PlantUML (V1=5) and it runs wherever Java runs, at effectively
  total reach over the notation (E2=5) — and it checks nothing else, by
  its own admission: a drawing tool, not a modeling tool. The
  [README](../README.md) recommends it as a companion step, and this chart
  is why: the two dots are complements, not competitors.
- **`bpmnlint` stands on the Leaders doorstep, on the boundary line.**
  Roughly 25 configurable rules, three presets, a plugin API, and — unique
  in this field — live feedback inside the modeler (`bpmn-js-bpmnlint`),
  sustained by the bpmn.io/Camunda ecosystem. What blocks the last step is
  V4=0: no grade, no aggregate. It is the strongest evidence in the field
  that execution and the verdict layer are separable — and that nobody has
  yet shipped both.
- **Structurizr DSL's checking layer is thin *because* its design absorbed
  the problem.** One model, many views: the identity drift pumllint hunts
  with XD rules is inexpressible in a workspace, so there is less left to
  check (V3=2 as a checker; as a *prevention* strategy it is the strongest
  in the field). It competes upstream of this chart — as a producer — and
  its 26 inspections stop at advisory findings.
- **D2 is an open niche on its own roadmap.** Compiler and canonical
  formatter, commercial backing (Terrastruct, E4=5) — and the roadmap
  line *"Build a configurable linter"* concedes V2/V3 are futures, not
  features ([D2 evaluation](d2-ecosystem-evaluation.md)).
- **`@mermaid-lint/cli` is the nearest dot and the fastest-moving one.**
  Authoritative parse fallback (`mermaid.parse()`, V1=5), a real rule
  layer with severities, suppressions, `--fix` and a GitHub Action
  (V2=4), presence-level semantics (V3=2) — and it lints fenced diagrams
  inside Markdown, in the notation where AI-authored diagrams actually
  land. Execution is early: 0.x, weeks old at evaluation, no licence
  field on npm, single maintainer (E1=2, E4=1). It reached 0.53.1 in
  under ten weeks.
- **LikeC4 delegates its semantic layer** (structural validation built in,
  custom rules handed to user-written Vitest tests via its Model API), and
  **`@probelabs/maid`** trails `mermaid-lint` on every criterion the
  [Mermaid evaluation's table](mermaid-ecosystem-evaluation.md) compares.

## 5. Reading the chart

**The empty top-right is the category claim, drawn.** Every incumbent
that can execute stops below the vision midline or on it; both tools past
the vision midline sit below the execution midline. The field has
validated the category twice over — two independent teams converged on
pumllint's rule concepts for other notations — and no one occupies the
quadrant where a graded verdict meets an installed base.

**What would move pumllint up** is exactly what
[README](../README.md) says 1.0 waits on: the score contract surviving a
foreign corpus, and adoption evidence from the
[pilot programme](pilot-charter.md). E1 and E2 are the two numbers the
project can only earn, not write.

**What would redraw the chart** is already on this project's record as a
re-litigation trigger: *"`mermaid-lint` or Maid shipping a level, score
or maturity verdict — the single event that would contest the
differentiator directly, from the notation with the volume."* On this
chart, that event moves `@mermaid-lint/cli` right, toward the empty
quadrant, from a better execution base than pumllint's. The empty
top-right is an opportunity precisely because it will not stay empty.

## 6. Part two: the SAFe DevOps wheel

The quadrant answers *against whom*. The wheel answers *where in the
pipeline, and alongside whom*: pumllint is one instance of a general
pattern — a deterministic validator gating a standards-bearing artefact
class — and every segment of the delivery pipeline has its own artefacts
and its own gates.

![The SAFe Continuous Delivery Pipeline as a four-segment wheel, with
pumllint's sixteen practice-domain claims marked and the neighbouring
validators placed upstream and downstream](safe-devops-wheel.svg)

The wheel's structure is the SAFe® Continuous Delivery Pipeline (Scaled
Agile, Inc. — nomenclature only, no endorsement implied): four aspects,
sixteen practice domains, flowing clockwise. The claim marks on the
sixteen domains reproduce the
[appendix table of the SDLC assessment](value-in-the-sdlc.md) exactly —
direct at **Architect**, **Develop** and **Build**; supporting where the
outputs are used (Collaborate & Research, Synthesize, Measure, Learn);
inherited where responders and auditors merely benefit from artefacts
kept trustworthy upstream; and **no claim across most of Continuous
Deployment**, stated rather than airbrushed. Five of sixteen domains
carry no claim; an instrument that scored well everywhere should worry
you.

Around the wheel, the field of fellow gates, placed where their artefact
is checked:

| Segment | Artefact class | Deterministic gate | Relative to pumllint |
|---|---|---|---|
| CE | requirements & prose specs | vale, markdownlint | **upstream** — intent precedes design |
| CE | **architecture diagrams (`.puml`)** | **pumllint** | the subject |
| CE | API contracts | Spectral | peer — the proven pattern for a neighbouring artefact |
| CE | process models (`.bpmn`) | `bpmnlint` | peer |
| CE | C4 models | Structurizr DSL `validate`, LikeC4 | peer |
| CI | source code | ESLint, ruff, SonarQube | **downstream** |
| CI | commit messages | commitlint | downstream |
| CI | Dockerfiles | hadolint | downstream |
| CI | CI workflows | actionlint | downstream |
| CD | infrastructure as code | tflint, checkov | downstream |
| CD | Kubernetes manifests | kubeconform | downstream |
| CD | policy as code | OPA conftest | downstream |
| RoD | licence compliance | REUSE lint | downstream |
| RoD | SBOMs | NTIA conformance checker | downstream |
| RoD | design-governance evidence | pumllint badge & HTML report | the subject, supporting |

Two readings follow. **Downstream artefacts are gated; the upstream one
mostly is not.** Everything to the right of Architect on this wheel —
code, commits, containers, infrastructure, policy, licences — has an
established deterministic gate that CI runs without anyone debating it.
The design artefact those gates all descend from is the one class where
"the linter" was, until recently, a syntax check. pumllint's position is
that the pattern the pipeline already trusts everywhere downstream
belongs at the source too. **And the wheel is a loop**: Learn feeds
Hypothesize, which is where the gap reports and the maturity trend —
RoD's supporting claims — hand the next iteration its improvement
backlog.

## 7. Bounds

None of the external tools named in either figure was executed for this
note. Facts about `@mermaid-lint/cli`, `@probelabs/maid`, `bpmnlint`,
Structurizr DSL, LikeC4 and D2 are read from this repository's own dated
evaluations (2026-08-27/28), which carry their own bounds — notably that
those tools were characterized from published documentation and registry
metadata, not paired runs. The downstream tools in Part 2 (ESLint through
NTIA conformance checker) are named as representatives of their artefact
class, not evaluated or endorsed; the list is illustrative, not a survey.
MermaidGuard and `mermaid-check` were excluded for unverifiability (§2).
Gartner's actual Magic Quadrant criteria are proprietary and were not
consulted; the resemblance is deliberate in form and absent in method.
The rubric weights all eight criteria equally because any other weighting
would be a second, hidden judgment; the scores themselves are argued in
§4 and are exactly as contestable as their arguments. Dot positions are
mechanical: `x = 200 + 28·Vision`, `y = 640 − 28·Execute` in the SVG's
coordinate space.

## Related reading

- [The Mermaid ecosystem, evaluated](mermaid-ecosystem-evaluation.md) —
  the direct substitute, the near-mirror linter, and the re-litigation
  trigger §5 leans on.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) —
  `bpmnlint`, the field's best executor and the first convergent
  validation of the rule catalog.
- [The Structurizr DSL ecosystem, re-examined](structurizr-dsl-ecosystem-evaluation.md)
  — the producer reclassification behind the dagger.
- [The D2 ecosystem, evaluated](d2-ecosystem-evaluation.md) — the open
  niche and the roadmap line.
- [pumllint in the SDLC](value-in-the-sdlc.md) — the claim-by-claim SAFe
  assessment the wheel's sixteen marks reproduce.
- [Where tooling pays](sdlc-tooling-landscape.md) — the Wardley map this
  note's figures complement: evolution there, competition and pipeline
  position here.
- [The case for pumllint](case-for-pumllint.md) — the landscape survey
  ("what else is out there") and the Spectral analogy.
