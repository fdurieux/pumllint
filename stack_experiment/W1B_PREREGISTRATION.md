# Wave pre-registration — W1b: the contract-bundle decomposition

*DRAFT, 2026-08-11, pre-verification — findings-before-verdicts. This
wave is NOT frozen and may not run: the charter §10 sequence is
pending in full — independent adversarial pass against this draft →
freeze commit (pinning suite/runner/driver hashes and the reading
rules below) → owner go → scored run. Lineage: this is W1-E4's fired
matrix branch ("interaction follow-up recorded, not queued") given its
concrete shape; recorded as a wave candidate in ROADMAP § Settled
questions and docs/external-review-evaluation.md § wave candidates;
sequencing rationale owner-accepted in
docs/external-review-comparison.md — the result determines what a
domain benchmark must contain, so this wave belongs before any
benchmark freeze. Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base (by import from W1, unchanged):** the W1 models
(`claude-opus-4-8`, `claude-haiku-4-5-20251001`; judge
`claude-sonnet-5` @16000, C4-wave JSON schema and rubric), prompt
variant stack-bundle-v2 with the byte-identical entry contract, the
frozen suite (tools/acceptance/cargo_quote_suite.py, sha256
`113ab6ac…9b501`) and runner (`f6cc907e…2fe7c88`) with their OVERLAYS,
and W1's shared definitions: materiality ≥ 9 pp pooled executed;
net slot-gains rate-based over named scenario sets; the tie rule with
per-pool quantums. Hashes re-verified and re-pinned at the freeze
commit.

## Question and decision link (mandatory)

**Question:** Which of the four artifacts inside W1's A3 contract
bundle — companion spec, decision tables, OpenAPI, state model —
carry the bundle's executed value (A2→A3 +37.9 pp pooled; the
programme's largest leave-one-out drop, 55.2 pp) and its judged
invention cut, in the add-one and leave-one-out directions, per
generator?

**Decision links:**

- **W1-E4's recorded follow-up** (the fired branch restricted
  portfolio claims to the additive direction and recorded an
  interaction follow-up, not queued — this is it, at component
  grain).
- **Charter §6 contract row:** "the written contract is
  executed-real under adversarial thresholds" gains component
  attribution — or a recorded bundle-level-only scoping if
  attribution fails.
- **docs/minimum-sufficient-stack.md §1 and the pilot-facing
  sentence:** "the written decision contract is the load-bearing
  artifact" becomes actionable for an adopter who must choose what
  to mandate — one file or four.
- **The external review's open question, owner-agreed** (comparison
  note row "Contract bundle (A3) decomposition"): state diagram?
  OpenAPI enough? Answered with empirical precision at this lab's
  scale — and the owner-accepted sequencing consequence: this
  result decides the artifact set of any future domain benchmark.
- **Rule-pack wording:** which artifact a contract-presence
  convention would name (wording only; builds stay demand-gated).
- **W3b design input:** if the decision tables dominate, the
  carrier question ("is it the table form or the number content?")
  sharpens — disclosed here as out of scope, W3b territory.

## Design (mandatory)

- **Conditions/arms (10 unique; information varies,
  carrier-per-component fixed — no artifact is re-rendered across
  arms; charter §2 E3):**

  In-wave anchors (W5's cross-occasion lesson: every gap below is
  computed in-wave; W1 stored values are quoted as cross-occasion
  references only — A2 0.439 / A3 0.818 pooled, opus 0.455/1.000,
  haiku 0.424/0.636):

  | Arm | Bundle |
  |---|---|
  | A2 (anchor) | brief + structure/containers.puml + behavior/quote_flow.puml |
  | A3 (anchor) | A2 + spec.md + decision_table.md + openapi.yaml + quote_states.puml |

  Add-one (component alone on top of A2 — standalone sufficiency):

  | Arm | Bundle |
  |---|---|
  | C+spec | A2 + contract/spec.md |
  | C+dt | A2 + contract/decision_table.md |
  | C+api | A2 + contract/openapi.yaml |
  | C+states | A2 + contract/quote_states.puml |

  Leave-one-out (component removed from A3 — necessity in the
  bundle):

  | Arm | Bundle |
  |---|---|
  | C−spec | A3 − spec.md |
  | C−dt | A3 − decision_table.md |
  | C−api | A3 − openapi.yaml |
  | C−states | A3 − quote_states.puml |

  Artifact order inside the prompt is fixed to W1's A3 order (brief,
  structure, behavior, spec, decision tables, OpenAPI, states);
  subset arms keep relative order. No tests_input artifact appears in
  any arm.

- **Declared information overlaps (the W1-finding-5 analog, stated
  before any run so no outcome can be narrated without them):**
  the behavior artifact is present in every arm and carries the full
  flow shape symbolically, including all five DT-S policy notes
  verbatim as diagram notes; spec.md restates that flow and error
  policy in prose (W1's declared overlap) and carries no numbers by
  kit design. Component adds on top of A2 are therefore:
  **decision_table.md** — every numeric rule (DT-V bounds, DT-S
  bands 41/42/66/67, DT-P constants with the normative P2-before-P3
  order and worked example) plus exact status strings and the
  priced/notified matrix in table form; **spec.md** — exact status
  strings, response-field presence rules (quote_id/price/hold),
  glossary, prose consolidation — no numbers; **openapi.yaml** —
  exact status enum, response-field vocabulary, and the DT-V bounds
  mirrored as schema constraints (the kit's one sanctioned numeric
  redundancy — validation bounds are dually carried by DT and
  OpenAPI; band and price numerics live in DT alone);
  **quote_states.puml** — symbolic lifecycle only; its unique
  content (late-resolution transitions) is outside the grading
  suite's scope by design, so its executed marginal is
  suite-relative and a null here may NOT be quoted as "state models
  are useless". Consequence, stated up front: add-one increments
  measure component value *given* the behavior artifact, never
  standalone artifact value; C−dt uniquely erases the band/price
  numerics while validation bounds survive in the OpenAPI mirror.

- **Named scenario sets (suite sensitivity classes, enumerated):**
  **DTNUM5** = {accept_boundary_41, review_boundary_42,
  refuse_boundary_67, price_exact_heavy, price_exact_both} — the
  scenarios whose pass requires numerics carried ONLY by
  decision_table.md. **VALBOUND2** = {invalid_weight_low,
  invalid_value_over} — DT-V bounds, dually carried (decision table
  + OpenAPI schema mirror). Flow and prior-inverting scenarios
  (quoted_low_risk, refuse_high_risk, store_down_error,
  screening_down_hold) are behavior-carried in every arm. W1's
  CONTRACT7 = DTNUM5 ∪ VALBOUND2.

- **Units and n:** one system (CargoQuote) × 10 conditions ×
  2 generators × 3 runs = **60 scored runs**. Pooled per condition
  (n = 6) carries the claims; per-generator pools reported.
  Quantums, stated up front: one scenario flipped in one run moves a
  pooled n = 6 rate by 1.5 pp (per-generator n = 3 by 3.0 pp); one
  scenario consistently flipped moves a pool by 9.1 pp. **Ceiling
  reading rule (disclosed):** opus's stored A3 is 1.000 — if two or
  more opus add-one arms reach 1.000, opus cannot rank those
  components (W5-E4's ceiling-arithmetic caveat applies); identity
  expectations are then read from the haiku and pooled views with
  the caveat named. Power note: with run-level SD ≈ 0.12 (C4-wave
  observed), a 9 pp gap between n = 6 pools is ≈ 1.3 SE — modest;
  the within-quantum branches below are pre-committed rather than
  left to post-hoc reading.

- **Models, exact IDs:** as the shared frozen base — generators
  `claude-opus-4-8` and `claude-haiku-4-5-20251001`, judge
  `claude-sonnet-5` (independent of both), max_tokens 16000.
  **Declared narrowing:** one vendor, as W1; the comparison note's
  cross-vendor-levers observation is recorded — a Gemini leg would
  be an amendment with its own key and pre-registered arms (charter
  §10), never a silent extension.

- **Prompts:** stack-bundle-v2 unchanged, byte-identical entry
  contract by import; the prompt is identical across arms, only the
  bundle contents differ; rules referring to artifact kinds an arm
  lacks are inert by construction, never edited per arm (W1's rule,
  unchanged).

- **Driver (disclosed harness work, freeze prerequisite):**
  tools/stack_ablation.py extended **data-side only** — eight new
  ARMS entries and the W1b comparison pairs in the analysis; the
  assembly, generation, runner/overlay and judge paths are
  untouched. Pre-freeze equivalence obligations (the W5
  adversarial-pass precedent): (1) the revised driver's assembled A2
  and A3 bundle texts are byte-identical to W1's stored prompts;
  (2) stored W1 A2/A3 artifacts replay bit-for-bit through the
  revised scoring path. Driver sha256 pinned at freeze.

- **Token accounting (for the per-thousand-tokens committed
  output):** artifact tokens per arm = API-reported input tokens
  minus the in-wave A2 arm's, per generator; raw char counts at
  draft time: spec.md 3 342 c, decision_table.md 2 989 c,
  openapi.yaml 2 092 c, quote_states.puml 934 c (contract total
  9 357 c, as W1 recorded).

- **Oracle-separation declaration:** no arm includes tests-as-input
  (acceptance.feature appears nowhere above), so the input-tests ↔
  grading-suite relationship is trivially disjoint; the VALUE9/LEAK2
  partition is not needed in this wave.

## Oracles (mandatory)

- **Primary — execution:** the frozen cargo_quote_suite (11
  scenarios, sensitivity classes as the suite header; hash above)
  under the unchanged runner and OVERLAYS; full and semantic-only
  pass-rates both reported; hashes re-verified at freeze.
- **Secondary — judged:** invented-business-logic count per run,
  C4-wave rubric and JSON schema, judge as above; judgments quoted
  as judgments, never merged with executed numbers.
- **Committed outputs:** the two component-marginal tables —
  executed pp per contract component in both directions (add-one
  increments over in-wave A2; leave-one-out drops from in-wave A3)
  — plus executed pp per thousand artifact tokens per component,
  the per-scenario slot tables they derive from, and the additivity
  readout (Σ add-one vs the in-wave jump — E5).
- **Analysis standards:** as W1 verbatim — gaps, orderings and
  correlations, never absolute rates; pooled-per-condition is the
  headline unit; no hard-demand partials on executed gradients;
  judged gradients may carry the partial with both rationales
  cited.

## Calibration (mandatory, disclosed)

- **Inherited (no new API calibration needed):** W1's
  generation-calibration PASSED on this exact pipeline — same
  substrate, prompts, models, suite, runner (attempt 2,
  stack-bundle-v2: opus median 11/11, haiku median 10/11; records
  results/W1/calib/). W5's pass additionally proved stored-artifact
  replay equivalence for the shared scoring path.
- **W1b-specific $0 checks before freeze:** smoke_test.py re-run
  (reference 11/11 + three mutants caught exactly); driver dry-run
  printing every arm's file inventory against the tables above; the
  two byte-identity/replay obligations under Design. **No scored,
  degraded or partial condition may be executed pre-freeze — every
  contract-subset bundle is a new condition and none has ever been
  run.**

## Pre-registered expectations (mandatory)

- **E1 (the decision tables carry the bundle — the wave's
  headline):** C+dt's pooled add-one increment over in-wave A2 is
  the largest of the four (tie rule) and ≥ +9 pp; AND C−dt's pooled
  leave-one-out drop from in-wave A3 is the largest of the four and
  ≥ 9 pp.
- **E2 (the value sits where the numbers are):** C+dt's net
  slot-gains over A2 are concentrated in DTNUM5 ∪ VALBOUND2 (> ½ of
  total net gain, total > 0).
- **E3 (the sanctioned mirror is a real fallback carrier):** C−dt's
  net slot-losses vs A3 are concentrated in DTNUM5, with VALBOUND2's
  net loss within one pooled slot-quantum (the OpenAPI schema mirror
  keeps the validation bounds when the table leaves).
- **E4 (the redundant carriers are individually removable —
  pre-registered nulls, one bar each):** each of C−spec, C−api,
  C−states drops < 9 pp pooled vs in-wave A3 (three separately
  reported verdicts E4-spec / E4-api / E4-states).
- **E5 (additivity — W1-E4's question at component grain):**
  |Σ (four add-one increments) − (in-wave A3−A2 jump)| ≤ 9.1 pp
  (one consistently-flipped scenario). Overshoot beyond +9.1 pp =
  subadditive (components substitute — redundant carriage of the
  same decisions); undershoot beyond −9.1 pp = superadditive (the
  bundle exceeds its parts — glue interaction).
- **E6 (judged invention, secondary):** the A2→C+dt step shows the
  largest median invented-business-logic drop of the four add-one
  steps, strictly positive, in each generator separately (W1
  precedent for the full bundle: opus 6→3, haiku 5→3). Quoted
  strictly as judgment.
- **E7 (cross-generator concordance — §8.3 discipline):** both
  generators agree on the identity of the largest add-one component
  (per-generator tie quantum 3.0 pp; ceiling reading rule applies).

**Validity guards (pre-committed, not expectations):**

- **G1 (the decomposition target must exist in-wave):** in-wave
  (A3 − A2) pooled ≥ 18 pp (2× materiality; W1 stored +37.9). Below
  that, this occasion cannot attribute a bundle effect it did not
  reproduce: expectations are still reported, labeled
  underpowered-on-this-occasion; the cross-occasion anomaly is
  recorded (W5 run-note precedent); no component-identity claim is
  made.
- **G2 (floor):** in-wave A3 pooled > 0.30 per generator; below,
  suspect harness/adapter defect — halt, investigate, disclose; any
  fix forces a conscious re-freeze.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| E1 | Charter §6 contract row gains component attribution, dated ("the decision tables carry it" — worded per-generator if E7 fails); minimum-sufficient-stack §1 and the pilot-facing sentence name the decision tables as the artifact to require; contract-presence rule wording names them (builds stay demand-gated) | Attribution stays bundle-level program-wide, published with equal prominence; if a different component leads (tie rule), that identity is recorded and the spec-stack / SDD-manifest rows update to it |
| E2 | The kit's numbers-only-in-DT design is validated as the value locus — the mechanism reading behind E1 | DT's value flows through non-numeric channels (status strings, the explicit priced/notified matrix) — recorded; W3b's form-vs-content question gains priority |
| E3 | Sanctioned redundancy is executed-real as a fallback carrier: one-source-per-decision guidance keeps its cost wording and gains "a mirrored schema bound held when the table left" | The mirror was not consumed (VALBOUND2 collapses with DT): machine-shape redundancy is decoration at this lab's scale — SDD-manifest machine-readable rows gain the negative |
| E4 (×3) | That component is individually removable at fixed information — a redundant carrier; for E4-states this answers the reviewer's state-diagram question **suite-relative** (its unique lifecycle content is ungraded by design — the scoping travels with every quote) | That component carries executed value beyond its redundant content — a measured surprise; the consolidated document's §1 gains the component row and the overlap declaration is re-examined before any reuse |
| E5 | Component marginals are additive-compatible: the add-one table is quotable as a decomposition of the bundle jump | Subadditive: components substitute — the bundle is redundant carriage; attribution claims quote the LOO direction only, and the one-source-per-decision doctrine gains the executed citation. Superadditive: the bundle exceeds its parts — glue interaction recorded; claims stay bundle-level; the interaction row replaces the marginal table as the headline |
| E6 | The invention cut localizes to the decision tables (judged, per-generator) | Recorded; invention–contract claims stay bundle-scoped |
| E7 | Component identity is portable across capability tiers — "ordering, not magnitude" claim language | §8.3 pattern: component claims quoted per-generator until re-measured; the consolidated document says so instead of recommending |

## Budget (mandatory)

- **Ceiling $30 (hard, harness cost guard).** Estimate **$10–15**:
  60 generations (30 opus ≈ $0.17, 30 haiku ≈ $0.04) + 60 judge
  calls @16k ≈ $0.14 ≈ $14.7 central, per W1's recorded per-call
  figures (W1 actual: $12.18 for 66 cycles). **MAX_CALLS 250** (plan
  ≈ 120 calls; ≈ 2× headroom). Costs recorded per phase in Results.

## Carried limitations (mandatory)

- Toy-scale, one system, n = 3 per condition per generator (pooled
  6); **single-shot generation** — W5 measured the k ≤ 2 agentic
  transfer for the full bundle, not per component, so component
  claims are single-shot until a W5-style leg re-measures them; LLM
  judge; both generators one vendor (Gemini leg = amendment, never
  silent); carrier-per-component fixed — "the decision tables win"
  licenses no claim about table *form* vs number *content* (W3b) and
  none about DMN or any unmeasured carrier; add-one increments are
  conditional on the behavior artifact (flow information present in
  every arm — no standalone-artifact reading); the states marginal
  is suite-relative (late-resolution transitions ungraded by
  design); capability-relative, dated — pivotal contrasts re-measure
  per model generation (charter §2 C1).

## Results

*(Empty by design: draft, pre-verification. Written strictly after
the freeze and the owner's go, run notes before verdicts, per the
template.)*
