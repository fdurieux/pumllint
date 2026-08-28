# The FEAF / Gartner EA ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `ad30b03` (v0.30.0). The
question as posed: investigate the FEAF/Gartner EA ecosystem, then assess
the boundaries, overlap, fit, gap, sense and nonsense of the different
fits against pumllint's roadmap and ecosystem. Eighteenth in a series,
and the first whose two halves are **opposites** — one public-domain and
artifact-heavy, one proprietary and artifact-sceptical.*

**Verdict up front: no as a build, and the two halves reach it by
opposite routes. The FEAF half is the cleanest confirmation the series
has produced. The Gartner half is the first genuine market headwind it
has found in eighteen notes, and this note does not argue it away.**

**FEAF — three of three, and the mapping is confirmed rather than
inferred.** FEAF v2 (OMB, January 2013) names ~50 artifacts across six
sub-architecture domains, with **one required "core" artifact per
domain**, and — the useful part — publishes a **"Other Framework Names"**
column mapping each to its DoDAF equivalent. Three of them are pumllint's
packs by description, and FEAF says which DoDAF models they are:

| FEAF artifact | FEAF's own DoDAF mapping | pumllint | level | score | findings |
|---|---|---|---|---|---|
| **D-8 Event Sequence Diagram** | *"DoDAF SV/SvcV-10c"* | `sequence` | 4 | **100.00** | **none**, exit 0 |
| **D-7 State-Transition Diagram** | *"DoDAF SV/SvcV-10b"* | `state` | 4 | **100.00** | **none** |
| **D-1 Logical Data Model (core)** | — | `class` | 4 | **100.00** | **none** |

The DoDAF evaluation, three turns earlier, mapped SvcV-10c to the
`sequence` pack **by judgement**. FEAF publishes that equivalence itself.
So the chain *FEAF D-8 → DoDAF SvcV-10c → pumllint `sequence`* has a
first-party link where the series previously had only inference — the
first time a framework has confirmed this series' own cross-framework
mapping from its own text. §5.1.

**Gartner — the first market headwind in eighteen evaluations, stated
without softening.** Gartner is not a framework, standard, notation or
tool; it is a commercial advisory practice, and its published position is
explicitly hostile to the thing the previous seventeen notes have been
circling. Via research VP Brian Burke: **"Focusing on a standard EA
framework doesn't work"**; EA practitioners historically **"focused on
deliverables that were useful to enterprise architects but not valuable
to senior management and/or did not respond to a specific business or IT
need"**; and **"stakeholders only value actionable and measurable
deliverables"**.

**That is an argument that documentation quality was never the
bottleneck — relevance was.** It cuts two ways and this note resolves
neither: it lands squarely on the framework-driven EA documentation that
seventeen notes have refused to serve, so pumllint's refusals have been
tracking Gartner's argument without knowing it; **and** it applies to
pumllint, because a quality score on diagrams is worth something only if
the diagrams are. That is the same open question 42030's abstention and
TOGAF's aggregate-elsewhere left, and Gartner states it more sharply than
either. §5.4.

*Bounds, and the pair is instructive. **FEAF was read directly** — a US
Government work, 434 pages, and every FEAF quotation here is extracted
from the OMB PDF. **Gartner was not read**: its research is
subscription-only, so every Gartner quotation is from its own press
releases and secondary trade coverage, not from the research notes
themselves. Sixth and seventh access data points, in one evaluation:
**public domain → read; commercial subscription → unread.** The three
probe samples are mine and were written well-formed *and named*, which is
why they score 100.00 rather than DoDAF's 99.88 — §8.4 is explicit that
this measures the ceiling. Every pumllint claim was executed at
`ad30b03` with default config from a neutral working directory. Per
session scope no GitHub repository was read.*

## 0. Why this ran

No prior record names FEAF or Gartner. The pairing is the user's, and it
turns out to be a good one: the two halves disagree with each other about
whether architecture documentation is worth producing at all, which makes
the note more useful than either half alone.

## 1. FEAF

### 1.1 Structure

**FEAF v2**, published by OMB on **29 January 2013**, sits on the
**Consolidated Reference Model** — six reference models (Performance,
Business, Data, Application, Infrastructure, Security) — and the
**Collaborative Planning Methodology**.

Its artifacts are organized by **six sub-architecture domains**, named in
the document as: **Strategic, Business Services, Data and Information,
Enabling Applications, Host Infrastructure, Security.** In its own words:

> These six sub-architecture domains delineate the types of analysis and
> modeling that are necessary to meet stakeholder requirements. Based on
> EA best practices, the Common Approach to Federal EA lists **one
> required core documentation artifact for each of the six
> sub-architecture views**.

### 1.2 The artifact catalogue

~50 artifacts, coded by domain: **S-1…S-5** (Strategy), **B-1…B-6**
(Business), **D-1…D-10** (Data), **A-1…A-11** (Applications),
**I-1…I-12** (Infrastructure), **SP-1…SP-6** (Security). Only six carry
"(core)".

The catalogue's third column is *"Other Framework Names"*, and it is what
makes FEAF worth an evaluation of its own rather than a footnote to
DoDAF. Verbatim examples:

- **S-1 Concept Overview Diagram (core)** — *"The high-level
  graphical/textual description of the operational concept"* —
  **"DoDAF OV-1 (Operational Concept)"**
- **D-7 State-Transition Diagram** — *"The states systems transition to
  in response to events"* — **"DoDAF SV/SvcV-10b"**
- **D-8 Event Sequence Diagram** — *"A sequence of triggering events
  associated with resource flows and systems"* — **"DoDAF SV/SvcV-10c"**
- **D-4 Data Flow Diagram** — *"The functions (activities) performed by
  systems or services, their hierarchical structure, and their resource
  flows"* — **"DoDAF SV/SvcV"**

### 1.3 Notation: named as examples, not mandated

FEAF's position sits between DoDAF's and NAF's:

> Business Process Modeling and Notation (BPMN) and the Unified Modeling
> Language (UML) are examples of **"open" industry standard notational
> formats** that support model-based systems engineering.

Examples, not requirements. DoDAF said *any* notation; NAF constrained
the *metamodel*; **FEAF names two open standards illustratively and
mandates neither**. A PlantUML sequence diagram is not excluded, and is
not endorsed either — it is simply not the question FEAF is answering.

## 2. Gartner

Gartner is the first subject in eighteen evaluations that is **not a
framework, standard, notation, method or tool**. It is a research and
advisory business. Its "EA framework" is a practice model sold through
subscription, and its most-cited public position is a critique rather
than a structure.

There is therefore **nothing to lint, nothing to conform to, and no
artifact catalogue** — but unlike Zachman (an ontology with nothing to
lint) or ISO 42010 (a standard with nothing at pumllint's altitude), the
Gartner half is not a boundary question at all. It is a **market
question**, and §5.4 treats it as one.

## 3. Overlap

| Concern | pumllint | FEAF | Gartner |
|---|---|---|---|
| Event sequences | `sequence` pack | **D-8**, mapped to DoDAF SvcV-10c | — |
| State machines | `state` pack | **D-7**, mapped to SvcV-10b | — |
| Data structure | `class` pack | **D-1 (core)**, D-5 | — |
| Use cases | `usecase` pack | **B-5 Use Case** | — |
| Notation | PlantUML | UML/BPMN named as examples | — |
| Artifact prescription | none | ~50, six required | **argues against** |
| Grading | levels + composite | services maturity matrix | Magic Quadrant, Hype Cycle |
| Object graded | **a description** | a business service | a vendor |

The last row is the note's contribution to a running thread (§5.3).

## 4. Boundaries

1. **FEAF prescribes artifacts, not notation** (§1.3) — the same boundary
   as TOGAF and DoDAF, in a third position on the same axis.
2. **Gartner prescribes nothing** — it advises. There is no boundary to
   draw, only an argument to answer (§5.4).
3. **Access**: public domain versus subscription, in one note (§5.5).

## 5. Sense — five true things

### 5.1 FEAF confirms a mapping this series had only inferred

The DoDAF note assigned SvcV-10c to the `sequence` pack and SvcV-10b to
`state` on the strength of what those models are *for*. It said so, and
flagged the classification as its own judgement.

**FEAF publishes the same equivalences in a normative table.** D-8 *is*
DoDAF SvcV-10c by FEAF's own account; D-7 *is* SvcV-10b. So one link in
the chain that reaches pumllint is now first-party rather than inferred,
and the artifact-mapping method the TOGAF, DoDAF and NAF notes used has
its first external corroboration.

That does not make the pumllint end of the chain first-party — mapping
SvcV-10c to a PlantUML sequence diagram is still this series' judgement.
It makes the framework-to-framework end sound.

### 5.2 Three of three, and the note says why that is less impressive than it looks

§8.3: D-8, D-7 and D-1 all score **100.00 with no findings at all**. That
is the cleanest sweep in eighteen evaluations, and it is inflated by a
choice: **the samples carry `@startuml <name>` and a `title`**, so GEN001
and GEN002 have nothing to say, where DoDAF's samples did not and scored
99.75–99.92.

Naming them is defensible — FEAF artifacts *are* named, coded deliverables
— but the comparison to DoDAF's numbers is not like-for-like, and reading
"FEAF scores better than DoDAF" out of it would be wrong. What the three
100.00s actually show is that a well-formed, named PlantUML rendering of
three FEAF artifact types produces nothing for pumllint to complain about,
which is what should happen.

### 5.3 Nobody grades a description, and the list of what *is* graded now has four entries

In the corrected form the TOGAF note established. This evaluation adds
two more objects to the tally of things the field *does* grade:

| Source | Grades | Object |
|---|---|---|
| TOGAF ACMM | weighted mean, six levels | an **organization's capability** |
| TOGAF Compliance | six ordinal levels | an **implementation vs a specification** |
| **FEAF** | business services maturity matrix, "level 0" baseline | a **business service** |
| **Gartner** | Magic Quadrant, Hype Cycle | a **vendor / a technology** |
| ISO 42030 | *declines to define an aggregate* | (architecture evaluation) |

**Four different objects graded, none of them a description.** The
pattern the TOGAF note identified holds and strengthens: the field
aggregates enthusiastically, and consistently over something other than
the artefact.

### 5.4 Gartner is the first market headwind in eighteen notes, and it is not answered here

Seventeen previous evaluations closed their SWOT threats column with
"none", or with an internal positioning risk. This one has an external
argument, and it is a serious one.

Gartner's public position — *"Focusing on a standard EA framework doesn't
work"*; deliverables that were *"useful to enterprise architects but not
valuable to senior management"*; *"stakeholders only value actionable and
measurable deliverables"* — is a claim that **the failure mode of
architecture documentation is irrelevance, not incoherence.** pumllint
measures incoherence.

Two readings, and this note takes neither:

- **The critique exempts pumllint.** Gartner is describing
  framework-driven EA deliverables produced for their own sake — exactly
  what seventeen notes have refused to build for. pumllint gates diagrams
  that developers already keep in a repository, tied to codegen and
  requirement traceability; it is a CI check, not an EA programme. On
  this reading pumllint has been tracking Gartner's argument by
  instinct.
- **The critique includes pumllint.** A quality score on a diagram is
  worth something only if the diagram is worth having. If the diagrams in
  a repository are not actionable, making them *coherent* raises no
  stakeholder's estimate of them, and a maturity level is precisely the
  kind of architect-facing metric Burke is describing.

The first reading is comfortable and partly true; the second is the one
worth keeping in the record, because it is the same question ISO 42030's
abstention and TOGAF's aggregate-elsewhere raised, now stated by the
industry's most-cited advisor in plain commercial terms. **The series has
found no answer to it in eighteen evaluations, and should stop expecting
one to arrive from an ecosystem.**

### 5.5 Access, sixth and seventh, and the pair is the lesson

**FEAF**: US Government work, published openly, **434 pages read
directly** — every quotation above is extracted from the OMB PDF.
**Gartner**: subscription research, **unread**; the quotations are from
Gartner's own press releases and trade coverage of them.

Running tally across five notes: paid-with-preview (42010, partly read),
registration-gated (TOGAF, unread), openly published (DoDAF, read),
free-but-unread (NAF), trademarked (Zachman, unread), **public domain
(FEAF, read)**, **commercial subscription (Gartner, unread)**. The
pattern that has held throughout: **what a publisher charges predicts
readability far less well than how it publishes.**

## 6. Nonsense — five moves to refuse

**N1. A FEAF artifact pack, "D-8 mode", or artifact recognizer. Refused
on the artefact.** FEAF prescribes no notation, so recognizing a "D-8"
would mean labelling a sequence diagram with a federal artifact code and
adding no capability. Third instance of this refusal (TOGAF, DoDAF,
this), and the wording is settled.

**N2. Any FEAF compliance or Federal-EA claim. Refused.** FEAF compliance
is about producing the six core artifacts and populating the CRM.
pumllint reads one file.

**N3. Reading the three 100.00s as a result about FEAF. Refused.** §5.2:
they are inflated by naming the samples, and they measure the ceiling on
material I wrote. The finding is the *mapping* (§5.1), not the score.

**N4. Answering Gartner by pointing at pumllint's CI positioning.
Refused — this is the tempting one.** The first reading in §5.4 is
available, comfortable, and would let the record close the threats column
with "not applicable". It is only partly true, and adopting it would
discard the one external critique the series has found. **The threat entry
stays open.**

**N5. Building anything to address §5.4.** The critique is about whether
the artefact matters, and no rule, report or feature answers that. The
answer, if there is one, is adopters using the tool on diagrams they
already care about — which is what the demand bar has been waiting for
all along.

## 7. Fit — graded

### F1 — a FEAF artifact pack or recognizer. **No.** N1, N2.

### F2 — pumllint on FEAF's D-1/D-7/D-8 as already-supported. **Yes; nothing to build.** §8.3.

Third instance of the "already works" result after Capella and
DoDAF/TOGAF, and the one with the clearest external warrant: FEAF names
these artifacts, cross-maps them to DoDAF models the DoDAF note already
measured, and names UML among the open notations that support this kind
of modelling. As before, **what is missing is a user, not a capability.**

### F3 — anything addressing the Gartner critique. **Not a fit; not buildable.** N5, §5.4.

### Fit against declared constraints

| Declared constraint | Where these fits land |
|---|---|
| **Demand bar** | **The operative constraint for F2**, and §5.4 is the sharpest external statement of *why* it exists. |
| **Claim language** | Decides N2. |
| **Zero deps / licence** | Not reached — FEAF is public domain, Gartner sells opinions. |
| **Golden score contract** | Untouched. |

## 8. Gap — measured

### 8.1 No discovery probe

Neither half defines a file format or notation. Sixth note in the series
with no §8.1 boundary measurement.

### 8.2 The samples

Three FEAF artifacts, hand-written in PlantUML, each given the
`@startuml <name>` and `title` that a coded federal deliverable would
naturally carry: **D-8** (four lifelines, six messages, balanced
activations, three returns), **D-7** (seven states with guarded
transitions, start and end) and **D-1** (three classes, two labelled
associations with multiplicities).

### 8.3 Three of three, clean

```
d8   type=sequence  Level 4  100.00  elements=10   ✔ No issues found.  (exit 0)
d7   type=state     Level 4  100.00  elements=12   ✔ No issues found.
d1   type=class     Level 4  100.00  elements=5    ✔ No issues found.
```

Zero findings on any of the three. The `sequence` pack exercised
participants, activations and paired returns; the `state` pack exercised
initial state, reachability and labelled transitions; the `class` pack
exercised naming, multiplicities and association labels. Everything that
could have fired had a reason not to.

### 8.4 Why these are 100.00 and DoDAF's were not

DoDAF's samples scored 99.75–99.92 and each carried one `info` finding —
GEN002, "no name". **These carry names and titles, so GEN001 and GEN002
have nothing to say.** That is the whole difference. It is a defensible
choice for FEAF artifacts, which are named, coded deliverables, and it
makes the two notes' numbers **not comparable**. Recorded so nobody reads
a FEAF-beats-DoDAF result out of two notes written a day apart.

### 8.5 What was not measured

**Gartner's research**, entirely — subscription-only, so §2 and §5.4 rest
on press releases and trade coverage of them, and a reader with a Gartner
subscription should check the primary notes before leaning on §5.4.
FEAF's **B-5 Use Case** artifact was not probed against the `usecase`
pack, nor **D-4 Data Flow** against `activity`. The remaining ~44 FEAF
artifacts were not classified; unlike the TOGAF and DoDAF notes, this one
attempts **no coverage count**, because the artifact names are mostly
catalogues, matrices and inventories rather than diagrams and a count
would be more noise than signal.

## 9. SWOT

**Strengths (pumllint, internal)**

- §8.3: three artifact classes, three packs, zero findings.
- §5.1: the framework-to-framework half of the series' mapping method now
  has external confirmation.

**Weaknesses (pumllint, internal)**

- §8.4: the cleanest numbers in the series are partly an artefact of how
  the samples were written, and the note has to say so.
- Nothing in the tool speaks to §5.4.

**Opportunities (external)**

- F2, again without a demonstrated user. Third framework in a row where
  the capability exists and the audience is unverified.

**Threats (external)**

- **§5.4, and it is real.** The first entry in this column across
  eighteen evaluations that is neither "none" nor an internal positioning
  risk. Gartner's position is that architecture documentation fails on
  relevance, not coherence; pumllint measures coherence. The note declines
  to resolve it in either direction (N4).

## 10. Decision, recorded candidates, triggers

**Decision: no FEAF support of any kind, no Federal-EA claim, and nothing
built in response to the Gartner critique. Nothing queued. Three
observations recorded.**

**Never build:**

- A FEAF artifact pack, "D-8 mode" or artifact recognizer (N1) — FEAF
  prescribes no notation, so the code would label a sequence diagram and
  add nothing. Third instance; wording settled.
- Any FEAF compliance or Federal-EA claim (N2).
- Anything premised on the three 100.00s being a result about FEAF (N3) —
  they are inflated by naming the samples (§8.4).
- **Anything built to answer §5.4** (N5) — the critique is about whether
  the artefact matters, which no feature addresses.

**Recorded, not queued:**

1. **FEAF confirms the series' cross-framework mapping** (§5.1). D-8 *is*
   DoDAF SvcV-10c and D-7 *is* SvcV-10b by FEAF's own normative table, so
   the framework-to-framework half of the method the TOGAF/DoDAF/NAF
   notes used is externally corroborated. The pumllint end of the chain
   remains this series' judgement.
2. **The graded-object tally** (§5.3). ACMM grades an organization, TOGAF
   Compliance an implementation, **FEAF a business service**, **Gartner a
   vendor**; ISO 42030 declines to define an aggregate at all. **Four
   objects graded, none of them a description.** Cite the streak with this
   list rather than as a count.
3. **The Gartner critique, unanswered** (§5.4). The first external market
   argument the series has found: architecture documentation fails on
   *relevance*, not *incoherence*; pumllint measures incoherence. Both
   readings recorded, neither adopted, and **the threats column stays
   open** — the comfortable reading (pumllint is a CI check, not an EA
   programme) is only partly true and adopting it would discard the
   critique.

**Re-litigate on:**

- **An adopter running pumllint on diagrams they already care about** —
  the only evidence that bears on §5.4, and the same trigger the demand
  bar has been waiting for since the series began.
- A Gartner subscription becoming available, to check §5.4 against the
  primary research rather than press coverage.
- **Not** on FEAF adoption. FEAF v2 is thirteen years old, prescribes no
  notation, and its artifacts are already reachable without anything
  being built (F2).

## Related reading

- [The DoDAF / UAF ecosystem, evaluated](dodaf-uaf-ecosystem-evaluation.md)
  — the models FEAF's own table maps its artifacts onto; §5.1 is that
  note's mapping, externally confirmed.
- [The TOGAF / ADM ecosystem, evaluated](togaf-adm-ecosystem-evaluation.md)
  — the corrected no-grader criterion, and the ACMM/Compliance entries
  §5.3 extends to four objects.
- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — 42030's abstention, which §5.4 restates in commercial terms.
- [The Zachman ecosystem, evaluated](zachman-ecosystem-evaluation.md) —
  the other "nothing to lint" subject, and the access tally §5.5 extends.
- [ROADMAP.md](../ROADMAP.md) — the demand bar, which §5.4 is the
  sharpest external argument for.
