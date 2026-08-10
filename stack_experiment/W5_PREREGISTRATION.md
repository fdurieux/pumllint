# Wave pre-registration — W5: the agentic condition

*FROZEN 2026-08-11, before any scored run — the freeze is the commit
titled "Lab: W5 frozen" carrying this file, the revised driver
(tools/agentic_codegen.py) and the pinned baselines. Provenance:
draft 07f36aa (findings-before-verdicts); independent adversarial
pass against it — **8 findings: 2 major, 6 minor, all adopted in
this revision** (the pass additionally proved execution-path
equivalence by bit-for-bit replay of stored W1 and C4 artifacts
through this driver). **Owner go on the scored run given 2026-08-11,
in the owner's words: "go ahead with the scored run after the
freeze; then proceed ('go') with the explicit scored-run to complete
the final wave of the charter's runnable program."** Editing
anything above Results after a scored run invalidates the wave.
Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base:** the W1 models (`claude-opus-4-8`,
`claude-haiku-4-5-20251001`; judge `claude-sonnet-5` @16000, C4-wave
schema), the substrates' STORED generation prompts unchanged —
stack-bundle-v2 for cargo arms, the C4 wave's GEN_PROMPT for rung
arms, both by import — the frozen suites
(cargo_quote_suite `113ab6ac…9b501`, c4_loan_suite as frozen for the
C4 wave) and runner (`f6cc907e…2fe7c88`); shared definitions
(materiality ≥ 9 pp pooled; rate-based comparisons; tie quantums per
pool) as frozen in W1_PREREGISTRATION.md.

## Question and decision link (mandatory)

**Question:** Do the standing single-shot claims survive the agentic
workflow — an agent that runs a visible smoke subset and iterates —
or does iteration close the gaps the artifacts were carrying?

**Decision links:** charter §7 W5 verbatim — the external-validity
keystone: it decides how every standing claim must be worded for the
workflows people actually run. Charter §8.4 is the named falsifier
("the cliff collapses under agency" → the gate thesis narrows to
single-shot workflows; response per the capability-horizon
settlement: a reviewed repositioning, never an unattended one).
Charter-pre-registered expectations carried: partial compensation
for suite-covered behavior; invention on uncovered behavior
persists; artifact value shifts from generation input toward
decision record and review oracle — the last is a claim-language
consequence read from E2 + E4's joint pattern, not a standalone bar.

## Design (mandatory)

- **The agentic loop (disclosed harness work,
  tools/agentic_codegen.py):** per run, up to **3 model calls** —
  initial generation with the substrate's stored prompt, then up to
  2 full revisions driven by structured feedback (per-scenario
  failure lines: name, stage, ≤200-char detail — or the compile
  error), in one conversation. After each generation the
  pre-registered VISIBLE subset executes; iteration stops when the
  visible subset passes or calls are exhausted. The FINAL artifact
  is graded on the FULL frozen suite; visible-subset, hidden-subset
  and full rates are all reported. Single-shot arms run the
  identical path with zero revisions.

- **Contrasts and arms (6 arms, 30 runs):**

  | Contrast (standing claim) | Arms | Generators | Baseline |
  |---|---|---|---|
  | Sequence cliff (below-cliff vs L5) | A2 vs A2-BC (cargo A2 bundle; behavior = quote_flow L5 100/100 vs quote_flow_bad L1 29/100) | both | A2: W1 stored (pooled 0.439; hidden-8 subset 0.333, visible-3 subset 0.722). A2-BC: **no stored baseline → in-wave single-shot arm** (A2-BC-single, both generators, n = 3) |
  | Contract lever (W1's headline) | A3 vs A2 | both | W1 stored (A3 pooled 0.818; subset baselines derived from the stored per-scenario tables, frozen at freeze time) |
  | C4 behavior arrival | R3 vs R0 (c4_experiment rungs) | **opus only** — the stored C4 wave was opus-only; declared narrowing for baseline comparability | stored C4 wave: R0 0.417, R3 0.917 executed (invention means 7.0 / 6.0); subset baselines derived from its stored scenario tables, frozen at freeze time |

  **Substrate deviation, disclosed prominently:** the charter's named
  sequence-cliff contrast was the stored corpus families; this wave
  substitutes the CargoQuote sequence pair (same artifact class,
  measured L5 100/100 vs L1 29/100, a frozen suite whose hidden set
  carries the boundary and prior-inverting scenarios, and clean
  stored/derivable baselines on the program's current substrate).
  If W5's sequence result surprises, an agentic corpus-family re-run
  is the recorded follow-up — not queued.

- **Visible smoke subsets (pre-registered; everything else hidden):**
  cargo — quoted_low_risk, invalid_weight_low, refuse_high_risk
  (hidden 8: both DT-S boundaries, refusal-notify, both exact
  prices, value bound, the prior-inverting hold, storage failure);
  c4 — approved_high, invalid_zero, declined_low (hidden 5:
  approved_boundary, borderline_review, over_cap, bureau_error,
  storage_error). Visible sets are deliberately generic — the
  boundary, exact-price and prior-inverting scenarios stay hidden,
  mirroring real smoke tests. Disclosed (adversarial finding 7):
  invalid_weight_low is visible yet contract-carried (the
  non-canonical weight bound), so its feedback can teach part of the
  contract lever to BOTH cargo arms of any contrast — symmetric
  within each contrast, but a real channel, named.

- **Units and n:** cargo arms 2 generators × 3 runs (pooled 6); c4
  arms opus × 3 (pooled 3 — quantums: full 4.2 pp, hidden-5 subset
  6.7 pp, disclosed as coarse). RUNS: 5 agentic arms + 1
  single-shot arm = 30 runs, ≤ 78 model calls + 30 judgements.

- **Baseline plumbing — the derived subset baselines, pinned
  (adversarial finding 3; independently recomputed by the pass):**

  | Single-shot baseline | Visible-3 | Hidden | Full |
  |---|---|---|---|
  | W1 A2 (pooled) | 13/18 = 0.7222 | 16/48 = 0.3333 (opus 0.375 / haiku 0.292) | 0.4394 |
  | W1 A3 (pooled) | 15/18 = 0.8333 | 39/48 = 0.8125 (opus 1.000 / haiku 0.625) | 0.8182 |
  | C4 R0 (opus, stored wave) | 7/9 = 0.7778 | 3/15 = 0.2000 | 0.417 |
  | C4 R3 (opus, stored wave) | 9/9 = 1.0000 | 13/15 = 0.8667 | 0.917 |

  Declared asymmetries (findings 3 and 5): R0/R3's references are
  cross-wave (the stored C4 sampling occasion) while A2-BC's is
  in-wave; and the stored waves' generation path retried once with a
  fresh sample on truncation/non-compile, which this driver's
  single-shot path does not — recorded as negligible (0 retries
  fired and 0 non-compiling finals across all 81 stored runs) but
  carried as a caveat on E1's A2-BC contrast.

## Oracles (mandatory)

As the substrates' waves (frozen suites + runner + overlays,
driver-side; full and semantic-only reported — the driver emits both,
finding 2 adopted; judged inventions via the C4-wave JSON schema,
with each substrate's own stored judge prompt — W1's stack rubric for
cargo arms, the C4 wave's for rung arms — quoted as judgments;
non-compiling final artifacts are excluded from judged medians,
disclosed). Oracle-separation:
the VISIBLE subsets are drawn from the grading suite by design —
that is the treatment (agents run smoke tests they can see), and
hidden-subset rates are the leakage-free outcome measure; cargo
arms carry no tests-as-input artifact (A2/A3 bundles have no
acceptance.feature).

## Calibration (mandatory, disclosed)

Inherited per substrate (W1's calibration for cargo under identical
prompt/models; the C4 wave's for the rungs). W5-specific $0 checks
before freeze: driver dry-run (arm inventories, visible-set
membership, rung presence); the loop exercised end-to-end at $0 by
running the reference implementation through the visible-execution
path. No scored or degraded condition executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W5-E1 (partial compensation on the low arms):** agentic
  full-suite rate minus same-arm single-shot baseline ≥ +9 pp for
  A2-BC (vs in-wave single-shot, pooled) and for R0 (vs stored
  0.417, opus).
- **W5-E2 (the cliff survives agency on hidden behavior):** agentic
  hidden-subset gaps stay material — (A2 − A2-BC) hidden pooled
  ≥ 9 pp, and (R3 − R0) hidden (opus) ≥ 9 pp. **This is §8.4's
  live test:** both gaps collapsing below 9 pp fires the falsifier's
  agentic branch.
- **W5-E3 (the contract lever survives agency):** (A3 − A2) hidden
  pooled ≥ 9 pp.
- **W5-E4 (compensation is suite-covered):** for each low arm with
  a same-configuration single-shot reference (A2-BC, R0), the
  agentic improvement on the VISIBLE subset ≥ its improvement on
  the HIDDEN subset (direction, per the charter's
  partial-compensation wording). Ceiling caveat (finding 3): R0's
  visible headroom is only +22.2 pp vs +80 pp hidden, so an E4-R0
  failure can be pure ceiling arithmetic — the matrix row reads it
  with that caveat before any "generalizes beyond feedback" claim.
- **W5-E5 (judged, secondary; finding 4's re-statement):** for each
  generator with judgeable artifacts on BOTH arms of a contrast,
  the low arm's invented-business-logic median remains ≥ the high
  arm's (A2-BC ≥ A2 per generator; R0 ≥ R3, opus). Split verdicts
  across generators are reported per-generator, never pooled.
  Disclosed inflation mechanism: the judge audits the final
  artifact against the bundle only, blind to feedback — behavior
  learned from visible-test failures is absent from a degraded
  bundle and counts as "invented," and low arms receive more
  feedback; E5's confirmation is read with that bias named.
- **G1 (the condition must bite; finding 1's re-statement):** ≥ ⅓
  of agentic runs contain a revision driven by a VISIBLE-test
  failure (compile-only revisions do not count; the driver records
  the flag per run). Below that, the agentic condition barely
  engaged; the pre-committed joint readings in the matrix apply.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W5-E1 | Iteration recovers part of what degraded artifacts lose — the compensation half of the charter's expectation, quoted with its visible-set scope | No compensation even with test feedback: below-cliff artifacts are not repaired by iteration at k ≤ 2 — strengthens the gate-first posture; recorded |
| W5-E2 | The cliff is workflow-robust: standing claim language KEEPS its validity for agentic workflows (wording upgraded from "single-shot" to "single-shot and k ≤ 2 agentic", dated) | §8.4 partially or fully fires: the gate thesis narrows to single-shot workflows — a reviewed repositioning per the capability-horizon settlement; every standing claim's wording gains the agentic scope note; published with full prominence |
| W5-E3 | W1's headline survives the workflow shift; the contract-rung claim gains the agentic scope | The contract lever is compensable by iteration: W1's claim language gains "single-shot" scoping, dated — a material narrowing, published |
| W5-E4 | "Partial compensation for suite-covered behavior" confirmed as worded — and the artifact-value-shifts claim-language consequence applies ONLY on E2 ∧ E4 jointly confirmed (finding 8c) and only when G1 held (a vacuous E4 under G1-failure licenses nothing — finding 1) | Compensation is NOT visible-concentrated: for R0 the ceiling caveat is checked first; if the pattern survives it, iteration generalizes beyond its test feedback — recorded as a genuine surprise; the claim-language consequence does not apply |
| W5-E5 | Invention persists on uncovered behavior (judged, per-generator), matching the charter expectation — read with the disclosed feedback-inflation bias | Iteration cuts invention on the low arms: judged-only finding, recorded; no executed claim |
| G1 | — (gate, not a claim) | Reported as the run-note scoping every verdict. **Pre-committed joint readings (finding 1):** G1-failed × E2-not-confirmed = a single-shot replication anomaly on this occasion, NOT a §8.4 fire (the agentic condition never engaged, so agency cannot be what closed the gap — re-measure before any repositioning); G1-failed × E4-confirmed = vacuous, no consequence licensed; G1-failed × E1-confirmed = the improvement is not attributable to iteration — reported as an anomaly, not compensation |

**E2 wording clarification (finding 8d):** §8.4's "cliff" is the
sequence cliff — a cargo-side hidden-gap collapse alone is the
cliff-collapse event proper; the C4 gap collapsing alone is a
behavior-arrival result, reported under the same matrix row but not
labeled a §8.4 full fire.

## Budget (mandatory)

Ceiling **$40** (hard, live guard — charter W5 envelope); estimate
≈ $15–22 (30 runs × ≤ 3 model calls with conversation growth, of
which 12 haiku-generated; 30 judgements at 16k; records-based
per-call figures from W1–W4). MAX_CALLS 250 (live counter over every
API call incl. retries and revisions). Costs recorded in Results.

## Carried limitations (mandatory)

As W1, plus: k ≤ 2 revisions with structured failure feedback — real
agentic harnesses iterate more, with raw test output and tool use;
visible sets are small (3) and generic by design (with the
invalid_weight_low channel named in Design); c4 contrast opus-only,
n = 3 (coarse quantums disclosed); the sequence-cliff contrast runs
on the CargoQuote substrate, not the stored corpus families
(deviation disclosed in Design); the single-shot reference
asymmetries named under Baseline plumbing; judged medians exclude
non-compiling finals; single system per substrate;
capability-relative, dated.

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
