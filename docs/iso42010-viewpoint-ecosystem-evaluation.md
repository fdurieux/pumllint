# The ISO 42010 / viewpoint ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `40c132c` (v0.29.0). The
question as posed: investigate the ISO 42010 / viewpoint ecosystem, then
assess the boundaries, overlap, fit, gap, sense and nonsense of the
different fits against pumllint's roadmap and ecosystem. Thirteenth in a
series (Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, Structurizr
DSL, Ilograph, Graphviz/DOT, SysML, Capella/Arcadia, this) — and the
first whose subject is **not a notation, not a tool, and not a product**,
but a standard about what an architecture description must be.*

**Verdict up front: no — and the reasons are unlike the twelve before it,
because 42010 is the one ecosystem in the series that is *about the same
question pumllint is about*. It is a standard for architecture
descriptions: what they contain, how their views relate, and what it
means for one to conform. Three findings, and the third is the one worth
keeping.**

**(1) pumllint's unit of analysis is precisely the one thing 42010 does
not define conformance for.** Clause 4 names five situations in which
conformance may be claimed — for an architecture description, an
architecture description framework, an architecture description language,
an architecture viewpoint, and a model kind. A `.puml` file is none of
these. In 42010's vocabulary it is at best a **view component** (3.19),
*"separable portion of one or more architecture views… governed by the
applicable model kind or legend"*. **pumllint can neither conform to
42010 nor fail to** — the standard has no requirements at its altitude,
which settles every "42010-conformant" claim before it is made.

**(2) The correspondence result, measured.** 42010's central structural
idea is that views *correspond*. pumllint has five cross-diagram rules
(XD001–005, all DIM-CON) that check whether a shared entity is used
consistently — an implementation of what 42010 calls **correspondence
rules**, arrived at independently. It has **no concept of the
correspondence requirement itself**:

| Two views… | pumllint |
|---|---|
| sharing an entity, with a **conflicting** kind | **XD001 ×2, major, exit 1** |
| sharing **nothing at all** | **✔ No issues found — Model set: Level 4 (Precise), 100/100** |

**Two entirely disjoint diagrams are a "Precise" architecture description
at 100 out of 100.** That is half of 42010's correspondence concept — the
cheap half — and the missing half is *already on the never-build list* as
**missing-edge inference**, refused for want of an oracle. The gap is
real, an international standard supplies the vocabulary for naming it,
and the reason it was refused still holds. §8.4.

**(3) The streak, reframed — and this is the finding that outlives the
note. Thirteen ecosystems, no grader.** The twelve before this were
*tools* that happened not to aggregate. This one is different:
**ISO/IEC/IEEE 42030, the standard in this family whose entire subject is
architecture evaluation, defines a process and a framework and
deliberately declines to define a scoring scheme, a rating scale, a
maturity level or an aggregate verdict** — it "does not prescribe how to
aggregate results into an overall verdict". That is not a market gap. It
is the standards body that owns the question, having considered it. So
the twelve prior results admit a second reading, and this note does not
resolve which is right: either pumllint has built something the field
overlooked, or it does something the field examined and chose not to
standardize. §5.5.

*Bounds, and one of them is the subject. **ISO/IEC/IEEE 42010:2022 is
paywalled and I did not read it.** What is quoted here comes from the
publisher's own **15-page preview** — front matter, the full table of
contents, part of Clause 3 (terms and definitions), **Clause 4
(Conformance) in full**, and the opening of Clause 5. **Clauses 6, 7 and
8 — which contain every actual requirement — were not read**, so this
note can state what conformance is claimed *for* and not what it
*requires*. 42030 is characterized entirely from secondary sources
(arc42's standards summary and abstracts); its text was not seen. Every
pumllint claim was executed at `40c132c` with default config from a
neutral working directory. Per session scope no GitHub repository was
read. The sample architecture descriptions are mine.*

## 0. Why this ran, and the prior record

One prior mention exists. The Linked.Archi evaluation recorded that its
subject ships *"framework-agnostic viewpoints aligned to ISO/IEC/IEEE
42010"* and claims *"standards alignments (42010, 42020, 12207, …)"*.
That note took the alignment at face value as a description of
Linked.Archi and did not examine 42010 itself. This does.

The ecosystem, taken as asked, is the standard plus the viewpoint
catalogues that predate and implement it: **Kruchten's 4+1** (1995 —
logical, process, physical, development, plus scenarios), **Rozanski &
Woods** (2005, viewpoints *and* perspectives), **RM-ODP**, **SEI Views
and Beyond**, **Zachman**, **TOGAF**, **IAF**, **E2AF** and **TRAK**,
which publishes a conformance statement against 42010.

## 1. The standard

### 1.1 Lineage and status

**IEEE 1471:2000** → **ISO/IEC 42010:2007** → **ISO/IEC/IEEE 42010:2011**
→ **ISO/IEC/IEEE 42010:2022**, second edition, published November 2022,
around 63 pages plus annexes. The 2022 revision's stated objectives
included specification of architecture frameworks and ADLs, architecture
decision capture, and **correspondences for model and view consistency**.

Two siblings matter: **ISO/IEC/IEEE 42020** (architecture processes —
governance, management, conceptualization, evaluation, elaboration,
enablement) and **ISO/IEC/IEEE 42030:2019** (architecture *evaluation*
framework). §5.5 is about 42030.

### 1.2 The vocabulary, verbatim

From the preview's Clause 3:

> **3.3 architecture description, AD** — *work product used to express an
> architecture*
>
> **3.4 architecture description element, AD element** — *identified or
> named part of an architecture description*
>
> **3.6 architecture description language, ADL** — *means of expression,
> with syntax and semantics, consisting of a set of representations,
> conventions, and associated rules intended to be used to describe an
> architecture.* EXAMPLE: AADL, ArchiMate, UML, SysML, UAF Profile.
>
> **3.7 architecture view** — *information part comprising portion of an
> architecture description*
>
> **3.8 architecture viewpoint** — *set of conventions for the creation,
> interpretation and use of an architecture view to frame one or more
> concerns*
>
> **3.15 model kind** — *category of model distinguished by its key
> characteristics and modelling conventions*
>
> **3.19 view component** — *separable portion of one or more
> architecture views that is governed by the applicable model kind or
> legend*

Note what the ADL example list contains: AADL, ArchiMate, UML, SysML,
UAF — five languages with semantics, four of which have their own note in
this series. **PlantUML is not among them, and is not one.** It is a
rendering notation; the repository has said so about itself for its whole
life, and 42010's definition independently agrees.

### 1.3 Conformance, verbatim

> **4 Conformance**
>
> The requirements in this document are contained in Clauses 6, 7 and 8.
> There are five situations in which claims of conformance with the
> provisions of this document can be made.
>
> 1) When conformance is claimed for an **architecture description**, the
>    claim shall demonstrate that the specification of the architecture
>    description meets the requirements listed in **Clause 6**.
> 2) …for an **architecture description framework** … **7.1**.
> 3) …for an **architecture description language** … **7.2**.
> 4) …for an **architecture viewpoint** …
> 5) …for a **model kind** …

Five targets. **A view component is not one of them**, and a `.puml` file
is a view component. §4.1 works out what follows.

## 2. The seam — and where it actually is

pumllint reads one PlantUML file and scores it; with a directory it also
emits a **model-set verdict** (§8.2). 42010 governs a *work product* —
the AD — assembled from views, governed by viewpoints, framing the
concerns of identified stakeholders, related by correspondences.

The seam is real but narrow, and it sits one layer below where 42010
starts: a `.puml` file is a **view component**, and pumllint checks
whether that component is internally coherent. Everything 42010 requires
is about the assembly.

## 3. Overlap

| Concern | pumllint | ISO 42010 | Reading |
|---|---|---|---|
| Unit of analysis | one diagram; a model set | AD, ADF, ADL, viewpoint, model kind | **Disjoint — §4.1** |
| Consistency between views | **XD001–005**, DIM-CON | **correspondence rules** | **Genuine, independently arrived at — §8.4** |
| Requirement that views relate | **none** | correspondences are central | **The measured gap — §8.4** |
| Stakeholders and concerns | GEN006 ownership tag; GEN007 requirement link | first-class AD elements | Gestured at, in prose carriers |
| Traceability | `trace`: requirement↔diagram matrix | correspondences; 42020 processes | Adjacent, different objects |
| Modelling conventions | the rule catalogue and profiles | **model kind** (3.15) | **The one reachable conformance target — F3** |
| Rationale / decisions | none | architecture decisions, 2022 revision | 42010-side |
| Aggregate quality verdict | the scoring model | **42030 declines to define one** | **§5.5** |

## 4. Boundaries

### 4.1 The altitude boundary, which decides most of this note

42010's five conformance targets are *specifications*: of a description,
a framework, a language, a viewpoint, a model kind. pumllint examines an
*instance* — one view component — against conventions it supplies itself.

The consequence is clean and worth stating in both directions: **pumllint
cannot claim 42010 conformance, and cannot be accused of violating it.**
No requirement in the standard applies to the object it inspects. Any
sentence of the form "pumllint helps you conform to 42010" would be
asserting a relationship the standard does not define.

### 4.2 The paywall, which is a new kind of boundary

Twelve predecessors had readable normative text: OMG specifications are
free downloads, ArchiMate's is free behind registration, D2's and
Mermaid's grammars are their source. **42010 is the first ecosystem in
the series whose normative content I could not read.** Only a 15-page
preview is published; the requirement clauses are not in it.

This is not merely an inconvenience to this note. It is an argument
against ever making a conformance claim: **users could not check it
either.** A badge asserting conformance to a document most readers cannot
open is a claim that cannot be audited by the people it is aimed at,
which is the opposite of what the claim-language discipline in this
repository exists to protect.

### 4.3 Not a notation

There is nothing to parse. 42010 defines no syntax; it is a conceptual
standard. The type-fallback probe that structured eleven previous notes
has no subject here, and its absence is the point rather than an omission.

## 5. Sense — five true things

**S1. The correspondence convergence is real, and it is the third of its
kind.** XD001–005 check that one entity keeps one identity across a
diagram set. 42010 calls that a correspondence rule and made
correspondences a headline of its 2022 revision. After bpmnlint's rule
overlap and Capella's category names, this is a third independent
arrival at the same idea — and the most abstract, since it comes from a
standard rather than a tool.

**S2. And the convergence is partial in a way that is measurable, not
rhetorical.** §8.4 shows exactly which half exists.

**S3. The altitude boundary settles a claim that would otherwise have
been tempting.** "42010-aligned" is the sort of phrase that attaches
itself to architecture tooling cheaply — Linked.Archi's own materials use
it. §4.1 makes it precisely inapplicable here, from the standard's own
conformance clause.

**S4. 42010's ADL definition lands beside the repository's own
self-description.** An ADL is *"a means of expression, with **syntax and
semantics**"*, and the standard's examples are AADL, ArchiMate, UML,
SysML and UAF. PlantUML has syntax and no semantics, so it is not an ADL
by that definition. README.md:6-8 makes a neighbouring claim in different
words — PlantUML is *"by its own admission, a drawing tool rather than a
modeling tool"*. The two are not the same statement, and they agree:
whatever a `.puml` file is, the standard does not treat it as a language
for describing architectures.

**S5. Thirteen ecosystems, no grader — and 42030 changes what that
means.** Every previous entry was a tool that reported violations without
aggregating. **ISO/IEC/IEEE 42030:2019 is the standard for architecture
evaluation**, and it defines evaluation objectives, methods, quality
models, criteria and stakeholder involvement — and, per its summary,
"only a process and framework… not a scoring scheme, rating scale,
maturity level, or aggregate verdict", declining to "prescribe how to
aggregate results into an overall verdict".

That reframes the streak. Twelve tools not aggregating is a market
observation. A standards body writing the evaluation standard and
stopping short of the aggregate is a *considered position*. Two readings
follow and this note picks neither: pumllint may have built something the
field overlooked, or it may do something the field examined and declined
to standardize. What the record should carry is that **the streak is no
longer evidence of an empty niche on its own** — the strongest entry in
it is a deliberate abstention.

## 6. Nonsense — five moves to refuse

**N1. Claiming 42010 conformance, alignment, or a badge. Refused on the
conformance clause.** §4.1: no target, no claim. §4.2: and no auditor.

**N2. Adding viewpoints, views, stakeholders or concerns to pumllint's
model. Refused on scope.** Those are AD-assembly concepts. Modelling them
would make pumllint an architecture-description tool with a linter
attached — a different product, and one whose competitors (§1.1's
catalogues, and every framework tool in the previous twelve notes) all
start from the model rather than the file.

**N3. A "views must correspond" rule. Refused — it is missing-edge
inference.** §8.4 measures the gap; the never-build already refuses the
fix, *"missing-edge inference (the participant-pair sweep's no-oracle
shape…)"*, and the reason transfers exactly. There is no oracle for which
views ought to relate. A rule firing on any diagram that shares no
entity with its neighbours would fire on every legitimately independent
diagram in a repository.

**N4. Renaming the dimensions or levels into 42010 vocabulary. Refused.**
Calling DIM-CON "correspondence" or a model set an "architecture
description" would import a standard's meanings onto objects that do not
satisfy them, which is N1 by vocabulary rather than by badge.

**N5. Reading 42030's abstention as permission. Refused, and this is the
subtle one.** That the evaluation standard declines to define an
aggregate is not endorsement of this project's aggregate, and not proof
the field was wrong. It is a fact that makes the scoring model *more*
exposed, not less: the one body that studied the question in public did
not do what this tool does. §5.5's two readings both stay open.

## 7. Fit — graded

### F1 — a 42010 conformance mode or claim. **No.** N1, §4.1, §4.2.

### F2 — viewpoint/view/stakeholder modelling. **No.** N2.

### F3 — publishing a pumllint profile as a **model kind** specification. **The one reachable target. Parked, not refused.**

This is the single fit in the note that 42010's own conformance clause
permits. A **model kind** is *"a category of model distinguished by its
key characteristics and modelling conventions"*, and conformance may be
claimed for one. A pumllint profile — the codegen profile plus the rules
applying to a diagram type — *is* a statement of modelling conventions
for a category of model.

It is parked on two independent grounds, either sufficient. **The
requirements are behind the paywall**: Clause 8's model-kind
requirements were not read, so nobody here can say what conformance would
take, let alone meet it (§4.2). And **there is no demand**: no adopter
has asked for a model-kind specification, and the artefact would be a
document, not a capability. Recorded because it is the honest answer to
"is there *any* fit", and because a future reader should not have to
re-derive that the answer is "one, and it is a paperwork exercise".

### F4 — correspondence completeness. **No.** N3.

### Fit against declared constraints

| Declared constraint | Where the 42010 fits land |
|---|---|
| **Claim language** ("PlantUML", never "UML") | **The operative constraint.** §4.1 and §4.2 make "42010-conformant" both inapplicable and unauditable. |
| **Demand bar** | Decides F3 jointly with the paywall. |
| **Never-build: missing-edge inference** | **Decides F4 directly** — §8.4's gap is that never-build seen from a standard's vocabulary. |
| **Zero runtime dependencies** | Not reached; nothing proposed. |
| **Licence posture** | **Not the issue here** — the constraint is *access*, not compatibility, which breaks a three-evaluation EPL run. |

## 8. Gap — measured

### 8.1 There is no boundary probe, and that is the finding

42010 has no file format and no syntax. There is nothing to place beside
`.puml`, nothing to wrap in `@startuml`, and no type-fallback question.
Every previous note's §8.1 measured a discovery boundary; here the
boundary is conceptual and §4.1 is where it lives.

### 8.2 An architecture description, scored

Three views — context (sequence), information (class), behaviour
(activity) — each carrying a title naming a stakeholder and a concern, an
ownership header and a requirement reference:

```
01-context.puml     [context-view]:     Level 4 (Precise) — 100/100
02-information.puml [information-view]: Level 4 (Precise) — 100/100
03-behaviour.puml   [behaviour-view]:   Level 4 (Precise) — 100/100

Model set: Level 4 (Precise) — 100/100 weighted across 3 diagram(s)
```

```json
{"level": 4, "levelName": "Precise", "score": 100.0,
 "diagramCount": 3, "elementCount": 17, "suppressedCount": 0}
```

**pumllint does have a set-level verdict**, which is worth stating plainly
because the altitude argument in §4.1 could be misread as saying it only
sees one file. It sees the set. What it does not see is what makes a set
an architecture description.

### 8.3 What the model set does not contain

Measured against 42010's vocabulary, the §8.2 set has: no stakeholders as
AD elements (they are substrings of title text), no viewpoints governing
the views, no model kinds, no architecture rationale, and — §8.4 — no
correspondences. It scores **100/100**.

The scoring model is not wrong to do so; it measures what it says it
measures. The observation is about the distance between "Precise" as this
tool means it and "architecture description" as the standard means it,
and the distance is the whole of Clauses 6 to 8.

### 8.4 Correspondences — half implemented, and the measurement

Two diagrams sharing an entity used inconsistently:

```
a.puml:3: [XD001/major] Participant 'Gateway' is declared 'participant' here and the
          set disagrees ('database' ×1, 'participant' ×1) — one entity, one kind
b.puml:3: [XD001/major] Participant 'Gateway' is declared 'database' here and the
          set disagrees ('database' ×1, 'participant' ×1) — one entity, one kind
✖ 2 issue(s): 2 major                                                    (exit 1)
```

Two diagrams sharing nothing whatsoever:

```
✔ No issues found.
Model set: Level 4 (Precise) — 100/100 weighted across 2 diagram(s)
```

XD001–005 are all DIM-CON and all about **identity**: conflicting kind,
conflicting stereotype, case collisions within a type and across types.
In 42010's terms they are **correspondence rules** — checks on relations
between AD elements — and they are good ones.

What has no counterpart is the **correspondence requirement**. 42010
treats correspondences as the mechanism by which an AD is one description
rather than a pile of pictures. pumllint has no way to say a view
*should* relate to another, so a pile of pictures scores as well as a
description does.

**And that is the never-build, restated.** ROADMAP: *"missing-edge
inference (the participant-pair sweep's no-oracle shape with a query
language)"*. The oracle problem is identical — nothing in a repository
says which diagrams are meant to be one architecture description — and
the false-positive shape is worse, since independent diagrams are normal
and correct. 42010 supplies a precise name for the gap and no way to
close it.

### 8.5 What was not measured

**Clauses 6, 7 and 8** — every requirement in the standard — behind the
paywall. **42030's text**, likewise; its abstention is characterized from
a secondary summary and abstracts, and §5.5 leans on it, so a reader who
can open 42030 should check that characterization before citing §5.5
further. **TRAK's published conformance statement**, which would have
shown a worked example of what conformance argumentation looks like,
returned 403. No viewpoint catalogue (4+1, Rozanski & Woods, TOGAF) was
exercised against pumllint, and no tool claiming 42010 conformance was
run.

## 9. SWOT

**Strengths (pumllint, internal)**

- XD001–005 implement correspondence rules that a 2022 international
  standard made a headline feature, independently and first.
- The model-set verdict exists, so the tool already reasons above the
  single file.
- The claim language has never asserted a standards relationship, so
  §4.1 requires no correction — only confirmation.

**Weaknesses (pumllint, internal)**

- §8.4: disjoint diagrams score 100/100 as a "model set", and the fix is
  refused on principle rather than deferred.
- §8.3: "Precise" and "architecture description" are far apart, and
  nothing in the output signals which one it is talking about.

**Opportunities (external)**

- Only F3, and it is a document nobody has asked for, gated behind a
  paywall.

**Threats (external)**

- **Procurement.** Defence, aerospace and public-sector buyers do ask for
  42010 conformance statements. A future adopter could need one, and
  §4.1's answer — the standard defines no target at this altitude — is
  correct but is not the answer such a buyer wants. That is the one
  place this evaluation could be forced back open.
- §5.5's second reading, which is a threat to the scoring model's
  premise rather than to its market.

## 10. Decision, recorded candidates, triggers

**Decision: no 42010 conformance claim, no viewpoint or stakeholder
modelling, and no correspondence-completeness rule. One fit parked (F3),
two observations recorded, nothing queued.**

**Never build:**

- A 42010 conformance claim, alignment badge, or "42010-aware" mode (N1)
  — the standard defines no conformance target at pumllint's altitude,
  and its text is not readable by the people such a claim addresses.
- Viewpoints, views, stakeholders or concerns as first-class model
  concepts (N2) — that is an AD tool with a linter attached.
- A "views must correspond" rule (N3) — **missing-edge inference**, whose
  no-oracle refusal transfers exactly, with a worse false-positive shape.
- Renaming dimensions or levels into 42010 vocabulary (N4).

**Recorded, not queued:**

1. **The correspondence half-implementation** (§8.4). XD001–005 are
   correspondence *rules*; the correspondence *requirement* has no
   counterpart and its fix is already refused. Recorded with the
   never-build link so that a future reader meeting 42010 does not
   propose the rule again as though it were new.
2. **The model-kind fit** (F3) — the single conformance target 42010
   makes reachable, parked jointly on the paywall and the demand bar.
3. **The streak reframe** (§5.5). Thirteen ecosystems, no grader, and the
   thirteenth is **ISO/IEC/IEEE 42030 declining to define an aggregate
   verdict for architecture evaluation**. The streak can no longer be
   cited as evidence of an unoccupied niche without this attached: the
   field's own evaluation standard considered the aggregate and stopped
   short. Both readings stay open, and future notes should cite the
   streak with the caveat rather than as a count.

**Re-litigate on:**

- **An adopter needing a 42010 conformance statement for procurement** —
  the only trigger a user can fire, plausible in defence and aerospace,
  and the one case where §4.1's correct answer is unsatisfying enough to
  be worth revisiting.
- **42010 or 42030 becoming freely readable** — would make F3 checkable
  and would let §5.5's characterization be verified rather than trusted.
- Evidence that any tool produces an aggregate architecture-quality
  verdict — the standing streak trigger, now with a sharper meaning: it
  would show the field moving *toward* what this project already does.
- **Not** on viewpoint catalogues gaining adoption. 4+1 and Rozanski &
  Woods have had decades; they describe how to organize descriptions, not
  how to check files.

## Related reading

- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) —
  the only prior mention, which took a "42010-aligned" claim at face
  value; §4.1 is what that phrase can and cannot mean.
- [The Capella / Arcadia ecosystem, evaluated](capella-arcadia-ecosystem-evaluation.md)
  — the immediately preceding note, whose category convergence is the
  second of the three §5.1 counts, and whose EPL run §7 breaks (the
  constraint here is *access*, not compatibility).
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  bpmnlint convergence, first of the three.
- [The SysML ecosystem, evaluated](sysml-ecosystem-evaluation.md) — the
  `trace` carrier measurement, the closest predecessor in shape to §8.4:
  a deliberate limit whose cost had not been measured.
- [ROADMAP.md](../ROADMAP.md) — the missing-edge-inference never-build
  that decides F4, the demand bar that parks F3, and the claim-language
  discipline behind N1.
