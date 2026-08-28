# The Capella / Arcadia ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `e989da8` (v0.29.0). The
question as posed: investigate the Capella/Arcadia ecosystem, then assess
the boundaries, overlap, fit, gap, sense and nonsense of the different
fits against pumllint's roadmap and ecosystem. Twelfth in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, Structurizr DSL,
Ilograph, Graphviz/DOT, SysML, this).*

**Verdict up front: no — and this is the first "no" in the series that
has to be argued *against a fit that works*. Eleven predecessors were
refused because the artefact was wrong, the syntax collided, the licence
forbade it, or the niche was occupied. Here the central measurement is
that an Arcadia **Exchange Scenario** hand-drawn in PlantUML is typed
`sequence`, parsed correctly, scored **Level 4 (Precise) 99.38 with exit
0 and only cosmetic findings** — the full eleven-rule sequence pack
applying *legitimately*, to an artefact from a foreign ecosystem, for the
first time in twelve evaluations. pumllint does this well. And it does
not matter, because **Capella has no PlantUML export** — not in its
official add-on catalogue, not as a community tool. The fit is real and
unreachable.**

**Three further grounds, none of which need the first. (1) Capella is not
a notation with a text form to lint: it is an Eclipse/Sirius graphical
tool over an XML model (`.capella`, `.aird`), and Arcadia is a *method*
before it is a language. (2) Not a producer — unlike SysML v2 and
Structurizr, nothing here writes `.puml`, which breaks a two-evaluation
run and matters for exactly that reason. (3) Capella is **EPL-2.0**, and
this is the *third consecutive* EPL collision. That repetition is now
itself the finding, and §1.4 states it once so a fourth does not
re-derive it.**

*Bounds. Every pumllint claim was executed at `e989da8` with default
config from a neutral working directory (verified: GEN006/GEN007 stay
dormant). **No Capella was installed or run** — its validation
behaviour, add-on catalogue and rule categories are characterized from
`mbse-capella.org` and the Eclipse project page, not observed. Per this
session's repository scope **no GitHub repository was read**, so
Python4Capella, the Capella-Extensions collection and any unindexed
community exporter were not inspected; §2's "no PlantUML export" is a
statement about the **official add-on catalogue plus search**, not a
proof of absence. Arcadia samples are hand-written PlantUML renderings
of Capella diagram types — Capella cannot emit them, so there is no
canonical form to test against, and the samples are mine.*

## 0. Why this ran

No prior Capella record exists beyond three passing references in the
SysML note, which named Capella only as an Eclipse project and a SysON
integration target. This is a first look, and it arrives with two
predecessors' findings pointed at it: the SysML note's EPL-closes-an-
ecosystem result, and its producer→consumer reclassification. Both turn
out to apply differently here, which is why the note is worth its length.

## 1. The ecosystem

### 1.1 A method first, a tool second

**Arcadia** — *ARChitecture Analysis and Design Integrated Approach* —
was developed by Thales between 2005 and 2010 with operational architects
across its business domains, and has been an **AFNOR standard (Z67-140)
since 2018**. That makes it the first *national-standard* ecosystem in
the series; the predecessors were OMG (UML, BPMN, SysML), Open Group
(ArchiMate), or vendor/community projects.

Its own description is *"a tooled method devoted to systems &
architecture engineering"* — and it is **both a method and a modelling
language**, in that order. Five perspectives, worked in sequence:

1. **Operational Analysis** — customer need: actors, capabilities,
   operational scenarios
2. **System Analysis** — what the system must do for them
3. **Logical Architecture** — coarse-grained component breakdown
4. **Physical Architecture** — the buildable architecture
5. **Component Requirements Contracts** — specifications handed to
   subsystem, hardware and software teams

**Capella** is the Eclipse tool that implements it: open-sourced in 2014
under PolarSys, **Mature** project status, release 7.1.0 (2026-07-10).

### 1.2 The diagram catalogue

Structured by perspective, and three families matter here:

| Family | Examples | Shape |
|---|---|---|
| **Architecture blanks** | OAB, SAB, LAB, PAB | components and their exchanges |
| **Data-flow blanks** | SDFB, LDFB, PDFB | *functions* and functional exchanges — information dependency, **not control flow** |
| **Scenarios** | **Exchange Scenarios** (lifelines = components/actors), Functional Scenarios (lifelines = functions) | **lifelines and messages** |

That third row is the whole evaluation. An Exchange Scenario is a
sequence diagram in everything but name, and §8.3 measures what pumllint
makes of one.

The data-flow row carries a trap worth naming early: a DFB is *not* a
flowchart. §8.4 measures the difference, because the natural wrong
assumption — "Arcadia dataflow, therefore pumllint's activity pack" —
does not hold.

### 1.3 Validation, and the shape of the streak question

Capella ships model validation, and the description is close enough to
this project's own vocabulary to be worth quoting:

> Capella organizes model validation rules in several categories:
> **Integrity, design, completeness, traceability**, etc.

with **validation profiles** *"focusing on different aspects"*, and quick
fixes where possible. Set against pumllint's dimensions:

| Capella category | pumllint dimension |
|---|---|
| Integrity | DIM-SEM (semantic correctness) |
| design | — |
| **completeness** | **DIM-CMP — completeness** |
| **traceability** | **DIM-TRC — traceability** |
| — | DIM-CON (consistency), DIM-RDB (readability), DIM-AMB (ambiguity) |

**Two of Capella's four named categories are pumllint's dimension names
verbatim**, and "validation profiles" is what this repository calls rule
profiles. Neither party knew of the other. That is the second
independent-convergence data point in the series after bpmnlint, and the
first on the *taxonomy* rather than on individual rules.

What Capella does with those categories is report violations with
severities. **No score, level, grade, percentage or rolled-up verdict**
appears in its documentation, and the official add-on catalogue contains
no metrics or quality-index add-on — the nearest is a commercial
requirements tool offering "real-time quality analysis" of requirement
*statements*, not of models. **Twelfth ecosystem, no grader.**

### 1.4 The licence, and why the third time is different

Capella is **EPL-2.0** (verified from its Eclipse project page). Against
the never-build — *"EPL dependencies anywhere in the repo (one GPL
sdist — product and lab alike)"* — that is the third consecutive
collision:

| Evaluation | Scope of the collision |
|---|---|
| Graphviz/DOT (2026-08-27) | one **library** |
| SysML (2026-08-28) | the open v2 **tool ecosystem** (SysON, Papyrus) |
| Capella/Arcadia (2026-08-28) | the **tool itself**, and its whole add-on platform |

Three findings, or one? **One.** The MBSE and modelling-tool world is
Eclipse-shaped — EMF, Sirius, Papyrus, Capella, SysON — so a GPL project
that forbids EPL is *structurally excluded from the MBSE tool space*, not
unluckily colliding with it three times. Stating it once here as a
standing condition is the point; a fourth evaluation should cite it
rather than rediscover it, and should not present it as news.

The corollary is worth keeping: the exclusion binds **linking**, not
**reading**. Nothing stops pumllint from linting a `.puml` file that a
Capella user produced by hand, and nothing about EPL would stop a
*separate* Python4Capella script in *someone else's* repository from
writing one. §6 refuses building that script here, for a different
reason.

## 2. The seam — and why there is not one

pumllint reads `.puml`. Capella reads and writes `.capella` and `.aird`,
which are XML. Between them there is no shipped conversion in either
direction.

The official add-on catalogue exports to: **HTML** (XHTML documentation
generation), **MS-Word** (M2Doc), **Simulink**, **ASN.1/AADL** (TASTE),
**SCADE Architect**, **SysML** (Obeo's commercial bridge), and
**Reqtify**. Plus **Python4Capella**, a scripting API that reads and
writes the model from Python.

**No PlantUML anywhere**, and no community `capella2plantuml` surfaced in
search. Python4Capella could obviously write one — the API is there — and
nobody appears to have.

So unlike Structurizr and unlike the SysML v2 pilot implementation, **the
Capella ecosystem is not a producer of the artefact pumllint gates**.
This breaks a two-evaluation run and is worth recording as a negative
rather than passed over: the producer relationship is what made those two
notes interesting, and its absence is what makes §8.3's result stranded.

## 3. Overlap

| Concern | pumllint | Capella / Arcadia | Reading |
|---|---|---|---|
| Scenarios | 11 base + 9 codegen sequence rules | Exchange & Functional Scenarios — lifelines, messages | **Genuine, and §8.3 shows pumllint does it well** |
| Architecture views | none | OAB / SAB / LAB / PAB | Capella-side |
| Data flow | none (the activity pack is *control* flow) | SDFB / LDFB / PDFB | **Not a match — §8.4** |
| Rule categories | six dimensions | Integrity, design, completeness, traceability | **Two names shared, independently** |
| Rule profiles | profiles | validation profiles | Same idea, same word |
| Traceability | `trace`: requirement↔diagram matrix | inter-phase traceability, built into the metamodel | Capella's is structural; pumllint's is textual |
| Method conformance | none — and see N2 | Arcadia's whole purpose | Arcadia-side, emphatically |
| Level / gap report / ratchet | the scoring model | none | Unoccupied |

## 4. Boundaries

1. **Method vs. artefact.** Arcadia governs *which models must exist and
   how they relate across five perspectives*. pumllint asks whether one
   file says anything. Different questions, different objects.
2. **XML vs. text.** Capella's model is not a text notation, so there is
   nothing to lint even in principle without a conversion nobody ships.
3. **Licence.** EPL-2.0 against a categorical never-build (§1.4).
4. **Direction.** Not a producer (§2) — the one boundary that is a
   disappointment rather than a relief.
5. **Discovery.** `.capella` is outside `PUML_EXTENSIONS`, and the model
   XML carries no `@startuml` — both measured honest (§8.1).

## 5. Sense — five true things

**S1. The Exchange Scenario result is the first positive control the
series has produced.** Eleven evaluations established what pumllint does
*wrong* with foreign input — drops it, mis-types it, manufactures
content, or judges it in the wrong dialect. §8.3 is the first foreign
artefact that lands right: correct type, correct parse, the deep pack
applying for the reasons it was written, Level 4 and exit 0. That is
worth recording precisely, because a record made only of negative results
slowly stops describing the tool.

**S2. And it is unreachable, which is the honest other half.** Capella
users draw scenarios in Capella. §8.3's file had to be written by hand,
by me, in a notation Capella cannot emit. A fit that only exists when
someone abandons the tool the ecosystem is named after is not a fit with
the ecosystem.

**S3. The category convergence is real and independent.** Two of
Capella's four named validation categories are pumllint's dimension
names, arrived at with no contact between the projects (§1.3). After
bpmnlint, that is a second corroboration that the decomposition is a
natural one rather than a local invention.

**S4. Not being a producer is a finding, not an absence.** Two
consecutive evaluations turned on producer relationships. Checking and
finding none here is what stops "MBSE tools emit PlantUML" from
hardening into a generalization on two data points.

**S5. The third EPL collision is one condition, not a third
coincidence.** §1.4. Naming it as a standing structural exclusion is
cheaper than meeting it again in whatever Eclipse-shaped ecosystem comes
next.

## 6. Nonsense — five moves to refuse

**N1. A Capella or Arcadia reader, or an Arcadia rule pack. Refused on
the artefact.** There is no text notation to read; there is XML from a
graphical tool. A reader would be an XML importer for a format owned by
an EPL project, feeding rules for diagram types pumllint does not model.

**N2. Mapping pumllint's maturity levels onto Arcadia's five
perspectives. Refused, and this is the specific trap here.** Both are
five-step ladders and both get called "levels" in conversation:

| Arcadia perspective | pumllint level |
|---|---|
| Operational Analysis | 1 — Sketchy |
| System Analysis | 2 — Structured |
| Logical Architecture | 3 — Disciplined |
| Physical Architecture | 4 — Precise |
| Component Contracts | 5 — Method-complete |

The alignment is **entirely spurious**. Arcadia's ladder is *abstraction*
— every perspective is present in a finished model, and being "at"
Physical Architecture says nothing about quality. pumllint's is *grade* —
exactly one applies to a diagram at a time, and it says nothing about
which architectural layer the diagram describes. A model can sit at
Arcadia's Physical Architecture and score Sketchy, or be pure Operational
Analysis and score Precise. Any feature, document or slide that puts
these two columns side by side is asserting something false.

**N3. Building a Capella→PlantUML exporter in this repository. Refused,
and it is the move §8.3 most invites.** The fit works and cannot be
reached, so bridging it looks like the obvious next step. It is not:
writing the producer in order to create demand for your own consumer is
manufacturing the pipeline rather than finding it. If such an exporter
should exist, it is a Python4Capella script in a Capella user's
repository, written by someone who wants the output — not a feature of a
PlantUML linter. The demand bar exists for exactly this shape of
temptation.

**N4. Any Capella or Eclipse-platform dependency, product or `tools/`.
Refused on the never-build** (§1.4).

**N5. Reading the category convergence as an integration opportunity.
Refused.** That Capella and pumllint independently named "completeness"
and "traceability" is evidence the decomposition is natural. It is not
evidence the tools should meet, and the shared vocabulary would make a
bad integration easier to describe than to justify.

## 7. Fit — graded

### F1 — a Capella/Arcadia reader or rule pack. **No.** N1, N4.

### F2 — pumllint on hand-written Arcadia-shaped PlantUML. **Works. Reaches nobody.** §8.3, S2.

The honest grade is not "no" but "yes, for a population that may not
exist": someone documenting an Arcadia-method system in PlantUML rather
than in Capella. Nothing to build either way — it already works — so this
is an observation about what the tool is good at, not a candidate.

### F3 — a Capella→PlantUML bridge. **No, and specifically not here.** N3.

### F4 — Arcadia-method conformance checking. **No.** N2.

Arcadia conformance is about which models exist across five perspectives
and how they trace to each other. pumllint sees one file at a time and
has no concept of a perspective. This is Capella's job, it does it, and
the overlap is zero.

### Fit against declared constraints

| Declared constraint | Where the Capella fits land |
|---|---|
| **Zero runtime dependencies** | Passes trivially — nothing proposed. |
| **Licence posture** (no EPL anywhere) | **Binding for the third consecutive evaluation**, and §1.4 restates it as one standing condition rather than a third finding. |
| **Demand bar** | **The operative constraint for F3** — the exporter that would make F2 reachable has no demonstrated user, and building it would be self-manufactured demand. |
| **Claim language** | Untested here; nothing proposed would claim pumllint checks Capella models. |
| **Golden score contract** | Untouched. |

## 8. Gap — measured

### 8.1 The boundary is honest

```
$ python3 -m pumllint only/                  # a directory of .capella files
warning: no PlantUML files found in only (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint model.capella
warning: 1 file(s) contained no @startuml block and were not checked: model.capella
✔ No issues found.                                                    (exit 0)
```

Capella project XML wrapped in `@startuml` is `unknown`, 0 elements,
**Level 1 (Sketchy) 95.0** — consistent with the SysML note's XMI row,
and for the same reason: XML has no line-initial punctuation that reads
as an arrow.

### 8.2 The full measurement

| Sample | type | level | score | elements | exit |
|---|---|---|---|---|---|
| Capella project XML, wrapped | `unknown` | 1 | 95.00 | 0 | 0 |
| **Exchange Scenario** (sequence syntax) | **`sequence`** | **4** | **99.38** | 10 | **0** |
| SDFB — functions + functional exchanges | `sequence` | 4 | 89.22 | 8 | 1 |
| LAB — components + exchanges | `sequence` | 4 | 88.96 | 6 | 1 |
| control-flow flowchart (**not** an Arcadia shape) | `activity` | 4 | 99.31 | 9 | — |

### 8.3 The Exchange Scenario — the positive control

```
@startuml
actor Driver
participant Cockpit
participant Powertrain
…
Driver -> Cockpit : press accelerator
activate Cockpit
Cockpit -> Powertrain : throttle demand
…
Powertrain --> Cockpit : delivered torque
deactivate Powertrain
@enduml
```

→ `sequence`, 10 elements, **Level 4 (Precise) 99.38**, **exit 0**, two
cosmetic findings (GEN001 no title, GEN002 no name).

Everything worked for the right reason. Participants declared, so SEQ001
and SEQ002 are satisfied rather than dormant. Activations balanced, so
SEQ003 is quiet on evidence. Dashed arrows are genuine returns paired
with genuine calls, so SEQ009 — the rule that has fired falsely in five
previous evaluations — **is correct here**. Every message is labelled,
so SEQ005 and the DIM-AMB rules have nothing to say.

**This is the first artefact from a foreign ecosystem in twelve
evaluations that pumllint handles well**, and the reason is not luck: an
Arcadia Exchange Scenario *is* a sequence diagram — lifelines are
components and actors, messages are exchanges — so the pack that applies
is the pack that was designed for it.

The cost of stating it is §2. Capella cannot emit this file. It was
written by hand for this note.

### 8.4 The other three shapes fall through, and it is already-known behaviour

The LAB and SDFB both type `sequence` and both draw false SEQ009s:

```
lab.puml:6:  [SEQ009/minor] Return 'vehicle state' from 'Chassis' to 'Cockpit' pairs with no preceding call
sdfb.puml:7: [SEQ009/minor] Return 'torque request' from 'F2' to 'F3' pairs with no preceding call
```

In Arcadia a `-->` in either diagram is a **functional exchange**, a
directed dependency; `is_return_arrow` at `parser/sequence.py:472` reads
any `--` or `..` as a return convention.

**None of this is new, and the note should not pretend otherwise.** The
ArchiMate evaluation named the false SEQ009 explicitly; the C4, Mermaid
and UML evaluations each recorded the same mechanism. The standing
type-fallback class, already twice amended, covers it — no candidate, and
no amendment.

One coincidence is worth a line, stated carefully because it is easy to
overstate. The LAB lands on **the same composite as C4 sample C** —
Level 4, 6 elements, **88.96** — which that note recorded from an
unrelated notation. The *finding sets differ*: three false SEQ009s here,
two plus a SEQ006 there. So this is not a reproduction; it is two
different foreign notations arriving at an identical score through
different penalties, which says something about how coarse the composite
is at this end of the range and nothing about Arcadia.

The last row is a precision point rather than a result. A PlantUML
activity diagram — `start` / `if` / `stop` — types `activity` and scores
99.31, but **it is not an Arcadia rendering**: a DFB shows information
dependency between functions, not control flow with decisions. Recorded
so that "Arcadia has dataflow, pumllint has an activity pack" is not
mistaken for a mapping. It is not one.

### 8.5 What was not measured

No Capella was installed, so its validation output was never seen — the
category list, the absence of aggregate scoring and the add-on catalogue
are characterized from the project's own documentation. Python4Capella
was not run and its API not read (GitHub, outside scope), so "nobody has
written a PlantUML exporter" rests on the official catalogue plus search,
not on inspection. Functional Scenarios (lifelines = functions) were not
probed separately from Exchange Scenarios; they would likely behave the
same, and that is a guess, not a measurement.

## 9. SWOT

**Strengths (pumllint, internal)**

- §8.3: the deep pack does its job on a foreign artefact, with exit 0 and
  no false findings — the first such result in the series.
- The boundary held in every form tested.
- Zero dependencies, so the EPL condition is met by construction.

**Weaknesses (pumllint, internal)**

- §8.4: the LAB and SDFB produce *confidently worded wrong advice* about
  returns that do not exist in Arcadia. Known behaviour, twelfth
  notation, still the tool's weakest surface.
- The best result in this evaluation is reachable only by users who have
  stopped using the ecosystem's own tool.

**Opportunities (external)**

- Only F2, and it is a population whose existence is unverified.

**Threats (external)**

- None. Capella does not compete with pumllint, does not produce its
  artefact, and does not grade. The nearest thing to a threat is the
  positioning risk in N2 — that somebody inside this project draws the
  five-levels-to-five-perspectives table and believes it.

## 10. Decision, recorded candidates, triggers

**Decision: no Capella or Arcadia support of any kind, no Arcadia
method-conformance mode, no exporter built here, and no Eclipse-platform
dependency. Two observations recorded; nothing queued.**

**Never build:**

- A Capella/Arcadia reader or rule pack (N1).
- Any mapping of pumllint's maturity levels onto Arcadia's perspectives
  (N2) — the ladders are orthogonal and the table is false.
- **A Capella→PlantUML exporter in this repository** (N3) — building the
  producer to create demand for the consumer; if it should exist it
  belongs in a Capella user's repo.
- Any Capella or Eclipse-platform dependency, product or `tools/` (N4).
- An integration justified by the shared category vocabulary (N5).

**Recorded, not queued:**

1. **The Exchange Scenario as the series' positive control** (§8.3).
   Twelve evaluations of negative results, and one artefact class that
   lands right: correct type, correct parse, Level 4, exit 0, the
   eleven-rule pack applying as designed. Worth citing when the question
   is what pumllint is *for* rather than what it refuses — and worth
   citing with S2 attached, since the population that would benefit is
   unverified.
2. **The EPL/MBSE structural exclusion, stated once** (§1.4). Third
   consecutive collision, and one standing condition rather than three
   findings: the modelling-tool world is Eclipse-shaped, so a GPL project
   forbidding EPL is structurally outside it. A fourth evaluation should
   cite this, not rediscover it.

**Re-litigate on:**

- **Somebody publishing a Capella→PlantUML exporter with users** — the
  only trigger here a user can fire, and the one that would move F2 from
  unreachable to reachable without this project building anything. N3
  refuses building it; it does not refuse *benefiting* from it.
- Capella gaining an aggregate verdict — the standing streak trigger.
  Its category taxonomy is already closer to this project's than
  anything else found in twelve ecosystems, so it is a plausible source.
- **Not** on Arcadia adoption growing. Capella users use Capella; volume
  does not create a PlantUML artefact to lint.

## Related reading

- [The SysML ecosystem, evaluated](sysml-ecosystem-evaluation.md) — the
  immediate predecessor: EPL closing an ecosystem (§1.4 makes it a
  standing condition), the producer→consumer reframe (§2 records its
  absence here), and the XMI row §8.1 matches.
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) —
  sample C, whose Level 4 / 6 elements / 88.96 the LAB lands on from an
  unrelated notation and a different finding set (§8.4).
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the false SEQ009 and the unsafe `--` token, both re-observed here
  without amendment.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  bpmnlint convergence, of which §1.3's category overlap is the second
  and first-taxonomic instance.
- [ROADMAP.md](../ROADMAP.md) — the EPL never-build, the demand bar that
  decides N3, and the maturity model N2 refuses to align.
