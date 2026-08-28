# The Zachman ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `51c9eea` (v0.29.0). The
question as posed: investigate the Zachman ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Seventeenth in a series, and
the oldest subject in it: Zachman's framework dates from 1987 and is the
ancestor the previous four notes' subjects all descend from or cite.*

**Verdict up front: no, and this is the purest "nothing to lint" case of
the seventeen — but the note is not about the refusal. Zachman supplies a
vocabulary that describes pumllint's unit of analysis more precisely than
this project has managed on its own, and one measurement falls out of it
that is worth keeping.**

**Zachman is an ontology, not a methodology, and it draws the distinction
in exactly the terms that matter here: it *"classifies the total set of
present 'primitive' (elemental) components"*, as against a methodology,
*"which produces 'composite' (compound) implementations of the
primitives"* — and *"primitives are timeless, whereas composites are
temporal"*. A PlantUML sequence diagram is a **composite** in that exact
sense: it mixes **Who** (participants), **When** (ordering and
activation) and **What** (message payloads) in one artefact. Zachman's
36 cells hold primitives. **pumllint lints composites and has no concept
of a primitive.** §5.1.**

**The measurement, and it is the contribution. Classifying all 51 rules
in `pumllint/rules/catalog.toml` by which of Zachman's six interrogatives
they examine:**

| Zachman interrogative | pumllint rules |
|---|---|
| **What** — data, inventory | 5 |
| **How** — function, process | 8 |
| **Where** — network, distribution | **0** |
| **Who** — people, responsibility | 13 |
| **When** — time, sequence, state | 15 |
| **Why** — motivation, rationale | **1** (GEN007, dormant until configured) |
| *artefact-level* (about the diagram, not the enterprise) | 9 |

**Who + When account for 28 of the 42 enterprise-facing rules — 67%** —
and Who + When is precisely the composite a sequence diagram is.
**Where has no rules at all**, and **Why has one, dormant by default**.
The classification is mine and reproducible from the catalogue; §8.2
gives the method. This is the first time the series has produced a
quantitative statement of *what pumllint's rules are about*, and Zachman
is what made it expressible.

*Bounds. **zachman.com returned 503 and was not read**, so every quotation
here is from secondary sources — encyclopaedic and vendor summaries — not
from Zachman International. Row names vary between framework versions and
between sources; the classic Planner/Owner/Designer/Builder/Sub-contractor
/User naming is used below and the 3.0 relabelling is noted rather than
asserted. **The Zachman Framework for Enterprise Architecture™ is a
trademark of John A. Zachman**; the framework graphic's reproduction terms
could not be established, so none is reproduced. The §-heading
interrogative classification is a judgement about each rule's subject and
another reader could move a handful of borderline cases (SEQ103, SEQ107
and SEQ109 are the ones most open to argument); the headline shape — Where
zero, Why one, Who+When dominant — does not depend on them. Every pumllint
claim was executed at `51c9eea` with default config from a neutral working
directory. Per session scope no GitHub repository was read.*

## 0. Why this ran, and the loop it closes

Two prior mentions, both in passing. The **Linked.Archi** note recorded
Zachman among its subject's "framework integrations" (beside TOGAF,
DoDAF, UAF, TIME, ATAM). The **ISO 42010** note listed it among the
viewpoint catalogues that predate and implement the standard.

A third reference is worth stating carefully, because it is *not* in the
record. **ISO/IEC/IEEE 42010:2022 itself cites Zachman** — its definition
of *stakeholder perspective* (3.18) gives as its example that *"the labels
given to the middle three rows (i.e. owner, designer and builder) of the
Zachman framework correspond to stakeholder perspectives"*. That is quoted
here from the standard's published preview, read during the 42010
evaluation; **the 42010 note does not contain it**, so this is an addition
to the record rather than a citation of it.

That reference is the loop this note closes. Four of the last five
evaluations — 42010, TOGAF, DoDAF/UAF, NAF/MODAF — examined frameworks
that descend from or cite Zachman's 1987 paper, and NAF's grid is
described in the note before this one as "Zachman-like". **This is the
ancestor**, and it is the only one of the five that is neither a method
nor a standard with conformance clauses, but a classification schema.

## 1. The framework

### 1.1 An ontology, emphatically not a methodology

The distinction is Zachman's own and is load-bearing:

> The Zachman framework is an **ontology**, which classifies the total set
> of present **"primitive" (elemental) components** that are important to
> the existence of an object, differentiating it from a **methodology**,
> which produces **"composite" (compound) implementations** of the
> primitives.

and:

> As a metamodel, the Zachman Framework does not imply anything about
> whether you build Primitive Models (the ontological, single-variable
> intersections between the Interrogatives and the Transformations) or
> whether you simply build ad hoc, multi-variable, **composite models**
> made up of components of several Primitive Models.

with the consequence stated as: **"Primitives are timeless, whereas
composites are temporal."**

§5.1 is about what that means for a `.puml` file.

### 1.2 The 6×6

Six **columns**, the interrogatives, each modelling one thing:

| Column | Interrogative | Models |
|---|---|---|
| 1 | **What** | data, things, inventory |
| 2 | **How** | function, process |
| 3 | **Where** | network, location, distribution |
| 4 | **Who** | people, roles, responsibility |
| 5 | **When** | time, events, schedules |
| 6 | **Why** | motivation, goals, rationale |

Six **rows**, the perspectives — classically Planner (scope contexts),
Owner (business concepts), Designer (system logic), Builder/Implementer
(technology physics), Sub-contractor (component assemblies) and User
(operations). Version 3.0 relabels these (Executive, Business Management,
Architect, Engineer, Technician, Enterprise); sources disagree on which
labels to present, so both are noted and neither is asserted as canonical.

**36 cells**, each a primitive model. Completeness, in Zachman's terms, is
having all 36.

### 1.3 Notation: none, and by design

The framework mandates no modelling language. Vendor guidance shows it
applied alongside "UML, BPMN, ERD and other diagrams" — the ontology
classifies what a model is *about*, and is silent on how it is drawn.

This is the third framework in a row to prescribe no notation, and the
most thoroughly so: TOGAF names 32 diagram artifacts, DoDAF names 52
models and explicitly permits any notation, NAF constrains the metamodel.
**Zachman names cells and stops.**

## 2. The seam — there is none, and that is the cleanest result available

pumllint reads a PlantUML file. Zachman classifies the *content* of models
by subject and perspective. There is no file, no syntax, no conformance
clause and no deliverable list to check against.

Every previous note in the series could at least locate a seam — narrow
(Capella), blocked (SysML), permissive (DoDAF), metamodel-shaped (NAF).
**Here there is nothing to locate**, and the note's value lies entirely in
what Zachman's vocabulary reveals when pointed at pumllint rather than the
other way round.

## 3. Overlap

| Concern | pumllint | Zachman | Reading |
|---|---|---|---|
| Unit of analysis | one diagram; a model set | a **primitive** model in one cell | **Disjoint — §5.1** |
| What / How / Who / When | 41 rules between them | four of six columns | **Measured — §8.2** |
| **Where** | **nothing** | column 3 | **Zero coverage, and it is a scope decision already settled** |
| **Why** | GEN007, dormant | column 6 | One rule, off by default |
| Completeness | rule-level, within a diagram | **all 36 cells** | Different objects, same word |
| Notation | PlantUML | none prescribed | No contact |
| Aggregate verdict | the scoring model | none | Seventeenth, no grader |

## 4. Boundaries

1. **Primitive vs. composite** (§5.1) — the boundary Zachman itself draws,
   and the one that places pumllint precisely.
2. **No notation, no artefact, no conformance** — nothing to parse and
   nothing to conform to.
3. **Trademark**, not a licence or a paywall: a fifth access category
   after paid (42010), gated (TOGAF), open (DoDAF) and free-but-unread
   (NAF). §5.4.

## 5. Sense — four true things

### 5.1 Zachman names what pumllint lints, and the name is "composite"

A PlantUML sequence diagram declares participants (**Who**), orders
messages over time with activations (**When**), and carries payloads and
return values (**What**). Three interrogatives in one artefact. In
Zachman's terms that is a **composite** — an "ad hoc, multi-variable"
model assembled from components of several primitives — and the ontology's
cells hold primitives.

Measured, the tool has no notion of the distinction:

| Sample | shape | type | level | score |
|---|---|---|---|---|
| logical data model (pure **What**) | primitive-like | `class` | **4 (Precise)** | 97.92 |
| order/payment interaction (**Who+When+What**) | composite | `sequence` | **4 (Precise)** | 99.11 |

Both are "Precise" on the same scale, and nothing in the parsed model, the
JSON report or the schema records how many interrogatives a diagram mixes
(§8.3). **That is not a defect** — pumllint is a PlantUML linter and
PlantUML diagram types *are* composites by construction. It is a precise
statement of the altitude the tool works at, and Zachman is the only
subject in seventeen evaluations that supplied the words for it.

### 5.2 The interrogative profile is the first quantitative account of what the rules are about

§8.2 and the table up top. **Who + When carry 67% of the enterprise-facing
rules**, which is the same as saying the catalogue is overwhelmingly about
interactions between actors over time — the sequence diagram's subject
matter, which the DoDAF and TOGAF notes reached from the opposite
direction by counting framework artifacts.

Two numbers are worth stating plainly rather than defending:

- **Where: 0 rules.** pumllint parses five diagram types and deployment is
  not among them; location and distribution are simply outside the tool.
  Consistent with the UML note's record that five of UML's fourteen types
  are parsed, and not a gap this note proposes closing (N4).
- **Why: 1 rule**, GEN007, dormant until a pattern is configured. The
  motivation column is the one Zachman practitioners most often say is
  neglected in practice, and pumllint neglects it too.

### 5.3 Seventeenth ecosystem, no grader — with the usual qualification

In the TOGAF-corrected form: nothing grades a description artefact.
Zachman defines completeness as having all 36 cells, which is a
*checklist*, not a score — no rating, no aggregate, no level. Third-party
Zachman-based maturity assessments exist; the framework itself defines
none, and none was examined.

### 5.4 Access, fifth category: trademarked

**The Zachman Framework for Enterprise Architecture™ is a trademark of
John A. Zachman**, and the framework graphic is distributed under terms
this note could not establish (zachman.com returned 503). So the running
access tally is: **paid** and partly read (42010), **registration-gated**
and unread (TOGAF), **openly published** and read (DoDAF), **free and
still unread** (NAF), **trademarked** with terms unverified (Zachman).

The practical consequence is small and worth recording anyway: **no
Zachman graphic is reproduced here**, and the structure is described in
prose instead.

## 6. Nonsense — five moves to refuse

**N1. A Zachman cell recognizer, "36-cell mode", or coverage report.
Refused on the artefact.** There is nothing to recognize: the framework
prescribes no notation, so a cell classification would be pumllint
guessing which interrogatives a diagram serves — from the diagram type it
already knows, which adds a label and no information.

**N2. Adding a primitive/composite distinction to the model. Refused,
and it is the tempting one after §5.1.** It would be a metamodel concept
of exactly the kind the knowledge-graph and OWL/SHACL settlements refuse,
and it has the no-oracle shape: nothing in a repository says which
interrogatives a given diagram *ought* to mix, and "this diagram is a
composite" is true of every PlantUML diagram type by construction, so the
finding would fire everywhere and mean nothing.

**N3. Any Zachman coverage, alignment or completeness claim. Refused.**
Zachman completeness is 36 primitive models across an enterprise.
pumllint sees files. A "Zachman coverage" report would be measuring
diagram types and calling them cells.

**N4. Reading `Where: 0` as a gap to close. Refused.** Deployment and
location diagrams are outside the parsed set by a scope decision made
long before this note, recorded in the UML evaluation. Zachman gives that
absence a name; it does not give it a reason to change.

**N5. Reading `Why: 1` as a gap to close. Refused, more carefully.**
The motivation column is genuinely thin — one dormant rule. But
motivation lives in prose, ADRs and requirement systems, and the
repository's answer to it is `trace` plus GEN007's configurable pattern,
which is the deliberate design the SysML note measured the cost of. Adding
rules that judge *rationale* would be the well-formedness-as-a-type
anti-goal in a new suit.

## 7. Fit — graded

### F1 — a Zachman cell recognizer or coverage mode. **No.** N1, N3.

### F2 — the interrogative profile as a positioning artefact. **A measurement worth keeping; nothing to build.** §5.2, §8.2.

The strongest thing this evaluation produces. It states, from the
catalogue rather than from intuition, that pumllint's rule mass sits in
Who and When, with What and How supporting, Where empty and Why nearly so.
That is useful for positioning and for deciding what a future pack should
*not* be, and it required no code.

### F3 — a primitive/composite concept in the model. **No.** N2.

### F4 — filling Where or Why. **No, for different reasons.** N4, N5.

### Fit against declared constraints

| Declared constraint | Where the Zachman fits land |
|---|---|
| **No metamodel layer** | **Decides N2** — primitive/composite is a metamodel concept. |
| **Claim language** | Decides N3 — "Zachman coverage" would rename diagram types as cells. |
| **Well-formedness-as-a-type anti-goal** | Decides N5. |
| **Demand bar** | Not reached; nothing here is a candidate. |
| **Zero deps / licence** | Not reached — though see §5.4 on the trademark. |

## 8. Gap — measured

### 8.1 No discovery probe, for the fourth time and most completely

Zachman defines no file format, no notation and no artefact list. Nothing
to place beside `.puml`. Fifth note in the series with no §8.1 boundary
measurement, and the only one where the subject has *nothing* a linter
could ever attach to.

### 8.2 The interrogative classification — method and result

Every rule in `pumllint/rules/catalog.toml` was assigned the interrogative
whose subject matter it examines, or `artefact` where the rule is about
the diagram as a document rather than about the enterprise it describes
(titles, names, skinparams, note density, size caps, elision markers,
cross-type identity):

| Interrogative | Count | Representative rules |
|---|---|---|
| **What** | 5 | CLS001–005 — classes, members, multiplicities, associations |
| **How** | 8 | ACT001–006, SEQ103 (operation signatures), SEQ107 (failure paths) |
| **Where** | **0** | — |
| **Who** | 13 | SEQ001/002/010/101/102, GEN004/005, XD001–003, UC001–003 |
| **When** | 15 | SEQ003–009, SEQ011, SEQ104/105/108/109, STA001–003 |
| **Why** | **1** | GEN007 (requirement/ADR link), dormant until configured |
| *artefact* | 9 | GEN001/002/003/006/008/009, SEQ106, XD004/005 |

**42 enterprise-facing rules; Who + When = 28 of them (67%).**

The assignment is a judgement, and the borderline cases are named in the
bounds. The shape is robust to them: moving all three contested rules
would not put a rule in **Where**, would not add one to **Why**, and would
not drop Who+When below 60%.

### 8.3 Primitive and composite are indistinguishable to the tool

```
primitive_what.puml   type=class     Level 4 (Precise)  97.92   elements=3
composite.puml        type=sequence  Level 4 (Precise)  99.11   elements=7
```

The JSON report exposes `diagramType`, `level`, `levelName`, `score`,
`elementCount`, `suppressedCount`, `dimensions`, `gapReport`, `syntaxOk`
and `baseline`. **Nothing records how many interrogatives a diagram
mixes**, and nothing could without the metamodel N2 refuses.

Cap C6 illustrates the point compactly: it counts *elements*, and an
element is an element whether it is a class (one interrogative) or a
message between two participants (three). The scoring model is
interrogative-blind by construction.

### 8.4 What was not measured

**Zachman's own material** — zachman.com returned 503, so nothing here is
quoted from Zachman International and the framework graphic's terms are
unknown. No Zachman-based maturity assessment was examined, so §5.3's
streak entry rests on the framework defining no score rather than on a
survey of what practitioners built around it. The row-perspective naming
was not resolved across versions. No tool claiming Zachman support was
run.

## 9. SWOT

**Strengths (pumllint, internal)**

- §8.2 is a defensible, reproducible account of what the rule catalogue is
  about — obtainable at any time from the catalogue, and now recorded.
- The concentration in Who+When is coherent rather than accidental: it
  matches the artefact the tool parses most deeply.

**Weaknesses (pumllint, internal)**

- **Where: 0** and **Why: 1** are real coverage facts, even though both
  absences are settled decisions rather than oversights. Anyone
  positioning pumllint as broad enterprise-diagram hygiene should read
  §8.2 first.
- The tool cannot say what its own diagrams are *about* beyond a type
  name, which is the §8.3 result stated positively.

**Opportunities (external)**

- None. F2 is a measurement, not a market.

**Threats (external)**

- None. Zachman is 39 years old, prescribes nothing, and competes with
  nothing.

## 10. Decision, recorded candidates, triggers

**Decision: no Zachman support of any kind — no cell recognizer, no
coverage report, no primitive/composite concept, no claim. Nothing
queued. Two observations recorded, both about pumllint rather than about
Zachman.**

**Never build:**

- A Zachman cell recognizer, 36-cell mode or coverage report (N1, N3) —
  the framework prescribes no notation, so cell assignment would restate
  the diagram type under another name.
- **A primitive/composite distinction in the model** (N2) — a metamodel
  concept the standing settlements refuse, with the no-oracle shape:
  every PlantUML diagram type is a composite by construction, so the
  finding would fire everywhere and mean nothing.
- Rules to fill **Where** (N4) — outside the parsed set by a scope
  decision recorded in the UML note; Zachman names the absence without
  giving a reason to change it.
- Rules to fill **Why** (N5) — motivation lives in prose and requirement
  systems, where `trace` and GEN007 already meet it; judging rationale
  would be the well-formedness-as-a-type anti-goal in a new suit.

**Recorded, not queued:**

1. **The interrogative profile** (§8.2) — What 5, How 8, **Where 0**,
   Who 13, When 15, **Why 1**, artefact-level 9; **Who+When = 67% of the
   42 enterprise-facing rules**. The first quantitative statement in the
   series of what pumllint's rules are *about*, reproducible from
   `catalog.toml`, and the thing to consult before describing the tool as
   broad diagram hygiene.
2. **"Composite" as the right word for pumllint's unit** (§5.1). A
   PlantUML sequence diagram mixes Who, When and What; Zachman's cells
   hold primitives; the tool lints composites and scores a primitive-like
   class diagram and a three-interrogative sequence diagram on the same
   "Precise" scale with nothing distinguishing them. Not a defect — a
   precise account of the altitude, in vocabulary this project did not
   have before.

**Re-litigate on:**

- **Nothing an adopter can bring.** Zachman prescribes no artefact, so no
  user can arrive with a Zachman file, a Zachman export or a Zachman
  conformance requirement that touches a PlantUML linter.
- A rule pack proposal that would change §8.2's shape — in which case the
  profile is the thing to update and check, not to re-derive.
- **Not** on Zachman adoption, in either direction: the framework has been
  cited for thirty-nine years without producing an artefact a linter could
  read.

## Related reading

- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — quotes Zachman from the standard itself, and shares the
  altitude-boundary shape §5.1 sharpens.
- [The TOGAF / ADM ecosystem, evaluated](togaf-adm-ecosystem-evaluation.md)
  — the corrected no-grader criterion §5.3 uses, and the first framework
  in the run that prescribes artifacts without notation.
- [The DoDAF / UAF ecosystem, evaluated](dodaf-uaf-ecosystem-evaluation.md)
  and [NAF / MODAF](naf-modaf-ecosystem-evaluation.md) — the two
  descendants whose artifact counts §5.2 reaches from the opposite
  direction.
- [The UML ecosystem, evaluated](uml-ecosystem-evaluation.md) — the
  five-of-fourteen parsed-type record that makes `Where: 0` a settled
  decision rather than a finding.
- [ROADMAP.md](../ROADMAP.md) — the metamodel never-build behind N2 and
  the well-formedness-as-a-type anti-goal behind N5.
