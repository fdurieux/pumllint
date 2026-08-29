# The Structurizr DSL viewpoints ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `1d08d02` (v0.30.0).
Twenty-first in the series, and the **third narrowing return in three
turns** — ArchiMate viewpoints (19th), C4 viewpoints/notation (20th),
this. The Structurizr DSL *ecosystem* was re-examined eighth
(2026-08-27); this note asks what that one did not, about its **views**.*

**Verdict up front: no — the eighth note's settlement is unchanged
(Structurizr is a *producer* of the artefact pumllint gates, not a
support candidate). The contribution is a correction, and it is to my own
reasoning in the two notes immediately before this one.**

## The correction

The ArchiMate viewpoints note recorded, as a general observation:

> **Viewpoint-shaped mechanisms are guidance, not contracts.**

and the C4 viewpoints note repeated it as a "second instance", with the
gloss that this is *"the general reason a third-party linter adjudicating
a viewpoint would be inventing an obligation"*.

**That was generalized from n = 2, and n = 3 refutes it.** Structurizr's
views are declared with a **typed scope argument** — `container <software
system>`, `component <container>` — and the C4 evaluation (second in the
series, 2026-08-27) already recorded Structurizr as preventing
abstraction mixing **"by construction"**, quoting *"components can't be
added to a container diagram"*. **I cited that note in both viewpoint
notes and did not notice the row cut against the generalization I was
making.**

**The distinction that actually holds is derived views versus drawn
views**, and it is not about viewpoints at all:

| Ecosystem | How a view gets its content | Conformance |
|---|---|---|
| **ArchiMate** (in Archi) | **drawn** — elements dragged onto a canvas; the viewpoint is a filter and a label over what you drew | a live question, answered **advisorily** (palette filter, ghosting, opt-in warning) |
| **C4** (the model) | no tool, no model — four levels of zoom as convention | **undefined** |
| **Structurizr DSL** | **derived** — `container softwareSystem { include * }`; the tool computes the content from a typed model and a scope | **not enforced because it cannot be violated** |

Where a view is *derived from a typed model by scope*, you cannot draw a
wrong view — only scope one. Conformance is not "unenforced"; it is
**vacuous**. Where a view is *drawn*, conformance is a real question, and
ArchiMate answers it with graded discouragement.

**The practical conclusion is unchanged and now has two different
reasons.** For ArchiMate and C4, a linter adjudicating viewpoints would
be inventing an obligation. For Structurizr, it would be **checking a
property that cannot fail** — which is a different mistake, and a worse
use of a rule slot. §5.1.

**The measurement is small and has a wrinkle worth reporting.** Two
Structurizr exports of *different view types* — a container view and a
component view — are indistinguishable: `sequence`, **Level 3, 84.58, 3
elements, identical findings**. But the **view key does survive the
export**, in the documented `@startuml(id=…)` construct, and **pumllint
already reads it**:

| | name captured | GEN002 | score |
|---|---|---|---|
| `@startuml` | `None` | fires | 84.58 |
| `@startuml(id=Containers)` | **`'(id=Containers)'`** | **satisfied** | **85.00** |

The one trace of a view's identity that survives export is captured — and
captured **verbatim including the `(id=` wrapper**, because
`RE_STARTUML` (`parser/sequence.py:40`) takes everything after
`@startuml` as the name. §8.3.

*Bounds. **The export samples are reconstructed, not captured from a real
`structurizr-cli` run** — the CLI is not installed. This is the same
bound the eighth note carried for the same reason, and its samples were
reconstructed too, so figures here and there are **not directly
comparable**: my container-view sample scores 84.58 where that note's
static export scored 85.0, a difference in the samples, not in
behaviour. **Scope enforcement is only partly established**: the DSL
documentation states what each view type *includes by default*, and gives
verbatim permission rules for only two types — the `dynamic` view, where
*"scope determines permissible elements"*, and the `custom` view, where
*"Only custom elements are permitted to be included on a custom view"*.
Whether an explicit out-of-scope `include` on a container or component
view is an **error** rather than merely unusual is **not established from
the documentation read**, and §1.2 says so rather than assuming. All
pumllint claims were executed at `1d08d02` (v0.30.0) with default config
from a neutral working directory. Per session scope no GitHub repository
was read.*

## 0. What the eighth note settled, and is not restated

Structurizr DSL is **not a support candidate but a producer of the
artefact pumllint already gates**: `structurizr-cli export` emits
PlantUML in two dialects plus Mermaid, D2, DOT, Ilograph and
WebSequenceDiagrams. Three export shapes were measured — the C4 export
honest at Level 1, the static export mistyped at Level 3, and the
sequence export correctly typed at Level 4 while tripping GEN004 on every
participant because the exporter emits numeric identifiers.

Also on record: `inspect` is a documented CLI verb alongside `validate`,
making Structurizr the only ecosystem in the series shipping syntax
validation *and* a named rule set from one CLI; and the never-build
against **"a Structurizr-export recognizer or profile"**, which
"special-cases one producer among many, and encodes a third party's
output shape as a contract this project would have to track".

None of that is re-derived here, and this note adds no measurement to it.

## 1. The views

### 1.1 View types take a typed scope

The DSL's `views` block declares views by type, and most take a scope
argument that is an identifier **in the model**:

| View type | Scope argument | Default content (documented) |
|---|---|---|
| `systemLandscape` | none | all people and software systems |
| `systemContext` | `<software system>` | the system in scope plus directly connected people/systems |
| `container` | `<software system>` | all containers within the system in scope, plus directly connected people/systems |
| `component` | `<container>` | all components within the container in scope, plus connected people/systems/containers of that system |
| `dynamic` | `<*\|software system\|container>` | **"scope determines permissible elements"** |
| `deployment` | `<*\|software system> <environment>` | deployment/infrastructure nodes and container instances in that environment |
| `filtered` | `<baseKey> <include\|exclude> <tags>` | derived from a base view |
| `custom` | — | **"Only custom elements are permitted to be included on a custom view"** |
| `image` | `<*\|element>` | an image |

The scope is not a label. `component webApplication` names a **container
identifier that must exist in the model**, and the view's content is
computed from it.

### 1.2 How strongly that is enforced — stated carefully

Two view types carry verbatim permission language (`dynamic`, `custom`,
above). For `container` and `component` the documentation states the
**default inclusion** rather than a prohibition, and **whether an
explicit out-of-scope `include` errors was not established** from the
pages read.

What *is* established, and is enough for §5.1: the content of these views
is **derived** — `include *` means "compute the members from the model and
the scope", not "here is a list I drew". The eighth note's own record of
Structurizr preventing abstraction mixing "by construction" is consistent
with that and predates this note.

## 2. The seam

The eighth note fixed it: producer → consumer. This note narrows it by one
step. **The view type and scope are inputs to the export and are not
outputs of it** — with one exception, the view key in `@startuml(id=…)`
(§8.3). Everything that made the view conformant happened before the
`.puml` existed.

## 3. Overlap

| Concern | pumllint | Structurizr views | Reading |
|---|---|---|---|
| View type / scope | no concept | typed, and an input to export | Invisible — **and harmlessly**, §5.1 |
| Abstraction mixing | invisible | **prevented by construction** (on record since the C4 note) | Cannot occur in an export |
| **View key** | `diagram.name`, GEN002 | survives as `@startuml(id=…)` | **The one trace, already read** — §8.3 |
| Exported styling | GEN003 fires | exporter emits `skinparam` blocks | Unownable findings — eighth note |
| Numeric identifiers | GEN004 fires | exporter emits them | Unownable findings — eighth note |
| Aggregate verdict | levels + composite | `inspect` reports per-finding | Twenty-first, no grader |

## 4. Boundaries

1. **Derived, not drawn** (§1.1) — the boundary that makes this ecosystem
   different from the two before it.
2. **The view type is an input** (§2) — it is consumed by the exporter,
   not emitted by it.
3. **The key is the exception** (§8.3), and it is already read.

## 5. Sense — four true things

### 5.1 The two-turn generalization was wrong, and its conclusion survives

§The correction. "Viewpoint-shaped mechanisms are guidance, not
contracts" held for the two ecosystems it was drawn from and does not
generalize. **Structurizr's views are derived from a typed model**, so
their conformance is not a matter of enforcement at all.

Two things follow, and the second is why this is worth a note rather than
an erratum:

- **The practical rule is unchanged.** Do not adjudicate viewpoint
  conformance. For ArchiMate and C4 because it would invent an
  obligation; for Structurizr because **the property cannot fail**, so a
  rule checking it would consume a slot to report a tautology.
- **The reason matters for anything built later.** A future reader who
  took "guidance, not contracts" as a fact about ecosystems would
  mis-predict Structurizr, and would mis-predict any other model-first
  tool. The predictor is **derived vs drawn**, and it is checkable from
  how a tool's views get their content.

### 5.2 The evidence was already in the record, and in my own citations

The C4 evaluation's occupancy table has carried the row *"Abstraction
mixing (Component in a container view) | prevented by construction"*
since 2026-08-27. Both viewpoint notes cite that evaluation. Neither
noticed.

That is worth recording plainly: **the series' failure mode is not
missing evidence but reading a cited note for the part that confirms the
line being written.** The narrowing-return format makes it likelier —
three consecutive notes returning to earlier subjects, each looking for
what its predecessor left out rather than for what its predecessor
already answered.

### 5.3 The view key is the one trace, and it is already read

§8.3. `@startuml(id=Containers)` is a documented Structurizr export
construct, and pumllint captures it as the diagram name — satisfying
GEN002. That is the *right* outcome (a named diagram is better than an
unnamed one) reached by a slightly *wrong* reading: the captured name is
`'(id=Containers)'`, wrapper and all.

**This is not a defect to fix.** `RE_STARTUML` treats everything after
`@startuml` as the name, which is correct for the general PlantUML case;
parsing Structurizr's `id=` syntax specifically is exactly the
**Structurizr-export recognizer the eighth note already refused** —
"special-cases one producer among many, and encodes a third party's
output shape as a contract this project would have to track". Recorded as
a fact about what the name field contains for one common producer, not as
a candidate.

### 5.4 Twenty-first ecosystem, no grader

In the corrected form, cited with the four-object tally rather than as a
count. Structurizr's `inspect` reports per-finding with configurable
severity across four levels and produces no aggregate — as the eighth
note recorded, and as the C4 note's *"three independently built
C4-capable validators … and not one of them grades"* already covered.

## 6. Nonsense — five moves to refuse

**N1. A view-type or scope-conformance rule over Structurizr exports.
Refused, and for the *new* reason.** The property cannot fail in a
derived view. A rule checking it would report a tautology on every
conformant export and could only ever fire on a hand-edited file — which
is not the population.

**N2. Parsing `@startuml(id=…)` as a Structurizr view key. Refused under
the eighth note's existing never-build** against a Structurizr-export
recognizer. §5.3.

**N3. Treating the identical container/component results as a new
invisibility finding. Refused.** It is the third measurement of the same
shape in three turns, and here it is *harmless* — which is the point, and
which makes it an observation about the ecosystem rather than a gap in
the tool.

**N4. Carrying "viewpoint-shaped mechanisms are guidance, not contracts"
forward. Refused — it is withdrawn.** §The correction. The replacement is
derived-vs-drawn, and it is offered as a predictor to be tested, not as
another generalization from three points.

**N5. Reading §1.2's uncertainty as settled either way.** Whether an
out-of-scope `include` on a container view errors is **not established**.
Nothing here depends on it, and nothing later should assume it.

## 7. Fit — graded

### F1 — a Structurizr view-aware rule or recognizer. **No.** N1, N2.

### F2 — the derived-vs-drawn predictor. **A correction and a tool for reading the next ecosystem; nothing to build.** §5.1.

### F3 — anything premised on the withdrawn generalization. **Withdrawn with it.** N4.

### Fit against declared constraints

| Declared constraint | Where this lands |
|---|---|
| **No producer-specific recognizers** (8th note) | **Decides N2.** |
| **Demand bar** | Not reached; nothing proposed. |
| **Golden score contract** | Untouched. |

## 8. Gap — measured

### 8.1 No discovery probe

Structurizr DSL's own `.dsl` files were measured in the eighth note. Ninth
note in the series with no §8.1 boundary measurement.

### 8.2 Two view types, indistinguishable

Reconstructed exports (see Bounds) of a **container** view of a software
system and a **component** view of a container inside it — different view
types, different scopes, same export shape:

```
container_view    type=sequence  Level 3  84.58  elements=3
component_view    type=sequence  Level 3  84.58  elements=3
                                        → identical findings
```

Both report GEN002 plus three GEN003 inline-skinparam findings — the
exporter-generated styling the eighth note recorded as unownable. The
only content distinguishing them is the `title` ("… - Containers" versus
"… - Web Application - Components"), read as opaque text.

**This is expected and, here, harmless**: both exports are conformant by
construction (§5.1), so there is nothing for the indistinguishability to
hide.

### 8.3 The view key survives, and is already read

With the documented `@startuml(id=…)` construct:

```
@startuml                          name=None                  GEN002 fires    84.58
@startuml(id=Containers)           name='(id=Containers)'     GEN002 quiet    85.00
@startuml(id=WebApplication-Components)
                                   name='(id=WebApplication-Components)'      85.00
```

The mechanism, verbatim:

```python
# pumllint/parser/sequence.py:40
RE_STARTUML = re.compile(r"^@startuml\s*(?P<name>\S.*)?$")
```

`\s*` matches the zero spaces before `(`, and `(?P<name>\S.*)` takes the
rest of the line — so the name is the whole parenthesised expression. A
Structurizr export therefore arrives with a **named** diagram whose name
is `(id=Containers)`.

Right outcome, slightly wrong reading, and **not a candidate** (§5.3, N2).

### 8.4 What was not measured

**No `structurizr-cli` run** — samples are reconstructions, as in the
eighth note, so their fidelity to real exporter bytes is characterized
rather than verified, and the scores are not comparable across the two
notes. **Whether an out-of-scope `include` errors** (§1.2). The
`dynamic`, `deployment`, `filtered` and `custom` view types were not
exported or probed. `inspect` was not run.

## 9. SWOT

**Strengths (pumllint, internal)**

- §8.3: the one surviving trace of a view's identity already lands in a
  field the tool reads and a rule already checks.
- Nothing here asks for a change, and the one tempting change is already
  refused by an existing never-build.

**Weaknesses (pumllint, internal)**

- §8.3's captured name includes the `(id=` wrapper — cosmetic, and fixing
  it is refused for good reasons, but it is what the field contains.
- Not a weakness of the tool but of the record: §5.2, a generalization
  published twice against evidence already cited.

**Opportunities (external)**

- None. The eighth note's settlement is unchanged.

**Threats (external)**

- None specific. The standing threat remains the FEAF/Gartner note's.

## 10. Decision, corrections, triggers

**Decision: the eighth note's settlement stands unchanged — Structurizr
is a producer, not a support candidate. Nothing queued, no new candidate,
no new defect. One correction to the record and two observations.**

**Correction to the record (the reason this note exists):**

**"Viewpoint-shaped mechanisms are guidance, not contracts" is
withdrawn.** Recorded in the ArchiMate viewpoints entry and repeated in
the C4 viewpoints entry as a "second instance", it was generalized from
two ecosystems and is refuted by the third: **Structurizr's views take a
typed scope argument and derive their content from the model**, and the
C4 evaluation has recorded Structurizr as preventing abstraction mixing
*"by construction"* since 2026-08-27 — a row both notes cited without
noticing it cut against them.

**The replacement is derived views versus drawn views**, offered as a
predictor to test rather than a law: where a view's content is *derived*
from a typed model by scope, conformance cannot be violated; where it is
*drawn*, conformance is a live question the ecosystem answers as it
chooses. **The practical rule is unchanged** — do not adjudicate
viewpoint conformance — but the reason differs by case, and for
Structurizr it is that the check would be a **tautology**, not an
invented obligation.

**Never build:**

- A view-type or scope-conformance rule over Structurizr exports (N1) —
  the property cannot fail in a derived view.
- Parsing `@startuml(id=…)` as a view key (N2) — the eighth note's
  **Structurizr-export recognizer** never-build covers it exactly.
- Anything premised on the withdrawn generalization (N4).

**Recorded, not queued:**

1. **The correction and its replacement predictor** (above, §5.1).
2. **The reading failure that produced it** (§5.2) — three consecutive
   narrowing returns, each reading its predecessor for what it left out
   rather than for what it already answered. Worth naming because the
   format invites it.
3. **`@startuml(id=…)` lands in `diagram.name` verbatim** (§8.3),
   wrapper included, satisfying GEN002 — a fact about what that field
   contains for one common producer, recorded so nobody re-derives it and
   nobody "fixes" it into a producer-specific recognizer.

**Re-litigate on:** the eighth note's triggers, unchanged. **Not** on
anything here — this note corrects a generalization and touches no
condition.

## Related reading

- [The Structurizr DSL ecosystem, re-examined](structurizr-dsl-ecosystem-evaluation.md)
  — the settlement this returns to, and the never-build that decides N2.
- [The ArchiMate viewpoints ecosystem, evaluated](archimate-viewpoints-ecosystem-evaluation.md)
  and [The C4 viewpoints / notation ecosystem, evaluated](c4-viewpoints-notation-evaluation.md)
  — the two notes whose shared generalization this one withdraws.
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — the
  occupancy table whose "prevented by construction" row was the
  counterexample all along.
- [The NAF / MODAF ecosystem, evaluated](naf-modaf-ecosystem-evaluation.md)
  — the other ecosystem whose conformance lives in a model rather than a
  picture; consistent with the replacement predictor.
- [ROADMAP.md](../ROADMAP.md) — the Structurizr settlement.
