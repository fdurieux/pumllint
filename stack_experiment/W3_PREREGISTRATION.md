# Wave pre-registration — W3: carrier equivalence

*FROZEN 2026-08-10, before any scored run — the freeze is the commit
titled "Lab: W2–W4 frozen" carrying this file, the revised driver and
the revised carrier files. Provenance: draft 2cf7d65
(findings-before-verdicts); independent adversarial pass against it —
**11 findings: 3 major, 3 moderate, 5 minor, all adopted in this
revision** (the carrier files were revised per findings 1, 2 and 10
before freezing — preambles stripped to a bare title, the code-stub's
harness-matching exception phrasing and typing removed and the
Shipper restored, the controlled-English updatedQuote return edges
added). Owner go for W2–W4 given 2026-08-10 (recorded in
W2_PREREGISTRATION.md's preamble). Editing anything above Results
after a scored run invalidates the wave. Template:
PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base:** as W2's preamble — the W1 models, prompt
stack-bundle-v2, frozen suite/runner/overlays, shared definitions,
W1's carried generation-calibration, and the prompt-identity
mechanism (labels are kit-style: the carriers render as
`behavior/quote_flow.mmd` etc., never as experiment paths; `--dry-run`
proves each arm's prompt equals the reused W1-A2 prompt with only the
behavior-carrier section substituted — verified OK, all arms).

## Question and decision link (mandatory)

**Question:** At fixed information, does the carrier matter — the
same behavior artifact rendered as PlantUML sequence, Mermaid
sequence, structured YAML, controlled English, and a code-stub
skeleton — measured as executed correctness at the A2 rung
(brief + structure + behavior, no contract)?

**Decision links:** charter §7 W3 — confirmation licenses
**checkability** as the deciding carrier criterion (charter §2 C1's
condition); refutation is a headline either way and reopens the
carrier question on outcome evidence. Informs the Mermaid
sibling-stack record and Arc H's value case (both keep their own
triggers). The code-stub arm brushes the prose-pipeline never-build:
it is a lab measurement only — a favorable result changes claim
language, never that settlement, absent explicit re-litigation.
Pilot-facing: if deltas are small, "PlantUML vs Mermaid is a
checkability/tooling decision, not an outcome sacrifice — within
±10 pp at n = 6 pools, this system, dated" becomes the citable
sentence (bounds attached; adversarial finding 4).
**Charter-deviation note (finding 8):** the charter says "deltas
< 10 pp"; this wave tests |Δ| ≤ 10 pp inclusive (moot on the pooled
1/66 grid except at exactly 10.00, declared decidable below), and
narrows the licensing condition to E1 AND E2 both — a conscious,
conservative strengthening.

## Design (mandatory)

- **Conditions (4 new + 1 reused; A2 bundle with ONLY the behavior
  carrier swapped, pristine labels):** mermaid (quote_flow.mmd), yaml
  (quote_flow.yaml), controlled-english (quote_flow.md), code-stub
  (quote_flow_stub.py) — in stack_experiment/w3_carriers/, revised
  post-pass. **PlantUML arm = W1 A2, declared reuse:** pooled 0.439
  (29/66; opus 0.455 = 15/33, haiku 0.424 = 14/33). The A2 rung is
  chosen because no contract artifact is present to buffer the
  behavior carrier.
- **Information-equivalence audit (verified by the adversarial pass
  against the revised files):** every carrier carries the diagram's
  units — U1 flow order; U2 invalid → reject, stop; U3
  store-failure → error, nothing else runs (note 3); U4 accept-band
  actions; U5 review-band semantics (note 1); U6 refuse-band
  semantics incl. refusal IS notified (note 2); U7 outage semantics
  incl. priced-not-notified (note 5); U8 fire-and-forget (note 4);
  U9 thresholds symbolic, zero numeric bounds in any carrier; U10
  participants and roles — plus the diagram's call signatures (the
  charter's information-unit definition includes signatures; all
  carriers carry them). **Declared residuals (finding 10):** the
  U-grain is coarser than the diagram — stop-explicitness varies
  (yaml `terminal: true`, controlled-English "the flow stops", stub
  "respond … ." vs the PUML/Mermaid alt-structure convention), and
  the stub renders updateQuote's two arities as one signature with
  its docstring stating both call shapes. **Frozen-prompt frame
  (finding 3, disclosed limitation):** stack-bundle-v2 names "a
  PlantUML UML sequence diagram" among bundle kinds and never these
  carriers; the judge prompt frames diagrams as PlantUML, and for
  the code-stub arm Python sits inside SPECIFICATION. The prompt is
  frozen — this asymmetry is carried as a limitation, not patched.
- **Units and n:** 4 new arms × 2 generators × 3 runs = 24 scored
  runs; pooled n = 6 per arm. Driver, storage, guards as W2
  (results/W3/wave_main/); the freeze pins the four carrier files
  AND cargo_quote/behavior/quote_flow.puml (finding 9) — recorded by
  the driver's kit_hashes in every report.
- **Flow-set (pre-registered sensitive lens):** the five scenarios
  the A2 baseline passes in ≥ 5 of 6 runs (finding 7) —
  quoted_low_risk, refuse_high_risk, review_boundary_42,
  screening_down_hold, store_down_error; baseline flow-set mean
  **28/30 = 0.9333 exactly** (finding 5). The pooled rate compresses
  carrier effects (six contract-pinned scenarios sit near zero at A2
  by design); the flow-set is where a carrier difference must show.
- **Power note (finding 4, disclosed):** with W1's run-level
  SD ≈ 0.12, a 6-run pooled rate has SE ≈ 5 pp; the ±10 pp bar is
  ≈ 2 SE, checked eight times (4 carriers × E1 + E2), and the
  baseline is itself an n = 6 estimate whose sampling error shifts
  all four deltas coherently. A single-arm false "carrier matters"
  headline is a real risk; the matrix's refutation branch therefore
  quotes magnitudes and flags one-arm-only refutations as
  low-confidence.

## Oracles (mandatory)

As W1 (frozen suite, runner, overlays; judged as judgments;
gaps/orderings, never absolutes). Oracle-separation: N/A — no
tests-as-input condition in this wave.

## Calibration (mandatory, disclosed)

Inherited from W1 (identical configuration). W3-specific $0 checks,
run post-revision: quote_flow_stub.py compiles; quote_flow.yaml
parses; prompt-identity OK for all four arms; the equivalence audit
re-verified by the adversarial pass on the revised files. No scored
or degraded condition has been executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W3-E1 (equivalence, pooled):** every carrier's pooled |Δ| vs the
  PlantUML baseline (29/66) is ≤ 10 pp, inclusive.
- **W3-E2 (flow-set lens):** every carrier's flow-set mean is within
  |Δ| ≤ 10.00 pp of 28/30 exactly, inclusive (a 25/30 arm — Δ
  exactly 10.00 pp — confirms; finding 5's boundary declared).
- **W3-E3 (generator concordance; finding 6's rewording):** for each
  carrier: the opus and haiku deltas vs their own baselines are
  same-sign, or every opposite-signed delta is at most one
  per-generator slot (1/33 ≈ 3.03 pp) from zero.
- **W3-E4 (judged, secondary):** each carrier's judged-invention
  median per generator is within 2 of the W1-A2 medians (opus 6,
  haiku 5); quoted as judgment.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W3-E1 + E2 both | Carrier is not an outcome variable at fixed information (this system, this rung, these generators, n = 6 pools, dated): **checkability licensed** as the deciding carrier criterion (charter §2 C1 condition met); the bounded pilot sentence becomes citable; Mermaid sibling-stack record and Arc H value case informed — triggers unchanged | Carrier matters: headline either way, magnitudes quoted; a refutation carried by a single arm at ≤ 1.5× its SE is flagged low-confidence (power note); checkability demoted per charter C1; the carrier question reopens on outcome evidence; if code-stub leads, quoted lab-only, never against the prose-pipeline never-build |
| W3-E3 | Orderings portable across the capability tiers for carriers | Carrier preference is generator-specific: per-generator claim language (extends W1-E8a's partial §8.3 fire to the carrier axis) |
| W3-E4 | Invention insensitive to carrier at fixed information | The deviating carrier named; judged-only caveat attached to any equivalence claim |

## Budget (mandatory)

Ceiling **$12** (hard, live guard); estimate ≈ $4.5 (finding 11:
records-derived per-call actuals — opus A2 gen ≈ $0.15, haiku
≈ $0.015, judge ≈ $0.12 → 12 + 12 generations + 24 judgements ≈
$4.3–4.7); MAX_CALLS 120. Costs recorded in Results.

## Carried limitations (mandatory)

As W1, plus: one rung (A2), one behavior artifact; hand-authored
translations (the audit pins information presence, not idiomatic
fluency — translation quality is itself a carrier property); the
frozen prompt's PlantUML-typed frame (Design); equivalence power
bounded as disclosed; carrier results are capability-relative and
decay per model generation (charter §2 C1 — re-measure on generation
change).

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
