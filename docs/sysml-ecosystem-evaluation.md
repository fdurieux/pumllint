# The SysML ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `59f4470` (v0.29.0). The
question as posed: investigate the SysML ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Eleventh in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, Structurizr DSL,
Ilograph, Graphviz/DOT, this) — and the first that was **already on the
books**: the UML evaluation named SysML v2 as a re-litigate trigger and
as the single entry in its SWOT threat column.*

**Verdict up front: still no — but for the first time in the series the
answer arrives by way of a trigger that has *fired*, and the reason it
fired is not the reason it was written. The UML note watched for "SysML
v2 / KerML acquiring a PlantUML-renderable textual form with users". It
already had one, and had had one for years: the OMG pilot implementation
ships an `org.omg.sysml.plantuml` component and renders models through
PlantUML in its Jupyter kernel. SysML v2 is therefore not a rival text
notation encroaching on the PlantUML niche — it is a **producer of the
artefact pumllint gates** — the classification the Structurizr note
coined, applied to a second ecosystem. The threat entry should be
rewritten as a producer entry, and the answer stays no.**

**The measurement is the sharpest of the eleven, and it splits three
ways.** SysML **v2** is the **first notation in the series that cannot
be misread at all** — and structurally, not by luck. SysML **v1** is the
first foreign notation that lands in a **fully correct parse**, where the
findings are right about the PlantUML text and the wrong dialect for the
model. And the **`trace` probe is the yield**, and it is not about SysML:

| Where `REQ-001` is written, same diagram | `trace` coverage |
|---|---|
| in a `<<requirement>>` block body — *where SysML puts it* | **0/1**, diagram reported **unlinked** |
| in a class name | 0/1 |
| in a stereotype `<<REQ-001>>` | 0/1 |
| on a relation label | 0/1 |
| in a note or title | **1/1** |

**A requirement diagram whose entire purpose is traceability reports
`0/2 covered — 2 uncovered, 1 unlinked diagram(s)`. And this is not a
defect: `trace.py:233-234` says message labels and other model content
"are deliberately not carriers — same as the rule", so that the rule and
the matrix cannot disagree about what counts as a reference. The
invariant is sound and should not be broken. What is new is that its
*cost* has now been measured, on the one diagram shape where it costs
the most.**

*Bounds, and they are wider here than usual. Every pumllint claim was
executed at `59f4470` with default config from a neutral working
directory (verified: GEN006/GEN007 stay dormant). **No SysML tool of any
kind was executed** — not Cameo, not SysON, not the pilot
implementation; all tool behaviour is characterized from vendor
documentation, package listings and release notes. Per this session's
repository scope **no GitHub repository was read**, which bites twice
here: the pilot implementation's PlantUML generator was not inspected,
so **the shape of the `.puml` it emits is unmeasured** — the single
biggest gap in this note — and the pilot's own licence could not be
resolved (§1.4). SysML v2 samples are reconstructed from published
syntax references, not from the OMG specification PDF. SysML v1 samples
are the *community* PlantUML rendering of bdd / ibd / requirement
diagrams; PlantUML has no SysML diagram type, so there is no canonical
form to test against.*

## 0. Why this ran, and what makes it different

Ten predecessors were first looks. This one is not. The UML evaluation
(2026-08-26) recorded SysML v2 twice: as **N4**, refusing to read UML's
age as an opportunity because "the successor energy went elsewhere"; and
in the SWOT, as the **only** entry under threats —

> **SysML v2 / KerML.** A textual modelling language *with* formal
> semantics, adopted by OMG in 2025, is the one development that speaks
> directly to the premise that text notations need an external semantic
> gate. It does not threaten the PlantUML niche, but it is the thing to
> watch.

and as a re-litigate trigger, in ROADMAP.md:1428-1433:

> **SysML v2 / KerML** acquiring a PlantUML-renderable textual form with
> users — OMG adopted SysML v2.0 + KerML 1.0 in July 2025 […] which is
> the one development that speaks directly to the premise that text
> notations need an external semantic gate (characterized; the pilot
> implementation is on GitHub, outside scope).

So this note has a specific job the others did not: **say whether the
trigger has fired.** It has, and §2 shows the wording pointed the wrong
way — which is worth more than a clean confirmation would have been,
because a trigger that fires in an unanticipated direction is the kind
that would otherwise be quietly mis-answered later.

## 1. The ecosystem

### 1.1 Two languages under one name

"SysML" in 2026 denotes two incompatible things, and conflating them
makes nonsense of every fit question.

**SysML v1** (current minor revision v1.7, June 2024) is a **UML
profile**: nine diagram types, seven reused or modified from UML plus
two new ones — the requirement diagram and the parametric diagram. Its
concrete syntax is UML's, its interchange format is XMI, and it has no
textual notation of its own.

**SysML v2** (final adoption 21 July 2025; the current specification is
OMG SysML v2.0 [Sep 2025], editorially updated March 2026 for ISO
submission) is **not a UML profile**. It is built on **KerML 1.0**, a
kernel modelling language with formal semantics, and it ships a
**textual notation with a published grammar** as a first-class concrete
syntax alongside the graphical one. The formal release is four
documents: the language specification, the v1→v2 transformation
specification, the API and services specification, and KerML.

There is no backward compatibility. The transformation specification
gives normative v1→v2 mapping rules, and tool support for it is
partial — migration coverage is characterized in the tooling literature
as roughly a fifth of the metamodel. SysML v1.7 is not deprecated and no
retirement date was found. **Both languages are live, and will be for
years.**

### 1.2 The textual notation, in the detail that matters here

Relationships in SysML v2 are spelled with **keywords**, not symbols:

```
part def Vehicle {
    attribute mass : Real;
    part engine : Engine;
}
part def Engine :> PowerSource;

connect tank.fuelOut to engine.fuelIn;
connect tank with engine;
flow lightOut.brightness to display.input;
succession flow command from controller.cmd to actuator.cmdIn;
succession first then second;
satisfy MaxMass by myCar;
```

Specialization is `:>`, redefinition `:>>`, namespacing `::`, typing `:`.
Declarations terminate with `;` or with a `{ … }` body. The one
arrow-shaped token in the language is `->`, and it is an **expression**
operator (method call on a sequence, `parts->size()`), not a
relationship. §8.2 measures what that adds up to.

### 1.3 The tooling

| Tool | Kind | Position |
|---|---|---|
| **Pilot implementation** (OMG Systems Modeling) | reference implementation, Eclipse + Jupyter kernel | **renders through PlantUML** (`org.omg.sysml.plantuml`; `%viz` in the notebook kernel) |
| **Eclipse SysON** (Obeo + CEA) | web-based graphical SysML v2 editor, Sirius Web | "the core SysMLv2 editing capability for Papyrus", integrates with Capella |
| **CATIA Magic / Cameo** (Dassault) | commercial MBSE suite | validation against SysML, KerML and Dassault predefined suites |
| **Papyrus**, **Capella** | Eclipse modelling platforms | v1 tooling, and SysON's integration targets |
| **SAIC Digital Engineering Validation Tool** | **free** rule set for MagicDraw / Cameo | **251 validation rules, language *and* style** |

### 1.4 The licence, and why it is a bigger question than last time

The Graphviz evaluation, one day earlier, was the first in the series
where the EPL never-build — *"EPL dependencies anywhere in the repo (one
GPL sdist — product and lab alike)"* — was decisive, and it applied to a
single library. Here it applies to **an ecosystem**.

**Eclipse SysON is EPL-2.0**, verified from its own Eclipse project
proposal, and by that proposal's account it is the core open-source
SysML v2 editing capability, feeding Papyrus and integrating with
Capella — both themselves Eclipse projects, and so EPL. The open SysML
v2 tool ecosystem is, in substance, an Eclipse ecosystem.

**The pilot implementation's own licence could not be resolved.**
Sources disagree: some report it still under LGPL with `LICENSE` and
`LICENSE-GPL` files; others report a relicensing to EPL, and the
adjacent API-Services and Release repositories are reported EPL-2.0.
Settling it would mean reading the repository, which is outside this
session's scope. **Recorded as unresolved**, and it does not need
resolving: SysON alone settles the ecosystem point, and nothing here
proposes depending on any of it.

## 2. The trigger, answered

The trigger asked for "a PlantUML-renderable textual form **with
users**". Taking the three clauses in turn:

**Textual form: yes, and normative.** The v2 textual notation is part of
the adopted specification, not a convenience.

**PlantUML-renderable: yes, and it predates the trigger.** The pilot
implementation's visualization path *is* PlantUML — an
`org.omg.sysml.plantuml` component, surfaced as `%viz` in the Jupyter
kernel. It is characterized in the literature as a *highly adapted*
PlantUML whose visualization is limited and not entirely conformant to
the specification, i.e. a fork rather than stock PlantUML.

**With users: partially, and growing.** SysON is in an Early Adopter
programme aimed at operational deployment in 2026, with named industrial
participants; Cameo ships a SysML v2 solution; v1→v2 migration is
underway and incomplete.

**So the trigger has fired — and the sentence it was written in points
the wrong way.** It was written as a threat: a text notation *with*
formal semantics might make an external semantic gate for text notations
look unnecessary. What the evidence shows is the opposite relationship.
SysML v2 does not compete with PlantUML; **it emits PlantUML.** The
correct classification is the one the Structurizr note introduced — a
**producer of the artefact pumllint gates**, alongside `structurizr-cli
export` and the C4 exporters that note named. No ordinal is claimed: the
Structurizr entry counted producers loosely, and after the Graphviz
note's bookkeeping correction this series does not add fragile counts.

That reclassification does not change the answer. It changes which
question is live, and §8.4 records the measurement that would answer it.

## 3. Overlap

| Concern | pumllint | SysML | Reading |
|---|---|---|---|
| Diagram typing | five parsed types | v1: nine types (7 UML-derived + requirement + parametric); v2: views/viewpoints over one model | v1 bdd ≈ class diagram — **the only real overlap in the series** |
| Class/block structure | CLS pack, 6 rules | v1 bdd blocks are stereotyped UML classes | **Applies, and §8.3 is about whether it should** |
| Requirements | `trace`: requirement↔diagram matrix, three directions | v1 requirement diagram; v2 `requirement def` / `satisfy` / `verify` / `derive` / `trace` | **Conceptually the closest fit anywhere in eleven — and §8.4 measures it missing** |
| Sequence semantics | 11 base + 9 codegen rules | v1 sequence diagram is UML's | Same as the UML note: real, and already covered there |
| Naming conventions | GEN004, CLS001, ACT005 | Cameo and SAIC style rules | **Occupied, by 251 rules** |
| Parametrics / constraints | none | v1 parametric diagram, v2 `constraint`, units, ISQ | Wholly SysML-side, and rightly |
| Formal semantics | none, by design | KerML | Wholly SysML-side |
| Level / gap report / ratchet | the scoring model | none found | **Unoccupied — eleventh ecosystem, no grader** |

Two rows are unlike anything in the previous ten. The **bdd row** is a
genuine overlap rather than a coincidence of syntax: a SysML v1 bdd
really *is* a UML class diagram, because SysML v1 really *is* a UML
profile. The **requirements row** is a genuine overlap of *purpose*:
`trace` and the SysML requirement diagram exist to answer the same
question. Both are measured in §8.

## 4. Boundaries

1. **Profile vs. text.** pumllint reads PlantUML source. SysML v1 lives
   in XMI and SysML v2 in its own grammar; the only place they meet is
   a `.puml` file that somebody wrote or generated.
2. **Two languages, one name.** Any SysML claim would have to say which
   SysML, and the answer would differ per diagram type. That alone
   defeats a "SysML mode".
3. **Licence.** The open v2 tool ecosystem is Eclipse, therefore EPL,
   against a categorical never-build (§1.4).
4. **Discovery.** `.sysml` is outside `PUML_EXTENSIONS`, and a `.sysml`
   file passed directly has no `@startuml` block — both measured honest
   (§8.1).
5. **Direction.** SysML v2 tooling *writes* PlantUML. pumllint reads it.
   The relationship is producer→consumer, not peer (§2).

## 5. Sense — five true things

**S1. The trigger fired, and firing it early was worth more than being
right about it.** The UML note put SysML v2 in the threat column and
told a later reader to watch it. A reader who checked found a producer,
not a threat. That is the mechanism working: the record named the thing
to check, and checking it corrected the record.

**S2. SysML v2 is the first notation in eleven that cannot be
misread — and structurally.** DOT's honesty came from optional
semicolons; SysML v2's comes from having **no relational symbol at
all**. `connect`, `flow`, `succession`, `satisfy`, `:>`: keywords, every
one. There is nothing for the arrow pattern to match, and §8.2 confirms
even a `->` expression produces no message. This is the one honest
result in the series that will still be honest after somebody edits the
file.

**S3. The bdd result is a new category, and it is uncomfortable in a
useful way.** Every earlier foreign notation either fell through or was
manufactured into content. This one **parses correctly**, and the
findings are **right about the PlantUML and wrong about the SysML**
(§8.3). "Wrong dialect" is a failure mode the series had not seen.

**S4. The `trace` measurement is the yield, and it generalizes past
SysML.** §8.4's matrix is about pumllint, not about SysML — any user
who writes a requirement ID as a class member, a stereotype or a
relation label gets the same confident zero. The behaviour is
deliberate, documented, and defensible; what did not exist until now is
a measurement of what it costs.

**S5. Eleventh ecosystem, no grader — and this is the strongest entry
in the streak.** SAIC's Digital Engineering Validation Tool is **free**,
carries **251 rules covering both language and style**, and reports with
severities (fatal / error / warning / debug / info); Cameo adds SysML,
KerML and vendor validation suites. That is the closest analogue to this
project's catalogue found anywhere in eleven ecosystems — a free,
large, style-inclusive, severity-graded rule set. It reports violations.
It does not produce a score, a level, a grade, or an aggregate verdict.
The streak has never had a better test.

## 6. Nonsense — six moves to refuse

**N1. A SysML v2 reader or rule pack. Refused on the artefact and the
direction.** SysML v2 is not a diagram notation pumllint could gate; it
is a modelling language whose tooling *emits* the notation pumllint
gates. Building a reader would be building a second product pointed
upstream of the one that exists.

**N2. A SysML v1 "profile mode" — `<<block>>`/`<<requirement>>`-aware
rules. Refused, and this is the tempting one.** §8.3 shows the class
pack already fires on a bdd, so the distance to "SysML support" looks
like a stereotype table. It is not: it is a claim that pumllint checks
SysML models, which it would not be doing — it would be checking one
community rendering of one of nine diagram types, in a language whose
own tooling ships 251 rules. The claim-language discipline the UML note
verified across the repository's whole history rules this out on its
own.

**N3. Relaxing CLS002 when a `<<block>>` stereotype is present.
Refused — this is N2 wearing a smaller hat.** CLS002 is *right* about
the PlantUML class diagram in §8.3. A stereotype-conditional exemption
would make pumllint a partial SysML checker through the back door, and
would make the rule's behaviour depend on a vocabulary the tool does not
otherwise model.

**N4. Any Eclipse/EPL SysML tooling, in the product *or* in `tools/`.
Refused on the never-build.** §1.4. Second application in two days, and
the first where it closes an ecosystem rather than a library.

**N5. Breaking the `trace`/GEN007 carrier invariant to catch
SysML-style IDs. Refused.** The invariant — the rule and the matrix
cannot disagree about what counts as a reference — is stated in the
source and is worth more than the coverage it costs. Anything that
widens the carriers must widen **both**, together, and that is a
different and larger change than §8.4's finding justifies on its own.

**N6. Reading "SysML v2 has formal semantics" as an argument against
this project. Refused, and the UML note half-invited it.** KerML gives
SysML v2 semantics inside SysML v2. It says nothing about whether a
PlantUML file in a repository means anything, which is the question this
tool asks. The two do not meet, and the threat framing should go.

## 7. Fit — graded

### F1 — a SysML v2 reader or rule pack. **No.** N1, N4.

The artefact argument and the direction argument are independent, and
the licence closes the tooling route besides.

### F2 — a SysML v1 profile mode. **No.** N2, N3.

The one fit in eleven evaluations that *would* partly work mechanically,
and is refused on what it would claim rather than on what it could do.

### F3 — SysML v2 as a producer, like Structurizr. **The live question, and unmeasured.** §8.5.

A producer in the Structurizr sense. Unlike Structurizr — whose three export
shapes are documented and were measured — the pilot's generator was not
inspected, so what its PlantUML looks like is unknown. Recorded as the
one thing worth measuring if this is ever picked up.

### F4 — the `trace` carrier cost. **A measurement, and a documentation candidate.** §8.4, N5.

Not a fix proposal. The invariant stands; what is recorded is its price
and the fact that any future widening moves GEN007 and `trace` together.

### Fit against declared constraints

| Declared constraint | Where the SysML fits land |
|---|---|
| **Zero runtime dependencies** | Passes trivially — nothing proposed. |
| **Licence posture** (no EPL anywhere, product and lab alike) | **Binding, for the second consecutive evaluation** — and here it closes an ecosystem, not a library. F1, N4. |
| **Deterministic product path, no LLM** | Not reached. |
| **Claim language** ("PlantUML", never "UML"/"SysML") | **The operative constraint for F2.** N2. |
| **Golden score contract** | Untouched — nothing proposed changes scoring. |

## 8. Gap — measured

### 8.1 The boundary is honest, in two forms

```
$ python3 -m pumllint onlysysml/          # a directory of .sysml files
warning: no PlantUML files found in onlysysml (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint model.sysml
warning: 1 file(s) contained no @startuml block and were not checked: model.sysml
✔ No issues found.                                                    (exit 0)
```

### 8.2 SysML v2 wrapped in `@startuml` — honest, and structurally so

| Sample | type | level | score | elements |
|---|---|---|---|---|
| idiomatic v2 (parts, ports, requirement, `:>`) | `unknown` | 1 | 95.00 | 0 |
| v2 with `connect` / `flow` / `succession` and a `parts->size()` expression | `unknown` | 1 | 95.00 | 0 |
| SysML v1 XMI interchange | `unknown` | 1 | 95.00 | 0 |

Nothing parses, cap C6 holds, Level 1 (Sketchy). The reason is worth
stating precisely because it is the first of its kind: **SysML v2 has no
relational symbol for the arrow pattern to match.** `connect a to b;`,
`flow x to y;`, `succession a then b;`, `satisfy R by p;`, `E :> P;` —
all keyword-spelled. The `->` that exists is an expression operator and
did not produce a message even when present.

Contrast the two predecessors. D2's `a -> b: label` collided head-on and
reached Level 4 (99.17). DOT was saved by semicolons that DOT does not
require — real protection, incidental cause. SysML v2's protection is
**in the grammar's choice of keywords over symbols**, which no edit to a
conforming file can remove.

The XMI row adds a small second data point to the Ilograph finding: XML
is the second data format tested and it degrades the *safe* way, because
unlike YAML it has no line-initial punctuation that reads as an arrow.
The Ilograph note's "manufactures content" failure is a property of
YAML's list dash, not of data formats generally.

### 8.3 SysML v1 bdd — a correct parse, and the wrong dialect

```
@startuml
class Vehicle <<block>> { +mass : Real … }
class Engine  <<block>> { +power : Real … }
Vehicle *-- "1" Engine
Vehicle *-- "4" Wheel
Engine --> FuelTank : draws fuel
@enduml
```

→ typed **`class`**, 8 elements, **Level 3, 69.22**, exit 1, with
CLS002 firing four times:

```
bdd.puml:14: [CLS002/major] Composition between 'Vehicle' and 'Engine' has no
             multiplicity on 'Vehicle' — write e.g. 'Order "1..*" -- "1" Customer'
```

**This is the first foreign notation in the series to land in a fully
correct parse.** It is not a fallback and not a coincidence: SysML v1 is
a UML profile, a bdd *is* a class diagram, and pumllint read it as one.

And the findings are the wrong dialect. CLS002's docstring is explicit —
*"Associations (and aggregations/compositions) declare both
multiplicities"* — and that is a defensible UML position. But SysML
**specifies defaults for both ends** of a composite association: 0..1 on
the composite end, 1 on the part end. Writing `Vehicle *-- "1" Engine`
and stopping is not an omission in SysML; it is reliance on the
specification. CLS002 asks the modeller to write down what the language
already defines.

The honest reading matters more than the finding. CLS002 is **right
about the PlantUML source text**, which is what pumllint claims to
check. It is **misleading about the SysML model that text depicts**. So
this is not a defect and not a rule change (N3) — it is a positioning
hazard, and the third instance of the pattern the ArchiMate and
Structurizr notes recorded: findings that are *true and unownable* by
the person receiving them. Here the twist is that the truth is in a
different language from the reader's.

The internal block diagram is a separate matter and not a new one:
`component` plus a bare `--` types `sequence`, recovers exactly 3
elements — the `l4_min_elements = 3` floor at `scoring.py:88` — and
scores **Level 4 (Precise) 91.25**. That is the standing type-fallback
class, in the alias-style-component form the **UML note already
recorded**. A tenth notation exhibiting it, not a tenth mechanism, and
no new candidate.

### 8.4 `trace` against a requirement diagram — the yield

Requirement IDs `REQ-001` and `REQ-002`, one inventory, one diagram,
varying only *where* the ID is written:

| Location | coverage | verdict printed |
|---|---|---|
| `id = "REQ-001"` inside a `<<requirement>>` block — **the SysML way** | **0/2** | `2 uncovered, 1 unlinked diagram(s)` |
| class name (`class REQ-001`) | 0/1 | uncovered |
| stereotype (`<<REQ-001>>`) | 0/1 | uncovered |
| relation label (`: satisfies REQ-001`) | 0/1 | uncovered |
| note or title | **1/1** | covered |

The failure is confident. It does not decline to judge; it reports the
requirements uncovered and names the diagram as unlinked — on a diagram
that exists to record exactly that link.

**And it is deliberate.** `pumllint/trace.py:233-234`:

> Exactly GEN007's haystacks: the prose directives
> (title/header/footer/caption/notes) plus the `@startuml` name. Message
> labels and other model content are deliberately not carriers — same as
> the rule.

with the reason given in the module docstring: *"so the rule and the
matrix cannot disagree about what counts as a reference."* That is a
real invariant and a good one.

So the finding is not "trace is broken". It is: **the carrier invariant
has a price, the price had never been measured, and the diagram shape
where it is highest is the one whose whole purpose is traceability.**
Anyone who later proposes widening the carriers now has the number, and
the constraint (N5) that GEN007 must widen with it.

Note also what this is *not* about. Nothing in the matrix is
SysML-specific — a plain class diagram with `+REQ-001 traceability` as a
member behaves identically. SysML surfaced it; it belongs to pumllint.

### 8.5 What was not measured

**The generated `.puml`.** The pilot implementation's PlantUML component
was not inspected and no model was rendered through it, so what its
output looks like — stock PlantUML or fork-specific syntax, which
diagram types, whether names survive as identifiers — is unknown. Given
§2's reclassification of SysML v2 as a producer, **this is the one
measurement that would make F3 answerable**, and its absence is the
largest hole in this note.

Also unmeasured: SAIC's rule set (not downloaded; the count, the
severities and the absence of scoring are from its product page), any
Cameo or SysON behaviour, the v1→v2 transformation output, and the
parametric diagram, which has no plausible PlantUML rendering and was
not attempted.

## 9. SWOT

**Strengths (pumllint, internal)**

- The boundary held in every form tested — `.sysml` undiscovered, XMI
  and both v2 samples honest at Level 1, `@startuml` scope guard
  correct.
- `trace` exists at all. No SysML tool found produces a coverage matrix
  in three directions; the gap in §8.4 is about *carriers*, not about
  the capability.
- Zero dependencies verified, so the EPL constraint is satisfied by
  construction rather than by vigilance.

**Weaknesses (pumllint, internal)**

- §8.4: a confidently-stated `0/2` on the diagram shape that exists to
  record traceability.
- §8.3: a correct parse producing four major findings that are right in
  one language and misleading in another.
- The ibd falls through to Level 4 (Precise), the standing type-fallback
  class, now observed in an eleventh notation.

**Opportunities (external, and each is refused above)**

- The bdd overlap is real and mechanical (F2 — refused on claim
  language, N2).
- SysML v2 as a producer is a genuine consumer relationship (F3 —
  unmeasured, recorded).

**Threats (external)**

- **None that the UML note's framing predicted.** Its threat entry
  should be replaced by a producer entry (§2). The residual threat is
  narrower and different in kind: if SysML v2's PlantUML output becomes
  a common repository artefact, pumllint will be scoring generated files
  whose findings belong upstream — the Structurizr problem, at whatever
  scale MBSE adoption reaches.

## 10. Decision, recorded candidates, triggers

**Decision: no SysML support of any kind — no v2 reader, no v1 profile
mode, no stereotype-aware rule behaviour, and no Eclipse/EPL SysML
tooling anywhere in the repository. The UML note's threat entry is
reclassified. Two candidates recorded; nothing queued.**

**Never build:**

- A SysML v2 reader or rule pack (N1) — wrong artefact, and pointed
  upstream of the one this tool gates.
- A SysML v1 profile mode or `<<block>>`/`<<requirement>>`-aware rules
  (N2) — it would claim pumllint checks SysML models, which the
  claim-language discipline forbids and which would be false besides.
- A stereotype-conditional CLS002 exemption (N3) — N2 in miniature; the
  rule is correct about the artefact it examines.
- Any Eclipse/EPL SysML tooling, product *or* `tools/` (N4) — SysON is
  EPL-2.0 and the never-build is categorical. Second consecutive
  evaluation where the licence binds, and the first where it closes an
  ecosystem rather than a library.
- Widening `trace`'s carriers without widening GEN007's (N5) — the
  invariant that rule and matrix agree is worth more than the coverage.

**Recorded, not queued:**

1. **The `trace` carrier cost, measured** (§8.4, F4). Not a fix: the
   invariant is deliberate and sound. What is recorded is the number,
   the confident-false-negative shape of the output, the fact that it is
   a pumllint property rather than a SysML one, and the constraint that
   any future widening moves GEN007 and `trace` together. A
   documentation note — "put the ID in a note or the title, and why" —
   is the small end of it, and is not queued either.
2. **The right-rule-wrong-dialect observation** (§8.3). Third instance
   of the true-and-unownable pattern (ArchiMate, Structurizr, this), and
   the first where the finding is true in a *different language* from
   the reader's rather than at a different layer. Stated once so a
   fourth does not re-derive it.

**Corrections to the record:**

- The UML evaluation's SWOT threat entry and its re-litigate trigger
  treat SysML v2 as a possible *competitor* to the PlantUML niche. §2
  shows the relationship is **producer→consumer**: the OMG pilot
  implementation renders through PlantUML. The trigger is discharged;
  the classification is wrong, not the conclusion it supported.

**Re-litigate on:**

- **An adopter running pumllint over PlantUML generated by the pilot
  implementation** — the concrete form of F3, the one an adopter can
  actually fire, and the thing §8.5 could not measure.
- SysML v2 tooling producing a graded verdict — the standing streak
  trigger, and the strongest candidate to end it, since SAIC's 251
  rules are already most of the way to a catalogue.
- The pilot implementation's licence resolving to EPL — would confirm
  §1.4 and change nothing, since SysON already settles the ecosystem
  point. Recorded so the open question is not mistaken for an opening.
- **Not** on SysML v1 adoption of PlantUML rendering growing: F2 is
  refused on what it would claim, and volume does not move that.

## Related reading

- [The UML ecosystem, evaluated](uml-ecosystem-evaluation.md) — the note
  this one discharges a trigger from, and whose threat entry §2
  reclassifies.
- [The Structurizr DSL ecosystem, re-examined](structurizr-dsl-ecosystem-evaluation.md)
  — the producer→consumer reframe this note is the third instance of,
  and the generated-artefact principle §8.3 extends.
- [The Graphviz / DOT ecosystem, evaluated](graphviz-dot-ecosystem-evaluation.md)
  — the first licence-decisive evaluation, one day earlier; §1.4 is the
  same never-build applied to an ecosystem instead of a library, and
  §8.2 contrasts DOT's incidental honesty with SysML v2's structural
  honesty.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md)
  — the YAML "manufactures content" finding that §8.2's XMI row bounds.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — candidate 1 (the type-fallback class), which §8.3's ibd exhibits
  without amending.
- [ROADMAP.md](../ROADMAP.md) — the EPL never-build, Arc G (`trace`),
  and the claim-language discipline that decides F2.
