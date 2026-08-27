# The C4 model ecosystem, re-examined — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `8fa5339` (v0.29.0). The
question as posed: investigate the C4 model ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem.*

**Verdict up front: the 2026-07-27 settlement stands — fit verified, wait
for census pull — and this re-examination changes nothing about the
decision. It changes three things about the record behind it. First, the
internal motivation is *stronger* than the settlement recorded: the
codegen profile, which `docs/agents.md` tells agents to run, is
**completely silent** on a well-formed C4 container diagram — 100.0 on
every one of the six dimensions, held at Level 1 only by cap C4 — and on
arrow-mixed C4 it now emits **8 findings including 4 blockers and exits
1**, seven of the eight false in C4 semantics. Neither was measured in
2026-07-27, which ran the default profile only. Second, the demand
evidence is *weaker* than the shorthand suggests: the census's "C4 macros
in 46% of files" and the corpus's "45% of files come from the C4-PlantUML
project's own sample gallery" are very nearly the same files. Both numbers
are disclosed in the census note, in different sections; their near
identity is not drawn, and the one sentence that reads a build signal off
the first is where it matters. Third, the market boundary moved: the C4
ecosystem took an AI turn since July, and it is the *vendors* who took
it.**

**Three claim-language corrections follow, and one trigger needs a guard.
"Nothing checks hand-written C4-PlantUML" must narrow again — a
third-party plugin does parse these files with an ANTLR grammar, for
architecture conformance rather than quality. "The defect list is
externally authored" is true, and about **40% mechanizable**: of the 21
C4 review-checklist items re-verified today, roughly 8 are checkable from
`.puml` text and the rest are about rendered colours, shapes, icons,
arrowheads, border styles and element sizes — the picture, not the
source. And the build trigger's words "a real corpus" need an operational
exclusion rule, because the instrument's only existing C4 reading is
mostly the notation's own examples.**

**What does *not* move is the differentiated position, and this
evaluation strengthens it from a third independent direction. Structurizr
inspections configure severity across four levels and report per-finding;
LikeC4 validates structurally and hands custom rules to Vitest; and, from
yesterday's evaluation, Linked.Archi's SHACL conformance is binary. Three
independently built C4-capable validators, three different technology
stacks, and **not one of them grades**. No maturity level, no gap report,
no ratchet, no aggregate score anywhere in the ecosystem. That territory
is still empty, and it is still gated on an adopter rather than on
whether the territory is attractive.**

*Bounds. Every pumllint claim below was executed against the working tree
at `8fa5339` with default config on files outside the repo, so the
project's own `pumllint.toml` is not in play (verified: GEN006/GEN007 stay
dormant). External claims were read from published documentation on
2026-08-27 with page URLs given. **No C4 tool was executed here**, and —
per this session's repository scope — **no GitHub repository was read**:
claims about C4-PlantUML's macro surface, the `jqassistant-c4-plugin` and
Mermaid's C4 syntax are characterized from vendor documentation sites and
web-search summaries, not from source. The c4model.com tools table could
not be retrieved (`/tooling/` 404s; `/tooling` returns the framing text
without the table), so tool-ranking claims are attributed to third-party
comparisons and marked as such. Where a 2026-07-27 claim is corrected
below, the correction is to *claim language*, and the underlying
measurement is re-run rather than assumed.*

## 0. Why this ran, and what it is not

The C4-PlantUML pack is a **settled question** (ROADMAP § Settled
questions, 2026-07-27), backed by a full fit evaluation
([c4-pack-evaluation.md](c4-pack-evaluation.md)) and an evidence
extension ([c4-codegen-detail-experiment.md](c4-codegen-detail-experiment.md)).
The working agreements say not to re-litigate a settled question without
new evidence.

So this note deliberately does **not** re-derive the fit case. It does
three things the settlement's own discipline asks for and nobody had
done:

1. **Re-measures the dated behavioural claims** at HEAD. The settlement's
   numbers were measured on v0.23.0; six minor versions have landed
   since, including parser and typing changes (`is_reversed` half-arrows,
   legend-body parsing, delay arrows). This repository was burned one
   release ago by exactly this — sixteen behavioural changes under one
   version string — so re-running a dated claim is house work, not
   ceremony.
2. **Widens the frame from one notation to the ecosystem.** The 2026-07-27
   note assessed C4-PlantUML as a rule pack. It did not assess Structurizr
   DSL, LikeC4, IcePanel, Mermaid C4, or the AI/MCP layer that did not
   exist in that form. Those are where the ecosystem's centre of gravity
   now sits, and each implies a different fit.
3. **Audits the trigger.** A build gate is only as good as the instrument
   that fires it. §8.4 audits the one C4 reading that instrument has
   produced.

Nothing here is queued. §10 records the corrections and what would have
to become true.

## 1. The C4 ecosystem as it stands

### 1.1 The method, and its own bias

C4 is a method before it is a tool: four levels (context, container,
component, code), a published
[review checklist](https://c4model.com/diagrams/checklist), and per-level
scope rules. The method's own [tooling guidance](https://c4model.com/tooling)
is explicit that **modelling is recommended over diagramming** — modelling
tools give "semantic understanding" of the architecture, querying, and
element management, against the "boxes and lines" limits of diagramming
tools.

That is the ecosystem's centre of gravity, stated by its author, and it
points *away* from C4-PlantUML. C4-PlantUML is a diagramming approach: a
macro library that renders pictures. Structurizr and LikeC4 are modelling
approaches: a model with views projected from it. The distinction matters
for every fit below, because pumllint's asset — a parser over diagram
*source* — is native to the side the method does not recommend.

### 1.2 The layers, and who validates what

| Layer | Examples | Validation it ships |
|---|---|---|
| **Models as code** | Structurizr DSL, LikeC4 | Structurizr: 26 named inspections (list read 2026-08-27). LikeC4: DSL/structural validation + a Model API for user-written rule tests. |
| **Diagrams as code** | C4-PlantUML, Mermaid C4 | **None.** C4-PlantUML is macros over a renderer; Mermaid C4 is an experimental renderer plugin. |
| **Visual modelling** | IcePanel, Archi, draw.io | Tool-internal model constraints; not source-checkable |
| **Graph / integration** | Linked.Archi (SHACL), jQAssistant (+ C4 plugin) | Conformance of the derived graph, or of code against diagram |

[Structurizr's inspections](https://docs.structurizr.com/workspaces/inspections)
are the richest published rule set in the ecosystem, and richer than the
2026-07-27 note captured. Re-read today, they cover: workspace scope and
tooling; empty model; missing description on person, software system,
container, component, deployment node and infrastructure node; missing
technology on container, component, deployment node and infrastructure
node; software systems with containers but no documentation and no
decisions; empty deployment nodes; **disconnected elements**; **elements
in no view**; missing relationship description and technology; empty
viewsets and views; view key and layout violations; element styles with
`metadata` false; and embedded-view inspections in documentation. All
default to `error`, and each is configurable to `ignore` / `info` /
`warning` / `error` via a `structurizr.inspection.*` workspace property.

[LikeC4](https://likec4.dev/) validates differently. Its built-in layer is
structural — DSL parsing and IDE syntax checking — and its
[guide to enforcing rules](https://likec4.dev/guides/validate-your-model/)
hands semantic constraints to the user: query the model through the
LikeC4 API and assert with Vitest, run in CI. Its worked example is
*"enforce that every element of kind `app` has a `technology`
specified"*. Note what that is: the same rule as Structurizr's
`model.container.technology` inspection, and the same rule as tier 1 of
this repository's own candidate C4 catalog. Three independent
implementations of one check is a strong signal the check is real.

### 1.3 The AI turn — the material change since July

This is what is genuinely new, and both major models-as-code tools made
the same move.

[Structurizr's AI page](https://docs.structurizr.com/ai) argues the DSL is
a good LLM target because "LLMs excel at generating text - the Structurizr
DSL is text-based, version controllable, and diff-friendly", and ships an
**MCP server** that "provides DSL validation, parsing, and inspection
tools to assist with creating software architecture models". Its
inspection feature is explicitly positioned inside the agent loop —
"especially when used via the Structurizr MCP server" — and the models-as-code
row of its own comparison marks only Structurizr as recommended for AI
workflows.

[LikeC4's AI tooling](https://likec4.dev/tooling/ai-tools/) ships two
mechanisms: **agent skills** (`npx skills add https://likec4.dev/`,
integrating with Claude Code, Cursor and Windsurf) whose stated purpose is
to let agents "write DSL code without hallucinating", and an **MCP
server** (`likec4 mcp`) exposing element search, relationship analysis,
graph traversal, metadata/tag queries and view access.

The two strategies are worth separating, because they land on opposite
sides of this project's thesis:

- **LikeC4's skill is prevention** — teach the agent the syntax so the
  artefact comes out well-formed. Upstream of the gate.
- **Structurizr's MCP is verification** — hand the agent validation and
  inspection tools and let it check its own output. That is the
  score → repair → re-score shape `docs/agents.md` describes, built by
  the C4 ecosystem's reference implementation, for its own DSL.

An ecosystem independently arriving at "give the agent a checker, not just
a syntax lesson" is corroboration of this project's positioning. It is
also a door closing on one side of it (§7, F2).

## 2. The seam, and how much of it is reachable

```
   the C4 ecosystem                          what pumllint can see
   ─────────────────────────────────────     ─────────────────────
   Structurizr DSL   ──► inspections ──► MCP      ✖ .dsl never discovered
   LikeC4 DSL        ──► validate    ──► MCP      ✖ .c4  never discovered
   IcePanel / Archi  ──► tool-internal            ✖ not source at all
   Mermaid C4        ──► renders                  ✖ .mmd / fences not discovered
   C4-PlantUML .puml ──► renders                  ✔ discovered — and misread
```

`PUML_EXTENSIONS = (".puml", ".plantuml", ".iuml", ".wsd")`
(`pumllint/engine.py:177`). Measured on a directory holding a Structurizr
`workspace.dsl` and a Mermaid `c4.mmd`:

```
$ python3 -m pumllint .
warning: no PlantUML files found in . (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint workspace.dsl
warning: 1 file(s) contained no @startuml block and were not checked: workspace.dsl
✔ No issues found.                                                    (exit 0)
```

That is the "nothing was checked" contract behaving exactly as specified —
warns on stderr, does not touch the exit code. **On the two formats where
the ecosystem's centre of gravity now sits, pumllint is silent and says so.
On the one dialect it can see, it is not silent and not right.** That
sentence is the whole boundary, and §8 measures both halves.

## 3. Overlap — where the ecosystem already checks what a C4 pack would

| Candidate C4 rule (2026-07-27 sketch) | Structurizr | LikeC4 | Linked.Archi | Status |
|---|---|---|---|---|
| Missing element description | `model.*.description` (6 inspections) | user rule | SHACL label shapes (presence/typing) | **Occupied** on the modelling side |
| Missing technology on Container/Component | `model.container.technology`, `model.component.technology` | the documented worked example | domain/range shapes | **Occupied** — three implementations |
| Orphan element (declared, never related) | `model.element.disconnected` | user rule | — | **Occupied** |
| Unlabelled relationship | `model.relationship.description` | user rule | label shapes | **Occupied** |
| Relationship technology/protocol | `model.relationship.technology` | user rule | — | **Occupied** |
| Undeclared alias in a `Rel` | n/a — a DSL cannot express it | n/a | n/a | **PlantUML-only defect** |
| Abstraction mixing (Component in a container view) | prevented by construction ("components can't be added to a container diagram") | *not* prevented — kinds come from a user-written specification | — | **PlantUML-only defect** |
| Missing legend / `SHOW_LEGEND()` | n/a (renders its own key) | n/a | notation sets | **PlantUML-only defect** |
| Level/maturity, gap report, ratchet | **none** | **none** | **none** | **Unoccupied everywhere** |

Two readings fall out, and they pull in opposite directions.

**The completeness rules are occupied on the modelling side and empty on
the diagramming side.** Every rule the 2026-07-27 tier-1 sketch listed
that is *also expressible in a model* has at least one implementation, and
usually three. The rules that remain uniquely pumllint's are the ones that
exist only because C4-PlantUML is a text macro layer with no model behind
it: an alias referenced but never declared, an abstraction level mixed
inside one file, a missing legend macro. Those are real defects — they are
just defects of the *diagramming* approach, which is the approach the
method itself does not recommend.

**Nothing anywhere grades.** Structurizr configures severity but reports
per finding with no aggregate. LikeC4's Vitest route reports test
failures. Linked.Archi's SHACL conformance is binary (yesterday's
evaluation, §1.2). No level, no dimension weighting, no gap report, no
baseline, no ratchet, no badge. The maturity model has no competitor in
this ecosystem — which is the honest form of the positioning claim, and is
unchanged since July except that it now rests on three observations
instead of one.

## 4. Boundaries

1. **Method vs artefact.** C4 is a set of abstractions and a review
   checklist. pumllint checks one serialization of it. Roughly 60% of the
   published checklist is about the rendered picture (§8.3) and is
   unreachable from source by anyone, this project included.
2. **Model vs diagram.** A model can make a defect unrepresentable
   (Structurizr: "components can't be added to a container diagram"). A
   diagram cannot — which is why representable ill-formedness is this
   product's premise, and why the modelling tools' checks are thinner
   than they look: they check what their type system left open.
3. **Check vs grade.** Everyone checks. Nobody grades. §3.
4. **Discovered vs not.** `.dsl`, `.c4`, `.mmd` and markdown fences are
   outside the file surface by construction, and the warning says so.

## 5. Sense — four true things

**S1. Re-measurement was worth running, and the claims held.** The
2026-07-27 numbers reproduce at v0.29.0 to the decimal (§8.1). Six minor
versions of parser and typing changes did not touch C4 behaviour. That is
a small result and a real one: the settlement can be cited as current
rather than as dated.

**S2. The internal motivation is stronger than the settlement recorded.**
The original measured the default profile. Under the **codegen** profile —
the one this project tells agents to run before generating — a well-formed
C4 container diagram scores 100.0 on all six dimensions and reports
nothing, and an arrow-mixed one hard-fails with four blockers that are all
wrong. The settlement's own strongest argument ("a pack would not merely
add coverage; it would correct wrong output on an input class the tool
currently misreads") is understated in its own record.

**S3. The ecosystem's AI turn corroborates the thesis, from the far
side.** Structurizr's MCP server hands agents *validation and inspection*
tools, not just syntax. That is an independent arrival at the claim
`docs/agents.md` makes — that the artefact should be gated before the
agent generates from it — by a vendor with no stake in this project's
argument, in the same quarter. Corroboration from a competitor's
roadmap is the strongest kind available.

**S4. The one place the Mermaid sibling-stack cost collapses is C4.** The
Mermaid record (2026-07-26) treats Mermaid as a full sibling stack:
parser, corpus, calibration, golden. That is right for sequence, class and
state, whose Mermaid syntax shares nothing with PlantUML's. It is *not*
right for C4: Mermaid's C4 plugin is deliberately syntax-compatible with
C4-PlantUML — `Person()`, `System()`, `System_Ext()`, `Container()`,
`Rel()`, `Container_Boundary()` — so a C4 macro recognizer would largely
transfer. The pipeline cost (discovery, fence extraction) does not
transfer, and the embedded-PlantUML demand scan already failed on exactly
that. But the *recognizer* economics are different here than the general
Mermaid record implies, and that is worth knowing before either item is
ever picked up.

## 6. Nonsense — four moves to refuse

**N1. Building for Structurizr DSL or LikeC4. Refused, and more firmly
than in July.** Both are separate languages with their own toolchains,
both now ship validation, and both ship an MCP server for the agent
workflow. A third-party checker for a language whose owner already checks
it — and who is shipping that checker into the agent loop — is the
SonarQube-plugin lesson with a faster-moving vendor. The 2026-07-27
"Structurizr DSL is out of scope by decision" needs no revision, only a
stronger reason.

**N2. Reading the ecosystem's AI turn as a demand signal for pumllint.
Refused — it is a demand signal for *their* tools.** Structurizr's AI page
recommends Structurizr; LikeC4's skill teaches LikeC4. Neither is evidence
that anyone wants a `.puml` gate. Treating a competitor's adoption push as
one's own pull is the exact error the embedded-PlantUML demand scan was
built to prevent ("raw token counts are not demand").

**N3. Checking the visual half of the C4 checklist. Refused — no oracle
in the source.** "Do you understand the meaning of all colours used?" and
its seven siblings are questions about a rendered picture and a legend
convention. The decidable residue is one rule — *is a legend declared?* —
which the tier-1 sketch already has. Anything beyond it would be inventing
a convention, which is the settled glossary objection.

**N4. Firing the build trigger off the census figure as it stands.
Refused on validity.** §8.4. The number is disclosed correctly; the
inference from it needs an exclusion rule first.

## 7. Fit — the candidate fits, graded

### F1 — the C4-PlantUML rule pack. **Verdict unchanged: fit verified, wait. Motivation up, demand evidence down.**

The 2026-07-27 analysis holds in full: the macro surface is closed and
regular, the tier sketch stands, and the hard parts (argument tokenizer,
level detection, macro indirection, typing precedence) are unchanged. What
this note adds is a sharper statement of both sides — the wrong-output
problem is worse than recorded (§8.2), and the demand reading is softer
than recorded (§8.4). Those move in opposite directions and the verdict is
the same. **Trigger unchanged, plus the guard in §10.**

### F2 — supporting Structurizr DSL or LikeC4. **Nonsense; stronger than in July.**

N1. Recorded so the next proposal lands on it rather than re-deriving it
from "but everyone uses Structurizr now" — which is true and is an
argument *against*, not for.

### F3 — Mermaid C4. **Recorded, not queued, and gated behind F1.**

S4's recognizer economics are real but do not change the pipeline
objection or the failed demand scan. If F1 is ever built, re-read this
before assuming a Mermaid C4 extension costs a full sibling stack; until
then it costs nothing to have noticed.

### F4 — diagram↔code conformance for C4. **Occupied; corroborates the standing "watch, don't build".**

The 2026-07-26 adjacent-verifiers settlement filed diagram↔code
conformance as "nearest by asset, farthest by scope: requires parsing
implementation languages, straining the zero-dependency promise". There is
now a named incumbent in exactly that slot for C4: the
`jqassistant-c4-plugin` scans C4-PlantUML `.puml` files (context,
container and component diagrams) with a custom ANTLR grammar, folds them
into the jQAssistant software graph, and validates the as-is
(implemented) architecture against the to-be (documented) one. It is a JVM
tool built on a code-scanning graph database — precisely the cost the
settlement declined to pay. *(Characterized from its documentation and
search summaries; two org paths are visible for it, one of them named
`-archive`, and its maintenance status was not verified — see Bounds.)*

### F5 — maturity grading for C4. **The differentiated position; still demand-gated.**

§3's bottom row. Nobody in this ecosystem grades. This is the fit that
would actually be *new* rather than duplicative — and it is unbuildable
without F1, since grading requires a parser. It is therefore not a
separate candidate but the reason F1's ceiling is higher than "another
completeness checker": the tier-1 rules would duplicate Structurizr, and
the *level* would not.

### F6 — publishing the C4 evidence as ecosystem-facing material. **Recorded, not queued.**

[c4-codegen-detail-experiment.md](c4-codegen-detail-experiment.md) measured
something no one else in this ecosystem has published: which C4 spec
ingredients move code-generation outcomes (+29 pp executed for behavioral
content, +8 pp for annotations). With three C4 tools now shipping AI
stories and none of them showing outcome evidence for their inspections,
that measurement is the most differentiated asset this project holds in
this space. Any use of it is a communications decision, not a build, and
the claim-language discipline in the working agreements applies in full.

### Fit against declared constraints

| Declared constraint | Where the C4 fits land |
|---|---|
| **Zero runtime dependencies** | **Passes** for F1 (tokenizer + rules are stdlib). **Fails** for anything touching Structurizr/LikeC4 (Node/JVM toolchains) or jQAssistant. |
| **Deterministic product path, no LLM** | **Passes** throughout. |
| **Byte-stable, contract-pinned outputs** | **Passes with the usual burden** — a new `diagramType` value is an open-set addition the schema already allows. |
| **Golden score contract** | **Material for F1**: a C4 parser turns 0-element diagrams into scored ones, which moves corpus scores and requires a deliberate additive re-freeze. This is the largest re-freeze since sequence. |
| **Demand-driven / Arc E + Arc C bar** | **Fails, and §8.4 says the instrument needs a guard before it can pass honestly.** |
| **Claim language is settled** | **Two corrections required** (§10, C1 and C2). |

## 8. Gap — measured

### 8.1 The dated claims reproduce at v0.29.0

The three appendix samples from
[c4-pack-evaluation.md](c4-pack-evaluation.md), re-run at `8fa5339`
with default config outside the repo:

| Sample | 2026-07-27 (v0.23.0) | 2026-08-27 (v0.29.0) | Verdict |
|---|---|---|---|
| A — pure-macro container | GEN002; Level 1, 99/100 | GEN002; Level 1, **98.75/100**, 0 elements | holds (the note rounded) |
| B — pure-macro dynamic | identical to A; not typed sequence | identical to A; `unknown` | holds |
| C — macros + raw arrows | SEQ009 ×2 + SEQ006; Level 4, 89/100 | SEQ009 ×2 + SEQ006; Level 4, **88.96/100**, 6 elements, typed `sequence` | holds |
| model set over all three | Level 1 (worst-diagram rule) | Level 1, 91.41/100 | holds |

Six minor versions, including parser fixes to half-arrows, legend bodies
and delay arrows, changed nothing here. The settlement's behavioural
record is current.

### 8.2 What the codegen profile does — not previously measured

The 2026-07-27 note ran the default profile. `docs/agents.md` tells agents
to run the **codegen** profile before generating. Measured today:

**A well-formed, named C4 container diagram, codegen profile:**

```
$ python3 -m pumllint --profile codegen c4_named.puml
✔ No issues found.

$ python3 -m pumllint score --profile codegen c4_named.puml
c4_named.puml [internet-banking-containers]: Level 1 (Sketchy) — 100/100
  To reach Level 2 (Structured):
    • diagram has no modelled content — add elements before scoring means anything

  dimensions: DIM-SEM 100.0  DIM-CMP 100.0  DIM-CON 100.0
              DIM-TRC 100.0  DIM-RDB 100.0  DIM-AMB 100.0
```

Every dimension vacuously perfect, the strictest profile silent, and only
cap C4 (`element_count == 0`) standing between that file and a clean
verdict. The census measured the corpus-scale form of this a fortnight
ago: C4-PlantUML's 86 sample diagrams scored **86 × Level 1 with a median
composite of 95**.

**The same file's arrow-mixed sibling, codegen profile:**

```
$ python3 -m pumllint --profile codegen c4_mixed_arrows.puml
… SEQ009 ×2   (C4 Rel() lines read as unpaired sequence returns)
… SEQ101 ×3   (blocker: "declare client/gateway/engine as participants" —
               they are declared, as Person() and Container())
… SEQ006      (a legitimate C4 self-dependency read as a self-message)
… SEQ103      (blocker: "applies sanctions screening" is not signature-shaped)
… GEN002      (true: the file has no diagram name)
✖ 8 issue(s): 4 blocker, 1 info, 3 minor                              (exit 1)
```

Seven of the eight are false in C4 semantics, four of them at `blocker`,
and the run **exits 1**. Under the default profile the same file produces
4 findings and exits 0. So the profile this project recommends for the
exact workflow the C4 ecosystem is now targeting is the profile that
handles C4 worst — silent where it should speak, and hard-failing with
invented blockers where it should be silent.

This does not change the decision. It changes how the decision should be
described: not "C4 input is uncovered" but **"C4 input is actively
mishandled, and worst under the recommended profile"**.

### 8.3 The externally-authored rule spec is about 40% mechanizable

The [C4 review checklist](https://c4model.com/diagrams/checklist)
re-verified today. Every item the 2026-07-27 note cited is still present.
Reading the whole list rather than the cited subset, the 21 items split:

| Group | Items | Checkable from `.puml` source |
|---|---|---|
| General | 4 | title ✔, legend/key ✔, diagram type ~, scope ~ |
| Elements | 10 | name ✔, abstraction level ✔, purpose/description ✔, technology ✔ — and 6 about acronyms, colours, shapes, icons, border styles and element sizes ✖ |
| Relationships | 7 | label ✔, technology ✔, direction-matches-description ~ — and 4 about acronyms, colours, arrow heads and line styles ✖ |

Roughly **8 clean and 3 partial of 21**. The 10 unreachable items are all
about the rendered picture and its legend, which is not a limitation of
this tool — it is a limitation of any source linter, and it is why
`SHOW_LEGEND()` is worth a rule: a declared legend is the mechanical proxy
for the ten questions a reviewer can then answer.

Sizing consequence, recorded because estimation should survive: the
tier-1 catalog sketched in 2026-07-27 is already approximately *the whole
mechanizable checklist*. Tiers 2 and 3 are this project's own additions
(abstraction mixing, scope rules, codegen lexicons) and carry no external
authorship — the "findings cite a published standard" argument covers
tier 1 only. That is a claim-language correction, not a scope change.

### 8.4 The trigger's instrument needs an exclusion rule

The build trigger is *"material C4 macro usage in a census of a real
corpus, or a concrete user asking"*. The census has run once, on public
wild material, and reported **73 of 159 files calling C4 macros (46%)**.
[The census note](pilot-census-first-contact.md) reads that as: "on public
wild material the dialect signals the demand-gated items wait for are loud
— C4 macros in 46% of files (→ the C4/component parser pack)".

The same note, in its corpus-composition table, records that
`plantuml-stdlib/C4-PlantUML` contributed **71 of the 159 files** — its
`samples/` and `percy/` trees, the C4-PlantUML project's own example and
visual-regression gallery. Recomputed from `sources.json`:

```
plantuml-stdlib/C4-PlantUML      71     ← the notation's own repository
hyperledger/aries-rfcs           39
awslabs/aws-icons-for-plantuml   37
plantuml-stdlib/Azure-PlantUML    8
dcasati/kubernetes-PlantUML       4
```

45% of the corpus is the notation's own sample gallery, and 46% of the
corpus calls C4 macros. The census does not record which files carry the
marker, so the overlap cannot be computed exactly from the artefacts in
this repo; the marker's own example list names at least three files from
other repos, so C4-PlantUML's own examples account for **at most 70 of the
73**, and — since its samples use the macros by construction — plausibly
most of them.

**Nothing here is undisclosed.** The composition table is in the census
note; so is "the corpus skews toward sample galleries", and so is "a
public corpus proves prevalence, not pull". The gap is narrower and it is
in the join: the two numbers appear in different sections, their near
identity is never drawn, and the one sentence that reads a build signal
off the 46% is the sentence where it matters.

The consequence for the roadmap is small and concrete. The trigger's words
"a real corpus" already carry the intent; nothing states the rule that
makes it operational. It should: **before a dialect marker is read as
demand, exclude the notation's own repository and vendor sample
galleries** — the same discipline `sources.json` already applies one level
shallower, where it excluded 32 theme/macro files from that same
repository as "library code by content". The exact overlap is cheaply
settleable by re-running the marker over a re-clone from `sources.json`
(which records repo, path and commit for all 159 files) with the
C4-PlantUML source excluded — a measurement, not a build.

Note what this does **not** say. It does not say C4-PlantUML is rare: 46%
of a corpus deliberately assembled to include a C4 sample gallery tells us
nothing either way about third-party adoption. It says the instrument has
not yet measured that, and the trigger should not be read as though it
had.

## 9. SWOT

Scope: *pumllint's position in the C4 ecosystem*.

**Strengths (internal, favourable)**

- The only graded verdict in the ecosystem — levels, dimensions, gap
  report, ratchet, badge — against three validators that all report flat.
- Outcome evidence nobody else has: the C4 detail-ladder wave measured
  which spec ingredients move generation outcomes.
- A settled, dated, re-measured record: the fit case does not need
  re-deriving, and its behavioural claims were just verified current.
- The recognizer target is closed and regular, and would partly transfer
  to Mermaid C4 (S4).
- Honest silence outside the file surface — the "nothing was checked"
  warning means the tool never implies coverage it lacks.

**Weaknesses (internal, unfavourable)**

- On the one C4 dialect it can see, current output is wrong in both
  directions, and worst under the recommended profile (§8.2).
- Zero coverage of where the ecosystem's centre of gravity sits, by
  construction (`.dsl`, `.c4`, `.mmd` never discovered).
- The tier-1 rules a pack would ship are already implemented, three times
  over, on the modelling side.
- The one demand reading the instrument has produced needs a guard before
  it can be cited (§8.4).

**Opportunities (external, favourable)**

- The ecosystem's AI turn creates a constituency that already believes in
  gating artefacts before agents generate from them — Structurizr is
  teaching it.
- The diagramming half of the ecosystem is validation-free and will stay
  so: neither vendor has an incentive to check a competitor's format.
- Grading is unoccupied and the vendors' architecture points away from it
  (an inspection list has no natural aggregate; a maturity model does).

**Threats (external, unfavourable)**

- **The method recommends away from the served format.** c4model.com
  favours modelling over diagramming; both vendors' AI stories are
  DSL-only. The C4-PlantUML population may be flat or shrinking on the
  axis this project's evidence lives on, and nothing here measures that.
- **Vendor speed.** Structurizr shipped inspections into an MCP server in
  a quarter. A pack built to fill a gap can find the gap filled.
- **Duplicative-by-default perception.** "Structurizr already checks
  descriptions and technology" is true and will be said; the answer is the
  format and the grade, and it has to be said crisply.
- **Trigger-on-noise.** §8.4, generalized: every dialect marker the census
  counts is exposed to the same composition question.

## 10. Decision, corrections, triggers

**Decision: the 2026-07-27 settlement stands unchanged — fit verified,
wait for census pull. Nothing queued. Three claim-language corrections and
one trigger guard are recorded below.**

**Corrections to the record** (claim language only; no measurement is
withdrawn):

- **C1 — "Nothing checks hand-written C4-PlantUML" narrows again.** A
  third-party tool does parse these files: `jqassistant-c4-plugin`, with a
  custom ANTLR grammar over context/container/component diagrams, for
  as-is-vs-to-be architecture conformance. It is not a modelling-quality
  linter, so the *substantive* claim survives in the form **"no tool
  checks C4-PlantUML modelling quality"**. The 2026-07-27 sentence "a
  search surfaced no third-party C4-PlantUML linter (absence of a find,
  not proof of absence)" was correctly hedged and is now superseded by a
  find. Maintenance status unverified.
- **C2 — "The defect list is externally authored" applies to tier 1
  only, and to ~40% of the checklist.** 8 of 21 items are cleanly
  mechanizable from source, 3 partially; the remaining 10 are about the
  rendered picture. Tiers 2 and 3 are this project's own design and carry
  no external authorship. Pitch material must not claim the checklist as
  the warrant for the whole pack.
- **C3 — the market boundary moved on the AI axis.** Structurizr ships an
  MCP server providing DSL validation, parsing and inspection to agents;
  LikeC4 ships agent skills plus an MCP server. Any statement that
  nothing gates C4 before an agent generates from it is false for
  Structurizr DSL as of 2026-08-27. It remains true for C4-PlantUML.

**Trigger guard (the one operational change recorded):**

- **Before a census dialect marker is read as demand, exclude the
  notation's own repository and vendor sample galleries.** The C4 trigger
  keeps its wording; this is how "a real corpus" is to be applied. The
  existing reading (46% C4 macros) must be cited with its composition
  (45% of the corpus is C4-PlantUML's own gallery) or not cited as a
  demand signal at all.

**Recorded, not queued:**

1. **Re-run the census C4 marker with the notation's own source
   excluded** — `sources.json` carries repo, path and commit for all 159
   files, so the exact overlap is recoverable. Cheap, and it converts
   §8.4's bounded statement into a number. Maintainer self-demand, not
   adopter pull.
2. **A second wild sweep weighted toward working project corpora** — the
   census note already names this as "the natural extension if one is
   ever needed"; §8.4 is the concrete reason it would be worth having,
   since sample galleries are exactly what dilutes a demand reading.
3. **The Mermaid-C4 recognizer note (S4)** — read before either the C4
   pack or the Mermaid sibling stack is picked up; the general Mermaid
   cost estimate over-states the C4 case.
4. **The codegen-profile amplification (§8.2)** as the sharpened form of
   the pack's internal motivation, for whenever the trigger fires.

**Re-litigate the settlement on any of:**

- An adopter's own census (not a public one) showing material C4 macro
  usage after the exclusion rule above — the trigger as always intended.
- A concrete user with hand-written C4-PlantUML asking for a gate.
- A vendor shipping quality checking for C4-PlantUML specifically, which
  would close the niche (today both vendors check only their own DSL).
- Evidence that the C4-PlantUML population is materially growing or
  shrinking — the threat in §9 that nothing currently measures, and the
  one input that would change F1's ceiling rather than its trigger.

## Related reading

- [Would a C4-PlantUML rule pack fit?](c4-pack-evaluation.md) — the
  2026-07-27 settlement this note re-examines, corrects in three places
  and leaves standing.
- [C4 detail ladder: which spec ingredients move codegen outcomes](c4-codegen-detail-experiment.md)
  — the evidence extension, and the asset §7/F6 is about.
- [First contact: the pilot census on a public wild corpus](pilot-census-first-contact.md)
  — the instrument §8.4 audits, and the source of every corpus number here.
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) —
  yesterday's evaluation; its SHACL-conformance-is-binary finding is the
  third leg of §3's "nobody grades".
- [ROADMAP.md](../ROADMAP.md) — the C4 settled question, the adjacent-verifier
  record F4 corroborates, and the Mermaid sibling-stack record S4 qualifies.
- [Using pumllint from a coding agent](agents.md) — the profile §8.2
  measures, and the loop Structurizr's MCP server independently arrived at.
