# A knowledge graph for pumllint — sense, nonsense, fit, gap, SWOT

*Dated evaluation, 2026-08-26, written against `3cb39ff` (post-v0.28.0).
The question as posed: define a knowledge graph for pumllint in the sense
of graph engineering, and assess its sense/nonsense/fit/gap/SWOT for two
named use cases — continued AI-assisted development of the project, and
rule-set extension/validation.*

**Verdict up front: mostly nonsense as infrastructure, and largely
redundant as an idea — because the graph already exists and is already
queried. pumllint's parsed model *is* a labelled property graph; 14 of
its 51 rules are already graph algorithms over it (9 intra-diagram
traversals, 5 cross-diagram joins over a global symbol table); and
`pumllint trace` is already a bipartite requirement↔diagram graph. What a
knowledge-graph layer would add on top is a store, a schema language and
a maintenance burden, against a measured corpus of 950 elements — three
orders of magnitude below where graph infrastructure starts paying. Two
things survive the triage. The first is vocabulary: entity resolution,
identity, provenance and shape validation are better names for things
this repository already ships, and they make three recorded-but-unqueued
items legible as one arc. The second is a genuinely new, cheap candidate
that came out of applying the graph lens and is *not* a graph: a
deterministic link-integrity check over the repository's own
claim→record→trigger web, which is where the one real gap is. Along the
way the same lens produced a concrete rule-set-coverage finding — DIM-AMB
carries zero rules for activity and use-case diagrams, so a quarter of
the composite is vacuous for those types — from a ten-line pivot over
`catalog.toml`, with no graph involved. That is the whole argument in
miniature.**

*Bounds: every repository claim below was executed against the working
tree at `3cb39ff` and the commands are quoted so they can be re-run.
Library licences were verified against PyPI metadata. The external
literature (GraphRAG benchmarks, KG-project failure surveys, GQL/SHACL)
is characterized from web search summaries, not fetched primaries —
arxiv.org, dl.acm.org and w3.org are unreachable from this environment —
and is kept deliberately non-load-bearing: no verdict below rests on an
external number. Where one is quoted it is marked as characterization.*

## 0. Why this evaluation ran, and what it is not

This is the sixth externally-prompted analysis run under the house
discipline (after the prose-pipeline reassessment and spec-stack
recommendation, 2026-07-29; the capability-horizon mapping, 2026-08-01;
the model-verification note, 2026-08-02; and the two-stage project
review, 2026-08-11). It follows their shape: state the proposal so it
stands alone, verify every claim against the tree, grade, and record with
triggers so it is not re-derived.

It is *not* a build proposal. Nothing in it is queued. Section 10 records
what would have to become true first.

One term needs pinning before anything else, because "knowledge graph"
names three different proposals that deserve three different verdicts:

- **(A) The diagram graph** — the parsed model itself (participants,
  messages, classes, states, transitions) persisted as nodes and edges in
  a graph store and queried with Cypher/GQL or SPARQL.
- **(B) The rule/method graph** — pumllint's own metadata (rules,
  dimensions, severities, levels, profiles, evidence, decision records)
  as a linked ontology, for reasoning *about* the rule set.
- **(C) The repository graph** — code, docs, ROADMAP records, evidence
  waves and their cross-references as a retrieval substrate for
  AI-assisted development (the GraphRAG shape).

The question as posed spans all three. They are graded separately from
§3 onward, because collapsing them is the main way this idea gets
adopted for the wrong reason.

## 1. What "graph engineering" and "knowledge graph" actually name

Compressed so this note stands alone, and so the fit assessment is
against the real discipline rather than a caricature.

**Graph engineering** is the practice of designing, building and
maintaining systems whose primary data structure is a graph: modelling
entities and relationships as first-class citizens, storing them in a
graph-native engine, and querying them by traversal rather than by join.
Its two mature data models are:

- **RDF triples** (subject–predicate–object), with a standards stack on
  top: OWL for ontologies and inference, SHACL for constraint validation,
  SPARQL for querying. Strong formal semantics; verbose; traversal is
  comparatively expensive because everything decomposes to triples.
- **Labelled property graphs (LPG)** — typed nodes and edges that carry
  key/value properties directly. Queried with Cypher and, since April
  2024, with **ISO/IEC 39075:2024 (GQL)**, the first new ISO database
  query language standard since SQL. Faster for multi-hop traversal;
  weaker formal semantics, no standard equivalent of OWL inference.
  *(Characterization from search summaries; the GQL date and designation
  are the only load-bearing facts here and are widely corroborated.)*

A **knowledge graph** is the applied artifact: a graph whose schema is an
explicit ontology, whose contents are extracted from heterogeneous
sources, and whose value proposition is that questions spanning many
sources become single traversals. The literature's canonical lifecycle is
*identify sources → build the ontology → extract → reconcile → construct
→ **maintain***, and the reported failure mode concentrates almost
entirely in that last step: ontology drift — the schema silently ceasing
to describe reality — is the standard named killer, and surveys put
production adoption low (one 2025 figure quoted at 27% of organizations)
with abandonment common inside 18 months. *(Characterization; treat the
percentages as directional.)*

Three properties of the discipline matter for the verdict, and all three
are about *when* it pays:

1. **It pays at scale and connectivity.** Graph engines exist because
   join-heavy traversals over 10⁶–10⁹ edges are intractable relationally.
2. **It pays across heterogeneity.** The win is unifying sources that do
   not share a schema.
3. **Its cost is the ontology and its upkeep, not the store.** Standing
   up a store is days; agreeing and maintaining a schema is the project.

## 2. What is already a graph here (measured)

This is the section that decides most of the verdict, so every number is
reproducible.

**The parsed model is already a labelled property graph.** Read
`pumllint/model.py` as a graph schema and the correspondence is exact:

| Graph concept | pumllint |
|---|---|
| Typed node with properties | `Participant` (kind, stereotype, declared, display_name), `ClassEntity` (+ members), `StateNode` (composite, container), `ActivityNode` |
| Typed edge with properties | `Message` (arrow, label, async, return, activation shortcuts), `ClassRelation` (kind, cardinalities, label), `StateTransition` (label, container), `UseCaseLink` (arrow, label, stereotype) |
| Subgraph / containment | `Block` (alt/opt/loop/par + `else_branches`, with `contains_line`), `StateNode.container` |
| Node property projection | `Diagram.element_count`, `prose_directives()` |
| Path / matching query | `pair_calls_and_replies()`, `walk_activation_stack()` |

**14 of 51 rules are already graph queries** — nine intra-diagram graph
algorithms plus the five cross-diagram joins. Read from the sources at
`3cb39ff`:

| Rule | Graph operation |
|---|---|
| CLS004 | depth-first cycle search over the generalization hierarchy |
| STA002 | in-degree test (self-loops excluded) |
| UC001 | degree-zero test |
| UC003 | one-hop neighbourhood query (which use cases an actor reaches via plain links), then edge-direction check against it |
| SEQ002 | set difference: declared nodes minus the union of edge endpoints and activation participants |
| SEQ009 | reverse-edge existence over the ordered edge list |
| SEQ104 | call/reply matching (`pair_calls_and_replies`) |
| SEQ108 | per-lifeline stack replay (`walk_activation_stack`) |
| SEQ107 | edge-in-subgraph containment (calls to external/db/queue nodes inside a failure-handling block) |

A coarser automated cut over the same sources — how many rules read more
than one model collection or use a path helper — agrees on the order of
magnitude:

```
single-collection scans: 38   multi-collection / helper-using: 8   cross-diagram: 5
```

(The two cuts differ on four rules and neither is wrong: CLS004 and
SEQ009 do graph work *inside* one collection, while SEQ106 and UC003
span several without necessarily traversing. The table above is the
hand-verified reading and is the one quoted elsewhere in this note.)

The five XD rules are a **global entity-resolution join**: one symbol
table across the whole batch, one entity → one kind, one stereotype, one
spelling — with a per-entity `authoritative` option that is precisely the
master-data "golden record" pattern, and a deliberate refusal to elect a
majority winner (issue #36).

**`pumllint trace` is already a bipartite graph** — requirement IDs on
one side, diagrams on the other — and reports all three directions a
graph query would: covered, unlinked, and dangling references to IDs the
inventory does not contain.

**The scale is three orders of magnitude below graph-store territory.**

| Corpus | Diagrams | Nodes+edges | Time |
|---|---|---|---|
| Wild public corpus (`pilot_results/first_contact/census.json`, 159 files from five repos) | 174 | **950** | 0.6 s census |
| Repo diagrams (`examples/`, `c4_experiment/`, repaired waves, lint-flow) | 79 | 474 | 33 ms parse |
| `examples/` + lint-flow, full codegen lint **including the 5-rule cross-diagram join** | 15 | — | **3.0 ms** |

950 elements is a Python dict. The cross-diagram join that a graph
database would exist to accelerate completes in single-digit
milliseconds over the whole batch.

**The rule catalog is already a small ontology with enforced referential
integrity.** `catalog.toml` holds 51 rules × 5 typed facts (name,
severity, dimension, applies_to, profiles) ≈ 255 assertions over a closed
vocabulary of 6 dimensions, 5 severities, 5 diagram types plus a
wildcard, and 1 profile.
`@register` fails at import time on a missing entry; `tests/test_catalog.py`
guards catalog↔registry parity; `tests/test_schema.py` sync-tests the
enums against the code's canonical sets. That is an ontology with a
validator — expressed in TOML and asserts, at roughly 1% of the cost of
expressing it in OWL.

**The conclusion this section forces:** the question "should pumllint
have a knowledge graph?" is malformed. It has one. The real question is
whether *persisting, externalizing and query-languaging* it pays. The
rest of this note answers that.

## 3. Sense — the four true things in the proposal

**S1. The framing is right about the substrate, and always has been.**
The README's founding premise — PlantUML is a drawing tool, not a
modelling tool — is the knowledge-graph thesis for this artifact class:
the picture is not the asset, the entity-relationship structure behind it
is. Every rule reasons over that structure and never over raw text. A
proposal to "add a knowledge graph" is, at its best, a proposal to keep
doing what the architecture already does.

**S2. The growth directions already recorded are graph-shaped, and the
lens names them better than the records do.** Three items sit
recorded-but-unqueued in the ROADMAP, filed under three different
settlements, and they are one thing: **cross-artifact identity**.

| Recorded item | Graph reading |
|---|---|
| Sequence ↔ contract cross-check (2026-07-29) — message signatures against OpenAPI/AsyncAPI operations | Edge type joining a diagram node to a contract node |
| Glossary / approved-term rule (2026-08-02) — declared names resolved against a project term inventory | Entity resolution against a controlled vocabulary |
| Model→spec change-impact (2026-08-10) — invalidation semantics over `trace`'s link table | Reachability over the traceability edges |

Add the shipped XD pack (diagram↔diagram identity) and `trace`
(diagram↔requirement) and the arc is: *one entity, one identity, across
progressively more artifact classes*. That is exactly what a knowledge
graph is for. The lens earns its keep here as a **naming and sequencing**
device — it does not add a build, and each item keeps its own recorded
trigger.

**S3. Multi-hop and global-sensemaking queries are where graph retrieval
genuinely wins, and this repository has exactly one such query class.**
The benchmark picture (characterization) is consistent: graph retrieval
ties plain chunk retrieval on simple fact lookup and wins by roughly
10–13 points on complex multi-hop reasoning and global summarization.
The repository's multi-hop class is not the diagrams — it is the
governance record: *which settled question governs this proposal, what
is its trigger, which wave produced the number it rests on, and has a
later dated note superseded it?* That is a four-hop question over the
ROADMAP's eleven settled questions and their dated superseding notes
(60 date stamps in that one file) plus 28 docs. It is real, and §8
grades whether a graph is the right answer to it.

**S4. The failure mode graph engineering warns about is one this project
already inoculates against.** Ontology drift — the schema quietly ceasing
to describe reality — is the named killer of KG projects, and the
standard advice is *start with the smallest ontology that delivers value
and budget for curation before launch*. The rule catalog is exactly that:
smallest viable vocabulary, integrity-tested, with corpus-firing analysis
(`tools/corpus_firing.py`) as the drift detector. The discipline transfers
in the direction the literature does not usually get: this project would
be an unusually *good* KG shop, which is a reason to trust its judgment
that it does not need one, not a reason to build.

## 4. Nonsense — five moves to refuse, and why

**N1. A graph database or triple store as runtime substrate. Refused on
scale and on the working agreement.** 950 elements, 3.0 ms for the full
cross-diagram join. The zero-dependency promise ("product code and its
tests must run under `python tests/run_tests.py` with the stdlib only")
excludes the mature stacks from the product path outright. Note the
refusal does *not* lean on licensing, which was checked rather than
assumed: `rdflib` is BSD-3-Clause, `pyshacl` Apache-2.0, `networkx`
BSD-3-Clause, the `neo4j` driver Apache-2.0, `kuzu` MIT (verified against
PyPI metadata, 2026-08-26). Unlike the Eclipse/EPL case in the
prose-pipeline settlement, licensing is genuinely not the blocker here —
saying so keeps the argument honest and keeps the extras door open for
`tools/`, where the packaging settlement already puts lab machinery.

**N2. An LLM-extracted knowledge graph anywhere on the product path.
Refused twice over.** It violates the deterministic-product-path
agreement ("no LLM call ever ships inside pumllint itself"), and it
inserts *invention* upstream of the gate whose entire measured purpose is
to catch invention. The agent-repair wave measured what happens when a
model supplies content a diagram does not contain: −6 pp pooled executed
correctness versus the unrepaired originals, and −53 pp on a single
diagram from one invented guard. An extraction layer that infers an edge
the author never drew is the same failure with a graph schema on it —
worse, because the inferred edge would then look like model content to
every rule downstream.

**N3. OWL/SHACL as the rule engine. Refused on two independent grounds.**
First, it is *well-formedness as a type* in new clothes — the anti-goal
already settled on 2026-08-02: representable ill-formedness **is** the
product. Findings, levels, ratchet and `fix` all require that an
ill-formed model be constructible, inspectable and scoreable. A validator
that rejects rather than reports deletes the product. Second, and less
obviously: pumllint's parser is a **tolerant projection** — it skips
lines it does not recognize, which is why the census found 103 of 174
wild diagrams "dialect-invisible", held at Level 1 by the zero-element
cap. Closed-world shape validation over an open-world projection reports
*absence of parse* as *absence of fact*. That is the C4 mistyping failure
generalized to every constraint at once. (Arc H already carries the
matching requirement for the verbalizer: unmodelled-content disclosure is
a build requirement, not a nicety.)

**N4. Inferring missing edges. Refused — it is the participant-pair sweep
with better ergonomics.** "The graph shows A calls B and B calls C but
nothing calls C directly — is an interaction missing?" is precisely the
question rejected on 2026-07-30 *regardless of implementation effort*,
because the complement of a diagram is not a set of omissions: there is
no oracle, so every absent edge is equally "missing" and the
false-positive rate is ~100% by construction. A graph query language does
not supply the missing oracle; it makes the unanswerable question
one line long, which is a hazard and not a feature. The decidable version
remains what it was: a *declared* obligation table (an `[obligations]`
selector × failure-mode matrix), which is an oracle someone wrote down —
already specced, already adopter-gated.

**N5. Graph-derived metrics as a maturity signal. Refused on Goodhart and
on evidentiary standard.** Centrality, density, clustering coefficient
and their friends are available the moment a graph exists, and they are
plausible. The scoring model's numbers are not plausible — they are
calibrated against an execution oracle and frozen behind a golden test,
and the auto-improvement settlement already recorded why a
plausible-but-uncalibrated fitness signal decays into optimizing for
itself. Any graph metric entering the score must clear EVIDENCE.md's bar,
which means a wave under charter §10 discipline, which nobody has asked
for.

## 5. Fit — against this repository's declared constraints

| Declared constraint | Where a knowledge-graph layer lands |
|---|---|
| **Zero runtime dependencies** (working agreement) | **Fails** for the product path (store, RDF stack, or `networkx`). **Passes** in `tools/` under the extras door — where the packaging settlement already puts lab machinery. |
| **Deterministic product path, no LLM** | **Passes** for a deterministically-built graph; **fails** for any extraction leg (N2). |
| **Byte-stable, contract-pinned outputs** (`-f json` shapes, HTML report, forward-slash paths) | **Passes with a new burden.** Traversal order is a nondeterminism surface; the repo already pays this tax deliberately (`_variant_summary` ranks by count then alphabetically "so the message reads the same whichever file sorts first"). Every graph-derived output would need the same treatment. |
| **Statelessness** (only `maturity.json` persists, and it is one level per diagram) | **Fails in spirit.** A knowledge graph is state, and the literature's dominant failure mode is that state going stale while continuing to look authoritative. The baseline file is deliberately the thinnest possible persisted artifact. |
| **Demand-driven / the Arc E bar** ("build only for a concrete user whose need the current tool cannot meet") | **Fails.** No adopter has asked; the phase-0 pilot census on a real organisation's corpus has not run; the recorded next action is that measurement, not a build. |
| **Golden score contract** | **Manageable.** Any new rule shifts corpus scores and needs a deliberate diff-verified re-freeze. Normal cost, not a blocker. |
| **Licence posture** (GPL-3.0-or-later, no EPL, no AGPL, non-relicensing commitment) | **Passes.** Verified above — the graph ecosystem is BSD/MIT/Apache. This constraint, which bound the Eclipse MDE question, does not bind here. |

Net fit: **the product path is closed; `tools/` is open; the gate that
actually matters is demand, and it is shut.**

## 6. Gap — what a knowledge graph would supply that nothing supplies today

Four candidates. Three are already owned or already refuted. One is real.

**G1. Cross-repository / cross-organisation identity.** A diagram in one
repo, a contract in another, a requirement in a tracker. Genuinely beyond
the current architecture, which resolves identity only within a single
lint batch. But the *next concrete instance* of it — the recorded
sequence↔contract cross-check — is a file-to-file comparison against
machine-readable data, which needs a parser and a rule, not a graph
store. **Owned, gated, cheaper without a graph.**

**G2. Persistence and change impact over time.** "This diagram changed;
which requirements, contracts and downstream diagrams are now suspect?"
This is the recorded model→spec change-impact design (invalidation over
`trace`'s link table), and its recorded gate is exactly right: write it
only after a real diagram-edit event has flowed through a pilot pipeline.
A graph is one plausible implementation of the link table; the link table
already exists. **Owned, gated.**

**G3. Global queries at a scale the batch cannot hold.** Real in
principle, absent in fact: the largest measured corpus is 950 elements.
**This is the trigger, not the gap** — see §10.

**G4. The repository's own claim → record → evidence → trigger web. This
is the real gap, and it has no owner.** The project's most valuable asset
is not the code; it is eleven dated settled questions and their
superseding notes, each with a verdict, a trigger, and citations into
EVIDENCE.md, the wave pre-registrations and the docs. That web has no
integrity check. Every cross-reference, every quoted figure, every
"recorded, not queued" and its trigger is maintained by hand and verified
by reading. And it has already failed once in a way that mattered: the
two-stage external review (2026-08-11) found a genuine contradiction —
`scoring.py` and the score schema naming Level 5 "Generation-ready" while
`docs/agents.md` asserted the level is "deliberately not called
'generation-ready'", making that sentence false while the name stood. A
human reviewer caught it. Nothing mechanical would have.

That gap is real, it is this repository's, and — the point of this
section — **its fix is not a knowledge graph.** It is a deterministic
link checker: resolve every relative doc link, every `§`-and-file
citation, every rule ID mentioned in prose against `catalog.toml`, every
level name against `LEVEL_NAMES`, and report the dangling ones. It is the
`trace` pattern (inventory + references + three directions of report)
applied to the repository's own prose, in `tools/`, stdlib-only. The
graph lens found the gap; the graph machinery is not the remedy.

## 7. SWOT

Scope: *adopting knowledge-graph engineering in or around pumllint*.

**Strengths (internal, favourable)**

- The substrate exists and is stable: a labelled property graph with a
  documented schema (`model.py`) and three schema-pinned report shapes.
- Entity resolution already shipped and already thoughtful — the XD pack
  refuses majority election and offers an `authoritative` pin.
- A bipartite traceability graph already shipped (`trace`), with all
  three report directions including dangling references.
- The metadata vocabulary is small, closed and integrity-tested at import
  time and in CI.
- Governance culture — pre-registration, golden contracts, corpus-firing
  analysis, published failures — is exactly the maintenance discipline KG
  projects are measured to lack.

**Weaknesses (internal, unfavourable)**

- Scale is ~10³ elements against a discipline built for 10⁶–10⁹.
- The zero-dependency promise excludes every mature graph stack from the
  product.
- Statelessness is a deliberate product property; a KG wants state.
- The parser is a tolerant projection: any graph built on it silently
  omits unmodelled content, and would present that omission as fact.
- No adopter demand, and no pilot corpus yet — the demand instrument
  (phase-0 census on a real organisation's corpus) has not run.

**Opportunities (external, favourable)**

- Vocabulary transfer: *entity resolution, identity, provenance, shape
  validation, projection* are better names for shipped behaviour and
  improve external legibility of the docs.
- Sequencing: the lens turns three orphaned recorded items into one
  coherent cross-artifact-identity arc (S2) — useful the moment any one
  of them gets pulled.
- The link-integrity check (G4) — small, stdlib, high leverage, and it
  protects the asset that external reviewers consistently rate highest.
- If graph-shaped retrieval over the repository is ever wanted, the
  ROADMAP already *is* the index; a generated link graph falls out of G4
  as a by-product rather than as a project.

**Threats (external, unfavourable)**

- **Ontology drift.** The measured number-one KG failure mode, and the
  worst possible one here: a stale graph that still looks authoritative
  is the invented-guard hazard moved one layer up the stack.
- **The no-oracle temptation.** A query language makes "what edge is
  missing?" trivially expressible and no more answerable (N4). This is
  the threat most likely to actually materialize, because the query looks
  reasonable right up until you ask what makes an answer correct.
- **Dependency and release-train creep** — the lesson already recorded
  against the Sonar plugin.
- **Goodhart via graph metrics** (N5).
- **Opportunity cost.** The recorded next action is measurement on a real
  corpus. A graph build would consume the attention that action needs,
  and would be justified by the corpus it is displacing.

## 8. Use case A — continued AI-assisted development

The honest question is not "would a knowledge graph help an agent
understand this repository?" but "what actually costs an agent time
here?" Two things, measured by how this repository is actually worked:

1. **Knowing which settled question governs a proposal**, so a decided
   matter is not re-litigated. This is a lookup, and the ROADMAP's
   settled-questions section is the index — dated, verdict-first, with
   triggers written inline.
2. **Knowing whether a figure is still current**, given that several
   records carry later dated updates that supersede their own earlier
   text.

Both are *link* problems over a few dozen records, not retrieval problems
over a large corpus. The benchmark picture (characterization) says graph
retrieval ties chunk retrieval on simple fact lookup and wins on multi-hop
sensemaking; question 1 is a lookup, question 2 is two hops. Against 17.5k
lines of markdown that `grep` searches in milliseconds, the construction
and maintenance cost of a retrieval graph is not recoverable — and the
construction cost is the ontology, which is the expensive part, which
would have to be maintained by the same people who maintain the records it
describes. **The cheaper instrument already exists and is already
maintained.**

What *would* pay, and is the same candidate as G4: making the record web
**mechanically checkable** rather than more elaborately indexed. An agent
(or a human) that can run one command and learn *"this doc cites §7 of a
file that has six sections; this prose names SEQ110 which is not in the
catalog; this level name does not match `LEVEL_NAMES`"* gets more value
than one that can traverse a graph of the same prose, because the failure
this repository actually suffered was a contradiction, not a retrieval
miss.

A note on evidence, since this evaluation is itself an instance: the
workflow that produced it — read the tree, execute the claims, grade,
record with triggers — was not retrieval-limited at any point. The
binding constraint was *verification*, and a graph does not verify.

## 9. Use case B — rule-set extension and validation

Two sub-questions, with different answers.

### 9.1 Extension — no

Authoring a rule is: a RULES.md section with rationale and a Gherkin
acceptance block, a `catalog.toml` row, and a 15–40 line `check()` over
the parsed model. `discover()` auto-imports; `@register` joins; nothing
else is wired. Arc F already investigated AI-authored rules and located
the actual bottleneck, and it is **not** structure or retrieval: it is
*under-specification* — "code that passes 2–4 example scenarios yet
generalizes wrongly, and an implementer editing its own oracle". The
recorded safeguards address exactly that (spec/implementation separation,
a thickened Gherkin bar with a held-out scenario, an implementer diff
gate making the oracle read-only, the corpus-firing report, an
adversarial verify pass). A knowledge graph thickens no Gherkin block and
holds out no scenario. **It does not touch the bottleneck.**

### 9.2 Validation — yes to the question, no to the graph

"Is the rule set consistent, complete, non-overlapping?" splits three
ways, and the graph loses all three:

**Catalog integrity** — every rule has metadata, every metadata row has a
rule, every enum value is one the code knows. Already enforced:
`@register` raises at import on a missing entry, `test_catalog.py` guards
parity, `test_schema.py` sync-tests the enums. A graph would re-implement
this at higher cost. The model-verification settlement already reached
the same conclusion for the stronger property: joint satisfiability is
witnessed *constructively* by the corpus's clean probes under golden
enforcement, "with no parallel Alloy formalization to drift."

**Rule interaction** — does a new rule over-fire, shadow an existing one,
or never fire at all? This is **data-dependent, not schema-dependent**,
and it is where the symbolic instrument loses outright to the empirical
one. `tools/corpus_firing.py` already answers it, and its first run
produced a result no ontology could have: SEQ102, SEQ104, SEQ107 and
SEQ109 fire **zero times** across all 97 calibration units plus the wild
tier — the deeper codegen rules have no corpus exercise. A rule graph
would have shown those four rules perfectly well-formed, correctly
typed, correctly dimensioned, and completely unexercised. **The corpus
dominates the ontology for this question.**

**Coverage occupancy** — is any (dimension × diagram type) cell empty or
thin? This is the one genuinely symbolic question, and it is a pivot
table. Ten lines over `catalog.toml`, wildcard rules expanded:

```
dimension    sequence  activity     class     state   usecase
DIM-SEM             5         1         1         1         1
DIM-CMP             7         3         1         1         1
DIM-CON             7         5         4         3         4
DIM-TRC             4         4         4         4         4
DIM-RDB             5         2         3         2         3
DIM-AMB             6         0         1         1         0
```

**Two empty cells: DIM-AMB × activity and DIM-AMB × usecase.** DIM-AMB
carries a 0.25 composite weight — the second-heaviest dimension, and one
of the two gated at Level 4 (`l4_dim_min = 70`). With no applicable rule,
those diagram types score a vacuous **100** on it and clear the Level-4
ambiguity gate for free. Measured, at `3cb39ff`, on the same vague
content written two ways (both files carry an `owner:` tag and a
`REQ-` id so DIM-TRC is not the variable):

```plantuml
@startuml vague-activity                @startuml vague-sequence
title Handle thing —                    title Handle thing —
      owner: nobody — REQ-000                 owner: nobody — REQ-000
start                                   participant "Front" as F <<ui>>
:do stuff;                              participant "Back"  as B <<service>>
if (maybe?) then (...)                  F -> B : do stuff
  :TBD;                                 alt ...
else (...)                                B --> F : TBD
  :handle it somehow;                   else ...
endif                                     B --> F : handle it somehow
:finish TBD;                            end
stop                                    @enduml
@enduml
```

```
$ python3 -m pumllint score vague.puml --profile codegen      # activity
level 5  100.0   DIM-AMB 100.0
$ python3 -m pumllint score vague_seq.puml --profile codegen  # sequence
level 2   75.0   DIM-AMB 0.0
```

Both files say `do stuff`, `TBD` and `...`. As a sequence diagram that is
Level 2 with DIM-AMB at zero; as an activity diagram it is Level 5,
Method-complete, 100/100.

Three honesty notes on that finding, because it is easy to over-read:

- **It is a coverage observation, not a defect.** Nothing misbehaves;
  every rule does exactly what its catalog row says. The SEQ1xx codegen
  pack is sequence-only by design.
- **Half of it is already known and already guarded.** Issue #35 and
  commit `feb8789` ("Score: C7 can require an applicable Level-5 rule")
  address the Level-5 half: with `scoring.c7_requires_applicable_rules`
  the same file caps at Level 4 instead of reaching 5. The residual — and
  what the pivot adds — is that the flag caps the *level* and not the
  *dimension*: DIM-AMB still reports 100 and still clears the Level-4
  gate. It belongs to the same family as the C6 zero-element cap, the C7
  profile cap and the "Syntax gate: not run" disclosure: **structural
  honesty about what was never checked.**
- **Any fix is a scoring change**, and so a deliberate golden re-freeze
  under the working agreements — not a drive-by.

The point for this evaluation: the sharpest rule-set-validation result in
this document came from a ten-line aggregation over a TOML file that
already exists. The graph did not produce it; the *lens* did — asking
"what does the schema say is covered?" is a graph-engineering habit, and
the habit is free.

## 10. Decision, recorded candidates, triggers

**Decision: no knowledge graph, in any of the three senses. Nothing
queued.** Filed in the settled-questions style so it is not re-derived.

**Never build** (each already implied by a standing settlement; recorded
here in graph vocabulary so the next proposal lands on it):

- A graph database or triple store on the product path (zero-dependency
  agreement; 950-element measured scale).
- Any LLM-driven graph extraction, anywhere on the product path
  (deterministic-path agreement; the measured invention failure).
- OWL/SHACL as the rule engine (the well-formedness-as-a-type anti-goal;
  closed-world validation over a tolerant projection).
- Missing-edge inference rules (the no-oracle shape, already rejected
  regardless of implementation effort).
- Graph-derived metrics in the maturity score without a wave under
  charter §10 discipline.

**Recorded, not queued:**

1. **Repository link-integrity check** (`tools/link_check.py`,
   stdlib-only, lab machinery per the packaging settlement) — resolve
   every relative doc link, cross-file citation, rule ID named in prose,
   and level/dimension/severity name against their canonical sources;
   report dangling ones. The `trace` pattern turned on the repository's
   own prose. Honestly labelled: **maintainer self-demand, not adopter
   pull** — the same label WS3a carries. It is the only item here with a
   demonstrated failure behind it (the Level-5 naming contradiction,
   found by a human, 2026-08-11).
2. **Rule-coverage occupancy table** — publish the pivot of §9.2 (or
   generate it) so empty and single-rule cells are visible rather than
   discoverable. Documentation candidate; no behaviour change.
3. **The DIM-AMB coverage residual** — DIM-AMB is unreachable for
   activity and use-case diagrams, so a 0.25-weight dimension and the
   Level-4 ambiguity gate are vacuous for those types, including under
   `c7_requires_applicable_rules`. Recorded as the next member of the
   integrity-cap family (C6, C7, syntax-gate disclosure). Any fix —
   whether an ambiguity rule for those types, or a vacuity disclosure in
   the report — is a scoring change and takes its own decision and golden
   re-freeze.
4. **"Cross-artifact identity" as the arc name** for the three recorded
   items in §2/S2 (sequence↔contract, glossary/term inventory,
   model→spec change-impact). A naming and sequencing decision only; each
   item keeps its own trigger unchanged.

**Re-litigate this settlement on any of:**

- An adopter with a model set too large for a single in-memory batch —
  the honest scale trigger. Today's largest measured corpus is 950
  elements; the order of magnitude that would matter is 10⁵–10⁶.
- A concrete cross-repository identity ask (diagrams here, contracts
  there, requirements in a tracker) that the recorded sequence↔contract
  and `trace` items cannot serve.
- The pilot census on a real organisation's corpus showing a model set
  whose entity graph is materially denser than anything measured so far
  (heavy `!include` composition, deep C4 nesting).
- Outcome-grade evidence that graph retrieval beats a maintained index
  for *this* class of governance record — noting that the standing
  benchmark picture says the two tie on the lookup queries that dominate
  here.

## Related reading

- [ROADMAP.md](../ROADMAP.md) — settled questions, including the
  obligation/flow no-oracle rejection, the auto-improvement settlement
  and the Arc E build bar this evaluation is triaged against.
- [Model verification beyond linting](model-verification-evaluation.md) —
  the nearest prior evaluation: formal-methods ambitions, the
  well-formedness-as-a-type anti-goal, and the rule-set-consistency
  argument reused in §9.2.
- [Writing rules](writing-rules.md) — the authoring loop §9.1 measures
  the proposal against.
- [SCORING.md](../SCORING.md) — dimensions, weights, levels and the
  integrity caps the §9.2 finding belongs beside.
- [First contact: the pilot census on a public wild corpus](pilot-census-first-contact.md)
  — the 174-diagram / 950-element scale measurement quoted in §2.
