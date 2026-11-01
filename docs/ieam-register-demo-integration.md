# Integrating "the dashboard" with `ieam-register`: reading, design, canvas, SWOT

> **Status: an investigation, nothing built (2026-10-30).** Written on the maintainer's ask by a
> sub-agent of the demo session, read-only, from the demo under `kg_experiment/demo/` and the
> register at `fdurieux/ieam-register` (commit `abb251c`). It recommends what to build and in
> what order; no code moved. The register's content is synthetic; a bank's instance never reaches
> the public demo. Session-local paths in the text refer to the two checkouts as the sub-agent
> saw them.
>
> *2026-11-01:* the demo moved to `fdurieux/knowgov` (ROADMAP, that date; #263). The
> `kg_experiment/demo/` paths and `kg-demo.yml` below are pumllint's at the time of writing and
> read as knowgov's `demo/` and its `demo.yml` now; the integrations built since are recorded on
> the demo's ROADMAP entry.

*2026-10-30. Maintainer register. Read against pumllint at the current checkout and
`fdurieux/ieam-register` at `abb251c` (two commits, no tag). Nothing built, nothing changed.*

## 0. The reading

**"The dashboard" is read as the kg demo page**: the compose stack under `kg_experiment/demo/`
(`app/server.py`, `app/views.py`, `app/index.html`, `app/cascade.py`, Neo4j 5.26 community),
which shows S1–S7 as a plain-English block, a clickable pipeline strip, a Gaps view, a systemic
drawing with node panels, saved Cypher and three run modes, every generated sentence registered
and held to `GLOSSARY.md` (`views.GLOSSARY`, `views.FORBIDDEN`, 20 words). It is the only
"dashboard" in either repository, it is lab territory (ROADMAP 2026-10-30, "lab, tooling and
docs only"), and it already consumes the CargoQuote kit the register's pilot slice describes
(`exports/kit/2026-10-30/MANIFEST.toml`: the ten documents `kitio.py` ingests, digested at
pumllint `b936587`).

**Second reading, briefly**: a claude.ai Dashboard artifact (hosted charts and tables) over the
register's `reports/<date>/check.json`. Two facts against it. `reports/` is empty: the
`register` workflow writes `check.json` only at a `v*` tag and only as a workflow artifact
(`upload-artifact`), nothing commits it, and no tag exists; the page would have nothing to read
until the first release, and then a few counters (27 nodes, 28 links, C1 2/3 + 1 excepted, C2
3/3, C3 3/3, three advisory warnings). It would also be a third surface beside the two
roadmap pages, with no test gate. **Recommendation: the demo page**, as a register view and,
at the demo's own scale, a projection; the artifact page only once the pilot has a tag and
something to compare between tags.

Settlements kept: no store on pumllint's product path (ROADMAP 2026-08-26, never-build list);
`kg_experiment/` is lab (2026-10-16, 2026-10-30); `pumllint/` never reads the register
(2026-10-30 "Re-litigate on": an adopter asking for that "stays refused under 2026-08-26").
Everything below lives under `kg_experiment/demo/` or the register's `tools/`.

## 1. What "integrate" can mean, and what the demo makes cheap

| option | what the page shows | cheap because | new machinery |
|---|---|---|---|
| **(a) register view** | the pilot slice's nodes and links, states and approvals; coverage C1–C3 with denominator, covered, excepted, uncovered; the one exception and its expiry; an impact walk from a chosen module; the mapping matrix, every row `unverified` | `views.stage_details` already renders `{title, intro, sections:[{heading, text, table, list}]}` panels and `index.html` draws them; `register.load_register` and `check_register.run` are stdlib and return dicts; `tomllib` is in the Python 3.13 image | a vendored copy of the register; a `register_view.py` module; one card and two endpoints; glossary terms |
| **(b) projection** | the register as nodes and edges in the demo's Neo4j at a tag, provenance-stamped, with saved Cypher | `server.CYPHER` is a list the page renders; the harness's driver is in the image; `store_status` shows the pattern for a census | a loader script; label namespace separate from the harness's; a load order that survives the harness's wipe |
| **(c) per-scenario footprint** | for S1–S7, which register nodes and links the planted defect touches: gap keys and the 36 gate keys mapped to `ENT`/`PROC`/`APP`/`CAP` nodes, R-REQ hits mapped to the `REQ-nn` the links cite as evidence, S6's changed `decision_table.md` mapped to every link whose evidence cites it | `views.gaps_view` and `det["gate_keys"]` already carry the keys; the register's links carry `kit:<path>#<anchor>` evidence (`REL-03001` cites `kit:requirements.md#REQ-04`, four links cite `#DT-P`); the manifest digests give an exact "changed" test for S6 v2 | a hand-authored key-to-node map (36 rows) with a test that every id resolves; a sentence kind for it |
| **(d) report artifact** | charts over `check.json` | nothing to build in the repositories | nothing to read yet; see §0 |

Cheapest first: (a) then (c) reuse the panel style, the registry and the test harness
(`tests/test_kg_demo.py`) unchanged in shape. (b) is a day's work but needs the label-namespace
and wipe-order decisions below. (c) is the one that makes the integration say something the
two repositories do not say apart: the defect the gate blocked sits on `APP-0002` QuoteAPI,
`PROC-0001`, `JRN-0003`, and the register's approved links cite `REQ-01`, `REQ-04`, `REQ-05`
but not `REQ-06`, the open decision S2 and S5 plant. That is a register finding the page can
state without inventing anything.

## 2. Data flows and authority

**Where the register enters the demo.** Four routes, one recommended:

- **Vendored copy at a tag** under `kg_experiment/demo/register/` with a `SOURCE.md` after
  `model/SOURCE.md` (repository, tag, commit sha, date copied, sha256 per file or of the
  tarball), the TOML trees plus `tools/register.py`, `check_register.py`, `impact.py`
  copied byte for byte, nothing else. Recommended: the image carries it (`COPY . /repo`,
  `Dockerfile`), replay works offline from first start as the README promises, the deterministic
  mode's byte-for-byte diff (`tools/compare_deterministic.py`, the CI job) extends to the
  register view, and a test holds the copy to its `SOURCE.md` as
  `test_vendored_model_matches_its_source_note` already does for the model. Until the register
  cuts `v0.1.0`, pin the commit (`abb251c`) and say so; a tag is the proposal's unit
  (`docs/ieam-register-proposal.md` §3, "Tags are cut on the register").
- **Git submodule**: the README's paste block clones without `--recursive`, the CI checkout has
  no `submodules:`, and `COPY . /repo` copies an empty directory on a plain clone. No.
- **Fetch at container build**: network at build, a moving target unless pinned by sha, against
  `model/SOURCE.md`'s rule ("not fetched at build time: the image carries it"). No.
- **Mounted volume** of a sibling checkout: for the maintainer's machine only, through
  `docker-compose.override.yml` (`KG_REGISTER_DIR`), as a labelled *live* source beside the
  vendored one, as the page labels record versus demo run. Never the default or the image.

**Why a vendored tag beats a live fetch for a demo**: reproducibility (the page's numbers are
derivable from committed bytes, as the record's are); no network at runtime (the README's
offline promise and the EC2 warning both assume it); the deterministic comparison the demo
already proves field by field needs a fixed input; and the coverage summary depends on `today`
(`EXC-0001` expires 2027-01-31, `check_register.run(today=...)`), so the view must run the
checker with `--today` pinned to the tag's date and show the wall-clock result as a second,
labelled source, or the page changes under the viewer on 2027-02-01 with nothing committed.

**What the demo must never do**: write to the register (no PR, no file, no `exports/` folder;
the demo has no token and should have none); present the projection or the view as the record
(the record is the register's TOML at the tag; the view is derived, like `reports/`); copy tool
attributes (the register holds `name` only and checks it against an export; the demo adds no
description, no owner prose, nothing the kit or ARIS would own); reword register text (a
`rationale`, a `name`, a finding message is *data*, shown verbatim, exempt from the 20-word
rule, GLOSSARY.md rule 4); and infer hierarchy from anything but `parent`.

**Authority at each step**: the register's TOML at the tag is authoritative for identities,
links, states, approvals, exceptions and glossary; `SOURCE.md` plus digests are authoritative
for which bytes the demo carries; `check_register.run` on those bytes is authoritative for
findings and coverage, and the page shows its output, never a recomputation; the key-to-node
map (c) is the demo's own reading, declared as such on the page the way `views.SYSTEMIC` is
declared "the demo's reading of the record's §6"; the projection in Neo4j is derived, rebuilt
on demand, stamped, never the record; the result files remain the record of the experiment.

## 3. Design for (a) and (c), then (b)

### 3.1 Files

- `kg_experiment/demo/register/` (vendored: `metamodel/`, `glossary/`, the seven taxonomy
  directories, `relationships/`, `exceptions/`, `mapping/`, `decisions/`,
  `exports/kit/2026-10-30/`, `tools/{register,check_register,impact}.py`) and
  `register/SOURCE.md`.
- `kg_experiment/demo/app/register_view.py`: stdlib; `sys.path` the vendored `tools/`; builds
  the view model and registers its sentences through `views._reg`.
- `kg_experiment/demo/app/register_map.toml`: the 36 gate keys and the gap kinds to register
  ids, hand-authored, with a `basis = "authored"` header and the kit anchors each row rests on.
- `kg_experiment/demo/tools/project_register.py` (for (b)): stdlib plus the harness's driver,
  run as a subprocess by the server like `run.py`.

### 3.2 Endpoints (`server.py`, same `do_GET` dispatch)

- `GET /api/register`: `{source: {repo, tag, commit, copied, digest_ok}, summary, findings,
  coverage, nodes: [...], links: [...], exceptions, matrix, glossary}`; `summary` and
  `coverage` are `check_register.run(root, today=<tag date>)` verbatim; a `today=wall` query
  returns the wall-clock run, labelled.
- `GET /api/register/impact/<ID>`: `impact.walk` output, each edge with state, owner, evidence;
  404 on an unknown id (the tool's own exit 2 path).
- `GET /api/register/footprint/<S>`: for scenario `S`, the rows of `register_map.toml` hit by
  `det["gate_keys"]` levels below approved and by `det["D6_gate"]["blocked_keys"]`; the R-REQ
  hits joined to links whose `evidence` cites `kit:requirements.md#<REQ>`; for S6, every link
  and `maps_to` target whose evidence cites `contract/decision_table.md`, with the manifest
  digest beside the v2 digest from `stage2.load_v2`.
- `POST /api/register/project` and `GET /api/register/project` (for (b)): starts the loader
  through `Runner`, which already serialises one subprocess at a time.

### 3.3 Page sections

- A card under *The store*: **The register**, with the tag and commit, `27 nodes, 28 links`,
  the three coverage lines in the checker's own print format (data), the three advisory
  warnings, the exception with its expiry, and a `mapping matrix: 16 rows, 16 unverified` line.
  A node list grouped by taxonomy, each row opening a stage-style panel: id, kind, name
  (data), state, owner, approval `{by, on, record}`, source pointer, the links in and out.
- An **Impact** input (default `APP-0002`, the README's own question) rendering the walk as the
  pipeline-box table style.
- In the report view, a **Register footprint** box at the end of the pipeline strip, coloured
  by whether any touched node or link is below approved (S3's `ENT-0005` is `draft`, S2's
  `REQ-06` is cited by no link), opening a panel: the touched nodes, the links with their
  evidence anchors, and one controlled sentence per group.
- In the systemic panels, no change: the model is Legible's, not the register's.

### 3.4 Controlled English

The register's `glossary/glossary.toml` already defines node, link, relationship type, source
of record, export, approval, exception, coverage rule. Add them to `views.GLOSSARY` and their
forbidden synonyms to `views.FORBIDDEN`, then reconcile collisions, each needing a line in
`GLOSSARY.md`:

- **extract**: the register forbids it as a synonym of *export*; the demo's pipeline stage is
  *extract* and the basis *extracted by a parser*. Add *export* as a term and forbid only the
  noun phrases "an extract", "the extract": the test's word-boundary regex takes a phrase, so
  the stage label stands untouched. Two entries.
- **record**: demo "the committed results"; register "decision record", "source of record".
  Keep *record* for the results; the register's two are always written as full phrases.
- **approval**: demo "acceptance of a verified assertion"; register "a recorded file-state
  change". Define once as "a recorded acceptance, of an assertion in the store or of a node
  or link in the register", and qualify (*assertion approval*) where a register panel is open.
- **status** versus **state**: assertion *status* (proposed … invalidated) and node *state*
  (draft … retired) never swap; add *state* as a term.
- **entity**: demo "a thing the documents talk about"; register `ENT` nodes are information
  elements. Write *information node* for the register's, keep *entity* for the store's.
- **decision**: the arm's choice; the register's is always *decision record*. *Model* versus
  *metamodel*: no collision.

The register's checker scans only names, rationales and decisions; the demo's test scans every
generated sentence. The demo's test is the stricter gate and should run the merged list.

### 3.5 Projection (b): labels, properties, loader

The harness's store uses `Artefact, Version, Fragment, Entity, Assertion, Activity, Agent,
Verification, Approval, Gap, Derived` and `CONCERNS, ABOUT, SUPPORTED_BY, VERIFIES, …`
(`harness/load.py`, `rules.py`). `Approval` and `Entity` collide, so the projection takes its
own namespace: every node carries the label `Register` plus one of `RegNode`, `RegLink`,
`RegException`, `RegType`; relationships are `REG_<TYPE>` (`REG_REALIZES`, `REG_SUPPORTS`,
`REG_IS_SUPPORTED_BY`, `REG_CRUD` with `mode`, `REG_MAPS_TO` to a `RegExternal` node holding
the `target_external` string, `REG_PARENT`, `REG_OWNS`), plus `REG_LINK_OF` from a `RegLink`
node to its two ends when the link's own id, state and approval must be queryable (a
relationship property map cannot carry the approval table cleanly). Properties on every
node and relationship: `reg_id`, `kind`, `state`, `owner`, `approval_by`, `approval_on`,
`approval_record`, `tag`, `commit`, `export_date` (from the manifest), `digest` (of the TOML
file), `loaded_at`. Derived edges, if any (an inferred `delivers` through `parent`), carry
`derived = true` and `rule = "<name>"`; the loader derives nothing in the first PR.

Wipe order: the harness "first deletes everything in the store" (`demo/README.md`), so a
projection loaded before a deterministic run vanishes. The loader runs on demand after a run,
a header chip says whether the register is loaded and at which tag, and `store_status` adds a
`register` census (`MATCH (n:Register)`). Saved Cypher appended to `server.CYPHER`: which tag
is loaded; the impact walk from `APP-0002`; approved journey steps without
`REG_IS_SUPPORTED_BY` with the exception joined (C1); the links that cite a changed kit file,
joined to the harness's `Artefact` by path, the one query that crosses the two namespaces and
the reason to share the database at all.

### 3.6 Tests (stdlib, `tests/test_kg_demo.py` style, in `tests/test_kg_register_view.py`)

- the vendored copy matches `register/SOURCE.md` (sha256 per file); `check_register.run` on it
  is clean at the pinned date with the committed counts (27, 28, C1 2/3 + 1, C2 3/3, C3 3/3,
  three warnings);
- every id in `register_map.toml` resolves; all 36 gate keys have a row; every `REQ-nn` the
  R-REQ hits name is cited by a link or listed as uncited, and the view says which;
- every sentence the register view generates obeys the merged glossary and the 20-word limit
  (the existing registry test covers it once `register_view` uses `views._reg`);
- S6's footprint names exactly the links citing `contract/decision_table.md`, and the manifest
  digest differs from `stage2.load_v2`'s;
- the wall-clock source at 2027-03-01 shows `JRN-0004` uncovered, as the register's own
  `test_expired_exception_stops_excusing` does;
- for (b): the label set is disjoint from the harness's; the stack job asserts the `register`
  census after a project call.

### 3.7 CI

`kg-demo.yml` already triggers on `kg_experiment/demo/**`; the vendored copy sits under it. Add
to the stack job: `curl /api/register` and assert `summary.nodes == 27`, `coverage.C1.excepted
== 1`, `source.digest_ok`; for (b) a `POST /api/register/project` after the deterministic run
and a census assertion. The image build context is the repository root with
`Dockerfile.dockerignore`; the copy is small and needs no ignore entry.

### 3.8 Order of PRs, one step each, ROADMAP line each, record untouched

1. Vendor the register at a commit with `SOURCE.md` and the digest test. Docs and lab only.
2. `/api/register` and the register card with coverage, exception, matrix, node panels;
   glossary merge and `GLOSSARY.md` reconciliation; tests. The first visible step.
3. `/api/register/impact/<ID>` and the Impact input.
4. `register_map.toml`, `/api/register/footprint/<S>`, the footprint box and panel; tests.
5. Optional: the projection loader, the namespace, the saved Cypher, the CI census.
6. On the register's `v0.1.0`: re-vendor at the tag, update `SOURCE.md`, one line.
   *2026-11-01 (#260):* the one line is now a command. `tools/vendor_register.py`
   copies the path set from a clean checkout at a tag (`git describe --tags
   --exact-match`) and writes `SOURCE.md` itself, earlier copies carried forward;
   steps 1 and 6 were hand-edited tables, re-generated byte-identical at `v0.1.1`.

Each PR: a "later" bullet under the 2026-10-30 demo entry, the two artifact pages refreshed
after merge (CLAUDE.md), nothing under `kg_experiment/results/` or `pumllint/`. The proposal
places the projection with the register ("reads one tagged commit", §3), so step 5's loader
may land in the register's `tools/` and be vendored back, which keeps the demo a consumer.

## 4. Opportunity canvas

**Problems.** The register's three pilot questions are answered only in a terminal
(`impact.py`, `check_register.py`, `inventory.py`). The demo shows governed knowledge at the
assertion level and nothing at the enterprise-identity level, though the kit is the same. The
proposal's Neo4j projection is described and unexecuted. Coverage is at risk of being read as
a percentage the moment it leaves the checker's print format.

**Solution ideas.** A register card and node panels in the demo. A per-scenario footprint
joining gate keys and R-REQ hits to register ids by evidence anchors. A one-way projection
with its own label namespace and saved Cypher. A pinned-date and wall-clock pair of sources.

**Users and customers.** The maintainer, walking a reviewer through both repositories on one
page. A reader of the IEAM proposal who wants to see "identity spine between ARIS and the
graph" rather than read it. The bank's architecture stewards, who would run the same page on
their private instance, never this one. Later, aris2puml's owner for the `caps.txt` hand-off.

**Solutions today.** Four CLI tools and `unittest` output. `README.md` prose in both
repositories. The proposal's §5 question list. Neo4j Browser with the harness's store, which
knows nothing of the register.

**Business challenges.** Two sources of truth if the demo rewords or adds. The `extract` and
`record` collisions in the controlled vocabulary. Community edition's one database and the
harness's wipe. The register has no tag yet; the demo would pin a commit. Public demo, private
instance: nothing bank-side can ever appear.

**User value.** One click from a planted defect to the owning module, process, journey step
and the approved links that cite the requirement. Coverage with denominator and exception on
screen, in the checker's words. The impact walk a reader can repeat in Cypher.

**User metrics.** The footprint box answers for all seven scenarios with no unmapped key. The
register card's numbers equal `check_register.py`'s print, byte for byte. Zero forbidden words
in the merged registry across all builds. A reviewer finds `REQ-06` uncited without being told.

**Adoption strategy.** PRs 1–2 first; show the maintainer before 3–5. Re-vendor at `v0.1.0`.
Offer the loader to the register as `tools/project_register.py` once it runs in the demo.
Never route the bank's instance through the public image; document the private route in the
register's README only when asked.

**Business benefits and metrics.** The proposal's "one-way publication" gets its first
executed instance at 27 nodes, a measurement the 2026-10-30 entry lists as unfired. The
footer-versus-map check (proposal §4) gains a visible home for its findings. The demo's
reviewer time per question drops from four commands to one page. Metric: the three pilot
questions answered on screen, with the same counts as the tools.

**Budget.** PRs 1–4: lab Python and HTML, a few hundred lines, stdlib, no new dependency,
one afternoon each with tests. PR 5: a day, the driver already in the image. Ongoing: one
re-vendor per register tag. No infrastructure beyond the existing stack and CI job.

## 5. SWOT

**Strengths.** Same synthetic content on both sides, digested at a known pumllint commit.
Panel, registry and test machinery exist and are shaped for it. Both repositories are stdlib
and TOML; `tomllib` is in the image. The vendoring pattern (`model/SOURCE.md`) is proven and
tested. The register's glossary was modelled on the demo's. The CI job already covers the
directory.

**Weaknesses.** The key-to-node map is hand-authored and the demo's own reading, a second
interpretive layer like `SYSTEMIC`. No register tag exists; the first vendoring pins a commit.
Community edition: one database, wiped per run, so the projection is transient. The register's
`impact.py` walks `supports`, `delivers`, `is_supported_by`, `realizes`, `concerns` from a
node's own taxonomy and does not climb `parent`, so from `APP-0003` it reaches `JRN-0003` but
no product; the page would show that limit honestly or not at all. `reports/` is empty, so
nothing cross-tag can be shown.

**Opportunities.** First executed one-way projection of a register tag, small enough to read.
A concrete demonstration that the register cites `REQ-01/04/05` and not `REQ-06`, the open
decision: evidence for the pilot's question 3 shape. A reusable loader the bank's instance
could run privately. A tested reconciliation of two controlled vocabularies, which the IEAM's
glossary step would need anyway.

**Threats.** The demo drifts into a second source of truth: a description typed into a panel,
a rounded coverage figure, a derived edge shown without its rule. The vocabulary merge weakens
either side's rules to make them agree. Time spent here before the register's export route is
tested on a target installation, which the 2026-10-30 entry names as the re-litigation
trigger, buys a nicer view of synthetic data. A reader mistakes the public demo for the bank's
instance, or the projection for the IEAM's ARIS-fed one. A live-fetch shortcut breaks the
offline promise.

## 6. Caveats and pushback

**Unverified.** Layout of a 27-row card in the menu column. The loader's Cypher against
`neo4j==6.4.1`; nothing here was executed against a server. Where the maintainer wants the
loader; the proposal says the register. The exact 36-row map: this note names the taxonomies
each key family lands on
(`weight_kg|*` on `ENT-0002`, `PROC-0002`, `CAP-0004`; `S-*` on `PROC-0003`, `CAP-0003`,
`APP-0004`, `ENT-0005`; `P*` on `ENT-0004`, `PROC-0004`, `APP-0003`, `CAP-0002`, `REL-10001`;
`QuoteAPI|*` and `response|*` on `APP-0002`, `PROC-0001`, `ENT-0003`, `JRN-0003`;
`flow|order` on `PROC-0001`), not the rows, and the rows are a reading to be approved by the
maintainer, not extracted.

**What would make the demo a second source of truth.** Any field on the page that is not
read from the vendored TOML, the checker's output or the result files. A coverage percentage.
A "description" column. A derived edge without `derived = true` and its rule. Running the
checker at wall-clock date only. Re-wording a `rationale` to fit 20 words instead of quoting
it as data. A write path of any kind, including a "propose a link" button.

**What the integration must not claim.** That the register's content is anything but the
synthetic CargoQuote kit (`decisions/0002`, "No bank-related data is stored here"). That the
bank's instance is reachable from, or reflected in, the public demo; it never is. That any
ARIS, Archi or EDM route exists: `exports/aris`, `exports/archi`, `exports/edm` are empty and
every matrix row reads `unverified`; the page shows those rows as they are and names no tool
feature beyond what `metamodel/sources.toml` says. That the projection is the IEAM's; it reads
a register tag, which is the proposal's redirection of the IEAM text, and the page should say
so in one data sentence quoted from the proposal.

**Worth doing before the pilot's three questions are answered?** Partly. PRs 1–2 (vendor,
card, coverage, glossary merge) cost little, break nothing, and give the maintainer a page to
show while the export route stays untested; the glossary reconciliation is work the IEAM needs
regardless. PR 4 (the footprint) is the integration's only new statement and is cheap once the
map is approved. PR 5 (the projection) should wait for `v0.1.0` of the register: a projection
of an untagged commit contradicts the proposal's own rule that it reads a tag, and 27 nodes
in Cypher prove nothing the TOML does not already show. Nothing here moves the re-litigation
trigger (a tested ARIS export route, or an adopter), so no ROADMAP checkbox: a "later" bullet
under the 2026-10-30 demo entry per PR, as #223–#238 were recorded.

## Summary

1. "The dashboard" is read as the kg demo page under `kg_experiment/demo/`; the claude.ai
   Dashboard-artifact reading has nothing to read (`reports/` empty, written only as a CI
   artifact at a tag that does not exist) and is deferred.
2. Four integrations: (a) a register view, (b) a Neo4j projection, (c) a per-scenario
   footprint, (d) a report artifact. (a) and (c) are cheap on the demo's panel, registry and
   test machinery; (b) needs a label namespace and a post-run load order; (d) waits.
3. The register enters as a vendored copy with `SOURCE.md`, pinned to a commit until
   `v0.1.0`; submodule, build-time fetch and live fetch are refused for reproducibility, the
   offline promise and the deterministic diff. The checker runs with `--today` pinned.
4. The demo never writes back, never presents view or projection as the record, never copies
   or rewords register text, never adds a field the TOML lacks.
5. Design: `/api/register`, `/api/register/impact/<ID>`, `/api/register/footprint/<S>`, an
   optional `/api/register/project`; a register card, node panels, an impact input, a
   footprint box; labels `Register`/`RegNode`/`RegLink`, relationships `REG_<TYPE>`, stamps
   `tag, commit, export_date, digest`; stdlib tests; the existing CI job.
6. Glossary collisions to settle in `GLOSSARY.md`: extract/export, record, approval,
   status/state, entity, decision.
7. The one new statement the integration can make: the register's approved links cite
   `REQ-01/04/05` and not `REQ-06`, the open decision S2 and S5 plant; S6's change touches
   four links citing `#DT-P` and `REL-10001`.
8. Six PRs, one step each, ROADMAP "later" bullets, record untouched, `pumllint/` untouched.
9. Worth doing now: PRs 1–2 and 4. The projection waits for the register's first tag. No
   settlement moves; the re-litigation trigger (a tested ARIS export route) is unaffected.
