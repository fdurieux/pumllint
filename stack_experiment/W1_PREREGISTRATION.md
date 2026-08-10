# Wave pre-registration — W1: artifact-portfolio ablation

*Verified revision for owner review, 2026-08-10 — NOT yet frozen.
Draft committed afe12a5 (findings-before-verdicts); independent
adversarial pass the same day against that commit: **17 findings — 7
major, 10 minor — all adopted in this revision.** Freeze happens only
after: (1) owner edits/approval, (2) the driver exists
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
  behavioral-content and contract rows (whose presence-of-artifact
  measurements are currently LoanCheck-only; the sequence cliff
  already spans three families).
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
- The package-level lint observation
  (docs/spec-stack-evaluation.md) — whether portfolio results bear on
  it (charter §7 W1 names this feed).
- W4 and W5 design inputs (dose–response ladder placement; the
  visible/hidden split if E3 exposes leakage).

## Design (mandatory)

- **Conditions/arms (9 unique; information varies,
  carrier-per-information-class fixed — no artifact is re-rendered
  across arms; charter §2 E3):**

  Additive ladder (nested; each rung adds one artifact class):

  | Arm | Bundle |
  |---|---|
  | A0 brief | brief.md |
  | A1 +structure | A0 + structure/containers.puml |
  | A2 +behavior | A1 + behavior/quote_flow.puml (L5, 100/100) |
  | A3 +contract | A2 + contract/spec.md + decision_table.md + openapi.yaml + quote_states.puml |
  | A4 +tests (full) | A3 + tests_input/acceptance.feature |

  Leave-one-out from A4 (whole artifact class removed):

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

  **Declared information overlap (adversarial finding 5):** spec.md —
  present in every LOO arm — restates the flow order and error policy
  in prose, including the prior-inverting hold rule; the kit's
  numbers-only-in-DT dedup rule covers numeric rules, not flow
  statements. L-behavior therefore removes the behavior *carrier*
  while flow information persists in prose: its drop measures carrier
  redundancy for flow information, not flow-information absence.
  E5's "absent" arm is artifact-absence within a stack whose prose
  still states the flow — the realistic ungated-stack condition, and
  the charter §4 contrast as recorded (which is about artifacts, not
  information erasure). All narration of E4/E5 outcomes carries this
  scoping.

  The brief is present in every arm: it is the task statement, not a
  treatment. Artifact order inside the prompt is fixed to the additive
  order for every arm (no per-arm reordering — order would otherwise
  confound the ablation).

- **Units and n (power-boosted on the E5 contrast — adversarial
  finding 7):** one system (CargoQuote) × 9 conditions ×
  2 generators; runs per generator: **3** for A0, A1, A2, A3,
  L-structure, L-contract; **5** for A4, L-behavior, BC-behavior.
  Total **66 scored runs**. Pooled per condition carries the claims
  (n = 6 or n = 10); per-generator pools reported. Granularity, stated
  up front: one scenario flipped in one run moves an n = 3
  per-generator pool by 3.0 pp (full pool 1.5 pp) and an n = 5
  per-generator pool by 1.8 pp (full pool 0.9 pp); one scenario
  flipped consistently across any pool moves it by 9.1 pp. Power note,
  disclosed: with run-level SD ≈ 0.12 (C4 wave observed), the E5
  difference at n = 10 vs n = 10 has SE ≈ 5.3 pp, so the 9 pp bar is
  ≈ 1.7 SE — modest power; the within-quantum branch of E5 is
  pre-committed below rather than left to post-hoc reading. Mixed n
  across conditions is deliberate and disclosed; rate comparisons are
  unaffected, quantums differ as stated.

- **Models, exact IDs (live-probed before freeze — never from
  memory):** generators `claude-opus-4-8` (adaptive thinking, the
  stored-wave mainline) and `claude-haiku-4-5` (no adaptive thinking —
  house shim omits it; generator precedent: the gen-haiku wave,
  57 runs, $2.41). Judge `claude-sonnet-5`, independent of both
  generators, JSON-schema-constrained, max_tokens 16000 (C4
  uniformity lesson). **Amplification scoping (adversarial finding
  6):** the measured weak-generator amplification is judged-oracle
  only (D2: haiku fidelity cliff 15.5 pts vs opus 12.7); on the
  executed oracle the haiku cliff sits inside the opus range and
  EVIDENCE.md marks that sample as carrying little weight. E8 is
  therefore a **first executed test** of amplification, not a
  replication, and its outcome may not be quoted as replicating a
  prior executed result. **Declared narrowing:** both generators are
  one vendor. The amplification contrast is within-vendor by design,
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
  tools/codegen_experiment.py for cross-program comparability
  (verified byte-identical between the two harness files at draft
  time). The prompt is identical across arms; only the bundle
  contents differ. Rules referring to artifact kinds an arm lacks are
  inert by construction, never edited per arm.

- **Driver (freeze prerequisite, disclosed harness work):**
  `tools/stack_ablation.py`, new — assembles arm bundles from
  stack_experiment/cargo_quote/, calls the generators via the house
  shim (join over content blocks, retry-once on empty/API error,
  thinking-token accounting), applies suite OVERLAYS driver-side
  after a runner pass (the c4 precedent, generalized per the W0
  README), records per-run: generated code, raw response,
  **per-scenario runner outcomes and overlay verdicts (the scored
  slot table), judge raw JSON**, API-reported input/output tokens,
  cost, run index. Stored under `stack_experiment/results/W1/` and
  committed (full-record style). Before freeze, its stopping rules
  are cross-checked against every expectation arm below (the X-R1
  unreachable-arm lesson).

- **Token accounting (for the per-thousand-tokens output):** artifact
  tokens per arm = API-reported input tokens of that arm minus A0's,
  per generator; raw char counts recorded alongside (kit at draft
  time: brief 963 c, structure 1 492 c, behavior 3 366 c / bad 771 c,
  contract 9 357 c across four files, tests 2 874 c; full A4 bundle
  ≈ 18.1 kc ≈ 4.5 k tokens).

- **Oracle-separation declaration (mandatory — tests-as-input arm;
  restated per adversarial finding 1 so the grading suite is
  partitioned):**
  stack_experiment/cargo_quote/tests_input/oracle_overlap.md (authored
  in W0, before the draft) declares the input↔grading relationship.
  For analysis, the **grading-side partition** is pre-declared here:
  - **Leakage-exposed (2):** invalid_weight_low, screening_down_hold —
    the two grading scenarios whose behavior a same-class input
    scenario states outright (G2, G4).
  - **Value-bearing (9):** the five adjacent-mapped scenarios
    (quoted_low_risk, refuse_high_risk, price_exact_heavy,
    price_exact_both, review_boundary_42) plus the four the input set
    does not reveal at all (accept_boundary_41, refuse_boundary_67,
    invalid_value_over, store_down_error) — the latter are the
    strongest value evidence.
  - **Disjoint input behavior (G7, notification-failure tolerance) is
    unobservable on the executed oracle by construction** — the
    grading suite never stubs a notification failure. It is watched
    on the judged oracle only, as an observation, not an expectation.

## Oracles (mandatory)

- **Primary — execution:** tools/acceptance/cargo_quote_suite.py,
  11 scenarios, sensitivity-classed [flow]/[contract]/[prior-inverting]
  (suite header; compound classes exist and every named scenario set
  in this document is enumerated by name, never by class shorthand).
  Draft-time sha256
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
- **Committed outputs (charter §7 W1):** Results MUST contain the two
  marginal tables — executed pp per artifact class in both directions
  (additive increments; leave-one-out drops), and executed pp per
  thousand artifact tokens — plus the per-scenario slot tables they
  derive from.
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
  works end-to-end on generated (not hand-written) code. Bar,
  **per generator** (adversarial finding 13): that generator's 3-run
  median ≥ 9/11; and every scenario passed by ≥ 1 of the 6 runs
  overall. Any adapter/suite fix it forces is made and disclosed
  here, then the suite hash is pinned and the freeze commit lands.
  Falling short of the bar blocks the freeze — fix, disclose,
  re-calibrate.
- **Placeholders filled at freeze:** calibration counts + cost, final
  suite hash, driver hash, freeze date + commit.

## Pre-registered expectations (mandatory)

**Shared definitions (adversarial findings 3, 11):**
- *Materiality bar:* ≥ 9 pp pooled executed (one
  consistently-flipped scenario), applied wherever "material" or a
  pp bar appears.
- *Net slot-gains between two arms:* per scenario, (slot-passes in
  the higher arm) − (slot-passes in the lower arm), summed over a
  named scenario set; "concentrated in set S" / "majority" means net
  gains on S > ½ of total net gain, with total net gain > 0.
- *Tie rule:* pooled rates within one slot-quantum of their pool
  count as tied; where a comparison spans pools of different n, the
  larger quantum applies; an identity clause ("largest", "top",
  "bottom") passes if the expected member is in the tied extreme set.
- *Named scenario sets:* **CONTRACT7** = {accept_boundary_41,
  review_boundary_42, refuse_boundary_67, price_exact_heavy,
  price_exact_both, invalid_weight_low, invalid_value_over} (every
  scenario whose class includes [contract], compounds included).
  **FLOWPI6** = {quoted_low_risk, refuse_boundary_67,
  refuse_high_risk, invalid_weight_low, screening_down_hold,
  store_down_error} (class includes [flow] or [prior-inverting]).
  **VALUE9 / LEAK2** = the grading-side partition declared in Design.

- **E1 (behavior is the lever):** A1→A2 pooled increment ≥ +9 pp and
  is the largest additive increment (tie rule applies). (Precedent:
  C4 R2→R3 +29.2 pp — the direct arrival analog. The 16–25 pp
  sequence cliff is adjacent support only: it measures quality
  degradation within a present artifact, not arrival.)
- **E2 (adversarial contract — the wave's headline):** A2→A3 pooled
  increment ≥ +9 pp, with net slot-gains concentrated in CONTRACT7.
  (LoanCheck measured 0.0 pp here under canonical thresholds;
  CargoQuote's values are non-canonical by construction — this either
  resolves the EC3 confound or hands the contract rung a real null.)
- **E3 (tests-as-input):** A3→A4 pooled increment ≥ +9 pp with net
  slot-gains concentrated in VALUE9 — that is the confirmation bar
  for the charter §6 row upgrade. A positive-but-immaterial increment
  is reported as a directional note only (row stays [external]); net
  gains concentrated in LEAK2 are reported as leakage-exposed, not as
  artifact value, whatever their size.
- **E4 (directional concordance):** the largest leave-one-out drop is
  L-behavior, and the LOO ranking's top and bottom match the additive
  ranking's (both rankings are over the same four artifact classes;
  tie rule applies; narration carries the Design overlap scoping).
- **E5 (below-cliff vs absent — charter §4 obligation, n = 5/generator
  arms):** BC-behavior pooled ≤ L-behavior pooled − 9 pp, with ≥ half
  of the net slot-losses (BC vs L-behavior) on FLOWPI6.
- **E6 (the prior-inverting instrument works):** scenario
  screening_down_hold's pooled pass-rate over the
  hold-information-carrying conditions {A2, A3, A4} exceeds the
  non-carrying {A0, A1} by ≥ +33 pp (pools of 22 and 12 runs;
  BC excluded as degraded). Rider: refuse_boundary_67's
  {A2,A3,A4} − {A0,A1} pooled difference is positive. (The hold path
  arrives with the behavior artifact at A2 — quote_flow.puml carries
  it — hence the split at A2, not A3.)
- **E7 (judged invention, secondary):** median judged inventions/run
  strictly decreases A2→A3 in both generators (equal medians =
  failed). (Precedent — a mean, not a median: R3→R4 6.00 → 4.00/run.)
  Quoted strictly as a judgment.
- **E8 (cross-generator — first executed amplification test, per the
  Design scoping):**
  (a) *concordance:* both generators agree on the identity of the
  largest additive increment (tie rule applies);
  (b) *amplification, exploratory-graded:* haiku's A1→A2 increment
  and haiku's (A4 − BC-behavior) drop each exceed opus's by more than
  one per-generator slot-quantum of the pools forming that gap
  (3.0 pp for A1→A2; 1.8 pp for A4 − BC); differences within one
  quantum are reported as indistinguishable, not as support.

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

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| E1 | Behavioral-content arrival lever generalizes to a second system; charter §6 row gains it | Lever is system-relative; §6 wording narrowed; W4 ladder design revisited before it runs |
| E2 | Contract value upgraded from invention-only to executed under adversarial thresholds; EC3 confound recorded resolved; spec-stack + SDD-manifest rows updated to measured; contract-presence rule wording gains outcome grounding (builds stay demand-gated) | Published as a headline null: written contracts cut invention but not executed failures even when priors cannot guess — companion-spec claim language stays invention-scoped everywhere it is quoted |
| E3 | §6 tests-as-input row → measured (this lab, this scale); W5 visible/hidden split informed | Positive-but-immaterial: directional note, row stays [external]. Gains in LEAK2: leakage-exposed — row stays [external] with the in-house caveat, and W5's split becomes a mandatory design element. Negative: recorded; recommendations quoting tests-as-input cite the negative |
| E4 | Portfolio claims quotable in either direction (with the carrier-redundancy scoping on L-behavior) | Order/interaction effects exist; claims restricted to the additive direction; interaction follow-up recorded, not queued |
| E5 | The constitutive-gates risk policy gains its missing harm-vs-absence leg (bounded: one system, one artifact class, prose flow present in both arms); §8.1 stays external-evidence-gated | Within one materiality bar either way: recorded as an underpowered null — §4 keeps the risk-policy label with "the lab contrast did not resolve it" noted; no support claimed in either direction. BC ≥ L-behavior + 9 pp: direction reversed — §4 reworded to say the lab contrast contradicts the policy's sharpest reading; partial §8.1 signal, published with the same prominence as a confirmation |
| E6 | Prior-inverting instrument validated for W2–W4 reuse | If no condition pins screening_down_hold, the instrument note goes on the kit and W2–W4 designs adjust before running |
| E7 | Invention–contract link replicates on a second system (judged, median) | Recorded; invention claims stay LoanCheck-scoped |
| E8 | (a) orderings portable across capability tiers — claim language keeps "ordering, not magnitude"; (b) if the exploratory arm clears its quantum bar, executed amplification is recorded as a first observation (never as replication) | (a) failed: §8.3 partially fires — stack claims become per-generator; the consolidated document must say so instead of recommending. (b) indistinguishable or reversed: recorded; the charter's "known effect" phrasing is corrected to judged-only wherever quoted |

## Budget (mandatory)

- **Ceiling $30 (hard, harness cost guard).** Estimate **$13–21**,
  records-grounded (adversarial finding 8): the C4 precedent $4.31
  decomposes as $0.22 calibration + $2.52 wave (15 gen + 15 judge) +
  $1.29 re-judge (9 × 16k) + $0.28 uniformity — ≈ $0.29 per full
  cycle upper bound; per-call figures from the stored waves: opus gen
  ≈ $0.17, haiku gen ≈ $0.04 (gen-haiku $2.41/57), judge@16k
  ≈ $0.14. Plan: 33 opus + 33 haiku generations + 66 judge calls +
  6 calibration runs ≈ $16 central. **MAX_CALLS 250** — a live
  counter over every API call the driver makes (generation, judge,
  retries, calibration); crossing it aborts the wave regardless of
  spend (plan ≈ 138 calls; ≈ 1.8× headroom). Costs recorded per phase
  in Results.

## Carried limitations (mandatory)

- Toy-scale, one system (CargoQuote) — no cross-system replication
  inside this wave; n = 3 per condition per generator (5 on the three
  E5 conditions; pooled 6/10); single-shot generation (the agentic
  condition is W5); LLM judge; both generators one vendor (declared
  above); carrier-per-information-class fixed — carrier effects are
  W3's question, and this wave's arms vary which artifacts are
  present, never how an artifact renders its information;
  capability-relative — results dated, pivotal contrasts re-measured
  per model generation (charter §2 C1).

## Results ([date], $[cost])

*Written strictly after the freeze. Run notes recorded before the
verdicts (harness incidents, retries, protocol deviations — however
embarrassing). Then per-expectation verdicts: confirmed / failed, with
the pre-committed interpretation applied, never reinterpreted.*
