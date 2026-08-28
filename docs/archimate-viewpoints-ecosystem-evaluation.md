# The ArchiMate viewpoints ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `51bc97d` (v0.30.0).
Nineteenth in a series, and a **narrowing return**: ArchiMate the
notation was evaluated third (2026-08-27). This note is about the
**viewpoint mechanism** — the thing ISO 42010 calls a viewpoint and
ArchiMate implements concretely — which the third note did not examine.*

**Verdict up front: no — and the hypothesis this note was opened to test
did not survive its own research, which is the most useful thing about
it.**

**The hypothesis was that viewpoint conformance is mechanically
checkable.** An ArchiMate viewpoint is built by selecting a subset of
element and relationship types, so "this view declares viewpoint X but
contains an element X excludes" looks like a lintable property — and
lintable properties are rare in this series. **Three findings killed
it**, in order of decisiveness:

**(1) ArchiMate does not make view-to-viewpoint conformance a
requirement.** The spec defines a viewpoint as *"A specification of the
conventions for a specific architecture view"* (§2.4) and a view as
*"A representation of a system from the perspective of a related set of
concerns"* (§2.3). The construction *procedure* is a subset selection,
but the criterion for what appears in a view is **stakeholder
relevance — an editorial judgement, stated as such**. Adversarial
verification confirmed the load-bearing negative: **no normative rule
anywhere in the specification makes a view's conformance to its viewpoint
a requirement.** And the 25 example viewpoints are explicitly
**informative**: conformance requires supporting the viewpoint
*mechanism*; supporting the example viewpoints is a **MAY**. §5.1.

**(2) The ecosystem already handles it, upstream, with a graded
response.** Archi offers the 25 viewpoints as a per-view setting (default
*None*) and applies **three mechanisms of increasing weakness**: it
**filters the palette** — its help says *"only the elements permitted for
the current Viewpoint are available in the Palette, whilst the others are
not available"*, a hard input restriction — it **ghosts** elements that
arrive anyway by drag-and-drop, and its Validator reports *"Invalid
elements in viewpoints"* as one of eight **opt-in** checkers, a
WarningType, testing **elements only**. What it declines to do is
**block** a drag-and-drop. By contrast Archi **hard-blocks relationship
legality at authoring time**: a disallowed relationship cannot be drawn
at all. **The ecosystem treats legality as a hard constraint and
viewpoint membership as a graded discouragement** — and it has clearly
thought about where on that scale each belongs.
§5.2 — and this is the third note's **N2** ("relationship-legality rules
… legality is the settled anti-goal, and this ecosystem enforces it
upstream by construction") extending cleanly to viewpoints, not a new
question.

**(3) Measured, and this is a controlled experiment — the first in the
series.** Two ArchiMate views, **identical in structure, arrow glyphs and
element count**, differing only in which ArchiMate layer and element type
each node carries. One conformant to the Application Cooperation
viewpoint; one violating it with business-layer and technology-layer
elements that viewpoint excludes. Both declare the viewpoint in the
title, as a practitioner would:

| | type | level | score | elements | findings |
|---|---|---|---|---|---|
| **conformant** | `sequence` | 4 | 90.00 | 8 | 4× false SEQ009 |
| **violating** | `sequence` | 4 | 90.00 | 8 | 4× false SEQ009 |

**Byte-identical output.** Not approximately — identically, and identically
again under `--profile codegen` (both Level 2, 47.50, four blockers).
Replacing the declared viewpoint with a *wholly fictitious* one changes
nothing either: the title is opaque text. **Viewpoint conformance is not
partially visible to pumllint; it is exactly invisible**, and the
invisibility is profile-independent. §8.3.

**The one genuinely new measurement is elsewhere, and it amends a
standing candidate.** The third note's §8.1 arrow table has **two**
outcomes — `unknown`/Level 1, or `sequence`/Level 3–4. Extending it with
the glyph ArchiMate practitioners use for **realization** produces a
**third**: `class`. §8.4, and §10's amendment.

*Bounds. **ArchiMate 3.2's text could not be read**: every Open Group host
serving it (`pubs.opengroup.org`, `digital-portfolio.opengroup.org`)
redirects to Open Group SSO — the same gate that defeated the TOGAF
evaluation. Research therefore worked from the **ArchiMate 3.1
Specification (Open Group C197, 2019)**, obtained as the Personal PDF
Edition and text-extracted, so **every verbatim quotation below is 3.1**,
and whether 3.2 renumbered or changed any viewpoint's element list is
**not established**. Section numbers, viewpoint counts and the four
basic-viewpoint categories are 3.1 figures. **No ArchiMate tool was
executed**; Archi's behaviour is characterized from its shipped help,
5.9.0 user guide and source, read by research agents, not run — and one
claim about it was corrected by the adversarial pass (§5.2). Per session scope **no
GitHub repository was read by me**; research agents fetched public files.
All pumllint claims were executed by me at `51bc97d` (v0.30.0) with
default config from a neutral working directory, except where
`--profile codegen` is named. Research for this note was run as a
parallel workflow with an adversarial verification pass; where a
verifier corrected a claim, the corrected form is what appears here.*

## 0. Why this ran, and what it deliberately does not restate

The third note (2026-08-27) settled **ArchiMate the notation**: a
principled no, on two grounds — the `.puml` is a generated rendering of a
model held elsewhere, and ArchiMate's externally-authored rule spec is a
*legality metamodel* whose enforcement is the settled anti-goal. It
measured the native dialect at **Level 4 (Precise), 93.33**, reading one
third of a nine-thing model and misreading all of it, and it recorded the
**typing-confidence / type-marker candidate** that has since been amended
twice.

**None of that is re-derived here, and none of it is presented as new.**
Specifically, this note does not restate the 93.33 measurement, does not
re-promote ArchiMate's invisibility to "load-bearing" (the NAF/MODAF note
did that on its own ground), does not propose type-marker widening as a
new idea, and does not quote the NAF Route B result without its Route A
pair.

What the third note did not examine is the **viewpoint mechanism**: the
apparatus by which ArchiMate selects, for a stakeholder concern, a subset
of its metamodel. That is a different object from the notation, it is the
concrete instance of the concept ISO 42010 defines abstractly, and it
looked — before the research — like the rare case of an externally
specified property a linter could check.

## 1. The mechanism

### 1.1 What ArchiMate says a viewpoint is

From the ArchiMate 3.1 Specification, verbatim:

> **architecture view** — *A representation of a system from the
> perspective of a related set of concerns.* (§2.3)
>
> **architecture viewpoint** — *A specification of the conventions for a
> specific architecture view.* (§2.4)

The body chapter adds an ISO-42010-flavoured second definition in which
the viewpoint *prescribes* the view's content, and states the governance
direction explicitly. **Creating a viewpoint is defined as a
procedure**: select a subset of element and relationship types, then
choose a representation. That subset semantics is real and was confirmed
under adversarial verification.

But two things sit against reading it as a conformance obligation:

- **The selection criterion is editorial.** What appears in a view is
  determined by **stakeholder relevance**, and the spec says so.
- **Nothing makes it a requirement.** The verifier's task was to refute
  the negative and could not: **no normative rule anywhere in the
  specification makes a view's conformance to its viewpoint a
  requirement.**

### 1.2 The catalogue is informative

ArchiMate 3.1 Appendix C, *"Example Viewpoints"*, defines **25**
viewpoints (C.1.1–C.1.13 basic, plus motivation, strategy and
implementation groups). The 13 basic viewpoints are grouped into four
categories — **Composition, Support, Cooperation, Realization** — defined
by the direction of the relationships they emphasise.

**The catalogue is explicitly optional**: conformance requires the
viewpoint **mechanism**; support for the example viewpoints is a **MAY**.
So even the subset lists that *do* exist are not the kind of thing a
conformance check could be built on without the tool inventing the
obligation itself.

*(Counts, numbering and categories are ArchiMate 3.1. A verifier
established that 3.1 added two viewpoints over 3.0.1 and renumbered the
basic block — so version drift in this catalogue is real, and the 3.2
figures are unknown to this note.)*

## 2. What PlantUML models — which turns out to be the deeper answer

The third note recorded that pumllint does not treat `archimate` as a
type marker. The research for this note establishes something one layer
down, and it reframes the whole question:

- **`archimate` is not a PlantUML diagram type.** It is a single-line
  *element command* inside the Description Diagram factory, and PlantUML
  itself classifies it among **53 element-type keywords** alongside
  `rectangle`, `node`, `folder` and `agent`. There is no `ARCHIMATE`
  member in PlantUML's diagram-type enum, and `@startarchimate` is
  rejected.
- **The element type is an icon, not a type.** `CommandArchimate`
  creates a generic description leaf; there is no ArchiMate element-type
  field anywhere in PlantUML's model.
- **The `<<element-type>>` stereotype is string-interpolated into a
  sprite path** and stored as a stereotype. Nothing validates it — a
  **nonexistent ArchiMate element type is accepted silently** and
  rendered as guillemet text.
- **The layer colours are seven ordinary named colours**, usable on any
  element in any diagram type, carrying no layer semantics.

**So pumllint's blindness to ArchiMate element types is not pumllint's
alone: PlantUML does not model them either.** There is nothing in the
parsed artefact to read, because the artefact never carried it. That is a
stronger and more honest statement of the boundary than "pumllint does
not recognise the keyword", and it belongs to this note rather than the
third one.

## 3. Overlap

| Concern | pumllint | ArchiMate viewpoints | Reading |
|---|---|---|---|
| Viewpoint as a declared subset | no concept | the mechanism, normatively required to be *supported* | **Disjoint — §1.1** |
| View-to-viewpoint conformance | invisible (§8.3) | **not a requirement**; Archi filters, ghosts, then warns | Owned upstream, graded |
| Relationship legality | anti-goal (3rd note, N2) | **hard-enforced by Archi at authoring time** | Owned upstream, by construction |
| Element vocabulary | none — and **PlantUML has none either** (§2) | 60+ typed elements across layers | Nothing to read |
| Behavioural/interaction shape | `sequence` — the deepest pack | **no sequence-shaped viewpoint in the catalogue** | Near-empty intersection — §5.4 |
| Aggregate verdict | levels + composite | none found in any ArchiMate tool | Nineteenth, no grader |

## 4. Boundaries

1. **Conformance is not defined**, so there is no external obligation to
   check against (§1.1).
2. **The catalogue is informative**, so even the subsets are not binding
   (§1.2).
3. **PlantUML carries no element types**, so the property is absent from
   the artefact, not merely unread (§2).
4. **The ecosystem's own tool already calibrated it** — filter, ghost,
   warn; don't block (§5.2).

## 5. Sense — five true things

### 5.1 The hypothesis died, and killing it is the result

This note was opened because viewpoint conformance *looked* checkable —
a declared subset, a mechanical membership test. §1.1 shows the spec does
not frame it as an obligation, and §1.2 shows the subsets themselves are
informative. **A linter enforcing viewpoint membership would be inventing
a requirement its own ecosystem declined to make.**

Recording a refuted hypothesis is worth as much as recording a confirmed
one, and this series has now done both (the NAF sibling test came back
negative; this one came back refuted from the primary source).

### 5.2 Archi has already drawn the line, and it is the third note's line

The most instructive fact found: **Archi hard-blocks illegal
relationships, and applies to viewpoints a graded response that stops
short of blocking** — palette filtering, then ghosting, then an opt-in
validation warning. Two constraints from the same specification,
deliberately given different enforcement strengths by the ecosystem's
dominant open-source tool.

*(An earlier draft of this note said Archi "does not enforce" viewpoints
and "never blocks". That was wrong and the adversarial pass caught it:
palette filtering is a real input restriction. The corrected picture is
more useful anyway — the ecosystem has not ignored viewpoint conformance,
it has calibrated it.)*

Two details make naive containment checking wrong even where a subset
exists, and both are the spec's own words: *"In addition to the specified
elements, the grouping element, junction, and or junction can be used in
every viewpoint"*; and the Layered viewpoint's row reads *"All **core**
elements and all relationships are permitted"* — core excludes Motivation,
Strategy and Implementation & Migration elements, so **no viewpoint in the
3.1 catalogue permits everything**, while Archi implements Layered as
literally-everything-allowed. **The tool and the specification disagree**,
which is a further reason no third party should be adjudicating
membership.

That is the third note's **N2** confirmed from a new direction. N2
refused relationship-legality rules on the ground that "this ecosystem
enforces it upstream by construction" — and the same sentence now covers
viewpoints, with the graded enforcement the ecosystem itself chose.
**Viewpoint-conformance rules are refused under the existing never-build,
not a new one.**

### 5.3 The controlled experiment is the series' cleanest measurement

§8.3. Everything held constant but the property under test, and the
output is **byte-identical**. Previous notes measured invisibility by
showing a bad score or a false finding; this one shows that two files
which differ *precisely* in the property under discussion are
indistinguishable to the tool, including under the strictest profile, and
including when the declared viewpoint is replaced with nonsense.

### 5.4 The intersection with the pack set is near-empty, consistent with TOGAF

Research found **no sequence-shaped viewpoint** in the 25 — a conclusion
the adversarial pass upheld while flagging the evidence as fragile, so it
is stated here as a conclusion and not a count. ArchiMate viewpoints are
structural and relational; the Zachman note measured pumllint's rule mass
as **67% Who + When**. Those do not meet.

This matches the TOGAF result (`sequence` mapped to **0 of 32** diagrams)
and is the opposite of DoDAF (**3 of 52**, plus an explicit
any-notation permission). **Three data points now say the same thing:
whether pumllint fits a framework depends on whether that framework asks
for time-ordered interaction models, and ArchiMate's viewpoints do not.**

### 5.5 Access, eighth data point — and a new resolution

**ArchiMate 3.2 is behind Open Group SSO**, the same gate that defeated
the TOGAF note entirely. But here the gate was *routed around
downward*: the previous edition, **ArchiMate 3.1 (C197, 2019)**, is
published as a Personal PDF Edition and was read directly.

So the tally gains a shape it did not have: **current edition gated,
previous edition readable.** TOGAF yielded no primary text at all; this
note has verbatim spec quotations, one version behind, and says so in
every one of them.

## 6. Nonsense — five moves to refuse

**N1. A viewpoint-conformance rule. Refused under the third note's N2,
not as a new decision.** §5.2: legality is the settled anti-goal, and
this is a legality question the ecosystem enforces upstream — more weakly
than relationship legality, because it chose to.

**N2. A viewpoint concept in pumllint's model. Refused under the 42010
note's N2.** Viewpoints, views, stakeholders and concerns as first-class
model concepts would make this an architecture-description tool with a
linter attached. Second ecosystem to invite it; same refusal.

**N3. Reading §8.4's `class` row as a reason to build an ArchiMate
reader. Refused.** It is a type-marker mis-fire in pumllint, fixable (if
at all) inside candidate 1's existing scope. It is not evidence that
ArchiMate element types should be read — §2 shows they are not in the
artefact to begin with.

**N4. Presenting any of §8.3 or §8.4 as a new defect class. Refused.**
The type-fallback class was characterized and closed in the third note.
§8.3 is a sharper *demonstration* of it and §8.4 is an *amendment* to its
candidate. Neither is a discovery, and the record should not be able to
be read as though a nineteenth note found a nineteenth defect.

**N5. Claiming this note establishes anything about ArchiMate 3.2.
Refused.** Every quotation is 3.1 (§Bounds). The 3.2 catalogue may
differ, and a verifier specifically flagged that 3.2 moved Physical
elements into the Technology chapter — which could change viewpoint
element lists.

## 7. Fit — graded

### F1 — a viewpoint pack, mode, or conformance check. **No.** N1, N2.

### F2 — the third amendment to candidate 1. **A real amendment; still not queued.** §8.4, §10.

The one thing this note contributes to the product record. Candidate 1
proposes widening the type-marker set so declaration keywords like
`archimate` type a file `unknown`. §8.4 shows the type-marker set does
not merely *omit* — it **mis-fires**: `<|` and `|>` are themselves type
markers (`parser/class_.py:67`), so an ArchiMate view drawn with
**realization** relationships is typed `class`. A fix that only widens
the keyword set leaves that cell wrong.

### F3 — anything premised on ArchiMate element types being readable. **No.** §2, N3.

### Fit against declared constraints

| Declared constraint | Where these land |
|---|---|
| **Legality is the settled anti-goal** | **Decides N1** — and now covers viewpoints, not just relationships. |
| **No metamodel / AD concepts in the model** | Decides N2. |
| **Claim language** | Nothing here claims anything about ArchiMate; the third note's audit stands. |
| **Golden score contract** | Candidate 1 remains a scoring change needing its own decision and a deliberate re-freeze. Unchanged by this note. |

## 8. Gap — measured

### 8.1 No discovery probe

ArchiMate viewpoints define no file format. Seventh note in the series
with no §8.1 boundary measurement — the third note already measured the
notation's discovery behaviour and this note adds nothing there.

### 8.2 The samples

Two ArchiMate views in PlantUML's native `archimate` form, **constructed
to differ in exactly one property**: four elements each, four `-->`
relationships each, identical topology, identical labels-absent, both
carrying `@startuml app-cooperation-view` and
`title Application Cooperation viewpoint — order handling`.

The **conformant** view uses application-layer elements only
(`application-component` ×2, `data-object`, `application-service`). The
**violating** view substitutes two business-layer elements
(`business-actor`, `business-process`) and two technology-layer elements
(`node`, `technology-service`) — element types the Application
Cooperation viewpoint excludes.

### 8.3 Byte-identical, including under codegen

```
conformant   type=sequence  Level 4  90.00  elements=8
violating    type=sequence  Level 4  90.00  elements=8

$ diff <(pumllint conformant.puml) <(pumllint violating.puml)   # modulo filename
(no differences)

both:  4× [SEQ009/minor] Return '<unlabelled>' … pairs with no preceding call
```

Under `--profile codegen`, both collapse identically to **Level 2
(Structured), 47.50, 12 issues, 4 blockers** — and remain byte-identical
to each other. Replacing the title's viewpoint name with *"Wholly
Fictitious viewpoint"* also produces byte-identical output: the declared
viewpoint is opaque text.

**Three ways of asking the question, three identical answers.** The
property is absent, not approximated.

### 8.4 A third outcome for the third note's arrow table

The third note's §8.1 measured seven relationship notations and found two
outcomes: `unknown`/Level 1 (honest) or `sequence`/Level 3–4. Extending
that table with the glyphs ArchiMate practitioners actually use for named
relationship types — on one model of five elements and four
relationships, varying only the glyph:

| ArchiMate relationship | glyph | type | level | score | elements |
|---|---|---|---|---|---|
| composition | `*-->` | `unknown` | 1 | 95.00 | 0 |
| **realization** | `..\|>` | **`class`** | 4 | **99.31** | 9 |
| serving | `-[#black]->` | `sequence` | 3 | 88.19 | 9 |
| association | `-->` | `sequence` | 4 | 90.42 | 9 |
| aggregation | `o-->` | `sequence` | 4 | 90.42 | 9 |
| triggering | `-->>` | `sequence` | 4 | 90.42 | 9 |
| plain/undirected | `--` | `sequence` | 4 | 90.42 | 9 |

**The realization row is the new cell, and it is the worst case
measured in this ecosystem.** Typed as a *different diagram type*, scored
**99.31**, and **completely silent** — its only findings are "no title"
and "no name". The `sequence` rows at least emit false SEQ009s, which
signal that something is off; the `class` row emits nothing at all.

The mechanism is exact and is not a fallback:

```python
# pumllint/parser/class_.py:67
_TYPE_MARKER_ARROW = re.compile(r"<\||\|>")
# :161
if m and (is_class or _TYPE_MARKER_ARROW.search(m.group("arrow"))):
    d.diagram_type = "class"
```

`<|` and `|>` are **themselves type markers**, independent of any `class`
keyword. Confirmed across all three realization spellings — `..|>`,
`--|>`, `<|..` — each typing `class` at Level 4, 97.92.

The third note tested `..>` (no bar) and got `sequence`. One glyph
character apart, and the file becomes a different kind of diagram.

### 8.5 What was not measured

**ArchiMate 3.2**, entirely (§Bounds) — all spec quotations are 3.1.
**No ArchiMate tool was run**: Archi's ghosting, its Validator's
WarningType and its relationship hard-blocking are characterized from its
5.9.0 guide and source as read by a research agent, not observed.
Commercial tools (BiZZdesign, Visual Paradigm, Sparx) could not be
resolved on whether they block or warn. No coverage count of the 25
viewpoints against pumllint's packs is attempted — §5.4 states a
conclusion, not a number, because the evidence for it was flagged fragile
under verification.

## 9. SWOT

**Strengths (pumllint, internal)**

- Nothing here requires a change: every refusal lands on an existing
  never-build, which is what a mature record should do on its
  nineteenth evaluation.

**Weaknesses (pumllint, internal)**

- §8.3: a property central to the ecosystem is exactly invisible, and the
  report gives no signal that it is not being assessed.
- §8.4: the `class` mis-fire is silent, high-scoring, and reachable by a
  one-character difference — the least detectable failure this ecosystem
  produces.

**Opportunities (external)**

- None. F2 is an amendment to a candidate that already has no trigger.

**Threats (external)**

- None specific to viewpoints. The standing threat is the one the
  FEAF/Gartner note recorded and left open.

## 10. Decision, recorded candidates, triggers

**Decision: no ArchiMate viewpoint support of any kind — no conformance
check, no viewpoint concept, no reader. Every refusal here extends an
existing never-build rather than adding one. One amendment recorded;
nothing queued.**

**Never build:**

- A viewpoint-conformance rule (N1) — refused under the **third note's
  N2**: legality is the settled anti-goal, and the ecosystem enforces it
  upstream, having itself chosen to make viewpoints advisory (ghosting, an
  opt-in Validator warning) while hard-blocking illegal relationships.
- Viewpoints/views/stakeholders/concerns as model concepts (N2) —
  refused under the **42010 note's N2**.
- Anything premised on ArchiMate element types being readable (N3) —
  **PlantUML does not model them** (§2), so they are absent from the
  artefact, not merely unread.

**Recorded, not queued:**

1. **Third amendment to candidate 1** (F2, §8.4). The type-marker set
   does not only *omit* declaration keywords — it **mis-fires**: `<|` and
   `|>` are type markers in their own right (`parser/class_.py:67,161`),
   so an ArchiMate view using **realization** relationships is typed
   `class` and scored **99.31 with no findings at all**. Any fix must be
   validated against a realization-glyph file as well as the
   foreign-diagram and YAML shapes the two earlier amendments named.
   **This is the quietest instance on record**: the sequence-typed cases
   at least emit false SEQ009s; this one emits nothing.
2. **The controlled viewpoint-invisibility measurement** (§8.3) — two
   files differing in exactly one property produce byte-identical output,
   under both profiles, and with a fictitious viewpoint name. Cite it when
   the question is what "Precise" does and does not assert.
3. **The specification finding** (§1.1) — *no normative rule makes a
   view's conformance to its viewpoint a requirement*, and the 25 example
   viewpoints are informative. Recorded so a later reader meeting the
   subset-selection procedure does not re-derive the hypothesis this note
   refuted.

**Re-litigate on:**

- **ArchiMate 3.2 becoming readable**, which would let §1.1's negative be
  checked against the current edition rather than 3.1.
- ArchiMate making view-to-viewpoint conformance normative in a future
  edition — the single change that would reopen §5.1, and there is no
  sign of it.
- **Not** on Archi's Validator gaining strength: it warning more loudly
  is the ecosystem doing its own job upstream, which is the reason for
  the refusal, not an opening.

## Related reading

- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the third note, which settled the notation; this one is the narrowing
  return to its viewpoint mechanism, and §8.4 amends its candidate 1.
- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — the abstract concept ArchiMate implements; its N2 decides this note's
  N2.
- [The NAF / MODAF ecosystem, evaluated](naf-modaf-ecosystem-evaluation.md)
  — which promoted the ArchiMate finding to load-bearing; not re-promoted
  here.
- [The TOGAF / ADM ecosystem, evaluated](togaf-adm-ecosystem-evaluation.md)
  and [DoDAF / UAF](dodaf-uaf-ecosystem-evaluation.md) — the two
  framework results §5.4's near-empty intersection sits between.
- [The Zachman ecosystem, evaluated](zachman-ecosystem-evaluation.md) —
  the 67% Who+When rule-mass measurement §5.4 uses.
- [ROADMAP.md](../ROADMAP.md) — candidate 1 and its two prior amendments.
