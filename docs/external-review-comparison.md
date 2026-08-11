# The two-stage external review, compared run by run

*Dated companion note, 2026-08-11 — companion to [the claim-by-claim
evaluation](external-review-evaluation.md) of the same externally
authored two-stage review. Sections 1–3 are the owner's side-by-side
distillation of the review's two runs ("Spec Driven AI Codegen
Research"); the fourth column of §1, the scores note in §2, and §§4–5
were added by Claude (Fable 5) at the owner's request. Source
conversation retained by the owner; not linked here (same practice as
the evaluation note).*

Side-by-side comparison of the two evaluation runs:

- **Run 1 — Initial evaluation** ("Executive assessment"): after W1
  was published, with W2–W4 still preregistered drafts.
- **Run 2 — Revised evaluation** ("Revised headline"): after
  completed W2–W4 results (dated 11 Aug 2026) were published.
- **Column 4 — Claude feedback** (added 11 Aug 2026, Claude Fable 5,
  at the owner's request; not part of the external review): a per-row
  re-evaluation against the repository's frozen records (wave
  pre-registrations § Results, research charter, ROADMAP.md) and
  against what has landed since Run 2 — chiefly the W5 run. Sections
  4–5 below are additions from the same pass; the fuller
  claim-by-claim evaluation of both stages is
  [external-review-evaluation.md](external-review-evaluation.md).

---

## 1. Topic-by-topic comparison

| Topic | Run 1 — Initial evaluation (after W1, before W2–W4) | Run 2 — Revised evaluation (after W2–W4) | Claude feedback — sense, fit, gaps (11 Aug 2026) |
|---|---|---|---|
| **Headline conclusion** | Keep the project as foundation, but don't make PlantUML/pumllint the centre of the solution. Core principle: deterministically verify every authoritative artifact, generate against a selected subset, verify against independent oracles. | Headline sharpened into an *operating envelope*: codegen needs sufficient authoritative information, in carriers the model reliably consumes, without contradictions and without unnecessary context. Both too little **and too much** information reduce correctness. | **Sense — and epistemically stronger than Run 2 credits: the envelope is a pre-registered frame *confirmed*, not a lesson discovered** (charter §2 formulated minimum sufficiency before the waves ran; §8.2 was its named falsifier and did not fire). Two scopings before quoting it: the two sides carry asymmetric evidence — too-little is generator-general (the cliff spans three generators, two vendors), too-much is weak-generator-borne at the measured doses (1.12–1.45×; opus flat-to-ceiling). The repo has since written this synthesis down in one place (docs/minimum-sufficient-stack.md); quote that, not the review. |
| **Most important finding** | "Specification quality matters, but a verifier can only verify that information has been *stated* — not that it is *true*." Mechanical omission → agent may repair; semantic omission → agent must ask, not invent. | Three empirically evidenced failure mechanisms: underspecification (model must invent), inconsistency (model silently resolves), overspecification (relevant information diluted, especially for weaker models). | **Sense as taxonomy; two things fall out of it and must not.** Run 1's "stated ≠ true" is not superseded — no wave tests spec truth, so independent oracles remain the only guard against a wrong-but-consistent spec. And the largest measured below-cliff lever has no slot: the author/ask loop (ask-vs-invent ≈ 27 pp executed) is the *measured* recovery for underspecification — route the absent decision to a human — and it keeps vanishing from the review's syntheses (flagged for both stages in docs/external-review-evaluation.md). |
| **Conflicting specifications (W2)** | W2 still a draft preregistration; rated "one of the highest-value experiments" for banking. Fail-closed behaviour recommended — but noted that agents.md's precedence ladder was adopted by reasoning, not demonstrated experimentally. | **0 of 18** implementations surfaced the inserted contradictions — every model silently reconciled them. Nuance: models mostly chose the *right* source (decision table 6/6, formula 12/12), but silent resolution is still an unauthorised governance decision. Conflict detection **before** generation is now mandatory. | **Sense — the both-halves reading (total silence AND mostly-right source choice) matches the frozen record, and "silent resolution is still an unauthorised decision" independently re-derives agents.md's updated position.** Two scopings the capsule drops: W2-E2's 6/6 was won "under in-band deference hints — scope as frozen", deliberately *not* clean precedence-ladder evidence; and no stale-adoption event was observed anywhere at this n (the one majority-arm miss was a type-handling bug) — so the measured case for the gate is governance (surfacing never emerges), not outcome loss. Unused ammunition: W2-E5, conflict damage stayed local (all non-discriminators within 9 pp) — the beginning of the blast-radius argument the reviewer's own gate architecture needs. |
| **Proposed conflict architecture** | "Specifications → AI agent → if conflict, ask" (prompt-level stop-and-ask, per agents.md). | That architecture judged **too weak**. New design: specification graph → cross-spec validation → HARD STOP + human decision on conflict; the LLM should ideally never receive a knowingly contradictory package. Stop-and-ask is harness work; it does not emerge on its own. | **Sense as harness design; "mandatory" and "too weak" outrun the measured case.** What W2 measured: surfacing is not emergent, and in-band authority cues don't make it emerge — which also cuts Run 1's later metadata instinct (honoring an `authority:` field is harness work too). What it did not measure: outcome harm — sources mostly resolved correctly, damage stayed local, and the stale worked example was outcome-harmless at this dose. The hard stop is still right for a regulated adopter, on governance grounds. Missing design element: blast-radius triage — scope the stop to the task's context projection, or a standing conflict backlog halts all generation. |
| **Carrier / DSL syntax (W3)** | W3 preregistered; strongly endorsed. Working hypothesis: at fixed information, carrier syntax probably won't matter much → choose DSLs for deterministic checkability, maintainability, ecosystem — not LLM preference. | **Hypothesis overturned.** Carrier is an outcome variable: PlantUML 43.9% > code stub 37.9% > Mermaid 34.8% > controlled English 28.8% > YAML 13.6% overall execution; Opus produced non-compiling Python in all 3 YAML runs. Preregistered carrier-equivalence hypothesis failed. | **Sense on the refutation — a pre-registered equivalence hypothesis failing is the strong, publishable claim. Treat the full ranking as fragile.** Mid-table gaps sit within cross-occasion noise at n = 3/condition (W5's run notes record a double-digit single-shot re-sample swing on this same substrate); the defensible ordering is PlantUML ≥ code-stub ≈ Mermaid > controlled English > YAML. The opus-from-YAML 3/3 non-compiles are the programme's *only* non-compiles anywhere — worth a root-cause read before "YAML is catastrophic" hardens into policy. For the codegen goal, the sharp implication: the worst carrier was the most machine-structured one — a warning shot for feeding raw enterprise machine formats (BPMN XML et al.) to generators, and the reason the adopter benchmark must test its real carriers. |
| **"PlantUML is best" / YAML assumption** | Not addressed (no data yet); suggestion to eventually add BPMN 2.x XML and DMN/FEEL to the carrier experiment. | Caution: frozen prompt referenced "PlantUML sequence diagram", so W3 measures carriers *inside a PlantUML-oriented harness* — do not conclude "use PlantUML everywhere". Separately: "machine-readable to a parser ≠ cognitively optimal to an LLM" — the structured-YAML instinct is unsafe. W3b follow-up needed (neutral + carrier-specific prompts). | **Sense — the review's best habit on display: this caution is W3's own disclosed limitation (the PlantUML-framed frozen prompt), correctly weaponised rather than discovered.** W3b is since recorded in ROADMAP as a wave candidate under charter discipline (own pre-registration, ceiling, owner go; nothing queued). One implication the review stops short of: carrier legibility is plausibly training-distribution-dependent, hence *model-version*-dependent — carrier choice belongs inside the per-model generation profile (see the universal-stack row) and reopens per information class, not once for the whole stack. |
| **Carrier assessment framework** | Implicit: mechanical checkability weighted very heavily. | Explicit four-axis framework: semantic completeness, **LLM legibility**, mechanical checkability, human maintainability — with LLM legibility promoted to first-class alongside checkability. | **Sense — graded in-house as "a sound generalisation of charter C1's demotion branch."** To become decision-grade it needs a measurement procedure per axis (LLM legibility is benchmarkable per model × version — W3 is the template; checkability can be catalogued per artifact type) and per-information-class application. Candidate fifth axis for the adopter: **deterministic derivability** — whether human renders can be generated mechanically from the authoritative carrier — which is what makes the single-source rule (below) workable in practice. |
| **Over-specification / context dose (W4)** | W4 preregistered; "more context is better" already looking false — preliminary signal from W1 (stronger model −3.6 pp when Gherkin added at ceiling). Distinguish authoritative knowledge base from generation context. | **Confirmed and quantified**: vs full-stack baseline, accurate redundancy −6.7 pp, irrelevant context −11.2 pp, accurate exhaustive enumeration −14.3 pp (pooled). Weaker model (Haiku): −10.9 / −26.1 / −32.1 pp; Opus stayed at ceiling. Extra information doesn't have to be *wrong* to be harmful. | **Sense, and the enterprise-counterintuitive lead is the right one: *accurate exhaustive enumeration* hurt more than irrelevant context (the wave's own directional miss, published as such).** Keep the frozen scopings when quoting: accurate redundancy alone (O1, −6.7 pooled) sat *below* the programme's 9 pp materiality bar — the measured breaches are O2/O3, weak-generator-borne, at doses of 1.12–1.45×. And W1-E5's exact null (below-cliff ≈ absent in a prose-redundant stack) still cuts against simple redundancy-harm stories. Dilution is real, dosed, and generator-scoped — quote all three properties together. |
| **Context compiler** | Sketched as "context builder" in the specguard/specgraph concept; retrieval boundary "should be determined experimentally". | Now "one of my strongest architectural recommendations", with direct experimental support from W4: compile the minimum sufficient task-specific projection of the spec graph; never hand the agent the whole repository. | **Rationale measured; "direct experimental support" overstates the mechanism.** W4 varied dose at fixed task — it never varied selection or retrieval, so the compiler as a mechanism is untested (the reviewer's own stage-1 "selective-context experiment" remains future work), and building it is adopter-programme scope, not repo scope (recorded boundary). W5 has since supplied the strongest argument *for* it: iteration fixes only what visible tests cover — an agent cannot buy back information the context never carried — so selection quality stays load-bearing even in agentic workflows. |
| **Universal minimum stack** | W1's cross-generator disagreement (behaviour vs contract dominance flipped between models) suggests there may be no permanent universal optimal stack — stable information model + capability-dependent context selection. | **Proven no universal minimum stack**: generator-specific knees confirmed (Opus knee at A3, Haiku at A4). New construct: stable enterprise truth (spec graph) vs model-specific generation profile; *model version becomes part of the build configuration*. | **Sense, minus the word "proven".** At two generators × 3 runs this is an existence proof of generator-dependence (knees opus A3 / haiku A4; the top lever disagrees per generator — the §8.3 partial fire already forces per-generator claim language), not a calibrated profile. The operational corollary is the quotable part: model version enters the build configuration, and charter C1's re-measure-per-generation instrument *is* that discipline. Cheapest hardening: a cross-vendor replication of the W1 ladder — the cliff already spans two vendors, but the wave levers are Claude-family-only so far, and the lab's Gemini shim exists. |
| **Single source of truth** | Motivated by maintenance drift and agent-context ambiguity; proposes document metadata (authority, supersedes, derived documents). | New, AI-specific reason: even non-drifted duplication damages generation (W4). Author once in the authoritative carrier (e.g. DMN), render/derive everything else. | **Right rule, wrong headline evidence, unvalidated example.** "Even non-drifted duplication damages generation" leans on O1, which did not breach the materiality bar — the strong form rests on O3 (enumeration) and is weak-generator-borne. The sound core survives: author once, derive deterministically, and keep derived renders *out* of generation context (they are dose). But "(e.g. DMN)" presumes an LLM-legibility result DMN does not have — after W3, authoritative-carrier choice per information class is an outcome question the adopter benchmark must answer, not a governance default. |
| **Contract bundle (A3) decomposition** | "Contracts are most important" NOT established — A3 bundles spec + decision table + OpenAPI + state model, so the +37.9 pp cannot be attributed. Needs a factorial/ablation layer "as a later experiment". | Still "the biggest unresolved issue in the current results". Elevated to one of three immediate post-W5 workstreams; without it the original question (state diagram? OpenAPI enough? DMN needed?) cannot be answered with empirical precision. | **Agreed — and it is now a recorded wave candidate (ROADMAP, under charter discipline: own pre-registration, ceiling, owner go if queued).** Precision: W1's leave-one-out arm already prices whole-class removal from the full stack (largest drop −55.2 pp, the contract class); what is open is attribution *inside* the A3 bundle — companion spec vs decision table vs OpenAPI vs state model. Sequencing consequence the review misses: A3 decomposition's result determines what a domain benchmark must contain, so it belongs *before* any benchmark freeze. |
| **W5 (agentic loop)** | "W5 is more important than W2–W4" — the external-validity keystone; recommended sequence: finish W2–W4, *then* prioritise W5. | **W5 is now the immediate priority**: test whether all four wave effects survive when the agent can inspect the repo, compile, run tests, retrieve context and repair. | **Sense — but it recommends the charter's already-recorded priority (W0 → W1 → W5), convergent rather than novel, and it never engages the W5 design that was already committed** (visible/hidden smoke split, k ≤ 2 revision loop, in-wave single-shot baselines). Note the scope: W5 tests the cliff and the contract lever under agency, not all four wave effects — carrier and dilution survival under agency remain open. **Since overtaken: W5 ran 2026-08-11 ($7.95 of $40, zero protocol deviations). The keystone held — see §4 below.** |
| **External validity** | 5/10. Direction believed; magnitudes (21.9 pp cliff, Level-2 threshold) must not be generalised to banking. Banking pilot indispensable. | Barely moves: 5.5. Still one toy CargoQuote system, mostly two Claude generators, 3 runs per condition, single-shot, Python. Take the *principles* seriously, be cautious with *magnitudes*. | **The review's most creditable habit — it polices its own enthusiasm; 5.5 was right when written.** Post-W5, the single-shot limitation — the largest single component of that caution — is retired up to k ≤ 2: standing claim language program-wide now reads "single-shot and k ≤ 2 agentic". Remaining threats in order: one toy substrate; wave levers measured on one vendor's models (the cliff itself spans two vendors); n = 3/condition (the record itself flags a double-digit cross-occasion swing); Python-only; k ≤ 2 is not long-horizon agency. |
| **Banking applicability** | 4–5/10 today; proposes 20 banking information classes (BPMN, DMN, journeys, state models, AsyncAPI…) and a mortgage/loan benchmark with non-canonical rules. | Raised to 6. Mortgage/loan benchmark now one of three parallel next steps, using the real artifact hierarchy (journey → L2/L3/L4 → capability → module → interaction → contract → rule → state → verification), leading to a "Banking AI-Codegen Specification Profile". | **Fit for the reviewer's programme; keep the boundary and one conflation visible.** The benchmark and profile are adopter-programme work — the repo records them explicitly out of scope (CargoQuote is domain-neutral *by construction*; it exists to kill domain priors). The 6 conflates research relevance (fair) with deployability toward "no unsupported behaviour reaches production" — W2 and W5's invention-persists result argue for *less* trust in ungated generation, not more; Run 1's 3/10 on that dimension has not moved. And stage 2 silently dropped the external-validity leg stage 1 called critical: the foreign-corpus pilot. The benchmark discipline it does specify (non-canonical values) is right — it is CargoQuote's own lesson applied. |
| **Research charter** | "Probably the best document in the repository"; adopt its information-vs-carrier distinction as a fundamental principle. | "Considerably stronger now" — correctly absorbed W2 (0/18), W3 (equivalence refuted), W4 (far-side dilution), model-specific knees; minimum sufficiency keeps an *outcome* justification, not merely cost. | **Agree — and the review is itself the evidence: it practices the house claim discipline (gaps and orderings, judged vs executed kept apart, per-generator scoping) without having been told it, which is independent proof the discipline is legible from the artifacts alone.** Since Run 2, the charter's promised consolidation exists: docs/minimum-sufficient-stack.md (shipped 2026-08-11 with its own adversarial pass), including "§5 The workflow transfer — it all survives agency". The synthesis no longer lives only as dated notes in three places. |
| **Documentation issues** | Several: rename Level-5 "Generation-ready" (→ Codegen-constrained); duplication across README/EVIDENCE/case-for/etc.; case-for-pumllint.md overreach; proposal for YAML doc metadata; full 30-document corpus assessment. | One issue remains: EVIDENCE.md doesn't yet contain W2–W4 results while the charter does — make the product-evidence vs research-synthesis boundary explicit, or agents will miss W1–W4. | **Both defect findings verified real and previously unrecorded — the review's concrete repo-side value.** Status now: the Level-5 rename is *decided* (owner, 2026-08-11: "Method-complete" at the next release — matching the settled description verbatim, not the reviewer's "Codegen-constrained"; agents.md's false "deliberately not called" sentence gets fixed with it). The EVIDENCE.md boundary is a recorded doc-hygiene candidate, not yet executed — EVIDENCE.md still carries zero stack-wave content today; the fix is one scope paragraph pointing at the pre-registrations' § Results and minimum-sufficient-stack.md. Run 1's YAML-metadata remedy stays rejected three ways: it mechanizes routing, not consistency; YAML fights the repo's stdlib-parseable rule; and W2+W4 cut its premise (in-band authority cues don't surface; added material is dose). If the drift class recurs, the recorded direction is a deterministic claim-language guard test — detection, not declaration. |
| **Target architecture** | "Specification verifier framework" (specguard/specgraph): per-artifact linters → cross-spec verifier → codegen gate; pumllint as one plug-in. | Same shape, but clearer and extended: spec graph → per-artifact verifiers → cross-spec verifier (conflict/drift/IDs) → **context compiler (task + model specific)** → coding agent → independent verification (contract/acceptance/invariant tests). | **Right shape; "the waves point toward it" reads as derivation and isn't.** The pipeline is stage 1's own specguard picture, drawn before W2–W4 ran; the waves upgraded exactly two boxes to measured rationale (cross-spec verifier via W2 — the *need* leg, not harm; context-compiler rationale via W4), while the carrier lineup, invariant tests and the BPMN/DMN/AsyncAPI graph stay hypothesis. W5 has since moved the coding-agent box in the review's favor: iteration fixed only what visible tests covered, so the upstream artifact and gate stages keep their weight on a measured basis. Structural gap unchanged: the only stop-for-humans is the conflict hard stop — the measured underspecification recovery (the ask loop, ≈27 pp) has no box. As drawn, the pipeline automates away the highest-value human touchpoint the lab has measured. |
| **Recommended next steps** | Finish W2–W4 → prioritise W5; in parallel *design* (not execute) the banking benchmark and cross-artifact spec graph; then mortgage/loan benchmark; plus added experiments (contract decomposition, carrier replication, conflict, traceability, selective context, maintenance W7). | W5 immediately; then three workstreams in parallel: (1) A3 decomposition, (2) W3b carrier replication + BPMN/DMN tests, (3) realistic mortgage/loan banking benchmark. | **Half historical, half right, one boundary.** W5 is done (§4 below). A3 decomposition and W3b are recorded candidates awaiting owner go — with A3 properly sequenced *before* any benchmark freeze, since its result decides the benchmark's artifact set. The benchmark itself is adopter-programme work, not repo work. Missing from both runs' lists: the foreign-corpus pilot leg (the repo-side external-validity move stage 1 itself called critical), and a cross-vendor replication of the wave levers (cheap — the lab's Gemini shim exists; the cliff is already two-vendor, the levers are not). |
| **Closing lesson** | Reframed research question: *what information must be authoritative, how represented so humans and machines can verify it, how is the relevant subset selected, and what independent gates guarantee unsupported behaviour cannot silently pass?* | Sharpened: *"The problem is not maximizing documentation. It is minimizing the amount of interpretation the AI must perform — while minimizing the irrelevant or duplicated material it has to process."* A stronger foundation for the near-zero-hallucination ambition than Run 1 credited. | **The most quotable sentence in either run — quote it with its four scopings** (graded fully in docs/external-review-evaluation.md): (1) it is a pre-registered frame confirmed, not discovered — which *raises* its status; (2) the two sides carry asymmetric evidence (too-little generator-general; too-much weak-generator-borne at measured doses, with "duplicated" its weakest leg); (3) the two-sided form folds away the third mechanism the review's own headline named — silent arbitration is interpretation performed *well*, a governance problem precisely because minimize-interpretation language doesn't catch it; (4) the ambition has a measured floor — no configuration was hallucination-free, and the author loop halved invention (98 → 45) without eliminating it. The honest target is the reviewer's own earlier phrasing: zero *undetected, unauthorized* invention. |

---

## 2. Scores

### Run 1 — original scoring dimensions ("Executive assessment")

| Dimension | Run 1 score |
|---|---|
| Quality of pumllint as deterministic PlantUML semantic linter | 8.5/10 |
| Methodological quality of the AI-codegen experiments | 8/10 |
| Honesty/discipline of evidence claims | 9/10 |
| External validity of current results | 5/10 |
| Ability to answer "what detail must a sequence diagram contain?" | 8/10 |
| Ability to answer "what complete specification stack do I need?" | 5/10 — rapidly improving |
| Ability to support the banking specification landscape today | 4–5/10 |
| Ability today to ensure "no unsupported behaviour reaches production" | 3/10 |
| Potential as nucleus of the broader verification framework | very high |

### Run 2 — the evaluator's own before/after re-scoring

| Dimension | Before W2–W4 | After W2–W4 |
|---|---|---|
| Research methodology | 8 | 9 |
| Empirical contribution to AI-codegen specification design | 7 | 8.5 |
| Evidence for minimum-sufficient-context concept | 6 | **9** |
| Evidence concerning carrier/DSL choice | 5 | 7.5 |
| Conflict/governance insight | 5 | **8.5** |
| External validity | 5 | 5.5 |
| Direct banking applicability | 4–5 | 6 |
| Overall relevance to the intended research programme | high | very high |

### Claude feedback on the scores (11 Aug 2026)

Numerical fidelity is not in question — the claim-by-claim check found
zero misquotes across ≈40 figures (verification table in
docs/external-review-evaluation.md; W2 and W5 § Results re-checked for
this pass). The scores are judgments; four notes on the judgments:

- **Minimum-sufficient-context 9** is fair *within-lab* only with the
  generator scoping attached: the far side is weak-generator-borne at
  measured doses — a strong-generator-only shop would measure a
  smaller envelope effect. The too-little side is the vendor-general
  half.
- **Conflict/governance 8.5** scores the *need* leg, which is measured
  (surfacing never emerges, even under in-band deference cues); the
  *harm* leg is not — at W2's dose, resolution was mostly right and
  damage stayed local. Right score for governance risk; an over-read
  for outcome risk.
- **Direct banking applicability 6** conflates relevance with
  deployability. Relevance to the adopter programme: 6 is defensible.
  Deployability toward "no unsupported behaviour reaches production":
  Run 1's 3/10 is still the honest number — the waves argue for gates,
  not for trust.
- **External validity 5.5** was right when written; W5 has since
  retired the single-shot limitation specifically (claims now scoped
  "single-shot and k ≤ 2 agentic"). The toy-substrate,
  single-vendor-levers and n = 3 limitations all still stand.

---

## 3. What changed most, in one line each

- **Biggest upgrade:** minimum-sufficient-context evidence (6 → 9) — W4 turned "more context is better looks false" into a quantified dilution effect.
- **Biggest surprise:** W3 refuted carrier equivalence — syntax *is* an outcome variable (PlantUML best, YAML catastrophic in this harness).
- **Biggest alarm:** W2's 0/18 silent conflict reconciliation — prompt-level "stop on conflict" demonstrably does not work; conflicts must be caught by a gate before generation.
- **Most stable:** external validity (5 → 5.5) — everything is still toy-scale, single-shot, mostly two generators; W5 is the keystone.
- **Priority flip:** W5 moved from "after W2–W4" to "immediate priority", with A3 decomposition, W3b and the mortgage benchmark promoted to parallel workstreams.

*Source: the externally authored review conversation ("Spec Driven AI
Codegen Research"); retained by the owner, not linked here.*

---

## 4. What has landed since Run 2 (repository state, 11 Aug 2026) — *Claude addition*

Run 2's forward programme is partly historical: **W5 ran the same day
the review was evaluated** (frozen pre-registration, adversarial pass
with 2 major / 6 minor findings adopted, $7.95 of the $40 ceiling,
zero protocol deviations; record:
stack_experiment/W5_PREREGISTRATION.md § Results). The keystone held,
in the direction favorable to the review's architecture:

- **The cliff survives agency** — §8.4 ("the cliff collapses under
  agency") did **not** fire: agentic hidden-subset gaps +31.3 pp
  (sequence) and +46.7 pp (C4).
- **The contract lever survives agency**: A3 − A2 hidden +54.2 pp
  (opus 1.000 vs 0.375; haiku 0.750 vs 0.292).
- **Compensation is strictly visible-bounded**: R0 improved +22.2 pp
  to ceiling on the visible tests while hidden moved exactly 0.0 —
  where iteration can fix anything, it fixes only what the visible
  tests cover; artifacts remain load-bearing for everything the tests
  do not state.
- **Below-cliff artifacts are not repaired by iteration at k ≤ 2**:
  +0.0 pp vs single-shot, with the visible set itself still failing
  after two revision rounds — the gate-first posture strengthens.
- **Invention on uncovered behavior persists under iteration**
  (judged, per-generator, inflation bias named).
- Standing claim language program-wide now reads **"single-shot and
  k ≤ 2 agentic"** where it read "single-shot".

Also since Run 2: the charter-promised consolidated record shipped
(**docs/minimum-sufficient-stack.md**, its own 9-finding adversarial
pass); the Level-5 rename is **decided** ("Method-complete", at the
next release); and the EVIDENCE.md boundary paragraph, **W3b** and
**A3 decomposition** are recorded candidates — nothing queued, per the
repo's demand-driven roadmap discipline. Decision record: ROADMAP.md
§ Settled questions; evidence note: docs/external-review-evaluation.md.

---

## 5. Claude — overall verdict on this comparison — *Claude addition*

**Nothing in either run is nonsense, and the comparison renders both
runs faithfully.** This remains the most accurate external assessment
the repository has received: every checked figure traces to its
source, both repo-facing defect findings were real and previously
unrecorded, and Run 2's revisions are driven by pre-registered
outcomes rather than narrative drift. Where the review errs, it errs
by attribution and scoping, not fact:

- **Systematic blind spot (both runs):** the author/ask loop — the
  largest measured below-cliff lever (≈27 pp) and the measured
  recovery for underspecification — appears in Run 1's opening and
  then vanishes from every synthesis, score and architecture box. A
  regulated adopter should treat "route absent decisions to an
  accountable human" as a first-class pipeline stage, not an
  implementation detail.
- **Scope-drops in compression:** bare "6/6" (W2's in-band-deference
  bound), "non-drifted duplication damages" (O1 sat under the
  materiality bar), "direct support for a context compiler" (dose
  measured, selection untested), "proven no universal stack"
  (existence proof at n = 2 generators).
- **Derivation direction:** the target architecture predates the
  evidence said to produce it; the waves upgraded two boxes to
  measured rationale and confirmed the rest.
- **Programme boundary:** the benchmark, cross-spec platform, context
  compiler and carrier graph belong to the adopter programme; the
  repo's analogues (`trace`, the census/pilot kit, agents.md's
  ladder) stay demand-gated as recorded.
- **Cheapest moves missing from every next-step list:** the
  foreign-corpus pilot (the repo-side external-validity leg stage 1
  itself called critical), and cross-vendor replication of the wave
  levers (the cliff is two-vendor-robust; the levers are not yet).

Disclosure, for weight: the wave generators are Claude models and so
is this reviewer; the external reviewer is not. Two differently-
sourced models converging on the same reading of the same frozen
records is mild additional evidence that the records communicate —
and the cross-vendor replication recommended above is the corrective
that depends on neither of us.
