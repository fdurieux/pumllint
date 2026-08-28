# The NAF / MODAF ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `a923595` (v0.29.0). The
question as posed: investigate the NAF/MODAF ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Sixteenth in a series, and the
first deliberately run as a **sibling test**: NAF and MODAF were both
unified into UAF alongside DoDAF, which was evaluated one turn ago and
produced the strongest fit in the series. The question this note exists
to answer is whether that result generalizes to the family.*

**Verdict up front: no — and the sibling test comes back negative, which
is the point. The DoDAF finding does not transfer, and the reason is
precise enough to be measured.**

**DoDAF's fit rested on one sentence: *"DoDAF does not endorse a specific
event-trace modeling methodology. An OV-6c may be developed using any
modeling notation…"* — so a PlantUML sequence diagram *is* a conformant
OV-6c. NAF says something that sounds similar and is not. NAF is
notation-agnostic about *drawing*, but a NAF-compliant architecture is
built on one of exactly **two approved metamodels — The Open Group's
ArchiMate (3.1) and the OMG's UAF Domain Meta-Model** — and requires
traceable, consistent architectural information structured according to
its viewpoints. **NAF conformance lives in the metamodel, not in the
picture.** A PlantUML file is a rendering; the thing NAF judges is a
model pumllint cannot see.**

**And the measurement inverts, which is the sharpest way to say it. Both
routes below are legitimate NAF practice:**

| NAF route | pumllint type | level | score | findings |
|---|---|---|---|---|
| **the ArchiMate metamodel** — one of the two NAF approves | `sequence` | 4 | **89.22** | **4× false SEQ009** |
| **a picture** — an event trace drawn as a sequence diagram, no metamodel behind it | `sequence` | 4 | **100.00** | **none** |

**The NAF-conformant artefact scores worse than the NAF-meaningless one.**
89.22 with four false findings against a clean 100.00 and exit 0.
pumllint's verdict is, here, *inversely* related to NAF conformance —
which is the measured form of "the DoDAF result was about DoDAF's
wording, not about defence frameworks". §8.3.

**MODAF, meanwhile, is dead — the first withdrawn framework in sixteen
evaluations.** Its GOV.UK guidance is marked **[Withdrawn]**, its
published PDFs carry `-withdrawn` in their filenames, and the UK MOD's
2024 Defence Architecture Framework adopts NAFv4 instead. Sixteen notes
have refused to build framework-specific packs on grounds of scope, claim
language and demand. **MODAF supplies the empirical grounds: a linter
tied to a framework dies with the framework.** §5.2.

*Bounds. **NAFv4 is freely downloadable and I did not read it.** NATO's
topic page returned 404; the framework's structure, its two approved
metamodels and the absence of any grading scheme are characterized from
Wikipedia and vendor guides, not from the standard. That makes this the
fourth access data point and an uncomfortable one: 42010 was **paid** and
partly read, TOGAF **gated** and unread, DoDAF **open** and read
directly, NAF **open and still unread** — free is necessary and not
sufficient, and the limit this time was mine, not the publisher's. **I
could not obtain the exact NAFv4 grid rows and columns** from any source
fetched, so this note does not name them. Both probe samples are mine.
Every pumllint claim was executed at `a923595` with default config from a
neutral working directory, and **re-confirmed unchanged after merging the
G3/G4 rule and CLI changes** that landed on `main` while this note was in
review — both §8.3 numbers and the finding set are identical either side
of that change. Per session scope no GitHub repository was
read.*

## 0. Why this ran, and what a sibling test is for

No prior record: the repository has never mentioned NAF or MODAF.

But the family has. The DoDAF/UAF note (fifteenth, hours old) found the
strongest artefact fit of the series and called it "the first that is
both real and reachable". UAF exists precisely because DoDAF, MODAF and
NAF were unified; NAFv4 is built on the UAF Domain Meta-Model. So the
three are siblings, and a result on one either generalizes or does not.

**Fifteen notes in, that question is worth asking about the series
itself.** A series that keeps finding novelty in adjacent ecosystems
should be suspected of manufacturing it. This note was run expecting to
report "the DoDAF finding, again, with different acronyms" — and the
honest answer turned out to be sharper and in the opposite direction.

## 1. The ecosystem

### 1.1 MODAF, withdrawn

The **UK MOD Architecture Framework**, last at version 1.2.004 (2010),
organized ~47 views across seven viewpoints: Strategic (StV),
Operational (OV), Service Oriented (SOV), Systems (SV), Acquisition
(AcV), Technical Standards (TV) and All Views (AV). Its OV-6c was an
**Operational Event-Trace Description**, the same artefact class as
DoDAF's.

It is **withdrawn**. The GOV.UK guidance page is labelled `[Withdrawn]`;
the archived specification PDFs are published under filenames ending
`-withdrawn.pdf`; and the MOD's **2024 Defence Architecture Framework
(DAF)** adopts **NAFv4** as its preferred framework. Existing MODAF
artefacts remain in circulation; new UK defence work is NAF.

### 1.2 NAFv4

The **NATO Architecture Framework version 4** was issued in **January
2018** by the Architecture Capability Team of NATO's Consultation,
Command and Control Board, with backward compatibility to NAFv3. Its
viewpoints are arranged in a **Zachman-like grid** — rows are "subjects
of concern", columns are "aspects of concern". (The exact row and column
names could not be obtained from any source fetched, and are therefore
not stated here.)

NAFv4 is **freely downloadable** from NATO, and aligns itself with ISO,
IEEE, The Open Group and the OMG.

### 1.3 The metamodel constraint, which is the whole finding

NAFv4 identifies **two approved metamodels** for creating its viewpoints:

- **The Open Group's ArchiMate**, version 3.1
- **The OMG's UAF Domain Meta-Model**

and it is described as not mandating ArchiMate, UML, BPMN or any other
*visual* notation while requiring **traceable, consistent architectural
information structured according to its viewpoints**.

Read carefully, those two statements do different work from DoDAF's
sentence. DoDAF freed the **notation** and said nothing about an
underlying model. NAF frees the **rendering** and constrains the
**model**. §2 works out the consequence.

## 2. The seam, and why it closes where DoDAF's opened

pumllint reads a `.puml` file — a rendering. It has no model behind it,
by design: the parser is a tolerant projection of text, and the
repository has refused a metamodel layer repeatedly and on record.

DoDAF asks for an OV-6c and accepts any notation that shows timing and
sequence. A PlantUML sequence diagram satisfies that as written, so
pumllint's verdict on the file is a verdict on the deliverable.

NAF asks for viewpoints whose content conforms to ArchiMate or the UAF
DMM. A PlantUML sequence diagram can *depict* such content, but the
conformance question — is this an ArchiMate model? does it satisfy the
UAF DMM? — is answered somewhere pumllint does not look. **So a good
pumllint score on a NAF artefact is silent about the property NAF
cares about**, and §8.3 shows it can be worse than silent.

## 3. Overlap

| Concern | pumllint | NAF / MODAF | Reading |
|---|---|---|---|
| Event traces | `sequence` pack | MODAF OV-6c; NAF sequence-aspect viewpoints | Same artefact class as DoDAF — but see the conformance row |
| **Conformance** | none — reads a rendering | **metamodel conformance (ArchiMate 3.1 or UAF DMM)** | **Disjoint, and this decides the note** |
| Metamodel | refused on record | required | pumllint has nothing to offer here and should not |
| ArchiMate route | **measured invisible** (third note, re-confirmed §8.3) | one of two approved metamodels | **The third note's finding is now load-bearing** |
| Grid vocabulary | five packs | UAF-derived aspects | Same convergence as the DoDAF note; nothing new |
| Framework longevity | notation-level | **MODAF withdrawn** | §5.2 |
| Aggregate verdict | the scoring model | none found | Sixteenth, no grader |

## 4. Boundaries

1. **Rendering vs. model.** §2. The boundary that DoDAF's wording
   dissolved, NAF restores.
2. **A dead framework.** MODAF is not a boundary so much as a warning
   (§5.2).
3. **No notation of its own.** Neither NAF nor MODAF defines a syntax, so
   there is nothing to parse and no §8.1 discovery probe — fourth note in
   the series with none.

## 5. Sense — four true things

### 5.1 The sibling test came back negative, and that is worth more than a confirmation

The DoDAF note's headline was that a PlantUML sequence diagram *is* a
conformant OV-6c. It would have been easy — and wrong — to carry that
into "defence frameworks are pumllint's best fit". **The fit was
specific to one sentence in one framework.** NAF's near-identical
notation-agnosticism does not produce it, because NAF spends its
constraint on the metamodel instead.

The DoDAF entry should be read with this attached: **the finding is
DoDAF-specific and does not generalize to the family it was unified
with.**

### 5.2 MODAF's death is the empirical case against framework packs

Sixteen evaluations have refused framework-specific packs — on scope
(the artefact is wrong), on claim language (it would assert a
relationship that does not exist), and on demand (nobody asked). All
three are arguments. MODAF supplies a fact: **a framework with ~47
prescribed views, national backing and a decade of use is now
`[Withdrawn]`, and anything built to recognize its view types would be
dead code today.**

pumllint's positioning — at the notation, below the framework — survives
this by construction. A PlantUML sequence diagram was a MODAF OV-6c in
2010 and is a NAF sequence-aspect view in 2026, and the tool needed no
change. That is an argument for the layer this project chose, and it is
the first time the series has been able to make it from evidence rather
than principle.

### 5.3 The ArchiMate finding is now load-bearing, not a curiosity

The ArchiMate evaluation (third in the series) measured native ArchiMate
notation as invisible to pumllint. At the time that was a fact about one
notation. **NAF makes ArchiMate one of exactly two approved metamodels
for a live NATO framework**, so the third note's finding now describes
what happens to half of NAF's sanctioned routes. §8.3 re-confirms it at
current HEAD.

### 5.4 Sixteenth ecosystem, no grader

In the corrected form the TOGAF note established: nothing here grades a
description. No conformance levels, maturity model or scoring scheme
appears in the NAF material examined. Weaker evidence than usual — the
standard itself was not read (§8.5) — and recorded with that caveat.

## 6. Nonsense — five moves to refuse

**N1. A NAF or MODAF pack, view-type recognizer, or mode. Refused on the
artefact and now on the evidence.** Neither framework defines a notation;
and §5.2 shows what a framework-shaped pack is worth when the framework
is withdrawn.

**N2. Any NAF conformance claim. Refused, and more firmly than the DoDAF
equivalent.** NAF conformance is metamodel conformance. pumllint reads a
rendering and has no metamodel, deliberately. A claim of NAF support
would be false in a way that is easy to demonstrate.

**N3. Reading the DoDAF result as a family result. Refused — this is the
specific trap this note exists to close.** §5.1. One framework's
permissive sentence is not a property of defence frameworks, and the
series should not accumulate a general claim out of one measurement.

**N4. Building toward the metamodel to close the gap. Refused on the
standing record.** A metamodel layer, a model store, or a conformance
checker over ArchiMate or the UAF DMM are all the same never-build the
repository has held since the knowledge-graph and OWL/SHACL settlements.
NAF is a new reason to want it and not a new reason to build it.

**N5. Presenting §8.3's 100.00 as a good result. Refused.** It is a clean
score on a file that tells a NAF architect nothing about the thing they
are accountable for. The number is correct and the impression it would
create is not.

## 7. Fit — graded

### F1 — a NAF/MODAF pack, recognizer or mode. **No.** N1.

### F2 — pumllint on NAF artefacts, as with DoDAF. **No — and this is the correction.** §5.1, §8.3.

The DoDAF fit was that the framework's own text made a PlantUML sequence
diagram a conformant deliverable. NAF's text does not do that. What is
left is a linter over a picture whose conformance is decided elsewhere,
and §8.3 shows the picture that scores best is the one furthest from the
approved metamodels.

### F3 — the ArchiMate route. **No, and it is the worst case.** §5.3, §8.3.

Half of NAF's sanctioned routes lands in a notation pumllint reads as
four unpaired returns.

### F4 — a MODAF anything. **No.** The framework is withdrawn (§5.2).

### Fit against declared constraints

| Declared constraint | Where the NAF/MODAF fits land |
|---|---|
| **Claim language** | **Decides N2.** "NAF-compliant" would assert metamodel conformance the tool cannot assess. |
| **No metamodel layer** (knowledge-graph / OWL-SHACL settlements) | **Decides N4** — NAF is a fresh motivation for a settled refusal. |
| **Demand bar** | Not reached; nothing here is a candidate. |
| **Zero runtime dependencies / licence** | Not reached. |

## 8. Gap — measured

### 8.1 No discovery probe

Neither framework defines a file format or a notation. Fourth note in the
series with no §8.1 boundary measurement, after 42010, TOGAF and DoDAF —
and the reason is now familiar enough to be a pattern: **frameworks do
not have syntax, so pumllint's boundary with them is never a parsing
question.**

### 8.2 The samples

Two files, both representing legitimate NAF practice. **Route A** uses
PlantUML's native `archimate` syntax — four elements (business actor,
business process, application component, node) and four relationships —
because ArchiMate is one of NAF's two approved metamodels. **Route B**
is an event trace for a tasking thread drawn as an ordinary PlantUML
sequence diagram: three participants, four messages, balanced
activations, two dashed returns.

### 8.3 The inversion

| Route | type | level | score | elements | findings | exit |
|---|---|---|---|---|---|---|
| **A — ArchiMate metamodel** | `sequence` | 4 | **89.22** | 8 | **4× SEQ009**, GEN001, GEN002 | 0 |
| **B — a picture** | `sequence` | 4 | **100.00** | 7 | **none** | 0 |

```
archimate_route.puml:6: [SEQ009/minor] Return '<unlabelled>' from 'CA' to 'TP' pairs with no preceding call
archimate_route.puml:7: [SEQ009/minor] Return '<unlabelled>' from 'TP' to 'C2' pairs with no preceding call
archimate_route.puml:8: [SEQ009/minor] Return '<unlabelled>' from 'C2' to 'CB' pairs with no preceding call
archimate_route.puml:9: [SEQ009/minor] Return '<unlabelled>' from 'CB' to 'C2' pairs with no preceding call
```

Route A reproduces the ArchiMate evaluation's finding in a NAF context
and at current HEAD: the `archimate` keyword is not a type marker, so
four ArchiMate elements become implicit lifelines and four ArchiMate
relationships become unpaired returns. Standing type-fallback class —
**no candidate and no amendment**.

Route B is a perfect score. It is also, by NAF's lights, an
unsubstantiated picture: nothing in it is traceable to ArchiMate or the
UAF DMM, which is what NAF asks for.

**So the ranking is backwards.** The route that satisfies NAF scores
89.22 and draws four false findings; the route that satisfies nothing
scores 100.00 clean. This is not a defect — pumllint is measuring what it
says it measures, and route B genuinely is a well-formed sequence
diagram. It is a **positioning** result, and the clearest available
statement of why the DoDAF fit does not carry over: **when a framework's
conformance lives in a metamodel, a renderer-level score can rank
artefacts in the opposite order from the framework's own criterion.**

### 8.4 What this does *not* show

Route B is not "wrong". Nothing in pumllint claims to assess NAF
conformance, and a NAF architect who also wants their sequence diagrams
coherent is well served. The finding is about what a score means, not
about whether the score is correct — and N5 exists so the 100.00 is not
quoted without §8.3's other row.

### 8.5 What was not measured

**NAFv4 itself**, which is freely downloadable and was not read: NATO's
topic page 404'd and no substitute primary source was obtained, so §1.2
and §1.3 rest on Wikipedia and vendor guides. **The grid** — rows,
columns and viewpoint codes — could not be obtained at all, so this note
names none of them and no coverage count of the DoDAF or TOGAF kind is
attempted. No MODAF view was probed beyond noting that its OV-6c matches
DoDAF's, already measured. No NAF or MODAF tool was run.

## 9. SWOT

**Strengths (pumllint, internal)**

- §5.2: the notation-level position survives a framework's death without
  a code change, demonstrated rather than argued.
- Route B is a genuine 100.00 with no findings — the tool does its own
  job well on the artefact.

**Weaknesses (pumllint, internal)**

- §8.3: the ranking is backwards relative to NAF's criterion, and nothing
  in the output signals that the criterion is different.
- Route A is the sixth-plus appearance of the ArchiMate fall-through, now
  affecting a live framework's approved metamodel.

**Opportunities (external)**

- None. F2 was the opportunity and §5.1 closes it.

**Threats (external)**

- None to the tool. The threat this note actually addresses is internal:
  a fifteen-note series generalizing one framework's permissive sentence
  into a family-wide fit.

## 10. Decision, recorded candidates, triggers

**Decision: no NAF or MODAF support of any kind, no conformance claim,
and no metamodel work motivated by NAF. Nothing queued. One narrowing
correction and two observations.**

**Narrowing correction to the record:**

The DoDAF/UAF entry's fit — "a PlantUML sequence diagram is a conformant
OV-6c" — **is specific to DoDAF's wording and does not generalize to the
family**. NAF, unified with DoDAF into UAF, frees the rendering and
constrains the **metamodel** (ArchiMate 3.1 or the UAF DMM), so
conformance sits where pumllint does not look. Cite the DoDAF result as a
fact about DoDAF, never as a fact about defence frameworks.

**Never build:**

- A NAF or MODAF pack, view-type recognizer or mode (N1) — no notation to
  recognize, and §5.2 shows what such a pack is worth when the framework
  is withdrawn.
- Any NAF conformance or compliance claim (N2) — NAF conformance is
  metamodel conformance; pumllint reads a rendering and has no metamodel,
  deliberately.
- **Reading the DoDAF result as a family result** (N3) — the specific
  trap this note closes.
- A metamodel layer, model store or ArchiMate/UAF-DMM conformance checker
  motivated by NAF (N4) — the standing never-build; a new reason to want
  it is not a new reason to build it.
- Quoting §8.3's 100.00 without its other row (N5).

**Recorded, not queued:**

1. **The narrowing correction** (above) — the substantive output.
2. **MODAF's withdrawal as empirical support** for the framework-pack
   refusal (§5.2). Sixteen notes argued the position; this one can point
   at a framework that died while the notation did not.
3. **The ArchiMate finding is load-bearing** (§5.3) — the third note's
   measurement now describes half of a live NATO framework's approved
   routes, not a curiosity.

**Re-litigate on:**

- **NAF issuing a notation-level conformance statement of DoDAF's kind** —
  the only development that would reopen F2, and there is no sign of it.
- An adopter working the ArchiMate route and reporting the fall-through —
  which would make §8.3's route A a demand signal rather than a
  measurement.
- **Not** on NAF adoption, and emphatically not on MODAF: one is a
  framework whose conformance criterion pumllint structurally cannot
  meet, and the other is withdrawn.

## Related reading

- [The DoDAF / UAF ecosystem, evaluated](dodaf-uaf-ecosystem-evaluation.md)
  — the sibling this note tests, and whose fit §5.1 narrows to DoDAF's
  own wording.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the third note, whose invisibility finding §5.3 promotes to
  load-bearing and §8.3 re-confirms at current HEAD.
- [The TOGAF / ADM ecosystem, evaluated](togaf-adm-ecosystem-evaluation.md)
  — the corrected "no grader" criterion §5.4 uses.
- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md)
  — the metamodel never-build that decides N4.
- [ROADMAP.md](../ROADMAP.md) — the claim-language discipline behind N2
  and the settled refusals behind N4.
