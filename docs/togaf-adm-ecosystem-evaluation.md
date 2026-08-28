# The TOGAF / ADM ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `0aa0305` (v0.29.0). The
question as posed: investigate the TOGAF/ADM ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Fourteenth in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, Structurizr DSL,
Ilograph, Graphviz/DOT, SysML, Capella/Arcadia, ISO 42010, this).*

**Verdict up front: no on every fit — and the note's value is not the
verdict. It is that TOGAF forces a correction to something this series
has repeated thirteen times.**

**The correction: "Nth ecosystem, no grader" was imprecise, and TOGAF is
where that becomes visible.** TOGAF ships **two** ordinal grading schemes,
and one of them aggregates the way this project aggregates. **Architecture
Compliance** defines six levels — Irrelevant, Consistent, Compliant,
Conformant, Fully Conformant, Non-Conformant. The **Architecture
Capability Maturity Model** defines six maturity levels across nine
architecture elements and computes a rating by **two complementary
methods: a weighted mean maturity level, and the percentage achieved at
each level**. A weighted mean over weighted elements producing an ordinal
level plus percentages **is pumllint's composite, structurally**. The
streak's real criterion was never "does anything grade" — it was "does
anything grade *the artefact class pumllint grades*". That distinction
was implicit for thirteen notes and is stated here. §5.1, §10.

**And the corrected picture is sharper than either half.** The ISO 42010
note, written hours earlier, found ISO/IEC/IEEE 42030 declining to define
an aggregate verdict and read it as the field's considered abstention.
Set beside TOGAF that reading is incomplete. **The field has aggregated
repeatedly and for decades — over organizations (ACMM) and over
implementations (Compliance levels) — and has declined to aggregate over
descriptions.** That is not abstention from aggregation. It is a
consistent choice about which object is worth a number, and pumllint has
chosen a different one. §5.2 states both readings and settles neither.

**The measurement is the best in the series, and it is a genuine
surprise.** Of four TOGAF diagram artifacts drawn in PlantUML, **three
land in the correct parsed type with nothing but cosmetic findings**:

| TOGAF artifact | pumllint type | correct? | level | score | findings |
|---|---|---|---|---|---|
| Business Use-Case Diagram | **`usecase`** | **yes** | 4 | 99.31 | GEN001, GEN002 |
| Conceptual Data Diagram | **`class`** | **yes** | 4 | 98.75 | GEN001, GEN002 |
| Data Lifecycle Diagram | **`state`** | **yes** | 4 | 99.48 | GEN001, GEN002 |
| Application Communication Diagram | `sequence` | no — fallback | 4 | 88.96 | **3× false SEQ009** |

Three artifact classes, three *different* packs, all correct. The Capella
note found one such artefact; this finds three. **And the pack that maps
to none of TOGAF's thirty-two diagrams is the sequence pack** — pumllint's
deepest, eleven base rules plus nine codegen. §8.3.

*Bounds, and one is awkward. **The TOGAF Standard is free but
registration-gated, and I could not read it**: every `pubs.opengroup.org`
URL tried — TOGAF 10, 9.2, 9.1 and 8.1.1 alike — redirects to an OAuth
login this session cannot complete. So every normative claim here about
compliance levels, ACMM and the artifact catalogue comes from **secondary
sources** (vendor guides, a partner's artifact reference, search
summaries), not from the standard. The irony is worth recording: the
*paywalled* ISO 42010 published a preview from which Clause 4 was quoted
verbatim, while the *free* TOGAF yielded no primary text at all. Every
pumllint claim was executed at `0aa0305` with default config from a
neutral working directory. Per session scope no GitHub repository was
read. The four sample diagrams are mine — TOGAF prescribes artifacts, not
notations, so there is no canonical PlantUML form.*

## 0. Why this ran, and the prior record

Two prior mentions, both glancing. The Linked.Archi note recorded that
its subject ships **TOGAF 9.2/10 framework integrations** and
**TOGAF ↔ ArchiMate SKOS mappings**. The ISO 42010 note listed TOGAF among
the viewpoint catalogues and recorded, in its bounds, that no catalogue
"was exercised against pumllint". This exercises one.

TOGAF also closes a loop: it is published by **The Open Group**, the same
body as **ArchiMate**, evaluated third in this series. That note found
ArchiMate's native `archimate` keyword invisible to pumllint and a
nine-element model scored "Precise" on three elements read. TOGAF is the
method that ArchiMate is usually drawn for.

## 1. The ecosystem

### 1.1 What TOGAF is

**The TOGAF Standard, 10th Edition** (April 2022; 9.2 before it, 2018) is
an enterprise-architecture framework: a method, a content framework, a
capability framework and a set of reference models. It is a **process
standard**, not a notation — it prescribes *what to produce and in what
order*, and leaves *how to draw it* open.

### 1.2 The ADM

The **Architecture Development Method** is the core: a Preliminary Phase,
eight lettered phases — **A** Architecture Vision, **B** Business
Architecture, **C** Information Systems Architectures, **D** Technology
Architecture, **E** Opportunities & Solutions, **F** Migration Planning,
**G** Implementation Governance, **H** Architecture Change Management —
and **Requirements Management** at the centre, continuous across all of
them.

A notable 10th-edition change, recorded because it bears on §6: the
**arrowheads were removed** from the ADM cycle diagram, so the standard
"no longer suggests that the phases must be performed in any specific
sequence".

### 1.3 The Architecture Content Framework — 56 artifacts

TOGAF classifies artifacts as **catalogs** (lists of things), **matrices**
(relationships between things) and **diagrams** (pictures of things). A
partner's published reference enumerates:

| Type | Count |
|---|---|
| **Diagrams** | **32** |
| Catalogs | 14 |
| Matrices | 10 |

The diagrams span Phase A (Value Chain, Solution Concept, Business
Footprint) through Phase E (Project Context, Benefits), with the bulk in
B and C. This catalogue is what §8.3 measures against.

### 1.4 The two grading schemes

**Architecture Compliance** defines six ordinal levels for how a project
or implementation relates to an architecture specification:

| Level | Meaning (as published in secondary sources) |
|---|---|
| Irrelevant | no features in common with the specification |
| Consistent | some features implemented in accordance with it |
| Compliant | all implemented features are covered by it |
| Conformant | all specified features implemented, plus some extra |
| Fully Conformant | full correspondence between specification and implementation |
| Non-Conformant | some features implemented *not* in accordance with it |

**The Architecture Capability Maturity Model (ACMM)**, developed by the US
Department of Commerce and carried in TOGAF's capability framework,
defines **six maturity levels** (None, Initial, Under Development,
Defined, Managed, Measured) across **nine architecture elements**, and —
this is the part that matters — computes a rating by **two complementary
methods: a weighted mean Enterprise Architecture maturity level, and the
percentage achieved at each maturity level across the nine elements**.

§5.1 is about that sentence.

## 2. The seam

pumllint reads a `.puml` file and scores it. TOGAF governs an
architecture *practice*: which artifacts exist, in which phase, reviewed
by which governance body, produced by an organization at some capability
maturity.

A `.puml` file could be the rendering of one of TOGAF's 32 diagram
artifacts. That is the entire seam, and §8.3 measures how well it holds.
Everything else TOGAF specifies is process.

## 3. Overlap

| Concern | pumllint | TOGAF | Reading |
|---|---|---|---|
| Diagram artifacts | five parsed types | **32 named diagrams** | **7 map — §8.3, and the mapping is better than expected** |
| Use-case modelling | `usecase` pack | Business & Application Use-Case Diagrams | **Correct, measured** |
| Data structure | `class` pack | Conceptual & Logical Data Diagrams | **Correct, measured** |
| Lifecycle | `state` pack | Product & Data Lifecycle Diagrams | **Correct, measured** |
| Control flow | `activity` pack | Process Flow Diagram | Plausible, unprobed |
| **Interaction** | **`sequence` — the deepest pack** | **no sequence diagram in the catalogue** | **Zero counterpart — §8.4** |
| Ordinal grading | levels 1–5 + composite | **Compliance levels; ACMM weighted mean** | **§5.1 — the correction** |
| Governance process | none | ADM phases, compliance reviews, boards | TOGAF-side entirely |
| Requirements | `trace` matrix | Requirements Management, continuous | Adjacent, different scale |

## 4. Boundaries

1. **Process vs artefact.** TOGAF says produce a Data Lifecycle Diagram
   in Phase C. pumllint says whether the file you produced holds
   together. Neither speaks to the other's question.
2. **No notation.** TOGAF names 32 diagrams and prescribes no syntax for
   any of them, so there is nothing to parse and no conformance to a
   drawing convention to check.
3. **Access.** Registration-gated, and unreadable in this session (§8.5).
4. **Object of grading.** TOGAF grades organizations and implementations;
   pumllint grades descriptions. §5.1.

## 5. Sense — five true things

### 5.1 The streak's criterion was imprecise, and this is the correction

Thirteen notes carry a line of the form *"Nth ecosystem, no grader"*, with
the criterion given as producing no level, gap report, ratchet or
aggregate. Read literally, **TOGAF falsifies it** — and has since long
before this project existed. Compliance levels are an ordinal scale.
ACMM is an ordinal scale *computed by weighted mean over weighted
elements, reported alongside per-level percentages*, which is what
`scoring.py` does.

The criterion the series was actually applying is narrower: **does any
tool in the ecosystem grade the artefact class pumllint grades — a
diagram file, or a set of them?** On that criterion nothing here grades
either, and the streak stands at fourteen. But the narrower criterion was
never written down, and "no grader" as published overstates.

What the record should carry from now on is the qualified form. Three
things follow:

- **Nothing found in fourteen ecosystems grades a description artefact.**
  That is the claim the evidence supports.
- **Plenty grades adjacent objects**, and TOGAF has done so for decades.
- The two are different claims and the notes conflated them.

### 5.2 And the corrected picture sharpens the 42010 finding rather than softening it

Hours before this note, the ISO 42010 evaluation found ISO/IEC/IEEE 42030
— the standard whose whole subject is architecture evaluation — defining
a process and framework while declining to specify a scoring scheme,
rating scale, maturity level or aggregate verdict. It read that as a
considered abstention and left two readings open.

TOGAF completes the picture, and not in the comfortable direction. The
same professional field that declined to aggregate over architecture
*evaluations* has aggregated enthusiastically over architecture
*capability* and *compliance*, with weighted means and percentage
scorecards, since the 1990s. **So the field is not shy of aggregation.**
It aggregates over organizations and implementations, and does not
aggregate over descriptions.

Both readings of that survive, and this note settles neither:

- **The niche is empty because it is hard to occupy well** — grading a
  description is a different and possibly better-founded problem than
  grading an organization, and nobody has attempted it because the
  artefacts were not in version control until recently.
- **The niche is empty because the field considered it and put the
  number elsewhere** — descriptions were judged the wrong object to
  score, and pumllint is doing the thing that was declined.

The honest summary is that the second reading is now better supported
than it was this morning, and the first is not refuted. Anyone citing the
streak should carry both.

### 5.3 Three of four TOGAF artifacts land correctly, which is the best result in fourteen

§8.3. Not one artefact, as with Capella's Exchange Scenario — three,
across three different packs, with nothing but GEN001 and GEN002 on any
of them. TOGAF's artifact names describe *kinds of model* — use case,
data structure, lifecycle — and three of those kinds are exactly what
three of pumllint's five packs are for.

### 5.4 The Open Group loop closes usefully

ArchiMate (third in the series) is the notation; TOGAF is the method it
serves. The ArchiMate note found the notation invisible to pumllint. This
note finds the method's *artifact kinds* mapping cleanly. The two results
are consistent and jointly informative: the ecosystem's **vocabulary**
does not survive contact with pumllint, and its **model kinds** do.

### 5.5 Access categories now number three, and free is not the same as readable

42010: **paid**, with a published preview from which Clause 4 was quoted
verbatim. TOGAF: **free**, registration-gated, and **no primary text
obtained at all**. Recorded because the obvious inference — paywalled
means unreadable, free means readable — is exactly backwards here, and a
future note should check rather than assume.

## 6. Nonsense — six moves to refuse

**N1. A TOGAF artifact-type recognizer or pack. Refused on the artefact.**
TOGAF prescribes no notation for any of its 32 diagrams. A "Business
Footprint Diagram" has no syntax to detect; a rule pack for one would be
inventing the convention and then checking it.

**N2. Mapping pumllint's maturity levels onto ACMM's, or onto the
compliance levels. Refused — this is the trap and it is a worse version
of the Arcadia one.** Arcadia's five perspectives at least were not a
*quality* ladder. ACMM's six levels are, and Compliance's six are too,
and both are ordinal — so a side-by-side table would look defensible and
be false. **ACMM grades an organization's capability. Compliance grades
an implementation against a specification. pumllint grades a
description.** Three objects, three ladders, no correspondence.

**N3. Claiming pumllint supports, enables, or accelerates the ADM.
Refused.** The ADM is a process with governance gates. A linter in CI is
not a phase, does not produce a deliverable named in the content
framework, and does not discharge a compliance review.

**N4. An "ADM phase" tagging convention in `pumllint.toml`. Refused as
scope creep dressed as configuration.** GEN006/GEN007 already let a
project tag whatever it wants in prose carriers; a TOGAF-specific key
would encode one framework's vocabulary in a tool that has kept
deliberately clear of all of them.

**N5. Reading ACMM's existence as validation of the scoring model.
Refused, and it is the mirror of N6 in the 42010 note.** That someone
else computes a weighted mean over weighted elements does not make this
project's weighted mean right; it makes the *shape* familiar and the
*object* the open question. §5.2.

**N6. Treating the removed ADM arrowheads as licence to claim
flexibility.** The 10th edition dropped the arrowheads because phases need
not be sequential. That is a fact about TOGAF's process, not an opening
for a tool that has no phases.

## 7. Fit — graded

### F1 — a TOGAF artifact pack or recognizer. **No.** N1.

### F2 — TOGAF artifact kinds as *already-supported*. **Yes, and nothing to build.** §8.3.

The honest grade. Three of TOGAF's diagram kinds already parse correctly
and score well with no work, because they are use-case, data-structure
and lifecycle models and pumllint has packs for those. This is a fact
about what the tool already does, not a candidate — and it is the second
such fact in the series, after Capella's Exchange Scenario.

### F3 — ADM alignment, phase tagging, or compliance-review support. **No.** N3, N4.

### F4 — a maturity-model correspondence. **No, emphatically.** N2, N5.

### Fit against declared constraints

| Declared constraint | Where the TOGAF fits land |
|---|---|
| **Claim language** | **The operative constraint for F3 and F4.** "TOGAF-aligned", "ADM-ready" and any ACMM level mapping are claims about objects pumllint does not examine. |
| **Demand bar** | Not reached — nothing here is a build candidate at all. |
| **Zero runtime dependencies** | Not reached. |
| **Licence posture** | Not the issue: the constraint is *access* (§5.5), as with 42010. Four evaluations since the EPL run and it has not recurred. |
| **Golden score contract** | Untouched, and note that N2/N5 are the two moves that would have pressured it. |

## 8. Gap — measured

### 8.1 There is no discovery probe

As with 42010, TOGAF defines no file format and no syntax. Nothing to
place beside `.puml`, nothing to wrap. Second note in the series with no
§8.1 boundary measurement, and for the same reason: the subject is a
framework, not a notation.

### 8.2 The samples

Four TOGAF diagram artifacts, hand-drawn in the PlantUML syntax a
practitioner would reach for: a **Business Use-Case Diagram** (actors,
system boundary, three use cases, one `include`), a **Conceptual Data
Diagram** (three classes, two labelled associations with multiplicities),
a **Data Lifecycle Diagram** (seven states, start and end), and an
**Application Communication Diagram** (three components, three labelled
arrows).

### 8.3 Three of four land correctly

| TOGAF artifact | type | correct | level | score | elements | findings |
|---|---|---|---|---|---|---|
| Business Use-Case Diagram | `usecase` | **✓** | 4 | **99.31** | 9 | GEN001, GEN002 |
| Conceptual Data Diagram | `class` | **✓** | 4 | **98.75** | 5 | GEN001, GEN002 |
| Data Lifecycle Diagram | `state` | **✓** | 4 | **99.48** | 12 | GEN001, GEN002 |
| Application Communication Diagram | `sequence` | ✗ | 4 | 88.96 | 6 | **3× SEQ009**, GEN001, GEN002 |

The three correct results carry **no false findings at all** — the only
output is "no title" and "no name", which are true of the samples and
would be true of any untitled diagram.

Extending the mapping across the published catalogue of 32 — my
classification of artifact *names*, not TOGAF's, since the standard
prescribes no notation:

| pumllint pack | TOGAF diagrams that plausibly map |
|---|---|
| `usecase` | Business Use-Case, Application Use-Case (**2**) |
| `class` | Conceptual Data, Logical Data (**2**) |
| `state` | Product Lifecycle, Data Lifecycle (**2**) |
| `activity` | Process Flow (**1**) |
| `sequence` | **none** |

**Seven of thirty-two.** Better coverage than any predecessor except
UML — and distributed across four packs rather than concentrated in one.

### 8.4 The sequence pack maps to nothing, which inverts the series

pumllint's sequence pack is its deepest: eleven base rules plus nine
codegen rules, four of them about activation. In eleven prior evaluations
it was the pack that *fired* — usually wrongly, on foreign syntax
mis-typed as `sequence`.

TOGAF's catalogue of 32 diagrams contains **no sequence diagram**. Its
interaction artefact is the Application Communication Diagram, which
shows components and interfaces, not an ordered exchange over time — and
§8.3 shows what happens when it is drawn with dashed arrows:

```
appcomm.puml:5: [SEQ009/minor] Return 'submitClaim' from 'P' to 'E' pairs with no preceding call
appcomm.puml:6: [SEQ009/minor] Return 'requestPayment' from 'E' to 'Y' pairs with no preceding call
appcomm.puml:7: [SEQ009/minor] Return 'paymentConfirmed' from 'Y' to 'E' pairs with no preceding call
```

Standing type-fallback class, false SEQ009s, already recorded in
ArchiMate, C4, Mermaid, UML and Capella. **No candidate and no
amendment.** One precise observation is worth adding, though: this output
is **byte-identical in level, score, element count and finding set to the
Capella LAB** measured hours earlier — Level 4, 6 elements, 88.96, three
false SEQ009s. Two unrelated frameworks, one shape (three components,
three dashed labelled arrows), one result. C4 sample C reaches the same
*composite* by a different finding set. The composite is not a
coincidence; the shape is common.

### 8.5 What was not measured, and the access problem

**The TOGAF Standard itself.** Every `pubs.opengroup.org` URL attempted —
the 10th edition's capability-and-governance chapter, TOGAF 9.1 chapters
48 and 51, and the 8.1.1 maturity page — returned a 302 to an OAuth
authorize endpoint. Registration is free; completing it is not something
this session can do. **So no compliance-level definition, no ACMM level
list, no calculation description and no artifact catalogue in this note
is quoted from the standard.** All of §1.3 and §1.4 rests on secondary
sources, and §5.1's correction — the most consequential claim here —
rests on a search summary's report of ACMM's two calculation methods.

That is thin support for a correction of this weight, and it is recorded
as such: **anyone with a TOGAF login should verify the ACMM calculation
description before §5.1 is cited further.** The correction's *direction*
is safe — TOGAF plainly has ordinal grading schemes, which is enough to
show "no grader" overstated — but the strength of the structural
similarity claim depends on that one unverified sentence.

Also unmeasured: the Process Flow Diagram against the `activity` pack;
any TOGAF-certified tool; and whether real TOGAF practitioners draw these
artifacts in PlantUML at all, which §9 treats as the open question it is.

## 9. SWOT

**Strengths (pumllint, internal)**

- §8.3: three artifact kinds correct across three packs, no false
  findings. The best foreign-artefact result in fourteen evaluations.
- The `usecase`, `class` and `state` packs — the three least discussed in
  this series — are the ones that earned it.

**Weaknesses (pumllint, internal)**

- §8.4: the deepest pack has no counterpart in the framework's catalogue,
  and the artefact that comes closest mis-types into it and draws three
  false findings.
- §5.1: thirteen notes published a claim in a form the evidence did not
  support.

**Opportunities (external)**

- None that require building. F2 is a description of the status quo.
- The unverified question in §8.5 — whether practitioners draw TOGAF
  artifacts in PlantUML — is the only thing that would turn F2 from a
  fact into a market.

**Threats (external)**

- §5.2's second reading, sharpened: the field aggregates where it has
  chosen to, and has not chosen descriptions. That is a threat to the
  scoring model's premise, not to its correctness.

## 10. Decision, recorded candidates, triggers

**Decision: no TOGAF or ADM support of any kind — no artifact pack, no
phase tagging, no ADM claim, and above all no maturity-model
correspondence. Nothing queued. One correction to the record and two
observations.**

**Correction to the record (the reason this note exists):**

The line *"Nth ecosystem, no grader"*, carried in thirteen entries, is
**imprecise as published**. TOGAF grades — Architecture Compliance's six
levels, and ACMM's six levels computed as a weighted mean over nine
elements with per-level percentages. The criterion the series was
applying is narrower and is now stated: **nothing found in fourteen
ecosystems grades the artefact class pumllint grades — a description.**
Adjacent objects are graded routinely and have been for decades. Future
notes should use the qualified form; past notes should be read with this
attached. Support for the structural-similarity half is a single
secondary source (§8.5) and needs verifying.

**Never build:**

- A TOGAF artifact recognizer or rule pack (N1) — the standard prescribes
  no notation, so the convention would have to be invented first.
- **Any mapping of pumllint's levels onto ACMM's or onto the compliance
  levels** (N2) — three ladders over three different objects
  (organization, implementation, description); a side-by-side table would
  look defensible and be false, which makes it worse than the Arcadia
  trap it resembles.
- Any claim that pumllint supports, enables or accelerates the ADM (N3),
  or a TOGAF-specific phase-tagging config key (N4).
- Reading ACMM as validation of the scoring model (N5) — familiar shape,
  different object, and the object is the open question.

**Recorded, not queued:**

1. **The corrected streak criterion** (above, §5.1) — the substantive
   output of this evaluation.
2. **The sharpened 42010 reading** (§5.2). 42030's abstention plus
   TOGAF's enthusiasm is one picture: the field aggregates over
   organizations and implementations and not over descriptions. Both
   readings of *why* stay open; the second is better supported than it
   was, and the first is not refuted.
3. **F2 as a fact about the tool** — three TOGAF artifact kinds already
   parse and score correctly with no work. Second instance after
   Capella's Exchange Scenario, and the first covering multiple packs.
   Worth citing when the question is what pumllint is for.

**Re-litigate on:**

- **Evidence that practitioners draw TOGAF artifacts in PlantUML** — the
  only trigger a user can fire, and the one that would turn §8.3 from a
  measurement into an audience.
- **A TOGAF login becoming available** — §8.5's verification, and the
  only way to put §5.1's correction on primary-source footing.
- A tool appearing that grades description artefacts — the streak
  trigger, now in its qualified form, and the only form in which it
  remains a meaningful signal.
- **Not** on TOGAF adoption, which is large and has been for twenty
  years without producing a description linter.

## Related reading

- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — written hours earlier; §5.2 sharpens its 42030 finding, and §5.5
  contrasts its paywall with TOGAF's registration gate.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the same standards body, the notation to this method; §5.4 reads the
  two results together.
- [The Capella / Arcadia ecosystem, evaluated](capella-arcadia-ecosystem-evaluation.md)
  — the first artefact that landed correctly, of which §8.3 is the second
  and larger instance; its LAB output is byte-identical to §8.4's.
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) —
  the TOGAF 9.2/10 integrations and TOGAF↔ArchiMate mappings recorded
  there.
- [ROADMAP.md](../ROADMAP.md) — the claim-language discipline that
  decides N2–N4, and the settled-questions entries whose "no grader"
  lines §5.1 corrects.
