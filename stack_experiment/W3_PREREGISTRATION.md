# Wave pre-registration — W3: carrier equivalence

*DRAFT for verification, 2026-08-10 — NOT yet frozen. Freeze = the
commit carrying this file (verified), the driver
(tools/stack_variants.py) and the carrier-file hashes, after the
adversarial pass is adopted; owner gave the W2–W4 go 2026-08-10.
Once a scored run exists, editing anything above Results invalidates
the wave. Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base:** as W2's preamble — the W1 models, prompt
stack-bundle-v2, frozen suite/runner/overlays, shared definitions,
and W1's carried generation-calibration, all by reference to
W1_PREREGISTRATION.md.

## Question and decision link (mandatory)

**Question:** At fixed information, does the carrier matter — the
same behavior artifact rendered as PlantUML sequence, Mermaid
sequence, structured YAML, controlled English, and a code-stub
skeleton — measured as executed correctness at the A2 rung
(brief + structure + behavior, no contract)?

**Decision links:** charter §7 W3 verbatim — confirmation licenses
**checkability** as the deciding carrier criterion (charter §2 C1's
condition); refutation is a headline either way and reopens the
carrier question on outcome evidence. Informs the Mermaid
sibling-stack record and Arc H's value case (both keep their own
triggers). The code-stub arm brushes the prose-pipeline never-build:
it is a lab measurement only — a favorable result changes claim
language, never that settlement, absent explicit re-litigation
(charter wording, restated here so the scope travels with the wave).
Pilot-facing: if deltas are small, "PlantUML vs Mermaid is a
checkability/tooling decision, not an outcome sacrifice" becomes a
dated, citable sentence for the census conversation.

## Design (mandatory)

- **Conditions (4 new + 1 reused; A2 bundle with ONLY the behavior
  carrier swapped):** mermaid (quote_flow.mmd), yaml
  (quote_flow.yaml), controlled-english (quote_flow.md), code-stub
  (quote_flow_stub.py) — all in stack_experiment/w3_carriers/.
  **PlantUML arm = W1 A2, declared reuse** (identical bundle, prompt,
  models, suite): pooled 0.439 (opus 0.455, haiku 0.424); its
  scenario profile is the frozen baseline. The A2 rung is chosen
  because no contract artifact is present to buffer the behavior
  carrier (W1's declared spec.md flow overlap does not exist at A2 —
  the carrier is load-bearing).
- **Information-equivalence audit (freeze prerequisite; the
  adversarial pass verifies it against the four files):** every
  carrier carries exactly the diagram's information units — U1 flow
  order (validate → store → screen → band → price → update → notify →
  respond); U2 invalid → reject, stop; U3 store-failure → error,
  nothing else runs (note 3); U4 accept-band: price, store, notify
  quote document, `quoted`; U5 review-band: no price, no
  notification, `review_hold` (note 1); U6 refuse-band: no price,
  refusal IS notified, `refused_screening` (note 2); U7 outage:
  price anyway, `held_unscreened`, not notified (note 5); U8
  notification fire-and-forget (note 4); U9 thresholds symbolic
  (ACCEPT_MAX / REVIEW_MIN / REVIEW_MAX / REFUSE_MIN; numbers only
  in DT); U10 participants and their roles. No carrier adds
  information the diagram lacks.
- **Units and n:** 4 new arms × 2 generators × 3 runs = 24 scored
  runs; pooled n = 6 per arm; baseline reused. Driver, storage,
  guards: as W2 (results/W3/wave_main/; carrier-file sha256 pinned
  at freeze).
- **Flow-set (pre-registered sensitive lens):** the five scenarios
  the A2 baseline actually passes — quoted_low_risk,
  refuse_high_risk, review_boundary_42, screening_down_hold,
  store_down_error; baseline flow-set mean 0.933. The pooled rate
  compresses carrier effects because six contract-pinned scenarios
  sit near zero at A2 by design; the flow-set is where a carrier
  difference must show.

## Oracles (mandatory)

As W1 (frozen suite, runner, overlays; judged as judgments;
gaps/orderings, never absolutes).

## Calibration (mandatory, disclosed)

Inherited from W1 (identical configuration). W3-specific $0 checks,
already run: quote_flow_stub.py compiles (py_compile); quote_flow.yaml
parses (yaml.safe_load); the Mermaid and controlled-English renderings
have no mechanical validator here — the equivalence audit above is
their check, verified by the adversarial pass before freeze. No scored
or degraded condition has been executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W3-E1 (charter's pre-registered bar):** every carrier's pooled
  delta vs the PlantUML baseline (0.439) lies within ±10 pp.
- **W3-E2 (flow-set lens):** every carrier's flow-set mean lies
  within 10 pp of the baseline flow-set mean (0.933).
- **W3-E3 (generator concordance):** per-generator deltas vs that
  generator's PlantUML baseline are same-sign or within one
  per-generator quantum (3.0 pp) for each carrier; reported
  per-generator regardless (W1-E8a consequence).
- **W3-E4 (judged, secondary):** each carrier's judged-invention
  median per generator is within 2 of the W1-A2 medians (opus 6,
  haiku 5); quoted as judgment.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W3-E1 + E2 both | Carrier is not an outcome variable at fixed information (this system, this rung, these generators, dated): **checkability licensed** as the deciding carrier criterion (charter §2 C1 condition met); the pilot sentence ("PlantUML vs Mermaid is a tooling decision, not an outcome sacrifice") becomes citable, dated; Mermaid sibling-stack record and Arc H value case informed — their triggers unchanged | Carrier matters: headline either way. The leading and trailing carriers are named with their deltas; checkability is demoted to one criterion among several (charter C1's demotion branch); the carrier question reopens on outcome evidence; if code-stub leads, the result is quoted as lab-only and the prose-pipeline never-build stands absent explicit re-litigation |
| W3-E3 | Orderings portable across the capability tiers for carriers | Carrier preference is generator-specific: per-generator claim language (extends W1-E8a's partial §8.3 fire to the carrier axis) |
| W3-E4 | Invention insensitive to carrier at fixed information | The deviating carrier named; judged-only caveat attached to any equivalence claim |

## Budget (mandatory)

Ceiling **$12** (hard, live guard); estimate ≈ $4 (24 A2-size
generations — ≈6 k-char bundles — of which 12 haiku + 24 judgements);
MAX_CALLS 120. Costs recorded in Results.

## Carried limitations (mandatory)

As W1, plus: one rung (A2), one behavior artifact, hand-authored
translations (translation quality is itself a carrier property —
the audit pins information presence, not idiomatic fluency);
carrier results are capability-relative and decay per model
generation (charter §2 C1 — re-measure on generation change).

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
