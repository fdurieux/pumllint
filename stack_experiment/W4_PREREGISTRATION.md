# Wave pre-registration — W4: dose–response, the far side

*DRAFT for verification, 2026-08-10 — NOT yet frozen. Freeze = the
commit carrying this file (verified), the driver
(tools/stack_variants.py) and the far-side file hashes, after the
adversarial pass is adopted; owner gave the W2–W4 go 2026-08-10.
Once a scored run exists, editing anything above Results invalidates
the wave. Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base:** as W2's preamble — the W1 models, prompt
stack-bundle-v2, frozen suite/runner/overlays, shared definitions,
and W1's carried generation-calibration, by reference to
W1_PREREGISTRATION.md.

**Design revisit note (mandated by W1's E1 failure and E8a):** W1
showed the largest lever on this system is the contract, not
behavior, and that the two generators disagree on ordering. This W4
therefore (a) builds every over-specification arm on the FULL A4
stack — the measured plateau start — rather than on a behavior-max
rung, (b) locates the knee on the combined W1 + W4 token-indexed
curve per generator AND pooled, and (c) quotes no
single-lever language.

## Question and decision link (mandatory)

**Question:** Past the full stack, does more text help, do nothing,
or dilute — accurate redundant restatement (O1), irrelevant context
(O2), exhaustive accurate enumeration (O3) — and where is the knee of
the dose–response curve?

**Decision links:** completes charter §2 E1's correction with data
(the far side measured, never assumed monotone); charter §8.2 is the
named falsifier ("redundancy is harmless or positive" → "minimum"
retreats to a cost-only argument — pre-committed below); §8.5 is the
abort criterion (knee not locatable at feasible n); W2-E5's locality
result is the conflict-side sibling (W4's doses are conflict-free by
construction — staleness is W2's variable, kept out of W4).

## Design (mandatory)

- **Conditions (3; all built on pristine A4):**

  | Arm | Dose | Content |
  |---|---|---|
  | O1-redundant | spec.md → O1_spec.md (~1.12× A4 chars) | every DT number restated accurately in prose, in-sync duplication (the kit's never-restate rule deliberately broken WITHOUT staleness) |
  | O2-irrelevant | A4 + O2_appendix.md (~1.7× A4 chars) | plausible, on-domain, irrelevant operational material; zero rule collisions (verified: the only numbers belong to a clearly-labeled different product) |
  | O3-enumeration | A4 + O3_worked_examples.md (~1.16× A4 chars) | exhaustive accurate enumeration derived from DT by script (w4_farside/gen_O3.py — correct by construction, three pinned asserts) |

  **Below-knee side: W1 A0..A4, declared reuse** (identical
  configuration): pooled 0.136 / 0.121 / 0.439 / 0.818 / 0.945.
  Baseline for all far-side deltas: W1 A4 (pooled 0.945; opus 0.964,
  haiku 0.927).
- **Units and n:** 3 arms × 2 generators × 3 runs = 18 scored runs;
  pooled n = 6 per arm. Driver, storage, guards as W2
  (results/W4/wave_main/; far-side file sha256 pinned at freeze).
- **Token axis:** arm mean input tokens (API-reported) minus W1's A0
  mean, per generator — same accounting as W1, so the combined curve
  is one axis.

## Oracles (mandatory)

As W1 (frozen suite, runner, overlays; judged as judgments;
gaps/orderings, never absolutes).

## Calibration (mandatory, disclosed)

Inherited from W1 (identical configuration; O-arms enlarge prompts
~1.1–1.7×, well inside the models' context and the 12000-token
generation budget). W4-specific $0 checks, already run: O3 derived by
script with pinned asserts (8652.49 / 3186.00 / 2121.40); O1
restatement checked value-by-value against DT-V/DT-S/DT-P; O2
checked for rule collisions (none — the only numeric rules named
belong to the explicitly-different air product). No scored or
degraded condition has been executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W4-E1 (plateau):** no O-arm exceeds the W1-A4 pooled baseline by
  ≥ +9 pp.
- **W4-E2 (dilution):** directional: O2 (irrelevant context) is the
  likeliest diluter. Bar: any O-arm ≤ baseline − 9 pp → far-side
  harm measured. If ALL three O-arms sit within ±9 pp →
  **pre-committed §8.2 branch:** at these doses the far side is
  outcome-harmless and "minimum sufficiency" retreats to a
  cost-only argument — the charter wording is updated accordingly,
  with the dose limitation (≤ 1.7×) stated.
- **W4-E3 (knee):** on the combined token-indexed pooled curve
  (W1 A0→A4 + O-arms), the last increment ≥ 9 pp is A3→A4 — i.e.,
  **the knee sits at A4** and nothing beyond it is material.
  Refuted if any O-increment ≥ +9 pp (then W4-E1 also fails) or if
  A3→A4 no longer stands as material in the combined view.
- **W4-E4 (judged, exploratory):** no O-arm's judged-invention
  median per generator is LOWER than A4's by more than 2 (more text
  is not expected to cut invention; O3's worked examples are the
  live question — an O3 improvement is a genuine finding for the
  enumeration idea, quoted as judgment).

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W4-E1 | The plateau holds past A4: no more-is-better tail at these doses | An O-arm materially beats the full stack: §8.2-adjacent surprise — the arm named; if O3, the enumeration result feeds the tests-as-input row (dated caveat, no build) |
| W4-E2 | Dilution measured: E1's correction completed with data — over-specification is a cost AND an outcome risk; the dormant-by-default / rule-count-creep argument (charter §2 E1) gains its measured citation | Far side harmless at these doses: §8.2 branch applied as pre-committed — "minimum" argued on cost alone at ≤1.7× doses, charter reworded, dose limitation stated; higher doses recorded as an open follow-up, not queued |
| W4-E3 | The knee is at A4 and the W1+W4 curve carries it per generator and pooled — the charter's dose–response answer gains its far side | Knee unstable or displaced: if noise swamps the ±9 pp calls, §8.5's abort criterion applies — record and stop, no hand-wave; if displaced by a material O-gain, the knee moves and the consolidated document says so |
| W4-E4 | Invention insensitive to dose | An O-arm cuts invention materially (likeliest O3): recorded as a judged-only finding for exhaustive enumeration; no executed claim without a dedicated arm |

## Budget (mandatory)

Ceiling **$12** (hard, live guard); estimate ≈ $6.5 (18 generations
at 1.1–1.7× A4 prompt size, of which 9 haiku + 18 judgements at 16k
over the enlarged specs); MAX_CALLS 120. Costs recorded in Results.

## Carried limitations (mandatory)

As W1, plus: three far-side doses only, all ≤ 1.7× A4 chars —
industrial-scale over-specification (10×+) is out of this budget's
reach and any harmless-verdict is dose-bounded; O2's irrelevance is
hand-curated (adversarially chosen irrelevance is a different, harder
condition); doses are conflict-free by construction (staleness lives
in W2).

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
