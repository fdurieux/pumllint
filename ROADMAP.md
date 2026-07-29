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
actually becomes a recurring pipeline rather than occasional sessions:

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
- [ ] **Corpus-firing report** — beyond pass/fail golden scores, run the new
  rule over the calibration corpus (and wild tier) and emit where it fires
  and how often, as a human review artifact. Catches "semantically wrong but
  golden-neutral" rules; this is the analysis that forced GEN006/GEN007's
  dormancy decision, made routine.
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

## Arc G — Requirements traceability (gated; first build on trigger)

- [ ] **Coverage matrix command** — given the diagrams plus a
  requirements inventory (a plain ID list, or a file/tree scanned with
  the project's GEN007 `pattern`), report both directions: which
  requirement IDs are realized by which diagrams, which IDs no diagram
  references, which diagrams reference nothing. Text + json (schema
  contract discipline applies), exit-code gate in the `--min-level`
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
  (docs/demand-scan-embedded-plantuml.md). The requirements-pipeline
  arcs (G–J, specified 2026-07-29 from the verified reassessment —
  docs/prose-pipeline-evaluation.md) are the newest gated thread: Arc G
  (traceability matrix) is first in line, on a configured
  requirement-ID convention or owner go.
