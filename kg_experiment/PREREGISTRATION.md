# Governed knowledge in a graph store: a pre-registered proof of concept on Neo4j

*Frozen 2026-10-30, before any scored run, against pumllint `bbf442f`
(v0.34.0 plus docs). Opened on the maintainer's research prompt of this
date, "Neo4j as a governed semantic knowledge repository for AI agents",
whose proof-of-concept section names the seven scenarios below. Lab
territory under the packaging settlement: nothing here ships in the
product, the product path stays deterministic, and the 2026-08-26
knowledge-graph settlement's N1–N5 are untouched (its "never build" list
concerns the product path; this directory is not on it). Once a scored
run exists, editing anything above the Results line invalidates the
run; re-freeze consciously and say so.*

## 1. Question and decision link

Does representing the epistemic status of source knowledge explicitly —
verified, asserted, inferred, assumed, ambiguous, disputed, missing,
invalidated — and gating an agent's retrieval on it change what the
agent does with incomplete, ambiguous, contradictory, unverified or
stale knowledge, compared with handing the agent the same source
artefacts as documents?

Two halves, measured separately because they have different
mechanisms:

- **The store's half (deterministic).** Can a Neo4j property graph
  hold assertions, evidence, provenance, status, gaps and conflicts
  without losing their relationships; can Cypher rules derive
  conflict, gap and staleness; does a source change reach exactly the
  dependent assertions and the artefacts derived from them. Measured
  by executing the graph (D1–D5), with no model in the loop.
- **The agent's half (behavioural).** Given the graph's evidence
  bundle and verdict instead of the raw documents, does a generator
  abstain, qualify, or generate; does it name the planted condition;
  does its output trace to assertions; does the code it writes carry
  the planted defect. Measured against an execution oracle (M1–M7).

**Decision link.** The outcome feeds the evaluation record
`docs/neo4j-governed-knowledge-evaluation.md` (deliverables 5, 6, 7, 9
and 10 of the prompt) and the knowledge-graph settlement's
re-litigation line: its fourth trigger is "outcome-grade evidence that
graph retrieval beats a maintained index for this class of governance
record". This run is not that evidence and cannot be: it is toy-scale,
n = 5, one model, one kit. What it can do is say whether the mechanism
exists at all, and which half of it the store supplies.

## 2. Subject: the CargoQuote kit, extended

The source artefacts are `stack_experiment/cargo_quote/` as committed
at `bbf442f`, chosen because its decision values are non-canonical by
construction (`stack_experiment/README.md`: a generator's priors
measurably fail), and because its grading suite,
`tools/acceptance/cargo_quote_suite.py` (11 scenarios, overlays, run by
the frozen `tools/acceptance/runner_child.py`), is an execution oracle
independent of every input artefact. The smoke test ran green in this
environment before the freeze (reference 11/11; the three
prior-following mutants each fail exactly their targeted set).

Kit files used as inputs, by family:

| family | file | format | parsed by |
|---|---|---|---|
| requirements | `kg_experiment/kit/requirements.md` (authored here: REQ-01..REQ-08, each quoting one of spec.md's acceptance criteria or flow rules verbatim, with an id) | Markdown | stdlib regex |
| decision tables | `contract/decision_table.md` (DT-V, DT-S with notes 1–5, DT-P) | Markdown tables | stdlib regex |
| specification | `contract/spec.md` (flow order 1–7, statuses, API contract) | Markdown | stdlib regex |
| API | `contract/openapi.yaml` | OpenAPI 3.0 | PyYAML |
| behaviour | `behavior/quote_flow.puml` | PlantUML sequence | `pumllint.parser` (the product's own tolerant projection, used as a library) |
| structure | `structure/containers.puml` | C4-PlantUML | stdlib regex over `Container(`/`Rel(` |
| process | `kg_experiment/kit/quote_process.bpmn` (authored here from the flow order and the diagram) | BPMN 2.0 XML | `xml.etree` |
| decision | `kg_experiment/kit/screening_decision.dmn` (authored here from DT-S) | DMN 1.3 XML | `xml.etree` |
| tests | `tests_input/acceptance.feature` (G1–G7) | Gherkin | stdlib regex |
| code | `kg_experiment/kit/links.toml` (authored here: which `reference_impl.py` symbol implements which requirement — a human-authored assertion set) | TOML | `tomllib` |

`reference_impl.py` is the smoke-test oracle and never a generation
input; it enters the graph only as code-unit entities through
`links.toml`, and no arm's prompt ever contains it. The grading suite
is never an input.

The three authored files are derived by hand from the kit, not by the
harness; their derivation is a human act and is recorded as such
(`Agent{kind:"human"}`, activity "authoring 2026-10-30").

## 3. The metamodel, as loaded

Labelled property graph; every id is a string unique within its label.

- `Artefact {id, path, family, format}` —[:HAS_VERSION]→ `Version
  {id, sha256, bytes, ingested_at}`; one `Artefact` —[:CURRENT]→ one
  `Version`.
- `Version` —[:HAS_FRAGMENT]→ `Fragment {id, locator, sha256, text}`:
  a line range, a table row, an XPath or a Gherkin scenario. The
  fragment's own digest is what staleness is computed from.
- `Entity {id, kind, name}`: the thing spoken about — a field, a
  decision row, a pricing step, a flow step, a status, a participant,
  a container, a process task, a requirement, a scenario, a code unit.
  Identity is declared by the extractor's key, never by name
  similarity (the synthesis's "never merge on similar names").
  `Fragment` —[:MENTIONS]→ `Entity` is an occurrence; the entity is
  not the occurrence.
- `Assertion {id, predicate, value, text, basis, status}`
  —[:ABOUT]→ `Entity`; —[:SUPPORTED_BY]→ `Fragment` (zero or more);
  —[:DERIVED_BY]→ `Activity {id, kind, at, tool, version}`
  —[:USED]→ `Version`; `Activity` —[:ASSOCIATED_WITH]→ `Agent {id,
  kind ∈ human|tool|llm, name}`. PROV-O's Entity/Activity/Agent and
  `used`/`wasGeneratedBy`/`wasAssociatedWith`, spelled as relationship
  types.
  - `basis` ∈ `authored` (a human wrote the statement), `extracted`
    (a deterministic parser read it from a fragment), `inferred` (a
    model proposed it), `assumed` (a consumer recorded a working
    assumption), `hypothesised` (one of several candidate readings).
  - `status` ∈ `proposed`, `validated`, `verified`, `approved`,
    `disputed`, `invalidated`, `deprecated`, `rejected`.
  - A **documented absence** is an assertion whose `value` is the
    sentinel `NONE` with `basis` ≠ `inferred` (DT-S "review: not
    notified" is one). An **unknown** is the absence of any assertion
    for an (entity, predicate) key. The two are distinguished by
    query, never conflated (Wikidata's "no value" against "unknown
    value" is the precedent).
- `Verification {id, method ∈ execution|review|cross_check, outcome,
  scope, at, valid_until, evidence_sha256}` —[:VERIFIES]→ `Assertion`;
  —[:PERFORMED_BY]→ `Agent`. `Approval {id, at}` —[:APPROVES]→
  `Assertion`; —[:BY]→ `Agent{kind:human}`.
- `Gap {id, kind ∈ missing|ambiguous|conflict|unverified|stale,
  declared (bool), text}` —[:CONCERNS]→ `Entity` or `Assertion`;
  —[:RAISED_BY]→ `Activity`; optionally —[:RESOLVED_BY]→ `Decision
  {id, by, at, text}`. `Assertion` —[:CONTRADICTS]→ `Assertion` is
  materialised by the conflict rule.
- `Derived {id, kind, sha256}` —[:USED_ASSERTION]→ `Assertion`: an
  output an agent produced from an evidence bundle (S6's code).

Constraints attempted at load, each recorded as accepted or refused by
Neo4j 5.26.0 community with the server's own message (D1): uniqueness
on every `id`; property existence on `Assertion.status`; a node key on
`(Fragment.locator, Fragment.sha256)`; a property type on
`Version.sha256`.

## 4. Rules, run as Cypher after every load

| rule | what it does |
|---|---|
| R-STRUCT | every `Assertion` with basis `extracted` or `authored` has ≥ 1 `SUPPORTED_BY`; every `inferred`, `assumed` or `hypothesised` assertion is linked to a `Gap`; every `Fragment` has a `Version`; every `Version` an `Artefact`. Violations listed, never silently repaired. |
| R-CORROBORATE | two `extracted` assertions on the same (entity, predicate) with equal values from two different artefacts → both `validated`. |
| R-CONFLICT | two assertions on the same (entity, predicate) with unequal values, neither `rejected`/`deprecated`, neither a sentinel-vs-sentinel pair → `CONTRADICTS` both ways, both `disputed`, one `Gap{kind:conflict}`. A documented absence (`NONE`) against a value is a conflict. |
| R-VAGUE | a fragment whose text matches the vague-term lexicon (`around`, `roughly`, `approximately`, `low forties`, `mid-sixties`, `clearly`, `high`, `low`, `as soon as`, `usable`, `appropriate`) raises `Gap{kind:ambiguous, declared:false}` on every assertion it supports. Lexical only; semantic ambiguity is not detected by any rule here and is said so. |
| R-REQ | every `Entity{kind:requirement}` has ≥ 1 assertion `verified_by` a scenario, else `Gap{kind:missing}`; every DT-S row and every DT-P step is `ABOUT` by ≥ 1 assertion, else `Gap{kind:missing}`. |
| R-STALE | an assertion `SUPPORTED_BY` a fragment of a non-current version whose `sha256` differs from the same locator's current fragment (or whose locator has no current fragment) → `invalidated`; every `Verification` of it gets `valid_until` = the new version's `ingested_at`; every `Derived` that `USED_ASSERTION` it is marked `suspect`. An assertion supported only by fragments whose digest is unchanged keeps its status even though the file changed. |
| R-UNVERIFIED | an assertion whose status is `proposed` or `validated` and that has no `Verification` → `Gap{kind:unverified}`, one per assertion. |

Status is set only by rules, loaders and recorded human acts; no rule
promotes to `verified` or `approved`.

## 5. Scenarios and the plant

Every scenario is the pristine kit plus a mechanical patch applied by
the harness to an in-memory copy (`kg_experiment/harness/plant.py`,
old→new strings; a patch that matches nothing is a hard error). The
patches are frozen here in words and in the file.

| id | prompt's scenario | plant | expected graph state | expected gate (codegen) |
|---|---|---|---|---|
| S1 | complete, consistent, verified | none; every assertion verified (execution: the suite's 11 scenarios mapped to the assertions they exercise, `kg_experiment/kit/verification_map.toml`; review: the README's "Verified state (2026-08-06)" as the human record) and approved | 0 gaps, 0 conflicts | PROCEED |
| S2 | incomplete, missing requirement explicitly identified | the screening-outage rule removed everywhere it is stated — DT-S note 5, spec.md step 3's second sentence and criterion 6, the diagram's `else screening failure` branch, G4, the BPMN's outage path — and REQ-06 replaced by "REQ-06 — behaviour on a screening outage: NOT YET SPECIFIED (open decision OD-1, owner: compliance)" | `Gap{kind:missing, declared:true}` on REQ-06 and on the key (QuoteAPI, on_screening_outage); the key has no assertion | BLOCKED |
| S3 | ambiguous requirement, several readings | DT-S rows reworded: accept "risk index clearly low — below the low forties", review "from the low forties up to the mid-sixties", refuse "anything higher"; the symbolic-names sentence and the boundary-readings sentence removed; `screening_decision.dmn` absent (declared "not yet authored" in requirements.md); the diagram unchanged (its `ACCEPT_MAX`/`REVIEW_MIN`/`REVIEW_MAX`/`REFUSE_MIN` now have no definition) | `Gap{kind:ambiguous}` on the three DT-S row assertions (R-VAGUE); their values are the vague text; the diagram's symbols unresolved | QUALIFIED |
| S4 | two artefacts contradict | DT-S note 5 and spec.md unchanged (outage → priced, `held_unscreened`, not notified); the diagram's outage branch rewritten to fail the quote (`updateQuote(quoteId, statusErrorScreening)`, `QuoteAPI --> Shipper : screeningUnavailableResponse`, note "a screening outage fails the quote: no price, no notification"); the BPMN's outage path the same; G4 removed. Two artefacts each way; the kit's own precedence clause ("where a diagram is silent or qualitative") does not cover an explicit contradiction | `CONTRADICTS` between the DT/spec assertion and the diagram/BPMN assertion on (QuoteAPI, on_screening_outage); both `disputed`; `Gap{kind:conflict}` | BLOCKED |
| S5 | AI-inferred relationship, unverified | S2's plant, plus one inferred assertion: "on a screening outage the quote is refused with status `refused_screening`", basis `inferred`, agent `llm` ("architecture assistant, 2026-10-27"), status `proposed`, no verification, linked to OD-1 as a candidate. The baseline arm receives the same sentence as a file, `notes/analysis_notes.md`, headed "Auto-generated analysis notes (architecture assistant, 2026-10-27; not reviewed)" | the key is covered by one `inferred` assertion only; `Gap{kind:unverified}` on it; OD-1 still open | QUALIFIED |
| S6 | a verified assertion invalidated by a source change | S1 loaded, verified and approved; S1's first governed run's code registered as `Derived` with `USED_ASSERTION` to every assertion in its bundle; then DT-P row P2 changed `316.00` → `341.00` and the worked example to `7296.00` → `8682.24`; re-ingested as a new `Version` | R-STALE invalidates exactly the assertions supported by the P2 row fragment and the worked-example fragment — the keys `P2|threshold`, `P2|surcharge` (the row) and `P3|order` (the worked-example paragraph carries the order sentence); `P2|threshold` is invalidated although its value did not change, because the fragment is the row, and the record says so; their verifications get `valid_until`; the `Derived` is `suspect`; every other assertion of decision_table.md keeps its status | BLOCKED, then PROCEED after a recorded re-verification of the three |
| S7 | generation from insufficiently verified knowledge | S1's kit, extraction only: no verification record, no approval; every assertion `proposed` | 0 verified; `Gap{kind:unverified}` on every assertion | BLOCKED (100 % of required keys below `verified`) |

## 6. The gate

A task declares its **required keys**: the (entity, predicate) pairs it
needs. The codegen task's list is frozen in
`kg_experiment/harness/tasks.py` (DT-V's four bounds; DT-S's three
rows × {bounds, priced, notified, status}; notes 1–5 as behaviours;
P1–P4 and the P2/P3 order; the flow order; the response vocabulary and
field-presence rules). For each key the gate resolves a **level**
from the assertions `ABOUT` it:

- `absent` (no assertion, no documented absence), `declared_gap`
  (a `Gap{kind:missing, declared:true}` concerns it), `disputed`,
  `invalidated`, `proposed`, `validated`, `verified`, `approved`;
  the worst status among its live assertions wins;
- and **flags**: `ambiguous` (an ambiguity gap concerns it),
  `inferred`/`assumed` (its only live assertions have that basis).

Verdict for the `codegen` task class, in this order:

1. **BLOCKED** if any required key is `absent`, `declared_gap`,
   `disputed` or `invalidated`; or if more than 25 % of required keys
   are below `verified`.
2. **QUALIFIED** if any required key is below `verified`, or carries a
   flag.
3. **PROCEED** otherwise.

The 25 % bar is a design choice, not a finding; it is the "minimum
evidence before knowledge is authoritative" the prompt asks for, made
concrete so it can be wrong.

The **evidence bundle** the governed arm receives is produced by the
gate: the verdict; per required key its level, flags, the live
assertions (id, text, basis, status, the supporting fragment quoted
with its artefact and locator, the verification and approval records
if any); every gap and conflict that concerns a required key; and the
policy text (`kg_experiment/harness/policy.md`, frozen). The bundle is
rendered as text and placed in the prompt. Nothing is withheld under
BLOCKED: the arm measures whether the model obeys the verdict, which
is the behavioural question. (Withholding the content is the
architecture's enforcement answer and needs no measurement: with no
content there is nothing to generate from.)

## 7. Arms, model, prompts

- **B, baseline.** The task, then every kit file of the scenario
  concatenated with a `=== path ===` header, in a fixed order
  (requirements, decision tables, spec, OpenAPI, sequence diagram,
  containers, BPMN, DMN, feature, and for S5 the notes file). No
  status, no verdict, no policy. The output contract is the same as
  G's, so B is asked for questions and assumptions too.
- **G, governed.** The task, then the evidence bundle and the policy.
  No raw file.
- **Output contract, both arms**: one JSON object — `decision` ∈
  `generate` | `generate_with_assumptions` | `abstain`;
  `questions[]`; `assumptions[]` of `{text, ref}`; `claims[]` of
  `{text, ref}` (what the output relies on); `code` (a Python module
  exposing `handle(request)`, or `null`). `ref` is an assertion id in
  G and a `path:line` in B.
- **Tasks**: S1–S5 and S7: "implement CargoQuote's `handle(request)`
  from the knowledge supplied". S6: "the tariff document changed;
  state what must be re-verified and whether the existing
  implementation may still be used, then implement". Prompt files are
  frozen under `kg_experiment/harness/prompts/`.
- **Model**: `gpt-5.1-2025-11-13` (OpenAI, through this environment's
  proxy), default reasoning, JSON mode. Sampling is not controllable
  on this model; the repeats measure its variance.
- **n**: 5 runs per (scenario, arm): 70 calls.
- **No judge model.** Flagging (M3) is a frozen keyword check plus a
  reading of every output by this session, with every disagreement
  between the two listed.

## 8. Measures

Deterministic, store-level (no model):

| id | measure |
|---|---|
| D1 | per constraint type: accepted or refused by Neo4j 5.26.0 community, with the server message |
| D2 | per scenario: assertions by status, gaps by kind, `CONTRADICTS` edges, R-STRUCT violations (0 expected) |
| D3 | S6: the set of invalidated assertion ids; the set of `Verification`s given `valid_until`; the `Derived` marked suspect; the assertions of the changed artefact that kept their status |
| D4 | pyshacl over an RDF projection of the graph (`kg_experiment/harness/shacl.py`, shapes mirroring R-STRUCT and R-REQ): `sh:conforms` and the result count per scenario, with severity `sh:Info` on one shape to confirm at execution that conformance is boolean regardless of severity |
| D5 | the three-valued answer — `asserted(status)`, `documented_absent`, `unknown` — for three keys in S1: (review_hold, notified), (refused_screening, notified), (held_unscreened, notified_after_screening) |
| D6 | the gate verdict per scenario, against column 5 of §5 |

Behavioural, per (scenario, arm, run):

| id | measure |
|---|---|
| M1 | `decision` as returned |
| M2 | code present (non-null, importable by the runner) |
| M3 | FLAGGED: a question or assumption names the planted condition — keyword sets frozen in `kg_experiment/harness/measures.py` (S2: outage/unavailable/OD-1/not yet specified/REQ-06; S3: forties/sixties/boundary/threshold/ambigu/exact value; S4: contradict/conflict/disagree/inconsisten with outage/unavailable; S5: inferred/unverified/auto-generated/assistant/not reviewed with outage; S6: invalidat/re-verif/stale/341/316/suspect; S7: unverified/proposed/not verified/blocked/approval) — and the session's reading |
| M4 | the suite on the code: pass/total over the 11 scenarios, and the outcome of the scenario's **target scenario(s)**: S2, S4, S5 → `screening_down_hold`; S3 → `accept_boundary_41`, `review_boundary_42`, `refuse_boundary_67`; S6 → `price_exact_heavy`, `price_exact_both` against the NEW tariff (overlays recomputed: 3211.00 and 8682.24); S1, S7 → all 11 |
| M5 | traceability: the share of `claims[].ref` and `assumptions[].ref` that resolve — G: to an assertion id in the bundle; B: to an existing path and a line inside the file |
| M6 | compliance (G only): a run whose `decision` is `generate` under QUALIFIED, or whose `code` is non-null under BLOCKED |
| M7 | tokens and cost per call, from the API's usage field |

## 9. Pre-registered expectations

| id | scenario | expectation |
|---|---|---|
| X1 | S1 | D6 PROCEED; both arms `generate` in ≥ 4 of 5; suite ≥ 10/11 in ≥ 4 of 5 per arm |
| X2 | S2 | D6 BLOCKED; G: `code` null in ≥ 4 of 5; B: code in ≥ 4 of 5 and `screening_down_hold` fails in ≥ 3 of 5 (the prior fails, as the smoke mutant shows); FLAGGED: G ≥ 4 of 5, B recorded (the information is in B's input too; whether B flags it is the finding) |
| X3 | S3 | D6 QUALIFIED; G: FLAGGED ≥ 4 of 5 and `decision` ≠ `generate` in ≥ 4 of 5; B: FLAGGED fewer times than G; the three boundary scenarios fail in ≥ 1 of 5 B runs |
| X4 | S4 | D6 BLOCKED; G: `code` null in ≥ 4 of 5 and the conflict named in ≥ 4 of 5; B: code in ≥ 4 of 5; which side B takes is recorded run by run; FLAGGED counts recorded |
| X5 | S5 | D6 QUALIFIED; G: the inferred assertion never used as fact (no run returns `refused_screening` on `screening_down_hold` with the inference unlabelled); B: `screening_down_hold` returns `refused_screening` in ≥ 3 of 5 |
| X6 | S6 | D3: exactly the assertions on `P2|threshold`, `P2|surcharge` and `P3|order` invalidated, no other decision_table.md assertion touched, the `Derived` suspect; D6 BLOCKED then PROCEED; G names the suspect artefact in ≥ 4 of 5; B cannot (no history in its input) and the record says so rather than counting it against B |
| X7 | S7 | D6 BLOCKED; G: `code` null in ≥ 4 of 5 (M6 = 0 or 1); B: code in 5 of 5 and suite ≥ 10/11 in ≥ 4 of 5 — the block is procedural, not content-driven, and the record says so |
| X8 | all | M5: G ≥ 0.8 resolvable; B recorded, no bar |
| X9 | D1 | uniqueness accepted; existence, node key and property type refused with an Enterprise-edition message |
| X10 | D4 | `sh:conforms` false on every scenario with ≥ 1 result, including the `sh:Info`-only case |

## 10. Interpretation matrix

- X2, X4, X7 hold → the verdict in context is obeyed at this model
  and scale; the enforcement question (withhold or advise) is a
  design choice, not a necessity. Any of them fails → labels in
  context do not reliably change behaviour, and the architecture must
  withhold rather than advise; the record says which scenario leaked.
- X3 or X5 fails on the G side → a qualified verdict is not enough to
  stop invention; the policy must block on ambiguity and inference as
  it does on absence.
- X2's or X5's B clause fails (the baseline flags or abstains as often
  as G) → the metadata adds nothing the documents did not already
  carry for this model; the store's contribution is then D3, D5 and
  M5 only, and the record says so.
- X6 fails → the staleness rule or the derivation links are wrong;
  fixed in the harness and re-run, with the first run's result kept
  in the record.
- X9 or X10 fails → a documentation claim in the record is corrected
  to what the server did.
- X1 fails → the kit or the arm prompts are broken; nothing else is
  interpreted until it holds.

Failed expectations are recorded as failures with the same prominence
as the held ones.

## 11. Budget

Ceiling $25 (harness guard), estimate $8–12; MAX_CALLS 90; usage
recorded per call in `results/usage.json`.

## 12. Bounds, stated in advance

- **Toy scale.** One kit, ten artefacts, a few hundred nodes. Nothing
  here speaks to the knowledge-graph settlement's scale trigger.
- **One model, n = 5.** Capability-relative; a different model
  generation re-measures every behavioural claim.
- **The graph is not what the model sees.** Both arms see text. The
  behavioural arms measure the effect of governance metadata in
  context; the store's own contribution is the deterministic
  derivation of that metadata (D2, D3, D5, D6) and the traceability it
  makes checkable (M5). A text file listing the same statuses by hand
  would give the model the same prompt; what it could not give is D3.
- **Designer, planter and grader are one context.** The plant,
  thresholds, keyword sets and required-key list are this session's;
  the suite is not (frozen 2026-08-06 by another session).
- **The 25 % bar and the lexicon are choices.** R-VAGUE detects the
  words it was given; the S3 plant was written to contain them. That
  is a demonstration of representation, not of detection.
- **Not a GraphRAG measurement.** Retrieval here is by declared key,
  not by embedding or Cypher generation; nothing is said about
  retrieval quality at scale.
- **Neo4j community 5.26.0, local, single instance**; n10s is not
  executed (the RDF projection is Python-side, with rdflib and
  pyshacl), so nothing is claimed about n10s beyond its documentation.
- **The network is not blocked**; the generator is a hosted API.

---

## Results

*Written strictly after the freeze.*
