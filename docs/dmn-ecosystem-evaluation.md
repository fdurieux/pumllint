# The DMN ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `a4d5f89` (v0.30.0).
Twenty-third in the series, and BPMN's sibling: the two OMG standards
have been paired in this repository's records since the 2026-08-11
external review proposed "BPMN 2.x XML and DMN/FEEL" as one carrier item.
BPMN was settled fourth and re-examined twenty-second. This is DMN's own
note.*

**Verdict up front: no — and on grounds that are *not* BPMN's. The
strongest of them is that this project already fenced DMN off from its
own best-looking evidence, in writing, before the evidence existed.**

**Five grounds. (1) *No artefact.* PlantUML documents 23 diagram types
and DMN is not among them; `.dmn` is OMG XML, never discovered, honestly
warned about. (2) *The payload is not a diagram.* OMG describes DMN as
"two tools for modeling decision-making: a graphical notation and an
expression language". Only the first half is the kind of thing every
previous note in this series was about. The half that carries the
decision logic is a table and a language. (3) *The properties that matter
are decidable, and belong to a solver.* Completeness, overlap under a hit
policy, subsumption, masked rules — these are static analysis over a
constraint space, not source linting. **Measured: a PlantUML `switch`
whose cases genuinely overlap and genuinely leave a gap scores Level 4
(Precise), 100/100, "No issues found".** (4) *The niche is occupied — by
analysers rather than linters.* `dmnlint` is real but vestigial: **two
rules, both about the requirements graph, and measured silent on a table
carrying both canonical defects**. The table work lives in `dmn-check`,
in vendor modelers, and in the research tooling. (5) *The one measured
result that looks like a DMN argument was pre-registered as not being
one.***

**Ground (5) is the reason to write this down.** This repository has
measured decision tables as a carrier — as markdown tables, in the
`stack_experiment` waves — and the result is emphatic. W1b (2026-08-11,
contract-bundle decomposition): the decision tables carry it at **+40.9 pp
pooled** add-one over A2, the largest of the four components with both
generators concordant; **the only component whose removal hurts** (+12.1
pp leave-one-out); and **removing each of the other three — spec prose,
OpenAPI, state model — *improved* pooled results by 10.6–21.2 pp.** Not
merely the best carrier in the bundle: on that suite, the only one that
helped.

That is the obvious opening argument for DMN, and W1B's pre-registration
refuses it twice before the fact:

> carrier-per-component fixed — "the decision tables win" licenses no
> claim about table *form* vs number *content* (W3b) and **none about DMN
> or any unmeasured carrier**

> the suite is hand-derived with `decision_table.md` as its normative
> source, and 5 of its 11 scenarios are constructed to be pinned by
> DT-only numerics — the oracle's composition gives the decision tables
> the largest sensitivity surface **by design**. … "the decision tables
> carry it" may never be quoted without this scoping.

**The strongest available argument for a DMN arm is an argument this
project's own charter discipline disarmed in advance** — once for
generalizing across carriers that were never measured, and once for the
result being partly an artefact of how the grading suite was built. There
is no need to relitigate it; there is a need to record that it holds.

*Bounds. Every pumllint claim was executed at `a4d5f89` with default
config on files outside the repository (no GEN006/GEN007 findings
appeared, so they stayed dormant). **`dmnlint` 1.0.0 was installed from
npm and executed**; its silence on the defective table was confirmed
against a probe that fires both of its rules, so it is a result and not a
misconfiguration. Per this session's repository scope **no GitHub
repository was read** — `dmn-check` is characterized from Maven Central
coordinates and a web-search summary of its own description, never from
its source, and no claim is made here about which validators it ships.
The Laurson–Maggi analysis tool and Trisotech's table analysis are read
from search summaries, not executed. **No DMN engine was run.** DMN spec
versions are from omg.org/spec/DMN and the hit policies from Camunda's
documentation, both read 2026-08-29; the PlantUML diagram-type count is
the language-specification index read the same day for the BPMN
re-examination, and DMN's absence is read off that enumeration rather
than searched for separately.*

## 0. Why this ran, and what the record already held

DMN entered this repository's record twice, both times attached to BPMN
and never on its own terms:

- **As a codegen carrier.** The 2026-08-11 external review recommended
  adding "BPMN 2.x XML and DMN/FEEL to the carrier experiment". That
  lineup was graded **hypothesis**, with "No wave touched BPMN/DMN/
  AsyncAPI" recorded against it.
- **As a platform item.** "BPMN/DMN carriers, cross-spec verifier,
  context compiler, coverage metric, domain benchmark" — recorded as
  staying "with the adopter programme — not this repository's scope".

The fourth note (BPMN) then mentioned DMN once more, in a table cell:
`bpmnlint` "(+ `dmnlint`)". That parenthetical is **true** — §3 verifies
it — and it turns out to be the most misleading true sentence in the
series, because it invites the reader to assume DMN's linting layer is
BPMN's linting layer with a different file extension. It is not.

Nothing here is queued. §9 records what would have to become true.

## 1. The ecosystem

### 1.1 The standard, and the shape of what it produces

DMN 1.5 is the current formal version (August 2024); 1.6 and 1.7 are in
process as betas (September 2024), over a lineage running 1.0 (2015), 1.1
(2016), 1.2 (2019), 1.3 (2021), 1.4 (2023). OMG's own scope description
is the sentence this whole evaluation turns on:

> two tools for modeling decision-making: a graphical notation and an
> expression language

The graphical notation is the **DRD** — decisions, input data, business
knowledge models, and the requirement edges between them. The expression
language is **FEEL**, and its best-known packaging is the **decision
table**, with a declared **hit policy** that says how multiple matching rules are
to be resolved. Camunda's engine documents five — UNIQUE (U), ANY (A),
FIRST (F), RULE ORDER (R), COLLECT (C) — of which UNIQUE is the strictest:
*"Only a single rule can be satisfied or no rule at all"*, and when more
than one matches, *"the Unique hit policy is violated"*. (The spec defines
further policies; only these five were verified here.)

**Twenty-two notes in this series have been about diagrams.** DMN is the
first standard evaluated where the diagram is the *index* and the
substance lives in a table of expressions the diagram merely points at. A
DRD with no decision logic under it is an empty filing system; the
decision logic is what anyone would want checked.

### 1.2 The tool layers

| Layer | Examples | Validation it ships |
|---|---|---|
| **Modeler** | `dmn-js` (17.10.2, updated 2026-08-25), Camunda Desktop/Web Modeler, Trisotech, Signavio | Editing; vendor table analysis (Trisotech: "Method and Style Decision Table Analysis") |
| **Linter** | **`dmnlint`** 1.0.0 | **Two rules**, both DRD-graph. §3 |
| **Static analyser** | **`dmn-check`** (`de.redsix`, 1.3.1, 2024-08-02) — seven Maven artefacts including `dmn-check-core` and `dmn-check-validators`, with Maven and Gradle plugins | Described as performing "static analyses on Decision Model Notation (DMN) files to detect bugs" |
| **Research** | Laurson & Maggi's `dmn-js` extension (BPM 2016 demo) | "detection of overlapping rules, detection of missing rules and simplification of decision tables via rule merging" |
| **Engine** | Camunda 8, Drools/KIE, jDMN | Evaluation; deploy-time validation |
| **Adjacent** | `bpmnlint-plugin-camunda-compat` | Lints the **BPMN side** of a DMN call (the business-rule-task binding), not the table |

**Two version numbers tell the story.** `dmn-js`, the editor, is at
**17.10.2**, updated four days before this note. `dmnlint`, the linter,
is at **1.0.0** — with four published versions in total: 0.1.0
(2019-12-12), 0.1.1 (2019-12-14), 0.2.0 (2020-03-30), then a **six-year
gap** to 1.0.0 (2026-05-20). The editor is alive. The linter is a
placeholder.

That is not neglect. It is where the work went.

## 2. The structural fact: the interesting properties are decidable

A decision table is a finite set of rules over a finite set of typed
inputs. Given the table, the questions practitioners actually ask have
**algorithmic answers**:

- **Completeness** — is every combination of input values matched by some
  rule? (Are there gaps?)
- **Consistency** — under hit policy UNIQUE, does any input combination
  match more than one rule? (Are there overlaps?)
- **Subsumption / masking** — is some rule shadowed by an earlier one and
  therefore dead?
- **Simplification** — can rules be merged without changing the function?

These are constraint problems over interval and enumeration domains. They
are not pattern-matching over source text, and they do not degrade
gracefully: a "mostly complete" answer is not useful, and a heuristic
that reports overlaps it cannot prove is worse than no report.

**That is why the DMN ecosystem's validation is shaped as it is.** The
tool that holds the parsed table — the modeler, the analyser, the engine
— can run the solver. A linter reading source text cannot, and `dmnlint`
correspondingly does not try.

It is also the cleanest statement of what this project is. pumllint reads
PlantUML source and reports properties of that source. Every one of its
51 rules is decidable from the text without solving anything about the
domain the text describes. **DMN's core question is a question about the
domain.** The boundary is not a matter of effort.

## 3. Overlap — measured, and the measurement is a negative

The fourth note's convergence with `bpmnlint` was this series' strongest
external validation. The obvious expectation is that DMN's sibling linter
supplies a second one. **It does not, and the measurement is worth having
precisely because the expectation was reasonable.**

`dmnlint` 1.0.0's entire catalogue:

```
$ ls node_modules/dmnlint/rules/
helper.js   label-required.js   no-duplicate-requirements.js
```

Two rules. `label-required` is the same principle as `bpmnlint`'s and as
this project's SEQ005/STA003/CLS003. `no-duplicate-requirements` is a
DRD-graph property — the same edge declared twice. **Neither touches a
decision table.**

Executed against a table carrying both canonical DMN defects — an
overlap illegal under its own declared hit policy (rules 2 and 3 both
match `[400..500]` under `hitPolicy="UNIQUE"`) and a gap (nothing matches
`> 1000`):

```
$ npx dmnlint discount.dmn
                                                                      (exit 0)
```

Silent. Nothing reported, exit 0.

**Confirmed as a result rather than a misconfiguration** by a probe that
fires both rules — a decision with no name and a duplicated requirement
edge:

```
$ npx dmnlint probe.dmn
  Unnamed  error  Element is missing label/name    label-required
  Unnamed  error  Duplicate outgoing requirements  no-duplicate-requirements
  Total    error  Duplicate incoming requirements  no-duplicate-requirements

✖ 3 problems (3 errors, 0 warnings)                                   (exit 1)
```

The harness is wired; the table is simply outside what `dmnlint` is for.

**The reading.** BPMN's linting niche is occupied by a mature linter,
which was ground (2) of that note's refusal. DMN's is *not* — and that is
not an opening, because the work that would justify a DMN linter has
been done one layer over, by `dmn-check` and the modelers, where the
solver can live. **An unoccupied niche adjacent to a well-occupied one is
evidence about where the work belongs, not an invitation.**

## 4. Gap — measured

### 4.1 The boundary behaves honestly

```
$ python3 -m pumllint discount.dmn
warning: 1 file(s) contained no @startuml block and were not checked: discount.dmn — pumllint lints @startuml…@enduml sources; @startmindmap / @startjson / @startsalt / @startgantt blocks are not linted
✔ No issues found.                                                    (exit 0)
```

`.dmn` is outside `PUML_EXTENSIONS`; the warning says so and the exit code
does not move. No coverage is implied that does not exist.

### 4.2 A tenth instance of the type-fallback defect class

A DRD drawn the only way PlantUML affords — `rectangle` declarations for
decisions and input data, plain arrows for requirement edges:

```
  diagramType='sequence'  level=4 (Precise)  score=90.0  elementCount=8
```

No recognized type marker, undecorated arrows, endpoints materialize as
implicit lifelines, cap C6 escaped. **Instance 10** in the corrected
enumeration (Linked.Archi 1, C4 2, ArchiMate 3, BPMN 4, UML 5, D2 6,
Structurizr 7, Ilograph 8, Graphviz 9, DMN 10). No new candidate — the
ArchiMate note's candidate 1 covers it, and this is recorded so the
instance count is not re-derived.

### 4.3 The decision table is invisible, in both places a person would put it

The substantive half of DMN has no PlantUML form. What a team would
actually do is paste the table into the diagram as text. There are two
natural places, and **both are byte-identical to not pasting it at all.**

The same activity diagram, three ways: no table; the table in a
`legend`; the table in a `note`.

```
flow_plain   type=activity level=4 score=100.0 elements=7
flow_table   type=activity level=4 score=100.0 elements=7   (legend)
flow_note    type=activity level=4 score=100.0 elements=7   (note)
```

Full `score -f json` reports compared with paths normalized: **identical
in both pairs.** A three-rule decision table with an overlap and a gap
changes nothing about the score, the level, the dimensions, the element
count or the findings.

This is by design, and the source says so in both cases. Legends:

```python
# Legend blocks are display furniture: swallow until 'endlegend' so
# body text can never parse as live messages or participants.
```
(`parser/sequence.py`)

And model content generally:

```python
"""IDs this diagram references → line of the first carrying text.

Exactly GEN007's haystacks: the prose directives (title/header/footer/
caption/notes) plus the ``@startuml`` name. Message labels and other
model content are deliberately not carriers — same as the rule.
"""
```
(`trace.py`)

**DMN's payload lands exactly where this project has deliberately
decided not to look.** That is the correct decision — a linter that
started parsing legend bodies as model content would be inventing a
notation — and it is also the reason there is nothing here to build.

### 4.4 But the two carriers are *not* equally invisible

Identical for scoring; **different for traceability**, and this appears
to be the first time the series has measured it.

The same table, carrying the same three rule IDs, once in a `note` and
once in a `legend`:

```
$ pumllint trace trace_note.puml --pattern 'DMN-R\d+' --requirements reqs.txt
✔ Requirement coverage: 3/3 covered across 1 diagram(s)
DMN-R1  ← trace_note.puml [pricing]:5
DMN-R2  ← trace_note.puml [pricing]:5
DMN-R3  ← trace_note.puml [pricing]:5

$ pumllint trace trace_legend.puml --pattern 'DMN-R\d+' --requirements reqs.txt
Requirement coverage: 0/3 covered — 3 uncovered, 1 unlinked diagram(s)
DMN-R1  ✖ uncovered
DMN-R2  ✖ uncovered
DMN-R3  ✖ uncovered
Unlinked diagrams (no requirement reference):
  trace_legend.puml [pricing] (activity)
```

The mechanism is `prose_directives` (`model.py`), whose carrier kinds are
`("title", "header", "footer", "caption", "note")` — **`legend` is not
one**, deliberately: "one carrier set, so the rule and the traceability
matrix cannot disagree about what counts as a reference."

**This is documented, not hidden.** GEN006 and GEN007 name the carrier
set in their own finding text ("in title/header/footer/caption/notes"),
`trace --help` names it, and three existing docs repeat it. So this is
**not a gap and not a candidate.** It is recorded because the practical
consequence is sharp and, for this ecosystem, specific: for a team
carrying decision-rule IDs in a PlantUML diagram, `note` and `legend`
look interchangeable — identical rendering intent, identical score — and
one of them silently produces a fully-traced diagram while the other
produces an unlinked one.

*Minor fidelity observation, recorded and not raised:* every ID inside a
multi-line note attributes to the note's **opening** line (`:5` for all
three above), not to the row it appears on, because a note block is one
directive. Correct for one-line notes, coarse for a pasted table.

### 4.5 The overlap and the gap survive the nearest native construct

PlantUML does have a construct that looks like a decision table:
`switch`/`case`. The same discount decision, with the same overlap
(`100..500` and `400..1000` both match `400..500`) and the same gap
(nothing matches `> 1000`):

```
$ python3 -m pumllint switch_gap.puml
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint score switch_gap.puml
switch_gap.puml [discount-switch]: Level 4 (Precise) — 100/100
```

**Level 4 (Precise), 100 out of 100, on a decision that is provably
ambiguous and provably incomplete.**

This is the single most useful measurement in the note, and it is not a
defect report. `( 100..500 )` and `( 400..1000 )` are *strings* to the
parser. Knowing they overlap requires interpreting them as intervals over
a numeric domain, which is the solver §2 says belongs elsewhere. The
score is honest about what it measures — the branches are labelled, which
is what ACT003 asks — and says nothing about whether the labels are
mutually exclusive, because nothing in the tool claims it does.

It is worth stating plainly anyway, because "Level 4 (Precise)" is
exactly the phrase someone would over-read when pointing at a decision.

## 5. Boundaries

1. **Diagram vs table-and-language.** §1.1. The one boundary that cannot
   be negotiated: half of DMN is not the kind of artefact this tool
   reads.
2. **Text-decidable vs domain-decidable.** §2. pumllint's 51 rules are
   all decidable from the source without reasoning about the domain; DMN's
   core questions are about the domain.
3. **Linter layer vs analyser layer.** §3. The niche is thin at the layer
   this project occupies because the work moved to the layer that holds
   the parsed table.
4. **Discovered vs not.** `.dmn` is outside `PUML_EXTENSIONS`; the
   warning says so and the exit code does not move.
5. **Pre-registered vs open.** §0 and §7. The carrier question is not
   merely unanswered for DMN — it is fenced.

## 6. Sense — four true things

**S1. `dmnlint`'s thinness is informative, not an opportunity.** Two
rules after seven years is what a linting layer looks like when the
properties worth checking are decidable one layer up. Reading it as an
unoccupied market is the error this note exists to prevent.

**S2. The honest boundary works, again.** §4.1, on a tenth ecosystem's
native artefact. The "nothing was checked" contract keeps behaving.

**S3. The type-fallback class reaches ten notations.** §4.2. The count is
now large enough that the standing candidate's justification does not
depend on any one instance.

**S4. This project's own carrier evidence is correctly fenced.** §7. The
pre-registration held under exactly the pressure it was written for — a
later evaluation with an obvious incentive to quote the result loosely.

## 7. Nonsense — four moves to refuse

**N1. "We measured decision tables winning; DMN is the standard for
decision tables; therefore a DMN carrier arm."** This is the tempting
one, and W1B refuses it in two independent ways: the result "licenses no
claim about table *form* vs number *content* … and none about DMN or any
unmeasured carrier", and it is **suite-relative by construction**, since
`decision_table.md` is the grading suite's normative source and 5 of 11
scenarios are pinned by DT-only numerics. **A markdown table in a
hand-built oracle is not a `.dmn` file, and the pre-registration said so
before anyone wanted it to.**

**N2. A decision-table completeness or overlap rule, over `.dmn` or over
PlantUML `switch`.** This is a solver wearing a rule's clothes. It would
require interpreting label text as intervals over inferred domains — an
inference this tool makes nowhere else — and would produce exactly the
failure mode the relationship-legality anti-goal was settled to avoid:
confident findings derived from a model of the domain the tool does not
have. §4.5 is the honest alternative: measure what the source says, and
do not claim the rest.

**N3. Reading `.dmn` XML.** Refused on identity, as with `.archimate`,
`.bpmn` and XMI. A second artefact class, an OMG schema to track, and a
notation this tool does not lint.

**N4. Treating `dmnlint`'s existence as the BPMN convergence repeated.**
The fourth note's table cell "(+ `dmnlint`)" is true and invites this.
§3 measures why it does not follow.

## 8. Fit — the candidates, graded

### F1 — a DMN rule pack over `.dmn`. **No.** N3, and §2.

Nothing to parse that this project should be parsing, and the properties
worth checking need a solver. Not wait-for-pull: an adopter asking for
this would be asking for a different product.

### F2 — a DMN-over-PlantUML pack. **No — there is nothing to parse.**

PlantUML has no DMN diagram type — its language-specification index,
read 2026-08-29, enumerates 23 and DMN is not among them — and the
DRD-shaped drawing that people do make is §4.2's
type-fallback instance rather than a DMN model. The table has no PlantUML
form at all beyond §4.3's invisible text.

### F3 — DMN/FEEL as a codegen carrier arm. **Recorded, hypothesis, unchanged — and now explicitly fenced.**

The 2026-08-11 review's proposal stands where it was: hypothesis, no wave
touched it, and it would need a pre-registered wave under charter §10.
What this note adds is §7's N1 — the nearest measured result must not be
quoted in its support.

### F4 — a cross-spec verifier spanning BPMN, DMN, OpenAPI and diagrams. **Adopter programme, unchanged.**

Recorded in the external-review evaluation as outside this repository's
scope on ownership grounds. Nothing here moves it.

### F5 — decision-table analysis over PlantUML `switch`/`case`. **No — new, and refused on merit.**

The one genuinely new candidate this ecosystem suggests, and §7's N2 is
the whole answer. Recorded explicitly so a later note does not re-derive
it as an opening from §4.5's measurement.

### Fit against declared constraints

| Constraint | Reading |
|---|---|
| **Deterministic product path, no LLM** | Not reached — nothing is queued. |
| **Golden score contract** | Untouched; no fit here changes a score. |
| **Demand-driven / Arc E bar** | F1, F2 and F5 **fail on merit, not demand** — an adopter does not flip any of them. F3/F4 are recorded elsewhere and unchanged. |
| **Claim language is settled** | The risk here is §7's N1, which is a *quotation* discipline rather than a feature claim, and the pre-registration already carries it. |

## 9. SWOT

Scope: *pumllint's position relative to the DMN ecosystem*.

**Strengths (internal, favourable)**

- The charter discipline worked without intervention (§7, S4) — the one
  place a later evaluation could have over-claimed was fenced in advance.
- Honest silence on `.dmn` (§4.1), and honest scoring on a construct it
  does not understand (§4.5) — the tool never claims the decision is
  sound, only that the branches are labelled.
- A tenth type-fallback instance strengthens a standing candidate at no
  new cost (§4.2).

**Weaknesses (internal, unfavourable)**

- **"Level 4 (Precise) — 100/100" on a provably ambiguous, provably
  incomplete decision** is defensible and still bad optics if quoted
  without §4.5's explanation. This is a presentation risk the DIM-AMB
  residual for activity diagrams (recorded twice now) makes worse.
- A tenth instance of the type-fallback defect class, still unfixed.
- The `note`/`legend` traceability asymmetry (§4.4) is documented but
  easy to trip over, and this ecosystem is where someone would trip.

**Opportunities (external, favourable)**

- None found. F5 is the only new candidate this ecosystem suggests and it
  is refused on merit; F3 and F4 are recorded elsewhere and unmoved. I did
  not re-read all twenty-two prior notes to check whether an empty
  Opportunities column is a first.

**Threats (external, unfavourable)**

- **Over-reading the carrier result.** §7's N1 is the live one. It has
  survived contact once, here; the pre-registration's wording is what did
  that, and it should be quoted rather than paraphrased.
- **Over-reading "Precise".** §4.5. The maturity vocabulary is about
  source discipline, and a decision table is the artefact most likely to
  make a reader hear it as being about correctness.

## 10. Decision, recorded candidates, triggers

**Decision: no DMN support of any kind, no carrier arm, no decision-table
analysis. The prior records stand unchanged; the carrier item stays
hypothesis and stays fenced.**

**Never build:**

- A DMN rule pack, over `.dmn` or over PlantUML (F1, F2, N3).
- **A decision-table completeness, overlap, subsumption or masking rule
  in any form** (F5, N2) — a solver wearing a rule's clothes, and the
  relationship-legality anti-goal's nearest relative.
- A DMN/FEEL carrier arm added without a pre-registered wave under
  charter §10 (F3).

**Recorded, not queued:**

1. **The pre-registration fence (§7, N1)** — worth citing whenever the
   decision-table carrier result is quoted, in either direction. The two
   clauses are the asset; paraphrase loses them.
2. **A tenth instance of the type-fallback defect class (§4.2)** — no new
   candidate; the ArchiMate entry's candidate 1 already covers it.
3. **The `note`/`legend` traceability asymmetry (§4.4)** — an
   observation, explicitly **not** a candidate: the behaviour is correct,
   deliberate and documented in three places. Recorded so it is not
   re-discovered as a bug.

**Re-litigate on:**

- PlantUML gaining a DMN diagram type with decision-table semantics —
  which would create an artefact where today there is none. Nothing
  suggests this; the same trigger for BPMN was checked on 2026-08-29 and
  has not fired in years.
- A pre-registered wave measuring DMN or FEEL as a carrier and beating
  the diagram baseline — the only thing that reopens F3, and W3's result
  points the other way.
- An adopter carrying decision logic in PlantUML `switch`/`case` as their
  record and asking for coverage checks on it — which would be the F5
  constituency showing up, and would still be refused on N2; what it
  would justify is *documentation* of §4.5, not a rule.

## Related reading

- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  sibling standard, settled fourth; its §1.2 table is where "(+
  `dmnlint`)" appears, and §3 here is what that parenthetical does not
  imply.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md) — the
  paired-run precedent this note follows, and the source of the
  "verified, not characterized" standard applied to PlantUML's diagram
  types.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the type-fallback defect class and its standing candidate 1.
- [The measured minimum sufficient stack](minimum-sufficient-stack.md) —
  the carrier table, and the decision-table figures §7 declines to
  generalize.
- [The two-stage external project review, evaluated](external-review-evaluation.md)
  — where the BPMN/DMN carrier proposal is graded, and the scope boundary
  §0 starts from.
