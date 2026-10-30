# A git structure for IEAM artefacts, per taxonomy

> **Status: a proposal, nothing built (2026-10-30).** Written on the maintainer's ask by a
> sub-agent of the demo session, from this repository's settlements and the IEAM proposed
> approach of 30 October 2026 (an enterprise document, not reproduced here). The companion
> opportunity canvas and SWOT is a private page of the maintainer's account
> (https://claude.ai/artifact/UKEJaGcJcGq7mD2yXwynh9); this file is the record, the page a view.
> The repository it proposes, `ieam-register`, does not exist yet; nothing in pumllint changes.
>
> **Two instances, one structure (maintainer's clarification, 2026-10-30).** The GitHub
> `ieam-register` is a public test case: the structure, the metamodel, the checker and the CI,
> populated only with synthetic content (the CargoQuote kit under `kg_experiment/` is the
> natural pilot slice: requirements, a decision table, a specification, an API contract,
> BPMN, DMN, Gherkin and `links.toml` already exist for it). No bank-related data may be stored
> outside the bank's private repositories, so the bank's instance is created from the test case
> inside those repositories and is never pushed outside them. Where this document says "the
> bank's" of a node, an export or an owner, read it of that private instance.

*Evaluation and proposal, 2026-10-30. Written against pumllint at the current checkout (README,
CLAUDE.md, docs/business-processes.md, kg_experiment/, recreate_experiment/, ROADMAP entries of
2026-08-26, 2026-09-06, 2026-09-14, 2026-10-16, 2026-10-29 and 2026-10-30) and the IEAM proposal
of 30 October 2026. Maintainer register. Nothing here is product code; every build item named is
a stdlib script in the new repository or lab machinery.*

## 1. Evaluation of the request

**The request as stated is ambiguous in two places, and the second matters more than the
first.**

"Per taxonomy layer" can mean (i) one repository per taxonomy, (ii) one directory per taxonomy,
or (iii) one directory per level inside each taxonomy. Reading (ii) is right: the IEAM says the
levels are "illustrative conventions, not mandatory", each domain "has its own depth", and
relationships cross taxonomies, so a per-repository split (i) puts the relationship registry and
its dangling-link check across repository boundaries for no gain, and a per-level split (iii)
freezes the levels the IEAM refuses to fix and makes every re-parenting a file move that breaks
history and references. Hierarchy belongs in the data (a `parent` field), not in the path; the
ROADMAP already refuses "hierarchy inferred from filenames or folders" (2026-08-27, ArchiMate
note, never-build) for the same reason.

"Store and version the artefacts" is the larger ambiguity. The IEAM makes ARIS the governed
authoring repository for processes, journeys, products and operational publication, Archi the
author of capability and application views, and the EDM repository the author of detailed data.
Git cannot be a second author of any of that without becoming the second source of truth the
IEAM's "one authoritative record per concept" forbids. Four classes of artefact, with different
answers:

| class | examples | git is | rule |
|---|---|---|---|
| (a) authored sources in a tool | ARIS database content, the Archi `.archimate` model, the EDM repository | **not the record**; a reference by stable external id | never retyped into git; `[source]` block names the system of record and its id |
| (b) exports and projections | ArchiMate exchange XML, ARIS XML/AML report output, the aris2puml JSON contract, `.puml` emitted from it, Archi CSV | **a dated mirror with provenance** | immutable once committed; digest, export date, source version, tool version; a later export is a new folder, never an overwrite |
| (c) hand-authored plain-text records | metamodel, glossary, mapping specification, relationship registry (types and instances ARIS cannot carry), identities, decision records, exceptions, owners | **authoritative** | these are what the request should mean by "store and version"; reviewed by PR, approved by a recorded file-state change |
| (d) derived and analysis outputs | reconciliation reports, coverage reports, impact answers, a Neo4j projection | **a dated result, never the record** | written under a dated folder as `kg_experiment/results/demo-runs/<date-time>/` is; the projection is never committed, it is rebuilt from a tag |

The structure prevents the second source of truth by construction: a node file holds the
register's own id, lifecycle, owner and links, plus a pointer to the external record; it never
holds a copy of the external record's attributes beyond `name` (needed for review) and that
`name` is checked against the latest export, not authored. This is the rule the kg demo already
states for its store ("authoritative for status, provenance and links, never for content",
`kg_experiment/demo/README.md`) and the glossary's rule 4 (rewording quoted data "would make it
a second source"). The register is the **identity and relationship spine**; the tools stay the
authors of content.

What git alone delivers: one reviewable, diffable history of the mapping between the tools, with
the approval, rationale and review date the IEAM wants on every relationship, and a CI that
refuses a merge on a dangling link. That is the deliverable.

## 2. Proposed layout

### 2.1 One repository, `ieam-register`

```
ieam-register/
├── README.md                      # adopter register: what this is, how to add a node, how approval works
├── METAMODEL.md                   # the design contract in prose; maintainer register
├── metamodel/
│   ├── types.toml                 # the six node kinds, their id prefixes, allowed parent kind, required fields
│   ├── lifecycle.toml             # states, allowed transitions, who may move, review cadence per kind
│   └── sources.toml               # the external systems (aris, archi, edm) and field-level authority
├── glossary/
│   └── glossary.toml              # one approved term per concept, forbidden synonyms, owner, since
├── capabilities/   CAP-0001.toml …
├── products/       PRD-0001.toml …
├── journeys/       JRN-0001.toml …        # journeys, stages, steps and touchpoints are all JRN nodes; kind field distinguishes
├── processes/      PROC-0001.toml …       # PROC- to match the footer convention aris2puml already emits
├── applications/   APP-0001.toml …
├── information/    ENT-0001.toml …
├── organisation/   ORG-0001.toml …        # business units; ownership is a relationship, never a parent
├── relationships/
│   ├── requires.toml              # product → capability
│   ├── concerns.toml              # journey → product
│   ├── is_supported_by.toml       # journey step/touchpoint → process/activity
│   ├── realizes.toml              # process → capability
│   ├── delivers.toml              # process → product
│   ├── supports.toml              # application/module → process/activity
│   ├── crud.toml                  # process/activity → information entity, with mode
│   ├── manages.toml               # application/module → information entity
│   ├── owns.toml                  # organisation → any node (the separate organisational relationship)
│   └── maps_to.toml               # logical entity → physical asset (realisation, not containment)
├── mapping/
│   └── matrix.toml                # the tested ARIS/Archi mapping matrix: per node kind and relationship type, status and evidence
├── decisions/      0001-….md …    # ADR-style records, one per decision; numbered, never edited after approval, superseded by a new one
├── exceptions/     EXC-0001.toml …# approved deviations from a coverage rule; scope, rationale, approver, expiry
├── exports/
│   ├── aris/<YYYY-MM-DD>/         # MANIFEST.toml + the report-script output (JSON contract, AML/XML) + RECONCILE.json
│   ├── archi/<YYYY-MM-DD>/        # MANIFEST.toml + model.archimate + exchange .xml + RECONCILE.json
│   └── edm/<YYYY-MM-DD>/          # MANIFEST.toml + the EDM's own export + RECONCILE.json
├── reports/<YYYY-MM-DD>/          # coverage, impact and reconciliation summaries at a tag; dated, committed with the tag only
├── tools/                         # stdlib Python: check_register.py, reconcile.py, impact.py, inventory.py
└── .github/workflows/ci.yml       # runs tools/check_register.py and, on a tag, writes reports/<date>/
```

Why one directory per taxonomy, hierarchy in data: the six taxonomies have different depths and
decomposition rules (IEAM §"Six linked architecture taxonomies"); journey sequence is not
containment and touchpoints are reused across steps, which a folder tree cannot express at all;
re-parenting a node is a one-line change in the file instead of a `git mv` that orphans every
path reference; CODEOWNERS maps one directory to one domain steward, which is exactly the IEAM's
steward per domain. Alternative shown for completeness: one repository per taxonomy gives each
steward a repository, but puts every cross-domain relationship in a seventh repository that must
check links into six others, and the IEAM's whole point is the cross-domain relationships.

Why TOML: the house format for exactly this (`kg_experiment/kit/links.toml`,
`verification_map.toml`, `pumllint/rules/catalog.toml`, `pumllint.toml`); read by `tomllib` in
the standard library since Python 3.11, so the CI check keeps the zero-dependency promise; typed
scalars with no YAML implicit-type surprises (`on = 2026-11-05` is a date, `NO` is a string);
array-of-tables reads naturally for relationship instances. Cost: no anchors, no multi-document
files; neither is wanted.

Why one file per node: blame and PR review per record, CODEOWNERS per directory, no merge
conflicts between stewards, findings that name a file. Cost: thousands of files for a full
process taxonomy; the pilot is dozens. Shard by id range (`processes/PROC-01xx/`) if needed,
never by hierarchy.

### 2.2 Identity scheme

- Register ids: `<PREFIX>-<4+ digits>`, minted by the register, never reused, never encoding
  hierarchy or organisation. Prefixes: `CAP`, `PRD`, `JRN`, `PROC`, `APP`, `ENT`, `ORG`, `EXC`,
  `REL` (relationship instance id, for approval records). `PROC-nnnn` and `CAP-nnnn` are already
  the carrier convention `pumllint trace` and aris2puml's footer use (docs/business-processes.md
  §2 and §7; ROADMAP 2026-10-29), so the register's ids ride the existing diagram footer
  unchanged.
- External ids live under `[source]`: `aris_guid` (the definition GUID; an occurrence is
  `<guid>#<index>`, the shape aris2puml's report script keeps, ROADMAP 2026-10-12 Gap 2),
  `archi_id` (the element `id` in the `.archimate` file, which the exchange format preserves),
  `edm_id` (the EDM repository's own key, format unverified). `metamodel/sources.toml` says, per
  node kind and field, which system is authoritative; the register's `name` is checked against
  it, not authored.
- One concept, one register id, one authoritative external record. A node may carry more than
  one external id (an application in ARIS and in Archi) only when `sources.toml` names which
  fields each owns; the reconciliation reports a disagreement between them as a gap.

### 2.3 Example files

`capabilities/CAP-0012.toml`

```toml
id = "CAP-0012"
kind = "capability"            # capability_domain | capability | sub_capability (illustrative, from types.toml)
name = "Assess credit risk"
parent = "CAP-0003"            # same taxonomy, must exist, acyclic
state = "approved"             # from metamodel/lifecycle.toml
owner = "ORG-0007"             # steward's unit; not a parent
review_due = 2027-04-30

[source]
system = "archi"               # Archi authors capabilities (IEAM Appendix A)
archi_id = "id-7c1e3a…"
model = "exports/archi/2026-10-28"
aris_guid = "c1f9…-…"          # the ARIS Capability Map occurrence, reference only

[approval]
by = "jdoe"
on = 2026-10-28
record = "decisions/0004-credit-capability-split.md"
```

`relationships/realizes.toml` (type header, then instances)

```toml
[type]
name = "realizes"
source_kind = ["process", "subprocess"]
target_kind = ["capability", "sub_capability"]
direction = "source_to_target"
inverse_label = "is realized by"
owner = "ORG-0002"                       # relationship owner (IEAM governance)
evidence_class = "authored"              # authored | exported | derived
aris_status = "unverified"               # unverified | native_tested | configuration_required | extension_required | unsupported
archi_status = "unverified"              # ArchiMate realization per Appendix A, untested in the target installation
note = "Not a verified ARIS connection name; status moves only with a tested row in mapping/matrix.toml"

[type.cardinality]                       # per lifecycle state of the SOURCE node
draft    = { min_targets = 0, max_targets = "n" }
approved = { min_targets = 1, max_targets = "n" }
deprecated = { min_targets = 0, max_targets = "n" }

[[link]]
id = "REL-00031"
source = "PROC-0042"
target = "CAP-0012"
state = "approved"
rationale = "Credit check function block in PROC-0042 is the only operationalisation of CAP-0012"
owner = "ORG-0002"
review_due = 2027-04-30
evidence = ["exports/aris/2026-10-28/epc/PROC-0042.json", "decisions/0004-credit-capability-split.md"]
approval = { by = "jdoe", on = 2026-10-28, record = "decisions/0004-credit-capability-split.md" }
```

`relationships/crud.toml` adds `mode = ["C","R","U"]` per link. `relationships/maps_to.toml`
targets a physical asset by `edm_id` with no register node, because the EDM is the record for
physical assets.

`exceptions/EXC-0003.toml`: `id`, `rule = "C1"`, `scope = ["JRN-0105"]`, `rationale`, `approved
= { by, on, record }`, `expires`; an expired exception stops excusing.

`exports/aris/2026-10-28/MANIFEST.toml`: `exported_on`, `source`, `source_version` (whatever the
installation exposes; unverified), `tool` and `tool_version`, `previous` (the prior export
folder), and a `[files]` table of sha256 per file.

`glossary/glossary.toml` follows `kg_experiment/demo/GLOSSARY.md`: one `[[term]]` per concept
with `term`, `meaning`, `forbidden = [...]`, `owner`, `since`; the check refuses a forbidden
synonym in any `name`, `rationale` or decision record, as
`recreate_experiment/harness/glossary_check.py` does for the kit.

`metamodel/types.toml` is the metamodel definition the IEAM says to start with: node kinds,
prefix, allowed `parent` kinds, required fields. `mapping/matrix.toml` is the "tested mapping
matrix" of IEAM step 1: one table per node kind and relationship type with `aris_model_type`,
`aris_connection`, `archi_element`, `archi_relationship`, `status` (the four IEAM values),
`tested_on`, `evidence`. Until a row is tested its `status` is `"unverified"`, a fifth value the
IEAM does not list and the register needs so an untested row cannot pass as native.

Exports and derived outputs never land on an authored record: `exports/` and `reports/` are
dated folders, append-only, as `kg_experiment/results/` versus `results/demo-runs/<date-time>/`
is here.

## 3. Versioning rules

- **A commit** changes authored records (class c) or adds a dated export or report folder (b,
  d); it never mixes the two. Commit message names the ids touched. Branch per change, PR, CI
  green, merge; the merge is the record of *who changed the file*, not of approval.
- **Approval is a file-state change**, not a git feature: `state` moves to `approved` and
  `[approval]` carries `by`, `on`, `record`. CI refuses `state = "approved"` without a complete
  `[approval]`, and refuses an approval whose `by` equals the PR author when the lifecycle says
  so (`lifecycle.toml`, `four_eyes = true` per kind). Material cross-domain links need both
  owners: `approval` becomes an array of two tables, one per side, checked against `owner` of
  source and target. A git signature or a review approval is corroboration, never the record.
- **Lifecycle** states per `lifecycle.toml`: `draft → proposed → approved → deprecated →
  retired`, plus `rejected` from `proposed`. Transitions are explicit; CI diffs the previous
  commit's state and refuses a skipped one. `review_due` is required on `approved`; an overdue
  date is a warning in the report, a failure only when `lifecycle.toml` says so for that kind.
- **A change to a node propagates to nothing automatically.** Rename of `name`: allowed, links
  reference ids. Re-parent: allowed, cycle check runs. State to `deprecated` or `retired`: CI
  lists every `approved` link that references it as a finding, and refuses the merge until each
  link is deprecated, re-pointed or excepted; no auto-fix (the house rule since `trace`: report,
  never invent).
- **Tags** are cut on the register, not on exports: `v<major>.<minor>.<patch>` where major = a
  `metamodel/` change that alters a type, a prefix or a required field; minor = an approved
  content baseline (a pilot slice complete, a review cycle closed); patch = corrections with no
  state change. A tag commit also carries `reports/<date>/` written by CI. Exports carry their
  own date and are never tagged separately.
- **Exports** are versioned by folder: `exports/<system>/<date>/` with `MANIFEST.toml` (export
  timestamp, source version as the installation exposes it, tool and version, `previous`, sha256
  per file). `tools/reconcile.py` reads `previous` and writes `RECONCILE.json` (adds, updates,
  deletes by external id, plus register nodes whose external id no longer appears, which become
  `stale` findings on the node, never deletions). `reconcile.py` is the only code that reads an
  export's content; the register's checks read `RECONCILE.json`.
- **Neo4j projection, if ever built**: reads one tagged commit, loads `metamodel/`, the six
  taxonomies, `relationships/`, `exceptions/` and the exports the tag's manifests name, stamps
  every node and edge with the tag, the commit sha, the export date and the digest, and derived
  edges with their rule. One-way, rebuilt from scratch per tag, never committed. This is the
  IEAM's "one-way publication" with the register as the identity spine between ARIS and the
  graph; it stays Loop C and off pumllint's product path (ROADMAP 2026-08-26 N1, 2026-10-16,
  2026-10-30).

## 4. Validation in CI

`tools/check_register.py`, stdlib only (`tomllib`, `pathlib`, `json`), exit 0/1/2 after
pumllint's contract. What it checks, and what it does not:

| IEAM check | where | how |
|---|---|---|
| allowed types and directions | register | each `[[link]]` source and target kind in the type header's lists; `metamodel/types.toml` for node kinds and parent kinds |
| required metadata | register | required fields per kind and state; `[approval]` complete when `approved` |
| hierarchy cycles | register | DFS over `parent` per taxonomy; journeys additionally check `sequence` edges separately from `parent` |
| duplicate identities | register | id unique across the repository; external id unique per system; `name` unique within a parent (warning) |
| cardinalities | register | per relationship type and source-node state, from `[type.cardinality]` |
| dangling links | register | every `source`, `target`, `parent`, `owner`, `scope`, `record`, `evidence` path resolves; a `maps_to` target checked against the latest EDM export's ids |
| obsolete dependencies | register | approved link to a `deprecated`/`retired` node |
| lifecycle consistency | register | approved link needs approved endpoints; transitions legal against the previous commit |
| coverage rules with exceptions | register | rule table in the script (C1: approved critical `JRN` step has an `is_supported_by` link or an unexpired `EXC`; C2: approved `PRD` has at least one `requires`; C3: approved `CAP` required by an approved product has a `realizes` source); each failure names the rule id so an exception can cite it |
| glossary | register | forbidden synonyms in names and prose; one term per concept |
| staleness against exports | register | `RECONCILE.json` deletes and renames become findings on the node |
| occurrence vs definition, group placement, model attributes, flow inside a process model | ARIS | ARIS semantic checks and the stock profiles (docs/aris-one-standard-semantic-check-evaluation.md); the register only records that they passed, by export date |
| ArchiMate relationship legality | Archi | Archi's own validator on the `.archimate` model; the register's `archi_status` row says the mapping was tested, not that the model is valid |
| structural validity versus business meaning | humans | the approval record; no check |

Where pumllint sits. `pumllint trace <converted-processes>/ --pattern 'CAP-\d+' --requirements
caps.txt --fail-on-uncovered` already answers "which capability ids no process diagram footer
realises" (ROADMAP 2026-10-29, measured); `tools/inventory.py` writes `caps.txt` and `procs.txt`
from the register so the inventory is never hand-typed, and aris2puml's `--manifest` plus `trace
--fail-on-unknown-ref` gives the process-hierarchy check over the converted corpus
(docs/business-processes.md §7). That is diagram-side coverage and stays pumllint's. **Checking
that a footer's `realises CAP-0012` agrees with the capability map** is Loop C (ROADMAP
2026-09-14, 2026-10-16, 2026-10-29: "a second artefact, so Loop C's, never this repository's"),
so it is this register's check: `check_register.py` reads `pumllint trace -f json` (ids are the
join keys, README §Requirement traceability) and reports a footer reference with no approved
`realizes` link, and an approved link whose process has no diagram of record, as register
findings. pumllint builds nothing for it; the typed `realises` relation inside pumllint stays
Arc C's declared-links item with its trigger untouched.

## 5. Repository boundary

**One new repository, `fdurieux/ieam-register`** (or the bank's equivalent, since the content is
the bank's). Not a directory in pumllint: the 2026-08-26 settlement keeps any store, ontology or
enterprise relationship model off pumllint's product path, and the 2026-10-16 and 2026-10-30
entries place "an enterprise graph assembled from other tools' exports" in Loop C outside the
seam; a register of the bank's architecture inside a GPL linter's tree would also mix the public
tool with private content. Not a directory in aris2puml: its scope is one converter emitting
`.puml` with a sidecar (its Never list refuses round trips and ArchiMate front-ends), and the
register spans five domains aris2puml never touches. Both tools consume the register's outputs
(`caps.txt`, the manifest) and feed it (`trace -f json`, the sidecar's line → ids map once D4
ships); neither hosts it.

Pilot slice (IEAM step 2): one product, one journey, their capabilities, the processes that
realise them, the modules that support those, the key entities. Pick the product whose processes
are already in the aris2puml pilot corpus (the five-process run of 2026-09-14), so the ARIS
export route, the converter, `trace` and the register are exercised end to end on content that
exists; expect dozens of nodes, not hundreds.

First decision questions, each mapped to files and checks:

1. *Which customer journeys and products would be affected by retiring module APP-x?* (the
   IEAM's own). `tools/impact.py --from APP-0007` walks `supports.toml` → `PROC` →
   `delivers.toml` → `PRD` and `is_supported_by.toml` ← `JRN`, prints each edge with its state,
   owner and evidence, and stops at a `deprecated` node. Needs `applications/`, `processes/`,
   `products/`, `journeys/`, three relationship files approved for the slice.
2. *Which approved critical journey steps have no supporting process, and which of those are
   excepted?* Coverage rule C1 over `journeys/`, `is_supported_by.toml`, `exceptions/`; the
   answer is CI output, and the exceptions' expiry dates are the review queue.
3. *Which capabilities the product requires have no process realising them, and which realising
   processes have no diagram of record?* `requires.toml` → C3 in the register; then
   `inventory.py` → `pumllint trace --fail-on-uncovered` over the converted corpus; the join on
   `CAP-`/`PROC-` ids is the first measured test of the footer convention against a map.

## 6. Caveats and pushback

Unverified, to test on a small sample before the layout is fixed:

- ARIS export formats and stable ids for all six domains. The EPC report-script route is known
  (aris2puml, unrun in the target installation); capability maps, product trees, journey
  landscapes and the technical-terms model have no tested extraction here. Whether a journey's
  steps and touchpoints survive any export, and keep a GUID across ARIS databases, consolidation
  or re-import, decides whether `JRN` nodes can carry `aris_guid` at all; if not, journeys are
  the one taxonomy the register authors directly, and the IEAM should say so.
- ArchiMate exchange coverage: Capability, Product, Business Service, Application Component and
  Business/Data Object export; customer journeys have no ArchiMate element (Appendix A), so no
  Archi route for `JRN`. Archi ids are stable within one model file; across a model split or
  merge they are not guaranteed.
- EDM identifiers: format, stability and export route unknown; the `maps_to` file assumes an id
  exists.
- ARIS connection names for the eight IEAM relationships: none verified; the `aris_status`
  column starts at `unverified` for every row, and the matrix is the IEAM's step-1 deliverable,
  not this document's.
- Definition versus occurrence: the register points at definitions; occurrence-level links (a
  function in one EPC, not every EPC) need the `#<index>` form and a tested export.
- Volume and authoring friction: TOML by hand suits dozens of nodes and a steward who reviews
  PRs; a thousand-node process taxonomy needs `reconcile.py` to propose node files from the
  export (as drafts, `state = "draft"`, `evidence_class = "exported"`), which is the only
  acceptable automation: generation of drafts, never of approvals.

Pushback on the request:

- "Store and version the artefacts" should not mean copying ARIS or Archi content into git. The
  register stores identities, relationships, approvals and provenance, and mirrors exports with
  digests; the moment a node file carries an attribute the tool owns, there are two records.
- Six taxonomies at once contradicts the IEAM's own step 2. Create the six directories and the
  metamodel on day one; populate one slice.
- The IEAM's Neo4j projection reads ARIS directly. With a register, the projection should read a
  tag of the register and the exports it names, or identity reconciliation is done twice. That
  is a change to the IEAM text worth making before step 4.
- Coverage rules invite the coverage-denominator failure (docs/ea-stack-in-the-sdlc.md): a
  refused or unmodelled process reads as a capability gap. Report coverage with the denominator
  stated and the exceptions counted; never gate the pilot on a percentage.

## Summary

Recommend one new repository, `ieam-register`, with one directory per taxonomy, hierarchy
expressed as a `parent` field in one TOML file per node, a `relationships/` area with one TOML
file per relationship type (type header with kinds, direction, inverse, cardinality per state,
owner, evidence class and ARIS/Archi support status, then `[[link]]` instances with rationale,
owner, review date and a recorded approval), plus `metamodel/`, `glossary/`,
`mapping/matrix.toml`, `decisions/`, `exceptions/`, dated append-only `exports/` with digests
and a reconciliation report, and dated `reports/` written at a tag. Git is authoritative only
for the hand-authored class (identities, links, approvals, glossary, decisions, exceptions) and
mirrors tool exports with provenance; ARIS, Archi and the EDM stay the authors of content.
Approval is a file-state change with approver, date and record; CI is a stdlib checker for
types, cycles, duplicates, cardinalities, dangling links, lifecycle and coverage with
exceptions; footer-versus-map agreement is Loop C and lives here, not in pumllint, whose `trace
--fail-on-uncovered` stays the diagram-side coverage check. Main caveats: no ARIS export or
connection name is verified for any domain, journeys may not survive export at all, EDM ids are
unknown, and the IEAM's direct ARIS-to-Neo4j projection should be redirected to read a register
tag. Start with one product and one journey from the existing aris2puml pilot corpus.
