# The DoDAF / UAF ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `a8ef78a` (v0.29.0). The
question as posed: investigate the DoDAF/UAF ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Fifteenth in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, Structurizr DSL,
Ilograph, Graphviz/DOT, SysML, Capella/Arcadia, ISO 42010, TOGAF, this).*

**Verdict up front: still no as a build — and this is the strongest
artefact fit found in fifteen evaluations, by a clear margin, and the
first that is both real and reachable.**

**The reason is one sentence of official DoDAF text.** The OV-6c
Event-Trace Description is a model DoDAF *requires*, described in its own
words as *"a time-ordered examination of the Resource Flows as a result
of a particular scenario"*, and *"sometimes called sequence diagrams"*.
And on notation, the Department of Defense CIO's own page says:

> **"DoDAF does not endorse a specific event-trace modeling methodology.
> An OV-6c may be developed using any modeling notation (e.g., BPMN) that
> supports the layout of timing and sequence of activities."**

**So a PlantUML sequence diagram is a conformant OV-6c.** Not a
workaround, not a hand-drawn approximation of something the framework
would rather see elsewhere — the framework authorizes it in normative
text. Capella's Exchange Scenario fitted and could not be reached because
Capella emits no PlantUML. Here there is nothing to reach past: the
notation is the practitioner's choice, and PlantUML is a legitimate one.

**The measurement, on the default profile:**

| DoDAF model | pumllint type | correct? | level | score | findings | exit |
|---|---|---|---|---|---|---|
| **OV-6c Event-Trace Description** | **`sequence`** | **yes** | 4 | **99.88** | GEN002 only | **0** |
| **OV-6b State Transition Description** | **`state`** | **yes** | 4 | **99.92** | GEN002 only | 0 |
| **DIV-2 Logical Data Model** | **`class`** | **yes** | 4 | **99.75** | GEN002 only | 0 |
| SV-1 Systems Interface Description | `sequence` | no — fallback | 4 | 89.79 | 2× false SEQ009 | 1 |

**99.88 with a single `info` finding, on pumllint's deepest pack.** The
eleven-rule sequence pack exercised activations, paired returns and
declared participants, and every one of them was right. No previous
foreign artefact in this series has scored that well.

**And the counterweight, which matters as much. Under the `codegen`
profile the same OV-6c collapses to Level 2 (Structured), 52.4/100, with
four blockers** — SEQ103 demanding signature-shaped messages of
`request immediate CAS` and `transmit 9-line brief`. Those messages are
*correct DoDAF*: an OV-6c records operational events in operational
language and will never generate code. **The profile that is right for
this artefact class is the default, and the profile that is wrong for it
is wrong loudly, and nothing in the tool says so.** §8.4 — the first
configuration finding in the series.

**Fifteenth ecosystem, no grader — in the corrected form the TOGAF note
established — and this one supplies a *reason*.** DoDAF's organizing
doctrine is **"Fit-for-Purpose"**: architectural content is to be
tailored so that "the purpose or use of an architectural description at
each level will be different in content, structure, and level of detail".
That is not silence about grading; it is a stated position that the right
content depends on the purpose, which is what a fixed rubric denies.
§5.4.

*Bounds. **This is the first ecosystem in three whose normative text was
actually readable**, and the arc is worth recording: ISO 42010 was
**paid** and yielded Clause 4 verbatim from a published preview; TOGAF was
**free but registration-gated** and yielded no primary text at all;
DoDAF is a **US Government work, published openly**, and the OV-6c
quotation above is from `dodcio.defense.gov` directly. UAF's grid
structure and view count are characterized from vendor and OMG secondary
sources, not from the UAF specification. **The four samples are mine**,
written to be well-formed, so §8.3 measures how pumllint treats a *good*
OV-6c — not how it treats one from a real program office, which is
unmeasured and is exactly where the value would be (§9). Every pumllint
claim was executed at `a8ef78a` with default config from a neutral
working directory except where the `codegen` profile is named. Per
session scope no GitHub repository was read.*

## 0. Why this ran, and the prior record

Three prior mentions, all glancing. The Linked.Archi note recorded
**DoDAF 2.02 and UAF 1.2 framework integrations** and **UAF ↔ DoDAF SKOS
mappings**. The ISO 42010 note quoted UAF twice from the standard itself —
once in the **ADL examples** (AADL, ArchiMate, UML, SysML, **UAF
Profile**), once under stakeholder perspective, where 42010 says the rows
of the **Unified Architecture Framework** grid *correspond to stakeholder
perspectives*. Neither exercised anything.

This note lands one turn after TOGAF, and the pairing is the point (§5.2).

## 1. The ecosystem

### 1.1 DoDAF

**The DoD Architecture Framework, Version 2.02** (2010) organizes **52
models** across **eight viewpoints**: All (AV), Capability (CV), Data and
Information (DIV), Operational (OV), Project (PV), Services (SvcV),
Standards (StdV) and Systems (SV). Underneath sits the **DoDAF Meta-Model
(DM2)**.

Its stated goals for 2.0 were to establish guidance for architecture
content **as a function of purpose — "fit for purpose"** — and to
increase utility via the DM2. §5.4 is about that phrase.

### 1.2 UAF

The **Unified Architecture Framework** (OMG; 1.0 in 2017, **1.2** in
2022) succeeds UPDM and unifies DoDAF, MODAF and NAF. It is a **UML/SysML
profile** — the UAFP — which is why 42010 lists it as an ADL beside
ArchiMate, UML and SysML.

Its **grid** is 10 rows (stakeholder domains: architecture management,
strategic, operational, services, personnel, resources, security,
projects, standards, actual resources) × 11 columns (model kinds:
motivation, taxonomy, structure, connectivity, **processes**, **states**,
**sequences**, **information**, constraints, roadmap, traceability),
organizing **71 view specifications**.

**Four of those eleven column names are pumllint's packs**: sequences,
states, processes (activity), information (class). That is not a
coincidence of vocabulary — it is the same decomposition of behaviour and
structure, reached independently, and it is the fourth such convergence
in the series after bpmnlint, Capella's categories and 42010's
correspondences.

### 1.3 The models that matter, in DoDAF's own words

- **OV-6c / SvcV-10c / SV-10c — Event-Trace Descriptions.** *"A
  time-ordered examination of the Resource Flows as a result of a
  particular scenario"*, allowing *"the tracing of actions in a scenario
  or critical sequence of events"*, **"sometimes called sequence
  diagrams"**. Notation explicitly unconstrained.
- **OV-6b / SvcV-10b / SV-10b — State Transition Descriptions**, used
  with the event traces *"to describe the dynamic behavior"*.
- **DIV-1 / DIV-2 / DIV-3 — Conceptual / Logical / Physical Data
  Models.**
- **OV-5b, SvcV-4, SV-4 — Activity and Functionality models.**

## 2. The seam, and why it is wide open here

pumllint reads a `.puml` file. DoDAF requires an OV-6c and **does not say
what to draw it in**. The seam is therefore not a conversion, an export,
or a mis-typing hazard: it is a straightforward case of a framework
requiring an artefact class and leaving the rendering to the architect.

This is the first ecosystem in fifteen where the seam is neither narrow
nor blocked. TOGAF prescribed artifacts and had no sequence diagram;
Capella had the artefact and no export; SysML had the model and no reach.
DoDAF has the artefact, permits the notation, and the notation is one
pumllint reads.

## 3. Overlap

| Concern | pumllint | DoDAF / UAF | Reading |
|---|---|---|---|
| **Event traces** | **`sequence` — 11 base + 9 codegen rules** | **OV-6c, SvcV-10c, SV-10c** | **The strongest overlap in the series — §8.3** |
| State machines | `state` pack | OV-6b, SvcV-10b, SV-10b | Correct, measured |
| Data structure | `class` pack | DIV-1, DIV-2, DIV-3 | Correct, measured |
| Activity / function | `activity` pack | OV-5b, SvcV-4, SV-4 | Plausible, unprobed |
| Use cases | `usecase` pack | **no counterpart** | DoDAF has no use-case model |
| Interfaces / structure | none | OV-2, SV-1, SvcV-1, SvcV-2 | Falls through — §8.5 |
| Matrices | none | ~14 matrix models | Wholly DoDAF-side, and rightly |
| Model-kind vocabulary | six dimensions, five packs | UAF's 11 grid columns | **Four names shared** — §1.2 |
| Aggregate verdict | the scoring model | none, and **"Fit-for-Purpose"** says why | §5.4 |

## 4. Boundaries

1. **Framework vs. file.** DoDAF says an OV-6c must exist and what it
   must convey. pumllint says whether the file holds together. Adjacent,
   not overlapping — but for once they are adjacent *at the same
   artefact*.
2. **12 of 52.** Most DoDAF models are matrices, taxonomies, forecasts
   and profiles with no diagram shape at all (§8.5).
3. **No conformance relationship.** DoDAF conformance is about the DM2
   and the required models' content; pumllint checks neither.
4. **Access is not a boundary here** — first time in three notes (§5.5).

## 5. Sense — five true things

### 5.1 The fit is real, reachable, and the best in fifteen evaluations

§8.3. A well-formed OV-6c scores **99.88 with exit 0 and one `info`**,
using pumllint's deepest pack correctly. Two more DoDAF model classes
land equally cleanly on two more packs. And unlike every previous "this
works" result in the series, **nothing blocks a practitioner from
getting it** — DoDAF permits the notation in writing.

### 5.2 One turn after TOGAF, this is the exact inversion, and the pair is the finding

The TOGAF note found the `sequence` pack — the deepest in the tool —
mapping to **none** of TOGAF's 32 diagrams, and called that an inversion
of the series. DoDAF maps **three** models to it, and names them event
*traces*.

| | artifacts | maps to a pack | `sequence` |
|---|---|---|---|
| TOGAF | 32 diagrams | 7 | **0** |
| DoDAF | 52 models | **12** | **3** |

Read together: **frameworks differ sharply in whether they ask for
time-ordered interaction models at all**, and pumllint's centre of
gravity suits the ones that do. That is a more useful statement about the
tool's fit than either note could make alone, and it took two adjacent
evaluations to see.

### 5.3 The UAF grid converges on the pack decomposition

§1.2. Four of UAF's eleven model-kind columns — sequences, states,
processes, information — are pumllint's packs by name. Fourth
independent convergence in the series (bpmnlint's rules, Capella's rule
categories, 42010's correspondences, this). The decomposition keeps being
reinvented, which is evidence it is natural.

### 5.4 Fifteenth ecosystem, no grader — and the first one that says *why*

In the corrected form the TOGAF note established: nothing here grades a
*description*. DoDAF adds something the previous fourteen did not — a
stated rationale. **"Fit-for-Purpose"** holds that architectural content
should be tailored so that "the purpose or use of an architectural
description at each level will be different in content, structure, and
level of detail."

A fixed rubric denies exactly that. So the running question — is the
empty niche an oversight or a choice? — gets its first piece of
first-party reasoning, and it points at *choice*. This does not settle
it: "content should vary with purpose" is an argument against a *fixed
content checklist*, and pumllint's rules are mostly about internal
coherence rather than required content, which is a narrower target. But
it is the closest thing to a stated objection the series has found, and
it belongs in the record beside 42030's abstention and TOGAF's
aggregation-elsewhere.

### 5.5 Access, third data point, and the pattern is not what one would guess

ISO 42010: **paid**, and Clause 4 was quoted verbatim from a published
preview. TOGAF: **free, registration-gated**, and no primary text was
obtained at all. DoDAF: **US Government work, openly published**, and
§1.3's quotations are from the DoD CIO's own pages. Price predicts
readability poorly; publication model predicts it well.

## 6. Nonsense — five moves to refuse

**N1. A DoDAF or UAF "mode", model-type recognizer, or artifact pack.
Refused on the artefact.** DoDAF prescribes no notation, so there is
nothing to recognize — an OV-6c is a sequence diagram whether or not
anything says so, and pumllint already reads it correctly *because* it is
one. A recognizer would add a label and no capability.

**N2. Claiming DoDAF or UAF conformance, support, or alignment. Refused.**
DoDAF conformance concerns the DM2 and required model content. pumllint
checks a file's internal coherence and would be claiming a relationship
it does not have — the same refusal as the 42010 note's N1, and for the
same reason.

**N3. A UAF profile, or reading the grid-column convergence as an
integration. Refused.** UAF is a UML/SysML profile; §1.2's shared
vocabulary is evidence the decomposition is natural, not that the tools
should meet. This is the fourth time this refusal has been needed and the
wording is now settled.

**N4. Marketing the OV-6c result. Refused, and it is the tempting one.**
§8.3 is a good result on a sample **I wrote to be well-formed**. It shows
what pumllint does with a clean OV-6c, not that real ones are clean, and
not that any program office wants a linter. The demand bar exists for
exactly this gap; §9 records the honest version.

**N5. Shipping a "DoDAF profile" of the rule set. Refused as
premature — but note §8.4 is a real problem.** The finding that `codegen`
is actively wrong for an OV-6c is worth recording; a named profile is not
the fix, because the default profile already does the right thing and a
DoDAF-branded alias would be N1 wearing a config key.

## 7. Fit — graded

### F1 — a DoDAF/UAF pack, mode, or recognizer. **No.** N1, N3.

### F2 — pumllint on OV-6c / OV-6b / DIV-2 as already-supported. **Yes, reachable, and nothing to build.** §8.3.

The strongest F2-shaped result in the series. Three DoDAF model classes
parse correctly and score 99.75–99.92 with no false findings, on three
packs, and DoDAF's own text permits the notation. Second instance of
"already works" after Capella and TOGAF, and the first where the
practitioner is not blocked from using it.

**What is missing is a user, not a capability.** §9.

### F3 — a `codegen`-profile warning for narrative sequence diagrams. **A real observation, parked.** §8.4, N5.

The measured problem is genuine: the same file is 99.88 on the default
profile and 52.4 with four blockers under `codegen`, and the blockers are
wrong for the artefact class. But the fix is not a DoDAF feature — it is
either documentation ("`codegen` assumes the diagram will generate code")
or nothing, since the default already behaves correctly. Parked on the
demand bar.

### F4 — DoDAF conformance claims. **No.** N2.

### Fit against declared constraints

| Declared constraint | Where the DoDAF/UAF fits land |
|---|---|
| **Demand bar** | **The operative constraint.** F2 needs no build and has no demonstrated user; F3 is parked on it. |
| **Claim language** | Decides N2 — "DoDAF-conformant" would assert a relationship that does not exist. |
| **Zero runtime dependencies** | Not reached. |
| **Licence posture** | Not the issue: DoDAF is a US Government work and UAF an OMG spec. Fifth evaluation since the EPL run. |
| **Golden score contract** | Untouched. |

## 8. Gap — measured

### 8.1 No discovery probe, and this time for a good reason

DoDAF prescribes no file format and no notation, so there is nothing to
place beside `.puml`. Third note in the series with no §8.1 boundary
measurement — but unlike 42010 and TOGAF, here the absence is *permissive*
rather than merely conceptual: the framework's silence on notation is
what makes §8.3 possible.

### 8.2 The samples

Four DoDAF models, hand-written in the PlantUML a practitioner would
reach for: an **OV-6c** (three lifelines, seven messages, balanced
activations, three dashed returns), an **OV-6b** (seven states, start and
end, guarded transitions), a **DIV-2** (three classes, two labelled
associations with multiplicities) and an **SV-1** (three components,
three labelled arrows).

### 8.3 Three of four correct, and the best score in the series

| Model | type | correct | level | score | elements | findings | exit |
|---|---|---|---|---|---|---|---|
| OV-6c Event-Trace | `sequence` | **✓** | 4 | **99.88** | 10 | GEN002 (info) | **0** |
| OV-6b State Transition | `state` | **✓** | 4 | **99.92** | 16 | GEN002 (info) | 0 |
| DIV-2 Logical Data Model | `class` | **✓** | 4 | **99.75** | 5 | GEN002 (info) | 0 |
| SV-1 Systems Interface | `sequence` | ✗ | 4 | 89.79 | 6 | 2× SEQ009 + GEN001 | 1 |

The three correct results carry **one `info` finding each** — "no name",
true of the samples and fixable with `@startuml ov-6c-cas`. Nothing
false, nothing spurious.

The OV-6c result is the one to note. It exercised the deepest pack in the
tool — declared participants (SEQ001/SEQ002 satisfied on evidence),
balanced activate/deactivate (SEQ003), dashed returns paired with
preceding calls (**SEQ009 correct**, where it was false in six previous
evaluations), and labelled messages (SEQ005, DIM-AMB quiet). Every rule
that fired or stayed silent did so for the right reason.

### 8.4 And the `codegen` profile is actively wrong for it

The same file, one flag different:

```
$ python3 -m pumllint score ov6c.puml --profile codegen
ov6c.puml: Level 2 (Structured) — 52.4/100

ov6c.puml:14: [SEQ103/blocker] Message 'check in on station' is not signature-shaped;
              use name(params) (the accepted shape is the 'pattern' option)
ov6c.puml:14: [SEQ104/major]   Synchronous call 'check in on station' has no explicit return
ov6c.puml:15: [SEQ103/blocker] Message 'transmit 9-line brief' is not signature-shaped
✖ 9 issue(s): 4 blocker, 1 info, 3 major, 1 minor
```

**99.88 → 52.4, exit 0 → exit 1, one info → four blockers.**

The blockers are not defects in the rules. SEQ103 exists because a
sequence diagram destined for code generation needs signature-shaped
messages. An OV-6c is destined for an operational review; `request
immediate CAS` and `transmit 9-line brief` are exactly what DoDAF asks
for, and turning them into `requestImmediateCAS()` would make the model
worse as an OV-6c.

So the profile is doing its job and is pointed at the wrong artefact. The
default profile — which is what a user gets without asking — is right.
**Nothing in the tool warns that `codegen` encodes an assumption about
the diagram's destiny**, and this is the first evaluation in fifteen where
a *configuration choice*, rather than a parse or a rule, produced the
wrong answer. F3, N5.

### 8.5 What falls through, and what is out of scope

SV-1 mis-types to `sequence` with two false SEQ009s — the standing
type-fallback class (ArchiMate, C4, Mermaid, UML, Capella, TOGAF), **no
candidate and no amendment**. DoDAF's structural models (OV-2, SV-1,
SvcV-1, SvcV-2) all have this shape.

Coverage across the 52, as my classification of model purposes — DoDAF
prescribes no notation, so this is a judgement about what each model *is*,
not what DoDAF says to draw:

| pumllint pack | DoDAF models |
|---|---|
| `sequence` | OV-6c, SvcV-10c, SV-10c (**3**) |
| `state` | OV-6b, SvcV-10b, SV-10b (**3**) |
| `activity` | OV-5b, SvcV-4, SV-4 (**3**) |
| `class` | DIV-1, DIV-2, DIV-3 (**3**) |
| `usecase` | **none** |

**12 of 52**, three each across four packs. The other 40 are matrices
(~14 of them), taxonomies, timelines, forecasts, rules models, standards
profiles and the AV overview — none of which is a diagram in pumllint's
sense, and none of which it should attempt.

### 8.6 What was not measured

The `activity` pack against OV-5b. Any real OV-6c: the samples are mine
and were written to be well-formed, so **this note measures the ceiling,
not the field**. No DoDAF or UAF tool was run. UAF's grid and its 71 view
specifications are characterized from vendor and OMG secondary sources;
the UAFP specification was not read. Whether any DoD program office
renders OV-6cs in PlantUML is unknown and is the whole of §9.

## 9. SWOT

**Strengths (pumllint, internal)**

- §8.3: the best foreign-artefact result in fifteen evaluations, on the
  deepest pack, with the framework's own text permitting the notation.
- Three model classes, three packs, no false findings.
- SEQ009 correct on a foreign artefact for the second time (after
  Capella), and for the same reason: the artefact really is a sequence.

**Weaknesses (pumllint, internal)**

- §8.4: the `codegen` profile produces four blockers and Level 2 on a
  model that is correct as written, with no warning that the profile
  assumes a destiny the artefact does not have.
- §8.5: DoDAF's structural models fall through, as they have in six
  previous ecosystems.
- The `usecase` pack — which TOGAF exercised — has no DoDAF counterpart.

**Opportunities (external)**

- F2 is the first fit in the series that is real, reachable and needs no
  build. **What it lacks is evidence of a user.** DoD program offices are
  a plausible but wholly unverified audience, and defence documentation
  practice is not something this note has any visibility into.

**Threats (external)**

- None to the tool. The honest risk is internal: §8.3 is a good number
  from a sample I wrote, and good numbers from self-authored samples are
  how a project talks itself into a market that is not there (N4).

## 10. Decision, recorded candidates, triggers

**Decision: no DoDAF or UAF support of any kind — no pack, no mode, no
recognizer, no profile, no conformance claim. Nothing queued. Three
observations recorded, one of which is about the tool rather than the
ecosystem.**

**Never build:**

- A DoDAF/UAF pack, mode or model-type recognizer (N1) — an OV-6c is a
  sequence diagram and already parses as one; a recognizer adds a label
  and no capability.
- Any DoDAF or UAF conformance, support or alignment claim (N2) — DoDAF
  conformance concerns the DM2 and model content, neither of which
  pumllint checks.
- A UAF profile, or an integration justified by the grid-column
  vocabulary overlap (N3) — fourth instance of this refusal.
- A "DoDAF profile" of the rule set (N5) — the default profile is
  already correct; a branded alias is N1 with a config key.

**Recorded, not queued:**

1. **The OV-6c result as the series' high-water mark** (§8.3, F2) — a
   framework-required artefact class, a notation the framework explicitly
   permits, the deepest pack applying correctly, 99.88 and exit 0. Cite
   it **with §9 attached**: the sample was written to be well-formed and
   no user has been demonstrated.
2. **The TOGAF pairing** (§5.2) — 0 of 32 versus 3 of 52 on the sequence
   pack, one turn apart. Frameworks differ sharply in whether they ask
   for time-ordered interaction models, and pumllint suits the ones that
   do. Neither note could say this alone.
3. **The `codegen` profile mismatch** (§8.4, F3) — the first
   *configuration* finding in fifteen evaluations. The same file scores
   99.88 by default and 52.4 with four blockers under `codegen`, and the
   blockers are wrong for a narrative event trace. Not a rule defect and
   not a DoDAF feature; at most a documentation note that `codegen`
   encodes an assumption about the diagram's destiny. Parked on the
   demand bar.
4. **"Fit-for-Purpose" as the first stated reason** (§5.4) for the
   no-grader pattern, recorded beside 42030's abstention and TOGAF's
   aggregation-elsewhere. It argues against a fixed *content* checklist,
   which is a narrower target than pumllint's coherence rules — so it
   sharpens the question without closing it.

**Re-litigate on:**

- **Any evidence that a DoD program office, contractor or UAF user
  renders event traces in PlantUML** — the single trigger that would turn
  §8.3 from a ceiling measurement into an audience, and the only one a
  user can fire.
- **A real OV-6c to measure**, from anywhere. §8.6's gap: this note
  measured a clean sample, and the interesting question is what the
  messy ones score.
- An adopter hitting §8.4 — running `codegen` over narrative sequence
  diagrams and reporting the blockers as wrong — which would move F3 from
  parked to a documentation task.
- **Not** on DoDAF or UAF adoption. Both are large and have been for
  years without producing a description linter, and §5.4 suggests the
  reason is doctrinal rather than accidental.

## Related reading

- [The TOGAF / ADM ecosystem, evaluated](togaf-adm-ecosystem-evaluation.md)
  — the immediately preceding note and the other half of §5.2's pairing;
  its corrected "no grader" criterion is the one §5.4 uses.
- [The Capella / Arcadia ecosystem, evaluated](capella-arcadia-ecosystem-evaluation.md)
  — the previous best artefact fit, which failed on reachability where
  this one does not.
- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — quotes UAF twice from the standard; §5.5 completes its access arc.
- [The SysML ecosystem, evaluated](sysml-ecosystem-evaluation.md) — UAF
  is a UML/SysML profile, so that note's claim-language findings govern
  N2 here.
- [ROADMAP.md](../ROADMAP.md) — the demand bar that decides F2 and F3,
  and the claim-language discipline behind N2.
