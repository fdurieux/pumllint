# Wave pre-registration — W1: artifact-portfolio ablation

*DRAFT for owner review, 2026-08-10 — NOT yet frozen. Freeze happens
only after: (1) owner edits/approval, (2) the driver exists
(tools/stack_ablation.py, see Design), (3) the generation-calibration
below has run and its numbers are filled in, (4) this file, the driver
and the suite hashes are committed together — that commit is the
freeze. Once a scored (non-calibration) run exists, editing anything
above the Results section invalidates the wave — re-freeze consciously
and say so. Template: PREREGISTRATION_TEMPLATE.md (house protocol =
EVIDENCE.md discipline + research-charter.md §7 standards).*

## Question and decision link (mandatory)

**Question:** For the model→code hop, which artifacts of a
specification stack carry executed-correctness value — at what
marginal rate per artifact and per thousand artifact tokens, in both
the additive and the leave-one-out direction — on a system whose
decision values a generator's priors cannot guess?

**Decision links (what the outcome feeds):**

- research-charter §6: the tests-as-input row ([external] → measured
  here or recorded negative), and a second system for the
  behavioral-content and contract rows (currently LoanCheck-family
  only).
- research-charter §4/§8.1: the below-cliff-vs-absent arm supplies the
  missing harm-vs-absence contrast behind the constitutive-gates risk
  policy (E5).
- research-charter §8.3: instability of marginal contributions across
  generators is a named falsifier (E8).
- The spec-stack recommendation (docs/spec-stack-evaluation.md) and
  the SDD + generation-manifest recommendation
  (docs/sdd-manifest-evaluation.md): their artifact-portfolio advice
  becomes measured instead of corroborated-but-unquantified.
- Rule-pack selection: whether contract-presence conventions earn
  outcome grounding (feeds wording only; builds stay demand-gated).
- W4 and W5 design inputs (dose–response ladder placement; the
  visible/hidden split if E3 exposes leakage).

## Design (mandatory)

- **Conditions/arms (9 unique; information varies, carrier set fixed —
  charter §2 E3):**

  Additive ladder (nested; each rung adds one information class):

  | Arm | Bundle |
  |---|---|
  | A0 brief | brief.md |
  | A1 +structure | A0 + structure/containers.puml |
  | A2 +behavior | A1 + behavior/quote_flow.puml (L5, 100/100) |
  | A3 +contract | A2 + contract/spec.md + decision_table.md + openapi.yaml + quote_states.puml |
  | A4 +tests (full) | A3 + tests_input/acceptance.feature |

  Leave-one-out from A4 (whole information class removed):

  | Arm | Bundle |
  |---|---|
  | L-structure | A4 − containers.puml |
  | L-behavior | A4 − quote_flow.puml (the "absent" arm of E5) |
  | L-contract | A4 − all four contract files |
  | L-tests | ≡ A3 (nested ladder end; deduplicated, reported in both views) |

  Below-cliff arm (charter §4 obligation):

  | Arm | Bundle |
  |---|---|
  | BC-behavior | A4 with quote_flow.puml → quote_flow_bad.puml (L1, 29/100) |

  The brief is present in every arm: it is the task statement, not a
  treatment. Artifact order inside the prompt is fixed to the additive
  order for every arm (no per-arm reordering — order would otherwise
  confound the ablation).

- **Units and n:** one system (CargoQuote) × 9 conditions ×
  2 generators × 3 runs = **54 scored runs**. Pooled per condition
  (n = 6) carries the claims; per-generator pools (n = 3) are
  reported. Granularity note, stated up front: one scenario flipped
  in one run moves a per-generator pool by 3.0 pp and the full pool
  by 1.5 pp; one scenario flipped consistently across a pool moves it
  by 9.1 pp.

- **Models, exact IDs (live-probed before freeze — never from
  memory):** generators `claude-opus-4-8` (adaptive thinking, the
  stored-wave mainline) and `claude-haiku-4-5` (no adaptive thinking —
  house shim omits it; the weak generator, amplification precedent).
  Judge `claude-sonnet-5`, independent of both generators,
  JSON-schema-constrained, max_tokens 16000 (C4 uniformity lesson).
  **Declared narrowing:** both generators are one vendor. The
  weak-generator amplification contrast is within-vendor by design,
  and the cliff's vendor-robustness is already measured (EVIDENCE.md
  cross-vendor wave); a Gemini leg would be an amendment with its own
  key (`GEMINI_API_KEY`/`GOOGLE_API_KEY`, charter §10), not a silent
  extension.

- **Prompts:** variant **stack-bundle-v1** — the c4 conforming-prompt
  scaffold (tools/c4_codegen_experiment.py GEN_PROMPT rules:
  class-per-element, alias-derived names, declared-relationships-only
  calls, failure paths as exceptions/error returns, best-guess on
  ambiguity, code-only output) generalized to a bundle of named
  artifact sections; the entry contract REQUEST_CONTRACT
  (`def handle(request: dict) -> dict`) stays **byte-identical** to
  tools/codegen_experiment.py for cross-program comparability. The
  prompt is identical across arms; only the bundle contents differ.
  Rules referring to artifact kinds an arm lacks are inert by
  construction, never edited per arm.

- **Driver (freeze prerequisite, disclosed harness work):**
  `tools/stack_ablation.py`, new — assembles arm bundles from
  stack_experiment/cargo_quote/, calls the generators via the house
  shim (join over content blocks, retry-once on empty/API error,
  thinking-token accounting), applies suite OVERLAYS driver-side
  after a runner pass (the c4 precedent, generalized per the W0
  README), records per-run: generated code, raw response, API-reported
  input/output tokens, cost, seedless run index. Stored under
  `stack_experiment/results/W1/` and committed (full-record style).
  Before freeze, its stopping rules are cross-checked against every
  expectation arm below (the X-R1 unreachable-arm lesson).

- **Token accounting (for the per-thousand-tokens output):** artifact
  tokens per arm = API-reported input tokens of that arm minus A0's,
  per generator; raw char counts recorded alongside (kit at draft
  time: brief 963 c, structure 1 492 c, behavior 3 366 c / bad 771 c,
  contract 9 357 c across four files, tests 2 874 c; full A4 bundle
  ≈ 18.1 kc ≈ 4.5 k tokens).

- **Oracle-separation declaration (mandatory — tests-as-input arm):**
  stack_experiment/cargo_quote/tests_input/oracle_overlap.md, authored
  in W0 before this draft: per-scenario classes — same
  (G2→invalid_weight_low, G4→screening_down_hold), adjacent
  (G1, G3, G5, G6 mappings), disjoint (G7). E3's analysis splits by
  this declaration: same-class gains measure leakage risk; adjacent +
  disjoint gains measure artifact value.

## Oracles (mandatory)

- **Primary — execution:** tools/acceptance/cargo_quote_suite.py,
  11 scenarios, sensitivity-classed [flow]/[contract]/[prior-inverting]
  (suite header). Draft-time sha256
  `113ab6ac27a1347bcac3dd21c5918cf488a65ace24d2588c9bb38a96a8d9b501`;
  **re-pinned at the freeze commit after generation-calibration** (the
  suite is authored + smoke-calibrated, deliberately not yet frozen —
  W0 README). Runner unchanged: tools/acceptance/runner_child.py,
  sha256
  `f6cc907edda9ba44c15b6ffe4490617597f1a2c2aa8b871bb0acca5972fe7c88`.
  Overlays: as declared in the suite's OVERLAYS map (require_re /
  forbid_re on serialized outcome, price regexes rounded-loose).
  Full and semantic-only pass-rates both reported.
- **Secondary — judged:** invented-business-logic count per run,
  C4-wave rubric and JSON schema, judge as in Design. Judgments are
  quoted as judgments, never merged with executed numbers.
- **Analysis standards:** quote gaps, orderings and correlations,
  never absolute rates (suite-relative); pooled-per-condition is the
  headline unit; NO hard-demand partials on executed gradients
  (mediator, not confound — charter §7); judged gradients may carry
  the partial with both rationales cited.

## Calibration (mandatory, disclosed)

- **Already run (W0, deterministic, $0):** smoke_test.py — reference
  implementation 11/11; three prior-following mutants each caught
  exactly (`prior_error_on_screening_outage` →
  {screening_down_hold}; `canonical_accept_threshold_70` →
  {review_boundary_42, refuse_boundary_67};
  `inverted_surcharge_order` → {price_exact_both}). No degraded or
  partial condition has been executed to date.
- **To run before freeze (needs `ANTHROPIC_API_KEY` /
  `ANTHROPIC_AUTH_TOKEN`):** generation-calibration on pristine A4
  only — 3 runs × both generators (6 runs, excluded from scored
  analysis, cost counted inside the ceiling). Purpose: the pipeline
  works end-to-end on generated (not hand-written) code. Bar: every
  scenario passed by ≥ 1 calibration run, and per-run median ≥ 9/11.
  Any adapter/suite fix it forces is made and disclosed here, then
  the suite hash is pinned and the freeze commit lands. Falling short
  of the bar blocks the freeze — fix, disclose, re-calibrate.
- **Placeholders filled at freeze:** calibration counts + cost, final
  suite hash, driver hash, freeze date + commit.

## Pre-registered expectations (mandatory)

Materiality bar for "material increment": **≥ 9 pp pooled executed**
(one consistently-flipped scenario). Each expectation is checkable
from the stored report files alone.

- **E1 (behavior is the lever):** A1→A2 pooled increment ≥ +9 pp and
  is the largest additive increment. (Precedent: C4 R2→R3 +29.2 pp;
  sequence cliff 16–25 pp.)
- **E2 (adversarial contract — the wave's headline):** A2→A3 pooled
  increment ≥ +9 pp, with [contract]-classed scenarios contributing
  the majority of gained scenario-passes. (LoanCheck measured 0.0 pp
  here under canonical thresholds; CargoQuote's values are
  non-canonical by construction — this either resolves the EC3
  confound or hands the contract rung a real null.)
- **E3 (tests-as-input):** A3→A4 pooled increment positive, reported
  split by overlap class; the artifact-value claim rests on
  adjacent + disjoint scenarios only. Gains concentrated in
  same-class scenarios are reported as leakage-exposed, not as
  artifact value.
- **E4 (directional concordance):** the largest leave-one-out drop is
  L-behavior, and the LOO ranking's top and bottom match the additive
  ranking's.
- **E5 (below-cliff vs absent — charter §4 obligation):** BC-behavior
  pooled ≤ L-behavior pooled − 9 pp (the degraded artifact is worse
  than no artifact), with [flow] and [prior-inverting] scenarios
  driving the gap.
- **E6 (the prior-inverting instrument works):** scenario 10
  (screening_down_hold) pooled pass-rate over A3+A4 exceeds A0+A1 by
  ≥ +33 pp; refuse_boundary_67 direction concordant.
- **E7 (judged invention, secondary):** median judged
  inventions/run decreases A2→A3 in both generators. (Precedent:
  R3→R4 6.00 → 4.00.) Quoted strictly as a judgment.
- **E8 (cross-generator):** both generators agree on the identity of
  the largest additive increment, and the weak generator's gaps are ≥
  the strong generator's (amplification).

**Validity guards (pre-committed, not expectations):**

- **G1 ceiling guard:** if A0 pooled ≥ 0.85, the adversarial-threshold
  design failed (priors suffice) — the wave still reports, but the
  "adversarial" framing is dropped and the kit is revised before any
  W2–W4 reuse.
- **G2 floor guard:** if A4 pooled ≤ 0.30 on both generators, suspect
  harness/adapter defect before interpretation: halt, investigate,
  disclose; any fix forces a conscious re-freeze per the template
  rule.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Failed → |
|---|---|---|
| E1 | Behavioral-content lever generalizes to a second system; charter §6 row gains it | Lever is system-relative; §6 wording narrowed; W4 ladder design revisited before it runs |
| E2 | Contract value upgraded from invention-only to executed under adversarial thresholds; EC3 confound recorded resolved; spec-stack + SDD-manifest rows updated to measured; contract-presence rule wording gains outcome grounding (builds stay demand-gated) | Published as a headline null: written contracts cut invention but not executed failures even when priors cannot guess — companion-spec claim language stays invention-scoped everywhere it is quoted |
| E3 | §6 tests-as-input row → measured (this lab, this scale); W5 visible/hidden split informed | If gains sit in same-class scenarios: leakage-exposed, row stays [external] with in-house caveat, and W5's split becomes a mandatory design element. If negative: recorded; recommendations quoting tests-as-input cite the negative |
| E4 | Portfolio claims quotable in either direction | Order/interaction effects exist; claims restricted to the additive direction; interaction follow-up recorded, not queued |
| E5 | The constitutive-gates risk policy gains its missing harm-vs-absence leg (bounded: one system, one artifact class); §8.1 stays external-evidence-gated | Below-cliff ≈/≥ absent: §4 is reworded to say the lab contrast failed to support the policy's sharpest reading; partial §8.1 signal, published with the same prominence as a confirmation |
| E6 | Prior-inverting instrument validated for W2–W4 reuse | If no arm pins scenario 10, the instrument note goes on the kit and W2–W4 designs adjust before running |
| E7 | Invention–contract link replicates (judged, second system) | Recorded; invention claims stay LoanCheck-scoped |
| E8 | Orderings portable across capability tiers; claim language keeps "ordering, not magnitude" | §8.3 partially fires: stack claims become per-generator; the consolidated document must say so instead of recommending |

## Budget (mandatory)

- **Ceiling $30 (hard, harness cost guard).** Estimate $12–18 by
  precedent scaling (C4 ladder: $4.31 for 15 opus-class
  generation+judge cycles; here 54 generations of which 27 haiku-class,
  54 judge calls at 16k, 6 calibration runs). MAX_CALLS 150. Costs
  recorded per phase in Results.

## Carried limitations (mandatory)

- Toy-scale, one system (CargoQuote) — no cross-system replication
  inside this wave; n = 3 per condition per generator (pooled 6);
  single-shot generation (the agentic condition is W5); LLM judge;
  both generators one vendor (declared above); carrier set fixed —
  carrier effects are W3's question, and this wave's rungs vary
  information at fixed carriers only; capability-relative — results
  dated, pivotal contrasts re-measured per model generation
  (charter §2 C1).

## Results ([date], $[cost])

*Written strictly after the freeze. Run notes recorded before the
verdicts (harness incidents, retries, protocol deviations — however
embarrassing). Then per-expectation verdicts: confirmed / failed, with
the pre-committed interpretation applied, never reinterpreted.*
