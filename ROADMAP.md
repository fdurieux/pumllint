# pumllint roadmap

Status baseline: **v0.5.0** (2026-07-22) shipped the complete SCORING.md
maturity model — scorer, gap reports, `score --min-level` CI gate, integrity
caps C1–C7, XD cross-diagram pack — calibrated (SCORING.md §9), frozen behind
golden tests, and empirically characterized (EVIDENCE.md: fidelity
correlation r ≈ 0.49, sharp degradation below Level 2). **v0.6.0**
(2026-07-23) added Arc A's model-set aggregate score and Arc B's
baseline/ratchet mode; **v0.7.0** (2026-07-23) added trend/delta reporting
and the shields.io badge; **v0.8.0** (2026-07-23) added the composite GitHub
Action and pre-commit hooks; **v0.9.0** (2026-07-23) opened Arc C with the
class-diagram parser and CLS pack; **v0.10.0** (2026-07-23) added the
state-diagram parser and STA pack; **v0.11.0** (2026-07-23) closed the
original base catalog with UC003; **v0.12.0** (2026-07-23) thickened
DIM-TRC/DIM-RDB (GEN006–009, SEQ011) and settled the weight revisit
(unchanged, SCORING.md §9); **v0.13.0** (2026-07-23) finished Arc C with
cross-type entity identity (XD004–005 — 42 base rules); **v0.14.0**
(2026-07-24) extended the calibration corpus and golden contract to every
diagram type (additive re-freeze, 49 → 83 units); **v0.15.0** (2026-07-24)
completed Arc B with the architect-facing HTML report; **v0.16.0**
(2026-07-24) opened Arc E with `pumllint fix`; **v0.17.0** (2026-07-24)
completed Arc D's deepening (complexity-normalized evidence, third family,
multi-model waves); **v0.18.0** (2026-07-24) pinned the JSON report shapes
behind shipped schemas (`pumllint schema`). This file tracks what remains,
grouped into arcs. Keep it updated as items land.

## Arc A — Integrity (done)

- [x] **Model-set aggregate score** *(0.6.0)* — `aggregate_scores()` folds
  per-diagram results into a `ModelSetResult` (worst level +
  element-weighted composite, SCORING.md §3); text and json reporters emit
  it. `--min-level` gates on the model-set level by construction (set level
  = worst diagram level).

## Arc B — Trust & adoption (done)

- [x] **Baseline/ratchet mode** *(0.6.0)* — `pumllint score --baseline
  maturity.json` records per-diagram levels on first run, then fails CI only
  on *regression*; `--update-baseline` accepts the status quo
  (`pumllint/baseline.py`).
- [x] Trend/delta reporting *(0.7.0)* — ratchet-compare runs annotate the
  text report ("Level 3 → 4 since last baseline", "new since baseline") per
  diagram and for the model set; json adds `baseline: {level, delta}`.
- [x] Badge output *(0.7.0)* — `-f badge` emits shields.io endpoint JSON for
  the model-set level (SVG deemed unnecessary: shields renders styling from
  the endpoint; revisit only on demand).
- [x] Packaging *(0.8.0)*: composite GitHub Action (`action.yml`, inputs
  mirroring the CLI, installs from the pinned ref) and pre-commit hooks
  (`.pre-commit-hooks.yaml`: `pumllint`, `pumllint-score`); both dogfooded
  in tests.yml and drift-guarded by tests/test_packaging.py.
- [x] HTML report *(0.15.0)* — `pumllint score -f html`: single
  self-contained page (no scripts, no external requests, no timestamps —
  deterministic and offline-renderable), model-set verdict first, diagram
  cards worst-first with dimension bars, gap report and baseline trends.
  Score-only like the badge; Action `format: html` + upload-artifact is the
  CI recipe (README). **Arc B is complete.**

  *Design record (inception reviewed before building):* the report serves
  the one audience the maturity score was built for but no output reached —
  the architect/reviewer who never runs CLIs; the gap report (the product's
  most persuasive feature) previously existed only as terminal text. The
  original one-liner was kept in spirit but sharpened four ways: (1) bound
  to the *score* pipeline, not lint — an architect report of raw findings
  is just a prettier error list, the value is levels/gaps/trends; (2)
  worst-first ordering, because the product's own thesis is that the set is
  only as trustworthy as its weakest diagram; (3) no JS and no timestamps —
  native `<details>`-free simplicity, deterministic and diffable output as
  a feature; (4) deliberately no charts/history — the baseline file is the
  only trend state the product has, and a snapshot + deltas is the honest
  scope. Fit was near-zero-cost by construction: `render_maturity()` was
  already the pluggable seam, so `-f html` needed no CLI or Action changes.

## Arc C — Coverage growth (base catalog done; further growth demand-driven)

- [x] **CLS pack + class-diagram parser** *(0.9.0)* — `parser/class_.py`
  (classifiers, brace-body members, relations with multiplicities; typed by
  classifier declarations and `<|` generalization arrows, never re-typing
  other forms) + CLS001–005. The corpus caveat this note originally carried
  was closed in 0.14.0: mutation ladders and clean probes for every diagram
  type, golden re-frozen additively — the contract now covers CLS scoring.
- [x] **STA pack + state-diagram parser** *(0.10.0)* — `parser/state.py`
  (declarations, composite bodies with a container stack, `[*]` endpoints;
  typed by the `state` keyword and `[*]`, never re-typing other forms) +
  STA001–003. Same corpus history as CLS: state fixtures joined the golden
  contract in 0.14.0.
- [x] UC003 *(0.11.0)* — usecase links now carry label/arrow (`UseCaseLink`,
  tuple-unpack compatible), endpoints typed by syntax (`(X)` usecase, `:X:`
  actor), reversed arrows normalized; direction judged via actor
  connectivity, only when exactly one endpoint is actor-connected.
- [x] **Thicken DIM-TRC** *(0.12.0)* — GEN006 owner-tag + GEN007
  requirement-link, both convention-gated (dormant until the project
  configures its `pattern` — an always-on tag requirement would demote every
  diagram below the L5 dimension gate by fiat); parser gained
  header/footer/caption directives as tag carriers. Weight revisit settled:
  unchanged, signal-proportional (SCORING.md §9, v0.12.0 bullet).
- [x] **Thicken DIM-RDB** *(0.12.0)* — SEQ011 max-messages (default 30),
  GEN008 note-density (≥4 notes and >0.5/element), GEN009 max-elements
  (default 60, any type). Tail guards: no calibration-corpus unit trips
  them, so golden scores were unchanged (verified, no re-freeze).
- [x] Grow DIM-CON into cross-*type* entity identity *(0.13.0)* — XD004
  cross-type-name-collision and XD005 cross-type-stereotype-conflict span
  sequence/use-case participants, class classifiers and activity swimlanes
  (state names excluded on purpose: modes, not entities). Sequence-internal
  conflicts stay XD002/XD003's territory — no double reporting. Golden is
  structurally immune (corpus units score one diagram at a time; cross rules
  need ≥ 2).
- [ ] **Further coverage (demand-driven; wait for pull).** The base catalog
  is done — five diagram types parsed, 42 rules, every type under the
  golden contract — and no further pack is queued. Candidate directions if
  a concrete user pulls: **new type packs** (component and deployment
  first, the common architecture-documentation forms — for the C4-PlantUML
  form of that demand see *Settled questions*: fit verified 2026-07-27,
  wait for census pull; object/ER/timing are progressively more niche), **deepening the thinner packs** (CLS 5, STA 3,
  UC 3 rules against the sequence family's 11 base + 9 codegen), and
  **growing the XD family** across more entity kinds. The bar is higher
  than "parser + rules": a new pack ships with corpus mutation ladders and
  clean probes, a deliberate additive golden re-freeze, pilot regeneration,
  and ideally an evidence extension — scores are a public contract.
  Implementation recipe: the new-parser pattern and registry discipline in
  RULES.md's implementation notes (type markers no other form uses; never
  re-type; blocked rules stay unregistered until their parser exists).
- [ ] **XD member and relationship coherence** — the concrete form the
  "growing the XD family" direction above took when a third-party corpus was
  finally read (2026-08-26, docs/foreign-corpus-audit.md). The XD pack already
  builds the corpus-wide symbol table for participant *identity*; extending it
  to **declared members** and **relationship direction** would have caught two
  defects that were text-visible and survived a Level 5 100/100 gate — an
  asymmetric dividend/sink pair, and a `..>` dependency pointing the wrong way.
  Scope carefully: this sits close to relationship *legality*, and the same
  corpus measured ~73% false positives on its own code-aware checks — the
  cautionary number, not the encouraging one. Arc C's bar applies in full
  (mutation ladders, clean probes, deliberate additive golden re-freeze, pilot
  regeneration). *Trigger: a second corpus or an adopter showing the same
  defect class — one corpus is an anecdote.* *Annotated 2026-08-28: the
  cross-diagram-relationships evaluation
  (docs/cross-diagram-relationships-evaluation.md) reached this same gap
  from the opposite direction — a synthetic probe (its M3: contradictory
  edges over perfectly agreeing entities, zero cross-diagram findings) now
  gives the item a reproducible fixture, and its §5 argues the scope
  boundary: within-notation edge coherence, never the RDF
  qualified-relationship shape. The trigger is unchanged — a probe is not
  a second corpus.*
- [ ] **XD display-name identity (G2)** — the cross-diagram join is keyed on
  the `as` alias, so `participant "Order Service" as OS` and `database
  "Order Service" as OrderService` — one entity by every human reading, with
  a conflicting kind and stereotype — are never compared (measured:
  docs/cross-diagram-relationships-evaluation.md, G2/M2), and an alias
  rename silences any XD finding. Candidate: an evidence-shaped rule
  (XD003/XD004 family, minor) flagging the same display name under
  different aliases as "likely one entity", honouring `distinct`. Moderate
  false-positive risk on generic display names; Arc C bar in full.
  *Trigger: an adopter corpus using `as` aliases inconsistently.*
- [ ] **`ref over` capture + declared diagram→diagram links (G6/O4)** — the
  notation's one cross-diagram construct (recommended by SEQ006's own
  message) is dropped whole by the parser, and the nearest declared-link
  mechanism, `trace`, is untyped and undirected (same note, G6/§2.3).
  Candidate, built together if built: parse `ref over` into the model, and
  a link-integrity check (dangling target, orphan diagram) with
  `trace`-style gates; any carrier widening moves GEN007 and `trace`
  together (the SysML invariant). Same shape as the Linked.Archi `'!la-`
  candidate — if either is built, build both. *Trigger: an adopter running
  `trace` who asks for diagram→diagram links in the same table.*

## Arc D — Evidence engine (core done; optional deepening)

EVIDENCE.md delivered the measured maturity→codegen relationship; the
2026-07-24 deepening (v0.17.0, 3 waves, 243 runs, $10.19) addressed all
three items — full write-up in EVIDENCE.md §Deepening:

- [x] Complexity-normalized fidelity *(0.17.0)* — `tools/analyze_evidence.py`
  computes partial correlations controlling for *hard demand* (judge-counted
  guards + failure paths). Headline: the confound was **suppressing** the
  signal — per-diagram r(composite, fidelity | hard demand) ≈ 0.65–0.70,
  stable across two generators and two judges (raw r 0.22–0.58).
- [x] Third scenario family + larger n *(0.17.0)* — `insurance_claim` pair
  (good = L5/100 under codegen, bad = L1/24) wired into the corpus ladder
  (additive golden re-freeze, 83 → 97 units); pooling the identical-config
  waves puts 18 diagrams at n = 6.
- [x] Multiple generator and judge models *(0.17.0)* — harness gained
  --gen-model/--judge-model/--results-dir and a judge-only --rejudge mode
  (judge robustness at ~$0.40). Cliff reproduces and *steepens* under
  haiku-4-5 generation; judges agree on ranking (r = 0.715) with a ~9-point
  leniency offset — quote correlations, never absolute fidelity. Both
  limitations this left standing were resolved 2026-07-26: prompt
  variation by the execution-oracle waves (three prompt styles),
  cross-vendor by the wave below.
- [x] **Execution-based oracle wave** *(2026-07-26)* — the research's one
  standing critique (fidelity was LLM-judged) answered with hand-written
  acceptance suites per scenario family (frozen + pre-registered before
  any scored run; `tools/acceptance/`, sandboxed per-scenario children).
  Phase A retro-executed 756 scenario runs over the three stored waves at
  $0; Phase B added two fresh pinned-entry waves ($15.03, three prompt
  styles total). Results (EVIDENCE.md §Execution oracle): the **cliff is
  oracle-robust** (16–25 pp executed pass-rate, 21.9 pp pooled) and
  **scaffold-resistant** (entry-contract pinning lifts L2 to ≈ pristine
  but does not rescue L1); pre-registered X3 **failed** — judged fidelity
  is not a per-run proxy for executed correctness (r ≈ 0.25) — so the two
  oracles are quoted separately, never merged. Fixed-prompt limitation
  resolved by XB.
- [x] **Agent-repair evidence wave** *(2026-07-27, $5.95)* — the
  interventional test of the docs/agents.md loop, run author-less (the
  worst case), pre-registered as X-R1..X-R4 with a pre-committed
  interpretation matrix. Repair = sonnet-5 from the gap report alone
  (≤ 2 passes, `pumllint fix` first, invented decisions logged);
  generation under the exact stored wave-main2 config; frozen suites.
  Results (EVIDENCE.md §Agent-repair): **structural repair recovers**
  (repaired-L2 +10 pp of a 20.8 pp deficit; structural mutants to full
  pass) but **invention is net-negative below the cliff** (repaired-L1
  0.583 vs 0.642 unrepaired — X-R3a failed in the informative
  direction) — and every repaired diagram still passes the gate
  (X-R4): the gate is an input filter, never a content certifier. The
  recipe's "ask, never invent" covenant is now measured, and
  docs/agents.md §What-is-measured carries the two-sided result.
  **With-author arm** *(same day, $5.73)*: the intended-use loop —
  firewalled LLM author (pristine + questions only), tagged Q&A,
  leakage audit (2/255 answers flagged, disclosed) — **recovers the
  cliff**: repaired-L1 0.857 (vs 0.583 author-less, 0.642 untouched;
  X-A2), repaired-L2 0.957 ≈ pristine 0.949 (X-A5); the ceiling below
  pristine held (X-A3, mechanism honestly revised: dominated by one
  blocking-loop artifact, a new failure mode); X-A1/X-A4 failed
  informatively (deep rebuilds cap at L3 on the DIM-CMP gate while
  executing at 0.75–1.0 — score conservative, execution led; invention
  halved but not eliminated). The two arms isolate the author as the
  causal ingredient: asking vs inventing ≈ 27 pp executed below the
  cliff.
- [x] **Cross-vendor evidence wave** *(2026-07-26, $8.66 — run the day
  the key arrived)* — `gemini-3.1-pro-preview` as generator and as judge
  (Google had retired the stable 2.5-pro for new API keys; the preview
  caveat was pre-registered, expectations XV1–XV3). **XV2 confirmed on
  the vendor-neutral oracle**: executed cliff 20.9 pp (opus pooled 21.9)
  — the below-Level-2 gate now stands on three generators across two
  vendors, measured by behavior. **XV1 failed**: sonnet judging Gemini
  code is nearly flat (gap 3.2 pts) and tracks execution at r = 0.002 —
  judged fidelity has no validity across the vendor boundary. **XV3
  confirmed**: judges agree with each other on ranking (r = 0.682,
  ~19-pt leniency offset) — better than either agrees with execution;
  reliability is not validity. Full record: EVIDENCE.md §Cross-vendor.
- [ ] **Adopt a foreign corpus as a regression fixture** — the 2026-08-26
  J-F audit (docs/foreign-corpus-audit.md) was the first time a corpus this
  repository did not author was read for *semantics* rather than dialect, and
  it returned four real defects (SEQ107 F1/F2, GEN005's use-case budget, and
  the replacing `lexicon()` helper — all fixed). That corpus offers
  what README's beta caveat actually asks for: 24 diagrams across five types,
  a clean baseline, a documented mutation battery with expected findings, and
  a defect ledger. Adoption is not a code decision — it is licence and
  attribution, vendor-vs-submodule, and a conscious additive golden re-freeze;
  the wild tier and the pilot census both settled on metadata-only, and this
  would be the first departure from that. Retiring the caveat needs the
  fixture, not the audit. *Trigger: owner go on vendoring.*

## Arc E — Ecosystem (demand-driven; wait for pull)

- [x] `pumllint fix` *(0.16.0)* — auto-remediation for exactly the
  mechanical findings where nothing has to be invented: GEN002 (name from
  file stem, ordinal suffixes for multi-diagram files), GEN001 (humanized
  title), SEQ001/SEQ101 (declare implicit participants in first-use order,
  anchored after existing declarations). Fixes are driven by the engine's
  violations — suppressed/disabled findings are never fixed — and the run
  is idempotent; `--dry-run` prints a diff and exits 1 when fixes are
  pending (CI check mode). Deliberately excluded: anything requiring
  invented content (labels, guards, multiplicities). Possible follow-up on
  demand: a `pumllint-fix` pre-commit hook.
- [x] JSON schema for the report formats *(0.18.0)* — reclassified as
  *contract hardening*, not ecosystem, and done without waiting for pull:
  the project already treats scores as a public contract (golden test), but
  the JSON report *shape* — what CI scripts actually parse — had no
  equivalent guard. Draft 2020-12 schemas for the lint and score `-f json`
  outputs ship as package data (`pumllint/schemas/`), printed by
  `pumllint schema {lint,score}`; tests/test_schema.py validates every
  emittable report shape against them and sync-tests the enums against the
  code's canonical sets (Severity, LEVEL_NAMES, dimensions, GAP_KINDS).
  Validation is a deliberately minimal stdlib subset validator
  (`pumllint/schema.py`) that refuses unsupported keywords — the
  zero-dependency promise rules out jsonschema. Badge and sonar are
  deliberately out of scope: those shapes are shields.io's and SonarQube's
  contracts. `diagramType` stays an open string (new parsers add values);
  gap `kind` is a closed enum anchored to `scoring.GAP_KINDS`.
- [ ] LSP server / IDE integration for inline findings. Note (2026-07-24
  re-evaluation): `pumllint fix` makes code-actions nearly free if this is
  ever built, and a stdlib JSON-RPC/stdio server fits the zero-dependency
  promise — but it is permanent maintenance surface; still strictly
  wait-for-pull. If the underlying ask turns out to be "inline findings in
  PRs", a GitHub `::error` annotations reporter is the cheap substitute.
- [ ] Real SonarQube plugin with measures (replacing the synthetic-issue
  workaround in the sonar reporter). Bar raised (2026-07-24 re-evaluation):
  build only for a concrete Sonar-shop user whose need the generic-import
  route cannot meet — the plugin's sole delta is measures/quality-gate in
  Sonar's UI, which `--min-level` + baseline already provide in CI, and a
  Java artifact with its own release train cuts against the repo's ethos.

## Arc F — AI-authored rules (demand-driven; wait for pull)

Feasibility investigated 2026-07-24: having an AI implement rules from the
RULES.md Gherkin is viable *because* the harness already exists — the blocks
are executable acceptance tests (extract_features + pytest-bdd + sync test),
rules are 15–40 lines over a parsed model, and the golden-score contract
catches silent over-firing. The residual risk is **not** hallucination (the
BDD/golden/parity gates fail loudly) but *under-specification*: code that
passes 2–4 example scenarios yet generalizes wrongly, and an implementer
editing its own oracle. Build these safeguards only when rule authoring
actually becomes a recurring pipeline rather than occasional sessions.
The concrete form of that trigger (recorded 2026-07-30): a pilot or
adopter yes that queues a new rule pack — the obligation/flow phases
are the standing candidate — makes authoring recurring by definition;
build these safeguards *before* that pack, which would be the first
one authored under the full harness:

- [ ] **Spec/implementation separation** — two-phase workflow: the RULES.md
  section (rationale, severity, dimension, default-vs-dormant, Gherkin) is
  authored and human-reviewed first; a *fresh* session implements from the
  spec. Step 0 design judgment and golden re-freezes stay human — the AI
  writes steps 2–4 of the writing-rules.md loop, never signs off step 0/5.
- [ ] **Thickened Gherkin bar** — before handing a rule to an implementer,
  its block must cover: fire case, pass case, each option's effect
  (GEN009 pattern: same diagram, threshold via config), dormancy case if
  convention-gated, and one boundary case (at-limit, suppression). Optional
  overfit detector: hold one scenario out of the implementer's context and
  run it only at verification.
- [ ] **Implementer diff gate** — the implementation diff may touch only
  `pumllint/rules/**`, `catalog.toml`, the README rules-table row, and the
  RULES.md status flip ⏳→✅. Any change to Gherkin blocks, `tests/bdd/**`,
  or golden files rejects the run (the oracle is read-only for the agent
  that must satisfy it).
- [x] **Corpus-firing report** — beyond pass/fail golden scores, run the new
  rule over the calibration corpus (and wild tier) and emit where it fires
  and how often, as a human review artifact. Catches "semantically wrong but
  golden-neutral" rules; this is the analysis that forced GEN006/GEN007's
  dormancy decision, made routine. *(Chassis built 2026-07-30:
  `tools/corpus_firing.py` — manifest-aware per-unit profiles with
  golden-pipeline engine parity, wild tier swept separately, `--config`
  for convention-gated packs, `--rules` for the new-rule zero-firing
  check. The census keeps its standalone pilot role. First run's yield:
  SEQ102/SEQ104/SEQ107/SEQ109 fire zero times across all 97 units + wild
  — the deeper codegen rules have no corpus exercise.)*
- [ ] **Adversarial verify pass** — an independent agent prompted to refute:
  construct a diagram where the implementation contradicts the RULES.md
  rationale. Concentrate the strongest model here and on algorithmic rules
  (cycles, reachability, XD majority attribution); pattern-following rules
  can use a cheaper implementer — the harness carries them.

## Requirements-pipeline arcs (G–J — specified 2026-07-29, builds gated)

A verified external reassessment of a prose → model → prose
requirements-validation pipeline (fit evaluation:
docs/prose-pipeline-evaluation.md — verdict: sense, with corrections)
maps onto four new arcs. The pipeline's shape: prose requirements are
cast into a typed model by an LLM under a human gate (**recipe and lab
territory — never product**), the model is gated by the shipped
conformance machinery (lint/score + codegen profile — already built),
and everything new in the product is deterministic: a traceability
matrix, a verbalizer (deterministic back leg — the reassessment's crux
conditional, satisfied here by construction), a k-way model-diff
divergence meter, and the evidence that measures them. No build starts
from the specification alone; per-arc triggers below. The never-build
list and license posture live in § Settled questions.

## Arc G — Requirements traceability (shipped in v0.25.0, 2026-07-29)

- [x] **Coverage matrix command** *(built 2026-07-29 on owner go — the
  arc's named trigger; implementation plan reviewed before build)* —
  shipped as `pumllint trace`: all three directions (uncovered
  requirements, unlinked diagrams, plus **unknown references** — IDs a
  diagram cites that the inventory lacks, the SEQ001 typo-detector
  instinct applied to requirement IDs), three opt-in gates
  (`--fail-on-uncovered/-unlinked/-unknown-ref`), text + json with a
  shipped schema (`pumllint schema trace`), and the carrier set
  refactored into `pumllint.model.prose_directives` so GEN007 and the
  matrix agree by construction. The Action's `command` whitelist gained
  `trace` (inventory flags via `extra-args`). Original spec follows —
  delivered as written:

  Given the diagrams plus a
  requirements inventory (a plain ID list in text/json/yaml — in
  practice the synchronized export from a canonical process or
  requirements repository — or a file/tree scanned with the project's
  GEN007 `pattern`), report both directions: which requirement IDs are
  realized by which diagrams, which IDs no diagram references, which
  diagrams reference nothing. Text + json (schema contract discipline
  applies; stable IDs first-class, shape designed to extend toward the
  full requirement → process step → rule → component → contract →
  verification matrix without breaking v1 — see
  docs/spec-stack-evaluation.md), exit-code gate in the `--min-level`
  style. Foothold: GEN007 already matches the reference pattern against
  name/title/header/footer/caption/notes; what's missing is only the
  aggregation. Deterministic, zero new dependencies. *Trigger: a
  requirement-ID convention actually configured — the pilot's
  conventions workshop is where one appears — or owner go.*

## Arc H — Verbalizer (gated on Arc G + review-aid pull)

- [ ] **Unmodelled-content tracking** (precondition, small and
  additive) — the parser skips unknown lines silently today; the model
  gains a per-diagram count (and line numbers) of skipped non-comment
  source lines so any rendering of the model can disclose what it does
  not show. Measured baseline on the bundled corpus: projection is
  semantically complete (evaluation doc, Probe A); the census bounds
  the claim on foreign corpora.
- [ ] **`verbalize` output** — deterministic controlled-English
  rendering of the parsed model, sequence-first (the richest model:
  call/reply pairing, blocks, activations). Byte-identical across runs
  (HTML-report determinism contract); every run prints the
  unmodelled-content disclosure the way scores print suppression
  counts — never silently. A review aid shown beside the source prose;
  **never a similarity score**. Test bar: a mechanical
  projection-completeness check — every model element renders a
  sentence (verifiable without parsing English back; a CNL grammar for
  re-parsing prose is exactly the from-zero territory that stays
  parked). The SBVR lesson applies: real templates under test, not a
  style guide. *Trigger: Arc G shipped, plus a pilot/adopter asking
  for the review aid.*

## Arc I — Divergence meter (gated on a real k-generation workflow)

- [ ] **k-way model diff** — parse k diagrams of the same scenario,
  match entities XD-style (identity + declaration comparison — the
  XD001–005 symbol-table walk generalized), similarity-match messages
  per (source, target) pair, and report divergence *localized to named
  elements*, with an agreement summary (unanimous / majority /
  contested). Text + json. Positioning: the empirical complement to
  static DIM-AMB — where k generations of the same prose disagree is
  where the prose is ambiguous. Feasibility measured with shipped
  machinery (evaluation doc, Probe B). k-fold generation itself
  (grammar-constrained decoding guidance included) stays in
  tools/ and docs/agents.md — the meter judges outputs, it never
  generates them. *Trigger: a k-generation workflow actually in use
  (agents.md loop or lab harness producing candidate models), or
  owner go.*

## Arc J — Pipeline evidence (bound to H/I; Arc D methodology)

- [ ] **Injected-ambiguity wave** — the mutation-ladder pattern applied
  to prose: scenario briefs with planted ambiguities, k models
  generated per brief in the lab, pre-registered expectations, then
  measure whether the Arc I meter localizes the planted ambiguity
  (precision/recall of divergence as an ambiguity signal). The
  reassessment's cited ~50%-precision LLM ambiguity detection is the
  bar to beat mechanically.
- [ ] **Foreign-corpus projection measurement** — the census extended
  to report verbalizer projection completeness (Probe A's number on a
  real corpus), which is the honest bound on Arc H's claim. *Trigger:
  Arcs H and I shipped — evidence measures them; costs recorded per
  wave, Arc D style.*

## Settled questions (decision records — don't re-litigate without new evidence)

- **Auto-improvement / self-tuning (2026-07-26): measurement yes,
  promotion loop no.** A deep-research pass (~100 sources: Google
  Tricorder, Meta Infer/Getafix/SapFix, BitsAI-CR, champion–challenger
  practice in regulated decisioning, LLM-eval methodology) assessed an
  empirical auto-improvement system for pumllint — propose config/rule
  changes, shadow-run candidate vs champion, auto-activate on a
  codegen-fitness delta. Verdict, adopted here:
  - *Evidence-backed rule governance* is the endorsed practice — and is
    already this project's (Arc D evidence, golden contract,
    corpus-firing analysis, dogfooding scorecard, suppression
    disclosure).
  - *Shadow runs* (a `--shadow-config` champion–challenger mode: evaluate
    both configs, log finding-level diffs, never affect exit codes) are
    sound, cheap and governance-native, but strictly wait-for-pull: they
    only pay off when someone actually iterates a config against a live
    corpus. This is the single loop component kept on the shelf.
  - *Unattended promote-on-delta* is **rejected**: no shipped system
    anywhere closes this loop (Tricorder, Meta, SonarQube, BitsAI-CR all
    keep humans on actuation); at realistic corpus sizes a paired config
    comparison detects only ~4–10 pp effects while LLM-generation
    nondeterminism plus repeated comparisons guarantee eventual
    promotion-on-noise; and a fitness score routed through an LLM judge
    is Goodhart-exposed (optimizes judge-pleasing diagrams) and silently
    decays when the generation model version changes. Regulated-industry
    governance points the same way: challengers never auto-promote —
    promotion is a reviewed decision over an evidence dossier.
  - The research's proposed phases map onto existing arcs: its telemetry
    ≈ suppression disclosure + ratchet/trends (built); its fitness
    benchmark ≈ Arc D (built; its judged-vs-execution critique landed as
    the execution-oracle wave, 2026-07-26); its rule-authoring
    safeguards ≈ Arc F (parked).
  - *Packaging*: measurement/lab machinery stays **in this repo** —
    `tools/` plus the gitignored corpus, with optional extras if a
    shippable piece ever needs a dependency. The zero-dep wheel already
    provides the isolation a separate `pumllint-lab` distribution would
    buy, without a second release train (same ethos bar as the Sonar
    plugin). Split only if the harness itself gains a concrete external
    user.

- **Adjacent verifier categories (2026-07-26): watch, don't build.**
  The tooling-landscape research (docs/sdlc-tooling-landscape.md — a
  verified fan-out research pass over DORA 2018/2024/2025, the 2025 AI
  Capabilities Model, the 2026 ROI report, SAFe's CDP and the oracle
  literature) positioned this project's category — deterministic
  verifiers for AI-read/AI-written artifacts — as the delivery
  pipeline's one under-built layer, now externally corroborated: DORA
  2026 names the "verification tax" as "the most immediate barrier to
  ROI", lists "guardrails" among its five systemic keys of adoption,
  and its named mitigations are literally pre-commit hooks paired with
  static analysis. Five adjacent oracle gaps were evaluated. Decision:
  **none is queued** — the Arc E bar applies (build only for a concrete
  user whose need the current tool cannot meet). Recorded so the
  evaluation isn't re-derived:
  - *Diagram↔code conformance* — nearest by asset (the parsed model),
    farthest by scope: requires parsing implementation languages,
    straining the zero-dependency promise. Pull looks like: a user
    asking to gate PRs on model↔code drift.
  - *Oracle quality for AI-generated tests* — strongest external
    evidence (HumanEval+: weak suites overstate AI-code correctness by
    up to 19.3–28.9%), weakest asset fit: nothing here parses test
    suites; this would be a sibling tool, not a rule pack.
  - *Spec/acceptance-criteria linting* — the architecture transfers
    (text artifact → parser → rules → score) but grammar, corpus, and
    calibration start from zero. Pull: a team feeding stories to AI
    asks for a floor.
  - *Prompt/agent-config linting* — the artifact class is forming
    (DORA: 21% of practitioners already store prompts in version
    control) but no convention exists to lint against; any rules would
    be dormant-by-default (GEN006/GEN007 pattern). Earliest, least
    defined.
  - *AI-context/documentation quality* — the bounded version (the
    model set as AI context) is closest to the existing XD family; the
    unbounded version ("all docs") is out of scope by construction.
  - Re-litigate on: concrete pull, a DORA result tying instability
    moderation to verification-capability strength, or outcome-grade
    oracle evidence for non-code artifacts.

- **Markdown-embedded PlantUML extraction (2026-07-26): watch, don't
  build — the demand was measured and isn't there.** A review of the
  vendor/practitioner AI-codegen literature (engineering-layer companion
  to the tooling-landscape research) surfaced one product-shaped
  candidate: extract and lint fenced PlantUML from markdown, where the
  spec-driven ecosystem (GitHub spec-kit, AWS Kiro) keeps its artifacts.
  Instead of waiting for pull, the pull was measured the same day —
  pre-registered decision rules, GitHub code search, repo-level join,
  raw-file inspection (docs/demand-scan-embedded-plantuml.md):
  - Genuine embedded-PlantUML spec content: ≈ 3–8 repos out of ~2,120
    public Kiro spec sets (≈ 0.2%, against a pre-registered 2% bar);
    spec-kit side ≈ zero (3 file hits, none organic on inspection;
    0/25 sampled spec-kit repos contain any `@startuml`).
  - The raw count nominally passed the pre-registered absolute bar
    (64 ≥ 50 files) and failed inspection: 37/61 Kiro hits are
    standalone `.puml` files pumllint lints today, and of the 9
    markdown hits in Kiro spec dirs one confirmed false positive is
    PlantUML inside a test fixture. Raw token counts are not demand —
    the scan's own reliability-vs-validity moment.
  - Mermaid dominates the same directories 76× (`.kiro/`) and 437×
    (spec-kit plan.md); globally, embedded PlantUML-in-markdown (8,068
    files) is 16× smaller than the standalone `.puml` ecosystem
    (131,008) the tool already serves.
  - Side-findings kept: Kiro's PlantUML users co-locate `.puml` files
    inside `.kiro/specs/` — served today, a documentation pattern, not
    a feature; steering/skills files teaching agents to author
    PlantUML corroborate the agent-consumption-recipe candidate
    (since built: docs/agents.md);
    Mermaid support would be a sibling stack (parser, corpus,
    calibration, golden) under the same Arc E bar — recorded, not
    queued.
  - Re-litigate on: a concrete user with fenced diagrams; a
    spec-driven tool emitting or recommending PlantUML in its
    artifacts; a GitLab-side measurement showing material embedding
    (GitLab renders PlantUML fences natively and was outside this
    scan's reach); the global embedded footprint passing the
    pre-registered 10k bar.

- **C4-PlantUML pack (2026-07-27): fit verified, wait for census pull.**
  A fit evaluation (full record: docs/c4-pack-evaluation.md — external
  claims verified against primary sources, behavior measured on v0.23.0)
  confirmed the fit case and bounded the claim:
  - c4model.com's review checklist supplies an externally-authored rule
    spec (title/type/scope/legend; element name, description, technology;
    relationship label, direction, protocol); C4-PlantUML's closed macro
    surface suits the line-oriented recognizer and ships no validation of
    its own; no third-party C4-PlantUML linter found.
  - Measured on v0.23.0: a well-formed container diagram scores
    **Level 1** (zero-modelled-elements cap) and a raw-arrow C4 file is
    **mistyped as sequence** (Level 4, SEQ009 false positives) — current
    output on C4 input is misleading in both directions, not merely
    absent. (The C4_Sequence-include misfire an earlier draft assumed
    does not occur: pure-macro files are never typed sequence — raw
    arrows are the mechanism.)
  - Claim language stays narrow: Structurizr's inspections already check
    description/technology completeness on its own workspaces — the open
    niche is *hand-written C4-PlantUML files* only. Structurizr DSL is
    out of scope by decision.
  - Sizing: largest pack since sequence (argument tokenizer, level
    detection, ~20 rules across base/level-dependent/codegen tiers, plus
    the full Arc C pack bar: corpus ladders, additive golden re-freeze,
    pilot regeneration, ideally an evidence extension).
  - Re-litigate/build trigger: the pilot census (tools/pilot_census.py
    already counts C4 macro calls) showing material C4 usage on a real
    corpus, or a concrete user asking.
  - Evidence extension since run (2026-07-27,
    docs/c4-codegen-detail-experiment.md): a five-rung C4 detail-ladder
    wave measured which spec ingredients move codegen outcomes —
    behavioral content +29 pp executed, annotations +8 pp, companion
    spec cuts judged invention but not executed error on
    canonical-threshold scenarios. Rule-selection implications recorded
    there; this adds selection evidence, not a build trigger.
  - *Ecosystem re-examination (2026-08-27, docs/c4-ecosystem-evaluation.md):
    settlement stands; three claim-language corrections and one trigger
    guard.* The whole ecosystem was assessed rather than the one notation,
    and the dated behavioural claims were re-run at `8fa5339` — samples
    A/B/C reproduce to the decimal (Level 1 98.75 / Level 1 98.75 /
    Level 4 88.96, model set Level 1), so six minor versions of parser and
    typing changes left C4 behaviour untouched and the record is current.
    **Motivation up:** the 2026-07-27 measurement ran the default profile
    only; under the **codegen** profile — the one docs/agents.md tells
    agents to run — a well-formed named C4 container diagram is *silent*
    and scores **100.0 on all six dimensions**, held at Level 1 only by
    cap C4, while the arrow-mixed sibling emits **8 findings, 4 of them
    blockers, and exits 1**, seven of the eight false in C4 semantics.
    The honest description is not "C4 input is uncovered" but "C4 input is
    actively mishandled, and worst under the recommended profile".
    **Demand evidence down:** the census's "C4 macros in 46% of files" and
    its own composition table's "71 of 159 files come from
    plantuml-stdlib/C4-PlantUML's `samples/`+`percy/` gallery" are very
    nearly the same files (recomputed from sources.json; the marker's
    example list names ≥3 files from other repos, so the notation's own
    examples account for at most 70 of the 73). Both numbers are disclosed
    in docs/pilot-census-first-contact.md, in different sections; the join
    is not drawn, and the one sentence reading a build signal off the 46%
    is where it matters. **Trigger guard, the one operational change:**
    before a census dialect marker is read as demand, exclude the
    notation's own repository and vendor sample galleries — the same
    discipline sources.json already applies one level shallower (32
    theme/macro files excluded from that repo as "library code by
    content"). Trigger wording otherwise unchanged.
    *Corrections:* (C1) "nothing checks hand-written C4-PlantUML" narrows
    again — `jqassistant-c4-plugin` parses these files with a custom ANTLR
    grammar for as-is-vs-to-be architecture conformance, so the surviving
    form is "no tool checks C4-PlantUML *modelling quality*" (maintenance
    status unverified; it also gives the 2026-07-26 diagram↔code
    adjacency a named incumbent, corroborating "watch, don't build").
    (C2) "the defect list is externally authored" covers **tier 1 only and
    ~40% of the checklist** — 8 of 21 items are cleanly mechanizable from
    source, 3 partially, and 10 are about rendered colours, shapes, icons,
    arrowheads, border styles and element sizes; tiers 2–3 are this
    project's own design and carry no external authorship. (C3) the market
    boundary moved on the AI axis: Structurizr ships an MCP server
    providing DSL validation, parsing and inspection to agents, and LikeC4
    ships agent skills plus an MCP server — so "nothing gates C4 before an
    agent generates from it" is false for Structurizr DSL as of
    2026-08-27, and still true for C4-PlantUML. That is corroboration of
    the agents.md loop from a vendor roadmap, and a reason N1 (no
    Structurizr/LikeC4 support) is now firmer than in July, not weaker.
    *Position confirmed from a third direction:* Structurizr inspections
    configure severity across four levels and report per finding, LikeC4
    hands semantic rules to Vitest, and Linked.Archi's SHACL conformance
    is binary — three independently built C4-capable validators, three
    stacks, and **none of them grades**. No level, gap report, ratchet or
    aggregate score anywhere in the ecosystem.
    *Recorded, not queued:* re-run the census C4 marker with the
    notation's own source excluded (sources.json carries repo/path/commit
    for all 159 files — converts the bounded statement into a number;
    maintainer self-demand); the second wild sweep weighted toward working
    project corpora the census note already names; the Mermaid-C4
    recognizer note (Mermaid's C4 plugin is deliberately syntax-compatible
    with C4-PlantUML, so a C4 recognizer would largely transfer — the one
    place the Mermaid sibling-stack cost estimate over-states the case,
    though the fence/discovery objection and the failed demand scan stand);
    and the codegen-profile amplification as the sharpened motivation for
    whenever the trigger fires.

- **Prose→model→prose requirements pipeline (2026-07-29): sense, with
  corrections — specified as Arcs G–J, builds gated.** An externally
  authored reassessment (itself reversing an earlier external "nonsense"
  verdict on the round-trip idea) was verified element-by-element
  against this repo (docs/prose-pipeline-evaluation.md). Adopted,
  corrected, and never-build decisions:
  - *Adopted*: the round trip is legitimate **iff the back leg is
    deterministic** (here: parse → verbalize, deterministic by
    construction); the metamodel-conformance gate is the real prize and
    is already shipped (lint/score + codegen profile); k-way model
    diffing is the rigorous ambiguity signal (feasibility measured,
    evaluation Probe B); LLM legs stay human-gated and out of the
    primary path — a stance this repo independently measured (X3/XV1:
    judged-vs-executed r ≈ 0.25 / 0.002).
  - *Corrected*: the reassessment's "textX/pyecore is licence-necessary"
    is overstated — what the EPL/GPL incompatibility requires is
    avoiding the Eclipse MDE stack, and the stdlib satisfies that while
    keeping the zero-dependency promise; textX/pyecore/Lark are recorded
    only as a *lab-tooling fallback* (optional extras door) if a
    purpose-built requirements DSL ever outgrows hand parsing. And the
    verbalizer's substrate is a *projection* (the parser skips unknown
    lines), so an unmodelled-content disclosure is a build requirement
    of Arc H, not a nicety.
  - *Never build*: a prose-similarity round-trip **score** (the round
    trip is a review UI, not a metric); an LLM back leg; free-form
    executable code as the intermediate; AGPL for any service/MCP
    wrapper derived from this codebase; EPL dependencies anywhere in
    the repo (one GPL sdist — product and lab alike).
  - *License posture recorded*: GPL-3.0-or-later was already chosen
    (v0.24.0) and the run-not-linked analysis fits the CLI/CI usage;
    Apache-2.0 deps stay compatible if the extras door is used.
    The public non-relicensing commitment was made 2026-07-29, on the
    owner's go (README § License): never source-available or
    proprietary, never AGPL — the SonarQube/Semgrep rug-pull lesson
    says trust outweighs the license text itself.
  - *Still parked*: a purpose-built EARS-shaped requirements DSL — the
    existing spec/acceptance-criteria-linting settlement stands,
    now enriched by the reassessment's design lessons (EARS's
    lightweight patterns succeeded where SBVR's grammar-less style
    guide failed; any future DSL must be low-overhead and
    hand-parseable first). Re-litigate on: a concrete adopter with a
    requirements corpus, or Arc G/H adoption generating pull for
    structured requirements input.

- **AI-ready specification-stack recommendation (2026-07-29):
  verified — corroborates the plan; the missing layer is per-artifact
  verification; one candidate recorded.** An externally authored
  recommendation on preparing specification artifacts for AI codegen
  (layered mandatory stack, DSL-per-concern, stable-ID traceability,
  repo instruction files, tests as the control) was evaluated against
  this repo's records (docs/spec-stack-evaluation.md). It independently
  corroborates Arc G's ship-first call, the C4 census posture, the
  Mermaid sibling-stack record, the parked purpose-built DSL, and the
  agents.md ask-never-invent covenant — and its sharpest line
  ("diagrams orient, contracts constrain") is corrected by this repo's
  own measurements: constraint-grade vs orientation-grade is a maturity
  level, not an artifact genre (C4 detail ladder +29 pp; the 21.9 pp
  cliff within one artifact type). Its blind spot sharpens the
  positioning claim: every artifact is mandatory to *exist*, only code
  is gated — while the below-Level-2 evidence says ungated upstream
  artifacts are not just insufficient but harmful. Adopted: Arc G
  input/schema refinements; the precedence-of-evidence ladder in
  docs/agents.md. Recorded, not queued: a **sequence ↔ contract
  cross-check** (message signatures against OpenAPI/AsyncAPI
  operations — the XD identity discipline extended across artifact
  classes; the lighter cousin of the diagram↔code conformance item
  above, since the target is machine-readable data, not an
  implementation language). Build trigger: a user with both artifact
  classes in one repo asking to gate drift between them.

- **Obligation & flow checking (2026-07-30): the participant-pair sweep
  is rejected; three decidable designs are recorded, none queued.** The
  originating ask — try all combinations of participants, actors and
  other diagram elements to check completeness of happy vs exception
  flows and edge cases — was assessed in a design spec (off-repo, rev. 3:
  written against `9fd894d`, twice adversarially verified against the
  source, probes executed). Verdict, adopted here:
  - *Enumerating participant pairs and asking "is an interaction
    missing?"* is **rejected regardless of implementation effort**:
    there is no oracle — the complement of a diagram is not a set of
    omissions, so every absent interaction is equally "missing"
    (~100% false-positive by construction). Re-litigate only if someone
    supplies an interaction oracle — which is a declared policy table,
    i.e. the kept reading below, not inference.
  - *Declared obligations* (policy completeness: an `[obligations]`
    table — target selector × failure mode — is the oracle; SEQ110–113
    plus a reported-only ledger) and *architecture conformance*
    (ARC001–003 against a declared `[architecture]` layer table) are
    decidable and specced. **Wait for adopter pull**: a team owning a
    modelling standard confirms the first table rows. When built, the
    specs land in RULES.md — the codegen range's first executable specs.
  - *Structural flow checking* splits in two. **WS3a** — "is any
    exception trace modelled at all?" (SEQ203) and "does an `alt` state
    its alternative?" (SEQ201) — needs only a fragment tree, no trace
    enumeration (proved in the spec), is golden-neutral behind a new
    `flows` profile, and is recorded as a **maintainer product-direction
    option**, honestly labelled: self-demand, not adopter pull. **WS3b**
    — branch-aware call answering (SEQ202) plus the shipped SEQ104's
    path-insensitive pairing (verified: a reply in a mutually exclusive
    sibling branch satisfies linear pairing while no execution path is
    answered) — is **measurement-gated**: prototype branch-aware
    pairing, count SEQ104 verdict flips over corpus + wild tier;
    flips > 0 → golden-diffed SEQ104 fix, flips ≈ 0 → record the latent
    defect in EVIDENCE.md and stay unqueued. Instrument note
    (2026-07-30, from the firing-report chassis): SEQ104 fires zero
    times across the calibration corpus and wild tier, so the flip
    measurement needs the pilot's real corpus or dedicated fixtures —
    corpus replay alone cannot exercise it. Timing note for WS3a: the
    spec is the pilot-conversation artifact; if the modelling-standard
    owner bites, the pilot's calibration week (real diagrams on hand)
    is the natural build window.
  - Parser debt surfaced by the same verification is defect-class, not
    feature work, and ships without pull (v0.26.0): `is_reversed`
    misdirects half-arrows, `x<-` and `<->` (live in the default
    profile via SEQ009); `legend` bodies parse as live source (phantom
    messages and participants); valid `->(10)` delay arrows are dropped
    entirely.

- **Aschenbrenner capability-horizon mapping (2026-08-01): sense, with
  corrections — recorded; nothing queued.** An externally authored
  mapping of *Situational Awareness* (June 2024) onto this project
  against a four-level capability ladder was verified element-by-element
  (docs/aschenbrenner-mapping-evaluation.md). Kept: the artifact-side
  unhobbling frame (whose measured form is the scaffold-resistance
  result — entry-contract pinning does not rescue below-cliff
  diagrams), maximum relevance in the current capability band, and the
  hedge already in these records — declared-policy rules
  (obligations/ARC) are governance instruments that outlive the
  ambiguity-service window, whose value is capability-relative in
  *payoff*, not in decidability. Corrected: two untraceable citations
  ("Orchid"; an AEI median-1-prompt figure) carry no weight until
  primaries are supplied; "Phase 2 fitness harness" misnames the Arc D
  harness (built, not pending); a 2027 trajectory cannot be scored
  falsified in mid-2026. The falsifiable premise is recorded with its
  standing instrument: the gate thesis holds while ambiguity degrades
  generation more than capability compensates — re-measured per model
  generation with the Arc D harness, whose three generators across two
  vendors so far show at most marginal narrowing of the executed
  cliff. Watch trigger: a wave in which the cliff materially narrows
  is the window-closing signal — the response is a reviewed
  repositioning toward the governance packs, never an unattended loop
  (the auto-improvement settlement already covers the actuation side).

- **Model-verification ambitions (2026-08-02): inverted, with one
  keeper — recorded; nothing queued.** An externally authored note
  proposed going "beyond linting into verifying the models themselves"
  (prove interactions deadlock-free / every message matched by a
  return; prove the rule set internally consistent; encode
  well-formedness as a type) with TLA+/Alloy or a rules DSL as
  alternatives, and recommended a Lark/ANTLR grammar + pluggable
  visitor rules + glossary-as-one-rule. Verified element-by-element
  (docs/model-verification-evaluation.md). Verdict, adopted here:
  - *Matching returns* is shipped linting (SEQ003/009/104/108); the
    semantic remainder is the already-specced, decidable SEQ202 (WS3b,
    measurement-gated above). *Deadlock-freedom* is a category error —
    PlantUML defines no concurrency semantics, so the check would
    verify its own invention: the no-oracle shape the obligation/flow
    settlement already rejects. Honest verification is cross-artifact
    (trace, XD, the recorded seq↔contract item) plus the Arc D
    measurement — never intra-diagram proofs over imposed semantics.
  - *Rule-set consistency*: pairwise is the weak property; joint
    satisfiability is witnessed constructively by the corpus's clean
    probes under golden enforcement, with no parallel Alloy
    formalization to drift. Corpus-firing reports cover surprising
    interactions; Hypothesis-in-tools/ is the extras-door form if
    adversarial instance-finding is ever wanted.
  - *Well-formedness as a type* is the anti-goal: representable
    ill-formedness is the product (findings, levels, ratchet, fix).
    Parse-don't-validate belongs downstream of the gate, never in it.
    ARIS's own conventions checking is rules-over-a-model — the
    ARIS-parity path here is the gated obligations/ARC packs.
  - *Grammar (Lark/ANTLR)*: re-litigates the settled lab-fallback
    shelf without new evidence; conflicts with zero-dependency and
    parse-tolerance requirements; buys only unpulled LSP features.
    Reopen only for a concrete LSP adopter, and evaluate span-tracking
    in the existing recognizer first.
  - *Keeper*: a **glossary/approved-term rule** — declared names
    resolved against a project term inventory (the trace-inventory
    pattern applied to names; dormant until configured, GEN006/GEN007
    style). Trigger: an adopter or the pilot's conventions workshop
    supplies a real term list — until then, building it would
    manufacture a convention, not check one.

- **SDD + generation-manifest recommendation (2026-08-10): evaluated —
  direction corroborated, specifics stale; two candidates recorded,
  nothing queued.** An externally authored recommendation (spec-driven
  development with PlantUML requirements as first-class inputs; a
  compose-style manifest + lockfile + per-run records governing the
  generation toolchain; this tool as input gate and output assertion)
  was verified element-by-element against the working tree
  (docs/sdd-manifest-evaluation.md). Its foundation proposals already
  ship — `pumllint trace` (v0.25.0), config/profiles, schema-pinned
  JSON + exit codes; its example "novel contractual rules" are shipped
  rules (UC001, ACT003, SEQ105/107, GEN007) or specced-and-gated packs
  (obligations, flow); its public-demand premise is contradicted by
  the embedded-PlantUML demand scan above; its compiler analogy is
  corrected to **attribution, not reproducibility** (snapshots retire;
  generation is nondeterministic even pinned). Independent
  re-derivation of the Arc G–J shape without repository access is
  recorded as another external convergence (alongside the spec-stack
  and model-verification evaluations). Recorded, not queued: a **portable run-record/manifest
  format** (a pilot-repo artifact formalizing what the lab already
  practices; if a real pilot stabilizes one, it becomes the first
  observed convention for the prompt/agent-config-linting adjacency
  above — re-examine that trigger then, build nothing before); a
  **model→spec change-impact design** (invalidation semantics over
  `trace`'s link table — write only after a real diagram-edit event
  has flowed through a pilot pipeline). The scope-threshold rule it
  asked for is written (pilot charter, the phase-4 scope test).
  Triggers unchanged; the census remains the next action.

- **Two-stage external project review (2026-08-11): evaluated — the
  most accurate external assessment this repository has received; both
  repo-facing defect findings real and previously unrecorded; three
  doc-hygiene and two wave candidates recorded, nothing queued.** An
  externally authored two-stage review (chat-authored, live web access
  to the raw repository files; stage 1 written at the W1-results
  state, stage 2 after the W2–W4 results and before any W5 run) was
  verified claim-by-claim against the md record
  (docs/external-review-evaluation.md). Roughly forty quoted figures
  across W1–W4, the C4 ladder, the sequence cliff and the
  judge-validity record all trace — zero misquotes. The two defect
  findings, both verified: the **Level-5 naming contradiction**
  (scoring.py and the score-schema enum name the level
  "Generation-ready" while the settled claim language says
  "method-convention complete" and agents.md states the level is
  "deliberately not called 'generation-ready'" — a sentence that is
  false while the name stands), and **EVIDENCE.md's unstated
  boundary** (zero stack-programme content, the boundary declared
  nowhere in the file). The review's capstone "target architecture"
  and closing-lesson claims are graded in the evaluation: two
  pipeline boxes gained measured rationales (mechanical conflict
  surfacing per W2; context minimization per W4), the carrier lineup
  and two further boxes stay hypothesis, the agentic keystone is
  untested until W5, and the measured author/decision loop appears in
  no box. Recorded, not queued: **reconcile the Level-5 name** (a
  rename is a public-contract change — schema enum, scoring.py,
  tests, docs sweep, regenerated example report — taking its own
  deliberate decision; the minimum honest fix is agents.md's
  sentence); an **EVIDENCE.md scope paragraph** (doubling as the
  placeholder for the charter §7 consolidated document); **case-for
  problem-statement tightening**; and wave candidates **W3b**
  (carrier × prompt-frame factorial) and **A3 decomposition**
  (contract information classes), each under charter §10 discipline
  if ever queued. *Dated update, 2026-08-11: the A3 decomposition
  RAN as W1b under full charter discipline (draft → adversarial pass,
  17 findings all adopted → freeze → owner go "freeze and go" →
  scored run, $10.89 of $30). Verdict: the decision tables carry the
  bundle in both directions (+40.9 pp add-one / +12.1 pp LOO,
  generators concordant, invention cut localized); the OpenAPI
  mirror held validation bounds at 0.0 loss; the three other
  components measured as in-bundle dilution (removal improved
  results 10.6–21.2 pp). Attribution is suite-relative — scoping in
  the record: stack_experiment/W1B_PREREGISTRATION.md § Results.
  W3b remains recorded, not queued.* *Staged, same day: W3b's
  pre-registration was drafted and independently adversarially
  verified (14 findings adopted: 6 major, 8 minor) — held pre-freeze
  in stack_experiment/W3B_PREREGISTRATION.md; driver build, freeze
  and owner go deliberately pending.* *Ran, same day ($13.72,
  84/84 runs, full §10 cycle): the stored-frame carrier ordering
  reproduced exactly (anchor delta 0.0) but is partly frame-carried
  — YAML intrinsic (frame caveat shed), controlled English scoped
  to the PlantUML-framed harness, code-stub/Mermaid stored-frame
  deficits unreproduced beyond equivalence (no re-scoping licensed);
  the surprise at full prominence: carrier-native frames HURT
  (−10.6…−18.2 pp pooled on three carriers; E2a/E2b/E5 failed,
  per-generator language mandatory — the stored-frame ordering is
  opus-borne); E3 split (stored 0/3 reproduced, neutral 2/3 are
  degenerate fragments, native 0/3); E4/E6 confirmed. Record:
  stack_experiment/W3B_PREREGISTRATION.md § Results.* *Dated
  addition, 2026-08-12 — two candidates opened by W3b's results,
  recorded, not queued: a **carrier-deficit reproduction wave**
  (code-stub's and Mermaid's stored-frame deficits did not reproduce
  beyond the equivalence bar on the second occasion, so G3 blocked
  any re-scoping and the cross-occasion instability is now measured
  once; a third measurement at higher n per generator would resolve
  it — queue only if a decision comes to hang on those two carriers'
  standing W3 numbers, which today none does: the pilot mandates
  PlantUML and the records carry the non-reproduction notes); and a
  **frame-robustness wave** (W3b measured carrier-native frames
  HURTING, −10.6…−18.2 pp pooled on one occasion, via two distinct
  mechanisms — opus output-contract collapse into non-code
  fragments, haiku compiling-but-worse; candidate design: frame ×
  phrasing-variant robustness at fixed carrier, to establish whether
  the harm is phrase-specific or frame-class-general — queue only if
  any adopter-facing guidance is about to recommend prompt-frame
  wording; the current records deliberately recommend none). Both
  under charter §10 discipline in full if ever queued.* The reviewer's platform items (BPMN/DMN carriers,
  cross-spec verifier, context compiler, coverage metric, domain
  benchmark) stay with the adopter programme — not this repository's
  scope. Priorities convergent: W5 next, as the charter already
  records. *Dated update, same day: W5 ran hours later — the cliff
  survived agency (§8.4 did not fire), compensation was
  visible-bounded, below-cliff artifacts unrepaired at k ≤ 2; the
  evaluation's "untested keystone" grading carries its dated note in
  place (record: stack_experiment/W5_PREREGISTRATION.md § Results).*
  *Decision (2026-08-11, owner): Option A — Level 5 renames to
  "Method-complete" at the next release. An output-contract change,
  carried with full release-note prominence: schema enum
  (score.schema.json), scoring.py, tests + BDD feature, docs sweep,
  regenerated pilot artifacts; the agents.md "deliberately not
  called" sentence correction folds in. The EVIDENCE-scope and
  case-for candidates remain recorded, undecided.*
  *Executed (2026-08-11, owner ask): the EVIDENCE.md scope paragraph
  is in — the boundary now stands at the top of the file, pointing at
  the wave pre-registrations' § Results, the charter synthesis and
  docs/minimum-sufficient-stack.md (shipped since the candidate was
  recorded, so the note is a pointer, not a placeholder). The
  case-for candidate remains recorded, undecided.*
  *Executed (2026-08-11, owner ask): the case-for problem statement
  is tightened — "no automated check we could find", pointing at the
  survey section and its honesty note; the SDD-checks sentence gains
  the "those tools themselves provide" precision. With this, all
  three doc-hygiene candidates from the review are closed or decided
  (L5 rename: decided, next release; EVIDENCE scope note: in;
  case-for: tightened).*

- **Knowledge graph / graph engineering (2026-08-26): no — the graph
  already exists and externalizing it fails on scale; two keepers
  recorded, nothing queued.** The question (define a knowledge graph
  for pumllint in the graph-engineering sense; assess
  sense/nonsense/fit/gap/SWOT for AI-assisted development and rule-set
  extension/validation) was run through the house triage against
  `3cb39ff` (full record: docs/knowledge-graph-evaluation.md; repo
  claims executed, library licences verified against PyPI, external
  literature characterized and non-load-bearing). Verdict:
  - *The premise is already satisfied.* `pumllint/model.py` is a
    labelled property graph; **14 of 51 rules are graph queries** — 9
    intra-diagram algorithms (CLS004 DFS cycle search, STA002
    in-degree, UC001 degree-zero, UC003 one-hop neighbourhood, SEQ002
    set difference over edge endpoints, SEQ009 reverse-edge existence,
    SEQ104/108 matching and stack replay, SEQ107 containment) and the
    5 XD rules, a
    global entity-resolution join with a `authoritative` golden-record
    pin. `pumllint trace` is a bipartite requirement↔diagram graph
    reporting all three directions.
  - *Scale refuses the infrastructure.* The 174-diagram wild corpus is
    **950 nodes+edges** (census 0.6 s); a 15-diagram codegen lint
    *including* the cross-diagram join is 3.0 ms. Graph engines exist
    for 10⁶–10⁹. The zero-dependency agreement closes the product path
    regardless; licensing does **not** bind here (rdflib BSD-3-Clause,
    pyshacl Apache-2.0, networkx BSD-3-Clause, neo4j driver
    Apache-2.0, kuzu MIT — verified), unlike the EPL case.
  - *Never build*: a graph store/triple store on the product path; any
    LLM-driven graph extraction anywhere on it (deterministic-path
    agreement + the measured invention failure); OWL/SHACL as the rule
    engine (the well-formedness-as-a-type anti-goal, plus closed-world
    validation over a tolerant projection); missing-edge inference (the
    participant-pair sweep's no-oracle shape with a query language);
    graph-derived metrics in the score without a charter §10 wave.
  - *Rule-set validation splits three ways and the graph loses all
    three*: catalog integrity is already enforced (`@register`,
    test_catalog.py, test_schema.py); rule interaction is
    data-dependent and `tools/corpus_firing.py` already answers it in a
    way no ontology could (SEQ102/104/107/109 fire zero times); and
    coverage occupancy is a pivot table. Rule *extension* is bottlenecked
    on under-specification (Arc F), which a graph does not touch.
  - *Recorded, not queued*: (1) a **repository link-integrity check**
    (`tools/link_check.py`, stdlib, lab machinery) — the `trace` pattern
    over the repo's own prose: dangling doc links, cross-file citations,
    rule IDs named in prose, level/dimension names. Honestly labelled
    **maintainer self-demand, not adopter pull** (WS3a's label), with
    one demonstrated failure behind it: the Level-5 naming contradiction
    a human reviewer found on 2026-08-11. (2) A **rule-coverage
    occupancy table** (documentation candidate). (3) The **DIM-AMB
    coverage residual** — DIM-AMB carries no rule for activity or
    use-case diagrams, so a 0.25-weight dimension scores a vacuous 100
    and the Level-4 ambiguity gate passes for free; measured, the same
    vague content (`do stuff`/`TBD`/`...`) is Level 2 / DIM-AMB 0 as a
    sequence diagram and Level 5 / DIM-AMB 100 as an activity diagram.
    Issue #35 / `feb8789` already caps the *level* half via the opt-in
    `c7_requires_applicable_rules` (→ Level 4); the *dimension* half is
    the residual. Same family as the C6 zero-element cap and the
    syntax-gate disclosure; any fix is a scoring change and takes its own
    decision and golden re-freeze. (4) **"Cross-artifact identity"** as
    the arc name for the three already-recorded items (sequence↔contract,
    glossary/approved-term rule, model→spec change-impact) — naming and
    sequencing only; each keeps its own trigger.
  - Re-litigate on: an adopter model set too large for one in-memory
    batch (10⁵–10⁶ elements, against 950 measured today); a concrete
    cross-repository identity ask the recorded sequence↔contract and
    `trace` items cannot serve; a pilot census showing a materially
    denser entity graph; or outcome-grade evidence that graph retrieval
    beats a maintained index for this class of governance record.

- **Linked.Archi ecosystem (2026-08-27): adjacent and complementary — no
  build, no dependency; the one fit worth having already ships. Two
  candidates recorded, nothing queued.** The question (investigate
  `meta.linked.archi` — RDF/OWL semantic layer linking architecture
  artefacts — and its ecosystem, then grade the boundaries / overlap /
  fit / gap / sense / nonsense against this roadmap) was run through the
  house triage against `3d64176` (full record:
  docs/linked-archi-evaluation.md; repo claims executed, Linked.Archi
  claims read from its published documentation with page URLs, its
  tooling **not** executed — the converters' source project answered 404
  on the documented GitLab path and 403 on the project page from the
  evaluation environment). Verdict:
  - *The categories do not compete, and both projects say so.*
    Linked.Archi is an integration layer — six Java converters lift
    ArchiMate, BPMN, PlantUML, Structurizr/C4, Backstage and LeanIX into
    one RDF graph, SHACL validates it, `rdf2docs`/SPARQL consume it — and
    its declared non-goal is "not a replacement for your existing tools",
    naming PlantUML. pumllint gates the source artefact before
    conversion. **The one fit worth having (pumllint in a producer repo,
    before `plantuml2linkedarchi convert`) needs no code on either side:
    it is the shipped Action, hooks, exit codes and `--min-level`.**
  - *The complementarity is structural.* SHACL conformance is binary by
    the spec and by RDF4J (their validation page says so), so vague
    labels, elided guards, prose-where-a-signature-belongs and unowned
    diagrams convert cleanly and pass. And their converter is a tolerant
    projection too — gates and exogenous messages "absent from the
    graph" — so the closed-world-over-a-projection hazard the
    knowledge-graph settlement predicted is now **observed in a second,
    independently built pipeline**. That strengthens the 2026-08-26
    never-build list rather than disturbing it; none of its four
    re-litigation triggers fires, because all four are about an adopter.
  - *One attractive claim withdrawn, and it is the decision-relevant
    one*: pumllint's SEQ102 role-type discipline does **not** protect the
    converter's typing. Its page states every sequence participant
    becomes `uml:Lifeline` "whichever keyword asked for it", the keyword
    republished as `schema:keywords` — "a plain label, not a type claim"
    — and a user-written `<<stereotype>>` "is not read by this
    converter". The two notions of *type* are not commensurable on the
    corpus's dominant diagram type (61 of 174 wild diagrams); any
    "align the vocabularies" proposal starts from there. (The
    type-mapping page reads differently on this point; flagged, not
    resolved — the source was unreachable.)
  - *Never build*: SHACL/OWL as the rule engine over converted RDF (N1/N2
    — binary conformance deletes the graded product); a vendored or
    bundled ontology on the product path; findings or scores emitted as
    graph properties *for querying quality* (the graph-derived-metrics
    refusal with a different transport); any alignment of participant
    kinds to `uml:Lifeline`.
  - *Recorded, not queued*: (1) **`'!la-` extension data as a governance
    carrier** — measured false negative: a file carrying
    `'!la-link OrderService am:realizes kg:REQ-4711` and
    `'!la-data OrderService arch:conceptOwner kg:TeamPayments` is
    reported by GEN006 as having no ownership tag, by GEN007 as having no
    requirement reference, and by `pumllint trace` as an *unlinked*
    diagram against an *uncovered* requirement, because
    `prose_directives()` carries title/header/footer/caption/note and
    PlantUML comments are not directives. One seam, one config key, a
    deliberate golden re-freeze (annotated files stop losing DIM-TRC).
    Honestly labelled *externally-authored convention, zero observed
    users here* — the C4 argument, not the glossary argument. Trigger: an
    adopter or pilot corpus using the annotations, or a second consumer
    of the same convention. (2) The **component-diagram typing
    residual** — measured A/B on the same architecture: a plain component
    diagram is `unknown`/0 elements/**Level 1** (C6 cap holds, honest),
    and adding one `database "…" as DB` line types it *sequence*, counts
    1 element, escapes the cap and reports **Level 3 (Disciplined)** with
    no component, package or relationship read. Same family as C6, C7,
    the syntax-gate disclosure and the DIM-AMB residual; any fix is a
    scoring change with its own decision and re-freeze. Trigger: the
    Arc C component pack being built, or a corpus showing the pattern is
    common. *Superseded 2026-08-27 by the ArchiMate entry's
    candidate 1: the same honesty-cap escape, characterized by token
    across three notations and two mechanisms, and generalized out of any
    one notation.* (3) An **RDF/Turtle reporter** — feasible and stdlib-shaped,
    refused today because `-f json` plus the shipped schema already
    serves an RDF-native consumer without importing another project's
    versioning; trigger is an adopter who tried that route and can say
    why it was insufficient. (4) The one-sentence positioning answer
    ("Linked.Archi converts and conforms; it does not lint"),
    documentation candidate only.
  - *Supply-chain read, recorded because any dependency would need it*:
    documentation public, extensive and per-asset versioned; **no overall
    licence statement found** for the ontologies or the tools (EDGY
    content is CC BY-SA 4.0); no named maintainer or organisation on the
    pages read; source repositories unreachable from the evaluation
    environment. Fine to read and reason about — not yet a thing to
    depend on. Irrelevant while nothing is vendored; a precondition, not
    a trigger.
  - Re-litigate on: an adopter or pilot organisation running an
    RDF/SHACL EA pipeline with PlantUML producers (fires candidate 1, and
    probably 3, with observed friction instead of assessed fit); a
    concrete cross-repository identity ask arriving through such a
    pipeline (the standing 2026-08-26 trigger, now with a plausible
    source named); the converter gaining severity-graded or
    coverage-aware validation; or a census meeting a corpus where
    component diagrams are material.

- **ArchiMate ecosystem (2026-08-27): no — no pack, no reader, and not
  wait-for-pull; one general defect-class candidate recorded, which is not
  an ArchiMate item.** Third in the week's ecosystem series (full record:
  docs/archimate-ecosystem-evaluation.md; repo claims executed at
  `e1d5862`, external claims read from published documentation, no
  ArchiMate tool executed, no GitHub repository read). Verdict:
  - *Refused on the artefact, not on demand — the distinction that
    separates this from the C4 settlement.* ArchiMate models live in
    Archi's `.archimate` files or the Open Group Model Exchange XML; the
    `.puml` is a **rendering exported from a view** (the circulated jArchi
    `PlantUML-V2G`/`V2NG` scripts emit one file per view, and MCP servers
    now generate the same class of file from agent prompts). A finding in
    a regenerated artefact cannot be durably acted on, so an adopter would
    not flip this the way one flips the C4 gate.
  - *Refused a second time on the rule spec.* ArchiMate's
    externally-authored spec is a **legality metamodel** — the normative
    Appendix B relationship tables, "mainly intended for tool
    implementation", plus derivation rules DR1–DR8/PDR1–PDR12. That is the
    well-formedness-as-a-type anti-goal (2026-08-02) seen from the far
    side: every modelling tool and every ArchiMate MCP server enforces it
    at authoring time, making it unrepresentable rather than checkable —
    which for a formal legality metamodel is the *right* design. It is also
    the relationship-legality boundary the Arc C XD item already flagged.
  - *Never build*: an ArchiMate rule pack over `.puml`; relationship-legality
    or derivation rules from the ArchiMate tables; a reader for `.archimate`
    or Model Exchange XML (refused on identity — the stdlib has an XML
    parser, so dependencies are not the objection; a second artefact class
    is a second product with its own corpus, calibration and golden
    contract).
  - *The measurement is the yield, and it generalises past ArchiMate.*
    PlantUML's native `archimate` keyword is **not a type marker** and its
    relationships are arrows. Measured: a 5-element/4-relationship model is
    read as **2 implicit lifelines and 1 message**, typed `sequence`, scored
    **Level 4 (Precise) — 93.33/100** with a false SEQ009; under the codegen
    profile **4 findings, 2 blockers, exit 1**, both blockers telling the
    author to declare participants that *are* declared. Characterized by
    token: a file with **no recognized type marker** is typed `sequence` by a
    single **undecorated** arrow — `->`, `-->`, `..>`, `--` (the latter two
    being ArchiMate realization and association) — whose two endpoints plus
    one message make exactly the 3 elements needed to escape cap C6 and clear
    the Level-4 floor. Direction-hinted (`-up->`, `-down->>`) and
    both-ends-decorated (`*-down-`) arrows are not read, so those files stay
    honest at Level 1. A `class` keyword types correctly, because it *is* a
    marker. The Archimate-PlantUML stdlib macro dialect is honest
    (`unknown`/0 elements/Level 1), like C4's macro form.
  - *This closes a defect class across three notes.* C4 sample C (raw
    arrows → `sequence`, Level 4, 88.96), the Linked.Archi component probe
    (one `database` keyword → `sequence`, Level 3, 100), and this
    (one undecorated arrow → `sequence`, Level 4, 93.33): three notations,
    two escape mechanisms, one honesty cap. No rule misbehaves — every rule
    does what its catalog row says and the sequence recognizer is doing its
    documented job on a file nothing else claimed. It is a
    **typing-confidence** gap, belonging beside C6, C7 and the syntax-gate
    disclosure.
  - *Recorded, not queued*: (1) **typing-confidence disclosure or
    type-marker widening** — the one real candidate and notation-general;
    two shapes, both scoring changes needing their own decision and a
    deliberate golden re-freeze: widen the type-marker set so declaration
    keywords like `archimate` type a file `unknown`, or make cap C6
    sensitive to fallback typing (all participants implicit, no declaration
    line) and disclose it as the syntax gate does. **Maintainer self-demand
    with a measured defect behind it** (the WS3a / link-integrity label).
    **Supersedes the Linked.Archi entry's component-diagram residual** —
    same class, different mechanism. No trigger: it awaits a decision, not
    demand. *Amended 2026-08-27 by the D2 entry: the class has
    a **second silencing mechanism** — a zero-declaration foreign-syntax
    file reaches Level 4 (Precise) 99.17 with only GEN001, because SEQ001's
    `only_if_any_declared` default (correct, and not a defect) withdraws the
    last objection. Any fix must be validated against that case or it
    repairs the loud instances and leaves the quietest one.* *Amended again 2026-08-27 by
    the Ilograph entry: the class has a **second degradation mode**. Foreign
    *diagram* syntax is dropped by the parser; foreign *data* syntax is
    **manufactured into content** — YAML's list dash is read as a PlantUML
    arrow, keys become participants, values become labels — and the
    composite **rises with volume** (99.44 → 99.82 across 3→40 resources,
    Level 4 throughout). Any fix must be validated against a YAML-shaped
    file as well as a foreign-diagram-shaped one.* (2) The **generated-`.puml` hazard** — exported ArchiMate views
    score Level 4 today, so a pipeline gating an agent loop on pumllint gets
    a passing verdict on a diagram the tool did not read; the consequence a
    user would actually meet, and candidate 1's motivation. (3) **Archi's
    missing CI validation gate** — its Model Validator is a workbench
    feature and command-line validation appears to be a standing feature
    request, with users asking for a pipeline gate; recorded explicitly as
    **not this project's** (the ecosystem's path is jArchi + ACLI) so a
    later reader does not mistake it for an opening. Status unverified.
  - *Position, fourth ecosystem running*: nothing in ArchiMate produces a
    maturity level, gap report or ratchet — as with Structurizr, LikeC4 and
    Linked.Archi. But here it is also **unreachable**, because the
    ambiguity dimension needs the model and the `.puml` is a picture of it.
    The agent-strategy triple completes usefully: LikeC4 prevents by
    instruction, Structurizr verifies (the agents.md shape), ArchiMate
    prevents by construction. Prevention beats verification wherever the
    constraint is formal enough to encode in an API — which is exactly true
    of relationship legality and exactly false of what DIM-AMB measures.
    That line is the sharpest scope statement the three evaluations produced.
  - Re-litigate on: evidence that *hand-authored* (not exported) ArchiMate
    PlantUML is a real population — the only load-bearing premise, and the
    2026-08-27 census exclusion rule applies in full (a sample gallery is
    not a population); PlantUML gaining first-class ArchiMate model
    semantics that make the `.puml` an artefact of record; or an adopter
    whose ArchiMate models live in PlantUML only, with no upstream tool.

- **BPMN ecosystem (2026-08-27): no, on four independent grounds — and
  the most useful of the four ecosystem evaluations, because what it
  returns is convergent validation of the rule catalog rather than a
  market judgment.** Fourth in the week's series (full record:
  docs/bpmn-ecosystem-evaluation.md; repo claims executed at `eee24ac`,
  external claims from package registries and vendor docs, no BPMN tool
  executed, no GitHub repository read). Two prior records stand unchanged
  and this note answers the question they left open — the 2026-08-11
  review's BPMN/DMN carrier proposal (graded *hypothesis*) and its
  platform items (recorded *adopter programme, not this repository's
  scope*): they fail on merit as well as on ownership. Verdict:
  - *(1) No artefact.* PlantUML has no BPMN diagram type with BPMN
    semantics — the stdlib carries BPMN icons and sprites, and native
    support appears to be a long-standing open request (characterized,
    not verified). `.bpmn` is OMG XML, never discovered, correctly warned
    about, exit code unmoved.
  - *(2) No gap.* **`bpmnlint` already exists and is architecturally the
    same product**: `.bpmnlintrc` with `extends`/`rules`, three named
    presets (`all`/`recommended`/`correctness`), `off`/`warn`/`error`
    severities, a `bpmnlint-plugin-{NAME}` surface, a CLI reporting
    `✖ 6 problems (6 errors, 0 warnings)`, and live feedback in the
    modeler via `bpmn-js-bpmnlint`. 27 rule files, two of them
    infrastructure — ~25 rules against this project's 51.
  - *(3) No generation step to gate — the structural ground, and the one
    an adopter cannot dissolve.* C4/ArchiMate/UML diagrams describe
    something a human or agent then implements; a `.bpmn` file **is** the
    implementation, deployed to Zeebe/Flowable and validated by the engine
    at deploy time. EVIDENCE.md's measured claim is *about a generation
    step*; BPMN has none. A defective BPMN file yields a deploy failure or
    a stuck token, not bad generated code.
  - *(4) Measured evidence against the remaining fit.* W3 measured the
    nearest analog to an enterprise machine format — structured YAML at
    fixed information — at **−30.3 pp pooled / −66.7 pp flow-sensitive**,
    with the strong generator non-compiling 3/3, the only non-compiles of
    the single-shot W1–W4 programme. docs/external-review-comparison.md
    already called that "a warning shot for feeding raw enterprise machine
    formats (BPMN XML et al.) to generators".
  - *Never build*: a BPMN rule pack in any form, over `.bpmn` or over
    PlantUML (a pack over PlantUML would have to invent the notation it
    checks — convention-manufacturing in its purest form); a BPMN XML
    carrier arm added without a pre-registered wave under charter §10.
  - *The yield: convergent validation nobody solicited.* `bpmnlint` was
    built for a different notation on a different runtime by people with
    no contact with this project, and converged on the same architecture
    **and the same rules**. `start-event-required` = ACT001,
    `end-event-required` = ACT002, `conditional-flows` = ACT003/SEQ007,
    `label-required` = SEQ005/STA003/CLS003, `no-disconnected` =
    UC001/SEQ002/STA002, and — the striking one — the
    `no-implicit-start`/`-end`/`-split` family is SEQ001/SEQ010/SEQ101's
    principle under another name: relying on the tool's implicit behaviour
    is an ambiguity hazard, so declare it. Measured, not just name-read: a
    PlantUML activity diagram carrying `bpmnlint`'s three foundational
    defects returns ACT001 + ACT003 ×2 + ACT002, exit 1; the clean version
    scores Level 4 / 100. Divergences are explained by the artefact, not
    taste — `bpmnlint` has layout rules because BPMN carries geometry,
    pumllint has an ambiguity dimension because its artefact feeds a
    generator. **Caveat recorded in the note: the mapping is read from
    rule names, rationales and this catalog, not from paired runs; a
    paired run would need a Node toolchain and a matched corpus that does
    not exist.**
  - *Fifth ecosystem running with no grader.* `bpmnlint` reports raw
    problem counts with severity breakdowns and stops — no level, no
    dimension weighting, no gap report, no ratchet, no aggregate.
  - *The agent-strategy quadruple completes, and BPMN supplies its most
    distant corner*: LikeC4 prevents by instruction, Structurizr verifies
    (the agents.md shape), ArchiMate prevents by construction, **BPMN
    contains** — Camunda's Processes MCP Server exposes deployed processes
    as tools an agent calls, so the model orchestrates the agent rather
    than being consumed by one. Which of the four an ecosystem has chosen
    predicts the fit better than anything else these evaluations measured,
    and is far cheaper to ask.
  - *Recorded, not queued*: (1) **the ACT-pack positioning note** — the
    ACT pack already implements what `bpmnlint` treats as foundational,
    for teams who sketch processes in PlantUML rather than adopt a BPMN
    toolchain. **Claim language, not a feature, and gated on a correctness
    precondition**: the 2026-08-26 DIM-AMB coverage residual (activity
    diagrams carry no ambiguity rule, so a vague process scores a vacuous
    100 on a 0.25-weight dimension) must be addressed first, or the claim
    overstates; any wording must say "activity diagrams, not BPMN" in the
    same breath. This is the first ecosystem where the positioning risk
    exceeds the build risk. (2) The **convergence record** itself, worth
    citing when the catalog's design is questioned. (3) A **fourth
    instance** of the type-fallback defect class — a BPMN-ish sprite
    sketch (`rectangle` + `-->`) types `sequence` at Level 4, 91.0; no new
    candidate, the ArchiMate entry's candidate 1 covers it, recorded so the
    instance count is not re-derived.
  - Re-litigate on: PlantUML gaining a BPMN diagram type with real BPMN
    semantics (the only thing that creates an artefact); a measured wave
    establishing that a machine interchange format beats a diagram carrier
    for the model→code hop (W3 points the other way and W3b showed carrier
    intuitions travel badly); or an adopter running PlantUML activity
    diagrams as process documentation of record and asking for flow rules
    beyond ACT001–006 — which would also make the DIM-AMB residual urgent.

- **UML ecosystem (2026-08-27): no — no conformance mode, no XMI reader, no
  repositioning; two inward-facing candidates recorded, neither queued.**
  Fifth and last of the week's series, and the only one whose yield points
  inward: UML is the ecosystem this artefact belongs to by name and not by
  substance (full record: docs/uml-ecosystem-evaluation.md; produced by a
  14-agent fan-out — five research dimensions each followed by an adversarial
  verifier, three repo probes, a completeness critic; 677 tool calls.
  **All five verifiers returned "refuted"** and every correction they forced
  is carried in the note rather than the original wording. No ArchiMate/UML
  tool executed; no GitHub repository read, which cost real coverage). Verdict:
  - *Three layers, one shared.* UML defines a metamodel — 242 metaclasses,
    449 metaclass-owned invariants (425 with OCL bodies), and Clause 2 makes
    validating them a conformance requirement. PlantUML borrows the
    **notation** and implements none of it: its 607-page Language Reference
    Guide has 0 occurrences of "metamodel", "semantic", "well-formed", "OCL"
    and "XMI", and 1 of "conform" (arrowhead shape). pumllint builds its own
    typed model behind that notation. Only the notation is common.
  - *Measured, not asserted.* Against the official server and
    `plantuml-1.2026.7.jar`, PlantUML renders — and `--check-syntax` exits 0
    on — mutual inheritance, a 3-way generalization cycle, self-generalization,
    two transitions out of the initial pseudostate, and an actor—actor
    association: violations of `no_cycles_in_generalization` (§9.9.4.8),
    `initial_vertex` (§14.5.6) and `Actor::associations` (§18.2.1.4). Its FAQ
    concedes it: "it does not restrict the creation of inconsistent diagrams —
    such as mutual inheritance between two classes. Consequently, it functions
    more as a drawing tool rather than a modeling tool." That sentence names
    **exactly the defect CLS004 detects** — a better warrant for the rule than
    the OMG spec.
  - *Claim language audited clean, which is itself the finding.* 59 bare-"UML"
    tokens repo-wide; only 3 in product-facing surfaces and all 3 are the same
    CLS004 claim (README.md:267, RULES.md:1545,
    pumllint/rules/class_/structure.py:105); a regex for
    lint/check/validat/verif/enforc/conform/comply within 25 chars of a bare
    "UML" returns **nothing** repo-wide (re-run and confirmed empty); no OMG /
    ISO 19505 / "UML 2.5.1" in README, RULES, SCORING, EVIDENCE, action.yml or
    the package source; no UML claim reaches users at runtime; 1 of 42
    rationales appeals to UML. Nothing to correct. Related: the prose-pipeline
    settlement's "metamodel-conformance gate" means pumllint's own typed
    dataclasses, as that same note states — not the OMG metamodel.
  - *The catalog is 86.3% not-UML.* Rule-by-rule: **7 of 51** are UML
    well-formedness in disguise and only **3** correspond to an actual OCL
    invariant (CLS004; STA001 in half — UML allows *at most* one initial
    Pseudostate, pumllint requires exactly one; UC003). 27 are hygiene /
    convention, 11 ambiguity / prose quality, 6 readability budgets. The other
    four A-rules (SEQ003, SEQ004, SEQ108, ACT004) **could not** be OCL
    invariants — an unclosed `alt` or an unpaired `activate` is unrepresentable
    in UML's abstract syntax; they are concrete-syntax repairs, re-establishing
    at text level what a metamodel gets structurally.
  - *Legality picture, corrected by the adversarial pass.* UML has no
    consolidated relationship-legality matrix, but it is **not** true that it
    enumerates nothing: 17 of the 25 Relationship metaclasses have ends typed
    narrower than NamedElement (Include UseCase→UseCase, Generalization
    Classifier→Classifier, …); only Dependency and its subtypes Abstraction /
    Realization / Usage have unrestricted ends. The nearest ArchiMate-table
    analogue is `InformationFlow::sources_and_targets_kind` (13 permitted
    metaclasses per end). So the difference from ArchiMate is one of *form* —
    typing the metamodel vs enumerating a matrix. Also corrected: UML's
    constraint density tracks **execution semantics**, not architecture
    (Actions 155, Activities 50, Interactions 49, StateMachines 47 vs
    Deployments 4, UseCases 8; StandardProfile's 33 stereotypes carry 0), so
    UML is thinnest exactly where this tool's users work. And "the formal layer
    is unvalidated" narrows to the two defects OMG issue OCL25-217 names, both
    reproduced in the omg.org file — a balance scan found 0 of 650 OCL bodies
    unbalanced, which is evidence *for* partial validity.
  - *Never build*: UML OCL invariants as a rule pack (the
    well-formedness-as-a-type anti-goal at scale, over a denominator mostly
    unexpressible in PlantUML); an XMI or `.uml` reader (second artefact class,
    refused on identity — and PlantUML's own FAQ says of XMI "Work is in
    progress"); any repositioning toward "UML linter" or UML-conformance claims
    (86.3% of the catalog is not UML; the audit shows the repo has avoided this
    for its whole life).
  - *Sixth ecosystem, still no grader — narrowest margin yet.* SDMetrics is the
    closest architectural analogue to pumllint found in any of the six:
    design-rule checking plus OO metrics over XMI from any UML tool, rules and
    metrics in a user-extensible XML config, a CLI for automated runs,
    HTML/XML reports, commercial since ~2002. Its 226-page manual contains no
    quality model, index, score, rating or maturity concept; output is metric
    tables plus severity-ranked violations. Karasneh et al. (CEUR-WS Vol-1555)
    from the inside: "Current CASE tools do not give any hints to improve
    models, except some layout algorithms and syntax."
  - *Recorded, not queued*: (1) **`CLS006 type-mismatched-generalization`** —
    verified at `08efeda`: a Class specializing an Interface *and* an
    Enumeration scores **Level 4 (Precise) 99.0 with zero structural findings**
    (only GEN001), and an Actor specializing a UseCase likewise, while the
    comparable `Pseudostate::initial_vertex` violation is an **STA001 blocker,
    exit 1**. `model.py:258` already carries the classifier `kind`
    (class|abstract|interface|enum|implicit) and the relation its own `kind`,
    so **no parser work**. Must be justified as CLS004 is — uncompilable in the
    target language, plus PlantUML's own admission — **never** by appeal to the
    OMG spec, which would break the claim-language discipline just verified.
    Scoring change: own decision, own golden re-freeze. Maintainer self-demand.
    (2) The **type-fallback defect class, fifth instance** — no new candidate,
    the ArchiMate entry's candidate 1 covers it; recorded for the mechanism at
    line precision. pumllint parses **5 of UML's 14 diagram types**; of the
    nine uncovered, component/deployment in bracketed style and timing fail
    **honestly** (the `[...]` and `@`-timecode tokens break `_IDENT` in
    `RE_MESSAGE`, nothing parses, C6 holds at Level 1), while object, package,
    composite structure, communication, alias-style component,
    bracketless deployment and timing-plus-one-arrow reach **Level 4 "Precise",
    often 100.0 with zero findings**. `A --> B` = 2 implicit participants + 1
    message = elementCount 3 = exactly `l4_min_elements` (scoring.py:88), so C6
    does not fire. **Arrow shape decides the margin**: dashed/dotted set
    `is_return_arrow` (sequence.py:472) → SEQ009 in DIM-SEM (w 0.20) → Level 4;
    a solid `->` trips SEQ005 in DIM-AMB (w 0.25) → 66.67 < the 70.0 L4 gate →
    Level 3. Sharpest case: `api -[#red]-> ledger : postEntry` — label kills
    SEQ005, solid arrow avoids SEQ009 — **Level 4, 100.0, zero findings** on
    two lines. And `--min-level` inverts: a timing diagram *with* one arrow
    passes `--min-level 4`; the same diagram minus it fails `--min-level 3`.
    Worse in one case: deployment using `database "orders" as ordersdb` types
    the file sequence and reports **critical** findings, failing CI at exit 1.
    (3) **Cite the PlantUML attribution** — README.md:6-8 says "by its own
    admission" with no URL; both the current and historic FAQ wordings are
    verbatim-quotable. Documentation candidate. (4) **The
    expressible-invariants numerator** — the analogue of the C4 note's
    "40% mechanizable" table; would convert "3 of 51 overlap" from a
    classification into a measurement. Lab work, no behaviour change.
  - Re-litigate on: an adopter feeding pumllint output to a real UML toolchain
    (which PlantUML's "XMI work is in progress" makes impossible today);
    **SysML v2 / KerML** acquiring a PlantUML-renderable textual form with users
    — OMG adopted SysML v2.0 + KerML 1.0 in July 2025, built on KerML rather
    than as a UML profile and shipping a textual notation with a published BNF,
    which is the one development that speaks directly to the premise that text
    notations need an external semantic gate (characterized; the pilot
    implementation is on GitHub, outside scope); or evidence that a UML tool has
    begun producing a graded verdict, ending the six-ecosystem streak.

- **Mermaid ecosystem (2026-08-27): no — and the 2026-07-26 sibling-stack
  parking is upgraded from *unqueued on cost* to *refused on an occupied
  niche*. Two documentation candidates recorded, nothing queued.** Sixth and
  last of the week's series, and the only ecosystem that is a **direct
  substitute** rather than an adjacent layer: same artefact class, same
  repositories, same authors, increasingly the same machine authors (full
  record: docs/mermaid-ecosystem-evaluation.md; repo claims executed at
  `f806dce`; **no Mermaid tool executed**, no GitHub repository read — both
  linters and Mermaid itself are GitHub-hosted, so the §3.1 rule mapping is
  read from published rule descriptions, not paired runs). Verdict:
  - *(1) The sibling stack exists.* `@mermaid-lint/cli` (0.53.1, created
    2026-06-16, published 2026-08-13) is a near-complete architectural
    mirror: config file (`mermaid-lint.config.js`/`.mermaidlintrc`),
    per-rule severities `off`/`warn`/`error`, inline suppression
    (`%% mermaid-lint-disable`), `--format json`, an **`--fix` autofix**, a
    GitHub Action posting inline PR annotations — and it lints **fenced
    diagrams inside Markdown**, the capability this repo demand-tested and
    declined for PlantUML. `@probelabs/maid` (0.0.29, ISC) is a second.
    Mermaid itself ships no semantic validation, and `mmdc` is
    characterized as unreliable even at parse errors.
  - *(2) Mermaid owns the niche the demand scan measured.* Native GitHub
    rendering since Feb 2022, plus GitLab/Notion/Obsidian/VS Code;
    characterized as the only format rendering inline in a README with no
    build step, and as what most LLMs emit when asked for a diagram in
    markdown. The scan already saw the local form: Mermaid outnumbering
    PlantUML 76× (`.kiro/`) and 437× (spec-kit `plan.md`).
  - *(3) This project's own evidence ranks the carrier lower.* W3:
    Mermaid sequence **−9.1 pp pooled / −20.0 pp flow-sensitive** vs the
    PlantUML baseline, carrier equivalence refuted. Extending the codegen
    profile to the carrier this lab measured as weaker, in order to serve
    generation quality, is incoherent. (W3b's non-reproduction of the
    stored-frame deficit does not rescue it; the recorded carrier-deficit
    reproduction wave stays gated as written.)
  - *(4) Seventh ecosystem, still no grader.* `mermaid-lint` reports
    pass/fail per diagram with file, line and message — no aggregate score,
    level, gap report or ratchet. Seven validators now (Structurizr,
    LikeC4, SHACL, Archi, bpmnlint, SDMetrics, mermaid-lint) and the
    grading layer is unoccupied **even where two linters compete**, which
    is the strongest form the finding has taken.
  - *The uncomfortable part, recorded because either half alone misleads:*
    the category claim and the carrier evidence now point opposite ways.
    The 2026-07-26 positioning is "deterministic verifiers for
    AI-read/AI-written artifacts"; Mermaid is where AI-authored diagrams
    land; and `mermaid-lint`'s stated motivation is this project's thesis in
    someone else's words — *"In agentic engineering workflows … your Markdown
    files are live context. A broken diagram doesn't just fail a human
    reader; it injects a parse error into a context window."* **The category
    is validated and the niche is contested.**
  - *Convergence, second instance and the sharper one.* After `bpmnlint`,
    a second independent linter reached this catalog's concepts — and this
    time in a substitute notation: `sequenceDiagram` activations without
    matching deactivations = **SEQ003/SEQ108**; duplicate or self-looping
    edges = **SEQ006**; empty labels = **SEQ005/STA003/CLS003**; duplicate
    node IDs = the **XD** identity family. Its own documentation
    distinguishes semantic rules from syntax because they catch diagrams
    that parse but "still mislead" — this project's founding distinction,
    independently derived. The surviving difference is exactly two rows:
    **DIM-AMB and the codegen lexicons** (mermaid-lint checks a label's
    *presence*, never what it *says*) and **the graded verdict**.
  - *Type transfer is partial*: Mermaid has sequence/class/state but **no
    use-case diagram at all**, and its flowchart is not a UML activity
    diagram — 3 of 5 packs transfer. Its own large surface (Gantt, pie, git
    graph, mindmap, ~15 experimental types) is mostly outside any
    modelling-hygiene rule set. Mermaid's C4 is flagged ⚠️ experimental,
    which weakens the C4 note's S4 transfer argument rather than
    strengthening it.
  - *Never build*: a Mermaid parser/rule pack (occupied niche + full
    sibling stack + a carrier this lab ranks lower); a PlantUML↔Mermaid
    converter or Mermaid `fix` output; **any repositioning from "PlantUML
    linter" to "diagram linter"** — the claim-language discipline audited
    clean against UML on 2026-08-27 and this is where it would break first.
  - *Boundary measured honestly in all three arrival forms*: a directory of
    `.mmd`/`.md`, a bare `.mmd`, and Mermaid source saved with a `.puml`
    extension all warn on stderr and leave the exit code at 0. The one
    dishonest case needs a user to wrap Mermaid in `@startuml…@enduml`:
    7 findings, 2 critical, exit 1, Level 3 — of which five are alias-binding
    artefacts (Mermaid's `participant X as Long Name` binds the opposite way)
    **but SEQ003 is correct**, and it is the very rule mermaid-lint names.
    Recorded as an observation, not a candidate.
  - *Recorded, not queued*: (1) **restate the demand-scan finding** — the
    2026-07-26 record concludes embedded PlantUML has no demand, which is
    right; its own numbers also support the stronger sentence that *the
    embedded niche is large and PlantUML does not own it*, and
    mermaid-lint shipping Markdown-fence linting is the confirmation. A
    dated pointer is added to that note; documentation only. (2) **The
    convergence record**, worth re-checking if mermaid-lint's rule set
    grows — **especially upward into a graded verdict**, which is the one
    change that would end the seven-ecosystem streak from the closest
    possible range.
  - Re-litigate on: **mermaid-lint or Maid shipping a level, score or
    maturity verdict**; a concrete adopter with PlantUML *and* Mermaid in
    one repository asking for one gate over both (the only shape in which a
    Mermaid recognizer serves an existing user rather than a new market); a
    carrier wave reversing W3's ordering; or Mermaid's C4 leaving
    experimental status *and* the C4 census trigger firing together.

- **D2 ecosystem (2026-08-27): no — the first refusal in the series where
  the linting niche is *open*, so it rests on ground none of the six
  predecessors used. One candidate recorded, and it amends an existing
  item rather than adding one.** Seventh of the series (full record:
  docs/d2-ecosystem-evaluation.md; repo claims executed at `5b4a5a0`;
  **no D2 tool executed** — `d2` was not installed, so nothing reports what
  `d2 validate` actually accepts; no GitHub repository read). Verdict:
  - *Naming collision, cleared first.* **"D2" is already taken in this
    repository** — EVIDENCE.md uses it as a pre-registered wave hypothesis
    label ("D2 (generator robustness): the below-composite-40 cliff
    reproduces under a weaker generator (`claude-haiku-4-5`)"; resolved
    "D2 — confirmed"), cited again in the Aschenbrenner note. Both names
    are correct, neither should change; recorded so the collision is
    deliberate rather than discovered.
  - *(1) Refused on the artefact.* D2 is a **general graph language**, not
    a family of typed notations: three primitives (shapes, connections,
    containers) and a presentational shape vocabulary (`rectangle, square,
    page, parallelogram, document, cylinder, queue, package, step,
    callout, stored_data, person, diamond, oval, circle, hexagon, cloud,
    c4-person`). Sequence is the **one verified** pack counterpart
    (`shape: sequence_diagram`); class/state/use-case/activity have none —
    not as missing features but as categories a general graph language
    does not have. Most D2 diagrams are therefore diagrams this catalog has
    no rules for at all. "One of five" is a **floor**: further special
    object types are documented on pages not fetched.
  - *(2) The niche is open but claimed by upstream.* First of seven
    ecosystems with no third-party linter found — and the only one whose
    maintainers have written the intent down: D2's roadmap reads verbatim
    **"Build a configurable linter."** Building it for them is the
    SonarQube-plugin lesson with the vendor's plan on the record.
  - *(3) D2's syntax floor is already higher than PlantUML's.* It ships
    `d2 fmt`, `d2 validate`, and a parser designed for "being able to parse
    broken syntax and output multiple, human-readable error messages". The
    founding premise (PlantUML renders inconsistent diagrams without
    complaint) travels to D2 only in its *semantic* half.
  - *The measurement is the series' sharpest, and it indicts this tool
    rather than D2.* D2's connections are written `a -> b: label` —
    **character-identical** to PlantUML's messages — and D2 auto-creates
    actors on first reference, exactly as PlantUML auto-creates lifelines.
    A D2 sequence diagram wrapped in `@startuml…@enduml` is typed
    `sequence` and scored **Level 4 (Precise), 99.17/100, one cosmetic
    finding (GEN001), exit 0**. The Mermaid equivalent measured a day
    earlier gave 7 findings, 2 critical, exit 1. Mermaid's foreign syntax
    was loud and wrong; D2's is quiet and wrong.
  - *And the silence is a designed behaviour, not a defect.* SEQ001 carries
    `only_if_any_declared` (default True), documented in the rule as *"stay
    quiet in files that declare nothing at all, so quick ad-hoc sketches
    aren't punished"* (pumllint/rules/sequence/participants.py:19-20). A D2
    file yields zero PlantUML declarations, so the one rule that would
    object withdraws by design. Correct for its intended input; it removes
    the last signal on unintended input. **No change to SEQ001 is
    proposed.**
  - *The one thing that transfers is a hazard, not a rule.* D2's own
    sequence docs say *"You don't have to explicitly define actors … but if
    you want to define a specific order, you should"* — SEQ001's rationale
    reached independently by a language with no linter to express it. After
    bpmnlint and mermaid-lint converged on *implemented* rules, this is the
    third convergence and the first where only the **hazard** converged.
    The rules are right; the reach is wrong.
  - *Never build*: a D2 parser or rule pack (refused on **merit**, not
    demand — an adopter asking would not fix the type mismatch or unclaim
    upstream's roadmap); a third-party D2 linter; any repositioning to
    "diagram linter" (three substitute notations now, one supported).
  - *Licence posture checked*: D2 is **MPL-2.0**, an independent project
    fiscally sponsored by Hack Club, source moved `terrastruct/d2` →
    `d2lang/d2`. No blocker, and nothing here proposes vendoring.
  - *Eighth ecosystem, no grader* — and the one roadmap that names a linter
    does not name a score, level or maturity model.
  - *Recorded, not queued*: (1) **amend the type-fallback candidate** (the
    ArchiMate entry's candidate 1) to cover the silent case — it addresses
    typing confidence and cap C6, and the D2 case passes both, being
    silenced instead by a *rule option*. Any fix must be validated against a
    zero-declaration foreign-syntax file or it repairs the five loud
    instances and leaves the quietest one at Level 4 (Precise) 99.17.
    (2) The naming-collision note above.
  - Re-litigate on: **D2 shipping its configurable linter with a graded
    verdict** (the single event that would end the eight-ecosystem streak,
    from a language whose tooling culture is unusually strong); an adopter
    with PlantUML *and* D2 in one repository asking for one gate over both
    (which would still face the one-of-five type mismatch); or evidence
    that `shape: sequence_diagram` dominates real D2 usage, which would
    raise the type-transfer floor and is currently unmeasured.

- **Structurizr DSL ecosystem (2026-08-27): no — the twice-settled
  decision stands and its *reason* is corrected. One documentation
  candidate; nothing queued.** Eighth of the series (full record:
  docs/structurizr-dsl-ecosystem-evaluation.md; repo claims executed at
  `2bac87e`; **export samples reconstructed**, not captured from a real
  `structurizr-cli` run — the CLI was not installed and the docs print no
  verbatim output, so the mechanisms below are measured and their fidelity
  to real exporter output is characterized; no GitHub repository read).
  Verdict:
  - *The framing in both prior records was wrong, and that is this note's
    contribution.* 2026-07-27 ruled Structurizr DSL "out of scope … a
    different language with its own toolchain"; 2026-08-27 reaffirmed it
    ("nonsense; stronger than in July"). Both treated Structurizr as
    something pumllint might **support**. It is not a support candidate —
    it is a **producer of the artefact pumllint already gates**.
    `structurizr-cli export` emits PlantUML in two dialects
    (`plantuml/structurizr`, `plantuml/c4plantuml`) plus Mermaid, D2, DOT,
    Ilograph and WebSequenceDiagrams. The relationship is
    producer→consumer, which none of the seven predecessors had.
  - *Measured on all three export shapes.* **(1) C4-PlantUML export** →
    `unknown`, 0 elements, **Level 1 (Sketchy) 98.75** — cap C6 holds,
    honest, and a clean cross-check: the C4 evaluation's dated Level-1
    measurement predicts a producer it never examined. **(2) Static-view
    export** → typed `sequence`, **Level 3 (Disciplined) 85.0**, three
    GEN003 inline-skinparam findings — true, and about styling the
    exporter regenerates on every run. Type-fallback class, sixth
    notation. **(3) Dynamic view with `plantuml.sequenceDiagram=true`** →
    a *genuine* PlantUML sequence diagram: typed correctly, parsed
    correctly, **Level 4 (Precise) 93.57** — and its three findings are
    GEN004 naming violations on participants named `1`, `2`, `3`.
  - *The finding: **every Structurizr sequence export trips GEN004 on
    every participant**, deterministically.* Verified: the exporter emits
    numeric identifiers and puts the real name in the display slot
    (identifier `'1'`, display_name `'Single-Page App'`), and GEN004 tests
    the identifier. **No change to GEN004 is proposed** — the rule does
    exactly what its catalog row says and the finding is *true*. What is
    absent is an actor who can act on it.
  - *That is the sharpest form of the generated-artefact problem in the
    series.* The ArchiMate note reached it by showing findings would be
    overwritten on the next export. This reaches it where **nothing
    malfunctions**: right type, right parse, true findings, and the only
    correct fix upstream in the DSL — where Structurizr's own `inspect`
    already runs. **A true finding with no actionable owner is worse than
    a false one, because it survives review.**
  - *Never build*: Structurizr DSL support (it would duplicate `validate`
    and `inspect`, shipped by the language's owner); a Structurizr-export
    recognizer or profile (special-cases one producer among many, and
    encodes a third party's output shape as a contract this project would
    have to track); any claim that pumllint checks Structurizr models.
  - *Added to the record* (not corrections — the C4 notes are silent on
    both, not wrong): **`inspect` is a documented CLI verb** alongside
    `validate`, so Structurizr is the only ecosystem in the series
    shipping syntax validation *and* a named rule set from one CLI; and
    **the ecosystem count stays at eight, not nine** — Structurizr was the
    first validator counted in the no-grader streak, so re-confirming it
    is a check, not a new data point.
  - *Licence checked*: Structurizr DSL is Apache-2.0 (Simon Brown; free
    open-source core plus a paid hosted platform). No blocker; nothing
    proposes depending on it.
  - *Recorded, not queued*: (1) **a short note on generated `.puml`** —
    what to expect from each of the three export shapes, and that GEN004's
    `pattern`/`per_kind` and GEN003's `allowed` already neutralise both
    systematic findings in `pumllint.toml`. Documentation only; awaiting
    an observed user. (2) **The generated-artefact principle** — second
    instance after ArchiMate, stated once so a third does not re-derive
    it: the hazard is not wrong findings but **true and unownable** ones.
    (3) Type-fallback class, sixth notation — no new candidate; the
    ArchiMate entry's candidate 1 as amended by the D2 entry covers it.
  - Re-litigate on: an adopter piping `structurizr-cli export` output into
    pumllint and reporting friction (the only trigger here a user can
    fire, and it would turn the documentation candidate into a page);
    Structurizr's inspections gaining an aggregate verdict (the standing
    streak trigger); or evidence that exported sequence diagrams are a
    common input, which would make the GEN004 pattern a common experience
    rather than a latent one.

- **Ilograph ecosystem (2026-08-27): no, on the cleanest grounds in the
  series — and the yield is not about Ilograph.** Ninth of the series
  (full record: docs/ilograph-ecosystem-evaluation.md; repo claims
  executed at `7043819`; **no Ilograph tool executed** — closed commercial
  software, not licensed or installed; the sample model is reconstructed
  from the published spec, whose page does **not** state the
  serialization, so "it is YAML" is characterized from Structurizr's
  exporter docs; no GitHub repository read). Verdict:
  - *Three structural refusals, each sufficient, none demand-gated.*
    **(1) Not a diagram notation** — a *model plus perspectives* format
    for an interactive viewer (`resources` tree, `perspectives` of
    relation or sequence type, `contexts`, `imports`), where a
    perspective is a traversal rather than a picture, so the unit
    pumllint reasons about does not exist. Sequence perspectives are the
    only partial map, and even they have no activation concept, where
    four of the eleven base sequence rules live. **(2) The first fully
    commercial, fully closed ecosystem in the series** — Free/Pro/Team/
    Team+ SaaS plus a paid Desktop app, no open-source component at all
    (every predecessor had an open core). No source to validate a
    recognizer against, no grammar-stability guarantee, and the licence
    posture question has **no answer available**. **(3) It is YAML**, and
    W3 ranked structured YAML last of five carriers (−30.3 pp pooled,
    −66.7 pp flow-sensitive, the only non-compiles in the single-shot
    programme).
  - *The finding, generalized past its occasion.* Wrapping the model in
    `@startuml…@enduml` is typed `sequence` and scored **Level 4
    (Precise) 99.62, one cosmetic finding, exit 0**. Verified in the
    parse: **the YAML list dash `-` is read as a PlantUML arrow**, the
    YAML *key* becomes the target participant and the *value* becomes the
    message label — `- id: Checkout UI` → a message to a participant named
    `id` labelled `Checkout UI`. The four recovered "participants" were
    `id`, `name`, `from`, `to`: the vocabulary of the file format, not
    entities.
  - *And it improves with size, which is the part that matters.* Measured
    across four model sizes (n resources + n−1 relations): **99.44 (9
    elements) → 99.78 (23) → 99.81 (53) → 99.82 (83)**, Level 4 and exit 0
    throughout. The extra findings at 53 and 83 are GEN009 (83 elements >
    60) and SEQ011 (80 messages > 30), both `minor`, moving the composite
    by fractions and the level not at all. **A bigger foreign file scores
    better.** Cap C6 stops a diagram with nothing *modelled* from claiming
    a level; nothing stops a diagram with nothing *understood* from
    claiming a good score.
  - *This is the sixth instance of the type-fallback class and differs in
    kind from the five before it.* Those **dropped** lines they could not
    read; this one **manufactures** content from structural punctuation.
    The ArchiMate entry's candidate 1 is amended a second time
    accordingly (see that entry).
  - *Never build*: an Ilograph reader or rule pack; **a YAML front-end of
    any kind** — §8 makes it look needed and the opposite follows, the fix
    is to stop scoring the unrecognized rather than to recognize more;
    anything premised on the Structurizr→Ilograph export being a pipeline
    into pumllint (Structurizr writes Ilograph YAML and `.puml` as
    *alternative* outputs; the branches never meet).
  - *Validation layer*: Ilograph documents **no** validation, linting or
    semantic checking of its own. The only tooling found is an
    **unofficial community MCP server** offering "real-time validation
    with detailed error analysis", whose own description says it is "not
    affiliated with or endorsed by Ilograph LLC".
  - *No-grader streak — first caveated entry.* Nothing here grades, but
    Ilograph ships no validator, so its non-grading is near-vacuous. The
    streak holds at **nine with that caveat attached**, and should not be
    cited without it.
  - *Small corroboration for the XD pack, from an unexpected direction*:
    Ilograph's `id`/`instanceOf`/`abstract` exist because a resource
    referenced from many perspectives must be *one* resource — XD001–005's
    one-entity-one-identity thesis, solved structurally by a tool that has
    a model, where pumllint must enforce it by inspection.
  - *Recorded, not queued*: (1) the second amendment to the type-fallback
    candidate (above); (2) **the next probe if it is picked up** — JSON,
    TOML and Markdown wrapped in `@startuml`, unmeasured, and the
    mechanism suggests they may degrade differently again.
  - Re-litigate on: **nothing an adopter can bring.** All three grounds
    are structural; only Ilograph open-sourcing a core or shipping a text
    notation with diagram semantics would move them, neither plausible.
    The YAML candidate is not demand-gated at all — it awaits the
    type-fallback decision, already recorded as maintainer self-demand.

- **Graphviz / DOT ecosystem (2026-08-28): no — and the first refusal in
  the series where this repository's own licence posture is decisive.**
  Tenth and last obvious one (full record:
  docs/graphviz-dot-ecosystem-evaluation.md; pumllint claims executed at
  `73f8ed9` with default config outside the repo; **`dot` was not
  installed**, so nothing reports what Graphviz itself accepts; per
  session scope **no GitHub repository was read**, so the four linting
  attempts are characterized from descriptions and forum discussion, not
  inspected; the licence and its date are verified from
  `graphviz.org/license/`). Verdict, on four independent grounds:
  - **(1) The licence, and this is the new thing.** Graphviz is **EPL
    2.0**, relicensed **7 March 2026**. The prose-pipeline settlement's
    never-build reads *"EPL dependencies anywhere in the repo (one GPL
    sdist — product and lab alike)"*, and the rule is categorical.
    Nothing is violated today (`pyproject.toml` is `dependencies = []`,
    verified; no source file mentions Graphviz). Nine ecosystems raised
    no licence obstacle; this one does. **The consequence worth
    recording is about `tools/`**: the knowledge-graph evaluation
    established that licensing does *not* bind lab tooling (rdflib BSD,
    pyshacl Apache-2.0, networkx BSD) — **Graphviz is the exception**,
    so the optional-extras door that stood open for the graph stack is
    **closed** for this one. Recorded because "let's just use
    `pygraphviz` in `tools/` for a quick visualization" is exactly the
    shape the rule exists to stop. *Invoking* a separately-installed
    binary would be the recorded run-not-linked posture and permissible;
    there is no reason to, so the distinction is recorded, not exercised.
  - **(2) Zero of five packs transfer — a first.** DOT is a *graph*
    language with layout attributes, not a diagram notation: no diagram
    types, no lifeline, message or activation concept, nothing for a rule
    to attach to. Mermaid transferred three of five, D2 one, Ilograph a
    partial sequence mapping. DOT transfers none.
  - **(3) Graphviz is not beside this project, it is underneath it.**
    `dot` was PlantUML's layout engine for most of its history and is
    optional since the pure-Java **Smetana** port (1.2021.5,
    `!pragma layout smetana`). A dependency-of-the-renderer relationship
    is unique across the ten, and it is the opposite of an adjacency —
    pumllint has never needed to know which engine drew the picture.
  - **(4) The niche is repeatedly attempted and unsettled**, a fourth
    distinct pattern after occupied (Mermaid, BPMN) and open-and-claimed
    (D2): `redot-lint` (community discussion, 2023: *"unfinished,
    unmaintained and tied to the redot editor"*), `graphviz-dot-hooks`,
    an attribute checker, `gvpr` as a substrate, and forum threads
    literally asking for a DOT linter. Thirty years, a large user base,
    nothing sustained — read as evidence *against* building, not as an
    opening.
  - *The measurement is the best boundary result in the series, and it
    is luck.* Idiomatic DOT wrapped in `@startuml` is `unknown`, 0
    elements, **Level 1 (Sketchy) 95.0** — where D2 reached Level 4
    99.17 and Ilograph YAML Level 4 99.62. **The semicolon is why**:
    `a -> b;` fails the message pattern on its trailing punctuation,
    `a -> b` matches. Semicolons are **optional** in DOT, so the same
    graph written without them types `sequence` at **Level 3, 89.0**,
    and the undirected `a -- b` form — the token the ArchiMate note
    already named unsafe — reaches **Level 4, 91.0**. Three honest
    results in the note have three *different* accidental causes. The
    protection is real and it is incidental; do not rely on it.
  - *The boundary itself is correct in three forms* (§8.1): a directory
    of `.dot` files warns "no PlantUML files found"; a `.dot` file passed
    directly warns "no @startuml block"; and PlantUML's own `@startdot`
    passthrough is correctly excluded. Exit 0 throughout.
  - *Tenth ecosystem, no grader* — the streak reaches ten, and unlike
    Ilograph's near-vacuous entry this is a real data point, with one
    qualification: what is established is that **none of the four
    attempts is *described* as grading** (their stated jobs are style,
    pre-commit hygiene and attribute validity), since none was inspected.
  - *Bookkeeping correction, made once so it is not re-derived*: the
    type-fallback instance count in this record had drifted. BPMN
    *fourth* and UML *fifth* are right; **Mermaid broke the one-per-
    ecosystem correspondence** by contributing no instance, and the two
    entries after it both reverted to counting by ecosystem position and
    both said "sixth" (Structurizr "sixth notation", Ilograph "sixth
    instance"), which cannot both hold. Correct enumeration:
    Linked.Archi 1, C4 2, ArchiMate 3, BPMN 4, UML 5, D2 6 (the quiet
    one), Structurizr 7, Ilograph 8, Graphviz 9. No finding changes —
    nothing downstream depended on the number.
  - *Never build*: a DOT parser or rule pack; **any Graphviz dependency,
    binding or vendored layout, in the product *or* in `tools/`**;
    anything premised on PlantUML's Graphviz dependency being a
    connection (it is a rendering detail, and optional); a "fix" for the
    semicolon result, which is a *pass* — §8.2's non-idiomatic forms are
    the standing type-fallback class, not a new defect.
  - *Recorded, not queued*: (1) **the incidental-honesty design note** —
    a type-fallback fix must not assume the existing honest cases are
    honest for a principled reason; attaches to the ArchiMate entry's
    candidate 1 as twice amended, adding no third amendment. (2) **The
    scope-guard wording** — `cli.py:326-329` enumerates four non-UML
    `@start*` forms with no "e.g." and reads as exhaustive; `@startdot`
    is absent and is the one a Graphviz user arrives with. Behaviour is
    correct; the enumeration is short. User-facing output through `_err`
    is a contract surface, so this is a recorded wording change rather
    than a drive-by.
  - Re-litigate on: **nothing an adopter can bring** — the artefact
    argument and the licence are both structural. **Graphviz relicensing
    away from EPL** would remove ground (1) and change nothing, since the
    other three stand; recorded so a licence change is not mistaken for
    an opening. A DOT linter finally establishing itself would settle the
    niche question the other way and still not make DOT a diagram
    notation.

- **SysML ecosystem (2026-08-28): still no — and the first entry in the
  series that answers a trigger this record already set.** Eleventh
  (full record: docs/sysml-ecosystem-evaluation.md; pumllint claims
  executed at `59f4470`, default config, neutral cwd — GEN006/GEN007
  verified dormant; **no SysML tool executed** — not Cameo, not SysON,
  not the pilot implementation, so all tool behaviour is characterized
  from vendor docs, package listings and release notes; per session
  scope **no GitHub repository was read**, which leaves the pilot's
  PlantUML generator uninspected and its licence unresolved).
  - **The trigger fired, and its wording pointed the wrong way.** The
    UML entry watched for *"SysML v2 / KerML acquiring a
    PlantUML-renderable textual form with users"* and listed SysML v2 as
    the single item in its SWOT **threat** column. It already had such a
    form, and had for years: the OMG **pilot implementation renders
    through PlantUML** (`org.omg.sysml.plantuml`; `%viz` in its Jupyter
    kernel, characterized as a *highly adapted* PlantUML whose output is
    not entirely spec-conformant). SysML v2 does not compete with
    PlantUML — **it emits PlantUML**. *Correction to the record*: the
    UML note's threat entry is reclassified as a **producer of the
    artefact pumllint gates**, the Structurizr classification, alongside
    `structurizr-cli export` and the C4 exporters. The conclusion the
    threat entry supported is unchanged; only the classification was
    wrong.
  - *Two languages under one name, and conflating them defeats every fit
    question.* **SysML v1** (v1.7, June 2024, not deprecated) is a **UML
    profile** — nine diagram types, XMI interchange, no textual notation.
    **SysML v2** (final adoption 21 July 2025; spec Sep 2025, editorially
    updated March 2026 for ISO) is **not** a UML profile: built on KerML
    1.0, with a normative textual notation. No backward compatibility;
    migration tooling covers roughly a fifth of the metamodel. Both live
    for years.
  - **SysML v2 is the first notation in eleven that cannot be misread,
    and structurally.** Wrapped in `@startuml` it is `unknown`, 0
    elements, **Level 1 (Sketchy) 95.0** — because its relationships are
    spelled with **keywords, not symbols**: `connect a to b`,
    `flow x to y`, `succession a then b`, `satisfy R by p`, `:>`. The one
    arrow-shaped token, `->`, is an expression operator
    (`parts->size()`) and produced no message when present. Contrast
    D2 (symbol collision, Level 4 99.17) and DOT (saved by semicolons the
    language does not require). This is the one honest result in the
    series that survives editing the file.
  - **SysML v1 bdd is the first foreign notation to land in a fully
    correct parse — and the findings are the wrong dialect.** A bdd in
    community PlantUML class syntax types **`class`**, 8 elements,
    **Level 3, 69.22**, exit 1, with **CLS002 firing four times**
    demanding both-end multiplicity. Not a fallback and not a
    coincidence: SysML v1 *is* a UML profile and a bdd *is* a class
    diagram. But SysML **specifies defaults for both ends** of a
    composite association (composite 0..1, part 1), so omitting them is
    reliance on the spec, not omission. CLS002 is **right about the
    PlantUML text and misleading about the SysML model** — a positioning
    hazard, not a defect, and the third instance of the
    true-and-unownable pattern (ArchiMate, Structurizr, this), the first
    where the truth is in a *different language* from the reader's.
  - *The ibd is not a new instance.* `component` + a bare `--` types
    `sequence`, recovers exactly 3 elements (the `l4_min_elements = 3`
    floor, `scoring.py:88`) and scores **Level 4 (Precise) 91.25** — the
    standing type-fallback class in the alias-style-component form the
    **UML entry already recorded**. Eleventh notation, same mechanism, no
    new candidate and no amendment.
  - **The yield is the `trace` measurement, and it is not about SysML.**
    Same IDs, same diagram, varying only *where* the ID is written:
    inside a `<<requirement>>` block body — **where SysML puts it** —
    gives **0/2 covered, "1 unlinked diagram(s)"**; in a class name, a
    stereotype, or a relation label, also 0; in a **note or title**,
    2/2. The tool does not decline to judge — it confidently reports the
    requirements uncovered and the diagram unlinked, on the one diagram
    shape that exists to record that link. **And this is deliberate**:
    `trace.py:233-234` — *"Message labels and other model content are
    deliberately not carriers — same as the rule"* — so that rule and
    matrix cannot disagree about what counts as a reference. Not a
    defect, not a fix. What is new is that the invariant's **cost is now
    measured**, and that it is a pumllint property, not a SysML one: a
    plain class diagram with `+REQ-001` as a member behaves identically.
  - **Eleventh ecosystem, no grader — the strongest entry in the
    streak.** SAIC's **free** Digital Engineering Validation Tool ships
    **251 validation rules covering language *and* style** for
    MagicDraw/Cameo, reported with severities (fatal/error/warning/
    debug/info); Cameo adds SysML, KerML and vendor validation suites.
    That is the closest analogue to this catalogue found in eleven
    ecosystems. It reports violations, and produces no score, level,
    grade or aggregate. (Characterized from the product page; the rule
    set was not downloaded.)
  - **Licence: the Graphviz finding generalizes from a library to an
    ecosystem.** **Eclipse SysON is EPL-2.0** (verified from its Eclipse
    project proposal), and by that proposal it is *the core SysMLv2
    editing capability for Papyrus*, integrating with Capella — both
    Eclipse projects. The open SysML v2 tool ecosystem is an Eclipse
    ecosystem, so the categorical EPL never-build closes it whole,
    product *and* `tools/`. Second consecutive licence-binding
    evaluation, first that closes an ecosystem. **The pilot
    implementation's own licence is unresolved** — sources disagree
    (LGPL, with `LICENSE`/`LICENSE-GPL` files, vs a relicensing to EPL;
    the adjacent API-Services and Release repos are reported EPL-2.0) —
    and settling it needs the repository, outside scope. It does not
    need settling: SysON alone establishes the point and nothing
    proposes depending on any of it.
  - *Never build*: a SysML v2 reader or rule pack (wrong artefact, and
    pointed *upstream* of what this tool gates); **a SysML v1 profile
    mode** or `<<block>>`/`<<requirement>>`-aware rules — the one fit in
    eleven that would partly work mechanically, refused on the
    claim-language discipline, since it would assert pumllint checks
    SysML models while actually checking one community rendering of one
    of nine diagram types; **a stereotype-conditional CLS002 exemption**
    (the same move in miniature — the rule is correct about the artefact
    it examines); any Eclipse/EPL SysML tooling, product or `tools/`;
    **widening `trace`'s carriers without widening GEN007's** (the
    agreement invariant is worth more than the coverage); and reading
    "SysML v2 has formal semantics" as an argument against this project
    (KerML gives SysML v2 semantics inside SysML v2 and says nothing
    about whether a PlantUML file means anything).
  - *Recorded, not queued*: (1) **the `trace` carrier cost, measured** —
    not a fix proposal; the number, the confident-false-negative shape,
    the fact that it belongs to pumllint rather than SysML, and the
    constraint that any future widening moves GEN007 and `trace`
    together. A documentation note ("put the ID in a note or the title,
    and why") is the small end and is not queued either. (2) **The
    right-rule-wrong-dialect observation**, stated once so a fourth
    instance does not re-derive it.
  - Re-litigate on: **an adopter running pumllint over PlantUML
    generated by the pilot implementation** — the concrete form of the
    producer question, the only trigger here a user can fire, and
    precisely what this note could not measure (the generator was not
    inspected, so the shape of its `.puml` is unknown — the largest hole
    in the record); SysML v2 tooling producing a graded verdict (the
    standing streak trigger, and SAIC's 251 rules are already most of a
    catalogue); the pilot's licence resolving to EPL (confirms, changes
    nothing). **Not** on SysML v1's PlantUML rendering growing in
    volume — the profile mode is refused on what it would claim, and
    volume does not move that.

- **Capella / Arcadia ecosystem (2026-08-28): no — and the first refusal
  in the series argued *against a fit that works*.** Twelfth (full
  record: docs/capella-arcadia-ecosystem-evaluation.md; pumllint claims
  executed at `e989da8`, default config, neutral cwd — GEN006/GEN007
  verified dormant; **no Capella installed or run**, so its validation
  behaviour, rule categories and add-on catalogue are characterized from
  mbse-capella.org and the Eclipse project page; per session scope **no
  GitHub repository was read**, so Python4Capella and the
  Capella-Extensions collection were not inspected and "no PlantUML
  exporter" is a statement about the official catalogue plus search, not
  a proof of absence; the Arcadia samples are hand-written, since Capella
  cannot emit PlantUML).
  - **The central measurement is a *positive* result, the first in
    twelve.** An Arcadia **Exchange Scenario** (lifelines = components
    and actors, messages = exchanges) hand-drawn in PlantUML is typed
    `sequence`, parsed correctly, and scores **Level 4 (Precise) 99.38,
    exit 0**, with two cosmetic findings (GEN001, GEN002) and nothing
    else. Everything worked for the right reason: participants declared
    so SEQ001/SEQ002 are satisfied rather than dormant; activations
    balanced so SEQ003 is quiet on evidence; **SEQ009 — false in five
    previous evaluations — is correct here**, because the dashed arrows
    are genuine returns paired with genuine calls. An Exchange Scenario
    *is* a sequence diagram, so the deep pack applies as designed. **This
    is the first artefact from a foreign ecosystem that pumllint handles
    well.**
  - *And it is unreachable, which is the honest other half.* **Capella
    has no PlantUML export** — the official add-on catalogue exports to
    HTML, MS-Word (M2Doc), Simulink, ASN.1/AADL, SCADE, SysML (Obeo's
    commercial bridge) and Reqtify, plus Python4Capella scripting; no
    PlantUML anywhere, and no community converter surfaced in search. The
    §8.3 file had to be written by hand. A fit reachable only by users
    who have stopped using the ecosystem's own tool is not a fit with the
    ecosystem.
  - **Not a producer — recorded as a finding, not an absence.** Unlike
    Structurizr and the SysML v2 pilot, nothing here writes `.puml`. Two
    consecutive evaluations turned on producer relationships; checking
    and finding none stops "MBSE tools emit PlantUML" hardening into a
    generalization on two data points.
  - *Three further grounds, none needing the first*: Capella is an
    Eclipse/Sirius **graphical** tool over XML (`.capella`, `.aird`) with
    no text notation to lint; **Arcadia is a method before it is a
    language** (five perspectives — Operational Analysis, System
    Analysis, Logical, Physical, Component Contracts; an **AFNOR standard
    Z67-140 since 2018**, the first national-standard ecosystem in the
    series); and the licence, below.
  - **Licence — third consecutive EPL collision, and the repetition is
    itself the finding.** Capella is **EPL-2.0** (verified, Eclipse
    project page; Mature, 7.1.0, 2026-07-10). Graphviz collided as a
    *library*, SysML v2 as an open *tool ecosystem*, Capella as *the tool
    and its whole add-on platform*. **This is one condition, not three
    coincidences**: the MBSE and modelling-tool world is Eclipse-shaped
    (EMF, Sirius, Papyrus, Capella, SysON), so a GPL project forbidding
    EPL is **structurally excluded from the MBSE tool space**. Stated
    once here as a standing condition — a fourth evaluation should cite
    it, not rediscover it, and must not present it as news. The exclusion
    binds *linking*, not *reading*: nothing stops pumllint linting a
    `.puml` a Capella user wrote by hand.
  - **Twelfth ecosystem, no grader — and the closest taxonomic
    convergence found so far.** Capella *"organizes model validation
    rules in several categories: **Integrity, design, completeness,
    traceability**, etc."* with **validation profiles**. Two of those
    four are pumllint's dimension names verbatim (DIM-CMP completeness,
    DIM-TRC traceability), and "validation profiles" is what this
    repository calls rule profiles — arrived at independently. Second
    convergence data point after bpmnlint, and the first on the
    *taxonomy* rather than on individual rules. Capella reports
    violations with severities; no score, level, grade or aggregate in
    its documentation, and no metrics add-on in its catalogue.
  - *The other three shapes fall through, and none of it is new.* LAB
    (components + exchanges) and SDFB (functions + functional exchanges)
    both type `sequence` at Level 4 with **false SEQ009s** — in Arcadia a
    `-->` is a *functional exchange*, a directed dependency, while
    `is_return_arrow` (`parser/sequence.py:472`) reads any `--`/`..` as a
    return. The ArchiMate note named this explicitly and C4, Mermaid and
    UML each recorded the mechanism; the standing type-fallback class
    covers it, **no candidate and no amendment**. One coincidence, stated
    carefully: the LAB lands on **the same composite as C4 sample C**
    (Level 4, 6 elements, 88.96) with a *different finding set* — three
    false SEQ009s here, two plus a SEQ006 there. Not a reproduction; two
    foreign notations reaching an identical score through different
    penalties, which says something about how coarse the composite is at
    that end and nothing about Arcadia.
  - *A precision point recorded so it is not assumed*: an Arcadia
    data-flow blank is **not** a flowchart — it shows information
    dependency between functions, not control flow — so "Arcadia has
    dataflow, pumllint has an activity pack" is **not** a mapping. A
    PlantUML activity diagram scores well (`activity`, Level 4, 99.31)
    and is not an Arcadia rendering.
  - *Never build*: a Capella/Arcadia reader or rule pack; **any mapping
    of pumllint's maturity levels onto Arcadia's five perspectives** —
    both are five-step ladders and both get called "levels", and the
    alignment is entirely spurious: Arcadia's is *abstraction* (every
    perspective present in a finished model) and pumllint's is *grade*
    (exactly one applies at a time), so a model can be at Physical
    Architecture and score Sketchy; **a Capella→PlantUML exporter in this
    repository** — building the producer to create demand for your own
    consumer is manufacturing the pipeline rather than finding it, and if
    it should exist it is a Python4Capella script in a Capella user's
    repo; any Capella or Eclipse-platform dependency, product or
    `tools/`; and an integration justified by the shared category
    vocabulary (convergence is evidence the decomposition is natural, not
    that the tools should meet).
  - *Recorded, not queued*: (1) **the Exchange Scenario as the series'
    positive control** — twelve evaluations of negative results and one
    artefact class that lands right; worth citing when the question is
    what pumllint is *for*, and worth citing with the unreachability
    attached, since the population that would benefit is unverified.
    (2) **The EPL/MBSE structural exclusion, stated once** (above).
  - Re-litigate on: **somebody publishing a Capella→PlantUML exporter
    with users** — the only trigger here a user can fire, and the one
    that moves the fit from unreachable to reachable without this project
    building anything (refusing to *build* it is not refusing to *benefit*
    from it); Capella gaining an aggregate verdict (the standing streak
    trigger, and a plausible source given the taxonomy). **Not** on
    Arcadia adoption growing — Capella users use Capella, and volume
    creates no PlantUML artefact to lint.

- **ISO 42010 / viewpoint ecosystem (2026-08-28): no — and the first
  subject in the series that is not a notation, a tool or a product, but
  a standard about the same question this project asks.** Thirteenth
  (full record: docs/iso42010-viewpoint-ecosystem-evaluation.md; pumllint
  claims executed at `40c132c`, default config, neutral cwd). **Bounds
  first, because one of them is the subject: ISO/IEC/IEEE 42010:2022 is
  paywalled and was not read.** What is quoted comes from the publisher's
  **15-page preview** — front matter, full table of contents, part of
  Clause 3, **Clause 4 (Conformance) in full**, and the opening of Clause
  5. **Clauses 6, 7 and 8, which contain every requirement, were not
  read**, so this record states what conformance is claimed *for*, never
  what it *requires*. 42030 is characterized from secondary summaries
  only; its text was not seen.
  - **(1) pumllint's unit is precisely the one thing 42010 defines no
    conformance for.** Clause 4 names five claim situations — architecture
    description (Clause 6), architecture description framework (7.1),
    architecture description language (7.2), architecture viewpoint, and
    model kind. A `.puml` file is none: in 42010's vocabulary it is at
    best a **view component** (3.19), *"separable portion of one or more
    architecture views… governed by the applicable model kind or
    legend"*. **pumllint can neither conform to 42010 nor fail to.** That
    settles "42010-conformant" / "42010-aligned" before it is claimed —
    and the Linked.Archi note's record of *its* subject's alignment claim
    should be read with this attached. Note also 42010's ADL examples:
    AADL, ArchiMate, UML, SysML, UAF — an ADL needs *syntax **and**
    semantics*, so PlantUML is not one, which lands beside (not identical
    to) README.md:6-8's "drawing tool rather than a modeling tool".
  - **(2) Correspondences — half implemented, and measured.** 42010's
    central structural idea is that views *correspond*; the 2022 revision
    made "correspondences for model and view consistency" a headline.
    **XD001–005 (all DIM-CON, all about identity) are correspondence
    rules**, arrived at independently and first. What has no counterpart
    is the correspondence **requirement**:
    two views sharing an entity with a conflicting kind → **XD001 ×2,
    major, exit 1**; two views sharing **nothing at all** → **"✔ No
    issues found", Model set: Level 4 (Precise) 100/100**. **Two disjoint
    diagrams are a "Precise" architecture description at 100/100.**
    *And the fix is already refused*: a "views must correspond" rule is
    **missing-edge inference** — the never-build's *"participant-pair
    sweep's no-oracle shape"* — and the reason transfers exactly (nothing
    says which diagrams are meant to be one AD) with a worse
    false-positive shape (independent diagrams are normal). 42010 supplies
    a precise name for the gap and no way to close it. Recorded so a
    future reader meeting 42010 does not re-propose the rule as new.
  - **(3) The streak, reframed — the finding that outlives the note.**
    **Thirteenth ecosystem, no grader**, but not like the twelve before.
    Those were tools that happened not to aggregate. **ISO/IEC/IEEE
    42030:2019 is the standard in this family whose entire subject is
    architecture evaluation**, and it defines evaluation objectives,
    methods, quality models, criteria and stakeholder involvement while
    defining *"only a process and framework… not a scoring scheme, rating
    scale, maturity level, or aggregate verdict"*, declining to
    "prescribe how to aggregate results into an overall verdict".
    A standards body that owns the question, considered the aggregate,
    and stopped short. **Two readings, and this record picks neither**:
    either pumllint built something the field overlooked, or it does
    something the field examined and declined to standardize. **The
    consequence for the record is concrete — the no-grader streak may no
    longer be cited as evidence of an unoccupied niche without this
    caveat attached.** (Characterized from a secondary summary; anyone
    who can open 42030 should verify before leaning further on it.)
  - *A new kind of boundary, and it breaks the EPL run.* Twelve
    predecessors had readable normative text (OMG free, ArchiMate free
    behind registration, D2/Mermaid grammars in source). **42010 is the
    first ecosystem whose normative content could not be read.** The
    constraint is **access, not licence compatibility** — three
    consecutive evaluations turned on EPL and this one does not. It is
    also an independent argument against any conformance claim: **users
    could not check it either**, and a badge citing a document its
    audience cannot open is unauditable by design.
  - *The model-set verdict exists, which the altitude argument must not
    obscure.* `score` over a directory emits `Model set: Level 4
    (Precise) — 100/100 weighted across 3 diagram(s)`. pumllint does
    reason above the single file. What it does not see is what makes a
    set an architecture description: stakeholders as AD elements
    (they are substrings of title text), viewpoints, model kinds,
    rationale, correspondences.
  - *No boundary probe exists and that is the point*: 42010 defines no
    syntax, so there is nothing to wrap in `@startuml` and no
    type-fallback question. First note in the series with no §8.1
    discovery measurement.
  - *Never build*: a 42010 conformance claim, alignment badge or
    "42010-aware" mode; viewpoints/views/stakeholders/concerns as
    first-class model concepts (that is an AD tool with a linter
    attached); **a "views must correspond" rule** (missing-edge
    inference); renaming dimensions or levels into 42010 vocabulary
    (the badge claim by vocabulary instead); and **reading 42030's
    abstention as permission** — it is not endorsement of this project's
    aggregate and not proof the field was wrong; it makes the scoring
    model *more* exposed, not less.
  - *Recorded, not queued*: (1) the correspondence half-implementation
    with its never-build link (above); (2) **the model-kind fit** — a
    **model kind** (3.15, *"category of model distinguished by its key
    characteristics and modelling conventions"*) **is** a conformance
    target, and a pumllint profile is a statement of modelling
    conventions, so this is the single reachable fit in the note; parked
    jointly on the paywall (Clause 8's requirements unread, so nobody
    here can say what conformance would take) and the demand bar (no
    adopter has asked; the artefact is a document, not a capability);
    (3) the streak reframe (above).
  - Re-litigate on: **an adopter needing a 42010 conformance statement
    for procurement** — the only trigger a user can fire, plausible in
    defence and aerospace, and the one case where the correct answer
    ("the standard defines no target at this altitude") is unsatisfying
    enough to reopen; **42010 or 42030 becoming freely readable** (would
    make the model-kind question checkable and let the 42030
    characterization be verified rather than trusted); evidence that any
    tool produces an aggregate architecture-quality verdict — the
    standing streak trigger, now sharper, since it would show the field
    moving *toward* what this project already does. **Not** on viewpoint
    catalogues (4+1, Rozanski & Woods, TOGAF) gaining adoption — they
    describe how to organize descriptions, not how to check files, and
    have had decades.

- **TOGAF / ADM ecosystem (2026-08-28): no on every fit — and the note
  exists for the correction, not the verdict.** Fourteenth (full record:
  docs/togaf-adm-ecosystem-evaluation.md; pumllint claims executed at
  `0aa0305`, default config, neutral cwd). **Bounds first: the TOGAF
  Standard is free but registration-gated and could not be read** — every
  `pubs.opengroup.org` URL tried (10th edition, 9.2, 9.1, 8.1.1) returns
  a 302 to an OAuth endpoint this session cannot complete, so **every
  normative claim below is from secondary sources**, none quoted from the
  standard. Worth recording the inversion: the *paywalled* ISO 42010
  published a preview from which Clause 4 was quoted verbatim; the *free*
  TOGAF yielded no primary text at all. Free ≠ readable.
  - **CORRECTION TO THE RECORD — "Nth ecosystem, no grader" is imprecise
    as published, in thirteen entries.** TOGAF ships **two** ordinal
    grading schemes. **Architecture Compliance**: six levels (Irrelevant,
    Consistent, Compliant, Conformant, Fully Conformant, Non-Conformant),
    grading an *implementation against a specification*. **ACMM** (US DoC,
    carried in TOGAF's capability framework): six maturity levels across
    nine architecture elements, with a rating computed by **two
    complementary methods — a weighted mean maturity level, and the
    percentage achieved at each level** — grading an *organization's EA
    capability*. A weighted mean over weighted elements yielding an
    ordinal level plus percentages **is `scoring.py`'s composite,
    structurally**. The criterion the series was actually applying is
    narrower and is now stated: **nothing found in fourteen ecosystems
    grades the artefact class pumllint grades — a description.** Adjacent
    objects have been graded routinely for decades. Use the qualified
    form from here; read the past thirteen with this attached. *The
    structural-similarity half rests on a single secondary source —
    anyone with a TOGAF login should verify ACMM's calculation
    description before citing it further; the correction's direction is
    safe regardless, since TOGAF plainly grades.*
  - **This sharpens the ISO 42010 entry rather than softening it.** That
    entry (same day) found ISO/IEC/IEEE 42030 declining to define an
    aggregate verdict and read it as the field's considered abstention.
    Incomplete. **The same field has aggregated enthusiastically since the
    1990s — over organizations (ACMM) and implementations (Compliance) —
    and has declined to aggregate over descriptions.** Not shyness about
    aggregation: a consistent choice about which object gets a number.
    Both readings stay open and neither note settles them — (a) the niche
    is empty because grading a description is a different and harder
    problem nobody attempted while the artefacts were not in version
    control; (b) the niche is empty because the field considered it and
    put the number elsewhere. **(b) is better supported than it was this
    morning; (a) is not refuted.** Cite the streak with both.
  - **The measurement is the best in the series and a genuine surprise:
    three of four TOGAF diagram artifacts land in the *correct* parsed
    type with no false findings.** Business Use-Case Diagram →
    **`usecase`, Level 4, 99.31**; Conceptual Data Diagram → **`class`,
    Level 4, 98.75**; Data Lifecycle Diagram → **`state`, Level 4,
    99.48** — each with only GEN001 (no title) and GEN002 (no name),
    both true of the samples. Three artifact classes, **three different
    packs**, all correct. Capella's Exchange Scenario was one artefact;
    this is three, and it is the `usecase`/`class`/`state` packs — the
    three least discussed in the series — that earned it.
  - *Coverage across the published catalogue* (32 diagrams, 14 catalogs,
    10 matrices): my classification of artifact **names**, not TOGAF's,
    since the standard prescribes no notation — `usecase` 2
    (Business/Application Use-Case), `class` 2 (Conceptual/Logical Data),
    `state` 2 (Product/Data Lifecycle), `activity` 1 (Process Flow),
    **`sequence` 0**. **Seven of thirty-two**, spread over four packs.
  - **And the sequence pack maps to nothing, which inverts the series.**
    pumllint's deepest pack (11 base + 9 codegen, four rules about
    activation) has **no counterpart in TOGAF's 32 diagrams** — the
    catalogue has no sequence diagram. In eleven prior evaluations that
    pack was the one that *fired*, usually wrongly. TOGAF's nearest
    artefact, the Application Communication Diagram, mis-types to
    `sequence` with **3 false SEQ009s at Level 4, 6 elements, 88.96** —
    the standing type-fallback class (ArchiMate, C4, Mermaid, UML,
    Capella), **no candidate and no amendment**. One precise note: this
    output is **identical in type, level, score, element count and
    finding set to the Capella LAB** measured the same day — two
    unrelated frameworks, one shape (three components, three dashed
    labelled arrows), one result. C4 sample C reaches the same composite
    by a different finding set.
  - *The Open Group loop closes usefully*: ArchiMate (third in the
    series) is the notation, TOGAF the method it serves. The ArchiMate
    note found the **vocabulary** invisible to pumllint; this finds the
    **model kinds** mapping cleanly. Consistent, and jointly informative.
  - *Never build*: a TOGAF artifact recognizer or rule pack (no notation
    is prescribed, so the convention would have to be invented first);
    **any mapping of pumllint's levels onto ACMM's or the compliance
    levels** — three ordinal ladders over three different objects
    (organization, implementation, description), and unlike the Arcadia
    trap both TOGAF ladders *are* quality ladders, so the side-by-side
    table would look defensible and be false; any claim that pumllint
    supports, enables or accelerates the ADM (it is not a phase, produces
    no named deliverable, discharges no compliance review); a
    TOGAF-specific phase-tagging config key (GEN006/GEN007 already carry
    arbitrary prose tags); and **reading ACMM's existence as validation
    of the scoring model** — familiar shape, different object, and the
    object is the open question.
  - *Recorded, not queued*: (1) **the corrected streak criterion**
    (above) — the substantive output of this evaluation; (2) **the
    sharpened 42010 reading** (above); (3) **three TOGAF artifact kinds
    already parse and score correctly with no work** — a fact about the
    tool, second instance after Capella's Exchange Scenario and the first
    covering multiple packs; worth citing when the question is what
    pumllint is *for*.
  - Re-litigate on: **evidence that practitioners draw TOGAF artifacts in
    PlantUML** — the only trigger a user can fire, and the one that turns
    the measurement into an audience; **a TOGAF login becoming
    available**, which is the only way to put the correction on
    primary-source footing; a tool appearing that grades *description*
    artefacts — the streak trigger in its qualified form, now the only
    form in which it is a meaningful signal. **Not** on TOGAF adoption,
    which has been large for twenty years without producing a description
    linter.

- **DoDAF / UAF ecosystem (2026-08-28): still no as a build — and the
  strongest artefact fit in the series, the first that is both real and
  reachable.** Fifteenth (full record:
  docs/dodaf-uaf-ecosystem-evaluation.md; pumllint claims executed at
  `a8ef78a`, default config, neutral cwd, except where `codegen` is
  named). **First ecosystem in three whose normative text was readable** —
  DoDAF is a US Government work published openly and the quotations below
  are from `dodcio.defense.gov` directly. UAF's grid and 71 view
  specifications are characterized from vendor/OMG secondary sources.
  **The four samples are mine, written to be well-formed**, so the note
  measures the *ceiling*, not the field.
  - **The fit turns on one sentence of official DoDAF text.** The
    **OV-6c Event-Trace Description** is a required model, described by
    DoDAF as *"a time-ordered examination of the Resource Flows as a
    result of a particular scenario"* and **"sometimes called sequence
    diagrams"** — and on notation: *"**DoDAF does not endorse a specific
    event-trace modeling methodology. An OV-6c may be developed using any
    modeling notation (e.g., BPMN) that supports the layout of timing and
    sequence of activities.**"* **So a PlantUML sequence diagram is a
    conformant OV-6c** — authorized in normative text, not a workaround.
    Capella's Exchange Scenario fitted and was unreachable (no PlantUML
    export); here there is nothing to reach past.
  - **The measurement, default profile — best in fifteen evaluations.**
    OV-6c → **`sequence`, Level 4, 99.88, exit 0, one `info` finding
    (GEN002)**; OV-6b State Transition → **`state`, 99.92**; DIV-2
    Logical Data Model → **`class`, 99.75** — each with only "no name",
    true of the samples. Nothing false. The OV-6c exercised the deepest
    pack correctly: declared participants (SEQ001/002 satisfied on
    evidence), balanced activations (SEQ003), and **SEQ009 *correct***
    where it was false in six prior evaluations, because the artefact
    really is a sequence. SV-1 Systems Interface falls through to
    `sequence` at 89.79 with 2 false SEQ009s — standing type-fallback
    class, **no candidate, no amendment**.
  - **And the counterweight, which is the first *configuration* finding
    in fifteen evaluations.** The same OV-6c under **`--profile
    codegen`** collapses to **Level 2 (Structured), 52.4/100, four
    blockers, exit 1** — SEQ103 demanding signature-shaped messages of
    `request immediate CAS` and `transmit 9-line brief`. Those are
    *correct DoDAF*: an OV-6c records operational events in operational
    language and will never generate code. The rules are not defective;
    the profile encodes an assumption about the diagram's destiny and is
    pointed at the wrong artefact. **The default profile — what a user
    gets without asking — is right, and nothing warns that `codegen` is
    not.** Recorded, parked on the demand bar; a "DoDAF profile" is
    refused (the default already behaves correctly).
  - **One turn after TOGAF, this is the exact inversion, and the pair is
    the finding.** TOGAF: 32 diagrams, 7 map to a pack, **`sequence` 0**.
    DoDAF: 52 models, **12 map**, **`sequence` 3** (OV-6c, SvcV-10c,
    SV-10c), plus `state` 3, `activity` 3, `class` 3, `usecase` **0**.
    Read together: **frameworks differ sharply in whether they ask for
    time-ordered interaction models at all, and pumllint's centre of
    gravity suits the ones that do.** Neither note could say this alone.
  - *Fourth independent convergence on the pack decomposition.* UAF's
    grid is 10 stakeholder-domain rows × **11 model-kind columns**, and
    four of the columns — **sequences, states, processes, information** —
    are pumllint's packs by name. After bpmnlint's rules, Capella's rule
    categories and 42010's correspondences.
  - **Fifteenth ecosystem, no grader** (in the corrected form the TOGAF
    entry established: nothing grades a *description*) — **and the first
    that states a reason.** DoDAF's organizing doctrine is
    **"Fit-for-Purpose"**: content tailored so that *"the purpose or use
    of an architectural description at each level will be different in
    content, structure, and level of detail"*. A fixed rubric denies
    that. It does not settle the running question — the argument is
    against a fixed *content checklist*, and pumllint's rules are mostly
    about internal coherence, a narrower target — but it is the closest
    thing to a stated first-party objection the series has found, and it
    belongs beside 42030's abstention and TOGAF's aggregation-elsewhere.
  - *Access, third data point, and the pattern is not the obvious one*:
    ISO 42010 **paid** → Clause 4 quoted verbatim from a preview; TOGAF
    **free but registration-gated** → no primary text at all; DoDAF
    **openly published** → quoted directly. Price predicts readability
    poorly; publication model predicts it well.
  - *Never build*: a DoDAF/UAF pack, mode or model-type recognizer (an
    OV-6c *is* a sequence diagram and already parses as one — a
    recognizer adds a label and no capability); any DoDAF or UAF
    conformance/support/alignment claim (DoDAF conformance concerns the
    DM2 and model content, neither of which pumllint checks); a UAF
    profile or an integration justified by the grid-column vocabulary
    (fourth instance of this refusal); a "DoDAF profile" of the rule set;
    and **marketing the OV-6c result** — it is a good number from a
    sample written to be well-formed, which is how a project talks itself
    into a market that is not there.
  - *Recorded, not queued*: (1) **the OV-6c result as the series'
    high-water mark**, to be cited *with* the caveat that the sample was
    self-authored and no user is demonstrated; (2) **the TOGAF pairing**
    (above); (3) **the `codegen` mismatch** — first configuration
    finding, at most a documentation note; (4) **"Fit-for-Purpose" as the
    first stated reason** for the no-grader pattern.
  - Re-litigate on: **any evidence that a DoD program office, contractor
    or UAF user renders event traces in PlantUML** — the single trigger
    that would turn the ceiling measurement into an audience, and the
    only one a user can fire; **a real OV-6c to measure**, from anywhere,
    since the interesting question is what the messy ones score; an
    adopter hitting the `codegen` mismatch and reporting the blockers as
    wrong. **Not** on DoDAF or UAF adoption — both are large and have
    been for years without producing a description linter, and
    "Fit-for-Purpose" suggests the reason is doctrinal rather than
    accidental.

- **Cross-diagram relationships (2026-08-28): the XD pack joins entity
  *nodes*, never *edges* — no declared diagram→diagram relation exists
  anywhere in the product, the RDF qualified-relationship shape stays
  refused, and the in-notation half of the ask is the Arc C
  edge-coherence item, which now has its reproducible probe. Two
  candidates recorded, nothing queued.** The question (does pumllint
  support/lint relationships *between* diagrams, versus Linked.Archi's
  declared qualified relationships — direct triple, qualified predicate,
  first-class relationship resource with source/target/provenance/owner)
  was run through the house triage against `e989da8` (full record:
  docs/cross-diagram-relationships-evaluation.md; every claim executed,
  commands quoted). Verdict:
  - *The asker's reading is correct, and sharper than stated.* The
    cross-diagram layer is an **implicit, undeclared name-equality
    join**: two diagrams are "related" iff they spell an entity the same
    way, and only node properties (kind, stereotype, spelling) are
    compared. Measured: three diagrams whose entities agree perfectly
    but whose *relationships* directly contradict each other — an edge
    asserted, reversed, and absent — draw **zero cross-diagram
    findings**. Nothing in `model.py`, the parser, the report schemas or
    the CLI has a slot for a relation between diagrams; `trace` is the
    nearest shipped mechanism and is bipartite, untyped and undirected
    (a diagram that *is* DGM-001 and a diagram that *refines* DGM-001
    land in the same row, undifferentiated).
  - *Three further measured gaps, all silencing- or false-positive-shaped*:
    the join key is the **alias**, so the same display name
    (`"Order Service" as OS` / `as OrderService`) with a conflicting kind
    *and* stereotype is silent — an alias rename clears any XD finding;
    an **`!include`d declaration** never reaches the model (the parser
    skips `!` lines), so the same XD001/XD002 conflict scores 72.5
    inline and **87.5 via include (DIM-CON 0 → 100)** — an evasion that
    *raises* the maturity score, the sharpest silencing instance on
    record and the first that is not a mistyping artefact; and with **no
    namespace**, two bounded contexts sharing a word (`Order` the
    aggregate, `Order` the work order) draw symmetric XD005 findings
    that `authoritative` cannot dissolve — identity without namespacing
    has no negative form. Also measured: **`ref over`** — the notation's
    one cross-diagram construct, recommended by SEQ006's own message —
    is dropped whole by the parser.
  - *Never build*: RDF/OWL/SHACL as substrate (the 2026-08-26 N1/N3,
    verbatim); reified relationship resources smuggled through `.puml`
    comments (convention-manufacturing, and the correct product for that
    need is Linked.Archi with pumllint gating the producer — the shipped
    zero-code fit); hierarchy inferred from filenames or folders
    (invention upstream of the gate that exists to catch invention);
    cross-diagram *completeness* quotas (no oracle — a disconnected
    portfolio linting clean at exit 0 is measured and **correct**);
    `!include` resolution in the parser as scoped today (path semantics,
    `!includeurl` network fetches, macro expansion, a security surface
    SECURITY.md's trust boundary was written to avoid).
  - *Recorded, not queued*: (1) an **`!include`-evasion disclosure** —
    not include resolution but visibility: a sequence diagram carrying
    preprocessor lines and declaring nothing gets a "nothing was
    declared here" signal, following the "nothing was checked"
    stderr-warning precedent (exit codes untouched). Fixes a
    scoring-integrity defect independent of this question. Trigger: an
    adopter whose corpus uses `!include` for shared declarations and
    whose scores are consequently inflated. (2) **Declared
    diagram→diagram links** via `ref over` (externally-authored
    convention — PlantUML's own, already recommended by SEQ006) and/or a
    prose-carrier ID scheme extending `trace`: link-integrity checking
    (dangling target, orphan diagram) with `trace`-style gates. Same
    shape as the Linked.Archi `'!la-` candidate — if either is built,
    build them together. Trigger: an adopter running `trace` who asks
    for diagram→diagram links in the same table.
  - The **Arc C "XD member and relationship coherence" item is this
    question's in-notation core**, arrived at from the opposite
    direction (J-F corpus, 2026-08-26); its trigger (a second corpus or
    an adopter showing the defect class) is unchanged, and the note's M3
    probe is now its reproducible fixture.
  - One defect found and fixed with the note: RULES.md's XD pack
    preamble still described the pre-v0.29.0 **majority vote**,
    contradicting `9f06672` (issue #36), the rule bodies below it, the
    README and shipped behaviour.
  - Re-litigate on: the recorded triggers above, or the Arc C trigger —
    **not** on the existence of Linked.Archi, RDF 1.2 reification, or
    any ecosystem's relationship model (settled 2026-08-26 and
    2026-08-27). *Amended 2026-08-28, same day: the maintainer picked up
    candidate (1) and the G4 residual directly — the `!include`
    hidden-declarations disclosure shipped (stderr warning in the CLI
    parse funnel, exit codes and scores untouched; the parser now records
    the `!include` family as directives, still never expanding them), and
    every XD rule gained the `distinct` option, the negative form of
    `authoritative`, closing G4's bounded-context false positive.
    Candidate (2) and the G2 alias gap moved to Arc C checkboxes with
    their triggers intact.*
- **NAF / MODAF ecosystem (2026-08-28): no — and the note was run as a
  *sibling test* of the DoDAF result, which comes back negative.**
  Sixteenth (full record: docs/naf-modaf-ecosystem-evaluation.md;
  pumllint claims executed at `a923595`, default config, neutral cwd).
  **Bounds, and an uncomfortable one: NAFv4 is freely downloadable and I
  did not read it** — NATO's topic page 404'd and no substitute primary
  source was obtained, so the framework's structure, its two approved
  metamodels and the absence of a grading scheme are characterized from
  Wikipedia and vendor guides. Fourth access data point, and the first
  where the limit was mine rather than the publisher's: **free is
  necessary and not sufficient**. The exact NAFv4 grid rows/columns could
  not be obtained, so none are named and no coverage count is attempted.
  - **NARROWING CORRECTION to the DoDAF/UAF entry (one turn old).** That
    entry's fit rested on one sentence — *"DoDAF does not endorse a
    specific event-trace modeling methodology. An OV-6c may be developed
    using any modeling notation…"* — making a PlantUML sequence diagram a
    conformant OV-6c. **NAF says something that sounds similar and is
    not.** NAF is notation-agnostic about *drawing* but requires a
    NAF-compliant architecture to be built on one of exactly **two
    approved metamodels — ArchiMate 3.1 or the OMG UAF Domain
    Meta-Model** — with "traceable, consistent architectural information
    structured according to its viewpoints". **NAF conformance lives in
    the metamodel, not the picture.** So the DoDAF result is **specific
    to DoDAF's wording and does not generalize to the family it was
    unified with**; cite it as a fact about DoDAF, never about defence
    frameworks.
  - **The measurement inverts, which is the sharpest form of that
    correction.** Two routes, both legitimate NAF practice: **the
    ArchiMate metamodel route** (one of the two NAF approves) →
    `sequence`, **Level 4, 89.22, 4 false SEQ009s**; **a picture** (an
    event trace as an ordinary sequence diagram, no metamodel behind it)
    → `sequence`, **Level 4, 100.00, no findings, exit 0**. **The
    NAF-conformant artefact scores worse than the NAF-meaningless one.**
    Not a defect — pumllint measures what it says it measures — but a
    positioning result: **when a framework's conformance lives in a
    metamodel, a renderer-level score can rank artefacts in the opposite
    order from the framework's own criterion.** Route A is the standing
    type-fallback class (the `archimate` keyword is not a type marker),
    **no candidate and no amendment**.
  - **MODAF is dead — the first withdrawn framework in sixteen
    evaluations, and it supplies the empirical case for a standing
    refusal.** Its GOV.UK guidance is marked **[Withdrawn]**, its
    published PDFs carry `-withdrawn` in their filenames, and the UK
    MOD's **2024 Defence Architecture Framework adopts NAFv4**. Sixteen
    notes have refused framework-specific packs on scope, claim language
    and demand — all arguments. MODAF is a fact: **a framework with ~47
    prescribed views, national backing and a decade of use is now
    withdrawn, and anything built to recognize its view types would be
    dead code today.** pumllint's notation-level position survived
    without a code change: a PlantUML sequence diagram was a MODAF OV-6c
    in 2010 and is a NAF sequence-aspect view in 2026. First time the
    series can argue the layer choice from evidence rather than
    principle.
  - **The ArchiMate finding is now load-bearing.** The third note
    measured native ArchiMate as invisible to pumllint; that was a fact
    about one notation. **NAF makes ArchiMate one of exactly two approved
    metamodels for a live NATO framework**, so that finding now describes
    what happens on half of NAF's sanctioned routes — re-confirmed at
    current HEAD.
  - *Sixteenth ecosystem, no grader* (corrected form: nothing grades a
    *description*). No conformance levels, maturity model or scoring
    found — **weaker evidence than usual**, since the standard itself was
    not read.
  - *Never build*: a NAF or MODAF pack, view-type recognizer or mode (no
    notation to recognize, and MODAF shows what such a pack is worth);
    **any NAF conformance claim** (NAF conformance is metamodel
    conformance; pumllint reads a rendering and has no metamodel,
    deliberately); **reading the DoDAF result as a family result** — the
    specific trap this note closes; a metamodel layer, model store or
    ArchiMate/UAF-DMM conformance checker motivated by NAF (the standing
    knowledge-graph/OWL-SHACL never-build — a new reason to *want* it is
    not a new reason to build it); and **quoting the 100.00 without the
    89.22 beside it**.
  - *Recorded, not queued*: (1) the narrowing correction (above); (2)
    **MODAF's withdrawal as empirical support** for the framework-pack
    refusal; (3) **the ArchiMate finding promoted to load-bearing**.
  - Re-litigate on: **NAF issuing a notation-level conformance statement
    of DoDAF's kind** — the only development that would reopen the fit,
    and there is no sign of it; an adopter working the ArchiMate route
    and reporting the fall-through. **Not** on NAF adoption, and
    emphatically not on MODAF: one has a conformance criterion pumllint
    structurally cannot meet, the other is withdrawn.

- **Zachman ecosystem (2026-08-28): no — the purest "nothing to lint" case
  of the seventeen, and the note is not about the refusal.** Seventeenth
  and the oldest subject in the series (1987); full record:
  docs/zachman-ecosystem-evaluation.md; pumllint claims executed at
  `51c9eea`, default config, neutral cwd. **Bounds: zachman.com returned
  503 and was not read**, so every quotation is from secondary sources;
  row-perspective naming varies across versions and is not asserted; **the
  Zachman Framework for Enterprise Architecture™ is a trademark of John A.
  Zachman** and the graphic's reproduction terms could not be established,
  so none is reproduced.
  - **Zachman supplies the vocabulary this project lacked for its own
    unit of analysis.** The framework is an **ontology, not a
    methodology**, and draws the distinction in exactly the terms that
    matter: it *"classifies the total set of present 'primitive'
    (elemental) components"*, against a methodology *"which produces
    'composite' (compound) implementations of the primitives"* —
    *"primitives are timeless, whereas composites are temporal"*. **A
    PlantUML sequence diagram is a composite in that exact sense**: it
    mixes **Who** (participants), **When** (ordering, activation) and
    **What** (payloads). The 36 cells hold primitives. **pumllint lints
    composites and has no concept of a primitive** — measured: a
    primitive-like pure-**What** class diagram scores **Level 4 (Precise)
    97.92** and a three-interrogative composite **Level 4 (Precise)
    99.11**, on the same scale, with nothing in the parsed model, the JSON
    report or the schema recording how many interrogatives a diagram
    mixes. **Not a defect** — PlantUML diagram types are composites by
    construction — but a precise account of the altitude, in words the
    project did not have before.
  - **THE MEASUREMENT, and it is the contribution: the interrogative
    profile of the rule catalogue.** All 51 rules in
    `pumllint/rules/catalog.toml` classified by which Zachman
    interrogative they examine — **What 5, How 8, Where 0, Who 13, When
    15, Why 1**, plus **9 artefact-level** rules (about the diagram as a
    document, not the enterprise). **Who + When carry 28 of the 42
    enterprise-facing rules — 67%** — which is precisely the composite a
    sequence diagram is, and matches from the opposite direction what the
    DoDAF and TOGAF entries reached by counting framework artifacts.
    **First quantitative statement in the series of what pumllint's rules
    are *about*.** Reproducible from `catalog.toml`; the classification is
    a judgement and SEQ103/SEQ107/SEQ109 are the contestable cases, but
    moving all three puts no rule in Where, adds none to Why, and keeps
    Who+When above 60%. **Consult this before describing pumllint as broad
    enterprise-diagram hygiene.**
  - *Two numbers to state plainly rather than defend*: **Where = 0** —
    deployment and location are outside the parsed set by the scope
    decision recorded in the UML entry, so Zachman names the absence
    without giving a reason to change it; and **Why = 1** — GEN007, dormant
    until a pattern is configured, in the column Zachman practitioners
    most often say is neglected.
  - *Seventeenth ecosystem, no grader* (corrected form). Zachman defines
    completeness as **all 36 cells** — a checklist, not a score: no
    rating, no aggregate, no level. Third-party Zachman-based maturity
    assessments exist and none was examined.
  - *Access, fifth category — **trademarked***, after paid-and-partly-read
    (42010), gated-and-unread (TOGAF), open-and-read (DoDAF), and
    free-but-unread (NAF).
  - *Addition to the record, not a correction*: **ISO/IEC/IEEE 42010:2022
    itself cites Zachman** — 3.18 gives as its example that *"the labels
    given to the middle three rows (i.e. owner, designer and builder) of
    the Zachman framework correspond to stakeholder perspectives"*. Quoted
    from the standard's preview read during that evaluation; **the 42010
    note does not contain it**.
  - *Never build*: a Zachman cell recognizer, "36-cell mode" or coverage
    report (the framework prescribes no notation, so cell assignment would
    restate the diagram type under another name); **a primitive/composite
    distinction in the model** — the tempting one, and refused as a
    metamodel concept with the no-oracle shape (nothing says which
    interrogatives a diagram *ought* to mix, and every PlantUML type is a
    composite by construction, so the finding fires everywhere and means
    nothing); any Zachman coverage/alignment/completeness claim; rules to
    fill **Where** (settled scope decision); rules to fill **Why**
    (motivation lives in prose and requirement systems where `trace` and
    GEN007 already meet it — judging rationale is the
    well-formedness-as-a-type anti-goal in a new suit).
  - *Recorded, not queued*: (1) **the interrogative profile** (above) —
    the thing to update and check when a rule pack is proposed, not to
    re-derive; (2) **"composite" as the right word for pumllint's unit**.
  - Re-litigate on: **nothing an adopter can bring** — Zachman prescribes
    no artefact, so no user can arrive with a Zachman file, export or
    conformance requirement that touches a PlantUML linter. A rule-pack
    proposal that would change the profile's shape is the only event that
    makes this entry live again. **Not** on Zachman adoption in either
    direction: thirty-nine years without producing an artefact a linter
    could read.

- **FEAF / Gartner EA ecosystem (2026-08-28): no as a build — and the two
  halves reach it by opposite routes.** Eighteenth (full record:
  docs/feaf-gartner-ecosystem-evaluation.md; pumllint claims executed at
  `ad30b03`, default config, neutral cwd). **Access, sixth and seventh,
  in one note: FEAF is a US Government work and was read directly** (434
  pages, every FEAF quotation extracted from the OMB PDF); **Gartner is
  subscription-only and was not read** — its quotations are from press
  releases and trade coverage. The pattern holds: how a publisher
  publishes predicts readability far better than what it charges.
  - **FEAF confirms a mapping this series had only inferred.** FEAF v2
    (OMB, 29 Jan 2013) names ~50 artifacts across six sub-architecture
    domains — Strategic, Business Services, Data and Information,
    Enabling Applications, Host Infrastructure, Security — with **one
    required "core" artifact per domain**, and publishes an *"Other
    Framework Names"* column giving each one's DoDAF equivalent.
    Verbatim: **D-8 Event Sequence Diagram** = *"DoDAF SV/SvcV-10c"*;
    **D-7 State-Transition Diagram** = *"DoDAF SV/SvcV-10b"*; **S-1
    Concept Overview Diagram (core)** = *"DoDAF OV-1"*. The DoDAF entry
    assigned SvcV-10c to the `sequence` pack **by judgement**; FEAF
    publishes the equivalence normatively. **The framework-to-framework
    half of the mapping method is now externally corroborated** — the
    pumllint end of the chain remains this series' judgement.
  - *Measured*: **D-8 → `sequence`, D-7 → `state`, D-1 Logical Data Model
    (core) → `class`, all Level 4, all 100.00, zero findings, exit 0.**
    Cleanest sweep in eighteen — **and inflated**: the samples carry
    `@startuml <name>` and a `title`, so GEN001/GEN002 have nothing to
    say, where DoDAF's samples did not and scored 99.75–99.92. Defensible
    (FEAF artifacts are named, coded deliverables) but **the two notes'
    numbers are not comparable**, and no FEAF-beats-DoDAF reading is
    available. *No coverage count is attempted* — most of FEAF's ~50
    artifacts are catalogues, matrices and inventories, and counting them
    would be noise.
  - *Notation*: FEAF sits between DoDAF and NAF — it **names UML and BPMN
    as examples**, verbatim *"'open' industry standard notational formats
    that support model-based systems engineering"*, and mandates neither.
  - **GARTNER — the first market headwind in eighteen evaluations, and it
    is not answered here.** Gartner is the first subject that is not a
    framework, standard, notation or tool but a **commercial advisory
    practice**: nothing to lint, nothing to conform to, and the
    "ecosystem" is an argument. Its published position (research VP Brian
    Burke): **"Focusing on a standard EA framework doesn't work"**;
    practitioners historically **"focused on deliverables that were
    useful to enterprise architects but not valuable to senior
    management"**; **"stakeholders only value actionable and measurable
    deliverables"**. **That is a claim that architecture documentation
    fails on *relevance*, not *incoherence* — and pumllint measures
    incoherence.** Two readings, **neither adopted**: (a) the critique
    exempts pumllint, which gates diagrams developers already keep, tied
    to codegen and traceability — comfortable, partly true, and the
    seventeen prior refusals have tracked Burke's argument by instinct;
    (b) it includes pumllint, because a quality score is worth something
    only if the artefact is, and a maturity level is precisely the
    architect-facing metric he describes. **The threats column stays
    open**; adopting (a) would discard the one external critique the
    series has found. Same open question as 42030's abstention and
    TOGAF's aggregate-elsewhere, stated in plain commercial terms.
  - **The graded-object tally now runs to four, and none is a
    description.** ACMM grades an **organization's capability**; TOGAF
    Compliance an **implementation against a specification**; **FEAF a
    business service** (its services maturity matrix, "level 0"
    baseline); **Gartner a vendor or technology** (Magic Quadrant, Hype
    Cycle); ISO 42030 **declines to define an aggregate at all**.
    **Cite the no-grader streak with this list rather than as a count** —
    the field aggregates enthusiastically and consistently over something
    other than the artefact.
  - *Never build*: a FEAF artifact pack, "D-8 mode" or recognizer (FEAF
    prescribes no notation, so the code would label a sequence diagram
    and add nothing — third instance of this refusal, wording settled);
    any FEAF compliance or Federal-EA claim; anything premised on the
    three 100.00s being a result about FEAF (they are inflated by naming
    the samples); and **anything built to answer the Gartner critique** —
    it is about whether the artefact matters, which no rule, report or
    feature addresses.
  - *Recorded, not queued*: (1) **FEAF's confirmation of the
    cross-framework mapping**; (2) **the four-object graded tally**; (3)
    **the Gartner critique, unanswered**, with both readings and neither
    adopted.
  - Re-litigate on: **an adopter running pumllint on diagrams they
    already care about** — the only evidence that bears on the Gartner
    critique, and the same trigger the demand bar has awaited since the
    series began; a Gartner subscription becoming available, to check the
    critique against primary research rather than press coverage. **Not**
    on FEAF adoption — thirteen years old, prescribes no notation, and
    its artifacts are already reachable with nothing built.

- **ArchiMate viewpoints ecosystem (2026-08-28): no — and the hypothesis
  the note was opened to test did not survive its own research, which is
  the useful part.** Nineteenth, and a **narrowing return**: ArchiMate the
  *notation* was settled third (2026-08-27); this is its **viewpoint
  mechanism**, which that note did not examine. Full record:
  docs/archimate-viewpoints-ecosystem-evaluation.md. **Bounds: ArchiMate
  3.2 could not be read** — every Open Group host redirects to SSO, the
  same gate that defeated TOGAF — so **every verbatim quotation is
  ArchiMate 3.1 (C197, 2019)**, read as the Personal PDF Edition, and the
  3.2 catalogue is unknown to the note. **No ArchiMate tool was
  executed.** pumllint claims executed at `51bc97d` (v0.30.0), default
  config, neutral cwd. Research ran as a parallel workflow with an
  adversarial verification pass; corrected forms are what the note
  carries.
  - *The hypothesis*: an ArchiMate viewpoint is built by selecting a
    subset of element and relationship types, so viewpoint conformance
    looks **mechanically checkable** — rare in this series. **Three
    findings killed it.**
  - **(1) ArchiMate does not make view-to-viewpoint conformance a
    requirement.** Viewpoint = *"A specification of the conventions for a
    specific architecture view"* (§2.4); view = *"A representation of a
    system from the perspective of a related set of concerns"* (§2.3).
    The construction procedure is a subset selection, but the criterion
    for what appears in a view is **stakeholder relevance, an editorial
    judgement, stated as such**. Adversarial verification could not refute
    the load-bearing negative: **no normative rule anywhere in the spec
    makes a view's conformance to its viewpoint a requirement.** The 25
    example viewpoints (3.1, Appendix C) are **informative** — conformance
    requires the *mechanism*; supporting the examples is a **MAY**. A
    linter enforcing viewpoint membership would be **inventing a
    requirement the ecosystem declined to make**.
  - **(2) The ecosystem already drew the line, and it is our line.**
    Archi offers the 25 viewpoints as a per-view setting (default *None*)
    and applies **three mechanisms of increasing weakness**: it **filters
    the palette** (its help: *"only the elements permitted for the current
    Viewpoint are available in the Palette, whilst the others are not
    available"* — a hard input restriction), **ghosts** what arrives by
    drag-and-drop anyway, and reports *"Invalid elements in viewpoints"*
    as **one of eight opt-in Validator checkers, a WarningType, elements
    only**. What it declines to do is **block** the drag-and-drop. By
    contrast Archi **hard-blocks illegal relationships at authoring
    time**. **That is the ArchiMate note's N2 extending to viewpoints**
    ("legality is the settled anti-goal, and this ecosystem enforces it
    upstream by construction") — refused under the existing never-build,
    not a new one. *(A draft of this entry said Archi "does not enforce"
    and "never blocks"; the workflow's adversarial pass refuted it from
    Archi's own shipped help. The corrected picture is stronger: the
    ecosystem has not ignored viewpoint conformance, it has calibrated
    it.)* **Two spec details defeat naive containment checking anyway**:
    *"the grouping element, junction, and or junction can be used in every
    viewpoint"*, and Layered permits *"all **core** elements"* — core
    excluding Motivation, Strategy and Implementation & Migration — so
    **no 3.1 viewpoint permits everything**, while Archi implements
    Layered as literally-everything-allowed. **Tool and specification
    disagree**, a further reason no third party should adjudicate
    membership.
  - **(3) A controlled experiment — the series' cleanest measurement.**
    Two ArchiMate views **identical in structure, glyphs and element
    count**, differing only in element type and layer: one conformant to
    the Application Cooperation viewpoint, one violating it with
    business- and technology-layer elements it excludes. Both →
    `sequence`, **Level 4, 90.00, 8 elements, 4 false SEQ009s** —
    **byte-identical output**. Identical again under `--profile codegen`
    (both **Level 2, 47.50, 4 blockers**). Replacing the declared
    viewpoint with a *wholly fictitious* one also changes nothing: the
    title is opaque text. **Viewpoint conformance is not partially
    visible; it is exactly invisible**, and profile-independently so.
  - *A deeper reframe, and it belongs to this note*: **PlantUML does not
    model ArchiMate element types either.** `archimate` is a single-line
    *element command* in the Description Diagram factory — PlantUML
    classifies it among **53 element-type keywords** beside `rectangle`
    and `node`; there is no ARCHIMATE diagram type, `@startarchimate` is
    rejected, the element becomes a generic description leaf with **no
    element-type field**, the `<<element-type>>` stereotype is
    string-interpolated into a sprite path with **nothing validating it**
    (a nonexistent type is accepted silently), and the layer colours are
    seven ordinary named colours. **So the property is absent from the
    artefact, not merely unread** — a stronger statement than "pumllint
    does not recognise the keyword".
  - **THE ONE NEW MEASUREMENT — third amendment to candidate 1.** The
    ArchiMate note's §8.1 arrow table has **two** outcomes
    (`unknown`/L1, or `sequence`/L3–4). Extending it with the glyphs
    practitioners use for named ArchiMate relationship types produces a
    **third**: composition `*-->` → `unknown` L1 95.00 (0 elements);
    **realization `..|>` → `class`, L4, 99.31**; serving `-[#black]->` →
    `sequence` L3 88.19; association/aggregation/triggering/plain →
    `sequence` L4 90.42. **The realization row is the worst case in this
    ecosystem and the quietest instance on record**: typed as a
    *different diagram type*, scored **99.31**, and **completely
    silent** — only "no title"/"no name", where the sequence-typed cases
    at least emit false SEQ009s. Mechanism is exact and is **not a
    fallback**: `_TYPE_MARKER_ARROW = re.compile(r"<\||\|>")`
    (`parser/class_.py:67`) and `parser/class_.py:161` set
    `diagram_type = "class"` on `<|` or `|>` **independent of any `class`
    keyword** — confirmed across `..|>`, `--|>`, `<|..`, each `class` L4
    97.92. The ArchiMate note tested `..>` (no bar) and got `sequence`:
    **one glyph character apart, a different kind of diagram.**
    *Amendment*: candidate 1's type-marker set does not only **omit**
    declaration keywords, it **mis-fires** — a fix that widens keywords
    alone leaves this cell wrong, and must be validated against a
    realization-glyph file as well as the foreign-diagram and YAML shapes
    the two earlier amendments named.
  - *Intersection with the pack set is near-empty, consistent with
    TOGAF*: research found **no sequence-shaped viewpoint** among the 25
    — upheld under verification but with the evidence flagged fragile, so
    it is a conclusion and **not a count**. ArchiMate viewpoints are
    structural and relational; the Zachman entry measured pumllint's rule
    mass at **67% Who+When**. Third data point for the same rule:
    **fit tracks whether a framework asks for time-ordered interaction
    models** — TOGAF `sequence` 0/32, DoDAF 3/52 with an any-notation
    permission, ArchiMate viewpoints none.
  - *Access, eighth data point, and a new resolution*: **current edition
    gated, previous edition readable.** TOGAF yielded no primary text at
    all; here 3.2 is behind the same SSO but **3.1 is a published Personal
    PDF Edition and was read**, so the note has verbatim spec quotations
    one version behind and says so in every one.
  - *Nineteenth ecosystem, no grader* (corrected form; cite with the
    four-object tally, not as a count).
  - *Never build* — **every refusal extends an existing never-build,
    which is what a mature record should do on its nineteenth
    evaluation**: a viewpoint-conformance rule (ArchiMate N2);
    viewpoints/views/stakeholders/concerns as model concepts (42010 N2);
    anything premised on ArchiMate element types being readable (they are
    not in the artefact); **and presenting any of this as a new defect
    class** — the type-fallback class was characterized and closed in the
    ArchiMate note, §8.3 is a sharper demonstration of it and §8.4 an
    amendment to its candidate, and the record must not read as though a
    nineteenth note found a nineteenth defect.
  - Re-litigate on: **ArchiMate 3.2 becoming readable** (to check the
    §1.1 negative against the current edition); ArchiMate making
    view-to-viewpoint conformance normative in a future edition — the one
    change that would reopen this, with no sign of it. **Not** on Archi's
    Validator gaining strength: that is the ecosystem doing its own job
    upstream, which is the reason for the refusal rather than an opening.

- **C4 viewpoints / notation (2026-08-28): the settlement is unchanged —
  *fit verified, wait for census pull* — and the contribution is a
  *reason*, not a finding.** Twentieth, and the **second narrowing return
  in two turns** (ArchiMate viewpoints was nineteenth). Full record:
  docs/c4-viewpoints-notation-evaluation.md; pumllint claims executed at
  `9e14f02` (v0.30.0), default config, neutral cwd. **c4model.com is free
  and was read directly** — ninth access data point and the best case,
  after ArchiMate 3.2 and TOGAF both behind Open Group SSO.
  - **The doctrine explains the C4 note's 40% ceiling.** That note
    measured C4's 21-item checklist as roughly **40% mechanizable** from
    `.puml` text and attributed the rest to *"the rendered picture"* —
    correct but incomplete. C4's own notation page: **"The C4 model is
    notation independent, and doesn't prescribe any particular
    notation."** and **"Any notation used should be as self-describing as
    possible, but all diagrams should have a key/legend to make the
    notation explicit."** **C4 is picture-heavy in its guidance *because*
    it refuses to specify a notation** — when shapes and colours are the
    author's free choice, all that is left to review is whether they were
    chosen sensibly (the image) or *declared* (the legend). So the
    source-checkable residue is small **structurally, and no parser work
    moves it**. *Attach to the C2 correction so the 40% is never read as
    a coverage gap better engineering could close.* This does not weaken
    the recorded fit: the pack's value was always tiers 2 and 3, which
    that note calls "this project's own design".
  - *Measured — C4's one unambiguously source-checkable requirement is
    invisible in **both** spellings.* PlantUML `legend`…`endlegend`
    present vs absent → identical (`sequence`, L4, 100.00, 7 elements);
    C4-PlantUML `SHOW_LEGEND()` present vs absent → identical
    (`unknown`, L1, 100.00, 0 elements, "✔ No issues found", exit 0).
    Byte-identical reports in both pairs.
  - **But the parser already tokenises legends**, which makes the
    recorded candidate cheaper than it looked: `RE_LEGEND_START` /
    `RE_LEGEND_END` at `parser/sequence.py:91-92`, with a deliberate
    swallow at `:249-251` — *"Legend blocks are display furniture:
    swallow until 'endlegend' so body text can never parse as live
    messages or participants."* Correct for a parser hunting model
    content, and it means *"is a legend declared?"* needs **no parser
    work for the PlantUML spelling**. The `SHOW_LEGEND()` spelling
    remains the macro-reading problem the pack already has.
  - *The honest Level 1 and the blindness are one behaviour seen from two
    sides*: a complete C4-PlantUML container diagram scores `unknown`,
    **Level 1 (Sketchy), 100.00, 0 elements, exit 0** — the honest result
    the C4 note recorded, re-confirmed at v0.30.0 — and it is invisible
    to the legend question for the same reason (no macro content is
    read). Worth stating once rather than recording as two findings.
  - **Viewpoint-shaped mechanisms are guidance, not contracts — second
    instance in two turns.** C4's four levels of zoom, each for *"a
    different amount of detail for a different audience"*, are 42010's
    viewpoint idea in plain words, and **C4 defines no conformance**;
    ArchiMate publishes 25 viewpoints *with* element subsets and still
    makes conformance no requirement. Stated once so a third ecosystem
    does not re-derive it, and as the general reason a third-party linter
    adjudicating a viewpoint would be **inventing an obligation**.
  - *Nothing here is new as a candidate.* The legend rule, abstraction
    mixing (a **PlantUML-only defect**), the 40% figure, the census
    exclusion guard and the codegen amplification are all on record in the
    C4 note; this entry adds an explanation, an implementation cost and a
    measurement, and **the record must not read as though a twentieth
    note found a twentieth gap**.
  - *Never build*: anything premised on the doctrine being demand (the
    trigger is unchanged); **a notation-conformance check** — C4
    prescribes no notation, so it would enforce this project's idea of C4
    against a model that declines to have one; a level-conformance check
    (already inside the waiting pack as abstraction mixing); and quoting
    the macro file's 100.00 without its Level 1 and zero element count.
  - Re-litigate on: **the C4 settlement's existing triggers, unchanged** —
    an adopter's own census after the exclusion rule, a concrete user with
    hand-written C4-PlantUML asking for a gate, or a vendor shipping
    quality checking for C4-PlantUML specifically. **Not** on anything in
    this entry: it explains the ceiling and does not touch the conditions.

## Working agreements (read before picking anything up)

- Scores are a public contract: any change that shifts corpus scores must be
  deliberate — the golden test enforces it; re-freeze consciously with
  `python tools/calibrate.py --freeze tests/golden_scores.json`.
- Claim language is settled (SCORING.md §9): Level 5 is "method-convention
  complete", never "guaranteed generation-ready"; the evidence-backed pitch
  is the correlation and the below-Level-2 cliff.
- The zero-dependency promise holds: product code and its tests must run
  under `python tests/run_tests.py` with the stdlib only.
- **The product path is deterministic end-to-end.** No LLM call ever
  ships inside pumllint itself: the forward leg of the requirements
  pipeline (prose → model authoring), k-fold generation, and judging
  live in `tools/` and docs/agents.md. What ships in the product —
  linting, scoring, fixing, and (when built) tracing, verbalizing,
  diffing — is deterministic code over the parsed model, byte-stable
  where output contracts say so.
- **docs/sdlc-tooling-landscape.md is the source of truth, and a second
  rendering of it exists off-repo and is deliberately out of date.** A
  separately-authored HTML version (own layout, its own provenance line)
  was published for a management audience and sits at **rev. 2** — the
  whole rev. 3 specification-quality stream and the rev. 4 caveats are
  missing from it. Nothing in it is false; it under-claims. Verified and
  decided 2026-07-27: **not synced**, because its source file is gone and
  any redeploy means reconstructing the page from a fetched copy — the
  inline Wardley SVG and the dark-mode blocks are what break. If it is
  ever brought current: **graft the missing sections, never regenerate
  from this markdown** (the two are not the same document), stage to a
  throwaway target and diff before touching the live one, and leave its
  audience-specific tag wording alone unless asked. Revise this doc
  freely in the meantime — the divergence is accepted, not a debt.
- Recommended next: **Arcs A–D are complete** — including the
  execution-oracle and cross-vendor waves (2026-07-26) and the
  agent-repair wave (2026-07-27) — and the report
  shapes are schema-pinned (0.18.0). No committed follow-ups remain;
  everything is strictly demand-driven: Arc E's LSP server and SonarQube
  plugin (wait for pull — see the re-evaluation notes on each item),
  Arc F's AI-authored-rules safeguards (build when rule authoring becomes
  a recurring pipeline). Auto-improvement is a settled question (see
  *Settled questions*): measurement and evidence-dossier surfaces on
  demand, never an unattended promote-on-delta loop. The adjacent
  verifier categories from the tooling-landscape research
  (docs/sdlc-tooling-landscape.md) are likewise settled: watch, don't
  build (see *Settled questions*) — as is markdown-embedded PlantUML
  extraction, demand-tested 2026-07-26 and failed
  (docs/demand-scan-embedded-plantuml.md), and the obligation/flow-checking
  designs, recorded gated 2026-07-30 (see *Settled questions*). The
  requirements-pipeline arcs (G–J, specified 2026-07-29 from the verified
  reassessment — docs/prose-pipeline-evaluation.md) are the newest
  thread: **Arc G shipped in v0.25.0** (`pumllint trace`, 2026-07-29,
  owner go) — next in line is Arc H (verbalizer), strictly on its
  trigger: a pilot/adopter asking for the review aid.
- **Next action (2026-07-30): not code but measurement — run the pilot
  census on the real corpus** (`tools/pilot_census.py`, read-only,
  standalone-copyable; charter and phased gates in
  docs/pilot-charter.md; kit verified end-to-end at v0.26.0 against the
  wild tier). The census output is the demand instrument the gated
  items wait for: C4 macro counts → the C4 pack; `!include` usage →
  include resolution; a requirement-ID convention from the conventions
  workshop → `pumllint trace` adoption (shipped, zero work); a
  review-aid ask → Arc H; an architect iterating config in the
  calibration week → `--shadow-config` (the one shelved
  auto-improvement component whose trigger the pilot can fire); the
  modelling-standard owner confirming an obligation table →
  obligation/flow Phases 2–4 — in which case build the remaining Arc F
  safeguards first (see Arc F's trigger note). *Dated note,
  2026-08-11: the census ran end-to-end on a public wild corpus — 159
  files / 174 diagrams from five public repositories (record:
  docs/pilot-census-first-contact.md; data:
  pilot_results/first_contact/). Instrument verified at scale (0.6 s,
  zero hard parse failures); the dialect signals are loud on public
  material (C4 macros in 73/159 files, `!include` in 118/159; 103/174
  diagrams dialect-invisible, held at Level 1 by the zero-element cap
  while their composite is vacuously high). This was prevalence
  measurement, not adopter pull: the phase-0 census on the pilot
  organisation's real corpus — and every demand gate above — stays
  open as recorded.*
- **Research track (accepted 2026-08-10): docs/research-charter.md is
  the source of truth for the measurement-wave program.** W0 shipped
  with the charter (2026-08-06, `stack_experiment/`); W1–W5 each take
  their own owner go with a frozen pre-registration and per-wave
  ceiling; W6/W7 keep their prior triggers above. The charter changes
  no product behavior and queues no build; it is revised in place,
  dated, as waves land. Acceptance was de facto at the 2026-08-06
  merges (PRs #18/#19); recorded here per charter §10.
