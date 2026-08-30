# The D2 ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `5b4a5a0` (v0.29.0). The
question as posed: investigate the D2 ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Seventh in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, this).*

**Verdict up front: no — and for the first time in the series the linting
niche is *open*, so the refusal rests on ground none of the six
predecessors used. Three things carry it. (1) D2 is not a UML notation at
all: it is a general graph language of shapes, connections and
containers, whose documented shape vocabulary is presentational
(`rectangle, square, page, parallelogram, document, cylinder, queue,
package, step, callout, stored_data, person, diamond, oval, circle,
hexagon, cloud, c4-person`) rather than a set of typed diagram forms.
Sequence is the one pumllint pack with a verified counterpart; four have
none. (2) The niche is unoccupied but **claimed by upstream** — D2's own
roadmap reads, verbatim, *"Build a configurable linter."* Building it for
them, in a language this project would have to parse from scratch, is the
SonarQube-plugin lesson against a maintainer who has said they intend to
do it. (3) D2 already ships more language tooling than PlantUML does —
`d2 fmt`, `d2 validate`, and a parser that emits *multiple* human-readable
errors from one broken program — so the gap that motivates this tool for
PlantUML is narrower there before any semantic rule exists.**

> **GROUND (3) CORRECTED 2026-08-30 by
> [the D2 re-examination](d2-ecosystem-reexamined.md), which ran D2's
> compiler.** The *premise* holds — multiple errors from one broken
> program is confirmed, and the shape vocabulary is closed and enforced.
> **The conclusion does not.** Measured, D2's compiler rejects syntax
> errors and unknown shape keywords and **accepts every semantic defect
> tested**: self-loop, duplicate connection, unlabelled connection. On
> the equivalent PlantUML pumllint reports **SEQ006** and **SEQ005**. So
> what D2 ships more of is *syntax and vocabulary* tooling; **the
> semantic gap is not narrower there, it is the same size.**
> **The refusal stands on grounds (1) and (2)** — which this correction
> does not touch — and **ground (2) is now load-bearing, and it is the
> fragile one**, since it rests on upstream's stated intention to build a
> linter.

**The measurement is the sharpest in the series, and it is not about D2.
D2's connection syntax — `a -> b: label` — is character-identical to
PlantUML's message syntax, and D2 auto-creates actors on first reference
exactly as PlantUML auto-creates lifelines. Measured: a D2 sequence
diagram wrapped in `@startuml…@enduml` is typed `sequence` and scored
**Level 4 (Precise), 99.17/100, with one cosmetic finding (GEN001, no
title) and exit 0**. Compare the Mermaid equivalent measured yesterday —
7 findings, 2 critical, exit 1. Mermaid's foreign syntax was loud and
wrong; D2's is quiet and wrong, which is worse.**

**And the reason it is quiet is not a defect. `SEQ001` carries an option
`only_if_any_declared`, default `True`, documented in the rule itself as
*"stay quiet in files that declare nothing at all, so quick ad-hoc
sketches aren't punished."* A D2 file parses to zero PlantUML
declarations, so it reads as an ad-hoc first-use sketch and the one rule
that would have objected withdraws by design. A deliberate kindness,
correct for its intended input, is exactly what removes the last signal
on unintended input. That interaction is worth recording precisely
because nothing in it is broken.**

**The cleanest way to state what this evaluation found: the rules are
right and the reach is wrong. D2 shares PlantUML's auto-creation hazard
exactly — its own documentation says *"You don't have to explicitly define
actors… but if you want to define a specific order, you should"* — which
is SEQ001's rationale almost word for word, arrived at independently by a
language that has never heard of this tool. SEQ001's reasoning transfers
perfectly to D2. SEQ001's implementation cannot see a `.d2` file. Eighth
ecosystem, and still no grader anywhere.**

*Bounds. Every pumllint claim was executed at `5b4a5a0` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
External claims were read on 2026-08-27 from `d2lang.com` and web-search
summaries, with URLs given. **No D2 tool was executed** — `d2` was not
installed, so nothing here reports what `d2 validate` actually accepts or
rejects; its scope is characterized from documentation. Per this
session's repository scope **no GitHub repository was read**, so D2's
release cadence, issue activity and the linter roadmap item's status are
uninspected. D2's type surface is **bounded, not exact**: the shape list
above is verbatim from `/tour/shapes` and `shape: sequence_diagram` is
verified from `/tour/sequence-diagrams`, but D2 documents further special
object types on pages not fetched, so "one of five packs transfers" is a
floor.*

## 0. Why this ran, and what it is not

No prior D2 record exists — this is a first look. But there is a naming
collision to clear before anything else, because it will otherwise mislead
a future reader of this repository.

**"D2" is already taken here, and means something entirely different.**
`EVIDENCE.md` uses `D2` as a **pre-registered evidence-wave hypothesis
label**: *"**D2 (generator robustness):** the below-composite-40 cliff
reproduces under a weaker generator (`claude-haiku-4-5`), plausibly with a
larger drop"*, resolved a few lines later as *"**D2 — confirmed.**"* It is
one of a lettered series of deepening hypotheses and has no connection to
the diagramming language. `docs/aschenbrenner-mapping-evaluation.md` cites
that same label. Anyone grepping this repository for "D2" will hit the
evidence wave first and this note second; both are correctly named and
neither should be renamed. Recorded so the collision is deliberate rather
than discovered.

Nothing here is queued. §10 records what would have to become true.

## 1. The ecosystem

### 1.1 What D2 is

D2 — *"a diagram scripting language that turns text to diagrams. It stands
for Declarative Diagramming"* — was open-sourced in November 2022 by
Terrastruct, and is now *"an independent open-source project fiscally
sponsored by Hack Club"*, licensed **MPL-2.0**, with its source at
`d2lang/d2` (moved from `terrastruct/d2`).

The structural fact that decides most of this evaluation: **D2 is a
general graph language, not a family of typed diagram notations.** Its
documentation presents three primitives — shapes, connections, containers
— and its shape vocabulary is about *appearance*:

```
rectangle, square, page, parallelogram, document, cylinder, queue,
package, step, callout, stored_data, person, diamond, oval, circle,
hexagon, cloud, c4-person
```

Those are presentational choices, not semantic types. There is no class
diagram, state machine, use case or activity diagram as a first-class
form with its own rules. Users combine primitives to make whatever
diagram they want — which is the opposite of the assumption every
pumllint rule pack rests on, namely that a diagram *has a type* and the
type determines what is checkable.

The one exception verified here is sequence: setting
`shape: sequence_diagram` on an object switches on sequence semantics,
and even then *"D2 uses its standard graph syntax throughout"*.

### 1.2 The tooling — more than PlantUML has, and a linter on the roadmap

D2's language tooling is unusually strong for a diagram language, and it
is worth being precise about what exists versus what is promised:

| | Ships today | Status |
|---|---|---|
| `d2 fmt` | autoformatter | shipped |
| `d2 validate` | syntax validation | shipped (**scope characterized, not executed**) |
| Multi-error parsing | *"being able to parse broken syntax and output multiple, human-readable error messages"* | shipped, and called out as a deliberate design goal |
| Editor integrations | syntax highlighting; VSCode/Vim/Obsidian/Slack/Discord plugins | shipped |
| **Configurable linter** | — | **roadmap: *"Build a configurable linter."*** |
| LSP | *"call out to LSP functions to refactor"* | roadmap |
| **Graded verdict** | — | **absent, and not on the roadmap** |

Two readings follow.

**The syntax floor is already higher than PlantUML's.** PlantUML's
`--check-syntax` is a pass/fail gate; D2 ships a formatter, a validator
and a parser designed to report several errors at once. The "PlantUML
renders inconsistent diagrams without complaint" premise that founds this
project is a statement about PlantUML, and it travels to D2 only in the
*semantic* half — the syntactic half is better served there.

**The semantic niche is open and spoken for.** This is the first of seven
ecosystems where no third-party linter was found — and also the first
where the language's own maintainers have written down that they intend
to build one.

### 1.3 Where D2 sits among the substitutes

D2 is the third diagram-as-code substitute in this series, after Mermaid
and PlantUML itself; the three are routinely compared as a set. Its
differentiators are presentational — layout engines (dagre, ELK, and
Terrastruct's proprietary TALA) and visual polish — rather than semantic.
Nothing found suggests D2 competes on modelling rigour; it competes on
how the picture looks.

## 2. The seam

```
   .puml   ──► PlantUML renderer   ──► picture     ← pumllint gates here
   .mmd    ──► mermaid.js          ──► picture     ← mermaid-lint gates here
   .d2     ──► d2 (fmt/validate)   ──► picture     ← nobody gates semantically;
                                                     upstream says it will
```

`PUML_EXTENSIONS` is `(.puml, .plantuml, .iuml, .wsd)`. `.d2` is outside
it, and the scope guard reports that honestly (§8.1). The interesting
seam is not the file extension — it is the *syntax*, which overlaps far
more than Mermaid's does (§8.2).

## 3. Overlap

### 3.1 Types — one of five, and that is a floor

| pumllint pack | D2 counterpart |
|---|---|
| sequence (11 base + 9 codegen) | `shape: sequence_diagram` — **verified**, and it uses D2's ordinary graph syntax |
| class (5) | not a first-class D2 form in the pages read (**not checked** — see Bounds) |
| state (3) | none found |
| use case (3) | none found |
| activity (6) | none found |

Mermaid transferred three of five and that was already thin. D2 transfers
one verified, and the four that do not are not "missing features" — they
are categories D2 deliberately does not have, because typed diagram forms
are not what a general graph language provides.

The corollary matters more than the count: **most D2 diagrams are not
diagrams pumllint has any rules for.** An architecture sketch of shapes,
connections and containers has no pumllint pack, in the same way a
Mermaid Gantt chart or a mindmap has none. A D2 pack would mostly be new
rules for a new kind of artefact, not existing rules against a second
syntax.

### 3.2 Rules — one exact correspondence, and it is the interesting one

D2 shares PlantUML's defining hazard. Its sequence documentation states:
*"You don't have to explicitly define actors (except when they first
appear in a group), but if you want to define a specific order, you
should."* Actors materialize on first reference.

That is precisely SEQ001's rationale, which reads: *"PlantUML silently
auto-creates lifelines on first mention, so a typo (`Custmer -> Bank`)
renders a phantom participant instead of failing. Requiring explicit
declaration turns typos into lint errors."* Two languages, one hazard,
and D2's own documentation independently recommending the same remedy
(declare explicitly) without framing it as correctness.

So the rule concept transfers exactly — and unlike `bpmnlint` and
`mermaid-lint`, where an *implemented* rule converged, here it is the
*hazard* that converged and nobody has implemented anything. That is the
open niche, seen from the rule side.

## 4. Boundaries

1. **Typed notation vs general graph.** Every pumllint pack assumes a
   diagram type that determines what is checkable. D2's primitives make
   that assumption false for most of its diagrams. §3.1.
2. **Syntax floor.** D2 ships formatting, validation and multi-error
   parsing; PlantUML does not. The founding premise travels only in its
   semantic half. §1.2.
3. **Open but claimed.** The semantic niche is empty and upstream has
   written down that it intends to fill it. That is a different boundary
   from Mermaid's (occupied) and from C4's (open and unclaimed).
4. **Extension-bound discovery.** `.d2` is never discovered, and the
   warning says so — but the *syntax* overlap defeats that protection the
   moment a file is wrapped. §8.2.

## 5. Sense — four true things

**S1. The measurement is the series' sharpest, and it indicts this tool
rather than D2.** Level 4 "Precise", 99.17/100, one cosmetic finding, on a
file written in a different language. Nothing else measured across seven
ecosystems produced a confident wrong verdict this quiet.

**S2. The silence is a designed behaviour meeting an undesigned input.**
`SEQ001`'s `only_if_any_declared` default exists so ad-hoc sketches are
not punished — a good decision, still a good decision. It happens to be
the exact condition a foreign-syntax file satisfies. Recording this
correctly matters: the lesson is not "fix SEQ001", it is that the
type-fallback class has a second silencing mechanism nobody had noticed,
and it is a rule option rather than a scoring cap.

**S3. The one thing that transfers is a hazard, not a rule.** D2
independently reproduced PlantUML's auto-creation behaviour *and*
independently recommends explicit declaration. SEQ001 is right about
something true of text diagram languages generally, not just PlantUML —
which is the strongest statement of that rule's validity yet available,
and it comes from a language that has no linter to express it.

**S4. Eighth ecosystem, no grader — and this time not even a candidate.**
D2's roadmap names a linter; it does not name a score, level, or maturity
model. Seven validators across seven ecosystems check without grading,
and the eighth's stated plan is to join them.

## 6. Nonsense — five moves to refuse

**N1. A D2 pack. Refused on the artefact.** One verified pack of five
transfers, and most D2 diagrams are general graphs with no pumllint rules
at all. This is not "the same rules, second syntax" — it is a new artefact
class needing new rules, which is a second product.

**N2. Building the linter D2's roadmap claims. Refused.** Building a
third-party checker for a language whose maintainers have written *"Build
a configurable linter"* into their own plan is the SonarQube-plugin
lesson with the vendor's intent on the record. If it ships, the niche
closes; if it does not, the reason will be demand, which is the same
signal this project would need anyway.

**N3. Treating the syntax collision as a reason to support D2. Refused —
it is a reason to be careful, not to expand.** §8.2 is a defect in this
tool's honesty on foreign input. The fix, if any, is to stop scoring
unrecognized dialects confidently — not to start parsing D2.

**N4. Reading D2's tooling as validation of the category. Refused.**
`d2 fmt` and `d2 validate` are syntax and style. They corroborate that
text-diagram languages benefit from tooling; they say nothing about
demand for *semantic* gating, which is the thing this project sells and
which no D2 user has been observed asking for.

**N5. Any repositioning to "diagram linter". Refused, as in the Mermaid
note.** Three substitute notations now, one supported. The claim-language
discipline audited clean against UML and holds here.

## 7. Fit — graded

### F1 — a D2 parser and rule pack. **No.** N1, N2.

First refusal in the series where the niche is *open*. Recorded plainly so
the openness is not later mistaken for an opportunity: the reasons are the
artefact's shape and upstream's stated intent, neither of which an
adopter's interest would change.

### F2 — the syntax-collision honesty problem. **The one real finding, and it is not a D2 item.** §8.2.

It belongs to the type-fallback class recorded in the ArchiMate entry —
but adds a **second silencing mechanism** that class did not have. The
existing candidate is about typing confidence and cap C6; this case
passes both and is silenced instead by a *rule option*
(`only_if_any_declared`). Any fix for the class should be checked against
this case, or it will fix the loud instances and leave the quietest one.

### F3 — Mermaid-style "occupied niche" reasoning. **Does not apply, and saying so is the point.**

Mermaid was refused because someone had built it. D2 cannot be refused on
that ground and does not need to be. Two different ecosystems, two
different reasons, same answer — recorded separately so neither argument
is used where it does not fit.

### F4 — the grading layer. **Unoccupied for the eighth time; unchanged.**

### Fit against declared constraints

| Declared constraint | Where the D2 fits land |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails on the artefact before a dependency question. |
| **Deterministic product path, no LLM** | Not reached. |
| **Golden score contract** | Material only for F2, which is a scoring change and inherits the existing candidate's re-freeze requirement. |
| **Demand-driven / Arc E bar** | F1 fails on **merit**, not demand — an adopter asking would not fix the type mismatch or unclaim upstream's roadmap. |
| **Licence posture** (GPL-3.0-or-later; no EPL, no AGPL) | **Passes** — D2 is MPL-2.0, and nothing here proposes vendoring. Recorded because it was checked. |
| **Claim language is settled** | N5 holds; no correction needed. |

## 8. Gap — measured

### 8.1 The extension boundary is honest

```
$ python3 -m pumllint .                      # a directory of .d2 files
warning: no PlantUML files found in . (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint arch.d2
warning: 1 file(s) contained no @startuml block and were not checked: arch.d2
✔ No issues found.                                                    (exit 0)
```

Both forms of the "nothing was checked" contract, unchanged.

### 8.2 The syntax collision — the quietest wrong verdict measured

D2's connections are written `a -> b: label`. PlantUML's messages are
written `a -> b: label`. They are the same characters. Wrapping a D2
sequence diagram in PlantUML delimiters — the mistake a user migrating
between text diagram languages would actually make:

```
@startuml d2wrapped
shape: sequence_diagram
ui: Checkout UI
os: OrderService
ui -> os: placeOrder(cart)
os -> db: persist
os -> ui: orderId
@enduml
```

```
$ python3 -m pumllint wrapped.puml
wrapped.puml:1: [GEN001/minor] Diagram has no title
✖ 1 issue(s): 1 minor                                                 (exit 0)
  type='sequence'  level=4 (Precise)  score=99.17  elements=6
```

Three D2 declarations (`shape:`, `ui:`, `os:`) are dropped as
unrecognized; three connections parse as messages; their six endpoints and
messages make `elementCount` 6. The verdict is **Precise, 99.17**, and the
only complaint is a missing title.

**Against the Mermaid equivalent measured yesterday** — 7 findings, 2
critical, exit 1 — this is strictly worse. Mermaid's alias syntax binds
the opposite way from PlantUML's, so the collision produced noise that a
user would investigate. D2's syntax agrees with PlantUML's closely enough
to produce silence.

**Why SEQ001 does not fire, precisely.** From the rule's own docstring
(`pumllint/rules/sequence/participants.py:19-20`):

> Option `only_if_any_declared` (default True): stay quiet in files that
> declare nothing at all, so quick ad-hoc sketches aren't punished.

A D2 file yields zero PlantUML declarations, so `declared` is empty and
the rule returns before examining anything. The behaviour is correct for
the input it was designed for and produces silence on input it was not.
**This is not a defect in SEQ001** and should not be recorded as one.

What it *is*: a second silencing mechanism for the type-fallback defect
class. The five instances recorded so far (C4 raw arrows, component +
`database`, native ArchiMate, BPMN sprites, nine UML types) all escape cap
C6 by reaching three elements and then report Level 3 or 4 *with*
findings. This one reaches Level 4 with essentially none, because a rule
option — not a scoring cap — withdrew the last objection. A fix aimed only
at typing confidence would leave it exactly as it is.

### 8.3 What was not measured

`d2` was not installed, so nothing here reports what `d2 validate`
accepts, whether it catches the undeclared-actor case, or how its
multi-error output reads. No D2 corpus was examined, so no claim is made
about how common the `shape: sequence_diagram` form is relative to general
graphs — which bears directly on §3.1's "one of five" being a floor.
Adoption relative to Mermaid and PlantUML is not measured here at all;
the Mermaid note's figures cover Mermaid only.

## 9. SWOT

Scope: *pumllint's position relative to D2*.

**Strengths (internal, favourable)**

- SEQ001's rationale independently corroborated by a second language's
  documented behaviour and its own advice (§3.2).
- Extension boundary honest (§8.1).
- Grading unoccupied for the eighth ecosystem, and absent from the one
  roadmap that names a linter.

**Weaknesses (internal, unfavourable)**

- The quietest wrong verdict measured anywhere in the series (§8.2), and
  the existing type-fallback candidate would not fix it.
- No reach into a third substitute notation whose syntax overlaps this
  tool's more closely than the second one did.

**Opportunities (external, favourable)**

- Honestly none. This is the second consecutive evaluation whose
  opportunity column is empty, and the first where that is because the
  artefact is the wrong shape rather than because someone got there first.

**Threats (external, unfavourable)**

- **The collision is invisible by construction.** A user who wraps D2 in
  `@startuml` gets a passing, confident verdict and no signal that
  anything was misread. Of everything in seven evaluations, this is the
  failure most likely to be believed.
- **If D2's linter ships with a graded verdict**, the eighth ecosystem
  becomes the first grader — and it would arrive in a language designed
  for good tooling, from maintainers who plan features before building
  them.

## 10. Decision, recorded candidates, triggers

**Decision: no D2 support of any kind. One candidate is recorded, and it
is a correction to an existing item rather than a new one.**

**Never build:**

- A D2 parser or rule pack (N1) — one verified pack of five transfers,
  and most D2 diagrams are general graphs with no rules in this catalog.
  Refused on **merit**, not demand.
- A third-party D2 linter (N2) — upstream's roadmap says *"Build a
  configurable linter."*
- Any repositioning to "diagram linter" (N5).

**Recorded, not queued:**

1. **Amend the type-fallback candidate to cover the silent case.** The
   ArchiMate entry's candidate 1 addresses typing confidence and cap C6.
   §8.2 passes both and is silenced instead by `SEQ001`'s
   `only_if_any_declared` default — a correct option meeting foreign
   input. Any fix for the class must be validated against a
   zero-declaration foreign-syntax file, or it will repair the five loud
   instances and leave the quietest one reporting **Level 4 (Precise),
   99.17**. **Not a defect in SEQ001, and no change to that rule is
   proposed.** Maintainer self-demand; scoring change; inherits the
   existing candidate's decision and golden re-freeze.
2. **The naming-collision note** (§0) — "D2" in this repository already
   means an EVIDENCE.md wave hypothesis. Both names are correct; neither
   should change; the collision is recorded so it is deliberate.

**Re-litigate on:**

- **D2 shipping its configurable linter with a graded verdict** — which
  would end the eight-ecosystem streak from a language whose tooling
  culture is unusually strong, and is the single event that would most
  change the positioning claim.
- An adopter with PlantUML *and* D2 in one repository asking for one gate
  over both — the only shape in which a D2 recognizer serves an existing
  user; note it would still face the one-of-five type mismatch.
- Evidence that `shape: sequence_diagram` dominates real D2 usage, which
  would raise §3.1's floor and is currently unmeasured.

## Related reading

- [The Mermaid ecosystem, evaluated](mermaid-ecosystem-evaluation.md) —
  the other substitute notation; refused on an occupied niche, which is
  precisely the argument that does **not** apply here (F3), and the source
  of the wrapped-syntax comparison in §8.2.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — candidate 1 there is the type-fallback class this note amends.
- [The UML ecosystem, evaluated](uml-ecosystem-evaluation.md) — the
  claim-language audit N5 relies on.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  occupied-niche ground, for contrast with an open one.
- [EVIDENCE.md](../EVIDENCE.md) — the *other* D2: the generator-robustness
  wave hypothesis (§0).
- [ROADMAP.md](../ROADMAP.md) — the Arc E bar and the licence posture
  checked in §7.
