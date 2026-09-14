# The ontology/graph EA stack, evaluated — where pumllint and aris2puml fit

*Dated evaluation, 2026-09-14, written against `6ce6760` (v0.33.0) and
aris2puml `c355b96`. The question as posed: an adopter's EA function
circulated five slides — an ArchiMate→ontology/graph transformation map,
an ArchiMate-at-the-centre standards star, a five-stage reporting
pipeline, an inputs-for-automated-validation sketch, and a use-case
list — with the question "investigate if/how pumllint and aris2puml fit
in these flows". Second adopter brief read against both roadmaps, after
the process-architecture brief of 2026-09-06.*

**Verdict up front: neither tool is in these flows, neither should be,
and that is the useful answer rather than a refusal — because the deck
is the design this repository already graded, one generation up its own
family tree, and the grading transfers with its measurements intact.
Slide 3 is the Linked.Archi pipeline with ArchiMEO in the ontology slot;
Linked.Archi's own related-work page says the ArchiMEO SHACL
principle-validation paper "directly inspired" its twenty governance
shapes — so Linked.Archi is the descendant, the deck the ancestor, and
the 2026-08-27 settlement — adjacent, complementary,
zero build, one seam — covers the deck without re-derivation. The seam
is unchanged and already ships: pumllint runs in the producer repo, on
the artefact a human wrote, *before* anything grounds it; the reasoner
runs on the triples a machine emitted, after. Binary conformance over a
closed world cannot say "Level 3, two findings short of Level 4", and
cannot say "this constraint was never reached because nothing parsed" —
which is the whole complementarity and the reason neither tool belongs
inside the deck's boxes.**

**What is new here is one live hazard and two refusals arrived at
independently. The hazard: if PlantUML ever leaves slide 1's
`iArchi Imp/Exp` box and someone gates it on this tool, they get a
*passing* verdict on a file the tool did not read. Re-measured today at
v0.33.0, five ArchiMate elements and four typed relationships are read
as five implicit lifelines and four unlabelled messages, typed
`sequence`, linting **exit 0** under the default gate and scoring
**Level 4 (Precise) — 90.4/100**; under `--profile codegen` the same
file emits **five SEQ101 blockers telling the author to declare
participants the file declares**. The sprite dialect — `!include
<archimate/Archimate>`, which is what the jArchi exports and the
ArchiMate MCP servers actually emit — is now honest, and that is a
change since the ArchiMate note: the `!include` disclosure shipped
2026-08-31 fires on it, and it holds Level 1 with a warning naming why.
So the two dialects have diverged, and the native `archimate` keyword is
now the *only* uncovered one. That sharpens the recorded type-marker
candidate; it does not queue it.**

**The first independent refusal is aris2puml's, and it is not a
market judgement: ArchiMate 3.2 has an And Junction and an Or Junction
and no XOR, the exclusive reading being conveyed by *naming* the
junction. aris2puml's version-1 JSON has `xor`, `and` and `or` as
distinct kinds, and the structuring pass treats them differently — XOR
becomes `if`/`switch`/`while`, AND and OR become `fork`, and a loop must
leave an XOR split and re-enter an XOR join or it is refused. An
ArchiMate front-end would therefore have to infer `xor` from a label,
which is invented structure: the one Iron rule carrying no
re-litigation clause. The second is that the deck fires none of the
knowledge-graph settlement's four re-litigation triggers and does not
touch its N3 — that refusal is OWL/SHACL as *pumllint's own rule
engine*, and the deck proposes a separate validator over a different
artefact, which is compatible with the settlement rather than a
challenge to it.**

*Bounds. Every pumllint and aris2puml claim below was executed against
the working trees at `6ce6760` / `c355b96` with the commands quoted, so
each can be re-run. External claims — ArchiMEO, Linked.Archi's
related-work page, the ArchiMate 3.2 junction semantics, the
Grakn→TypeDB rename — were read from published documentation and
web-search summaries on 2026-09-14, with URLs given; **no ontology,
reasoner or graph store was executed**, and none of them is load-bearing
for a verdict. The deck itself is the adopter's internal material and is
neither reproduced nor quoted beyond the box labels needed to place a
tool. Nothing here was read from the adopter's model estate: every
figure comes from this repository's fixtures and the public corpus.*

## 0. Why this ran, and what it is not

This is the second adopter brief run through the house triage — the
first being the process-architecture brief of 2026-09-06, whose Loop A /
Loop B split this note extends — and the latest of the
externally-prompted analyses. It follows the series shape: state the
proposal so it stands alone, verify every claim against the tree, grade,
record with triggers so it is not re-derived.

It is **not** a build proposal. Nothing in it is queued, and the two
candidates it touches were already recorded before it opened.

One thing needs pinning before anything else, because the deck's five
slides are not one proposal. They are:

- **(1) A transformation map** — ArchiMate models out of Archi via the
  Open Exchange Format, lifted by XSD→schema transformations into a
  graph store and into OWL2, then queried (SPARQL, DL query) and
  reasoned over (Datalog, incremental reasoning).
- **(2) A standards star** — ArchiMate at the centre, TOGAF, Zachman,
  BMM, BPMN, DMN and UML around it, captioned *vendor neutral, language
  with grammar*.
- **(3) A reporting pipeline** — EA models and principles → ontology
  grounding (an enterprise ontology, principles formalised via SBVR) →
  derivation → validation → a validation report.
- **(4) The same pipeline reduced** to its inputs: models plus
  principles, through an enterprise ontology, out as an automated
  validation report.
- **(5) A use-case list** — gap analysis (declarative versus running),
  automated validation by derivation rules, human-to-human and
  human-to-machine collaborative viewing and editing, root-cause
  analysis, linear and non-linear metrics.

They get different answers, and (3)/(4) are the only ones where a fit
question is even well-posed.

## 1. What the deck's stack is, and what this repository already knows about it

The enterprise ontology named on slide 3 is **ArchiMEO**, an
ArchiMate-based OWL enterprise ontology from FHNW, developed since
~2010 and validated across five applied research projects; its ArchiMate
module is built on ArchiMate 2.1 and models relationships as both OWL
classes and object properties. That is characterization from its
publication and repository, not an executed claim.

The decision-relevant fact is not ArchiMEO's content but its lineage.
**Linked.Archi's own related-work page states that the ArchiMEO paper on
SHACL-based EA principle validation "directly inspired linked.archi's
own principle-based validation shapes", which it implements as twenty
SHACL shapes for governance concepts.** Linked.Archi was evaluated here
on 2026-08-27 ([note](linked-archi-evaluation.md)), in full, with its
seam measured. So the deck is not a new ecosystem to grade — it is the
same design one generation upstream, and the existing note's §2 (the
seam), §3 (five overlap points and who owns each) and §4 (four
boundaries) apply line for line with ArchiMEO substituted for
Linked.Archi's core ontology.

Two differences are worth a line each and neither changes a verdict:

- Linked.Archi defers to W3C vocabularies (SKOS, PROV-O, Dublin Core,
  Schema.org) where ArchiMEO defines its own top-level ontology, and
  **ArchiMEO carries ISO 42010 Correspondence and CorrespondenceRule
  classes that Linked.Archi lacks** — which is the one place the deck's
  stack reaches a gap this repository has measured. The 42010 note
  (2026-08-28) found that XD001–005 implement the cheap half of
  correspondence rules, independently arrived at, and that the other
  half — the *correspondence requirement* itself — is absent: two
  entirely disjoint diagrams score **Level 4 (Precise), 100/100**. That
  half is on the never-build list as missing-edge inference, refused for
  want of an oracle, and a declared correspondence rule is exactly the
  oracle it wants (N4's "an obligation table someone wrote down"). So
  the deck's ontology is, for this one concern, the upstream that would
  make the refused check decidable — and it would still be *its* check,
  run at stage ④ over the graph, not a rule here.
- Slide 1's graph leg names **Grakn** and **GraQL**. Both were renamed
  in 2021 — Grakn to TypeDB, Graql to TypeQL. Non-load-bearing, but it
  dates that half of the map, and a reader following the box labels to
  current documentation will not find them.

## 2. Slide by slide: where each tool sits

| Deck | pumllint | aris2puml |
|---|---|---|
| **(1) Transformation map** | Not in it. One touch point, and it is a hazard, not a fit: if `.puml` appears anywhere in this flow it is a *rendering exported from a model held elsewhere*, and a finding on it cannot be durably acted on — the 2026-08-27 N1, unchanged. §3 measures what happens if it is gated anyway. | Not in it, and cannot be: §4. |
| **(2) Standards star** | Under none of the six boxes. Each already carries a dated verdict — TOGAF no (2026-08-28), Zachman no, BPMN no on four independent grounds, DMN no, UML "the ecosystem this project's artefact belongs to by name and not by substance", ISO 42010 no. BMM has never been evaluated and needs no note: there is no artefact. pumllint's unit is a PlantUML file, which is under the star rather than in it. | Same, via pumllint: the converter's target is that same file. |
| **(3) Reporting pipeline** | **The one real fit, and it is upstream of stage 1.** §5. | **The one real fit for the converter too**, and by the same argument: it is what makes a process model *exist* as a checkable artefact before the pipeline grounds it. §5. |
| **(4) Inputs: models + principles** | The "principles" input has a shipped, much smaller analogue: the conventions file. §6 measures what it does and does not reach. | Carries no principles and must not: **No linting in aris2puml**, settled, rules live in pumllint. |
| **(5) Use cases** | Row by row in §7. Two of the six land on standing refusals; one lands on a shipped feature; three are outside. | `--diagnose` and the sidecar are the root-cause row; nothing else. |

## 3. The hazard, re-measured at v0.33.0

The ArchiMate note measured this on 2026-08-27 at v0.29.0. It reproduces
at v0.33.0 on a freshly written file, and the codegen half is worse than
the prose there suggests.

A five-element, four-relationship ArchiMate model in PlantUML's native
dialect — `archimate #Business "Customer" as customer <<business-actor>>`
and friends, with assignment (`--`), serving and realization (`..>`)
between them:

```
$ pumllint native.puml                       # default gate
native.puml:1: [GEN001/minor] Diagram has no title
native.puml:1: [GEN002/info] @startuml has no name …
native.puml:8: [SEQ009/minor] Return '<unlabelled>' from 'customer' to 'claim' pairs with no preceding call
… 3 more SEQ009 …
✖ 6 issue(s): 1 info, 5 minor                # exit 0

$ pumllint score native.puml
native.puml: Level 4 (Precise) — 90.4/100    # exit 0
  diagramType: sequence · elementCount: 9
```

Nine modelled things in, nine elements counted, and not one of them the
kind it is: five ArchiMate elements read as **implicit sequence
lifelines**, four typed ArchiMate relationships read as **unlabelled
messages**, four of those as *returns* — hence the SEQ009s, which are
the tool reporting a reply-pairing defect on a notation that has no
replies. The `<<business-actor>>` stereotypes are not read; neither is
the `archimate` keyword, neither is `as customer`. Under the codegen
profile:

```
$ pumllint --profile codegen native.puml
… 5 × [SEQ101/blocker] Participant 'x' is created implicitly on first use;
      declare it (participant/actor/database/...) so its identity is authoritative
✖ 15 issue(s): 5 blocker, 1 info, 9 minor    # exit 1
```

Five blockers instructing the author to declare five participants that
the file declares, in a notation where the declaration keyword is
`archimate`. This is the generated-`.puml` hazard (ArchiMate note §7/F6)
in its sharpest form: **the failure is silent on the default path and
loud-and-wrong on the strict one**, and neither reading tells a user
that the dialect was not recognised.

**What has changed since 2026-08-27, and it is an improvement.** The
sprite dialect — the one the jArchi export scripts and the ArchiMate MCP
servers actually produce — now discloses:

```
$ pumllint score sprite.puml
warning: 1 diagram(s) contain '!include' but declare nothing: sprite.puml —
  pumllint does not expand preprocessor directives, so declarations inside
  included files are invisible to cross-diagram (XD) identity checks and
  declared-entity rules
sprite.puml: Level 1 (Sketchy) — 95/100
  • diagram has no modelled content — add elements before scoring means anything
  diagramType: unknown · elementCount: 0
```

That is the `!include` disclosure's second condition, shipped
2026-08-31 (nothing declared **and** (entities exist **or**
`element_count == 0`)), four days after the ArchiMate note was written
and therefore not in it. The consequence for the recorded candidate:
**the two ArchiMate dialects have diverged.** The population that
actually circulates is now covered — it scores Level 1 and says why —
and the native `archimate` keyword is the sole remaining dialect where a
file this tool cannot read reports Level 4. The candidate (widen the
type-marker set so declaration keywords type a file `unknown`, or make
cap C6 sensitive to fallback typing) is unchanged in shape, still a
scoring change needing its own decision and a golden re-freeze, and now
narrower in scope than the note that recorded it implies.

**The operational sentence for the adopter is one line: keep exported
ArchiMate `.puml` out of the gate.** It is the same sentence the
2026-09-06 brief got for component and deployment diagrams, for the same
reason and by a second mechanism.

## 4. Why aris2puml has no ArchiMate front-end, and it is not about demand

Arc C's gate for a second front-end is an adopter who cannot use the
notation's own tool. That gate is not what stops an ArchiMate reader.
This does:

**ArchiMate 3.2 has an And Junction and an Or Junction. It has no XOR.**
The specification's own position is that the or junction expresses both
inclusive and exclusive readings and that a modeller indicates which by
*naming* the junction.

aris2puml's version-1 JSON contract has `xor`, `and` and `or` as three
distinct node kinds, and the structuring pass does not treat them as
decorations:

- `xor` becomes `if`/`else`, `switch`/`case`, or a loop's `while`;
- `and` and `or` become `fork`/`fork again`/`end fork`, with the OR case
  recorded as an approximation (`' epc: OR-split <id>`, a stderr
  warning, and a `--strict` refusal);
- a loop must **leave from an XOR split and re-enter at an XOR join** or
  it is refused, by name;
- an XOR split joined by an AND is refused, by name.

So a reader over ArchiMate would meet a junction whose exclusivity lives
in a human-chosen label and would have to decide `xor` or `or` from that
label. Deciding it is **invented structure** — the Iron rule that reads
"*No clause: this is the tool's reason to exist*". Declining to decide
means every junction becomes `or`, which routes every branch through
`fork` and through the approximation path, i.e. every ArchiMate process
refuses under `--strict` and converts to a diagram whose control flow is
wrong in the one way the tool exists to prevent.

This is a refusal on the artefact, not the market — the same *shape* as
pumllint's ArchiMate refusal, reached from the opposite end of the
chain and with no coordination between the two. That is worth recording
precisely because it is a second, independent derivation.

**The clause the deck does touch** is aris2puml's emitter *Never*:

> **No BPMN output, no round-trip to ARIS.** One direction, one target.
> *Re-litigate only if a consumer other than pumllint appears that needs
> the intermediate model as its input — then the JSON, not a new emitter,
> is the product.*

The deck's knowledge base is exactly such a consumer **in shape**: if
the EA function wants the bank's process layer in the graph, the
converter's version-1 JSON — notation-neutral by construction, already
carrying process id, owner, lanes, typed nodes, edges, data objects and
interface refs — is the obvious feed, and `--manifest` is already the
inventory of what converted and what each process links to. The clause
is **not fired**: firing it needs someone naming that ask. When it
fires, the answer is already written and this note does not improve on
it — *the JSON, not a new emitter*. No RDF, no TriG, no OWL in
aris2puml; a consumer reads the JSON contract and does its own lifting,
exactly as `tools/corpus/epml_to_json.py` reads in the other direction.

## 5. The fit: stage 0 of the deck's pipeline, and why it is not inside it

Reduced to the one line that matters, with the deck's stage numbers:

```
producer repo                              the deck's pipeline
────────────────────────────────────────   ─────────────────────────────────
ARIS EPC ──► aris2puml ──► .puml ──► pumllint  │ ①models  ②grounding  ③derivation
             structure     lint/score/trace    │ ④validation  ⑤reporting
             refuse-or-    exit 0/1/2          │      ▲
             convert            ▲              │      │
                                │              │  is the grounded graph
              is this model worth              │  consistent with the
              grounding at all?                │  principles?
```

pumllint runs **before ①**, on the artefact a human wrote. The reasoner
runs **at ④**, on triples a machine emitted. Four structural reasons the
questions do not substitute, three of them transferred verbatim from the
Linked.Archi note's §4 and one specific to this deck:

1. **Report versus reject.** pumllint's product *is* the graded
   finding — six dimensions, five levels, a prescriptive gap report, a
   ratchet, an auto-fixer. Conformance in a shape/constraint validator
   is binary. A gate that can only say yes or no cannot say "Level 3,
   88.3/100, and here are the two findings blocking Level 4" — which is
   what the measured batch in §6 actually returns.
2. **Source versus projection.** Both ends are tolerant projections;
   pumllint *reports* its projection (cap C6, the `!include` disclosure,
   the "Syntax gate: not run" line) and a conformance report has no way
   to say "this constraint was never reached because nothing parsed".
   Absence of a triple and absence of a fact are indistinguishable
   downstream.
3. **Author-time versus integration-time.** pumllint runs in the editor
   (`pumllint lsp`), the pre-commit hook and the PR; the deck's pipeline
   runs at aggregation. The failures each catches belong to different
   people on different days.
4. **Naming content versus label presence.** The defect class this
   catalog exists for is *what a name says* — `Fehlersuche` is not
   verb-first, a swimlane is blank, an XOR outcome has no event. A
   shapes layer checks the presence, typing and cardinality of a label
   the transformation generated. Neither reaches the other's failure,
   and the deck's slide 3 has no box for the first.

**Measured, so the claim is not rhetorical.** Five processes — the demo
plus the four public corpus models — through the whole chain:

```
$ aris2puml tests/fixtures/order_to_cash.json tests/fixtures/corpus/*.json \
      -o out/ --report sidecar.json --manifest manifest.json
aris2puml: …/mortgage-application.json [BPMAI-504129192]: join sid-084E…
  reached without passing through its split (unstructured)
aris2puml: …/mortgage-application-variant.json [BPMAI-1525267023]: join sid-77F8… (unstructured)
# sidecar summary: inputs 5, processes 5, converted 3, refused 2,
#   converted_percent 60.0, approximated 0, dropped 3, flagged 13

$ pumllint out/ -c tests/fixtures/conventions.toml
✖ 39 issue(s): 20 major, 19 minor            # exit 1

$ pumllint score out/ -c tests/fixtures/conventions.toml
out/order-to-cash.puml [order-to-cash]: Level 4 (Precise) — 100/100
Model set: Level 3 (Disciplined) — 88.3/100 weighted across 3 diagram(s)
  — worst: out/finanzierung-soll.puml [finanzierung-soll] (Level 3)

$ pumllint trace out/ --requirements manifest.json \
      -c tests/fixtures/conventions.toml --fail-on-unknown-ref
Requirement coverage: 1/3 covered — 2 uncovered, 1 unknown reference(s),
  2 unlinked diagram(s) — across 3 diagram(s)
Unknown references (not in the inventory — a typo, or the inventory is stale):
  PROC-0051  ← out/order-to-cash.puml [order-to-cash]:3   # exit 1
```

Four things in that transcript are what the deck's stages ③–⑤ would
otherwise have to supply for the process layer, and all four are
upstream of the ontology:

- **A refusal with a named node** — two of five models have no block
  structure, and the converter says which connector, rather than drawing
  something plausible. Nothing at ④ can recover this: an unstructured
  EPC lifted into a graph is a graph, and the defect becomes invisible.
- **A fidelity account** — `converted_percent`, and per process what was
  dropped, approximated, refused or flagged. This is the number a
  process owner reads, and it is the honest denominator under any figure
  the pipeline later reports about process coverage.
- **A graded verdict with a named worst member** — not conformance.
- **A bipartite coverage matrix** with covered / uncovered / unknown-ref
  / unlinked, over the converter's own manifest. That is a gap analysis
  in the slide-5 sense, with an exit code, and it is the closest shipped
  thing to the deck's "validation report".

*(The nineteen ACT005 and twenty ACT006 findings are the two German
corpus models against an English verb list and a Title-Case swimlane
pattern — a configuration artefact of the demo conventions file, not a
defect in those models. Quoted for the shape of the output, not as a
result about the corpus.)*

## 6. "Principles" — what the conventions file already reaches, and what it does not

Slide 4 reduces the pipeline to **models + principles → enterprise
ontology → automated validation report**. pumllint has a much smaller
analogue of the principles input, and being explicit about its ceiling
is more useful than either claiming or disclaiming the fit.

`tests/fixtures/conventions.toml` in aris2puml — the file
`docs/business-processes.md` publishes — is twenty-five lines and
expresses four house rules:

```toml
swimlane-naming  = { pattern = '^[A-Z][a-z]+( [A-Z&][a-z]*)*$' }
verb-first-activity = { severity = "major", verbs = [ "Receive", "Validate", … ] }
unlabelled-decision-branch = { require_else_label = true }
owner-tag        = { pattern = '(?i)owner\s*:' }
requirement-link = { pattern = 'PROC-\d{4}' }
```

The last two are the governance pair: GEN006 `owner-tag` and GEN007
`requirement-link` are dormant until a pattern arms them, and the
converter writes the carrier they read into the footer
(`footer owner: Sales Operations — ARIS process PROC-0042 — interfaces: PROC-0051`).
"Every process names an owner" and "every process cites its ARIS id" are
therefore *principles, declared as data, enforced at commit time, with
an exit code* — the same worked example ("every application component
must have an owner") that the shapes literature uses.

**The ceiling is sharp and it is the division of labour.** A principle
pumllint can express is one decidable **from a single artefact's own
text**, plus name-equality joins across one lint batch (XD001–005). A
principle needing a second artefact — this component realises a
capability in the capability map, this process is owned by a stakeholder
who exists in the HR system, this application is on the approved
technology list — is not expressible here and should not be: that is
what an enterprise ontology is for, and it is why the deck's slide 4 has
an ontology in the middle rather than a linter. The recorded item on
this side is `trace`'s typed successor (Arc C's declared diagram→diagram
links, trigger: an adopter running `trace` asking for typed relations),
and aris2puml's manifest is its carrier once the JSON contract grows the
relation — recorded 2026-09-06, unchanged by this note.

**One warning to pass back, from the record.** Slide 3 grounds the
principles via **SBVR**. This repository has a dated finding on SBVR,
from the prose-pipeline evaluation (2026-07-29): *EARS succeeded — five
lightweight human-readable patterns, industrial adoption — where SBVR
Structured English failed: no formal grammar, no tooling, a style guide
rather than a language*, and the standing consequence is that any future
requirements DSL here "must be low-overhead and hand-parseable first".
That is a finding about **SBVR Structured English as a controlled
natural language**, and it is not a claim about the ArchiMEO work, which
formalises principles into SHACL shapes — a mechanism with a grammar and
a validator, i.e. precisely what the 2026-07-29 note says SBVR lacked.
The warning is therefore narrow and worth exactly one sentence: if the
principles are to be *written* in SBVR Structured English and read by a
human before a machine, that leg has a documented adoption history and
EARS is the cheaper shape; if SBVR is the analysis vocabulary and SHACL
is the artefact, the objection does not apply.

## 7. Slide 5, use case by use case

| Use case | Where it lands |
|---|---|
| **Gap analysis — declarative versus running** | Already split, and the deck adds a third term. The 2026-09-06 brief placed aris2puml → pumllint as **Loop A, commit-time** and process-mining conformance as **Loop B, run-time**. The deck is **Loop C: declared-versus-ontology** — is the model consistent with the principles and with the rest of the estate. Three loops, three artefacts, three clocks; none substitutes for another, and the failure mode is a programme that funds one and reports it as all three. |
| **Automated validation — derivation rules** | The legality/derivation half is the **settled anti-goal** here — "well-formedness as a type" (2026-08-02): representable ill-formedness *is* the product, because findings, levels, ratchet and `fix` all require an ill-formed model to be constructible and scoreable. That is a statement about a linter, not about a reasoner: on the ontology side derivation is the right design, ArchiMate's own relationship tables are a legality metamodel "intended for tool implementation", and a reasoner is the correct engine for them. Nothing to build on this side, and no objection to that side. |
| **H2H collaborative viewing and editing** | Outside both tools, with one adjacency worth naming so it is not mistaken for a fit: `pumllint lsp` puts findings in an editor as diagnostics over stdio. That is one author's editor, not collaboration. |
| **H2M collaborative viewing and editing** | The nearest shipped thing is `docs/agents.md`'s score → repair → re-score loop, and the record attached to it is a caution, not an offer: the agent-repair wave measured **−6 pp pooled executed correctness** against unrepaired originals, and **−53 pp** on one diagram from a single invented guard. The product path is deterministic by working agreement — no LLM call ships inside pumllint — so H2M editing is a consumer of the gate, never a component of it. |
| **Root cause analysis** | The one row with a genuine shipped analogue, on the converter side and at one model's scope: `--diagnose` writes `<name>.refused.puml` — the EPC as the graph it is, offending node in red, the reason as a note — and the sidecar carries the same refusal as prose with the run's fidelity account. Root cause for *why this model cannot be made checkable*; not root cause across an estate, which is the deck's sense and needs the graph. |
| **Linear and not linear metrics** | The row to be most careful about. **N5 of the knowledge-graph settlement refuses graph-derived metrics as a maturity signal** — on Goodhart and on evidentiary standard: pumllint's score is calibrated against an execution oracle (EVIDENCE.md: fidelity correlation r ≈ 0.49, sharp degradation below Level 2) and frozen behind a golden test, and a plausible-but-uncalibrated fitness signal decays into optimising for itself. If the EA function wants a pumllint number on a metrics wall, the sentence to circulate is the guide's own: **gate on the linter, not the level** — and for activity diagrams specifically, DIM-AMB is 100 by construction (the BPMN record's 2026-08-29 measurement, quoted in the 2026-09-06 brief record), so the composite is thinner there than the number looks. |

## 8. Sense, nonsense, fit, gap

**Sense — four true things in the deck, as they bear on these tools.**

1. *The pipeline's shape is right and the two tools sit upstream of it.*
   Grounding models in an ontology and validating principles against the
   grounded graph is a real design with a working instance; the seam
   below it is real too, and needs no code on either side.
2. *"Models + principles" is the correct decomposition of governance*,
   and the conventions file is a working miniature of it at
   single-artefact scope.
3. *ISO 42010 correspondence rules* — present in ArchiMEO, absent from
   Linked.Archi — are the one concern where the deck's stack supplies
   something this repository measured as missing and refused: the
   correspondence *requirement*, whose absence lets two disjoint
   diagrams score 100/100 (42010 note, 2026-08-28) and whose
   general form is the no-oracle refusal. A declared correspondence rule
   is the oracle; it belongs at stage ④, over the graph.
4. *An EA function asking where a commit-time gate fits is asking the
   right question*, and the honest answer is "before your stage 1, in
   the repo, on the file" rather than "inside your stage 4".

**Nonsense — four moves to refuse.**

1. **Feeding exported ArchiMate `.puml` through pumllint as a gate.**
   §3. Silent pass at Level 4 on the native dialect; five invented
   blockers under codegen.
2. **An ArchiMate front-end in aris2puml.** §4. No XOR junction to read;
   deciding exclusivity from a label is invented structure.
3. **An RDF/OWL emitter in aris2puml.** The *Never* clause's own answer:
   the JSON is the product, a consumer lifts it.
4. **OWL/SHACL as pumllint's rule engine.** N3, unchanged — and the deck
   does not ask for it. Recorded here only so a later reader does not
   mistake the deck's compatibility with the settlement for a challenge
   to it.

**Fit against declared constraints.** Nothing in this note proposes code,
so the table is short: every fit identified is a *usage* of shipped
behaviour (pumllint in the producer repo, `--manifest` plus
`trace --fail-on-unknown-ref`, `--report` as the fidelity denominator),
which costs no dependency, changes no contract and moves no score. The
two candidates it touches — type-marker widening and typed process
relations — were recorded before it and keep their existing gates.

**Gap — measured, and it is one.** The deck's stages ③–⑤ have no box for
*what a name says*, and the tools below them have no reach above one
artefact. The measured consequence of the first half is §5's 39 findings
(20 major) on three converted processes, none of which is a cardinality,
domain/range, enumeration-membership or label-presence defect — i.e.
none of which the published shape classes address. The measured
consequence of the second half is §6's ceiling. The gap is symmetric,
which is why the answer is a seam rather than a merge.

## 9. SWOT, one pass

- **Strengths.** The seam is already shipped on both sides (pre-commit
  hook, composite Action, `--check`, exit codes) and needs no
  integration work; the chain returns a graded verdict and a fidelity
  denominator that a conformance layer structurally cannot; the refusal
  discipline means an unstructured process is *named*, not silently
  lifted.
- **Weaknesses.** The native-ArchiMate mistyping is live and reports
  Level 4; the score is thinner for activity diagrams than the number
  suggests (DIM-AMB); `trace` is bipartite and untyped, so "realises"
  and "variant-of" have no carrier yet; aris2puml's real-ARIS leg (A1b)
  is still adopter-gated, so the process half of any such programme
  starts with an unrun export script.
- **Opportunities.** If the EA function wants the process layer in the
  graph, the version-1 JSON and the manifest are a ready feed and the
  *Never* clause already says so; the same delivery is the census the
  component parser waits on, the foreign fixture Arc D waits on, and the
  A1b gate — one corpus, three triggers, recorded 2026-09-06.
- **Threats.** A programme that funds Loop C and books Loop A's benefit;
  a metrics wall carrying a level rather than a gate; exported
  ArchiMate `.puml` entering a CI gate and passing.

## 10. Decision, recorded candidates, triggers

**Decision: no build on either side, nothing queued, no settlement
disturbed.** The deck is graded as the Linked.Archi ecosystem one
generation upstream; that note's verdict stands and this one supplies
the ArchiMEO lineage, the aris2puml half it never covered, and one
re-measurement.

**Never build** (each already implied by a standing settlement; recorded
here in the deck's vocabulary so the next proposal lands on it):

- An ArchiMate rule pack, `.archimate` reader or Open Exchange Format
  reader in pumllint (2026-08-27, N1–N3).
- An ArchiMate front-end in aris2puml — refused on the artefact, not the
  gate: no XOR junction exists to read (§4). Same standing as the Iron
  rule it derives from.
- An RDF/OWL/TriG emitter in aris2puml. The *Never* clause's own answer
  applies: the JSON is the product.
- OWL/SHACL as pumllint's rule engine (knowledge graph, N3).
- Graph-derived or ontology-derived metrics in the maturity score
  without a wave under charter §10 discipline (N5).

**Recorded, not queued:**

1. **The type-marker candidate is narrower than recorded.** The
   `!include` disclosure (2026-08-31) now covers the sprite dialect, so
   the native `archimate` keyword is the only ArchiMate dialect still
   reporting Level 4 on a file the parser does not read. Shape and cost
   unchanged — a typing or cap change, its own decision, a golden
   re-freeze. This note supersedes the ArchiMate note's scope statement
   for candidate 1, not its content.
2. **"Keep exported ArchiMate `.puml` out of the gate"** — the
   operational hazard line for any adopter with an EA function, matching
   the component/deployment hazard recorded for the 2026-09-06 brief.
   Belongs in the same place that one does: the adopter's ledger, not a
   rule.
3. **Loop C as the third term.** The Loop A / Loop B naming from
   2026-09-06 gains a third: declared-versus-ontology. A naming and
   sequencing device only; no item changes.
4. **aris2puml's version-1 JSON as the graph's process feed** — the
   shape that would fire the emitter *Never*'s re-litigation clause,
   with the answer already written (the JSON, not an emitter). Recorded
   so the next reader does not re-derive it.
5. **The correspondence requirement has an upstream after all.** The
   42010 gap (two disjoint diagrams at Level 4, 100/100) is refused here
   as missing-edge inference for want of an oracle; ArchiMEO's
   CorrespondenceRule class is an oracle someone wrote down. This does
   **not** re-open the refusal — the check stays the graph's, at the
   deck's stage ④ — but it is the first time the missing oracle has been
   located in a named artefact rather than hypothesised, and that is
   worth having on file. No item changes.

**Re-litigate this note on any of:**

- **A named ask for the process layer in the knowledge base** — the
  emitter clause's trigger, fired by a consumer, not by a slide.
- **An adopter whose ArchiMate models live in PlantUML only**, with no
  Archi or EA tool upstream — the one case where the 2026-08-27 N1's
  premise fails (unchanged from that note; the deck does not fire it,
  since slide 1 has Archi at the top).
- **A principle the EA function needs enforced at commit time that the
  conventions file cannot express** — the honest shape of a pumllint
  ask out of this deck, and the one that would tell us something.
- **The bank's corpus arriving** — already the re-litigation clause on
  the 2026-09-06 record, with the maintainer's 2026-09-07 qualifier
  attached: the models' quality is itself in doubt, so a low conversion
  rate or a high finding count is a result about the models and not a
  reason to soften a gate.

## Related reading

- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) —
  the ecosystem this deck instantiates; its §2 seam, §3 overlap table
  and §4 boundaries are the load-bearing prior and are not repeated
  here.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the artefact refusal and the mistyping measurement §3 re-runs.
- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md)
  — N3 and N5, the two settlements slide 3 and slide 5 come nearest to.
- [Cross-diagram relationships in pumllint, evaluated](cross-diagram-relationships-evaluation.md)
  — why `trace` is bipartite and untyped, and what a typed relation
  would cost.
- [Model verification beyond linting](model-verification-evaluation.md)
  — the 2026-08-02 well-formedness-as-a-type anti-goal that slide 5's
  derivation row lands on.
- [The prose pipeline, reassessed](prose-pipeline-evaluation.md) — the
  SBVR/EARS design-history finding §6 quotes.
- [Linting business processes](business-processes.md) — §2's mapping
  table and the conventions file §6 measures.
- [ROADMAP.md](../ROADMAP.md) — the process-architecture brief record
  (2026-09-06) this note extends, and the Arc E build bar it is triaged
  against.

**External sources** (read 2026-09-14, characterization only):
[ArchiMEO](https://www.scitepress.org/Papers/2020/90002/90002.pdf) ·
[ArchiMEO repository](https://github.com/ikm-group/ArchiMEO) ·
[Linked.Archi on ArchiMEO](https://meta.linked.archi/docs/practice/related-work/archimeo-enterprise-ontology/) ·
[ArchiMate 3.2, relationship connectors](https://pubs.opengroup.org/architecture/archimate3-doc/ch-Relationships-and-Relationship-Connectors.html) ·
[TypeQL releases (the Graql rename)](https://github.com/vaticle/typeql/releases)
