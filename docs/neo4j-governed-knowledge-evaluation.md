# Neo4j as a governed semantic knowledge repository for AI agents, evaluated — with an executed proof of concept

*Dated evaluation, 2026-10-30, written against pumllint `cf9d919` (v0.34.0
plus docs, after #214). The question as posed, the maintainer's research
prompt of this date: can Neo4j serve as a persistent, governed knowledge
graph of semantically transformed knowledge from heterogeneous artefacts
(BPMN, DMN, UML, requirements, architecture, code, documentation) with
explicit authorship, provenance, validation, verification and approval,
and become a trusted grounding layer for AI agents and LLMs; which
capabilities are native, which need tooling, process or custom code;
with the architectural principle that unknown, ambiguous, contradictory,
assumed, under-specified and unverified knowledge are first-class, never
silently resolved. Seven research-question groups, ten deliverables, a
proof of concept with seven controlled scenarios, and a hypothesis to be
evaluated empirically rather than assumed.*

**Verdict up front. Neo4j is suitable as the store, under conditions,
and supplies almost none of the governance itself. Everything the prompt
calls fundamental — epistemic status, provenance, verification state,
documented absence, conflict, invalidation on source change — is
application-level modelling on top of a labelled property graph that
natively offers uniqueness constraints (existence, key and type
constraints are Enterprise-only, refused by the community server at
execution, §3.4), no versioning, no history, no statement-level metadata
beyond a relationship's property map, and a closed-world pattern negation
that reads a missing edge as "no". The proof of concept, pre-registered
and executed on a local Neo4j 5.26 community server
(`kg_experiment/`), shows the store's half of the hypothesis works:
assertions with evidence, basis and status load without losing their
relationships (597 nodes, 1,472 relationships for ten artefacts);
seven Cypher rules derive corroboration, conflict, vagueness, missing
verification and staleness; a changed tariff row invalidates exactly the
four assertions its fragments support and marks the code derived from
them suspect; the three-valued answer (asserted, documented absent,
unknown) is a query. The agent's half, measured at one model with an
advisory arm (n = 5): the governed arm never generated under BLOCKED
(20 of 20 cells) and named the blocking key, gap or conflict every
time, while the documents-only baseline generated in all 35 cells,
adopted an unreviewed machine note as a decision in 4 of 5 runs and
resolved an undeclared contradiction by a precedence it invented in 4
of 5; under QUALIFIED the governed arm made its guesses findable and
its code worse. Eight pre-registered expectations held, one split,
none failed (§10). The literature's weaker figures for label obedience
across models (fact sheet C) are why the architecture still withholds
under BLOCKED rather than advising (§7). The hypothesis is therefore supported for the mechanism
and unproven for the outcome: nothing here is outcome-grade evidence
that a governed graph improves delivered software, and the measured
links between the four quality layers are thinner than the folklore
(the 100× cost-escalation claim has a 171-project null result against
it, §9). For pumllint nothing moves: the 2026-08-26 knowledge-graph
settlement's N1–N5 bind the product path, this directory is lab
territory, and the two gated candidates of 2026-10-12 (run provenance,
the sidecar as evidence record) are exactly what a consumer such as this
PoC would need from the chain. Recorded, not queued: the PoC as a
standing fixture of the thread, with the follow-on scenarios in §10.**

*Bounds. Every repository claim was executed at `cf9d919`; §12 lists
the commands. Neo4j 5.26.0 community ran locally; every Cypher statement
quoted was executed and its result recorded under `kg_experiment/results/`.
n10s was not executed (the RDF projection and SHACL validation are
Python-side, rdflib 7.6.0 and pyshacl 0.40.2); nothing is claimed about
n10s beyond its documentation. The generator was `gpt-5.1-2025-11-13`
through this environment's proxy, n = 5 per cell; every behavioural
number is capability-relative and toy-scale. The five fact sheets behind
§1, §3, §7, §8 and §9 were compiled by research subagents from primary
sources on 2026-10-30 with verbatim quotes and a "could not verify" list
each; load-bearing facts are cited at the source below, and a claim that
rests on a secondary rendering says so. Evidence classes are tagged
throughout: [capability] a documented product capability;
[standard] normative or spec text; [measured] a published measurement;
[measured here] this PoC; [measured, this repository] a measurement by
one of this repository's earlier experiments; [industry data] a
practitioner survey or vendor dataset, not peer-reviewed;
[tool-documented] a tool's own documentation of itself; [proposal] an
architectural design of this note; [proposal, executed] such a design
that the PoC built and ran; [standing settlement] a decision recorded
in this repository's ROADMAP; [hypothesis] a claim needing validation;
[unknown] not established. Schema validity, ontology conformity, traceability and
human approval are never equated with factual correctness; where the
note says "verified" it names the independent evidence.*

## 0. Why this ran, and what it is not

This is the seventh record in the knowledge-graph thread, and the first
with a graph store executed:

- the knowledge-graph note (2026-08-26): N1–N5 and four re-litigation
  triggers;
- Linked.Archi (2026-08-27): the seam, SHACL's binary conformance;
- the EA ontology stack (2026-09-14): Loop C, the generated-`.puml`
  hazard;
- the research synthesis (2026-10-12, #168): N3 read at w3.org, the
  six-way integration model, Gap 1 and Gap 2;
- the graph-store note (2026-10-16): three readings of "run pumllint on
  Neo4j", every Cypher fragment illustrative and unexecuted;
- the degradation test (2026-10-29, `recreate_experiment/degradation-2026-10-28/`):
  fifteen planted defects, six propagated, all six concealed by the
  arm's own suite, every outcome the kit's precedence rule — the
  repository's own measurement of defect propagation.

What is new: the prompt is not about pumllint. It asks for a corporate
governed knowledge layer for agents, which the 2026-10-16 note called
Loop C and left outside the seam. This note evaluates that layer on its
own terms, builds and runs the proof of concept the prompt asks for, and
then says what, if anything, bears on this repository (§11). It is not
a build proposal for pumllint, and nothing in it touches the product
path.

Where each of the prompt's seven question groups is answered:

| Prompt § | Question group | Here |
|---|---|---|
| 1 | semantic transformation and representation | §2.2, §3, §5 |
| 2 | authorship, provenance, epistemic status | §3, §4 |
| 3 | verification, governance, uncertainty management | §4, §6, §9 |
| 4 | Neo4j as a knowledge repository | §1, §3.4, §8 |
| 5 | grounding agents and LLMs | §7, §6 |
| 6 | spec-driven development and downstream quality | §9, §6 |
| 7 | evaluation and alternatives | §8, §9, §10 |

The ten deliverables are §1 (correctness assessment), §2 (reference
architecture), §3 (metamodel), §4 (lifecycle), §5 (worked example), §6
(uncertainty and contradiction demonstration), §7 (agent grounding and
enforcement), §8 (alternatives), §9 (quality framework), §10 (the proof
of concept, its results against its pre-registration, and the follow-on).

## 1. Technical correctness assessment of the proposed architecture

The prompt's architecture is correct in its separations and wrong, or
at least unsupported, wherever it expects the store or the model to do
governance work. Point by point, with what the evidence says.

**1.1 The store supplies storage and traversal, not governance.**
[capability] Neo4j 5.26 LTS and 2025.x have four constraint families —
uniqueness, existence, key, property type — and only uniqueness in
Community Edition (Cypher manual, constraints: "Create property
existence constraints — Enterprise Edition"); there is no closed schema
(the 2026.02+ "graph type" is Enterprise, Cypher 25 and explicitly
open: "a graph type only constrains the data included by the graph
type"). Versioning is a modelling pattern whose own page says
"Duplications of data cannot be avoided"; CDC (5.13+, Enterprise/Aura)
is a stream stored in transaction logs with "no memory of previous
changes"; transaction logs "are unrelated to log monitoring" and have
no query surface. A relationship is "id, relationship type, a map of
properties, start node id, and end node id"; hyperedges are "not
supported in Neo4j but can be solved by using an intermediary node".
No official page prescribes a provenance vocabulary. [measured here]
The community server refused the existence, node-key and property-type
constraints the PoC attempted, each with
`Neo.DatabaseError.Schema.ConstraintCreationFailed`, and accepted the
six uniqueness constraints (§3.4). Consequence: every construct of the
prompt's principle — assertion, evidence, basis, status, gap, conflict,
verification, approval, invalidation — is a node, a relationship or a
property the application defines and rules the application runs. That
is also true of every alternative store surveyed (§8): "no store
surveyed models verified/asserted/inferred/disputed/unknown or
documented absence natively".

**1.2 Closed-world negation is a hazard the model must design around.**
[standard] openCypher 9: "Patterns are not only expressions, they are
also predicates"; `NOT (a)-[]->(b)` excludes the pattern; `null` "means
a missing or unknown value" with `NOT null = null`. So a missing
relationship answers "no" and a missing property answers "unknown",
inside one query language. [standard] OWL is open-world ("may simply be
missing (but possibly true)"); SHACL "makes no assumptions about
whether a graph contains triples that are entailed" and reports every
absence a shape constrains (`sh:minCount`). The prompt's distinction
between a documented absence and an absence of record therefore cannot
be carried by omission: both need explicit statements. [measured here]
The PoC carries a documented absence as an assertion whose value is the
sentinel `NONE` (DT-S "review: not notified"), and a query returns one
of `asserted`, `documented_absent`, `unknown` for a key (§6, D5).
Wikidata is the production precedent: "no value" is "a positive
statement that she had no children", "unknown value" "a positive
statement that that information has not been preserved".

**1.3 Validation, verification and approval are three things, and the
store does one of them badly.** [standard] ISO 8000-8: syntactic and
semantic quality are measured by verification, pragmatic quality by
validation. [standard] SHACL §3.6.1.1: `sh:conforms` is true "if and
only if the validation did not produce any validation results"; §3.6.1.4:
"The specific values of sh:severity have no impact on the validation".
[measured here] pyshacl over the PoC's projection: an informational-only
shapes graph produced 145 `sh:Info` results and `conforms: false` (D4).
So shape conformance is a structural gate with a boolean verdict, never
a grade and never truth; the PoC's `verified` status is granted only by
an execution record (the suite's scenario on the reference
implementation, with the digest of what ran) or a dated human review,
and `approved` only by a recorded human act. Nothing in the metamodel
lets a rule promote to either (§4).

**1.4 Labels in context are not enforcement.** [measured] The literature
on whether an LLM obeys provenance or status cues placed in its prompt
is thin and negative-leaning: "vigilant prompting" moved exact match by
−7 to +8 % (Pan et al. 2023); stating per-document credibility moved it
by −4.9 to +16.7 EM depending on the model, while the same labels used
at attention level gave +20 EM (CrAM, AAAI 2025); timestamped outdated
documents still cost 20–50 points (HoH, ACL 2025, no no-timestamp
ablation); stylistic credibility cues are ignored (Wan et al. 2024);
frontier models adopt wrong retrieved content over a correct prior
31–63 % of the time (ClashEval 2024); with insufficient context they
hallucinate rather than abstain 15–40 % of the time and RAG lowers
abstention further (Joren et al. 2025); on ambiguous coding tasks they
silently pick an interpretation at rates of 60–95 % (HumanEvalComm
2025, Ambig-SWE 2026, ClarifyCodeBench 2026). No study was found that
tests obedience to a status tag such as "unverified" or "deprecated"
directly. The design consequence is the one the fact sheet draws: the
graph's value is as the pre-prompt source that filters and resolves
before anything reaches the model, not as a supplier of labels the
model is trusted to honour. The PoC's governed arm is an *advisory*
arm by design (§10): it measures how far labels alone carry at one
model, and the architecture (§2) withholds under BLOCKED regardless.

**1.5 Extraction fidelity bounds everything downstream.** [measured]
LLM triple extraction is noisy before verification: zero-shot GPT-4
micro-F1 0.007 on WebNLG and 15–31 on Re-TACRED/DuIE against 69–91
fine-tuned (n = 20 per dataset in the latter study); the best engineered
pipeline reaches 0.82 F1 on clean WebNLG sentences and 0.60–0.71 on
document-level REBEL/Wiki-NRE, with 2–3× relation-name sprawl before
canonicalisation (EDC, EMNLP 2024). [standing settlement] N2 of
2026-08-26: no LLM-driven extraction on a deterministic path, and the
agent-repair wave's measured invention (−53 pp on one diagram from one
invented guard). [proposal] The reference architecture parses
machine-readable artefacts deterministically (a mapper per format, the
aris2puml shape), lets a model propose links only with basis
`inferred`, and keeps a model-proposed statement from reaching
`verified` by any path but an independent verification record (§2, §4).
[measured here] The PoC's ten extractors are hand-written mappers for
one kit; they found 145 assertions in the pristine kit, and the
vagueness rule detects the words it was given, not semantic ambiguity
(§6, S3).

**1.6 Source change must invalidate, not overwrite.** [standard] PROV-O
has the construct: "Generation marks the beginning of an entity,
whereas invalidation marks its end"; `prov:wasInvalidatedBy`,
`prov:invalidatedAtTime`, and `prov:wasRevisionOf` for the successor.
PROV has no construct for belief, confidence, contradiction or absence.
[capability] No RDF store surveyed keeps a persistent history (Stardog
removed versioning in 7.0: it "cannot be supported with the new
backend"; GraphDB's change tracking "is stored only in memory"); the
versioned stores — TerminusDB, Dolt, XTDB, Datomic, Fluree — do, with
as-of syntax quoted in §8. Neo4j does not; the PoC implements
invalidation as the application's rule over fragment digests (R-STALE),
and §8 says when a versioned store is the better choice.

**1.7 The hypothesis is partly testable and the prompt's causal chain
is longer than the evidence.** The prompt asks for empirical evaluation
across artefact quality, product quality, quality in use and delivery
performance. [measured] The couplings that exist are narrow: ambiguity
in a specification lowers LLM pass@1 by 7.22 pp on average and up to
32.35 pp (Orchid, 2026) and repairing it recovers about a third
relative (SpecFix, ASE 2025); correct trace links make maintainers 24 %
faster and 50 % more often right (Mäder & Egyed 2015, n = 71);
requirements faults were about a third of failures in a 21-CSCI NASA
system (Hamill & Goseva-Popstojanova 2009). [measured] Against the
folklore: "We found no evidence for the delayed issue effect" over 171
projects (Menzies et al. 2017), and the 100× figure traces to a 1981
IBM course via Pressman. [unknown] No peer-reviewed study measures any
spec-driven-development toolkit's outcome, none measures a controlled
hallucination-rate reduction from graph grounding on open generation,
and no study reaches quality in use or delivery performance from a
knowledge-graph intervention. The PoC reaches the artefact → product
leg only (§9), as the degradation test did.

**1.8 What the prompt gets right, confirmed rather than disturbed.**
The six-way separation of the 2026-10-12 synthesis — semantic entity,
artefact and version, representation, assertion, transformation run,
validation result — is the metamodel's spine and survived execution
unchanged (§3). Keeping a diagram's occurrence of an element apart from
the entity it depicts, never merging on name similarity, keeping
asserted, inferred and proposed apart, and never overwriting history
are each enforced by construction in the PoC's loader and rules.

## 2. Reference architecture

[proposal] Five stages, each with what is native, what is tooling and
what is custom. The PoC implements every box in `kg_experiment/harness/`
except the withholding retriever's access control and the human
verification interface, which are described.

```
 source repositories (git: .md .bpmn .dmn .puml .yaml .feature .py .toml)
      │  pull by path + commit; sha256 per file and per fragment
      ▼
 [A] ingestion ─────────── deterministic parsers, one per format
      │                    (stdlib, PyYAML, xml.etree, the product's own
      │                     PlantUML parser as a library); no model
      ▼
 [B] semantic transformation
      │   B1 syntactic: fragment → entity key + predicate + value
      │   B2 interpretation: canonical value forms per predicate
      │      (numbers; behaviour token maps; NONE for documented absence)
      │   B3 enrichment: model-PROPOSED links only, basis = inferred,
      │      attributed to the model, linked to the gap they claim to fill
      ▼
 [C] the graph (Neo4j)     Artefact → Version → Fragment; Entity;
      │                    Assertion{basis,status}; Activity/Agent (PROV);
      │                    Verification; Approval; Gap; CONTRADICTS;
      │                    Derived→USED_ASSERTION
      │   native: uniqueness constraints, MERGE, Cypher, (EE: existence/
      │           key/type, property-value read filters)
      │   custom: R-STRUCT R-CORROBORATE R-CONFLICT R-VAGUE R-REQ
      │           R-UNVERIFIED R-STALE, run after every load
      │   tooling: SHACL over an RDF projection (n10s or Python-side)
      ▼
 [D] governance            verification records (execution with digest;
      │                    dated human review), approvals, decisions
      │                    resolving declared gaps; lifecycle in §4;
      │                    all human acts are nodes, never property flips
      ▼
 [E] agent retrieval       a task declares its required keys → the gate
                           resolves level + flags per key → verdict
                           PROCEED | QUALIFIED | BLOCKED → the evidence
                           bundle (assertion ids, text, basis, status,
                           quoted fragment, verification, approval, gaps)
                           → under BLOCKED the retriever WITHHOLDS;
                           outputs register as Derived with USED_ASSERTION
```

**2.1 What stays in the source repositories and what is materialised.**
The artefacts stay where they are authored and versioned (git); the
graph holds their identity (path), each ingested version's digest, the
fragments it read (with text, so a bundle can quote evidence without a
round trip), and the assertions. The graph is authoritative for
*status, provenance and the links between artefacts*; it is never
authoritative for the artefact's content, and a fragment's text is a
copy whose digest proves which bytes it was. This is the synthesis's
"identifier, version, location and hash kept apart", and the 2026-10-16
note's Reading 3 (reports flow into the store; the consumer maps them).

**2.2 Syntactic transformation, semantic interpretation, enrichment.**
Three levels, kept apart because they carry different error classes:
B1 is lossless and checkable (a table row is a row); B2 is where
meaning enters and is the only place a mapper can be wrong (the PoC
maps "**no**" in a notified column to `NONE` and a `TariffEngine`
call in a branch to `priced=yes`); B3 is where invention enters and is
confined to basis `inferred`. The prompt's "preserve meaning without
introducing unsupported assumptions" is met at B1 and B2 by
determinism plus the R-VAGUE rule recording what could not be read as a
value (the raw text becomes the value and a gap is raised), and at B3
by the basis.

**2.3 When Neo4j is the authoritative repository rather than a derived
index.** [proposal] When the questions are about status and links
across artefacts — what is verified, what conflicts, what a change
invalidates, which outputs used what — and the answers must be the same
for every consumer. It is a derived index when it only re-indexes
content for retrieval (GraphRAG over chunks) and can be rebuilt from the
sources without loss; then nothing governed lives in it and it needs no
lifecycle. The test: if deleting the graph loses a human decision, it
was authoritative.

**2.4 Retrieval modes.** GraphRAG (vector or hybrid retrievers of the
`neo4j-graphrag` package: Vector, VectorCypher, Hybrid, HybridCypher,
Text2Cypher — Text2Cypher's query "is not guaranteed to be syntactically
correct" [capability]) retrieves by similarity; a governed retrieval
retrieves by declared key and status, which is a Cypher query with the
verdict computed before the model sees anything. The PoC uses the
second; §8 says what the first adds and costs. The empirical case for
graph structure in retrieval is narrow [measured]: it helps on multi-hop
and corpus-wide aggregation (+8–13 accuracy, GraphRAG-Bench 2026;
Think-on-Graph +20–50 Hits@1 on KBQA with a curated graph) and hurts or
is neutral on single-fact lookup and abstention (Microsoft-style global
mode answered should-abstain questions correctly 19 % against 96 % for
plain RAG, Han et al. 2026); the headline 72–83 % GraphRAG win rates
are LLM-judge preferences that an audit found inflated by position and
length bias (66.7 % → 39.1 % for one pair after de-biasing, Zeng et al.
2026).

## 3. Semantic metamodel

[proposal, executed] As loaded by `kg_experiment/harness/load.py`;
pre-registration §3 is the frozen statement.

**3.1 Nodes and relationships.**

| node | properties | relationships |
|---|---|---|
| `Artefact` | id (path), family, format | `HAS_VERSION`→Version; `CURRENT`→Version |
| `Version` | id, sha256, bytes, ingested_at, tag | `HAS_FRAGMENT`→Fragment |
| `Fragment` | id, locator (row, note, step, XPath, scenario), sha256, text, artefact | `MENTIONS`→Entity |
| `Entity` | id (declared key, never a name match), kind, name | — |
| `Assertion` | id, key (`entity|predicate`), predicate, value, raw_value, text, basis, status, artefact, version, unresolved | `ABOUT`→Entity; `SUPPORTED_BY`→Fragment; `DERIVED_BY`→Activity; `ATTRIBUTED_TO`→Agent; `CORROBORATES`↔; `CONTRADICTS`↔; `CANDIDATE_FOR`→Gap |
| `Activity` | id, kind (extraction, inference, authoring), at, tool, note | `USED`→Version; `ASSOCIATED_WITH`→Agent |
| `Agent` | id, kind ∈ human, tool, llm, name | — |
| `Verification` | id, method ∈ execution, review, cross_check; outcome; scope; at; valid_until; evidence_sha256 | `VERIFIES`→Assertion; `PERFORMED_BY`→Agent |
| `Approval` | id, at, record | `APPROVES`→Assertion; `BY`→Agent |
| `Gap` | id, kind ∈ missing, ambiguous, conflict, unverified, stale; declared; text | `CONCERNS`→Entity or Assertion; `CONCERNS_KEY`→Entity (with key); `RAISED_BY`→Activity; `RESOLVED_BY`→Decision |
| `Derived` | id, kind, sha256, suspect | `USED_ASSERTION`→Assertion |

PROV-O alignment [standard]: `Assertion` and `Version` are
`prov:Entity`; `Activity` is `prov:Activity`; `Agent` is `prov:Agent`;
`DERIVED_BY`+`USED` is the qualified derivation (`prov:qualifiedDerivation`
with `prov:hadActivity` and `prov:entity`); `ATTRIBUTED_TO` is
`prov:wasAttributedTo`; invalidation (R-STALE) sets `invalidated_at`
and `invalidated_by`, which is `prov:invalidatedAtTime` and
`prov:wasInvalidatedBy`; a successor assertion on the same key and
artefact is `prov:wasRevisionOf`. A nanopublication's four graphs map
to Assertion (assertion), Activity/Agent/Fragment (provenance) and
Verification/Approval (publication info); its "you can never edit nor
delete it" is the rule here that status is appended by acts, never
rewritten.

**3.2 Epistemic basis and status are two axes, not one.** Basis is how
the statement came to exist and never changes: `authored` (a human
wrote it), `extracted` (a deterministic mapper read it from a fragment),
`inferred` (a model proposed it), `assumed` (a consumer recorded a
working assumption), `hypothesised` (one of several candidate readings).
Status is where it is in the lifecycle (§4): `proposed`, `validated`,
`verified`, `approved`, `disputed`, `invalidated`, `deprecated`,
`rejected`. The prompt's "verified, asserted, inferred, hypothetical,
disputed, unknown" splits across the axes: asserted/inferred/hypothetical
are bases; verified/disputed are statuses; unknown is the absence of an
assertion for a key, which the gate reports as `absent` and which is
distinct from a `Gap{declared:true}` (someone wrote down that it is
missing) and from a documented absence (value `NONE`).

**3.3 Documented absence versus unknown, as a query.** [measured here]
The three-valued answer for three keys of the pristine kit (D5):

| key | answer |
|---|---|
| `S-review|notified` | `documented_absent` — DT-S row review says "**no**", the DMN rule says `"none"`, the diagram's branch calls no notifier, the BPMN path has no notify task: four assertions of value `NONE`, corroborated |
| `S-refuse|notified` | `asserted` — "refusal notice", four artefacts |
| `QuoteAPI|notified_after_screening` | `unknown` — no artefact states what happens when screening completes; DT-S note 5 says "out of scope here" |

The third is the prompt's "absence of recorded information": the
prudent answer is a question, and the gate's `absent` level makes it
one.

**3.4 What the store enforced, measured.** [measured here] D1 on Neo4j
5.26.0 community: six uniqueness constraints accepted; property
existence (`REQUIRE n.status IS NOT NULL`), node key
(`(n.locator, n.sha256) IS NODE KEY`) and property type
(`n.sha256 IS :: STRING`) each refused with
`Neo.DatabaseError.Schema.ConstraintCreationFailed`. The docs predicted
this [capability]. The consequence for a governed repository on the
community edition is that an assertion without a status is a loader
bug the store will not catch; R-STRUCT catches it after the fact. On
Enterprise the three constraints would hold, and property-based read
privileges (`GRANT READ {*} ON GRAPH … FOR (n:Assertion) WHERE
n.status = 'approved'`) can filter what a role sees, with the documented
limits: one property per privilege, "A DENY rule fails open when its
criteria cannot be evaluated", "significant performance overhead in
certain scenarios" [capability]. A read filter is not a workflow: the
status property is writable by any role with write access, so approval
must be a node created by a recorded act (§4), and the filter a second
line.

**3.5 Fragment granularity is a design parameter with a measured cost.**
[measured here] R-STALE works on fragment digests, and the S6 change to
one number in the P2 row invalidated `P2|threshold` as well as
`P2|surcharge`, because the row is the fragment, and the
worked-example paragraph's change invalidated `P3|order` and
`worked_example|price`. Finer locators (a table cell) would invalidate
less and cost a locator scheme per format; coarser (the file) would
invalidate everything on any edit, which is what a path-only provenance
(Gap 1 of 2026-10-12) forces. The pre-registration predicted three of
the four; the fourth was a frozen-text omission (§10).

## 4. Knowledge lifecycle

[proposal, executed] States, who may move an assertion between them,
and what moves with it.

```
                 R-CORROBORATE            Verification record          Approval record
 proposed ──────────────────▶ validated ──────────────────▶ verified ──────────────▶ approved
    │                             │                              │                       │
    │   R-CONFLICT (any live pair on one key with unequal values) │                       │
    └──────────────┬──────────────┴──────────────────────────────┴───────────────────────┘
                   ▼
               disputed ──── Decision (human) ───▶ one side rejected, the other re-enters at proposed
                                                   (never silently "resolved")
 any status ─── R-STALE (supporting fragment's digest changed or vanished) ───▶ invalidated
                   │  verifications of it get valid_until = the new version
                   │  Derived outputs that USED it become suspect
                   └── a successor on the same key enters at proposed; the invalidated one
                       blocks the key until the successor is verified (§6, S6)
 any status ─── a human act ───▶ deprecated (still true, no longer in force) | rejected (wrong)
```

Rules of the lifecycle, each enforced in the PoC:

1. **No rule promotes to `verified` or `approved`.** `validated` is the
   most a rule grants (two independent artefacts agree), and it means
   consistency, not truth: two artefacts can agree on a wrong value, as
   the degradation test's D3 arm showed with every layer stating the
   planted value and every gate green.
2. **Verification is a record with scope, method and evidence.** The
   PoC's execution verifications name the suite scenario, the artefact
   it ran against and its digest; the review verifications name the
   dated record (`stack_experiment/README.md`, "Verified state
   (2026-08-06)"). `valid_until` is set by R-STALE, never by hand; a
   verification whose scope no longer matches the fragment is over.
   This is the prompt's verification scope, validity period and evidence
   freshness in three properties.
3. **Verification is of a (key, value), not of a key.** [measured here]
   In S3 the DT-S rows' vague values are not the values the suite
   verified, so the same verification records do not attach, and the
   keys fall to `proposed` with an ambiguity flag. A planted
   contradiction (S4) leaves the verified side verified and the new
   side proposed until R-CONFLICT marks both disputed: a conflict with
   verified knowledge is not resolved in favour of the verified side by
   a rule, because the new artefact may be the correct one (the Legible
   review's F1: defects measurably travelled from code into derived
   specs).
4. **Inferred never becomes fact by inference.** An `inferred` assertion
   enters at `proposed`, must be linked to the gap it proposes to fill
   (R-STRUCT), and reaches `verified` only through a verification
   record like any other; at that point its basis still says `inferred`
   so a consumer can weigh it.
5. **Invalidation is an event, supersession is a verified successor.**
   The invalidated assertion keeps its history; the key it is about
   blocks until a verified replacement exists (§6, S6, measured:
   BLOCKED before the re-verification record, PROCEED after).
6. **Declared gaps are first-class and outrank candidates.** A
   requirement that says "NOT YET SPECIFIED (open decision OD-1)" raises
   `Gap{kind:missing, declared:true}` on the requirement and on the key
   it governs; a model-proposed candidate for the gap is recorded as
   `CANDIDATE_FOR` and does not lift the block (§6, S5). Only a
   `Decision` node by a human resolves a declared gap.
7. **Re-evaluation is a re-ingest plus the rules**, not an edit: the new
   version's unchanged fragments are reused (digest match), only
   changed fragments create new assertions, and the deterministic
   consequence set (invalidated, kept, suspect) is the answer to "what
   must be re-verified" (§6, S6: 2 new fragments, 16 reused, 4
   invalidated, 31 kept).

## 5. End-to-end worked example

[measured here] S1 of the proof of concept: the pristine CargoQuote kit
through every stage of §2, ending in code graded by the kit's oracle.
Every number below is in `kg_experiment/results/S1/`.

**5.1 Ingestion and transformation.** Ten artefacts (seven of the kit,
three authored for the experiment) were read by ten deterministic
mappers: 95 fragments, 145 assertions, 0 unresolved symbols. By
artefact: the decision tables gave 35 assertions (DT-V bounds, DT-S
rows and notes 1–5, DT-P steps, the worked example); the OpenAPI file
10, which corroborate DT-V's seven bounds and the response vocabulary;
the sequence diagram 21 through the product's own parser (participants,
and the accept, review, refuse, store-failure and screening-outage
branches read as behaviour tokens); the BPMN 11 and the DMN 13, which
corroborate the DT-S rows from the OMG formats; the specification 7
(the flow order, the two failure behaviours, the response vocabulary);
the requirements 8; the Gherkin 14; the C4 diagram 11; the
human-authored link set 15 (eight `implemented_by`, seven
`verified_by`).

**5.2 The graph.** 597 nodes and 1,472 relationships. Six uniqueness
constraints accepted, three Enterprise-only constraints refused (D1,
§3.4). R-STRUCT: 0 violations. R-CORROBORATE: 88 pairs of assertions on
one key with equal values from different artefacts, each pair
`validated`. R-CONFLICT: 0. R-VAGUE: 0. R-REQ: one gap, undeclared —
REQ-05 (storage failure) has no verifying Gherkin scenario, which is
true of the kit as committed (G1–G7 cover the other seven
requirements) and was not planted. R-UNVERIFIED: 34 assertions with no
verification record, none of them a required key (participant kinds,
container technologies, scenario titles, the implemented-by links).

**5.3 Verification and approval.** 79 execution verifications
(the suite's eleven scenarios mapped to the keys they exercise by
`kit/verification_map.toml`, each record naming the scenario, the
artefact it ran against and its digest), 42 review verifications (the
ten keys no scenario reaches, under the kit README's dated "Verified
state"; the authored requirements and links), 111 approvals (every
verified assertion, under the same record). Status census: 111
`approved`, 34 `proposed`. The three-valued query of §3.3 answered
`documented_absent`, `asserted`, `unknown` for its three keys.

**5.4 The gate.** Task `codegen`, 36 required keys, every one at
`approved`, no flags: **PROCEED**. The evidence bundle rendered as
17,394 prompt tokens, each key with its assertions, quoted fragments,
verification and approval records; an excerpt:

```
## P2|surcharge  level=approved  flags=-
  [A:dt:P2|surcharge@v1] value='316.00' basis=extracted status=approved
      source=contract/decision_table.md by=kg_experiment harness
      text: heavy surcharge: if `weight_kg > 1244`, add `316.00` (flat)
      evidence: contract/decision_table.md @ DT-P/row/P2: '| P2 | heavy
      surcharge: if `weight_kg > 1244`, add `316.00` (flat) |'
      verification: execution (suite scenario price_exact_heavy on
      reference_impl.py (smoke 2026-10-30)) at 2026-10-30T10:42:15+00:00
      approval: stack_experiment/README.md Verified state at 2026-08-06
```

**5.5 Generation and grading.** Governed arm, five runs: `decision =
generate` in all five, code in all five, **11/11** on the suite in all
five, every claim's reference an assertion id that resolves in the
bundle (36 of 36 in run 1; 1.0 in all five). Baseline arm, five runs:
`generate_with_assumptions` in all five (the assumptions are interface
choices the documents leave open, such as what `store_draft` returns),
code in all five, **11/11** in all five, references resolving to a file
and line in 83–100 % of claims. SHACL over the projection: the main
shapes graph reports one `sh:Warning` (REQ-05) and `conforms: false`;
the Info-only graph 145 results and `conforms: false`.

**5.6 Traceability of the output.** Run 1's governed code is registered
in S6 as `Derived{id:'derived:S1:G:run1'}` with `USED_ASSERTION` edges
to all 36 keys' assertions; a suite failure on `price_exact_heavy`
would trace to `P2|threshold` and `P2|surcharge`, to
`A:dt:P2|...@v1`, to fragment `DT-P/row/P2` of `decision_table.md` at
version `v1`, to the extraction activity and the harness as agent.

**5.7 What the example shows and does not.** With complete, consistent,
verified knowledge both arms produce correct code; the governed arm's
gain here is traceability, not correctness. The gap R-REQ found is the
kind of thing the prompt's completeness check is for, and it was found
in a kit that four rebuild waves and a degradation test had used
without noticing: the suite covers storage failure, the Gherkin input
does not.

## 6. Uncertainty and contradiction handling, demonstrated

[measured here] The six planted scenarios of `kg_experiment/`, each
read against the prompt's seven questions: how the source information
is represented, what status is recorded, which rules fire, what the
agent may retrieve and conclude, whether generation proceeds, is
qualified or is blocked, how the output traces, and whether the
downstream defect is detected or prevented. The baseline arm (B)
receives the same documents, planted text included, with no status;
the governed arm (G) receives the gate's bundle and verdict, with
nothing withheld (§7.3). Five runs per arm unless a cell is marked;
"flagged" is the frozen keyword check of the pre-registration's §8,
and where the session's reading differs the difference is stated.

| scenario | represented as | gate | G: decision · code · flagged · suite | B: decision · code · flagged · suite | downstream defect |
|---|---|---|---|---|---|
| S1 complete, verified | 145 assertions, 111 `approved`; 0 gaps on required keys | PROCEED | generate 5/5 · 5/5 · — · 11/11 ×5 | generate_with_assumptions 5/5 · 5/5 · — · 11/11 ×5 | none; both arms correct |
| S2 missing, declared | `Gap{missing, declared}` on REQ-06 and on the outage key; `hold_presence` absent | BLOCKED | abstain 5/5 · 0/5 · 5/5 · — | generate_with_assumptions 5/5 · 5/5 · 5/5 · 10/11 ×5 | prevented in G; outage scenario fails in every B run |
| S3 ambiguous | 17 ambiguity gaps; 4 keys `proposed`; DMN declared not authored | QUALIFIED | generate_with_assumptions 5/5 · 5/5 · 5/5 · 6, 0, 5, 11, 10 | generate_with_assumptions 5/5 · 5/5 · 5/5 · 10/11 ×5 | 41-boundary fails 4/5 G, 5/5 B; the guess is an `# ASSUMPTION` constant in G, silent in B |
| S4 contradictory | 4 `CONTRADICTS` pairs, 4 `disputed`, 4 conflict gaps | BLOCKED | abstain 5/5 · 0/5 · 5/5 · — | generate_with_assumptions 5/5 · 5/5 · 0/5 (4/5 by reading) · 11/11 ×5 | none by the oracle; B resolved by an invented precedence |
| S5 inferred, unverified | one `inferred` candidate for the declared gap, `proposed` | BLOCKED | abstain 5/5 · 0/5 · 3/5 · — | generate_with_assumptions 5/5 · 5/5 · 1/5 · 10/11 ×5 | prevented in G; B adopted the note as fact in 4/5 |
| S6 invalidated by change | 4 `invalidated`, 4 verifications ended, `Derived` suspect; BLOCKED → PROCEED on re-verification | PROCEED | generate 5/5 · 5/5 · 5/5 · 11/11 ×5; suspect artefact named 5/5 (re-run) | generate_with_assumptions 5/5 · 5/5 · 4/5 · 11/11 ×5; asks in general terms | the stale artefact is identified in G only |
| S7 unverified | 0 `verified`, 145 unverified gaps, 0 approvals | BLOCKED | abstain 5/5 · 0/5 · 5/5 · — ; non-compliance 0/5 | generate_with_assumptions 5/5 · 5/5 · 0/5 · 11/11 ×5 | procedural; content correct in both |

**6.1 S2 — an explicitly identified missing requirement.** The
screening-outage rule is deleted from every artefact that states it,
and REQ-06 reads "NOT YET SPECIFIED (open decision OD-1, owner:
compliance)". *Representation:* `Gap{kind:missing, declared:true}`
raised by R-REQ on REQ-06 and, through the requirement→key table, on
`QuoteAPI|on_screening_outage`, whose key has no assertion; a second
undeclared gap on REQ-06 (no verifying scenario); `response|hold_presence`
has no assertion at all (`absent`), because `hold` left the API with
the rule. *Gate:* BLOCKED on both keys. *G:* `abstain` 5 of 5, no code,
and every run's first question names the key and the gap id
(`QuoteAPI|on_screening_outage`, `gap:declared:OD-1`) and the second
the unknown key; flagged 5 of 5. *B:* code 5 of 5, `generate_with_assumptions`
5 of 5, flagged 5 of 5 — the words "NOT YET SPECIFIED" produced a
question in every run — and the code treats the outage as an
unhandled exception or a generic failure in every run, so
`screening_down_hold` fails 5 of 5 (no price computed). *Reading:*
the information was in both arms' input; the baseline turned it into
a question and generated anyway, which is HumanEvalComm's measured
behaviour ("incompleteness" is the one defect type those models did
ask about, at 31.7 %, and still answered); the gate turned it into a
refusal. The defect that would have shipped is the prior-following
one the kit's smoke mutant exists to catch (an outage becomes an
error), prevented in G by abstention and left in B's code in every
run, detected only by the oracle.

**6.2 S5 — an AI-inferred relationship without verification.** S2's
kit plus one statement: "on a screening outage the quote is refused
with status `refused_screening`", basis `inferred`, agent `llm`,
status `proposed`, `CANDIDATE_FOR` the declared gap OD-1, no
fragment; the baseline receives the same sentence as
`notes/analysis_notes.md`, headed "Auto-generated analysis notes
(architecture assistant, 2026-10-27; not reviewed)". *Gate:* BLOCKED
(the declared gap outranks the candidate, §4 rule 6; the §5 table's
QUALIFIED was the frozen-text error of the run notes). *G:* `abstain`
5 of 5, no code; 3 of 5 name the inference as `inferred`/`unverified`
in their questions (flagged 3 of 5), the other two name the declared
gap only. *B:* code 5 of 5; the note was adopted as fact in **4 of 5
runs** — three return `refused_screening` on the outage scenario and
one refuses without pricing — and one run (run 5) names the note's
"assistant" origin as an assumption and still implements it; flagged
1 of 5 by keywords, and by reading run 3's assumption says in terms
"The open decision OD-1 ... is resolved as described in
notes/analysis_notes.md". `screening_down_hold` fails 5 of 5.
*Reading:* a labelled, unreviewed machine inference in a document is
treated as a resolution of the gap it claims to resolve; in the graph
the same inference is a candidate that cannot lift the block. The
downstream defect (refusing on outage) is prevented in G and present
in every B run; nothing in B's output distinguishes the inferred
premise from the authored ones except the file name of its
reference.

**6.3 S7 — generation from insufficiently verified knowledge.** S1's
kit, extraction only: 76 `validated`, 69 `proposed`, 0 `verified`,
145 unverified-gaps, 0 approvals. *Gate:* BLOCKED, 36 of 36 required
keys below `verified` against the 25 % bar. *G:* `abstain` 5 of 5,
no code, flagged 5 of 5; every run's first question is that the
verdict is BLOCKED and must be lifted, and the next ones ask for
verification of named keys by assertion id (run 1 and 3:
`A:dt:invalid_request|behaviour@v1`). Non-compliance (M6) 0 of 5.
*B:* code 5 of 5, 11/11 on the suite 5 of 5, flagged 0 of 5: nothing
in the documents says they are unverified, so nothing was asked.
*Reading:* the block is procedural, as pre-registered — the content
was correct, and the baseline's code is correct — and that is the
point: without a verification record nothing distinguishes S7's kit
from S1's except the record, and an agent that generates from either
with equal confidence has no way to carry the difference into its
output. The cost of the procedure is five abstentions on correct
content; the benefit is that S2–S5's contents, equally confident,
were not generated from.

**6.4 S3 — an ambiguous requirement with several readings.** The DT-S
rows read "clearly low — below the low forties", "from the low
forties up to the mid-sixties", "anything higher"; the symbolic-names
sentence and the boundary readings are gone; the DMN is "not yet
authored"; the diagram still says `riskIndex <= ACCEPT_MAX` with no
definition anywhere. *Representation:* the three rows' assertions
carry the raw text as their value, none matches a verified value, so
all fall to `proposed`; R-VAGUE raises 17 ambiguity gaps (the vague
words on every assertion the three row fragments support, and the
four unresolved diagram symbols); R-CONFLICT raises nothing, because a
numeric key with a non-numeric side is incomparable; the DMN's absence
is a declared gap. *Gate:* QUALIFIED — 4 of 36 keys below `verified`
(11 %, under the 25 % bar), 13 flagged. *B:* code 5 of 5, flagged
5 of 5 (every run asks for the exact thresholds), and every run picks
a reading silently in the code — accept below 40 or 39, review from
40 — so `accept_boundary_41` (41 must be accepted) fails 5 of 5 while
42 and 67 pass. *G:* `generate_with_assumptions` 5 of 5, flagged 5 of
5, every qualified key in `assumptions` by id and isolated as a named
constant with an `# ASSUMPTION` comment, as the policy asks; suite
6, 0, 5, 11 and 10 of 11. The spread is the finding: told the
thresholds were unsettled, two runs made the collaborators abstract
(`raise NotImplementedError`) or moved the decision into the screening
service, one run had a plain attribute bug, and two chose a reading in
a constant as the baseline did. Three governed runs (1, 2 and 4) wrote the pristine 41/42/66/67
into their constants with no number in their input, only run 4's code
executing; the model's release (2025-11-13) predates the kit (authored
2026-08-06), so this reads as interpretation variance of "low forties"
and "mid-sixties", but the kit is public and contamination cannot be
excluded (§10.3). *[Corrected 2026-10-30, after the merge: the count
first read "two".]* *Reading:* the gate
represented the ambiguity and the policy made it visible in the
output, which a reviewer can act on; it did not make the code better,
and at this model the instruction to isolate assumptions cost
executability. Prevention of the downstream defect here is not by
abstention but by making the guess findable: in B the 39/40 is a
silent constant; in G it is `# ASSUMPTION A:dt:S-accept|max@v1`.

**6.5 S4 — two artefacts contradicting each other.** The decision
table and the specification keep "priced, `held_unscreened`, not
notified"; the sequence diagram's outage branch and the BPMN's outage
path now say "no price, `error: screening_unavailable`, not notified";
G4 is removed, so two artefacts each way, and the kit's own precedence
clause ("where a diagram is silent or qualitative") does not cover an
explicit contradiction. *Representation:* four `CONTRADICTS` pairs on
one key (every DT/spec assertion against every diagram/BPMN one),
all four assertions `disputed`, four `Gap{kind:conflict}`; the
verified side is demoted with the other, by §4 rule 3. *Gate:*
BLOCKED. *G:* `abstain` 5 of 5, no code, flagged 5 of 5, every run
naming the conflict gap and the disputed key. *B:* code 5 of 5,
`generate_with_assumptions` 5 of 5, flagged **0 of 5** by the frozen
keyword set (no run used *contradict*, *conflict*, *disagree* or
*inconsistent*); by reading, 4 of 5 noticed the two sides and recorded
an assumption that resolved them — "the DMN and BPMN descriptions ...
are superseded by the later normative text", "ignored in favor of the
newer normative text in decision_table" — a precedence nothing in the
kit states (no artefact is dated); 1 of 5 did not mention the diagram
side at all. Every B run implemented the decision table's side and
passed 11/11, including `screening_down_hold`. *Reading:* the
baseline resolved the contradiction silently and, by the oracle,
correctly; the governed arm refused. This is Xie et al.'s and Wang et
al.'s measured behaviour (models resolve by coherence and majority,
flag conflicts only when asked, and here invented a "newer" rationale)
reproduced at n = 5, and the degradation test's precedence reflex
without a declared precedence. Prevention: G prevents nothing wrong
here and generates nothing; B generated something right by a reasoning
step no reviewer can check from its output. Had the diagram been the
correct side — the Legible review's F1 showed defects travelling from
code into specs — B's five runs would all have been wrong with the
same confidence.

**6.6 S6 — a verified assertion invalidated by a source change.** S1's
graph, fully verified and approved; S1's first governed run's code
registered as `Derived{id:'derived:S1:G:run1'}` with `USED_ASSERTION`
edges to all 36 keys' assertions; then `decision_table.md` changes P2's
surcharge from 316.00 to 341.00 and the worked example with it, and
is re-ingested as version `v2`. *Representation (D3):* 2 fragments
new, 16 reused by digest, 4 new assertions; R-STALE invalidates
exactly the four assertions the two changed fragments support —
`P2|surcharge`, `P2|threshold`, `P3|order`, `worked_example|price` —
sets `valid_until = v2` on their four execution verifications, marks
the derived code `suspect`, and leaves the other 31 assertions of the
changed file at their status. *Gate:* BLOCKED (two required keys
`invalidated`, their successors `proposed`), then PROCEED after a
recorded re-verification and approval of the three successors by the
maintainer stand-in. *G (the re-run, with the corrected bundle):*
`generate` 5 of 5, 11/11 on the suite with the new prices 5 of 5, and
every run's first question names `derived:S1:G:run1` as suspect
because it used `A:dt:P2|threshold@v1`, `A:dt:P2|surcharge@v1` and
`A:dt:P3|order@v1`, and says it may not be reused as it is. In the
first run the bundle lacked that section (run notes); its run 1 named
the `@v2` successors and the need to re-verify but could not name the
artefact, and its runs 2–5, produced after the fix, did. *B:* code 5
of 5, 11/11 5 of 5; 3 of 5 ask whether "the existing implementation"
may still be used and what changed, in general terms — the documents
hold the current version only, so nothing in B's input can say which
implementation, what it used, or what the change was. *Reading:* this
is the store's half of the hypothesis at its clearest. The impact set
is a traversal (two fragments → four assertions → four verifications
→ one derived output), it is exact, and the baseline has no object
that could carry it. The fragment granularity over-invalidated
`P2|threshold`, whose value did not change (§3.5), and the ended
verifications were printed as `valid_until=None` in the arms' bundle
because the stage-2 verification loader re-merged them (a defect
found after the run and fixed; D3 re-established deterministically in
`results/d3check/`).

**6.7 What the six scenarios show together.** The governed arm never
generated under BLOCKED (20 of 20 cells across S2, S4, S5, S7, M6 = 0)
and named the blocking key, gap or conflict in every one; under
QUALIFIED it produced code that carries its assumptions by id and that
executed worse than the baseline's. The baseline generated in every
cell (35 of 35), asked about the missing requirement when the text said
it was missing, adopted an unreviewed machine note as a decision in
four of five runs, resolved an undeclared contradiction by a precedence
it invented in four of five, and never asked about verification when
nothing in the text raised it. The prompt's central question — does
explicit epistemic status keep source defects from becoming
authoritative claims downstream — has, at this model and scale, the
answer: yes where the status is a verdict that stops generation (S2,
S4, S5, S7), weakly where it is a qualification the model must carry
(S3), and only the store can answer where the question is what a change
invalidates (S6).

## 7. Agent grounding and enforcement mechanisms

**7.1 The policy an agent runs under** (`kg_experiment/harness/policy.md`,
frozen; [proposal]):

1. only `verified` or `approved` knowledge is fact; `validated` and
   `proposed` may be used as a labelled assumption; `disputed`,
   `invalidated` and declared-gap knowledge may not be used at all;
2. basis `inferred` is a hypothesis: never a fact, never a silently
   adopted assumption; reliance is stated by id and marked unverified;
3. a key marked UNKNOWN has no statement: nothing is invented for it;
4. BLOCKED → no output of the governed kind, `decision = abstain`, and
   the questions name the keys and gap ids that must be decided or
   verified;
5. QUALIFIED → output with every qualified key in `assumptions` by
   assertion id, isolated in the artefact (a named constant, a marked
   branch) so the assumption can be found and replaced;
6. PROCEED → generate;
7. every claim and assumption carries an assertion id.

**7.2 When an agent may use, infer from, challenge or must reject
knowledge.** Use: verified or approved, within the verification's scope
and validity. Infer from: only to *propose* — the output of inference is
an `inferred` assertion with its own id, linked to the gap it addresses,
and the generated artefact that relies on it is `Derived` with a
`USED_ASSERTION` edge to the inference, so the inference is a
traceable, revocable dependency and not an invisible premise. Challenge:
an agent that finds two live assertions disagreeing, or a verified
assertion contradicted by the artefact it reads, records a conflict
candidate rather than choosing (the degradation test's agents did
choose, by the kit's declared precedence rule, which is the baseline
behaviour §6 measures). Reject: disputed, invalidated, declared-gap, and
anything whose verification `valid_until` has passed.

**7.3 Enforcement is structural, not persuasive.** [measured] The
literature §1.4 summarises, in the words of the fact sheet behind it
(uncommitted, §12): label-following via prompt is "model-dependent and
often small", what works reliably sits "below the prompt" (attention,
decoding, calibrators, filtering before retrieval), and forced
clarification recovers 54–89 % of the accuracy lost to
under-specification (Ambig-SWE 2026). [proposal] Therefore: (a) the retriever withholds assertion
content under BLOCKED and returns only the verdict, the blocking keys
and the gaps — there is nothing to generate from; (b) under QUALIFIED
the bundle carries the flags and the output contract makes assumptions a
required field, checked mechanically for the ids of every qualified key;
(c) an output is registered as `Derived` before it is used anywhere,
so that §4 rule 5 can reach it; (d) the agent's clarification questions
are routed to the gap's owner as the resolution path (§4 rule 6). The
PoC's governed arm deliberately did not withhold (pre-registration §6),
to measure (a)'s necessity rather than assume it; §6 reports what the
model did with advice alone.

**7.4 What prevents an agent from treating graph content as true.**
Nothing in the graph; the policy and the retriever do. A graph that
only holds approved content (the Enterprise read filter of §3.4) looks
true to a model exactly as a document does; the gain is that the
*filter* is deterministic and auditable. The remaining risk is the
graph's own correctness, which §1.3 and §4 rule 1 keep separate from
its conformance: a validated, verified, approved assertion can be wrong
when its verification was wrong — the degradation test's concealed
defects were green under the arm's own suite and caught only by an
independent oracle.

**7.5 Traceability of outputs.** [measured here] M5: in the governed
arm every claim and assumption carries an assertion id that resolves in
the bundle (S1 calibration: 35 of 35; the scored run in §6); in the
baseline arm the reference is a `path:line` that resolves to a file and
a line but not to a statement with a status. A `Derived` node with
`USED_ASSERTION` edges closes the loop: a downstream defect found by the
suite is traced to the scenario's keys, to the assertions about them,
to their fragments and to the transformation run (§6, defect
propagation rows).

## 8. Alternatives, compared

[capability, status-verified unless marked] From fact sheet E, read at
the vendors' documentation on 2026-10-30; "?" means not verified.

| product | model | write-time constraints | statement-level metadata | history / as-of | provenance built in | licence |
|---|---|---|---|---|---|---|
| **Neo4j** CE / EE | LPG, Cypher | uniqueness (CE); existence, key, type (EE); open graph types (EE, 2026.06) | relationship properties; reified nodes | none (CDC is a stream, EE) | no | GPL-3.0 CE; commercial EE/Aura |
| GraphDB | RDF quads | SHACL on commit (set at repository creation) | RDF-star embedded triples | in-memory change tracking only | no | proprietary; Free single-core; 11.0 requires a licence for every edition |
| Stardog | RDF | SHACL ICV, guard mode fails transactions | edge properties (early RDF*) | removed in 7.0 | no | proprietary; Free 1-year renewable |
| Jena / Fuseki | RDF | SHACL Core + SPARQL, on request to `/shacl` | RDF-star (CG syntax, "This is not RDF 1.2") | none | no | Apache-2.0 (6.2.0) |
| RDF4J | RDF | SHACL on commit (ShaclSail) | ? | none | no | BSD-3 (6.0.0) |
| Oxigraph | RDF | none | RDF 1.2 "preliminary" | none | no | Apache-2.0 / MIT |
| AllegroGraph | RDF | ? | triple attributes, immutable, access control per triple | ? | no | proprietary; Free ≤ 5M triples |
| Neptune | PG or RDF (separate models) | none | named graphs (RDF) | none (backups only) | no | managed service |
| TerminusDB | JSON-LD document graph | its own schema, no SHACL | ? | commits, branch, merge, "Query any state of the database at any historical commit" | commit log | Apache-2.0 (v12.0.9, 2026-10-28, Gettier) |
| Fluree | RDF/JSON-LD ledger | SHACL "enforced at transaction time" | ? | `@t:` / `@time:` as-of, history from–to; "Changes are represented as new facts that supersede previous ones" | commit metadata | BSL 1.1 → Apache-2.0 (v4.2.4) |
| XTDB 2 | SQL / document | SQL | n/a | bitemporal, `FOR SYSTEM_TIME AS OF`, `FOR VALID_TIME AS OF` | system time | MPL-2.0 |
| Datomic | EAV facts | ? | n/a | `as-of`, `since`, `history`; retractions kept | transaction entity | free binaries, closed source |
| Dolt | SQL | SQL | n/a | `AS OF <commit>`, `dolt_history`, `dolt_diff` | commit log | Apache-2.0 |
| Memgraph / FalkorDB / AGE / TigerGraph / ArangoDB / Dgraph | PG | existence/unique/type at best | ? | none | no | BSL/MEL; SSPLv1; Apache-2.0; proprietary; BSL; Apache-2.0 |
| Kùzu | PG | — | — | — | — | MIT, **archived 2025-10-10** |
| Pinecone / Weaviate / Qdrant / pgvector | vectors + payload | filters only | payload fields | none | no | SaaS / BSD-3 / Apache-2.0 / ? |
| TopBraid EDG ("TQ Data Foundation") | RDF/SHACL application over a store | SHACL (application) | RDF 1.2 reification (9.2) | working copies, change history | workflow log, governance roles | commercial |

**8.1 How each class represents uncertainty, conflict, provenance and
verification.** None natively, in any class: "in every product the
approval state is a workflow object or a status attribute on an entity,
maintained by the application; no underlying store (RDF, PG, SQL)
exposes it as a storage primitive". The only epistemic distinction a
store keeps on its own is explicit versus inferred (GraphDB's change
tracking exposes "explicit and inferred" statements; Stardog does not
materialise inferences). The precedents that do model status are data
patterns: Wikidata's ranks ("The deprecated rank is used for statements
that are known to include errors", with a reason-for-deprecation
property, and "This does not apply to correct historical information")
and no-value/unknown-value snaks; nanopublications' signed retraction
and supersession; CIO's three-level confidence with weak versus strong
contradiction (a 2015 draft, 44 classes); SEPIO's evidence lines. A
property graph carries all of these as nodes and properties; an RDF
store carries them as named graphs, RDF-star/RDF 1.2 reifiers or
PROV-O triples with the advantage that PROV-O, SHACL, DCAT and SKOS are
standards one imports rather than conventions one invents.

**8.2 Trade-offs, by class.**

- *Neo4j (LPG).* Strengths: traversal, Cypher's readability for the
  rule set, mature drivers, the GraphRAG and MCP ecosystem (the official
  `neo4j/mcp` server has a `NEO4J_MCP_READ_ONLY` switch; the Labs
  servers are "not supported by the Neo4j product team" [capability]),
  constraints adequate on EE. Limitations: no history (R-STALE is the
  application's), governance primitives and provenance vocabulary all
  custom, standards interoperability only through n10s, which is a Labs
  project "not part of Neo4j's supported product lineup", last released
  2025.06.1 with nothing documented for Neo4j 2026.x, and whose ontology
  loader keeps classes, subclass, properties, subproperty, domain and
  range and says "All other elements will be ignored by this loader"
  [capability]. Operational complexity: low for one instance, Enterprise
  licensing for existence constraints and fine-grained access.
- *RDF-native.* Strengths: PROV-O, SHACL and SKOS as first-class
  standards; SHACL at commit in GraphDB, RDF4J, Stardog and Fluree
  (Jena validates on request); named graphs or reifiers for
  statement-level metadata; OSLC Core 3.0, the lifecycle-linking
  standard, is RDF/LDP-based, so an RDF store is OSLC-conformable
  without a mapping. Limitations: the same absence of native status and
  of history in every RDF store surveyed; licence cliffs (GraphDB 11
  requires a licence for every edition; Stardog Free is a renewable
  one-year licence); SPARQL 1.2 is a Working Draft (25 October 2026) and
  RDF 1.2 Concepts a Candidate Recommendation (7 April 2026), so
  vendors' RDF-star differs from the standard's triple terms.
- *Versioned stores.* The one class that supplies §1.6 natively.
  Fluree is the only product combining RDF, SHACL at transaction time
  and as-of queries; TerminusDB gives git-like branch and merge over a
  JSON-LD graph. Neither has the agent ecosystem; both are smaller
  communities (BSL and Apache-2.0 respectively). For a repository whose
  central question is "what did we know, and what changed", they
  remove R-STALE's hardest half (keeping history) and leave the
  epistemic modelling exactly as custom as it is on Neo4j.
- *Vector databases and document RAG.* Provenance and status are payload
  fields filterable at query time; no relationships, no multi-hop, no
  cross-record constraints; the baseline arm of the PoC is this class
  with the documents in the prompt. Where the question is single-fact
  retrieval over prose they win [measured]: evidence recall 83 versus 61
  for the graph method on fact retrieval (GraphRAG-Bench), F1 64.8
  versus 54.5 on NQ (Han et al.), at 40–60× lower construction cost.
- *Hybrid.* Neo4j's native vector index (GA 5.13, HNSW, approximate;
  procedures deprecated 2026.04 for a `SEARCH` clause) or Weaviate with
  cross-references (whose docs say "we strongly encourage you to
  consider whether you can avoid using cross-references"). HybridRAG on
  earnings calls [measured]: faithfulness 0.94 / 0.96 / 0.96 and answer
  relevance 0.91 / 0.89 / 0.96 for vector / graph / hybrid, RAGAS
  scored, one domain. The governed layer of §2 is orthogonal to the
  retrieval mode: the gate runs on keys, whichever retriever found them.
- *Governance applications above the store.* TopBraid EDG's working
  copies, governance-role transitions and change history, OpenMetadata's
  Draft → Approved by assigned reviewers ("In case, the glossary does
  not have any Reviewers assigned, then the glossary terms will be
  Approved by default" — a default to design against), Collibra's
  Candidate → Under Review → Accepted. They prove the lifecycle of §4 is
  an application concern everywhere and give the vocabulary to reuse;
  none models evidence per assertion or documented absence.

**8.3 Does a knowledge graph measurably beat simpler approaches?**
[measured] For retrieval: only on multi-hop and aggregation, and the
original win rates are inflated (§2.4). For governance: no published
measurement exists for any store or toolkit (the five SDD toolkits —
Spec Kit, Kiro, Tessl, OpenSpec, BMAD — "all converge on versioned,
linked, reviewable spec artefacts" and "none publishes any measured
outcome" [tool-documented]). [measured here] The PoC's contribution is
mechanism-level: what a flat document set cannot do at all is D3 (the
exact invalidation set and the suspect output), D5 (the three-valued
answer) and M5's statement-level traceability; what it can do as well
is carry the words "NOT YET SPECIFIED" to a model, and §6 reports what
the model did with them in each arm.

## 9. Quality assurance and evaluation framework

**9.1 Criteria per quality layer, with their standard source.**
[standard] ISO/IEC 25010:2023 gives nine product-quality characteristics
(functional suitability, performance efficiency, compatibility,
interaction capability, reliability, security, maintainability,
flexibility, safety); ISO/IEC 25019:2023 gives quality in use
(beneficialness, freedom from risk, acceptability); ISO/IEC 25012 gives
fifteen data-quality characteristics of which accuracy, completeness,
consistency, credibility, currentness and traceability are measurable
per assertion; ISO/IEC/IEEE 29148:2018 clauses 5.2.5 and 5.2.6 give
per-requirement and per-set characteristics (the per-set ones,
consistency and completeness, are what a graph query checks and a flat
file cannot; the clause bodies are paywalled and the characteristic
names are the standard list, not quoted); DORA's four keys are delivery
performance [industry data]. ISO 8000-8's syntactic / semantic /
pragmatic split maps onto SHACL, the source check, and the agent task's
fitness.

| layer | criterion | measure in the PoC or proposed | evidence class |
|---|---|---|---|
| artefact | correctness | assertions with an execution verification / total required keys (S1: 36 of 36 at `approved`) | [measured here] |
| artefact | completeness | required keys at `absent` or `declared_gap`; requirements without a verifying scenario (R-REQ found REQ-05 in the pristine kit) | [measured here] |
| artefact | consistency | `CONTRADICTS` pairs per key (S4: four pairs on one key); corroborated pairs (S1: 88) | [measured here] |
| artefact | traceability | assertions with ≥ 1 supporting fragment (R-STRUCT: 0 violations in every scenario); outputs' refs resolving (M5) | [measured here] |
| artefact | currency | assertions invalidated by R-STALE; verifications with `valid_until` set | [measured here] |
| artefact | semantic fidelity | extraction agreement across independent artefacts (R-CORROBORATE); the mapper's own tests; a human spot-check sample (not done here) | [proposal] |
| artefact | verification coverage | required keys with a verification record / required keys (S7: 0 of 36; S1: 36 of 36) | [measured here] |
| product | functional suitability | the execution oracle: 11 scenarios, target scenarios per planted defect (M4) | [measured here] |
| product | defect propagation | PLANTED / ORIGINAL per target scenario (the degradation test's R6, reused as M4's target outcome) | [measured here] |
| quality in use | beneficialness, freedom from risk, acceptability | not reached by this PoC or by the degradation test (no users, no deployment) | [unknown] |
| delivery | the four DORA keys | not reached; DORA 2024/2025 associate AI adoption with throughput now positive and stability still negative (regression estimates, n ≈ 39,000 and ≈ 5,000) | [industry data] |

**9.2 Causal mechanisms between layers, graded.**

- *Artefact → product.* [measured] Ambiguity in the specification lowers
  generated-code pass@1 by 7.22 pp on average, up to 32.35 pp (Orchid,
  1,304 tasks, 5,216 variants; preprint); repairing the description
  before generation raises pass@1 by 33.66 % on the modified 23.93 % of
  items (SpecFix, ASE 2025); models rarely ask (0.24–2.2 clarification
  turns where ≥ 1 is required, ClarifyCodeBench 2026). [measured, this
  repository] The degradation test: six of fifteen planted defects
  reached the code, all six concealed by the arm's own suite, every
  outcome the one the kit's precedence rule gives; the gates were green
  over four of five defective kits. [measured here] §6's target-scenario
  outcomes per arm. Mechanism: a model fills omission by its prior and
  resolves conflict by a declared precedence or a majority; the graph's
  contribution is to make the omission and the conflict a verdict
  *before* generation.
- *Product → quality in use → delivery.* [unknown] No study in the fact
  sheets reaches these layers from a knowledge-graph intervention, and
  the cost-escalation claim that would supply the mechanism is contested
  (Menzies et al. 2017: no delayed-issue effect in 171 projects; Bossavit
  on the 100×'s provenance). What survives is detectability, not cost:
  requirements defects have the lowest removal efficiency in Jones's
  13,000-project industry data (77 % against 95 % for coding, unreviewed)
  and were about a third of failures in the NASA data (peer-reviewed);
  the defensible claim is that a defect undetected at the artefact layer
  is more likely to ship, not that it costs 100× more.
- *The reverse edge.* [measured, this repository] The Legible review's
  F1: defects travelled from code through code-derived specs into a
  rebuild, and a code-calibrated oracle turned inheritance into a
  passing grade. A governed repository must therefore record the
  *direction* of derivation (`DERIVED_BY` with the activity's inputs), so
  that a spec derived from code is never counted as independent
  verification of that code. §4 rule 3's "verification is of a (key,
  value)" is half of this; the other half is a verification record
  whose `scope` names its independence.

**9.3 Where defects become harder to detect downstream, and whether
semantic verification interrupts it.** [measured, this repository] The
degradation test's D3 arm: a wrong value stated consistently in every
layer passed lint, score, trace, DMN and glossary gates and the arm's
own suite, and was caught only by calibration against the pristine
oracle (G6: 241 of 258). D5-M2: a deleted clause propagated with every
gate green and the arm's suite green. [measured here] The PoC's rules
interrupt three of the prompt's seven defect classes before generation
by construction (absence → `absent`/`declared_gap`; contradiction →
`disputed`; staleness → `invalidated`), interrupt ambiguity only when a
lexical cue is present (S3), and do not interrupt a consistent wrong
value at all: R-CORROBORATE promotes it to `validated`, and only an
independent verification record keeps it from `verified`. That is the
boundary: semantic verification of the *graph* catches what the
artefacts disagree about or leave out; it cannot catch what they agree
on wrongly, which needs an oracle outside the artefacts — the
prompt's "evaluate correctness through independent evidence".

## 10. The proof of concept: results against the pre-registration, limitations, risks, and the follow-on

The pre-registration (`kg_experiment/PREREGISTRATION.md`, frozen as
#214 before any scored run) is the record; its Results section holds
the run notes and the per-expectation verdicts, which this section
summarises and interprets.

**10.1 Verdicts against the pre-registered expectations** (the counts
are §6's; the pre-registration's Results section carries them with
the run notes).

| id | expectation, in short | verdict |
|---|---|---|
| X1 | S1 PROCEED; both arms generate ≥ 4/5; suite ≥ 10/11 ≥ 4/5 | **held** (5/5, 11/11 ×5 per arm) |
| X2 | S2 BLOCKED; G code null ≥ 4/5; B code ≥ 4/5 with the outage scenario failing ≥ 3/5; B flagging recorded | **held** (G 5/5 null; B 5/5 code, 5/5 fail; B flagged 5/5) |
| X3 | S3 QUALIFIED; G flagged ≥ 4/5 and decision ≠ generate ≥ 4/5; B flagged fewer times than G; a boundary scenario fails ≥ 1 B run | **split**: the G clauses held (5/5, 5/5) and the boundary clause held (5/5), the "B flagged fewer" clause failed (B 5/5 = G 5/5) |
| X4 | S4 BLOCKED; G code null ≥ 4/5 naming the conflict; B code ≥ 4/5; sides recorded | **held** (G 5/5; B 5/5, all on the decision table's side) |
| X5 | S5 QUALIFIED; G never uses the inference as fact; B returns `refused_screening` on the outage ≥ 3/5 | **held on the measured clauses** (G abstained 5/5; B 3/5 exactly `refused_screening`, 4/5 adopting the note); the D6 clause is the frozen-text error of the run notes (BLOCKED by §6's lattice) |
| X6 | S6: exactly the three keys invalidated, nothing else touched, `Derived` suspect; BLOCKED then PROCEED; G names the suspect artefact ≥ 4/5; B cannot | **held on the re-run** (5/5), with the frozen text's omission of `worked_example|price` (four invalidated, not three) and the first run's bundle defect recorded (first run: 4/5, the one cell under the old bundle not naming it) |
| X7 | S7 BLOCKED; G code null ≥ 4/5 (M6 ≤ 1); B code 5/5, suite ≥ 10/11 ≥ 4/5 | **held** (G 5/5 null, M6 0; B 5/5, 11/11 ×5) |
| X8 | G references ≥ 0.8 resolvable | **held** (0.94–1.0 wherever G produced references; B 0.75–1.0, recorded) |
| X9 | D1: uniqueness accepted; existence, key, type refused with an Enterprise message | **held** |
| X10 | D4: `sh:conforms` false on every scenario with a result, the Info-only case included | **held** (7 of 7; Info-only 133–145 results, `conforms: false`) |

Eight held, one split, none failed outright; two frozen-text errors
and three harness defects (the calibration adapter, the S6 bundle, the
verification loader), each recorded before or beside the verdict it
touches.

**10.2 The pre-committed interpretation, applied.** X2, X4 and X7 held,
so at this model and scale the verdict in context was obeyed and the
enforcement question (withhold or advise) is a design choice here
rather than a necessity — a result the literature's weaker figures for
label obedience did not predict, and one that n = 5 at one model
cannot carry to another model; the architecture still withholds
(§7.3), because the cost of being wrong once is the whole point. X3's
G side held, so the qualified verdict did stop silent invention of a
value — but at the price of worse code, which the matrix did not
anticipate and §6.4 records. X2's B clause "failed" in the matrix's
sense (the baseline flagged as often as the governed arm), so for the
declared gap the metadata added nothing to *flagging* that the words
"NOT YET SPECIFIED" did not carry; what it changed was the decision,
five abstentions against five generations, and that is the store's
contribution as a gate, not as a label. X5's B clause held: an
unreviewed machine note in a document was adopted as a decision in
four of five runs. X6 held on the re-run after a harness fix the
matrix prescribed.

**10.3 Limitations, as they bit.**

- *Toy scale.* Ten artefacts, 145 assertions, 36 required keys, one
  kit whose values are adversarial by construction. Nothing here
  speaks to the knowledge-graph settlement's scale trigger (10⁵–10⁶
  elements), to retrieval quality at scale, or to a corpus of
  hand-authored diagrams, where the recreation experiment's first round found 25 claims of a
  Level 5, 100/100 diagram set contradicted by the code under a green
  gate (its E3; the degradation test is the later, planted measurement).
- *One model, n = 5, and a proxy that dropped calls.* Nine of the
  seventy cells failed with repeated HTTP 502 responses on the first
  pass and were retried; every number is capability-relative to
  `gpt-5.1-2025-11-13` on 2026-10-30. Three of the five governed S3 runs wrote the pristine 41/42/66/67
  into their constants with no number in their input (one chose
  40/40/66/66, one moved the decision out of the code), so this reads
  as interpretation variance of "low forties" rather than
  contamination, but the kit is public and contamination cannot be
  excluded. *[Corrected 2026-10-30, after the merge: first read "one
  governed S3 run"; the run files say three.]*
- *The graph is not what the model sees.* Both arms see text. The
  behavioural arms measure governance metadata in context; the store's
  own contribution is D2, D3, D5, D6 and the traceability of M5. A
  hand-written status list would give the model the same prompt; it
  could not give D3.
- *Advisory, not withholding.* The governed arm was given the content
  under BLOCKED on purpose, to measure obedience; the architecture
  withholds. The measured obedience at this model (§6) does not
  transfer to another model without re-measurement (§1.4).
- *Designer, planter and grader are one context.* The plant, the 25 %
  bar, the vague-term lexicon, the keyword sets and the required-key
  list are this session's; the oracle is not (frozen 2026-08-06).
  R-VAGUE detected the words it was given, and S3 was written to
  contain them: representation demonstrated, detection not.
- *Fragment granularity over-invalidates* (§3.5): four assertions for
  a one-number change, two of them unchanged in value.
- *The extractors are mappers for one kit.* Per-format, deterministic,
  the aris2puml shape; a second kit needs its own. Nothing was
  measured about LLM extraction; §1.5's figures are the literature's.
- *n10s not executed; Enterprise features not executed.* The RDF
  projection and SHACL validation are Python-side; the three refused
  constraints and the property-value read filter are documented, not
  run.
- *The oracle is the kit's own suite.* It verifies the eleven
  scenarios it has; a consistent wrong value in a key no scenario
  reaches would pass every rule and the oracle alike (§9.3).

**10.4 Risks of the architecture, beyond the PoC.**

- *The status property is writable.* On Community anyone with write
  access can set `status='approved'`; on Enterprise the read filter
  helps and the property is still a property. The approval node with
  its agent and record is the audit trail; the property is a cache of
  it, and a rule should assert they agree.
- *Green over wrong.* `validated` by corroboration is consistency; a
  value every artefact states wrongly reaches `verified` the moment
  one verification record is written against it (§4 rule 1, §9.3).
  The independence of the verification's scope is the only defence,
  and it is a human discipline, not a rule.
- *Ontology upkeep.* The predicate vocabulary (`min`, `max`,
  `on_screening_outage`, the behaviour tokens) is the schema that
  drifts; the 2026-08-26 note's "its cost is the ontology and its
  upkeep, not the store" is confirmed at ten artefacts.
- *Poisoning.* A governed graph is an attack surface for multi-query
  poisoning (GraphRAG under Fire, up to 98 % success on relation
  exploitation [measured]); provenance edges make it auditable, not
  immune.
- *The precedence reflex.* The degradation test's agents and S4's
  baseline resolved contradictions by invoking a precedence the kit
  did or did not state; a governed layer that records a precedence
  rule as an assertion makes it citable, and must then verify it like
  any other.

**10.5 The follow-on proof of concept, recommended.** Scenarios and
success criteria, each with the limitation it addresses:

1. *A withholding arm* (G-W: content withheld under BLOCKED, flags
   only under QUALIFIED) beside the advisory arm, two further models
   from different vendors, n ≥ 10: success is G-W at 0 generations
   under BLOCKED by construction and the advisory arm's obedience
   measured per model, so that §7.3's reading is a measurement and
   not a literature citation.
2. *The kit at the degradation test's scale* (207 files, 163
   requirements, J-F's daily asset load): success is the gate's
   verdicts on the five degraded kits D1–D5 reproducing the measured
   propagation (six of fifteen) as BLOCKED or QUALIFIED before any
   rebuild, with the consistent-wrong-value arm D3 as the expected
   miss.
3. *A human verification loop*: verification records written by a
   person other than the extractor's author against a sample of
   assertions, with inter-rater agreement; success is a measured
   false-approval rate, which this PoC assumed to be zero.
4. *Real artefacts through the chain*: aris2puml's sidecar with D4's
   digests and line → ids map, pumllint's score and trace reports with
   Arc E's run provenance, ingested as verification results against
   process assertions; success is a finding traced to an ARIS object
   through the graph with no name-equality join. This is the one
   scenario that touches either repository, and it waits on their
   gated candidates.
5. *A versioned-store arm* (Fluree or TerminusDB) running the same
   seven scenarios: success is R-STALE's history half supplied by the
   store's as-of query, with the epistemic half measured as equally
   custom.
6. *Extraction fidelity measured*: an LLM-extraction arm beside the
   deterministic mappers on the same kit, graded per assertion;
   success is a precision figure per predicate class, so that basis
   `inferred` carries a measured prior.

## 11. Decision, recorded candidates, triggers

**Decision: nothing queued, no checkbox, priorities unchanged.** The
critical path stays aris2puml A1b → A4. Open checkboxes stay at 17,
all gated.

**Is Neo4j suitable, and under which conditions?** Suitable as the
store of a governed knowledge layer when (a) the questions are about
status and links across artefacts, so that a graph traversal is the
natural query and the three-valued answer must be the same for every
consumer; (b) the organisation accepts that every epistemic construct
is its own modelling, maintained by its own rules, with no help from
the store beyond uniqueness constraints on Community and the three
further constraint families plus property-value read filters on
Enterprise; (c) history is reconstructible from the versioned sources
and the fragment digests, because the store keeps none; and (d) the
agent-facing retriever is built to withhold, not to advise. Prefer an
RDF store where PROV-O, SHACL at commit, OSLC conformance and
standards interchange matter more than the Cypher ecosystem; prefer a
versioned store (Fluree, TerminusDB) where "what did we know on that
date" is the central question. Prefer plain documents with a
maintained index where the questions are single-fact lookups over
prose and no status governs anything, which is the measured regime in
which vector retrieval wins.

**Additional mechanisms required** (none of them native, all of them
implemented or specified here): the metamodel of §3; the seven rules;
verification and approval as recorded acts with scope, method,
evidence digest and validity; the gate with declared required keys and
a task-class threshold; withholding under BLOCKED; registration of
outputs as derived entities; the fragment locator scheme per format;
an independent oracle outside the artefacts for what they agree on
wrongly; and a human decision path for declared gaps.

**Never build**, restated in this question's vocabulary and each
already on record: a graph or triple store on pumllint's product path
(N1); LLM extraction on it (N2); OWL/SHACL as its rule engine (N3);
missing-edge inference (N4); graph-derived metrics in the score without
a charter §10 wave (N5).

**Recorded, not queued:**

1. **The proof of concept as a standing fixture of the thread**
   (`kg_experiment/`), with the follow-on scenarios of §10.5.
   *Trigger:* an adopter whose governed knowledge lives in a store and
   who asks for the chain's reports as evidence in it — row 8c's
   trigger (Arc E run provenance; aris2puml D4), unchanged; a research
   prompt is not an adopter.

**Annotated in place, as pointers:** the knowledge-graph settlement's
re-litigation line (touched, not fired, a third time; its fourth
trigger, outcome-grade evidence, is the one this PoC was built to
approach and does not reach); the graph-store note's bounds sentence
("no Neo4j server is available") — true of that note's Cypher, which
stays unexecuted, and no longer of the thread.

**Re-litigate on** the knowledge-graph settlement's four triggers,
unchanged; or on a second model generation reversing §6's governed-arm
findings at the same scenarios, which would move §7.3's enforcement
reading, not any pumllint item.

## 12. Reproduction

```bash
# pumllint at cf9d919; a Neo4j 5.26.0 community server on bolt://localhost:7687
# (password in KG_NEO4J_PASSWORD, default kgpoc2026); Python 3.13 with
# neo4j 6.4.1, pyyaml, rdflib 7.6.0, pyshacl 0.40.2, openai 3.41.0 and
# this repository installed (pip install -e .).

python stack_experiment/smoke_test.py            # the oracle: reference 11/11, mutants caught
cd kg_experiment/harness
python plant.py                                  # every plant patch matches exactly once
python extract.py S1 | head -40                  # the extraction, per artefact
python run.py --deterministic --out /tmp/dry     # D1-D6 for S1-S7, no model call
python run.py --n 5                              # the scored run (OpenAI key or proxy needed)
python run.py --n 5 --resume --scenarios S3 S4 S6  # re-run only the cells marked api_error
python report.py                                 # the per-scenario, per-arm counts of §6 and §10
python run.py --n 5 --scenarios S6 --out results/rerun   # the S6 re-run with the corrected bundle
python run.py --deterministic --scenarios S6 --out results/d3check  # D3 after the loader fix
python report.py results/rerun                   # the re-run's counts (§6.6, X6)

# D1 by hand, on the community server:
#   CREATE CONSTRAINT t IF NOT EXISTS FOR (n:T) REQUIRE n.status IS NOT NULL
#   -> Neo.DatabaseError.Schema.ConstraintCreationFailed
#      "Property existence constraint requires Neo4j Enterprise Edition"
# D5 by hand, after loading S1:
#   MATCH (x:Assertion {key:'S-review|notified'}) RETURN x.id, x.value, x.status
#   -> four rows, every value 'NONE', every status 'approved'
#   MATCH (x:Assertion {key:'QuoteAPI|notified_after_screening'}) RETURN count(x)
#   -> 0   (unknown: no assertion, not a documented absence)
```

The same stack as two containers: `kg_experiment/demo/` (`docker compose up`)
starts a Neo4j 5.26 community server and a web app that replays the seven
scenarios from `results/`, re-runs D1–D6 or the arms against the container's
store into a dated `results/demo-runs/` folder, and draws each scenario on the
§2 pipeline and on the Legible v0.3 knowledge view; `demo/README.md` has the
one-block start for a Mac, a laptop pulling the published image, or an EC2
instance. `demo/tools/compare_deterministic.py` checks any deterministic run
against the record field by field.

The five fact sheets behind §1, §3, §7, §8 and §9 are not committed;
their load-bearing quotes are cited inline with the source URL at the
primary, and their "could not verify" lists are folded into the bounds
of the sections that use them.

## Related reading

- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md) — N1–N5 and the four triggers.
- [Knowledge graphs for architecture and process artefacts — a research synthesis, evaluated](kg-research-synthesis-evaluation.md) — N3 at the primary; the six-way integration model; Gap 1 and Gap 2.
- [Running pumllint on a graph store (Neo4j), evaluated](graph-store-evaluation.md) — the three readings; Reading 3's consumer-side mapping.
- [The ontology/graph EA stack, evaluated](ea-ontology-stack-evaluation.md) — Loop C.
- `recreate_experiment/degradation-2026-10-28/PREREGISTRATION.md` — the repository's measured defect propagation.
- `recreate_experiment/legible-model-review-2026-10-28/REVIEW.md` — the reverse edge (F1) and shared-premise concealment (F2).
- `kg_experiment/PREREGISTRATION.md` — this note's proof of concept, frozen before the run; its Results section.
