# C4 detail ladder — what spec detail does C4-based AI-codegen need?

*Dated experiment record, 2026-07-27. Protocol and expectations frozen
before any scored run (calibration disclosed below). Harness:
`tools/c4_codegen_experiment.py`; inputs: `c4_experiment/R0..R4`; suite:
`tools/acceptance/c4_loan_suite.py` (executed by the frozen, unchanged
`tools/acceptance/runner_child.py`). This is groundwork evidence for the
C4-PlantUML pack decision recorded in ROADMAP § Settled questions — it
sharpens WHAT a pack should check if the census trigger fires; it does
not re-open WHETHER to build one (wait-for-census stands).*

## Why this ran, and the request assessed honestly

The prompt behind this experiment: *create a syntactically and
semantically correct C4 model for an invented use case (credit check for
a personal loan), generate code from it with AI, check the code against
the spec, and research what extra information in C4 diagrams reduces
codegen hallucination — objective: assess the level of detail needed in
specs for near-hallucination-free AI-codegen, as input for a next set of
pumllint rules.*

Assessment, recorded before the run:

- **The question is real and already on file.**
  [docs/c4-pack-evaluation.md](c4-pack-evaluation.md) (2026-07-27) names
  exactly this as the missing evidence extension: *"does C4 completeness
  move codegen outcomes the way sequence maturity measurably does?"* An
  answer selects among the ~20 sketched pack rules (the Tier-3 codegen
  profile especially) with the same evidence-backing the sequence pack's
  SEQ101–109 got from EVIDENCE.md.
- **"Near-hallucination-free" is not a reachable target, by design.**
  C4 is deliberately structural; even the *behavioral* pristine-L5
  sequence diagrams of the standing program average ~3 judge-flagged
  inventions per run (EVIDENCE.md: a diagram underdetermines an
  implementation). The honest reframing, which this protocol adopts:
  measure the **marginal effect of each added spec ingredient** and the
  **residual invention floor** at the richest rung — not chase zero.
- **The request as literally posed (one correct model → generate →
  check) has no contrast** and therefore cannot answer "what level of
  detail is needed". The design below replaces the single model with an
  additive five-rung detail ladder over one invented system, so every
  claim is a gap between rungs — the standing program's
  pristine-vs-degraded logic, run upward.
- **Oracle discipline transfers unchanged.** Judged conformance is
  reliability-without-validity (EVIDENCE.md X3/XV1: judge↔execution
  r ≈ 0.25 same-vendor, 0.002 cross-vendor). Primary oracles here are
  mechanical (AST-derived structural conformance) and executed
  (acceptance suite); LLM-judged fidelity/inventions are recorded and
  quoted strictly as judgments.
- **Scope honesty:** a settled question says diagram↔code conformance
  is watch-don't-build as a *product surface*. This experiment uses a
  conformance measurement as lab oracle — in-repo lab machinery, not a
  product feature. And whatever this measures, C4-pack building stays
  gated on the census trigger; a positive result here adds *rule
  selection* evidence, not a build trigger.

## What the sources say (research synthesis, 2026-07-27)

What should accompany or enrich C4 diagrams to reduce codegen
hallucination:

- **The C4 author's own checklist** — title/type/scope/legend; element
  name, description, technology; relationship label, direction,
  technology/protocol
  ([c4model.com/diagrams/checklist](https://c4model.com/diagrams/checklist)) —
  is annotation-completeness guidance: exactly the surface a linter can
  check (pack Tiers 1–3), and rung R1 of the ladder.
- **C4 shows structure, not consequences.** Practitioner guidance on
  C4-as-LLM-context recommends *complementary* artifacts — domain
  glossaries, interface contracts — and slicing context by C4 level;
  the diagrams set boundaries ("what to touch"), not semantics
  ([The C4 Model: context management protocol of the AI era](https://medium.com/@windead/the-c4-model-the-most-underrated-context-management-protocol-of-the-ai-era-046580bd9aa5)).
- **The hallucination taxonomy for practical codegen** (three classes:
  Task Requirement Conflicts 43.5%, Factual Knowledge Conflicts 31.9%,
  Project Context Conflicts 24.6%) attributes the dominant class to
  under-specified/complex requirements — the generator guesses intent —
  and measures only modest gains from retrieval-grounding alone
  ([LLM Hallucinations in Practical Code Generation](https://arxiv.org/html/2409.20550v1)).
  Mapping: the ladder's behavioral rungs target Task Requirement
  Conflicts; the structural conformance metric targets the
  dependency/context class.
- **Spec-driven development guidance** (GitHub spec-kit and industry
  write-ups) converges on specs containing outcomes, scope boundaries,
  constraints, prior decisions, task breakdown and **verification
  criteria** — i.e. the ladder's top rung, beyond what any diagram
  carries
  ([GitHub blog](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/),
  [Augment Code guide](https://www.augmentcode.com/guides/spec-driven-development-ai-agents-explained),
  [Microsoft](https://developer.microsoft.com/blog/spec-driven-development-ai-native-engineering/)).
- Adjacent but not adopted here: multi-agent generate-then-verify
  pipelines and RAG grounding (general hallucination mitigations, e.g.
  [RAG for structured outputs](https://arxiv.org/html/2404.08189v1));
  C4-generation-from-code is the reverse direction
  ([Collaborative LLM agents for C4](https://arxiv.org/pdf/2510.22787),
  [Code2UML](https://arxiv.org/pdf/2605.24453)).
- **A C4-specific gap surfaced while authoring R3:** C4 dynamic
  diagrams have no native alt/else construct — branch conditions live
  as free text inside relationship labels ("[score sufficient]"), one
  diagram per path. C4's behavioral form is structurally weaker than a
  UML sequence diagram; nothing in the macro surface *requires* guards,
  thresholds or failure paths anywhere. Whatever the wave measures,
  this is already a finding about where a linter could and could not
  demand behavioral content in C4.

The ladder operationalizes this synthesis: R0 bare structure → R1
checklist-complete annotations (the lintable rung) → R2 component
decomposition → R3 dynamic diagrams, qualitative guards (C4's own
behavioral ceiling) → R4 companion spec with thresholds, error policy,
API contract and acceptance criteria (the SDD rung).

## Design (frozen)

- **System (invented):** LoanCheck — credit check for a personal loan.
  Person `applicant`; containers `origination_api`, `decision_engine`,
  `application_store` (db); externals `credit_bureau`,
  `notification_service`. Call-direction container graph: api→store,
  api→engine, engine→bureau, api→notifier. Deliberately distinct from
  the existing `credit_intake` sequence family (which stays untouched);
  same domain register as the standing families, new alias vocabulary.
- **Rungs (additive; each rung contains every file of the one below):**
  - R0 `containers.puml`: bare containers — vacuous title, no
    descriptions, no technology, "Uses" labels, no legend. Passes the
    PlantUML grammar; fails the c4model.com checklist.
  - R1: the same diagram checklist-complete (scope-bearing title,
    descriptions, technologies, directed verb-phrase labels with
    protocols, legend). **The rung a C4 lint pack could enforce.**
  - R2: + component diagrams for api (ApplicationService,
    ApplicationValidator) and engine (ScoringPolicy, BureauGateway).
  - R3: + six dynamic diagrams (approved / declined / review / invalid /
    bureau-unavailable / storage-failure) with **qualitative** guards
    only ("[score sufficient]").
  - R4: + `spec.md` — glossary, validation rules (amount 1–100000, term
    6–120), decision table (approve ≥700, review 620–699, decline
    <620, inclusive), flow order, error policy, exact response
    statuses, API contract, 8 acceptance criteria.
  All `.puml` files pass `plantuml-1.2026.6.jar -checkonly` (the
  CI-pinned version; C4 stdlib includes) and were reviewed against the
  c4model.com checklist at their intended rung.
- **Generation:** `claude-opus-4-8`, 3 runs/rung, adaptive thinking,
  retry-once on truncation/non-compiling (house rule), scaffold-pinned
  prompt: class per element, alias-derived CamelCase names, declared
  relationships as calls, "do not add calls between elements that have
  no declared relationship", `handle(request)` contract verbatim from
  Phase B, and the standing ambiguity clause ("make your best guess").
  Conformance numbers are therefore measured **under an explicitly
  conforming prompt** — the favorable condition; leakage despite the
  instruction is the signal. The ambiguity clause keeps invention
  measurable, as in every prior wave.
- **Oracles:**
  1. **Mechanical structural conformance** (no LLM): AST class set +
     cross-element reference edges (textual mention OR constructor
     name-flow), rolled up to the container-group graph.
     `group_edge_recall` (of 4 declared edges), `extra_group_edges`
     (architecture violations), `extra_classes` (actor names and
     exception types excluded), `groups_missing`; component refinement
     edges (R2+) reported separately.
  2. **Execution** against the frozen 8-scenario suite (above), run
     sandboxed by the unchanged runner; full and semantic-only
     pass-rates, house stage taxonomy. One pre-registered overlay:
     `borderline_review` additionally requires a review-token (and no
     approve/decline token) in the serialized outcome, because the
     runner has no third outcome class.
  3. **Judged** (`claude-sonnet-5`, JSON-schema): house invention
     taxonomy vs the generating rung's own spec text, plus
     technology-honored counts. Judgments only; never merged with
     executed numbers.
- **Suite-derivation trick, restated:** the intended system is fixed
  (R4); lower rungs describe the same system with less information, so
  one suite scores every rung. Scenarios 2 (boundary 700), 4 (review
  band) and 6 (amount cap) are threshold-sensitive by design — below
  R4 the generator must guess them.
- **pumllint view recorded per rung** (v0.23.0 codegen profile) — the
  fit evaluation predicts Level 1 / zero-modelled-elements across all
  rungs; recording it makes the pack gap a measured number inside this
  experiment.
- **Budget:** ceiling $15; estimate ~$3 (15 gen + 15 judge calls;
  execution and conformance $0). Calibration spend below is additional
  and disclosed.

## Calibration (pre-freeze, disclosed)

Two R4-only generations ($0.22) calibrated adapter, suite and scanner
before this freeze — house protocol: pristine artifacts only, no
degraded/lower rung executed or scanned before freezing.

- Execution: 16/16 scenarios passed as generated — suite and stubs work
  end-to-end; no suite edits were needed.
- Scanner: two false readings found and fixed: (1) constructor-injected
  collaborators referenced only via parameter-named attributes
  (`self.store = store`) evaded the textual scan — fixed by the
  name-flow resolver; (2) a generated `Applicant` actor class counted
  as extra — fixed by the actor-name exclusion, and `groups_missing`
  added (a container realized entirely by its declared components is
  not a missing group). Post-fix: recall 1.0, zero extras, both
  refinement edges detected, on both stored calibration artifacts.

## Pre-registered expectations (written before the wave)

- **EC1 (structure is cheap):** pooled `group_edge_recall` ≥ 0.85 at
  **every** rung, R0 included, with extra_group_edges ≈ 0 — under a
  conforming prompt, bare structure already secures structural
  conformance; the ladder's value, if any, lies in behavior, not in
  edge realization.
- **EC2 (invention falls with detail):** judged
  invented-business-logic per run decreases from R0 to R4, with the
  largest single-rung drop at **R2→R3** (behavior arrives), not at
  R0→R1 (annotations arrive).
- **EC3 (executed behavior climbs in steps):** pooled executed
  pass-rate is non-decreasing along the ladder (inversions ≤ 2 pp
  tolerated), **R3−R2 ≥ 10 pp**, **R4−R3 ≥ 10 pp** (three scenarios
  are threshold-sensitive and only R4 pins thresholds), and
  **R1−R0 < min(R3−R2, R4−R3)** — checklist annotations are the
  smallest behavioral contributor.
- **EC4 (no rung is hallucination-free):** even at R4, pooled judged
  inventions > 0 and pooled executed pass-rate < 1.0. (The calibration
  pair's 16/16 does not pre-confirm the executed half: n = 2, and the
  scored wave is fresh runs.)
- **EC5 (today's tool is blind to the whole ladder):** v0.23.0 codegen
  profile scores every rung file Level 1 via the zero-modelled-elements
  cap with findings invariant along the ladder — current pumllint
  cannot distinguish R0 from R4 at all.

**Interpretation matrix (pre-committed):**

- EC3 holds as stated → the detail that moves C4-based codegen is
  behavioral and contractual, not annotational. Pack consequence: Tier
  1/3 annotation rules are hygiene with limited codegen-outcome claims;
  the evidence-backed codegen-profile rule for C4 is **presence-of-
  behavioral-content** (dynamic diagrams or companion spec for flows,
  thresholds and failure paths) — plus the structural floor. Claim
  language mirrors the gate: input filter, never a content certifier.
- R1−R0 ≥ 10 pp instead → annotation completeness is itself
  outcome-bearing; Tier-3 rules (technology mandatory, informative
  labels) gain direct evidence and the pack's codegen profile is the
  headline.
- EC1 fails at R0 (structure not realized from bare diagrams) →
  structural linting is outcome-bearing at the floor; report which
  edges break.
- EC4 fails upward (R4 ≈ 1.0 executed with ~0 inventions) → a full
  companion contract can saturate an 8-scenario suite; the honest
  claim becomes "hallucination-free *for suite-covered behavior* at
  SDD-grade spec detail", with the invention list deciding what
  remained outside the suite.
- EC2's drop concentrating anywhere other than R2→R3 → report where,
  and credit that rung's ingredient accordingly.

**Standing limitations, pre-declared:** one family, one generator, one
judge, one suite, n = 3 runs/rung — pooled rungs carry the claims,
never single runs; absolute rates are suite- and prompt-relative; quote
gaps, orderings and correlations, never absolutes. The scaffold prompt
pins naming and entry — the standing Phase-B lesson (pinning lifts
moderate rungs, does not restore missing content) is expected to
transfer, not re-tested here. Cross-vendor and human-authored C4 are
out of scope.

## Results (2026-07-27, $4.31 total: calibration $0.22 + wave $2.52 + re-judge $1.29 + uniformity re-judge $0.28)

**Run notes, recorded before the verdicts:** (1) 15/15 generations
compiled first-try; every failure at every rung was semantic —
full = semantic pass-rate throughout. (2) 9/15 first-pass judge calls
died of token exhaustion (the known adaptive-thinking zero-text-block
mode: C4 rung specs are far larger than the sequence diagrams the house
judge budget of 6000 was sized for). Harness repaired
(`JUDGE_MAX_TOKENS = 16000`, retry-once on parse failure) and the nine
re-judged against the stored artifacts — no regeneration; generation,
conformance and execution rows untouched. (3) The `--rejudge` mode and
the budget constant are post-freeze harness repairs, disclosed here;
prompts, schema, models and oracles unchanged. (4) A uniformity pass
(`--rejudge-uniform`, +$0.28) then re-judged the six R0/R1 artifacts
whose first-pass judgements had run at the old 6000 budget, so all 15
judgements in the record share one configuration; the 6000-budget
values are preserved in the report under `judge_6k` (they differed
only in decimals: R0 inventions 6.67 → 7.00, embellishments
5.00 → 5.67, fidelity 59.3 → 58.0; R1 inventions unchanged 7.00,
fidelity 46.3 → 50.7 — judge-sampling jitter at n = 3, executed and
mechanical numbers untouched).

**The ladder, all three oracles** (pooled, n = 3 artifacts × 8
scenarios per rung; judged numbers are judgments, never merged with
executed):

| Rung | Executed pass-rate | Edge recall (mech.) | Extra edges | Invented/run (judged) | Fidelity (judged) |
|---|---|---|---|---|---|
| R0 bare | 0.417 | 1.00 | 0 | 7.00 | 58.0 |
| R1 checklist | 0.500 | 1.00 | 0 | 7.00 | 50.7 |
| R2 components | 0.625 | 1.00 | 1 | 6.67 | 57.3 |
| R3 dynamics | 0.917 | 1.00 | 0 | 6.00 | 62.0 |
| R4 companion spec | 0.917 | 1.00 | 0 | 4.00 | 66.3 |

(Judged fidelity is scored against each rung's own richer spec — a
harder target as the ladder climbs — so it is not comparable across
rungs; recorded, not interpreted.)

**Verdicts:**

- **EC1 — confirmed, decisively.** Group-edge recall is 1.00 at every
  rung including R0; one extra cross-group edge in the whole wave (one
  R2 artifact gave the engine a reverse reference to the api) and one
  extra class (a `Decision` DTO). Under a conforming prompt, bare
  structure already secures structural conformance — the ladder's
  executed value is entirely behavioral.
- **EC2 — failed as located, direction intact.** Invention falls
  R0→R4 (7.00 → 4.00) but is flat across the annotation rung
  (R0→R1: 7.00 → 7.00 under the uniform judge budget), and the
  largest drop is **R3→R4 (−2.0)**, not the pre-registered R2→R3
  (−0.67). Per the matrix: the invention reduction belongs to the
  **companion spec**, not the dynamic diagrams. The two oracles split
  cleanly: dynamics fix executed outcomes; the written contract
  reduces guessing.
- **EC3 — half confirmed, and the failed half is the headline.**
  Monotone ✓; **R3−R2 = +29.2 pp** ✓ (the largest single step —
  behavioral content arriving); R1−R0 = +8.3 pp < R3−R2 ✓. But
  **R4−R3 = 0.0 executed** (bar ≥ 10 pp) — failed. Post-hoc mechanism,
  labeled as such: the suite's thresholds (approve ≥ 700, review band,
  amount cap) are domain-canonical values, and the generator's priors
  guessed them: the 700-boundary passed 3/3 from R0 up; one R2 run
  invented `MAX_AMOUNT = 50000` from the validator description's
  "product limits" — a *different* rule than R4's 100 000, yet
  agreeing with the suite on every tested point. The suite measures
  agreement at tested points, not rule identity — the judge saw what
  the suite could not.
- **EC4 — confirmed.** R4 still averages 4.0 judged inventions per run
  (e.g. a default credit score of 700 *auto-approving* when no score
  key is recognized; fabricated notification-delivery payloads) and
  executes at 0.917, not 1.0 (one run notified despite storage failure
  and mishandled the bureau-failure object). No rung is
  hallucination-free; the floor at full SDD-grade detail ≈ 4
  judged inventions/run and ~8 pp executed shortfall on this suite.
- **EC5 — confirmed in substance.** Every rung file scores **Level 1**
  under v0.23.0's codegen profile via the zero-modelled-elements cap
  (element_count 0 throughout). One nuance: R0's unnamed diagram draws
  GEN002 (composite 98.75 vs 100.0) — the governance rules see the
  file, so R0 vs R1 is *faintly* visible; R1 through R4 are entirely
  indistinguishable to the current tool. The pack gap, measured inside
  this experiment: pumllint currently discriminates none of a ladder
  whose executed outcomes span 50 pp.

**What failed where (the residual at R3/R4):** the two error-policy
scenarios. Two runs (one R3, one R4) notified the applicant despite a
storage failure (forbidden call) and treated the bureau's failure
object as a score (TypeError surfaced as an unclassified error text) —
error-path discipline is the last thing to become reliable, echoing
the with-author arm's residual. The review branch is a pure R3+
effect: 0/3 at every rung below R3 (the concept does not exist in a
static C4 model), 3/3 at R3 and R4.

**Read for the user's question — "what detail level does
near-hallucination-free need?":** *near-hallucination-free is not on
this menu at any rung* (EC4). What the ladder buys, measured:
annotations (R1) ≈ +8 pp executed, no invention reduction — they cue
defensive validation (invalid-zero went 1/3 → 3/3), and their wording
*steers* invention (the "product limits" description conjured a
concrete invented cap). Behavioral diagrams (R3) ≈ +29 pp executed —
presence of flows, branches and failure paths is the single biggest
lever. The companion contract (R4) bought no executed points *on this
suite* — because the tested decisions were canonical — but cut judged
invention by a third; where business rules are idiosyncratic
(non-canonical thresholds, unusual caps), that written contract is the
only rung that pins them, and the R2 cap incident shows what happens
otherwise: a plausible, wrong, *confidently implemented* rule that
tests at the observed points cannot distinguish.

## Implications for a C4 pack (rule-selection evidence, census-gated)

Recorded for the build decision if/when the ROADMAP trigger fires —
this experiment adds rule *selection* evidence, not a build trigger:

1. **Presence-of-behavioral-content is the evidence-backed codegen
   rule.** A model set whose C4 content is purely static (no dynamic
   diagrams, no companion spec reference) sits on the wrong side of a
   29 pp executed step. Shape: codegen-profile finding when a C4 model
   set declares containers/components but no behavioral artifact
   covers the flows.
2. **Vague-decision-language lexicons port to C4.** R3's qualitative
   guards ("[score sufficient]") executed at 0.917 here only because
   the true thresholds were canonical; the existing sequence
   vagueness-lexicon mechanism applied to C4 Rel labels and
   descriptions — flagging decision words with no number or pointer —
   is the honest mitigation, and the "product limits" incident
   motivates the same rule for element *descriptions* that name
   rules without stating them.
3. **Annotation-completeness rules (Tier 1/3) are hygiene with a
   measured but modest executed effect** (+8 pp, invention-neutral).
   Claim language: input hygiene, misread prevention (per the fit
   evaluation), validation cueing — not outcome guarantees.
4. **Structural conformance is not the bottleneck** under a conforming
   prompt (EC1) — structural rules justify as misread-prevention, not
   codegen-outcome rules.
5. **The gate stays an input filter.** The R2 invented-cap incident is
   the C4 rehearsal of the standing claim: passing observable checks
   never certifies content. Nothing here weakens — everything here
   re-confirms — the settled claim language.

**Limitations, standing:** one family, one generator (opus-4-8), one
judge, one suite, n = 3/rung; suite thresholds are domain-canonical
(post-hoc identified confound for R4−R3 — an adversarial-threshold
replication is the obvious follow-up if this ever needs to carry more
weight; **run 2026-08-01, recorded below in §Adversarial-threshold
replication**); scaffold-pinned prompt (conformance measured under the
favorable condition); judged fidelity not comparable across rungs.
Quote gaps and orderings, never absolutes.

## Adversarial-threshold replication — pre-registered expectations (written 2026-08-01, before the wave)

*The follow-up named in the standing limitations, run on request. The
main wave's R4−R3 = 0.0 executed was confounded: the suite's thresholds
(approve ≥ 700, review 620–699, amount cap 100 000) are domain-canonical
values the generator guessed from priors — `approved_boundary` passed
3/3 from R0 up, with no spec in sight. This replication moves every
numeric business rule off its canonical value, so that at the tested
points the canonical-prior rule set and the true (adversarial) rule set
disagree. If the companion spec carries real executed value for
idiosyncratic rules, it must show here; if R4A−R3 ≈ 0 again, the
companion spec's executed value is refuted even where priors cannot
rescue the generator.*

**Design (frozen).** Two arms, n = 3 runs each, same scaffold-pinned
prompt as the main wave, verbatim:

- **R3 arm:** inputs byte-identical to the main ladder's R3 (dynamic
  diagrams, qualitative guards — "[score sufficient]", no numbers
  anywhere; re-verified at freeze).
- **R4A arm:** the same R3 files + a companion `spec.md` that is
  word-for-word the R4 spec with ONLY the parameter values changed
  (single-factor manipulation): decision thresholds, validation bounds,
  and the acceptance-criteria probe values. As in R4, the acceptance
  criteria enumerate the suite scenarios — that is what the SDD rung
  means.

Oracles: the frozen runner (`runner_child.py`, unchanged) with an
adversarial suite (`tools/acceptance/c4_loan_adv_suite.py`) that keeps
the canonical suite's 8-scenario shape, stub machinery, lexicons and
review-overlay mechanism, and moves exactly three probes into the
**disagreement zones** between the canonical and adversarial rule sets;
the other five scenarios are byte-identical agreement anchors. Scenario
slots: `approved_high` (760), `review_mid` (probe), `declined_low`
(540), `declined_band` (probe), `invalid_zero` (0), `over_cap` (probe),
`bureau_error`, `storage_error`. Mechanical conformance and the judge
taxonomy are unchanged; the judge scores each arm against its own rung
spec, as before.

**Sealed-parameters commitment.** The adversarial numbers and probe
values appear in no repository file at freeze time — a generation run
that went looking could find only the qualitative design above, not the
values. They are committed here by SHA-256 and revealed (files added to
the repo, hashes verifiable) after the last generation completes:

| Sealed file (revealed post-generation) | SHA-256 |
|---|---|
| `c4_experiment/R4A/spec.md` | `02ddbc66102164588b65cd77af61e782c32eb8bd1ceb6cca743c5b112082daf5` |
| `tools/acceptance/c4_loan_adv_suite.py` | `a72d7e60a90722a1d304c9d240dfa1de45cf8d0edecb5c352766ea72ef129cb1` |
| `c4_experiment_results/adv_wave/sealed/parameters.json` | `de3d4c10198589ddcc15148b25287695c1a6d7c5c1e4576c70279246aa1e718c` |
| `c4_experiment_results/adv_wave/sealed/ref_canonical.py` | `ad84234651c12221c027472201740eb8c5dda461f6ccaa8388da8274f45f8dcd` |
| `c4_experiment_results/adv_wave/sealed/ref_adversarial.py` | `7442aefa6a8bdc6bad3f31041fd1645f8c259ad42a9d57cf21e9b8d3ec0507b2` |

**Instrument, disclosed.** This session's environment holds no raw
Anthropic API credentials (verified: `api.anthropic.com` reachable
through the egress proxy, authentication rejected with 401 for want of a
key), so the main wave's `messages.create` path cannot run. The wave
therefore runs on a **Claude Code subagent instrument**: one subagent
per generation, prompt = the harness `GEN_PROMPT` byte-identical, plus a
fixed preamble instructing the agent to use no tools and reply with only
the module source; model override `opus` (platform-resolved current
Opus — NOT pinnable to the main wave's `opus-4-8`; the resolved identity
is recorded at reveal). Judging runs the harness `JUDGE_PROMPT` the same
way on subagents with model override `sonnet` (same family as the
pinned judge `claude-sonnet-5`), JSON-only reply validated against the
harness schema, retry-once on parse failure (house rule). Fences are
stripped by the harness's `_strip_fences` (house rule). Token spend is
not meterable for subagents; call counts are reported instead.
**Audit rule:** the task runtime reports each subagent's tool-use
count; any generation or judge run with `tool_uses > 0` is discarded
and regenerated, disclosed. Artifacts are extracted from the task
transcripts by script and retained in `c4_experiment_results/adv_wave/`
(gitignore exception — with no API request logs, the artifacts are the
audit record). The $0 oracles run in the extended harness
(`--adversarial --score-dir`, pre-freeze extension of
`tools/c4_codegen_experiment.py`; canonical-path behavior verified
unchanged). Within-wave contrasts (R4A − R3, same instrument both arms)
carry the claims; comparisons against the 2026-07-27 ladder are
indicative only.

**Instrument anchor (calibration, pre-freeze, disclosed).** Two
generations from the CANONICAL R4 spec through the subagent instrument,
executed against the canonical suite: **16/16 pooled** — identical to
the raw-API calibration pair's 16/16 — with group-edge recall 1.0,
`handle()` present, `tool_uses = 0` on both. One anchor produced two
extra classes (an `Application` record and a `LoanCheckSystem`
assembly — same class of extras as the main wave's `Decision` DTO). No
instrument shift detectable on known ground at n = 2; the anchor
artifacts are retained alongside the wave's.

**Suite calibration (deterministic, pre-freeze, disclosed).** Two
hand-written reference implementations — one of the canonical rules, one
of the adversarial rules (sealed above) — executed against both suites
through the frozen runner (2×2, no LLM anywhere):

| | canonical suite | adversarial suite |
|---|---|---|
| canonical-rules impl | **8/8** | **5/8** — fails exactly the three probes |
| adversarial-rules impl | 7/8 — fails only `approved_boundary` | **8/8** |

The canonical-rules failures carry the exact predicted signatures
(review-probe answered with an approv-token; declined-probe answered
with review; cap-probe proceeded past validation). The suites therefore
discriminate **rule identity** at the probe points — the thing the main
wave's suite could not do. An implementation of canonical priors has a
measured ceiling of 5/8 ≈ 0.625 on the adversarial suite.

**Pre-registered expectations:**

- **EC-A1 (headline — the companion spec carries executed value when
  rules are idiosyncratic):** pooled executed R4A − R3 ≥ 10 pp on the
  adversarial suite; sharper, R3 pooled ≤ 0.70 and R4A pooled ≥ 0.80.
- **EC-A2 (mechanism — canonical priors are what fails):** of the 9
  R3-arm probe executions (3 runs × 3 probes), ≥ 6 fail, and ≥ 4 of the
  failures carry the canonical signature (`review_mid` failing on an
  approv-token outcome; `declined_band` failing on a review/unknown,
  non-declin outcome; `over_cap` failing with the bureau called or a
  success outcome).
- **EC-A3 (the spec overrides the prior when stated):** R4A-arm probe
  executions pass ≥ 7/9.
- **EC-A4 (structure stays free):** group-edge recall 1.00 in both
  arms; extra cross-group edges ≤ 1 in the whole wave.
- **EC-A5 (no rung is hallucination-free — the standing EC4, re-run):**
  R4A pooled judged inventions > 0 and pooled executed < 1.0.

**Interpretation matrix (pre-committed):**

- EC-A1–A3 hold → the main wave's R4−R3 = 0.0 is confirmed as the
  canonical-threshold confound, and the ladder's reading is amended:
  dynamics buy flow/branch/failure-path discipline (+29 pp there), the
  written contract buys **rule identity** — invisible when the tested
  rules are canonical, decisive when they are not. Pack consequence:
  the vague-decision-language rules (decision words with no number or
  pointer, in guards AND element descriptions) carry codegen-outcome
  evidence, not just hygiene claims; presence-of-behavioral-content
  alone is NOT sufficient where business rules are idiosyncratic.
- EC-A1 fails low (R3 arm passes probes) → the generator did not
  default to canonical rules. Calibration proves the suite
  discriminates, so passing means numeric agreement with the sealed
  values: audit the runs for leakage (tool-use counts, transcript
  provenance) before any other reading; absent leakage, report the
  prior-distribution finding honestly.
- EC-A3 fails (R4A arm fails probes despite the spec stating the
  values) → **spec-following failure**: the written contract does not
  reliably override priors — a stronger hallucination finding than
  anything in the main wave; the judge rows decide invention vs
  omission per run.
- EC-A4 fails → structural realization is instrument-sensitive; bound
  the conformance claims to the raw-API instrument.
- EC-A5 fails upward (R4A 24/24 with ~0 inventions) → an adversarial
  companion contract can saturate suite-covered behavior; the claim
  stays bounded exactly as the main wave's matrix already words it.

**Limitations, pre-declared:** one family/system; one generator
instrument per wave (subagent-opus here, raw-API opus-4-8 in the main
wave — cross-wave gaps are indicative, within-wave gaps carry claims);
one judge; n = 3/arm; no token/$ metering for subagents (call counts
and tool-use audits instead); scaffold-pinned prompt (the favorable
condition, as always); the adversarial values are plausible-range, so
an individual prior guess can agree with an individual probe — the
claims rest on the probe SET, per the 2×2 calibration; the R4A
acceptance criteria enumerate the probes (that is the SDD rung's
definition, unchanged from R4). Pooled arms carry the claims, never
single runs.

## Adversarial-threshold replication — results (2026-08-01; executed and mechanical oracles; judged oracle recorded below when run)

**Run notes, recorded before the verdicts:** (1) All six generations
arrived first-try compiling; wall time ~80–90 s each; generator resolved
to `claude-opus-5[1m]` (recorded per the instrument disclosure). (2) The
tool-use audit passed two ways on every run: the task runtime's usage
metadata reported `tool_uses: 0`, and an independent transcript scan
counted zero tool-use blocks — no generation had any channel to the
sealed values beyond its inline specification. (3) The sealed reveal
verified: all five SHA-256 hashes match the freeze commitment exactly.
(4) One oracle-conservatism artifact, disclosed: R3 run 1's response
schema includes a key literally named `notification_error` (value
`None`); the serialized outcome therefore contains the failure token
"error" and the frozen lexicon rule (failure beats success) classifies
its correct `approved_high` outcome as a failure. This costs the R3 arm
one pass it behaviorally earned (0.708 → 0.750 without it); the rule is
frozen, vendor- and arm-neutral, and left untouched. (5) The judged
oracle had been planned on sonnet subagents; vendor API keys were
approved for the follow-on cross-vendor wave after this wave ran, so the
judge pass instead runs on the pinned raw-API judge configuration
byte-identical to the main wave's (`claude-sonnet-5`, schema-enforced,
`JUDGE_MAX_TOKENS = 16000`, retry-once) via `--adversarial --judge-dir`
— an instrument upgrade over the plan, disclosed here before the pass
runs; executed and mechanical rows above it are final and untouched.

**The two arms, executed and mechanical** (pooled, n = 3 × 8):

| Arm | Executed | Edge recall | Extra edges | review_mid (705) | declined_band (630) | over_cap (90 000) |
|---|---|---|---|---|---|---|
| R3 diagrams-only | 0.708 | 1.00 | 3 | 0/3 | 0/3 | 3/3 |
| R4A + adversarial spec | **1.000** | 1.00 | 6 | 3/3 | 3/3 | 3/3 |

**Verdicts against the pre-registered expectations:**

- **EC-A1 — confirmed.** R4A − R3 = **+29.2 pp** (bar ≥ 10); R4A pooled
  1.000 ≥ 0.80. The sharper sub-bar R3 ≤ 0.70 missed by one scenario
  (0.708): `over_cap` passed 3/3 by accidental agreement — see EC-A2.
- **EC-A2 — confirmed.** 6/9 R3 probe executions failed (bar ≥ 6), and
  all six failures carry the canonical signature (bar ≥ 4): every run
  approved 705 (approv-token outcomes), every run sent 630 to review
  (review/unknown outcomes). The third probe is the caveat the
  pre-registration named: **all three R3 runs invented the same
  `MAX_AMOUNT = 50 000`** — the exact "product limits" invention the
  main wave saw once at R2 — and a 50 000 cap happens to reject 90 000
  just as the true 84 500 rule does. The suite scores agreement at the
  tested point; the rule is wrong. Confidently, identically wrong,
  three out of three — the strongest prior-consistency observation in
  the program so far, and it is invisible to the executed oracle.
- **EC-A3 — confirmed.** R4A probe executions 9/9; all three artifacts
  implement 713 / 641 / 500..84 500 / 9..96 as literal constants. When
  the contract states the numbers, the generator uses the numbers.
- **EC-A4 — half confirmed, half failed.** Recall 1.00 in both arms ✓;
  extra cross-group edges **9 total vs the ≤ 1 bar — failed**. Post-hoc
  mechanism, labeled as such: all nine extras are *reversals of
  declared edges* (engine→api ×5-of-9, bureau→engine, notifier→api,
  store→api) — the opus-5 idiom quotes `Rel(...)` lines and peer
  aliases inside class docstrings, which the textual half of the
  mechanical scanner reads as reverse mentions. Zero undeclared
  element pairs appeared. Per the matrix: the extras metric is bound to
  the generator idiom the scanner was calibrated on (opus-4-8); a
  docstring-aware scanner revision is future lab machinery, not applied
  post-freeze.
- **EC-A5 — the executed half failed upward, as the matrix anticipated:
  R4A executed 1.000.** An adversarial companion contract saturated
  every suite-covered behavior, error paths included — the first 1.000
  in the program. The claim stays exactly as bounded: hallucination-free
  *for suite-covered behavior*; the R3 arm's invented-cap incident above
  is the standing proof of why that bound is not removable. The
  invention half of EC-A5 awaits the pinned judge pass; its numbers
  will be appended here as judgments when it runs.

**Read for the original question, updated:** the main wave said the
companion spec "bought no executed points on this suite" — the
replication shows why that was an artifact of canonical thresholds: with
rules the generator cannot guess, the written contract is worth
**+29 pp executed and the difference between 0.708 and saturation**.
Dynamics buy flow discipline; the contract buys rule identity. And
detail does not remove invention — it relocates it: at R3 the model
invents *rules* (the same wrong cap, three times); at R4A, with every
rule pinned, executed invention vanishes from the suite's view while
the judged floor remains to be measured.

## Cross-vendor recipe wave — pre-registered expectations (written 2026-08-01, before the wave)

*User-directed follow-up: does the saturation recipe port across
vendors? Scope chosen from the offered designs: arms R3 vs R4A only
(the contrast that carries the entire executed effect), C4 family only,
three vendors, n = 3 per cell — 18 generations. Everything else is
reused frozen: the LoanCheck system, the sealed adversarial suite
(2×2-calibrated to discriminate rule identity), the unchanged runner,
the mechanical conformance scanner, the pinned judge.*

**Design (frozen).** Generators, raw API, one per vendor —
`anthropic: claude-opus-5` (deliberately the same model family+version
as the replication's subagent instrument, giving a free
same-model/two-instruments bridge), `openai: gpt-5.2` (default),
`google: gemini-3.1-pro-preview` (default) — defaults overridable via
`XV_*_MODEL` env pins; the exact ids and dates that actually answer are
recorded at smoke-test time (house precedent: pro-class SKUs churn).
One generation prompt, verbatim `GEN_PROMPT`, retry-once house rule;
transport shims: existing Anthropic SDK path, existing Gemini REST shim
(thinking billed and counted as output), new OpenAI chat-completions
shim (reasoning tokens counted as output). Thinking configurations
therefore differ by vendor and are NOT equalized — absolute cross-vendor
rates are not comparable and are not claimed; **per-vendor R4A−R3 gaps
carry every claim** (standing house rule: gaps, orderings,
correlations — never absolutes). Oracles identical for all arms;
executed + mechanical carry the claims. Judge: `claude-sonnet-5` held
constant across vendors, with the standing cross-vendor caveat quoted
up front: judged↔executed agreement on cross-vendor code was measured
at **r = 0.002** (EVIDENCE.md XV1) — judged numbers here make no
outcome claims at all; they are the invention taxonomy, quoted strictly
as judgments. Results: `c4_experiment_results/xv_wave/` (artifacts
retained, same audit-record rationale). Budget: **ceiling $20**
(user-approved), estimate ~$6–10; `MAX_CALLS = 60` guard (plan: 18 gen
×2 worst-case + 18 judge = 54).

**Pre-registered expectations:**

- **XVA1 (headline — the recipe is vendor-robust):** for EVERY keyed
  vendor, pooled executed R4A − R3 ≥ 10 pp on the adversarial suite.
- **XVA2 (saturation-or-near):** R4A pooled executed ≥ 0.85 per vendor.
- **XVA3 (canonical priors are cross-vendor):** per vendor, ≥ 4/9
  R3-arm probe executions fail, and ≥ half of the failures carry the
  canonical signature (approv-token at 705; review/unknown at 630;
  bureau-called or success at 90 000). Either outcome is informative:
  shared failures say the canonical values are training-corpus-wide
  priors; divergent inventions say each vendor guesses differently —
  both strengthen the pin-the-numbers rule, differently.
- **XVA4 (structural floor):** group-edge recall ≥ 0.85 per vendor
  under the conforming prompt (the main wave's EC1 bar, not the
  replication's 1.00 — vendor idioms may differ; the extras metric is
  recorded but carries no bar after EC-A4's idiom finding).
- **XVA5 (the floor persists):** R4A pooled judged inventions > 0 for
  every vendor (judgment-only claim).

**Interpretation matrix (pre-committed):**

- XVA1–A3 hold everywhere → the recipe — behavioral diagrams + written
  contract with pinned numbers — is vendor-robust, and the pack
  consequence hardens: presence-of-behavioral-content and the
  vagueness-lexicon rules (decision words must carry a number or a
  pointer) are *vendor-independent*, evidence-backed codegen-profile
  rules. C4-pack building itself stays census-gated; claim language
  stays input-filter.
- XVA1 fails for a vendor because its R3 arm PASSES probes → that
  vendor's priors happen to match the adversarial values or it hedges;
  inspect its invented constants against `parameters.json`; the
  canonical-prior claim becomes vendor-scoped.
- XVA1 fails for a vendor because its R4A arm FAILS probes → a
  **spec-following ceiling** for that vendor: stated rules did not
  override priors. The recipe is not vendor-robust; pumllint's claim
  language must scope input-side sufficiency per generator class.
- XVA2 fails with error-path failures (probes fine) → the residual is
  error-path discipline again (main-wave echo), a different, familiar
  gap — report which paths.
- XVA4 fails for a vendor → the scaffold-pinned prompt does not secure
  structure for that vendor; structural rules regain codegen-outcome
  relevance there.

**Limitations, pre-declared:** one family/system; n = 3/cell; one judge
(validity caveat above); per-vendor thinking/token configs differ by
design; preview/flagship SKU churn (exact ids recorded at smoke);
absolute rates not comparable across vendors; the execution oracle is
the vendor-neutral leg that carries the claims. Order of operations
when keys arrive: replication judge pass first (pinned judge, the
disclosure above), then per-vendor smoke calls (ids recorded here),
then the wave.
