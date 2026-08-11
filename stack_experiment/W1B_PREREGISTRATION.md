# Wave pre-registration — W1b: the contract-bundle decomposition

*FROZEN 2026-08-11, before any scored run — the freeze is the commit
titled "Lab: W1b frozen" carrying this file with the pins under
Calibration § Frozen values. Provenance: draft 4887dec
(findings-before-verdicts); independent adversarial pass against it —
**17 findings: 8 major, 9 minor, all adopted** (fb8e9ad; the pass
additionally verified every quoted W1 number, both oracle hashes, the
char counts, the quantum and budget arithmetic, the DT-V mirror
values, and the named-set identity DTNUM5 ∪ VALBOUND2 = CONTRACT7
against the working tree); driver build + $0 pre-freeze checks
**33/33 PASSED** (c11b672), two dated pre-freeze amendments marked
inline (driver placement; checks record). **Owner go on the scored
run given 2026-08-11, in the owner's words: "freeze and go".** From
here, editing anything above the Results section invalidates the
wave — re-freeze consciously and say so. Lineage: W1-E4's fired
matrix branch ("interaction follow-up recorded, not queued") given
its concrete shape; recorded as a wave candidate in ROADMAP § Settled
questions and docs/external-review-evaluation.md § wave candidates;
the before-any-benchmark-freeze sequencing rationale is recorded in
docs/external-review-comparison.md's commissioned feedback column —
Claude-authored at the owner's request, not itself an owner decision
(adversarial finding 5; the owner decision on THIS wave is the go
quoted above). Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base (by import from W1, unchanged):** the W1 models
(`claude-opus-4-8`, `claude-haiku-4-5-20251001`; judge
`claude-sonnet-5` @16000, C4-wave JSON schema and rubric), prompt
variant stack-bundle-v2 with the byte-identical entry contract, the
frozen suite (tools/acceptance/cargo_quote_suite.py, sha256
`113ab6ac…9b501`) and runner (`f6cc907e…2fe7c88`) with their OVERLAYS,
and W1's shared definitions: materiality ≥ 9 pp pooled executed; net
slot-gains rate-based over named scenario sets; the tie rule with
per-pool quantums. Hashes re-verified and re-pinned at the freeze
commit.

**Disclosed deviation from the recorded candidate (finding 17):** the
candidate is recorded as contract classes "isolated factorially"; this
wave runs an **ablation, not a factorial** — 8 of the 14 non-anchor
subsets (four add-one, four leave-one-out; the six pairwise bundles
are unmeasured). Pairwise interactions are visible only through E5's
aggregate residual. Rationale: budget and the house additive+LOO
instrument (W1's own shape). If E5's residual is material, the
factorial completion is the recorded follow-up shape — not queued.

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
  attribution fails. Every attribution quote carries the
  suite-composition scoping under Oracles (finding 7).
- **docs/minimum-sufficient-stack.md §1 and the pilot-facing
  sentence:** "the written decision contract is the load-bearing
  artifact" becomes actionable for an adopter who must choose what
  to mandate — one file or four.
- **The external review's open question** (comparison note row
  "Contract bundle (A3) decomposition"): state diagram? OpenAPI
  enough? Answered with empirical precision at this lab's scale.
  The sequencing consequence — this result decides the artifact set
  of any future domain benchmark, so it belongs before any benchmark
  freeze — is recorded in that note's commissioned feedback column
  (not an owner decision; finding 5).
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
  any arm. **Positional asymmetry, disclosed (finding 16):** in an
  add-one arm the component sits directly after behavior and last in
  the prompt; in A3 and the LOO arms the same component sits at its
  W1 depth — a component's two directions are measured at different
  context positions, a residual confound this scale does not
  disentangle. **Dose inequality, disclosed (finding 15):** the four
  components span 934–3 342 chars (3.6×), so add-one identity
  comparisons ride unequal token doses — a live variable for the
  weak generator per W4; identity claims are per-artifact, never
  per-token, with the per-ktok committed output as the control view.

- **Declared information overlaps (the W1-finding-5 analog, stated
  before any run so no outcome can be narrated without them; wording
  corrected per adversarial finding 8):**
  the behavior artifact is present in every arm and carries the full
  flow shape symbolically, including five diagram notes that
  **paraphrase** the DT-S policy notes, each citing its note number —
  NOT verbatim: the note-3 paraphrase omits the exact status string
  `error: store_unavailable` and the note-5 paraphrase omits
  `held_unscreened` and the `hold: true` response flag, all of which
  the decision tables carry (finding 8a). spec.md restates the flow
  and error policy in prose (W1's declared overlap) and carries no
  numbers by kit design. Component adds on top of A2:
  **decision_table.md** — every numeric rule (DT-V bounds, DT-S
  bands 41/42/66/67, DT-P constants with the normative P2-before-P3
  order and worked example) plus exact status strings and the
  priced/notified matrix in table form; **spec.md** — exact status
  strings, response-field presence rules (quote_id/price/hold),
  glossary, prose consolidation — no numbers; **openapi.yaml** —
  exact status enum, response-field vocabulary **with the same
  presence rules in its field descriptions ("Present whenever a
  draft was stored", "Present exactly on the priced rows", "true
  exactly on held_unscreened") — a declared spec↔openapi overlap for
  narrating C−spec and C+api (finding 8b)** — and the DT-V bounds
  mirrored as schema constraints (the kit's one sanctioned numeric
  redundancy — validation bounds are dually carried by DT and
  OpenAPI; band and price numerics live in DT alone);
  **quote_states.puml** — the symbolic lifecycle, **plus
  suite-visible decision content beyond lifecycle: its action labels
  encode the priced/notified matrix (priceAndNotify /
  holdWithoutPricing / notifyRefusal / priceAndHold) and its state
  names supply overlay-matchable status vocabulary (finding 8c)**;
  its unique content (late-resolution transitions) is outside the
  grading suite's scope by design, so its executed marginal is
  suite-relative and a null here may NOT be quoted as "state models
  are useless". Consequence, stated up front: add-one increments
  measure component value *given* the behavior artifact, never
  standalone artifact value; C−dt uniquely erases the band/price
  numerics while validation bounds survive in the OpenAPI mirror.

- **Named scenario sets (enumerated; sets are defined by their
  enumerations):** **DTNUM5** = {accept_boundary_41,
  review_boundary_42, refuse_boundary_67, price_exact_heavy,
  price_exact_both} — the set that **jointly pins the DT-S bands and
  DT-P constants** (per-scenario accuracy, finding 10: the smoke
  record shows a canonical-threshold mutant still passes
  accept_boundary_41 — that scenario anchors the accept side of the
  band structure rather than requiring DT numerics alone).
  **VALBOUND2** = {invalid_weight_low, invalid_value_over} — DT-V
  bounds, dually carried (decision table + OpenAPI schema mirror).
  **REST4** = the four scenarios in neither set — quoted_low_risk,
  refuse_high_risk, store_down_error, screening_down_hold —
  behavior-carried in every arm; compound suite classes noted
  (refuse_boundary_67 is [contract + prior-inverting],
  invalid_weight_low is [contract + flow]; finding 11). W1's
  CONTRACT7 = DTNUM5 ∪ VALBOUND2.

- **Units, n, and reading rules:** one system (CargoQuote) ×
  10 conditions × 2 generators × 3 runs = **60 scored runs**. Pooled
  per condition (n = 6) carries the claims; per-generator pools
  reported. Quantums, stated up front: one scenario flipped in one
  run moves a pooled n = 6 rate by 1.5 pp (per-generator n = 3 by
  3.0 pp); one scenario consistently flipped moves any rate-based
  pool by 9.1 pp. **Sign convention (finding 6):** an add-one
  increment is (C+x − A2); a LOO drop is (A3 − C−x); both signed —
  a negative LOO drop means removal improved the pool, and it is
  read under E4's dilution branch, never folded into "largest drop"
  (largest = largest positive). **Net slot-gains and their loss-side
  mirror (finding 1):** per-scenario pass-rate deltas between two
  arms' pools, summed over a named set (W1's definition); net
  slot-losses are the same quantity computed A3-minus-arm, so one
  flipped slot in one run moves a set's rate-sum by 1/6 ≈ 0.167.
  "Concentrated in set S" keeps W1's meaning on the loss side: net
  losses on S > ½ of total net loss, with total net loss > 0.
  **Ceiling reading rules (findings 3, 9):** opus's stored A3 is
  1.000. (a) If two or more opus add-one arms reach 1.000, opus
  cannot rank those components — identity expectations are read from
  the haiku and pooled views with the caveat named. (b) E5's
  mechanism claim is carried by the haiku view whenever the opus
  ceiling is in play (two or more opus C+x at 1.000, or opus A3
  in-wave at 1.000): haiku Σ-vs-jump adjudicates, pooled is reported
  with the ceiling caveat, and no subadditivity mechanism claim may
  rest on the pooled arithmetic alone. (c) Under (a), E7 is reported
  **not evaluable for opus** — haiku identity is reported and no
  concordance claim is made or denied; this supersedes the tie rule
  for arms at 1.000. Power note: with run-level SD ≈ 0.12 (C4-wave
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

- **Driver (disclosed harness work, freeze prerequisite — rewritten
  per adversarial finding 4; the draft's "data-side only" claim was
  false):** tools/stack_ablation.py requires real W1b code, not only
  ARMS entries: a **W1b job plan** restricted to the ten arms above
  (the current `--wave` path enumerates every ARMS entry and would
  re-run all nine W1 arms); a **new results root**
  (`stack_experiment/results/W1B/`) and report `pre_registration`
  pointer to this file; and a **W1b analysis block** — add-one and
  LOO marginals against the in-wave anchors (the W1 code hardcodes
  A4 as the LOO baseline and A0 as the token baseline; W1b uses A3
  and A2 respectively), per-ktok rates on the A2 token baseline,
  DTNUM5/VALBOUND2/REST4 net gain and loss sums, the E5 additivity
  residual, judged add-one drops, and every E1–E7/G1–G2 expectation
  input. The assembly, generation, runner/overlay and judge paths
  are untouched. **Pre-freeze equivalence and cross-check
  obligations (three, the third added by finding 4):** (1) the
  revised driver's assembled A2 and A3 bundle texts are
  byte-identical to W1's stored prompts; (2) stored W1 A2/A3
  artifacts replay bit-for-bit through the revised scoring path;
  (3) the revised analysis, run against W1's stored A2/A3 runs,
  reproduces the stored marginals exactly, and an expectation-inputs
  dry-run emits every E1–E7/G1–G2 input (the W1 X-R1
  unreachable-arm lesson, carried forward). Driver sha256 pinned at
  freeze. *[Amended pre-freeze 2026-08-11, build record: the W1b code
  lives in a separate module, tools/stack_w1b.py, which imports the
  frozen W1 driver and registers the ten arms into its table at
  import — the frozen stack_ablation.py is untouched on disk, so W1's
  pinned sha still describes what W1 ran, and the reused assembly/
  generation/scoring/judge paths are the frozen code itself, not
  copies; arm keys use ASCII '+'/'-' for filename portability. The
  freeze pins stack_w1b.py's sha256, with stack_ablation.py's
  recorded alongside.]*

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
  **Suite-composition scoping (finding 7), attached to every
  outward attribution quote:** the suite is hand-derived with
  decision_table.md as its normative source, and 5 of its 11
  scenarios are constructed to be pinned by DT-only numerics — the
  oracle's composition gives the decision tables the largest
  sensitivity surface **by design**. Component attribution here is
  therefore suite-relative in the same way the states null is; "the
  decision tables carry it" may never be quoted without this
  scoping.
- **Secondary — judged:** invented-business-logic count per run,
  C4-wave rubric and JSON schema, judge as above; judgments quoted
  as judgments, never merged with executed numbers. **Judged-oracle
  handling, inherited and disclosed (finding 12):** non-compiling
  artifacts are never judged; failed judge calls are excluded; a
  judged median may therefore be n-reduced (at n = 2 it is the
  mid-mean) — E6 is read under these conventions and each arm's
  judged n is reported.
- **Committed outputs:** the two component-marginal tables —
  executed pp per contract component in both directions (add-one
  increments over in-wave A2; leave-one-out drops from in-wave A3,
  signed) — plus executed pp per thousand artifact tokens per
  component, the per-scenario slot tables they derive from, the
  named-set net gain/loss sums, and the additivity readout
  (Σ add-one vs the in-wave jump — E5).
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
  three equivalence/cross-check obligations under Design. **No
  scored, degraded or partial condition may be executed pre-freeze —
  every contract-subset bundle is a new condition and none has ever
  been run.** *[Amended pre-freeze 2026-08-11 — the $0 checks RAN and
  PASSED, 33/33: obligation (1) every kit hash and the GEN_PROMPT
  template byte-identical to the stored W1 wave record, A2/A3
  assembled-bundle shas recorded; obligation (2) all 12 stored A2/A3
  artifacts replayed bit-for-bit through the imported scoring path,
  0 mismatches; obligation (3) the W1b analysis reproduced the
  stored A2→A3 marginals exactly (pooled 0.3788, opus 0.5455, haiku
  0.2122) and all four judged medians (6→3, 5→3), and the
  expectation-inputs dry-run emitted all 14 E1–E7/G1–G2 inputs over
  a disclosed synthetic dataset (stored A2 runs cloned into the
  component arms — code-path exercise only, no scoring meaning);
  reference 11/11 through the frozen scoring path; every arm
  inventory matches the Design tables. Record:
  stack_experiment/results/W1B/prefreeze_checks/report.json. No
  generation call was made; spend $0.]*
- **Frozen values:** pre-wave W1B spend $0.00 of the $30 ceiling
  (prefreeze checks $0; no probe or calibration call made — the W1
  calibration is inherited as declared above); suite and runner
  hashes re-verified unchanged at freeze (`113ab6ac…9b501`,
  `f6cc907e…2fe7c88`, as the Shared frozen base); driver
  tools/stack_w1b.py sha256
  `337e64ceead3e3b9102cfbf75c88125e1bef43387805734a9b6f13bc964af1ad`,
  importing tools/stack_ablation.py sha256
  `5134cddbd0950ed2e21c2c5a1772d68f1b62925b3b82713c567dede0c422b73b`
  — byte-identical to W1's frozen pin, confirming the frozen driver
  file is untouched; freeze date 2026-08-11; freeze commit = the
  commit introducing this bullet.

## Pre-registered expectations (mandatory)

- **E1a (add-one identity and materiality — the wave's headline,
  split per finding 9):** C+dt's pooled add-one increment over
  in-wave A2 is the largest of the four (tie rule; ceiling reading
  rule (a)) and ≥ +9 pp.
- **E1b (leave-one-out identity and materiality):** C−dt's pooled
  LOO drop from in-wave A3 is the largest positive drop of the four
  (sign convention above) and ≥ 9 pp. E1a and E1b are adjudicated
  and reported separately; "identity holds in both directions but
  one is submaterial" is a distinct, pre-named outcome — reported as
  identity-confirmed / materiality-partial, not folded into either
  failure.
- **E2 (the value sits where the numbers are — standalone
  mechanism claim, decoupled from E1 per finding 9):** C+dt's net
  slot-gains over A2 are concentrated in DTNUM5 ∪ VALBOUND2 (> ½ of
  total net gain, total > 0).
- **E3 (the sanctioned mirror is a real fallback carrier — units
  fixed per finding 1):** C−dt's net slot-losses vs in-wave A3
  (loss-side mirror, rate-sum) are concentrated in DTNUM5 (> ½ of
  total net loss, total > 0), AND |VALBOUND2 net rate-sum loss|
  ≤ 1/6 — one flipped slot in one run — i.e. the OpenAPI schema
  mirror keeps the validation bounds when the table leaves.
- **E4 (the redundant carriers are individually removable —
  two-sided per finding 6; three separately reported verdicts
  E4-spec / E4-api / E4-states):** for each of C−spec, C−api,
  C−states, |pooled Δ vs in-wave A3| < 9 pp. A component whose
  REMOVAL IMPROVES the pool by ≥ 9 pp is not a confirmation and not
  a plain failure: it takes the pre-committed **dilution branch** —
  excess carriage measured inside the bundle itself, read with W4's
  weak-generator scoping and published with equal prominence.
- **E5 (additivity — W1-E4's question at component grain; ceiling
  reading rule (b) applies):** |Σ (four add-one increments) −
  (in-wave A3−A2 jump)| ≤ 9.1 pp (one consistently-flipped
  scenario), adjudicated on the haiku view whenever the opus ceiling
  is in play, with pooled reported under the named caveat. Overshoot
  beyond +9.1 pp = subadditive (components substitute — redundant
  carriage of the same decisions); undershoot beyond −9.1 pp =
  superadditive (the bundle exceeds its parts — glue interaction).
- **E6 (judged invention, secondary — tie rule per finding 2):**
  C+dt's median judged-invention drop (A2 median minus C+dt median,
  per generator, judged-n conventions per Oracles) is strictly
  positive and **strictly exceeds** each of the other three add-one
  drops, in each generator separately; any tie at the largest =
  failed, reported as the tied set. Quoted strictly as judgment.
- **E7 (cross-generator concordance — §8.3 discipline; ceiling
  reading rule (c) applies):** both generators agree on the identity
  of the largest add-one component (per-generator tie quantum
  3.0 pp). Under opus ceiling, E7 is not evaluable for opus: haiku
  identity is reported, no concordance verdict is issued.

**Validity guards (pre-committed, not expectations):**

- **G1 (the decomposition target must exist in-wave):** in-wave
  (A3 − A2) pooled ≥ 18 pp (2× materiality; W1 stored +37.9). Below
  that, this occasion cannot attribute a bundle effect it did not
  reproduce: expectations are still reported, labeled
  underpowered-on-this-occasion; the cross-occasion anomaly is
  recorded (W5 run-note precedent); no component-identity claim is
  made.
- **G2 (floor — units fixed per finding 14):** each generator's
  in-wave A3 pool > 0.30; below on any generator, suspect
  harness/adapter defect — halt, investigate, disclose; any fix
  forces a conscious re-freeze.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| E1a | Charter §6 contract row gains add-one attribution, dated ("the decision tables carry it"), ALWAYS quoted with the suite-composition scoping (finding 7) and worded per-generator if E7 fails or is not evaluable; minimum-sufficient-stack §1 and the pilot-facing sentence name the decision tables; contract-presence rule wording names them (builds stay demand-gated) | If another component leads (tie rule): that identity recorded, spec-stack / SDD-manifest rows update to it. If C+dt leads but < +9 pp: identity-confirmed / materiality-partial, attribution language stays bundle-level with the direction noted. Published with equal prominence either way |
| E1b | The necessity direction concurs — attribution quotable in both directions (with finding-7 scoping) | LOO disagrees with add-one: direction-dependent attribution recorded; claims restricted to the direction that held (W1-E4 precedent); interaction reading deferred to E5 |
| E2 | The kit's numbers-only-in-DT design is validated as the value locus — a mechanism statement standing on its own (decoupled from E1 verdicts) | DT's value flows through non-numeric channels (status strings, the explicit priced/notified matrix) — recorded; W3b's form-vs-content question gains priority |
| E3 | Sanctioned redundancy is executed-real as a fallback carrier: one-source-per-decision guidance keeps its cost wording and gains "a mirrored schema bound held when the table left" | The mirror was not consumed (VALBOUND2 collapses with DT): machine-shape redundancy is decoration at this lab's scale — SDD-manifest machine-readable rows gain the negative |
| E4 (×3) | That component is individually removable at fixed information — a redundant carrier; for E4-states this answers the reviewer's state-diagram question **suite-relative** (its unique lifecycle content is ungraded by design — the scoping travels with every quote) | |Δ| ≥ 9 pp toward harm: the component carries executed value beyond its redundant content — a measured surprise; the consolidated document's §1 gains the component row and the overlap declaration is re-examined before any reuse. Removal-improves ≥ 9 pp: the dilution branch — excess carriage inside the bundle, W4 cross-reference with its weak-generator scoping, published with equal prominence |
| E5 | Component marginals are additive-compatible: the add-one table is quotable as a decomposition of the bundle jump (haiku-adjudicated under opus ceiling, caveat named) | Subadditive: components substitute — the bundle is redundant carriage; attribution claims quote the LOO direction only, and the one-source-per-decision doctrine gains the executed citation (only if the verdict survives the ceiling reading rule). Superadditive: the bundle exceeds its parts — glue interaction recorded; claims stay bundle-level; the interaction row replaces the marginal table as the headline; the factorial completion (deviation note) becomes the recorded follow-up |
| E6 | The invention cut localizes to the decision tables (judged, per-generator, judged-n conventions) | Recorded, including tied-largest sets as such; invention–contract claims stay bundle-scoped |
| E7 | Component identity is portable across capability tiers — "ordering, not magnitude" claim language | Disagreement: §8.3 pattern — component claims quoted per-generator until re-measured; the consolidated document says so instead of recommending. Opus-ceiling state: not evaluable for opus, haiku identity reported, no concordance verdict issued or implied |

## Budget (mandatory)

- **Ceiling $30 (hard, harness cost guard) — scoped to this wave
  (finding 13):** W1b records live under the new results root
  `stack_experiment/results/W1B/`, so the guard's cumulative
  accounting starts at $0 for this wave; the $30 is W1b spend alone,
  not shared with results/W1. Estimate **$12–16, central ≈ $14.7**:
  60 generations (30 opus ≈ $0.17, 30 haiku ≈ $0.04) + 60 judge
  calls @16k ≈ $0.14, per W1's recorded per-call figures (W1 actual:
  $12.18 for 66 cycles). **MAX_CALLS 250** — a live counter over
  every API call the driver makes, generation, judge and retries
  included (plan ≈ 120 calls; ≈ 2× headroom). Costs recorded per
  phase in Results.

## Carried limitations (mandatory)

- Toy-scale, one system, n = 3 per condition per generator (pooled
  6); **single-shot generation** — W5 measured the k ≤ 2 agentic
  transfer for the full bundle, not per component, so component
  claims are single-shot until a W5-style leg re-measures them; LLM
  judge with the judged-n conventions above; both generators one
  vendor (Gemini leg = amendment, never silent);
  carrier-per-component fixed — "the decision tables win" licenses
  no claim about table *form* vs number *content* (W3b) and none
  about DMN or any unmeasured carrier; **suite-relative attribution
  (finding 7)** — the grading suite's normative source is
  decision_table.md and 5/11 scenarios grade DT-only numerics, so
  the identity result describes this oracle's composition as much as
  the artifacts and travels with that scoping; add-one increments
  are conditional on the behavior artifact (flow information present
  in every arm — no standalone-artifact reading); **dose inequality
  and positional asymmetry disclosed under Design (findings 15,
  16)**; the states marginal is suite-relative (late-resolution
  transitions ungraded by design); **ablation, not factorial —
  pairwise bundles unmeasured (finding 17)**; capability-relative,
  dated — pivotal contrasts re-measure per model generation (charter
  §2 C1).

## Results

*(Frozen, pre-run. Written strictly after the scored run — run notes
recorded before the verdicts, then per-expectation verdicts with the
pre-committed interpretations applied, never reinterpreted — per the
template.)*
