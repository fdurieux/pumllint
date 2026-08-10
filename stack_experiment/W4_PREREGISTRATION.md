# Wave pre-registration — W4: dose–response, the far side

*FROZEN 2026-08-10, before any scored run — the freeze is the commit
titled "Lab: W2–W4 frozen" carrying this file, the revised driver and
the revised far-side files. Provenance: draft 2cf7d65
(findings-before-verdicts); independent adversarial pass against it —
**11 findings: 3 major, 4 moderate, 3 minor + 1 observation, all
adopted in this revision** (two of the majors — the O2 dose misstated
at ~1.7× and the O2 FAQ entries restating notification rules — were
also self-caught by the author before the pass reported; disclosed
here). Kit revisions before freeze: the two rule-restating FAQ
entries replaced with neutral content; gen_O3.py docstring corrected
and a rounding-tie note added to O3 (regenerated). Owner go for
W2–W4 given 2026-08-10 (recorded in W2_PREREGISTRATION.md's
preamble). Editing anything above Results after a scored run
invalidates the wave. Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base:** as W2's preamble — the W1 models, prompt
stack-bundle-v2, frozen suite/runner/overlays, shared definitions,
W1's carried generation-calibration, and the prompt-identity
mechanism (added files render under neutral kit-plausible labels —
`operations-appendix.md`, `worked-examples.md` — never experiment
paths; `--dry-run` proves each arm's prompt equals the reused W1-A4
prompt plus/with only the declared change — verified OK, all arms).

**Design revisit note (mandated by W1's E1 failure and E8a):** W1
showed the largest lever on this system is the contract, not
behavior, and that the generators disagree on ordering. W4 therefore
(a) builds every over-specification arm on the FULL A4 stack, (b)
locates knees per generator AND pooled with the per-generator
readings pre-registered below (finding 5), and (c) quotes no
single-lever language.

## Question and decision link (mandatory)

**Question:** Past the full stack, does more text help, do nothing,
or dilute — accurate redundant restatement (O1), irrelevant context
(O2), exhaustive accurate enumeration (O3) — and where is the knee of
the dose–response curve?

**Decision links:** completes charter §2 E1's correction with data
(the far side measured, never assumed monotone); charter §8.2 is the
named falsifier (pre-committed branch below); §8.5 is the abort
criterion, operationalized below (finding 7); W2-E5's locality
expectation (scheduled to run before W4 in this program — finding 9)
is the conflict-side sibling: W4's doses are conflict-free by
construction.

## Design (mandatory)

- **Conditions (3; all built on pristine A4; doses re-counted after
  the FAQ revision — finding 2 corrected):**

  | Arm | Dose (chars vs A4 = 18 052) | Content |
  |---|---|---|
  | O1-redundant | 20 281 ≈ **1.12×** | every DT number restated accurately in prose (value-by-value verified by the pass: zero deviations), in-sync duplication without staleness |
  | O2-irrelevant | 26 159 ≈ **1.45×** | plausible, on-domain, quotation-irrelevant operational material |
  | O3-enumeration | 21 005 ≈ **1.16×** | exhaustive accurate enumeration derived from DT by script (w4_farside/gen_O3.py; regenerates byte-identically; three pinned asserts; float tie-semantics note in the file header) |

  **O2's verified property (finding 4's correction — the draft's
  "only numbers belong to the air product" was false as written):**
  no number or numeric rule in O2 bears on the quotation decision or
  collides with any DT value (3/19400/25/7150/50/83000/41/42/66/67/
  0.87/1.13/1244/316/4912/1.19) or any W2 stale value (45, 0.85,
  1866.00); the only tariff-like rule numbers belong to the
  explicitly-labeled air product; the remaining figures (fleet
  counts, SLA classes, retention periods, dock doors) are
  operational trivia with no quotation-rule content. The two former
  FAQ entries that accurately restated notification semantics are
  replaced (finding 3); the one remaining notification mention is
  brand-template styling, not a decision rule.
  **Below-knee side: W1 A0..A4, declared reuse:** pooled
  0.136 / 0.121 / 0.439 / 0.818 / 0.945; per-generator opus A3 1.000
  → A4 0.964, haiku A3 0.636 → A4 0.927.
- **Units and n:** 3 arms × 2 generators × 3 runs = 18 scored runs;
  pooled n = 6 per arm vs the n = 10 A4 baseline pool — mixed-n
  comparisons use W1's frozen rate-based definitions; where a tie
  quantum is needed the larger pool quantum applies (1.5 pp pooled).
- **Power note (finding 7, disclosed):** with W1's run-level
  SD ≈ 0.12, a 6-run-pool vs 10-run-pool gap has SE ≈ 6 pp; the 9 pp
  harm bar is ≈ 1.5 SE — weaker than W1-E5's disclosed 1.7 SE. A
  within-quantum null is therefore reported as underpowered, never
  as proof of harmlessness beyond its dose.
- **Token axis:** arm mean input tokens minus W1's A0 mean, per
  generator (same accounting as W1; O-bundles are strict supersets
  of A4, so the axis ordering past A4 is guaranteed).

## Oracles (mandatory)

As W1 (frozen suite, runner, overlays; judged as judgments;
gaps/orderings, never absolutes).
**Oracle-separation declaration (finding 8):** all arms carry the
pristine acceptance.feature — W1's declared overlap carries
unchanged. O3 additionally enumerates the DT-V just-invalid values
(2 / 24 / 49 / 19401 / 7151 / 83001): weight 2 is
invalid_weight_low's exact probe — that scenario is already
leakage-exposed (LEAK2, via G2) and its class is unchanged; the other
bound values are adjacent to (not identical with)
invalid_value_over's probe (90 000). O3's banding rows and the
8652.49 cell are already carried by the DT in every arm — no new
revelation. The VALUE9/LEAK2 partition therefore carries unchanged,
with O3's enumeration noted as deepening the invalid-bounds
adjacency.

## Calibration (mandatory, disclosed)

Inherited from W1 (identical configuration; O-arms enlarge prompts
1.12–1.45×, well inside context and the 12000-token generation
budget). W4-specific $0 checks, run post-revision: O3 regenerated
byte-identically by gen_O3.py with the three asserts (8652.49 —
DT-P's worked example; 3186.00 — suite-graded; 2121.40 — the G1
input example, NOT suite-graded; finding 10's docstring correction
applied); O1 verified value-by-value against DT (zero deviations);
O2 re-hunted for rule collisions after the FAQ revision (none);
prompt-identity OK for all three arms. No scored or degraded
condition has been executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W4-E1 (plateau; finding 1's re-statement):** no O-arm's pooled
  rate exceeds the A4 baseline (0.945) by more than one tie quantum
  (1.5 pp). **Ceiling disclosure:** at this baseline the maximum
  arithmetically possible exceedance is +5.5 pp pooled (+3.6 opus /
  +7.3 haiku), so a ≥ 9 pp gain is unreachable — this bar detects
  ANY gain, and "no more-is-better tail" is claimed only up to the
  ceiling's limit; gain detection beyond that is out of this wave's
  reach by construction.
- **W4-E2 (dilution):** directional: O2 (irrelevant context) is the
  likeliest diluter. Bar: any O-arm ≤ baseline − 9 pp → far-side
  harm measured. If ALL three O-arms sit within ±9 pp →
  **pre-committed §8.2 branch:** at these doses (≤ 1.45×) the far
  side is outcome-harmless and "minimum sufficiency" retreats to a
  cost-only argument — the charter wording is updated accordingly,
  with the dose limitation stated and the power note carried
  (underpowered-null wording, not proof of harmlessness).
- **W4-E3 (knee; finding 5's re-statement — the vacuous clause is
  dropped):** live content: no O-increment beyond A4 exceeds one
  tie quantum, AND the per-generator knees land as pre-registered
  from W1's frozen data — **pooled knee at A4; opus knee at A3**
  (opus A3 = 1.000, A3→A4 = −3.6 pp); **haiku knee at A4** (haiku
  A3→A4 = +29.1 pp). Any O-arm materially breaking its generator's
  pre-registered knee (beyond the quantum) refutes E3 for that
  generator and the combined-curve reading says so per-generator
  (W1-E8a discipline).
- **W4-E4 (judged, exploratory; finding 6's floor disclosure):** no
  O-arm's judged-invention median per generator is lower than A4's
  by more than 2. **A4 medians: opus 3, haiku 1 — the bar binds
  opus only** (a count median cannot go below 0, so haiku cannot
  fail it; any haiku movement is reported descriptively). An opus
  O-arm median of 0 breaks it (likeliest O3) → recorded as a
  judged-only finding for exhaustive enumeration; no executed claim
  without a dedicated arm.
- **§8.5 abort, operationalized (finding 7):** the knee claim is
  aborted — recorded as not-locatable, no hand-wave — iff the two
  generators' knee identities disagree with their pre-registered
  values AND the pooled O-arm ordering is not stable under
  leave-one-run-out re-pooling.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W4-E1 | The plateau holds past A4 at these doses (up to the disclosed ceiling) | An O-arm shows a detectable gain (> 1 quantum): recorded as a far-side surprise; if O3, it feeds the tests-as-input/enumeration caveat on the charter §6 row (dated; no build) |
| W4-E2 | Dilution measured: E1's correction completed with data — over-specification is a cost AND an outcome risk; the dormant-by-default / rule-count-creep argument (charter §2 E1) gains its measured citation | Far side harmless at these doses: §8.2 branch applied as pre-committed — cost-only "minimum" at ≤ 1.45× doses, charter reworded with dose + power limitation; higher doses recorded as an open follow-up, not queued |
| W4-E3 | The knee readings hold per generator and pooled — the charter's dose–response answer gains its far side, quoted per-generator | A generator's knee breaks its pre-registered value: that generator's curve is re-read and reported per-generator; if the §8.5 abort fires, "knee not locatable at feasible n" is recorded and the claim stops there |
| W4-E4 | Invention insensitive to dose (opus-side claim; haiku descriptive) | An opus O-arm cuts invention to 0 (likeliest O3): judged-only finding for exhaustive enumeration, recorded with the floor disclosure |

## Budget (mandatory)

Ceiling **$12** (hard, live guard); estimate ≈ $4–6.5 (records-based
actuals scale to ≈ $4 central at 1.12–1.45× input sizes; the $6.5
figure is kept as the conservative envelope — adversarial finding on
budget attribution adopted from the W2 pass's sibling). MAX_CALLS 120
(live). Costs recorded in Results.

## Carried limitations (mandatory)

As W1, plus: three far-side doses only, all ≤ 1.45× A4 chars —
industrial-scale over-specification (10×+) is out of this budget's
reach and any harmless-verdict is dose-bounded AND power-bounded (the
disclosed ≈ 1.5 SE bar); O2's irrelevance is hand-curated
(adversarially chosen irrelevance is a different, harder condition);
doses are conflict-free by construction (staleness lives in W2); E1
gain detection is ceiling-limited as disclosed.

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
