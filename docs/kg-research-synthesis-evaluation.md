# Knowledge graphs for architecture and process artefacts — a research synthesis, evaluated

*Dated evaluation, 2026-10-12, written against pumllint `558d762` (v0.33.0
plus docs) and aris2puml `f725b59`. The question as posed: evaluate the
maintainer's research note of the same date, "Knowledge graphs for
architecture and process artefacts — Medium research" (a private Notion
page), and investigate which of its elements are relevant to pumllint.*

**Verdict up front: nothing to build, and little that is new. The
synthesis's main proposal — a graph store, an ontology, SHACL validation,
LLM-proposed links — lands on five settled records and fires none of their
triggers. What it adds is evidentiary and diagnostic. Evidentiary: it cites
the W3C primaries the 2026-08-26 knowledge-graph note could only
characterize, and read at w3.org they confirm that note's N3 from both
sides — OWL cannot see an absence, SHACL reports every absence a shape
constrains, and neither grades. Diagnostic: its integration model separates *representation*,
*transformation run* and *validation result*, and keeps a diagram's
occurrence of an element apart from the entity it depicts. Held against the
chain, that separation finds two gaps no record names. **Gap 1**: what the
chain *ships* names its inputs by path only — pumllint's JSON reports carry
no tool version, configuration identity or input digest (the HTML report's
footer names the version, and nothing else), and aris2puml's sidecar names
its tool version but no digest. The project's own measurement drivers do
digest their inputs (§4); the shipped tools do not. **Gap 2**:
element identity stops at aris2puml's emitter — the ARIS ids survive into
the JSON and the sidecar's notes, none reaches the `.puml`, and a pumllint
finding offers `(file, line)` and the element's name, so the only way back
to the ARIS object is the name-equality join the synthesis warns against.
Both are recorded as gated candidates, one per repository's contract —
pumllint's covering the score and trace reports, not lint; neither is
queued, and no priority moves.**

*Bounds: every repository claim was executed at the two commits above, and
§9 lists the commands. The primaries were read at the source for the
load-bearing facts only: SHACL (W3C Recommendation, 20 July 2017) §2.1.4,
§3.6.1.1 and `sh:minCount`; the OWL 2 Primer (Second Edition, W3C
Recommendation, 11 December 2012) §2 and §4.8; PROV-O (W3C Recommendation,
30 April 2013) for the terms §4 uses; DataCite's best-practice page for
the landing-page rule. This is the first time w3.org was reachable for this
thread. The seven Medium articles were not fetched: they are characterized
from the synthesis, and no verdict rests on them. The OMG BPMN, Neo4j
neosemantics, Crossref and DOI Foundation pages were not read, and nothing
here depends on them. The DCAT 3 page was read for its status line only.*

*Corrected 2026-10-16, after a code review of this record: seven
statements were wrong or overreached, and are fixed in place. XD005 never
joins swimlanes (§2, §5); the demo is the golden plus a comment header, not
the golden (§5); Gap 1 is about what the chain ships, not every run record
(verdict, §4); per-input digests are a per-file fact and do not ride as
root keys (§4 constraints 1–2, §8); lint findings get no provenance from a
score or trace report, which is a separate run (§4 constraint 1); and the
shared digest is now defined to the byte (§4 constraint 4). The ROADMAP's
decision log carries the same list under this date.*

*Corrected again 2026-10-16 (#171), after a code review of that correction:
the ROADMAP's decision log, under this record's 2026-10-12 entry, holds the
one list of findings and where each was fixed. In this file: the verdict's
last sentence, §4 constraints 1, 2, 4, 5 and the new 7 (open questions for
the build, with their evidence), §5's join, §6's acceptance line, §8 and
§9. The note above is left as #170 wrote it; it is wrong in two places. It
says digests "do not ride as root keys", while §4 puts the digests no item
carries in a root list: digests are a per-file fact, not a run-level root
key on the `syntaxGateRan` precedent. And it leaves out constraint 6, which
#170 also rewrote. This note's repository claims were executed against
pumllint's code at `64007cb`, which neither correction changes; §9 lists
the commands.*

## 0. The document, so this note stands alone

The synthesis is a curated review, explicitly "not an exhaustive literature
review or an executed software benchmark". It has six parts:

- **Seven Medium articles**, ranked for relevance to integrating
  requirements, processes, architecture, interfaces and tests:
  1. Alenezi (2026): an ontology-backed repository linking requirements,
     architecture decisions, OpenAPI, Git and delivery evidence.
  2. Figay (2024): ArchiMate → OWL.
  3. Lazarevic (2021): an Archi model explored in Neo4j.
  4. Staehler (2025): source text → rules and processes → knowledge graph
     → BPMN, with the author reporting wrongly generated XOR branches.
  5. Achtziger (2026): entity identity, vocabulary alignment and validation.
  6. Figay (2025): explicit transformation rules and derivation history.
  7. Pospisil (2021): architecture documentation generated from graph facts.
- **Grounded findings**:
  - identity independent of labels and of diagram appearances (§2.1);
  - meaning, validation and execution are separate concerns — OWL is
    open-world, SHACL validates constraints, BPMN defines process
    semantics, and a SHACL-valid graph does not prove a process behaves
    (§2.2);
  - ontology import implements a subset (§2.3);
  - provenance should describe transformations, PROV-O (§2.4);
  - two corrections to the articles: non-standard `dcat:` terms, and
    generated BPMN (§2.5).
- **An integration model.** A table of artefact families (requirements,
  architecture models, BPMN processes, API specifications, tests,
  documents and transformations). Then a six-way separation: *semantic
  entity*, *artefact and version*, *representation* (file, format,
  location, content hash), *assertion*, *transformation run*, *validation
  result*.
- **Do's and don'ts.** Parse exports deterministically first; let LLMs
  only propose links; keep asserted, inferred and proposed apart; never
  reduce relationship types to `RELATED_TO`; never merge entities on name
  or embedding similarity; never treat conformance as truth or overwrite
  history.
- **DOI practice**: cite with DOIs; mint them for citable releases only;
  keep identifier, version, location and hash separate.
- **A first experiment**: one process with its requirements, architecture,
  API specification and tests, and three questions — what a changed
  requirement affects; which tasks lack an implementing service; which
  source version and transformation justify each link.

## 1. What is settled, and why none of it reopens

| The synthesis proposes | Settled record | Here |
|---|---|---|
| A graph database or triple store holding the artefacts | Knowledge graph, 2026-08-26, **N1** | Refused on scale (950 elements across the 174-diagram wild corpus) and on the zero-dependency agreement. The synthesis agrees on the point that matters: "the research does not establish a universal database winner". |
| LLMs proposing links from prose | **N2** and the deterministic-product-path agreement | Compatible off the product path, which is where docs/agents.md and `tools/` keep generation. The synthesis's own rule — keep asserted, inferred and proposed apart — is what the deterministic product path enforces by construction: nothing proposed reaches a finding. |
| OWL for meaning, SHACL for validation | **N3**; Linked.Archi, 2026-08-27 | Confirmed at the primary; see §3. |
| Answering "which tasks lack a service" by inference | **N4** (missing-edge inference: no oracle) | See §6, Q2. |
| ArchiMate → OWL (Figay), Archi → Neo4j (Lazarevic) | ArchiMate note **N3** (reading `.archimate` or Model Exchange XML, refused on scope and identity) and the Linked.Archi settlement | Both articles read the Archi model, not a `.puml`. That confirms the premise of the ArchiMate note's **N1**: the `.puml` is a rendering of a model held elsewhere. |
| The whole pipeline: sources → ontology → validation → report | EA ontology stack, 2026-09-14 (**Loop C**) | Same seam: pumllint gates the file a human wrote, before stage 1. |

None of the knowledge-graph settlement's four triggers fires:

1. **A model set beyond one in-memory batch** (10⁵–10⁶ elements): none is
   named.
2. **A concrete cross-repository identity ask** that the sequence↔contract
   and `trace` items cannot serve: a synthesis is not an ask. Gap 2 is the
   nearest thing to one, and it is served by a file-to-file map (§5).
3. **A pilot census with a denser entity graph**: no census has run.
4. **Outcome-grade evidence that graph retrieval beats a maintained
   index**: the document disclaims being a benchmark.

The Linked.Archi trigger — an adopter running an RDF/SHACL EA pipeline
with PlantUML producers — names an adopter, and none is named here.

Running the synthesis's experiment would be an owner go, not a trigger.
§6 shows that the chain's half of it already ran.

## 2. Element by element

| Synthesis element | Relevance | Where it lands |
|---|---|---|
| Alenezi | Same shape as existing work | Arc G's matrix: "requirement → process step → rule → component → contract → verification", whose columns `trace`'s schema reserves as additive properties on the requirement row. Shipped columns: requirement ↔ diagram (v0.25.0) and requirement ↔ feature-file reference (`--features`, 2026-09-09). Recorded: message ↔ operation (sequence↔contract, 2026-07-29). ADR ids ride GEN007's pattern. No column needs a store. |
| Staehler | Supports existing rules | Generated XOR branches are model-supplied structure: the failure the agent-repair wave measured (−6 pp pooled, −53 pp from one invented guard). It is also why aris2puml refuses an ArchiMate front-end: exclusivity inferred from a label is invented structure. The synthesis draws the same conclusion — "assisted modelling, not verified automatic process generation". |
| Achtziger | Recorded | The glossary/approved-term rule, a recorded keeper; trigger: a real term list. |
| Figay (2025) | Already practised | Explicit transformation rules: aris2puml's mapping table, one row per element with the pumllint rule that checks it, moved in both repositories together and pinned by the golden. Derivation history: the sidecar's notes. Its `dcat:` terms are irrelevant here. |
| Pospisil | Same discipline | Documentation rendered from a model is Arc H's verbalizer. Its precondition — unmodelled-content tracking, so a rendering says what it does not show — is the synthesis's "claim lossless round-tripping only when fixtures demonstrate it", in this repository's form. |
| §2.1 identity | **Relevant** | Gap 2, §5. |
| §2.2 separate concerns | **Strongest support** | §3. |
| §2.3 ontology import | None | Nothing is imported. |
| §2.4 provenance | **Relevant** | Gap 1, §4. |
| §2.5 corrections | Supports existing rules | DCAT: no use here. BPMN: see Staehler. |
| §3 integration model | Locates the chain | Entity: the ARIS object definition, whose occurrence in an EPC is the appearance §2.1 keeps apart. Representations: the JSON export and the `.puml` ("a *view* of the EPC", in `aris2puml/report.py`'s words). Transformation run: aris2puml's sidecar. Inventory: `--manifest`. Assertions: pumllint's findings; validation result: its report. |
| §3, "requirement constrains process" | Shipped, untyped | `trace`'s link: one untyped, undirected relation (2026-08-28). |
| §3, "test verifies requirement" | Shipped, declared only | `--features` records a declared reference: `verified` means "at least one feature file references this ID". It never records an execution result or a tested version. |
| §3, "task invokes operation" | No item | sequence↔contract is message → operation on *sequence* diagrams. Nothing carries an activity action's operation. |
| §3, "component realizes service; service supports process" | No item | No component parser (Arc C, census-gated at 0 of 39), and no ArchiMate pack or reader (that note's N1 and N3). |
| §4 Do: parse deterministically first | Already the rule | aris2puml reads exports, never prose; pumllint's product path is deterministic. |
| §4 Do: keep asserted, inferred and proposed apart | Already the rule | pumllint only asserts (N4 refuses inference). aris2puml qualifies its own assertions: approximated, dropped, flagged, refused. |
| §4 Do: record the rule behind each derivation | Already the rule | `ruleId` on every finding; `code` and `node` on every sidecar note. |
| §4 Do: test cross-artefact questions against reviewed answers | Already the rule | The executable RULES.md, the golden scores, aris2puml's golden diagram and corpus census. |
| §4 Don't: reduce relationships to `RELATED_TO` | The shape `trace` has | Typed diagram→diagram links are Arc C's G6/O4 item. Trigger unchanged: an adopter running `trace` who asks for them. |
| §4 Don't: merge entities on similar names | **The XD join, in exact-match form** | XD joins on name equality: participants by alias, swimlanes by name — in XD004 only, case-insensitively. XD005 never sees a swimlane: a lane declares no stereotype, and XD005 keeps only sites that declare one. XD compares and reports; it never merges. `distinct` declares a join false. The display-name identity candidate (Arc C, G2) is already written as evidence-shaped, minor and `distinct`-honouring, so this warning bounds G2 rather than firing it; G2's trigger is an adopter corpus using aliases inconsistently. |
| §4 Don't: treat conformance as truth | Already the rule | "Gate on the linter, not the level"; the chain certifies Know What and never Know Why (2026-09-14). |
| §4 Don't: overwrite history | Already the discipline | The ROADMAP's decision log annotates in place. The product keeps one level per diagram and leaves history to git. |
| §4 Don't: claim lossless round-tripping | Already the rule | aris2puml's census figures and the sidecar's `dropped`. |
| §4 Don't: build the ontology before the slice | Already the rule | The demand-driven agreement. |
| §5 DOIs | Marginal | §7. |
| §6 first experiment | Already run, in part | §6. |

## 3. N3, read at the primary

The knowledge-graph note refused OWL/SHACL as the rule engine on two
grounds:

1. well-formedness as a type deletes the graded product;
2. closed-world validation over pumllint's tolerant projection reports
   absence of parse as absence of fact.

The first ground rests on this repository's own 2026-08-02 settlement. The
second rested on outside facts: the note's bounds recorded w3.org as
unreachable, so what it said of SHACL and OWL came from search summaries,
and the Linked.Archi note's "binary conformance" from Linked.Archi's own
validation page. Read at the source:

- **SHACL §3.6.1.1**: `sh:conforms` is of datatype `xsd:boolean`, "true if
  and only if the validation did not produce any validation results".
- **SHACL §2.1.4**, informative: "The specific values of `sh:severity` have
  no impact on the validation". Results carry one of three severities
  (`sh:Info`, `sh:Warning`, `sh:Violation`), and conformance discards them:
  a single `sh:Info` result makes a graph non-conforming.
- **SHACL, `sh:minCount`**: "If the number of value nodes is less than
  $minCount, there is a validation result." An absent value is a result.
- **OWL 2 Primer §2**: information absent from a document "may simply be
  missing (but possibly true), following the open-world assumption". The
  same section: "OWL 2 is not a schema language for syntax conformance".
- **OWL 2 Primer §4.8**: "a domain (or range) statement is not a constraint
  on the knowledge, but allows a reasoner to infer further knowledge".

Together they make the dilemma exact:

- **OWL** cannot see an absence. An owner, a guard or a requirement
  reference the graph does not state is, in the Primer's words, "possibly
  true".
- **SHACL** reports every absence a shape constrains, including what
  pumllint's projection simply did not read (103 of 174 diagrams
  dialect-invisible in the 2026-08-11 wild census).
- **Neither grades.** SHACL's severities are labels on results; its only
  verdict is a boolean.

pumllint's product sits in the space between: findings graded across five
severities, six dimensions and five levels, over a projection that says
what it did not read (the `!include` disclosure, the zero-element cap).

The synthesis's §2.2 reaches the same place from the other side: "a
SHACL-valid graph does not prove that a process behaves correctly". N3
stands, and is now quoted rather than characterized. The Linked.Archi
note's "binary by the specification", read then from Linked.Archi's page,
is annotated as confirmed.

## 4. Gap 1 — the shipped reports name their inputs by path only

What each output carries, as executed:

| Command (pumllint 0.33.0; aris2puml 0.1.0) | What it names about its own run |
|---|---|
| `pumllint examples/ -f json` | A JSON **array**. Each finding is `{file, line, message, ruleId, severity}`. Nothing run-level. |
| `pumllint score examples/ -f json` | Root keys `diagrams`, `modelSet`, `syntaxGateRan`. No version, configuration or digest. |
| `trace.schema.json` (root properties) | `requirements`, `unknownReferences`, `unlinkedDiagrams`, the feature-side lists, `summary`. Same. |
| `pumllint examples/ -f sonar` | `rules[].engineId` is `"pumllint"`, with no version. The shape is SonarQube's contract. |
| `pumllint score examples/ -f badge` | `"schemaVersion": 1`, which is **shields.io's endpoint-format version, not provenance**. |
| `pumllint score examples/ -f html` | `<footer>generated by pumllint 0.33.0</footer>`, the only self-description any report carries. |
| `aris2puml … --report sidecar.json` | `"version": 1`, `"tool": "aris2puml 0.1.0"`, and each record's `input` and `output` paths. No digest. |

The separation the synthesis asks for — identifier, version, location and
content hash kept apart — is practised wherever this project *measures*:

- The measurement-wave drivers record sha256 digests of the frozen kit and
  of themselves in their run records (`tools/stack_ablation.py`;
  `tools/stack_w1b.py`'s `driver_sha256_at_check` and
  `stack_ablation_sha256`; `tools/stack_w3b.py`'s `cell_prompt_sha256`;
  `tools/agentic_codegen.py`).
- aris2puml pins `SAPModels.epml` by `EPML_SHA256` in
  `tools/corpus/fetch_sap.py`, checked by `--verify` and quoted in its
  corpus README.

It is absent from what the chain *ships*. A path names a location, and the
same path holds different bytes from one commit to the next. In PROV-O's
terms, the sidecar records an activity (the conversion run), the entity it
*used* (the export), the entities *generated by* it (the diagrams) and the
agent it *was associated with* (the tool, named with its version). The
entities, though, are named by location only. A pumllint report is a
validation result that names neither the rule set it applied nor the bytes
it judged.

Design constraints, recorded so a build does not re-derive them:

1. **The lint report has no root, and no other report stands in for
   it.** It is a bare array. The run-level facts — version, configuration
   identity — have nowhere to go but onto every finding, which is the shape
   rejected for `syntaxGateRan` ("a per-diagram key would repeat one fact
   N times", #30's record); turning the array into an object breaks a
   pinned report shape. A digest per finding is a different case — a
   per-file fact, not a run-level one — but alone it names neither the
   version nor the rule set. The lint report stays as it is.
   - A score or trace report does **not** carry provenance for lint
     findings. `pumllint <paths>`, `pumllint score` and `pumllint trace`
     are separate invocations, free to differ in their paths, in `-c` —
     without it each discovers its configuration from its own working
     directory (`load_config`) — and in time, and lint and score also in
     `--profile` and `--no-suppressions`, which `trace` does not take.
     There is no "same run" to borrow from. Nor does the score report carry
     the findings themselves: its gap report holds "the minimal blocking
     set to reach `level + 1`" (`build_gap_report`), not every finding.
   - So this candidate leaves the lint report's findings — and the sonar
     report's, the outputs most consumers ingest — without provenance, and
     nothing recorded closes that. The 2026-08-10 portable run-record
     candidate is not the route: it is a format for adopter generation
     runs, "a pilot-repo artifact" gated on a real pilot stabilizing one,
     with "nothing … built here before then"
     (docs/sdd-manifest-evaluation.md, *Recorded, not queued*, item 1).
     When the trigger below fires on lint findings, how they get provenance
     is an open design question for that build, put to the owner, not
     settled here.
2. **Score and trace: run-level facts at the root, digests per input.**
   Both are inside owner decision §6.5's yes ("an additive field in an
   existing pinned shape is inside the yes").
   - **Run-level facts** — the version and an identity of the effective
     configuration (constraint 5) — are one fact per run: additive root
     keys. `syntaxGateRan` is the precedent, and its route is the
     announcement — README § Report schemas, the schema's own
     description, and this file.
   - **Input digests** are one fact per input file, so the precedent does
     not cover them, and a root map keyed by path would duplicate the paths
     the report's items already carry. Where each sits is the Arc E item's
     to say; the reasoning behind it: a digest belongs beside a path the
     report already names once per diagram, so a file holding several
     diagrams repeats its digest, the same bytes named twice and not a run
     fact named N times; and where no item names a file once — on trace,
     where a diagram appears on as many sites as it has citations and the
     inventory on none, and for a score input with no `diagrams[]` item — a
     root list of `{file, digest}` is a root key that is still the per-file
     fact, listed once, not a run-level fact on the `syntaxGateRan`
     precedent.
   - Every schema involved closes its objects (`additionalProperties:
     false`), so a strict validator holding an older schema rejects the
     new keys; README already says so.
3. **A version in the report changes its bytes every release.** This is
   already accepted for the HTML report: the published example carries
   `0.33.0`, and `tests/test_pilot_example.py`'s byte comparison forces a
   regeneration per release.
4. **Digest the decoded text with LF line endings, not the bytes.** The
   definition, to the byte:
   - decode as `read_text_and_encoding` does: a UTF-8, UTF-16 or UTF-32
     byte-order mark selects the codec and is dropped; otherwise strict
     UTF-8;
   - replace every CRLF, then every remaining lone CR, with LF;
   - change nothing else — no Unicode normalisation, no trimming, no final
     newline added or removed;
   - encode the result as UTF-8 without a byte-order mark, and take its
     SHA-256, as lowercase hex.

   The build pins it with the same test vectors in both repositories — at
   least a UTF-16 file with a BOM, a UTF-8 file with a BOM, a CRLF file
   and a lone-CR file, each equal to its plain-UTF-8, LF twin. Why not the
   bytes:
   - `read_text_and_encoding` reads bytes and decodes them without newline
     translation, with the codec a UTF-8, UTF-16 or UTF-32 byte-order mark
     selects (`_BOMS` in `pumllint/textio.py`), which drops the mark.
   - Git for Windows checks text out as CRLF by default, which is why this
     repository's `.gitattributes` pins `eol=lf`: without it, its own
     comment says, the pilot artefacts' byte comparison fails on a Windows
     checkout.
   - A raw-byte digest would therefore make one commit's report differ
     between Windows and POSIX, against the byte-identical-report contract
     that forward-slash paths exist to keep.
5. **Configuration identity means the effective configuration**, not the
   configuration file's bytes, since two files can state one rule set.
   What it covers on each command is open (constraint 7).
6. **Use one digest definition in both tools.** aris2puml writes diagrams as
   UTF-8 with `newline="\n"` (`aris2puml/cli.py:142`). It computes the
   digest under constraint 4 on the text it is about to write, not on
   bytes re-read, so its output digest and pumllint's input digest of the
   same diagram are equal by construction, and the shared test vectors
   keep them so. The two records then join on content, not on paths that
   differ between machines and invocations (the sidecar's `output` is
   whatever `-o` was given, absolute or relative).
7. **Open for the build, decided when the trigger fires.** The evidence is
   recorded so the build does not re-derive it; none of it is design.
   - *What the configuration identity covers.* Score builds an engine from
     the rules, the active profile with its `profiles:` definition (enable
     lists, escalations) and the top-level `suppressions` key; it reads the
     `scoring` section through `ScoringConfig.from_dict`, except
     `syntax_gate` and `syntax_command` — the PlantUML command the gate
     runs — which `_run_score` reads itself; `--profile`,
     `--no-suppressions` (configuration twin: `suppressions`) and
     `--check-syntax` (configuration twin: `scoring.syntax_gate`) change
     what it reports. Trace applies no profile and builds no engine: its
     whole configuration is the requirement-ID pattern — `--pattern`, else
     the `pattern` of the configuration's `rules.GEN007` entry, or of
     `rules.requirement-link` when there is no `GEN007` entry at all
     (`pattern_from_config`). Like the engine's `_rule_entry`, it lets any
     `GEN007` entry shadow the other, even one without a pattern. Unlike
     the engine (`_rule_entry`, `_rule_config`), which the lint and score
     paths use, it matches the two keys exactly, where the engine also
     accepts a case variant (`gen007`), and it does not read `enabled`, so
     a table with `enabled = false`, which turns GEN007 off in lint and
     score, still gives trace its pattern. Its docstring's "a disabled rule
     … yields None" holds only for the non-table forms (`false`, `off`,
     `disabled`).
   - *Which files the root list holds.* Candidates: trace's diagrams, its
     inventory sources (the `--requirements` file and every file
     `--requirements-scan` read, whichever were given) and its feature
     files; score's `--baseline FILE`, from which the report's `baseline`
     values come, which `_run_score` reads whenever the file exists — with
     or without `--update-baseline`, before any rewrite — and not when it
     does not exist yet, the run then creating it; and collected files that
     yield no diagram (no `@startuml` block, an `.iuml` fragment), which
     pumllint reads, which the syntax gate hands to PlantUML like every
     collected file (`check_files`), and which may also be another
     diagram's `!include` target.
   - *Trace's lenient readers.* Trace's diagrams and its `--requirements`
     inventory go through `read_text_file`; it reads its
     `--requirements-scan` and `--features` files with
     `read_text(encoding="utf-8", errors="replace")` (`scan_inventory` and
     `scan_features` in `trace.py`), honouring no byte-order mark and
     failing on nothing. The ASCII text of a UTF-16LE feature file then
     reads as its characters with a NUL between each: a multi-character ID
     pattern such as `REQ-\d+` matches nothing in it, a one-character
     pattern can match stray letters (its file name, matched separately,
     still matches as usual), while constraint 4's digest would hash the
     decoded text; and for a file with no byte-order mark that is not valid
     UTF-8 that digest cannot be computed at all. Moving those readers onto
     `read_text_file` is a behaviour change: an undecodable file becomes an
     error instead of being scanned.
   - *What the syntax gate depends on beyond the file.* With the gate on
     (`syntaxGateRan` true), DIM-SYN is decided by the PlantUML engine
     `scoring.syntax_command` names: its version, its environment (its
     default charset, for one) and the targets of a diagram's `!include`s,
     which pumllint's parser records but never expands (`parse_source` in
     `parser/sequence.py`).

**Recorded as** pumllint Arc E, *Run provenance in the score and trace
reports*, plus the converter half as aris2puml D4(b).

*Trigger, shared by both halves:* an adopter retaining the chain's reports
as audit evidence, or a consumer — an evidence store, a knowledge graph —
ingesting them, who must say which version, configuration and input
produced a finding. When it fires, both halves land in one cross-repository
change, pumllint first (the landing order), with one digest definition.

## 5. Gap 2 — element identity stops at the emitter

Walked through one fixture, aris2puml's golden
(`tests/fixtures/order_to_cash.json` → `tests/expected/order-to-cash.puml`):

1. **ARIS.** An object *definition* (the entity) has *occurrences* in
   models (its appearances), which is the synthesis's §2.1 distinction,
   native to ARIS. The report script writes node ids as
   `<definition GUID>#<occurrence index>` (`aris/export_epc.js:21-23`), so
   it keeps both halves. The script is unrun (A1b).
2. **JSON.** 18 nodes and 4 lanes, each with an id.
3. **Structuring pass and sidecar.** The ids survive: `StructureError.nodes`
   for `--diagnose`, and `node` on every approximated, dropped and flagged
   note.
4. **Emitter.** The golden diagram carries two ids, both process ids: its
   own (`ARIS process PROC-0042`, in the footer) and its interface target's
   (`PROC-0051`, in the footer and in the `' aris: interface` comment).
   None of the 22 element ids reaches it.
5. **pumllint.** A finding is `{file, line, message, ruleId, severity}`, and
   the element's only identity in it is its label, quoted in the message.
   In `docs/process-demo/order_to_cash_draft.puml` that is ACT006 on line
   10, "Activity 'Order intake' is not verb-first". Process-level findings
   sit on line 1 (GEN006, GEN007).
6. **Across diagrams.** XD joins on name equality. Participants join by
   alias — the probe in §9 draws zero XD findings for
   `participant "Order Service" as OS <<svc>>` against
   `database "Order Service" as OrderService <<store>>`, and XD001 plus
   XD002 at both sites once the alias matches. Swimlanes join by name
   (XD004 only; XD005 never sees a lane). For a converted process the
   lane is an ARIS org unit, itself an object definition whose GUID the
   join never sees.

So the chain carries the entity/occurrence distinction from ARIS as far as
the sidecar, and drops it at the one boundary a finding crosses. The way
back is a name lookup — the synthesis's "merge on similar names", done by a
human with the diagram open.

Three carriers are possible, and two are wrong:

- **A footer, header, title or caption** holds one value per diagram, so
  it cannot say which line an id belongs to. **A note per node** can, but
  notes are scored — GEN008 counts them, which is why aris2puml's
  `--notes` is off by default — and every one of these is in the GEN007
  and `trace` carrier set, scanned with the requirement pattern. Refused.
- **A comment per node** (the `' aris:` form). Invisible to every rule —
  docs/business-processes.md §2's interface row says so — so no finding
  carries it, and a consumer would still read the diagram's text. It also
  moves the golden and pumllint's demo together — the demo
  (`docs/process-demo/order_to_cash.puml`, 40 lines) is the golden's 34
  lines plus a six-line comment header (lines 2–7), so its lines sit six
  below the golden's — and is therefore a change in both repositories.
  B4 (2026-09-06) met this exact wall for interface targets and added a
  footer copy beside the comment. That is right for one process id per
  diagram and impossible for one id per line. Expensive, for nothing a
  rule can use.
- **A line → ids map in the sidecar**, per converted record:
  - aris2puml's alone, and an additive key inside version 1, as `flagged`
    and `interfaces` were (both 2026-09-06);
  - read-only: nothing is written to ARIS, so the "no round-trip" Never
    stands;
  - multi-valued by necessity: line 10 of the golden (line 16 of
    pumllint's demo), `if (Order valid?) then (Order valid)`, carries
    the XOR split `x1` and its first outcome's event `e1`; lane lines
    carry org-unit ids; and a process-level finding maps to the process
    id the record already holds;
  - joined on `(file, line)`; path-independently, once gap 1 is built, only
    where the report carries the file's digest: lint-report findings
    excepted (Arc E item, *Not covered*), item 5's among them.

  The cheapest correct carrier.

This is a second concrete instance of the knowledge-graph note's G1
(cross-repository identity), after sequence↔contract, and the first one
measured — on the chain's own golden fixture. Like sequence↔contract, it is a
file-to-file join, not a store. It joins the "cross-artifact identity"
family as its fourth member, after sequence↔contract, the
glossary/approved-term rule and model→spec change-impact.

**Recorded as** aris2puml D4(a). pumllint has nothing to build.

*Trigger:* an adopter routing pumllint findings back to the ARIS objects or
their owners. The A1b adopter becomes one once the chain runs in its CI, so
this trigger sits downstream of the critical path, not on it.

## 6. The first experiment, against what runs today

**The chain's half ran on 2026-09-14** (the EA record). Five processes went
through `aris2puml … --report --manifest`, `pumllint -c conventions.toml`,
`score` and `trace --requirements manifest.json --fail-on-unknown-ref`:

- 3 converted and 2 refused, with the connector named;
- 39 issues;
- Level 3, 88.3/100;
- 1 of 3 covered, 1 unknown reference, 2 unlinked diagrams.

Architecture and API specifications have no reader in either repository.
Tests enter only as Gherkin references (`--features`).

**Q1 — which implementations and tests does a changed requirement
affect?** `trace` answers the current-state half without a graph:
`coveredBy` and `verifiedBy` for that ID. The change half is the
model→spec change-impact design (2026-08-10), gated on a real
diagram-edit event flowing through a pilot pipeline.

**Q2 — which process tasks lack an implementing service or operation?**
At requirement granularity, `trace`'s uncovered direction is the decidable
form, because the inventory is the oracle. At task granularity it needs
two things:

- a declared obligation per task — without one it is N4's missing-edge
  inference;
- a carrier for task-level ids, which is gate (1) of Arc G's step-to-model
  item: model content as a trace carrier, an owner decision.

**Q3 — what exact source version and transformation justify each
relationship?** The sidecar is the transformation and the report the
validation. Gap 1 is the missing version half; gap 2 the missing element
half.

The synthesis's acceptance evidence, item by item:

- **Repeatable ingestion without accidental duplication: ships.**
  aris2puml gives deterministic output names, appends the process id to a
  shared name, and reads every input before writing; pumllint's XD rules
  are permutation-invariant (`tests/test_crossfile.py`).
- **Explicit reporting of uncertain mappings: ships** (`approximated`,
  `--strict`).
- **A controlled source change that preserves historical evidence: half.**
  The baseline ratchet keeps one level per diagram and leaves history to
  git. With gap 1's Arc E half built, a retained score or trace JSON report
  would also say what it judged, within what §4 leaves open (constraint 7);
  other reports would not (Arc E item, *Not covered*).

## 7. DOIs

Nothing to build. DataCite's best-practice page:

> "DOIs must resolve to a publicly available landing page. … The
> underlying content does not need to be publicly available, but the
> metadata must be open."

For an adopter whose processes cannot be committed in any form (aris2puml
A1, 2026-09-06), open metadata is already too much. A DOI never fits an
adopter's models or reports.

For this repository, releases are already published on GitHub (the newest,
v0.33.0, on 2026-09-06). A citable release DOI would need only
the owner's archive integration — Zenodo's GitHub integration mints one per
published release (characterized, not executed) — and optionally a
`CITATION.cff`, which neither repository has. That is the owner's decision,
with no trigger. A hosted session cannot publish a release (aris2puml
CLAUDE.md, 2026-09-07).

The synthesis's separation of identifier, version, location and hash is
already practised where this project measures (§4).

## 8. Decision, recorded candidates, triggers

**Decision: nothing queued.** Two candidates are recorded, both gated:

1. **pumllint, Arc E — run provenance in the score and trace reports:**
   designed in §4 (constraints 1–6, with the open questions in 7) and
   specified in the ROADMAP's Arc E item, which this section does not
   restate; what it leaves out is the item's *Not covered*. *Trigger*: §4.
2. **aris2puml, D4 — the sidecar as an evidence record**, two independent
   additive keys:
   - (a) the line → ids map (gap 2; *trigger*: §5);
   - (b) input and output digests under pumllint's definition (gap 1's
     converter half; *trigger*: §4).

**Annotated in place, as pointers:**

- the knowledge-graph note's bounds (w3.org read);
- the Linked.Archi note's "binary by the specification" (confirmed at the
  primary);
- the ROADMAP's *Recommended next* bullet, whose inventory of open work
  had named neither Arc G's step-to-model item (2026-09-09) nor the new
  Arc E item;
- the knowledge-graph settlement's re-litigation line (touched, not fired);
- aris2puml's "no round-trip" Never (touched, not fired, again).

**Priorities unchanged.** The critical path stays aris2puml A1b → A4.
Open checkboxes go from 16 to 17 here and from 7 to 8 in aris2puml, all
gated.

**Re-litigate on** the candidates' triggers, or the knowledge-graph
settlement's four, unchanged. Not on the existence of this synthesis or of
the next one.

## 9. Reproduction

```bash
# pumllint, at 558d762
python -m pumllint examples/ -f json -o lint.json            # array of findings
python -m pumllint examples/ -f sonar -o sonar.json          # rules[].engineId
python -m pumllint score examples/ -f json -o score.json     # root keys
python -m pumllint score examples/ -f badge -o badge.json    # schemaVersion 1
grep -n "generated by" docs/example-maturity-report.html     # the version footer
python -m pumllint docs/process-demo/order_to_cash_draft.puml \
    -c docs/process-demo/conventions.toml -f json            # (file, line), label in message

# the alias-join probe: a.puml and b.puml share a display name, a.puml and c.puml an alias
#   a.puml: participant "Order Service" as OS <<svc>>             + Client -> OS : place()
#   b.puml: database "Order Service" as OrderService <<store>>    + Client -> OrderService : place()
#   c.puml: database "Order Service" as OS <<store>>              + Client -> OS : place()
python -m pumllint a.puml b.puml -f json    # no XD finding
python -m pumllint a.puml c.puml -f json    # XD001, XD002 at both sites

# aris2puml, at f725b59
aris2puml tests/fixtures/order_to_cash.json -o out --report sidecar.json --manifest manifest.json
grep -c "" tests/expected/order-to-cash.puml                 # 34 lines, two ids, both process ids

# pumllint again: the demo is the golden plus a comment header
grep -c "" docs/process-demo/order_to_cash.puml              # 40 lines: header at 2–7, golden line 10 is 16

# the second correction (2026-10-16), against pumllint's code at 64007cb
python -m pumllint trace --profile codegen examples/ 2>&1 | tail -1  # unrecognized arguments: --profile
grep -n 'errors="replace"' pumllint/trace.py                 # in scan_inventory and scan_features
grep -n 'scoring_cfg.get("syntax_gate")' pumllint/cli.py    # in _run_score: the gate runs on config too
grep -n "def pattern_from_config" -A12 pumllint/trace.py    # trace's configuration: the GEN007 pattern
grep -n "def _rule_entry" -A18 pumllint/engine.py           # the engine's key matching, case variants included
grep -n "def _rule_config" -A22 pumllint/engine.py          # enabled = false disables; false/off/disabled too
grep -n "Path(args.baseline).exists()" pumllint/cli.py      # in _run_score: the baseline is read when it exists
grep -n "for f in files" pumllint/syntax.py                 # check_files: PlantUML on every collected file
grep -n "read_text_file" pumllint/trace.py pumllint/parser/sequence.py  # strict readers
grep -n "def from_dict" -A30 pumllint/scoring.py            # ScoringConfig reads the scoring section
grep -c "syntax_gate\|syntax_command" pumllint/scoring.py    # 0: from_dict reads neither
grep -n "PUML_EXTENSIONS = " pumllint/engine.py             # .iuml is collected
grep -n "def load_config" -A6 pumllint/config.py            # without -c, discovered from the working directory
grep -n "never expanded" pumllint/parser/sequence.py         # !include recorded, not expanded
grep -n "minimal blocking set" pumllint/scoring.py           # the gap report is not every finding
```

## Related reading

- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md):
  N1–N5, G1–G4, the four triggers.
- [Linked.Archi and pumllint](linked-archi-evaluation.md): binary
  conformance, the tolerant projection observed a second time.
- [Cross-diagram relationships in pumllint](cross-diagram-relationships-evaluation.md):
  the alias join key, untyped `trace` links, G2 and G6/O4.
- [The ontology/graph EA stack, evaluated](ea-ontology-stack-evaluation.md):
  Loop C, the 2026-09-14 end-to-end run.
- [The SDD + generation-manifest recommendation, evaluated](sdd-manifest-evaluation.md):
  the portable run-record candidate.
- [Linting business processes](business-processes.md) §2 and §7: the
  mapping table and the chain.
- aris2puml's README, *What was lost: the fidelity sidecar*, and its
  ROADMAP, D4.
