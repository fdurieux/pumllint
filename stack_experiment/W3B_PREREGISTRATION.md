# Wave pre-registration — W3b: carrier × prompt-frame

*DRAFT, 2026-08-11, pre-verification — findings-before-verdicts. NOT
frozen, may not run. Charter §10 sequence pending in full:
independent adversarial pass against this draft → freeze commit
(pinning the carrier-file, driver and frame-string hashes) → owner
go → scored run. Lineage: W3's frozen record carries the
prompt-frame asymmetry as its disclosed limitation (finding 3) and
its matrix's refutation branch reopened the carrier question on
outcome evidence; the candidate is recorded in ROADMAP § Settled
questions and docs/external-review-evaluation.md § wave candidates as
"carrier × prompt-frame factorial separating intrinsic carrier effect
from prompt-carrier alignment". Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base (by import, unchanged):** the W1 models
(`claude-opus-4-8`, `claude-haiku-4-5-20251001`; judge
`claude-sonnet-5` @16000, C4-wave schema and rubric), the frozen
suite (sha256 `113ab6ac…9b501`), runner (`f6cc907e…2fe7c88`) and
OVERLAYS, W1's shared definitions (materiality ≥ 9 pp pooled;
rate-based comparisons; tie rule with per-pool quantums), W3's four
frozen carrier translations in stack_experiment/w3_carriers/
(REUSED BYTE-IDENTICAL — no edits; hashes pinned at freeze) and W3's
flow-set lens. Kit-style labels and the prompt-identity mechanism as
the W2–W4 driver.

## Question and decision link (mandatory)

**Question:** How much of W3's carrier ordering (PlantUML ≥
code-stub ≈ Mermaid > controlled English > YAML) is intrinsic to the
carriers, and how much was carried by the frozen prompt's
PlantUML-typed frame — measured by crossing the five carriers with
the prompt frame (stored / neutral / carrier-native) at fixed
information?

**Decision links:**

- **W3's matrix, refutation branch:** "the carrier question reopens
  on outcome evidence" — this wave is that reopening, on the one
  axis W3's own pre-registration disclosed as untested (the
  frozen-prompt frame, finding 3).
- **W3's standing headline gains or loses its frame scoping:** if
  the ordering survives a neutral frame, "carrier matters" becomes
  frame-free (a strengthening); if a carrier's deficit closes under
  neutral or native framing, W3's claim for that carrier gains a
  "under a PlantUML-framed harness" scoping — a material narrowing,
  published with full prominence.
- **The opus-YAML non-compile mechanism** (the W1–W4 program's only
  non-compiles, 3/3): frame-induced misparse vs carrier-intrinsic —
  decided by E3.
- **Pilot-facing sentence:** the honest dated Mermaid sentence
  ("−9.1 pp pooled / −20 pp flow-sensitive in this lab's single
  measurement") either hardens (intrinsic) or gains the frame
  scoping.
- **Charter §2 C1 / checkability:** already demoted by W3 on outcome
  evidence; this wave cannot re-promote it (demotion was
  outcome-based), but a frame-carried result would shift WHERE the
  outcome evidence points (harness alignment, not carrier syntax).
- Mermaid sibling-stack record and Arc H keep their own triggers,
  informed either way.

## Design (mandatory)

- **The factorial (14 unique cells; information fixed, carrier ×
  frame varied):** five carriers — PlantUML (kit
  behavior/quote_flow.puml) and W3's four frozen translations
  (mermaid `.mmd`, yaml `.yaml`, controlled-english `.md`, code-stub
  `_stub.py`) — crossed with three prompt frames. For PlantUML,
  native ≡ stored (identical string), so the design is 5 × 2 + 4 × 1:

  | Frame | Cells | The behavior-kind phrase in the prompt |
  |---|---|---|
  | F-stored | all 5 carriers | "a PlantUML UML sequence diagram" (stack-bundle-v2 verbatim — W3's condition; the misaligned frame for the four alternatives) |
  | F-neutral | all 5 carriers | "a behavior interaction specification" (format-silent) |
  | F-native | 4 alternatives | the carrier's own name: "a Mermaid sequence diagram" / "a structured YAML behavior specification" / "a controlled-English behavior specification" / "a Python skeleton of the behavior (function stubs with docstrings)" |

  **Frame construction rule (the whole treatment):** each frame is
  stack-bundle-v2 with EXACTLY ONE substitution — the behavior-kind
  phrase above. Every other byte of the generation prompt, the
  artifact order, the kit-style labels and the entry contract are
  identical across all 14 cells; the frames' exact strings are
  frozen in this section and diff-proved pre-freeze. The judge
  prompt is NOT varied (one fixed judge frame across all cells, for
  judge comparability); its PlantUML typing is carried as a
  disclosed limitation exactly as in W3.

- **Everything runs in-wave (the W5/W1b cross-occasion lesson):** all
  14 cells are freshly scored; W3's stored arms and W1-A2 serve as
  cross-occasion references only (stored: PlantUML 0.439 pooled /
  0.933 flow-set; code-stub 0.379/0.767; mermaid 0.348/0.733;
  controlled-english 0.288/0.600; yaml 0.136/0.267; opus-yaml 0/3
  compiling). No stored number enters any expectation's arithmetic.

- **Units and n:** 14 cells × 2 generators × 3 runs = **84 scored
  runs**, pooled n = 6 per cell. Quantums, stated up front: one slot
  in one run moves a pooled cell rate by 1.5 pp (per-generator
  3.0 pp); the flow-set (30 slots per cell) moves 3.33 pp per slot
  and 20 pp per consistently-flipped scenario — flow-set contrasts
  are coarse and the verdicts below use the W3 convention
  (|Δ| ≤ 10.00 pp inclusive = equivalent). Power note, disclosed:
  at W1's run-level SD ≈ 0.12, a 6-vs-6 pooled gap has SE ≈ 5 pp
  and a flow-set gap ≈ 7 pp; E1 is checked four times and E2 four
  times — single-cell surprises at ≤ 1.5× SE are flagged
  low-confidence in the narration, per W3's power discipline.

- **Flow-set lens (reused from W3, frozen):** quoted_low_risk,
  refuse_high_risk, review_boundary_42, screening_down_hold,
  store_down_error — the five scenarios where a behavior-carrier
  difference must show; pooled rates compress carrier effects
  because the six contract-pinned scenarios sit near zero at A2.

- **Models, exact IDs:** as the shared frozen base; declared
  narrowing: one vendor, as W1–W5; a Gemini leg would be its own
  pre-registered amendment (charter §10), never a silent extension.

- **Driver (disclosed harness work, freeze prerequisite):** a new
  module `tools/stack_w3b.py` importing the frozen machinery
  (generation shim, suite, runner/overlay path, judge, spend guard —
  the W1b placement precedent: no frozen file edited on disk), with:
  the 14-cell job plan; the three frame strings as module constants;
  a results root `stack_experiment/results/W3B/` (the $ ceiling
  scoped to this wave alone); and a W3b analysis block (per-cell
  pooled/per-generator/flow-set rates; per-carrier frame deltas
  native−stored and neutral−stored; per-frame carrier orderings;
  compile counts per cell; judged medians; every E1–E6/G1 input).
  **Pre-freeze equivalence obligations:** (1) each F-stored cell's
  assembled prompt is byte-identical to the corresponding W3 stored
  arm's prompt (and the puml-stored cell's to W1-A2's); (2) each
  F-neutral/F-native prompt differs from its F-stored sibling by
  exactly the one declared phrase (mechanical diff, printed); (3) an
  expectation-inputs dry-run emits every E/G input (the X-R1
  lesson). Driver sha256 pinned at freeze.

- **Oracle-separation declaration:** no arm includes tests-as-input;
  trivially disjoint.

## Oracles (mandatory)

As W3: frozen suite + runner + overlays, full and semantic-only
reported; flow-set reported per cell. Judged secondary (invention
medians, one fixed judge prompt across cells, judgments never merged;
non-compiling artifacts never judged, judged-n reported per cell —
the W5/W1b convention). Committed outputs: the carrier × frame rate
matrix (pooled / per-generator / flow-set), the per-carrier
alignment-delta table, per-cell compile counts, and the E-inputs.

## Calibration (mandatory, disclosed)

Inherited: W1's generation-calibration (identical pipeline) and W3's
carrier files as adversarially revised and frozen. W3b-specific $0
checks before freeze: smoke_test.py re-run; driver dry-run printing
all 14 cell inventories and the three frame strings; the three
equivalence/diff obligations under Design. **No scored, degraded or
partial condition may be executed pre-freeze — every F-neutral and
F-native cell is a new condition and none has ever been run.**

## Pre-registered expectations (mandatory)

- **W3b-E1 (the intrinsic-ordering test — the wave's headline):**
  under F-neutral, every alternative carrier's flow-set deficit vs
  the in-wave PlantUML-neutral cell is > 10.00 pp (strictly outside
  W3's inclusive equivalence bar), checked per carrier (four
  verdicts E1-stub / E1-mermaid / E1-english / E1-yaml).
- **W3b-E2 (alignment is non-negative and material where the frame
  plausibly hurt):** for each alternative carrier, pooled(F-native)
  − pooled(F-stored) ≥ −1.5 pp (one pooled quantum below zero
  tolerated), AND for yaml specifically the alignment gain is
  ≥ +9 pp pooled.
- **W3b-E3 (the non-compile mechanism):** opus-yaml compiles in ≥ 2
  of 3 runs under F-native AND under F-neutral (stored: 0/3). Both
  arms clearing the bar = the W3 non-compiles were frame-induced;
  neither clearing = carrier-intrinsic; split = mixed, reported
  per-frame.
- **W3b-E4 (the baseline's own frame-sensitivity):**
  |pooled(puml-neutral) − pooled(puml-stored)| ≤ 9 pp — PlantUML's
  lead is not an artifact of its aligned frame.
- **W3b-E5 (generator concordance on the alignment axis — §8.3
  discipline):** for each alternative carrier, the opus and haiku
  alignment deltas (native − stored) are same-sign, or every
  opposite-signed delta is within one per-generator slot (3.0 pp)
  of zero.
- **W3b-E6 (judged, secondary):** for every evaluable cell, the
  judged-invention median per generator is within 2 of the same
  carrier's W3 stored median (evaluability per the judged-n
  conventions; cells with < 2 judgeable runs reported not-evaluable,
  never imputed).

**Validity guards (pre-committed, not expectations):**

- **G1 (anchor sanity — run-note rule, not a blocker):** the in-wave
  puml-stored cell lands within ±15 pp pooled of W1-A2's stored
  0.439. Outside that band, a cross-occasion anomaly is recorded
  prominently; every contrast in E1–E5 remains in-wave-valid by
  construction (all cells same-occasion).
- **G2 (floor):** each generator's in-wave puml-stored pool > 0.15;
  below, suspect harness defect — halt, investigate, disclose; any
  fix forces a conscious re-freeze.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| E1 (×4) | The carrier effect is intrinsic for that carrier: W3's headline sheds the frame caveat for it, dated; the pilot Mermaid sentence hardens ("under aligned, neutral and misaligned frames alike") | That carrier's W3 deficit was frame-carried in material part: W3's claim for it gains the "PlantUML-framed harness" scoping — a published narrowing; the pilot sentence carries it; harness-alignment (naming the artifact's actual format in the prompt) is recorded as a measured lever |
| E2 | Alignment never hurts and materially helps the far carrier: prompt-carrier alignment recorded as cheap hygiene for any non-PlantUML corpus | A negative alignment effect beyond quantum anywhere is a surprise — recorded, per-generator, with the affected carrier named; no hygiene claim |
| E3 | Both-clear: the program's only non-compiles were harness-frame artifacts — the YAML carrier's executed penalty is re-stated net of them; opus-yaml judged cells become evaluable for the first time | Neither-clear: non-compiles are carrier-intrinsic for opus — the W3 wording stands as written. Split: reported per-frame, no single-mechanism claim |
| E4 | The baseline is frame-robust; every W3-relative delta stands on a stable reference | PlantUML's lead is partly self-frame: every W3 delta gains the note, and E1's verdicts are read against the neutral baseline only (pre-committed here) |
| E5 | Alignment claims portable across tiers ("ordering, not magnitude") | Per-generator alignment language (extends the §8.3 partial fire to the frame axis) |
| E6 | Invention insensitive to frame at fixed carrier | The deviating cell named; judged-only caveat attached to any frame claim |

## Budget (mandatory)

Ceiling **$30** (hard, live guard, scoped to results/W3B); estimate
**$14–20**: 84 generations (42 opus ≈ $0.15, 42 haiku ≈ $0.015) +
84 judgements ≈ $0.12, per the W3 records-derived per-call actuals
(W3 actual: $4.21 for 24 cycles) ≈ $17 central. **MAX_CALLS 250**
(plan ≈ 168 incl. judges; retries counted). Costs recorded in
Results.

## Carried limitations (mandatory)

As W3, verbatim where applicable: one rung (A2), one behavior
artifact, hand-authored translations reused frozen (the audit pinned
information presence, not idiomatic fluency — translation quality
remains a carrier property this wave cannot separate); the judge
prompt keeps its PlantUML typing in every cell (frame treatment is
generation-side only — judged numbers carry that asymmetry); frames
vary a single phrase, not the full scaffold (deeper prompt-carrier
co-adaptation — carrier-specific rules, examples — is unmeasured and
out of scope); flow-set quantums coarse as disclosed; single vendor
pair; n = 3 per generator per cell; capability-relative, dated —
carrier and frame results re-measure per model generation (charter
§2 C1).

## Results

*(Empty by design: draft, pre-verification. Written strictly after
the freeze and the owner's go, run notes before verdicts, per the
template.)*
