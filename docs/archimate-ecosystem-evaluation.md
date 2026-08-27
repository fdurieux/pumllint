# The ArchiMate ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `e1d5862` (v0.29.0). The
question as posed: investigate the ArchiMate ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Third in a series (Linked.Archi,
C4, this).*

**Verdict up front: no pack, and — unlike C4 — this is a principled no
rather than a wait-for-pull. Two reasons, either sufficient. First, the
artefact this tool can see is the wrong one and is usually not
hand-written: ArchiMate models live in Archi's `.archimate` files or the
Open Group Model Exchange XML, and the `.puml` is a *rendering exported
from a view* — the widely-circulated jArchi export scripts produce one
file per view, and MCP servers now generate PlantUML ArchiMate from agent
prompts. Defects found in that file belong upstream and would be
overwritten on the next export. Second, ArchiMate's externally-authored
rule spec is a **legality metamodel** — the normative relationship tables
in Appendix B of the specification, explicitly "intended for tool
implementation" — and every real ArchiMate tool enforces it at authoring
time, which makes most of it unrepresentable rather than checkable. That
is the well-formedness-as-a-type anti-goal (settled 2026-08-02) arriving
from the far side: here the model-based tools already did it, correctly,
because for a legality metamodel it is the right design.**

**What this evaluation is actually worth is the measurement, which is the
worst of the three ecosystems and the first that generalises past its own
notation. PlantUML's native ArchiMate form declares elements with an
`archimate` keyword that is not a type marker, and expresses
relationships as arrows. Measured: a five-element, four-relationship
ArchiMate model is read as **two implicit lifelines and one message**,
typed `sequence`, and scored **Level 4 (Precise) — 93.33/100**, with a
false SEQ009. Under the codegen profile it emits **4 findings, 2
blockers, exit 1**, telling you to declare participants that are declared.
Nine modelled things in the source, three read, all three misread,
verdict "Precise".**

**Characterizing that produced the general result. A file carrying no
recognized type marker is typed `sequence` as soon as it contains **one**
undecorated arrow — `->`, `-->`, `..>` or `--` — because its two
endpoints become implicit lifelines and 2 participants + 1 message = 3
elements, which is exactly enough to escape the C6 zero-element honesty
cap and clear the Level-4 element floor. Direction-hinted arrows
(`-up->`, `-down->>`) and both-ends-decorated ones (`*-down-`) are not
read, so those files stay honest at Level 1. ArchiMate's realization
(`..>`) and association (`--`) notations are both in the unsafe set.
This is the same failure the C4 note measured as "raw arrows are the
mechanism" and the Linked.Archi note measured on a component diagram via
a different route (one `database` keyword, 1 element, Level 3) — three
notations, two escape mechanisms, one honesty cap. That passes the "one
corpus is an anecdote" bar, and it is the one thing here recorded as a
candidate.**

*Bounds. Every pumllint claim was executed at `e1d5862` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
External claims were read from published documentation and web-search
summaries on 2026-08-27, with URLs given. **No ArchiMate tool was
executed**, and per this session's repository scope **no GitHub repository
was read** — the jArchi export scripts, the ArchiMate MCP servers and
Archi's issue tracker are characterized from search summaries and
third-party write-ups, not from source. Two pages could not be retrieved
(BiZZdesign's conformance-check blog 403s; its Horizzon help article
returned navigation chrome only), so commercial-tool claims are thinner
than the open-source ones and are marked where they are load-bearing.
The probe files below are **constructed**, not copied from PlantUML's
documentation: the docs page fetched did not print a relationship-bearing
`archimate`-keyword example, so §8.1 characterizes pumllint's behaviour
against arrow notations directly rather than resting on a quoted sample.*

## 0. Why this ran, and what it is not

ArchiMate appeared in this repository exactly once before today — a single
line inside yesterday's Linked.Archi entry, naming it as that ecosystem's
flagship notation. There is no settled question, no prior evaluation, and
nothing recorded. So unlike the C4 re-examination, this is a first look.

It is not a build proposal, and §7 explains why it is not even a
wait-for-pull. It is also not a claim that ArchiMate modelling is
low-value — the opposite: the reason the fit fails is that this ecosystem
solved the modelling problem properly, at a layer below where this tool
operates.

## 1. The ecosystem

### 1.1 The standard, and the size of its rule spec

ArchiMate is an [Open Group standard](https://pubs.opengroup.org/architecture/archimate3-doc/),
current at **3.2** (October 2022 — a refinement release over 3.1, not a
concept expansion). Its structure matters here more than its content:

- Layers (business, application, technology, physical) crossed with
  aspects (active structure, behaviour, passive structure), plus
  motivation, strategy and implementation extensions.
- **Normative relationship tables** in Appendix B, stating for every
  ordered pair of element types which relationships are permitted. The
  specification says these are "mainly intended for tool implementation
  purposes".
- **Formal derivation rules** — valid relationships inferable from chains
  of asserted ones, which the specification says can be trusted when the
  model is well designed.

That is by a wide margin the largest and most formal externally-authored
rule spec of the three ecosystems evaluated this week. C4 offers a
21-item prose review checklist. Linked.Archi offers SHACL shapes — 97 for
ArchiMate alone, plus SHACL-rule implementations of derivation rules
DR1–DR8 and PDR1–PDR12 — which are themselves a formalization *of this
specification*. ArchiMate offers a machine-intended legality matrix.

§4 and §6 explain why a bigger, more formal rule spec makes the fit
*worse* here rather than better.

### 1.2 The tools

| Layer | Examples | Validation it ships |
|---|---|---|
| **Modelling tools** | Archi (open source), Sparx EA, BiZZdesign, MEGA HOPEX, Orbus iServer, Avolution ABACUS | Metamodel enforced at authoring time; Archi ships a Model Validator; BiZZdesign ships conformance checks against user-declared conventions |
| **Interchange** | Open Group Model Exchange File Format (XML) | Schema conformance |
| **Scripting / automation** | jArchi (JavaScript), Archi CLI (ACLI) | User-written checks; ACLI does HTML reports and CSV export |
| **Graph / semantic** | Linked.Archi (SHACL, 97 shapes) | Post-hoc conformance of derived RDF |
| **Rendering** | Archimate-PlantUML stdlib, PlantUML native `archimate`, Mermaid | **None** |
| **AI / agents** | several community MCP servers | Metamodel enforced *server-side at authoring time* |

**[Archi](https://www.archimatetool.com/)** is the centre of the
open-source ecosystem: free, mature, `.archimate` native format, a
**Model Validator** that reports errors and warnings against the
specification, **jArchi** scripting for custom rules, **coArchi** for
collaboration, and **ACLI**, a headless command-line mode that can load a
model and generate an HTML report or export CSV.

One gap in that picture is directly relevant and worth stating carefully:
Archi's validator is a workbench feature, and **command-line model
validation appears to be a standing feature request rather than a shipped
ACLI capability** — users have asked for it precisely so a pipeline can
"stop the process when bad content is pushed". *(Characterized from search
summaries surfacing the request and from third-party automation write-ups;
the issue's current status was not verified — see Bounds. If ACLI has since
gained validation, the point below weakens accordingly.)*

So the ecosystem's flagship open-source tool has a validator and,
apparently, no first-class CI gate for it — while its users are explicitly
asking for one. That is the closest thing to a pumllint-shaped gap
anywhere in ArchiMate. §7/F4 explains why it is still not this project's.

**BiZZdesign** ships conformance checks in Enterprise Studio, where
modelling conventions are declared as ordinary ArchiMate views describing
the permitted elements and relationships, and violations are reported "as
a heat map, in a table, or in a dashboard". *(Blog and help pages could
not be retrieved in full — see Bounds. No aggregate quality level or
score appears in the material that was retrievable, which is a weaker
statement than the equivalent for Structurizr and LikeC4.)*

### 1.3 The AI layer — denser than C4's, and community-built

Where C4's agent story is two vendors shipping MCP servers for their own
DSLs, ArchiMate's is a cluster of community MCP servers, and they converge
on one design:

- **`archimate-mcp`** (Python, on PyPI) — full ArchiMate 3.x authoring:
  CRUD over elements, relationships, folders and views; query and
  traversal; import/export of the Open Group Model Exchange File Format
  so results open directly in Archi.
- **An Eclipse PDE plugin for Archi** exposing models over MCP with a
  large tool surface for querying, searching, creating, layout and batch
  operations.
- **A PlantUML-generating ArchiMate MCP server** — an agent-facing
  generator whose output is exactly the dialect §8 measures.

The design they share is stated plainly in the ecosystem's own framing:
*the agent describes the architecture; the server enforces what ArchiMate
actually permits, lays out the diagram, and writes the file.* That is
**prevention by construction** — the relationship tables are enforced in
the authoring API, so an illegal relationship is not reported, it is
unconstructable.

Set against the other two evaluations, a pattern completes:

| Ecosystem | Agent strategy |
|---|---|
| LikeC4 | a skill that teaches the DSL — prevention by instruction |
| Structurizr | an MCP server exposing validation and inspection — verification |
| ArchiMate | MCP servers that enforce the metamodel in the authoring API — prevention by construction |

Only Structurizr's shape is the one `docs/agents.md` describes. ArchiMate's
is the one a legality metamodel *should* have, and it leaves nothing for a
downstream checker of legality to find.

## 2. The two PlantUML dialects, and which artefact they are

PlantUML carries ArchiMate two ways, and pumllint behaves oppositely on
them:

**Dialect A — the `Archimate-PlantUML` stdlib macros.** `!include
<archimate/Archimate>` plus `Business_Actor(id, "Label")` and
`Rel_Serving_Up(a, b, "serves")`. Relationship macros carry no arrow
tokens, so nothing types the file.

```
$ python3 -m pumllint score stdlib.puml
  type='unknown'  level=1 (Sketchy)  score=100.0  elements=0
✔ No issues found.
```

Honest: the C6 zero-element cap holds and the report says there is no
modelled content. Identical in shape to the C4 pure-macro result.

**Dialect B — PlantUML's native `archimate` keyword.** `archimate
#Application "Payment Application" as payApp <<application-component>>`,
with relationships written as arrows. This is where it goes wrong, and §8
measures it.

**Both dialects are usually generated, not written.** The
widely-circulated jArchi export scripts (`PlantUML-V2G`,
`PlantUML-V2NG`) walk the visual objects of a selected Archi view and emit
one `.puml` per view; the PlantUML-generating MCP server emits the same
class of file from an agent prompt. So the seam looks like this:

```
   .archimate model  ──►  Archi validator (GUI)  ──►  jArchi / MCP export  ──►  view.puml
   ▲                      ▲                                                      ▲
   where the model        where the ecosystem                             what pumllint
   actually lives         already checks it                               can see — and
                                                                          regenerates
```

pumllint sits at the far right, on a derived artefact, downstream of a
checker that already ran, on a file that is rewritten whenever the view
is re-exported. Every fit below is judged against that picture.

## 3. Overlap

| Concern | pumllint | ArchiMate ecosystem | Reading |
|---|---|---|---|
| **Relationship legality** | none, by decision | the normative Appendix B tables, enforced at authoring time by every modelling tool and by the MCP servers' APIs | **No overlap, and none wanted.** Settled as the well-formedness-as-a-type anti-goal; here it is also unrepresentable upstream. |
| **Derived relationships** | none | derivation rules DR1–DR8 / PDR1–PDR12, implemented in tools and in Linked.Archi's SHACL rules | **No overlap.** Inferring edges is the rejected no-oracle shape; ArchiMate supplies the oracle, in a layer this tool does not reach. |
| **Naming / conventions** | GEN004, CLS001, ACT005, UC002 (regex, configurable) | jArchi custom scripts; BiZZdesign convention views | **Genuine overlap** — and the ecosystem's version is model-aware and runs where the model lives. |
| **Completeness (documentation, ownership)** | GEN001/GEN006/GEN007, DIM-TRC | Archi validator warnings; BiZZdesign conformance views; Linked.Archi `ConceptOwnerShape` | **Genuine overlap**, three implementations upstream. |
| **Ambiguity / vagueness of labels** | DIM-AMB, the codegen lexicons | **nothing anywhere** | **Unoccupied** — and unreachable, because it needs the model, not the rendering. |
| **Level / gap report / ratchet** | the whole scoring model | **nothing found** | **Unoccupied**, as in both prior evaluations. |

Two rows carry the argument. The ecosystem owns legality and derivation
outright, in a layer below the one this tool operates in — and should.
And the row where pumllint is genuinely differentiated (ambiguity, and
grading on top of it) is unreachable here, because the `.puml` is a
rendering of a model whose labels were already fixed upstream.

That combination is what makes ArchiMate different from C4. In C4 the
`.puml` *is* the model for many teams, so the gap is real. In ArchiMate
the `.puml` is a picture of the model, so the same gap is somebody else's.

## 4. Boundaries

1. **Model vs rendering.** ArchiMate's artefact of record is `.archimate`
   or Model Exchange XML. The `.puml` is downstream and regenerated.
   Linting a regenerated artefact produces findings that cannot be fixed
   in place.
2. **Legality vs hygiene.** ArchiMate's spec is a legality metamodel;
   this tool's catalog is modelling hygiene. Legality is enforced by
   construction upstream; hygiene needs a model to attach to.
3. **Enforced vs representable.** The MCP servers make illegal
   relationships unconstructable. Representable ill-formedness is this
   product's premise — and where a metamodel is formal enough to enforce,
   enforcement is the better design, not a worse one.
4. **Discovered vs not.** `.archimate` and the Model Exchange XML are
   outside `PUML_EXTENSIONS` by construction, and the "nothing was
   checked" warning says so.

## 5. Sense — three true things

**S1. The measured defect is real, reproducible, and this evaluation's
whole yield.** §8.1 characterizes it by token, not by anecdote, and it
generalises past ArchiMate to any type-marker-less file with one
undecorated arrow. It connects two previously separate observations from
the C4 and Linked.Archi notes into one defect class.

**S2. The one pumllint-shaped gap in the ecosystem is real — and it is
Archi's to fill.** A validator that runs in the workbench but not in CI,
with users asking for the pipeline gate, is precisely the shape of need
this project exists to serve. It is also a need for `.archimate` files
inside a JVM/Eclipse tool with a scripting layer already present. jArchi
plus ACLI is a far shorter path to it than a PlantUML linter, and it is
the ecosystem's own path.

**S3. ArchiMate's agent design completes the AI picture the last two
evaluations started, and it is the one this project should expect to lose
to where it applies.** Prevention-by-construction beats
verification-after-the-fact whenever the constraint is formal enough to
encode in an API. That is exactly true of relationship legality and
exactly false of the things `DIM-AMB` measures — "do stuff", "TBD",
"handle it somehow" are not preventable by any metamodel. The dividing
line between the two is the clearest statement of this project's scope
that any of the three evaluations produced.

## 6. Nonsense — four moves to refuse

**N1. An ArchiMate rule pack over `.puml`. Refused on the artefact, not
on demand.** §2: the file is a generated rendering. This is not "wait for
pull" — a pull would not fix it, because a finding in a regenerated file
is a finding the user cannot durably act on. If anyone ever does ask, the
right answer is to point upstream.

**N2. Implementing the relationship tables as rules. Refused twice
over.** It is relationship legality, which the Arc C XD note already
flagged as the boundary to scope away from ("this sits close to
relationship *legality*", against a corpus that measured ~73% false
positives on its own code-aware checks); and it is
well-formedness-as-a-type, settled 2026-08-02 — with the added twist that
here the ecosystem enforces it upstream, so a downstream implementation
would re-check what could not have been constructed.

**N3. Reading `.archimate` or Model Exchange XML. Refused on scope and
identity.** It is a different artefact class, an XML schema, and a
different product. The zero-dependency promise survives it (stdlib has an
XML parser) — which is exactly why it needs refusing on identity instead:
this is a PlantUML linter, and "we also read Archi files" is a second
product with a second corpus, a second calibration and a second golden
contract.

**N4. Reading the ecosystem's density as opportunity. Refused.** Six
commercial tools, an Open Group standard, a mature open-source workbench
and a cluster of MCP servers describe a *well-served* market, not an
underserved one. The C4 note already recorded the general form of this
error; ArchiMate is where it would be easiest to make.

## 7. Fit — the candidate fits, graded

### F1 — an ArchiMate rule pack over PlantUML. **No. Not "wait" — no.**

N1 and N2. This is the first candidate in the three evaluations to fail on
something other than demand, and it is worth being explicit about why the
distinction matters: the C4 settlement can be flipped by an adopter, and
this one cannot, because the objection is to the artefact rather than to
the market. Recording it as a plain no is what stops it being re-derived
every time someone notices ArchiMate is popular.

### F2 — fixing the mistyping so ArchiMate files fail honestly. **Yes in principle, and it is not an ArchiMate item.** 

This is the real candidate, and F1's refusal does not touch it: whatever
is decided about packs, a file this tool cannot model should not score
**Level 4 (Precise)**. Because the mechanism is notation-general (§8.1),
the fix belongs to the integrity-cap family (C6, C7, the syntax-gate
disclosure, the DIM-AMB residual) rather than to any notation. Two shapes
are available and both are scoring changes needing their own decision and
a deliberate golden re-freeze:

- **Widen the type-marker set** so `archimate` (and the other
  non-sequence declaration keywords) type a file `unknown` rather than
  letting arrows decide. Narrow, cheap, and does not touch scoring
  directly — but it is a typing change, which moves scores.
- **Make the cap sensitive to how the type was reached** — a diagram
  whose participants are *all* implicit and which contains no declaration
  line was typed by fallback, not by recognition, and could carry the same
  disclosure the syntax gate does ("typed by fallback; verdict assumes the
  dialect was recognized"). Honest without guessing.

Recorded, not queued: it is a scoring change, and this project does not
make those as drive-bys.

### F3 — supporting Archi's `.archimate` / Model Exchange XML. **Nonsense.** N3.

### F4 — the CI-gate gap in Archi's validator. **Real, and not this project's.**

S2. Worth recording because it is the only genuine unmet need found in the
ecosystem, and because someone reading these notes later might otherwise
mistake it for one. The right tool is jArchi plus ACLI, written by someone
who already has the model in hand.

### F5 — grading ArchiMate models. **Unoccupied, unreachable, and third in a row.**

Nothing found in this ecosystem produces a maturity level, gap report or
ratchet over a model — the same result as Structurizr, LikeC4 and
Linked.Archi. Four ecosystems now, no grader. But unlike C4, this one is
unreachable from the artefact pumllint can see (§3), so the observation
strengthens the *positioning* and supplies no path.

### F6 — the ArchiMate-generated-PlantUML population as a corpus. **Recorded, not queued.**

An interesting inversion: if `.puml` ArchiMate is machine-generated, then
a linter over it is a **generator conformance check** — did the export
preserve the model? — which is a legitimate question and not this
product's. The reason to record it is the hazard, not the opportunity:
those generated files score Level 4 today (§8), so anyone feeding an
exported ArchiMate view into an AI codegen loop and gating on pumllint
gets a *passing* verdict on a diagram this tool did not read. That is the
F2 candidate's strongest motivation.

### Fit against declared constraints

| Declared constraint | Where the ArchiMate fits land |
|---|---|
| **Zero runtime dependencies** | **Passes** for F2. Passes technically for F3 (stdlib XML) — which is why F3 is refused on identity instead. |
| **Deterministic product path, no LLM** | **Passes** throughout. |
| **Byte-stable, contract-pinned outputs** | **Passes.** F2 changes verdicts, not shapes. |
| **Golden score contract** | **Material for F2**: both shapes move corpus scores and need a deliberate re-freeze. |
| **Demand-driven / Arc E bar** | F1 **fails and would keep failing** — the objection is the artefact, not the market. F2 is **maintainer self-demand** with a measured defect behind it, which is the WS3a / link-integrity label. |
| **Claim language is settled** | No corrections required. Nothing on file claims anything about ArchiMate. |

## 8. Gap — measured

### 8.1 Which arrow notations cost a file its honesty

Two `archimate` element declarations plus one relationship, varying only
the relationship notation. Default config, outside the repo:

| Relationship notation | ArchiMate use | Result |
|---|---|---|
| `-up->` | directional layout hint | `unknown`, Level 1, 0 elements — **honest** |
| `-down->>` | flow | `unknown`, Level 1, 0 elements — **honest** |
| `*-down-` | composition | `unknown`, Level 1, 0 elements — **honest** |
| `-->` | plain dashed | **`sequence`, Level 4, 91.67, 3 elements** |
| `->` | plain solid | **`sequence`, Level 3, 90.0, 3 elements** |
| `..>` | **realization** | **`sequence`, Level 4, 91.67, 3 elements** |
| `--` | **association** | **`sequence`, Level 4, 91.67, 3 elements** |

The safe forms are the ones carrying a direction hint or a decoration at
both ends; the unsafe forms are the undecorated ones — which include two
of ArchiMate's most-used relationship types. Nothing about that split is
designed; it falls out of which tokens the sequence recognizer matches.

**The mechanism generalises, and the type-marker rule is what saves the
other dialects:**

```
bare arrows, no declarations at all        type='sequence' level=4 score=91.0  elements=5
class KEYWORD present (a type marker)      type='class'    level=4 score=98.33 elements=3   ← correct
archimate keyword (NOT a type marker)      type='sequence' level=4 score=91.67 elements=3   ← wrong
component brackets [A] --> [B]             type='unknown'  level=1 score=95.0  elements=0   ← honest
```

**And one arrow is enough to escape the honesty cap:**

```
zero arrows                                type='unknown'  level=1 score=95.0  elements=0
one arrow (2 endpoints + 1 message = 3)    type='sequence' level=4 score=91.67 elements=3
```

Cap C6 fires only at `element_count == 0`, and Level 4 requires ≥ 3
elements. A single undecorated arrow produces exactly 3. The gap between
"nothing modelled" and "Precise" is one line.

### 8.2 The full native-dialect measurement

A five-element, four-relationship ArchiMate model in PlantUML's native
form:

```
archimate #Technology  "Firewall"            as firewall <<technology-device>>
archimate #Application "Payment Application" as payApp   <<application-component>>
archimate #Application "Payment Service"     as paySvc   <<application-service>>
archimate #Business    "Corporate Client"    as client   <<business-actor>>
archimate #Technology  "Payments DB"         as db       <<technology-node>>

firewall -up-> payApp
payApp   -up-> paySvc
paySvc   -up-> client
payApp   -->   db
```

What the parser reads:

```
type = sequence        elements = 3
participants  : {'payApp': ('implicit', declared=False), 'db': ('implicit', declared=False)}
messages      : 1  →  {'source': 'payApp', 'target': 'db', 'label': '', 'arrow': '-->'}
```

Five declared elements become zero participants. Four relationships become
one message. Verdict:

```
$ python3 -m pumllint native.puml
native.puml:13: [SEQ009/minor] Return '<unlabelled>' from 'payApp' to 'db' pairs with no preceding call
$ python3 -m pumllint score native.puml
  type='sequence'  level=4 (Precise)  score=93.33  elements=3
```

**Level 4 (Precise), 93.33/100, on a diagram of which it read one third
and misread all of it.**

### 8.3 The codegen profile amplifies it, as it did for C4

```
$ python3 -m pumllint --profile codegen native.puml
native.puml:13: [SEQ009/minor]   Return '<unlabelled>' … pairs with no preceding call
native.puml:13: [SEQ101/blocker] Participant 'payApp' is created implicitly on first use; declare it …
native.puml:13: [SEQ101/blocker] Participant 'db' is created implicitly on first use; declare it …
native.puml:13: [SEQ109/minor]   Reply '<unlabelled>' is empty or a generic label …
✖ 4 issue(s): 2 blocker, 2 minor                                          (exit 1)
```

Both SEQ101 blockers instruct the author to declare participants that
*are* declared — as `archimate #Application "Payment Application" as
payApp`. This is the same amplification the C4 note measured a day
earlier: the profile this project recommends for agent workflows is the
profile that handles unrecognized dialects worst, because its rules are
stricter about a structure it inferred rather than read.

### 8.4 The defect class, across three notations

Assembling the three evaluations:

| Note | Input | Escape mechanism | Verdict reported |
|---|---|---|---|
| C4 (2026-07-27, re-run 2026-08-27) | C4 macros + raw arrows | undecorated arrows | `sequence`, Level 4, 88.96 |
| Linked.Archi (2026-08-27) | component diagram + one `database` declaration | a sequence-participant keyword | `sequence`, Level 3, 100 |
| This note (2026-08-27) | native ArchiMate | one undecorated arrow | `sequence`, Level 4, 93.33 |

Three notations, two distinct escape mechanisms, one honesty cap. The C4
note recorded its instance as a coverage observation; the Linked.Archi
note recorded its instance as an integrity-cap residual "found on one
probe, not a corpus measurement". With a third instance and a token-level
characterization, the class is no longer an anecdote. The repository
applies that standard elsewhere by name — the Arc C XD coherence item is
gated on "a second corpus or an adopter showing the same defect class —
one corpus is an anecdote". That trigger belongs to that item and is not
inherited here; it is quoted as the house standard for when an
observation becomes a class, and by it this one qualifies.

What it is *not* is a defect in any rule: every rule does what its catalog
row says, and the sequence recognizer is doing its documented job on a
file nothing else claimed. It is a **typing-confidence** gap, and it
belongs beside C6, C7 and the syntax-gate disclosure — all of which exist
to say what was not checked.

## 9. SWOT

Scope: *pumllint's position relative to the ArchiMate ecosystem*.

**Strengths (internal, favourable)**

- Grading remains unoccupied — now across four ecosystems.
- The ambiguity dimension has no counterpart anywhere in ArchiMate,
  because a metamodel cannot make "TBD" illegal.
- The evaluation discipline caught a general defect from a
  notation-specific question, and the fix is small and already located.

**Weaknesses (internal, unfavourable)**

- The measured mistyping is the worst of the three ecosystems, and the
  codegen profile makes it worse.
- Nothing in the reachable artefact set corresponds to where ArchiMate
  models live.
- A generated `.puml` scoring Level 4 is a live hazard for anyone gating
  an agent loop on it (§7/F6).

**Opportunities (external, favourable)**

- None that are this project's. The one unmet need found (Archi's
  missing CI gate) belongs to jArchi/ACLI, and saying so plainly is worth
  more than a strained fit.

**Threats (external, unfavourable)**

- **Silent wrong verdicts.** Unlike absence of coverage, a Level 4 on an
  unread diagram is a claim, and it is wrong. This is the only threat in
  the three evaluations that is *this project's own behaviour* rather
  than a market movement.
- **Prevention beats verification where the metamodel is formal.** The
  MCP servers show what that looks like fully built. The defensible
  residue is exactly the part no metamodel can encode — which is where
  the evidence already points.

## 10. Decision, recorded candidates, triggers

**Decision: no ArchiMate support of any kind — no pack, no `.archimate`
reader, no wait-for-pull. One general candidate is recorded, and it is not
an ArchiMate item.**

**Never build:**

- An ArchiMate rule pack over `.puml` — the artefact is a generated
  rendering of a model held elsewhere, so findings cannot be durably
  acted on (N1). Unlike the C4 settlement, an adopter does not flip this.
- Relationship-legality or derivation rules from the ArchiMate tables —
  legality is the settled anti-goal, and this ecosystem enforces it
  upstream by construction (N2).
- A reader for `.archimate` or the Open Group Model Exchange XML — a
  second product, refused on identity rather than on dependencies (N3).

**Recorded, not queued:**

1. **Typing-confidence disclosure or type-marker widening** — the one
   real candidate, and notation-general. A file with no recognized type
   marker is typed `sequence` by a single undecorated arrow (`->`,
   `-->`, `..>`, `--`), producing exactly the 3 elements needed to escape
   cap C6 and clear the Level-4 floor. Two shapes, both scoring changes
   needing their own decision and a deliberate golden re-freeze: widen the
   type-marker set so declaration keywords like `archimate` type a file
   `unknown`; or make the cap sensitive to fallback typing (all
   participants implicit, no declaration line) and disclose it the way the
   syntax gate does. **Maintainer self-demand with a measured defect
   behind it** — the WS3a / link-integrity label. Supersedes the
   Linked.Archi note's component-diagram residual, which is the same class
   by a different mechanism.
2. **The generated-`.puml` hazard** (§7/F6) — exported ArchiMate views
   score Level 4 today, so a pipeline gating an agent loop on pumllint
   gets a passing verdict on a diagram the tool did not read. The
   motivation for candidate 1, recorded separately because it is the
   consequence a user would actually meet.
3. **Archi's missing CI validation gate** — recorded as *not this
   project's*, so a later reader does not mistake it for an opening. The
   ecosystem's own path is jArchi plus ACLI. *(Status unverified — see
   Bounds.)*

**Re-litigate this settlement on any of:**

- Evidence that hand-authored (not exported) ArchiMate PlantUML is a real
  population — which would attack N1's premise, the only load-bearing one.
  Note the census exclusion rule recorded yesterday applies here in full:
  a sample gallery is not a population.
- PlantUML gaining a first-class ArchiMate model semantics that makes the
  `.puml` an artefact of record rather than a rendering.
- An adopter whose ArchiMate models live in PlantUML *only*, with no
  upstream tool — possible, and the case where N1's objection genuinely
  does not apply.

Candidate 1 has no trigger: it is a defect-class fix awaiting a decision,
not a build awaiting demand.

## Related reading

- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — the
  nearest prior; its "raw arrows are the mechanism" finding is the first
  instance of §8.4's defect class, and its codegen-amplification result is
  reproduced here in a second dialect.
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) — the
  second instance (component diagram, one `database` keyword), whose
  recorded residual candidate 1 supersedes; also the SHACL formalization
  of the ArchiMate tables discussed in §1.1.
- [Model verification beyond linting](model-verification-evaluation.md) —
  the well-formedness-as-a-type anti-goal N2 rests on, here observed
  correctly applied by someone else.
- [SCORING.md](../SCORING.md) — cap C6, cap C7 and the integrity-cap
  family candidate 1 would join.
- [Using pumllint from a coding agent](agents.md) — the profile §8.3
  measures and the loop §7/F6's hazard would sit inside.
