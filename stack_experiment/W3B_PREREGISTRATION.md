# Wave pre-registration — W3b: carrier × prompt-frame

*FROZEN 2026-08-11, before any scored run — the freeze is the commit
titled "Lab: W3b frozen" carrying this preamble; nothing above
Results changed at freeze. Provenance: draft 56fb30e
(findings-before-verdicts) → independent adversarial pass — **14
findings: 6 major, 8 minor, all adopted** (inline "(adversarial
finding N)" annotations) → verified revision 6b8a995 → driver +
pre-freeze checks f521048 (**68/68 green**; record:
stack_experiment/results/W3B/prefreeze_checks/report.json). Pins at
freeze: driver tools/stack_w3b.py sha256
`c528378079bd938f97099d6fd6574c0a528bb08c294277748048608a37d73ba9`;
stack_ablation.py byte-identical to W1's pin (`5134cddb…c422b73b`);
stack_variants.py `4ffefa3d…fc785560`; the four carrier files
byte-identical to W3's stored kit_hashes (`quote_flow.mmd
bc6447ec…`, `.yaml 51c8298a…`, `.md 4935cb1a…`, `_stub.py
5c6b92a9…`); suite `113ab6ac…9b501`, runner `f6cc907e…2fe7c88`; the
three frame strings frozen in Design and as driver constants.
**Owner go, verbatim (2026-08-11): "freeze and go, as soon as all 3
models come back OK." — condition satisfied the same day: the
key-probe session reported WAVE_API_KEY present and all three wave
models OK (generators + judge), no key material relayed.** Editing
anything above Results after a scored run invalidates the wave —
re-freeze consciously and say so. Lineage: W3's frozen record
carries the prompt-frame asymmetry as its disclosed limitation
(W3's finding 3) and its matrix's refutation branch reopened the
carrier question on outcome evidence; the candidate is recorded in
ROADMAP § Settled questions and
docs/external-review-evaluation.md § wave candidates as "carrier ×
prompt-frame factorial separating intrinsic carrier effect from
prompt-carrier alignment". Template: PREREGISTRATION_TEMPLATE.md.*

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
  frozen-prompt frame, W3's finding 3).
- **W3's standing headline gains or loses its frame scoping:** if
  the ordering survives a neutral frame, "carrier matters" becomes
  frame-free (a strengthening); if a carrier's deficit closes under
  neutral or native framing, W3's claim for that carrier gains a
  "under a PlantUML-framed harness" scoping — a material narrowing,
  published with full prominence. **In either direction, editing
  W3's stored record for a carrier is licensed only by G3** — the
  record-edit gate below: no re-scoping on an occasion that did not
  reproduce that carrier's stored-frame deficit (adversarial
  finding 5).
- **The opus-YAML non-compile mechanism** (the W1–W4 program's only
  non-compiles, 3/3): frame-induced misparse vs carrier-intrinsic —
  decided by E3, conditioned on the in-wave F-stored cell
  reproducing the non-compile behavior (adversarial finding 3).
- **Pilot-facing sentence:** the honest dated Mermaid sentence
  ("−9.1 pp pooled / −20 pp flow-sensitive in this lab's single
  measurement") either hardens (intrinsic) or gains the frame
  scoping — G3-gated likewise (adversarial finding 5).
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
  | F-neutral | all 5 carriers | "a behavior interaction specification" (behavior-slot-silent — scope disclosed below) |
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

  **Frame-scope disclosure (adversarial finding 7):** the
  substitution touches the behavior-kind phrase only. The generation
  prompt's container slot still reads "a PlantUML C4 container
  diagram" in all 14 cells (aligned wording for the structure
  carrier, which never varies), and every bundle physically contains
  containers.puml. F-neutral is therefore **behavior-slot-silent,
  not PlantUML-free** — no sentence in this record may claim a
  "frame-free" harness beyond the behavior slot.

- **Charter-standards classification (adversarial finding 9):** the
  frame axis varies harness wording, not an information unit
  (charter §4: information = decisions, thresholds, failure policy,
  signatures) — every cell carries identical information, and the
  carrier axis reuses W3's frozen fixed-information translations.
  Each contrast therefore varies carrier at fixed information
  (across-carrier columns) or harness frame at fixed everything
  (within-carrier rows), complying with charter §2 E3 as W1/W1b/W3
  cited it; the frame is a harness property, as prompts have been
  treated across W1–W5.

- **Everything runs in-wave (the W5/W1b cross-occasion lesson):** all
  14 cells are freshly scored; W3's stored arms and W1-A2 serve as
  cross-occasion references only (stored: PlantUML 0.439 pooled /
  0.933 flow-set; code-stub 0.379/0.767; mermaid 0.348/0.733;
  controlled-english 0.288/0.600; yaml 0.136/0.267; opus-yaml 0/3
  compiling). No stored number enters any expectation's arithmetic
  (held throughout — E6 re-anchored in-wave by adversarial finding
  1; stored-median comparisons are run notes only).

- **Units and n:** 14 cells × 2 generators × 3 runs = **84 scored
  runs**, pooled n = 6 per cell. Quantums, stated up front: one slot
  in one run moves a pooled cell rate by 1/66 ≈ 1.52 pp
  (per-generator 1/33 ≈ 3.03 pp); the flow-set (30 slots per cell)
  moves 1/30 ≈ 3.33 pp per slot and 20 pp per consistently-flipped
  scenario — flow-set contrasts are coarse and the verdicts below
  use the W3 convention (|Δ| ≤ 10.00 pp inclusive = equivalent).

  **Power note (disclosed; recomputed from the stored run data by
  the adversarial pass, finding 6):** at W1's pooled run-level
  SD ≈ 0.12, a 6-run pool has SE ≈ 5 pp and a 6-vs-6 **gap** has
  SE ≈ 6.9 pp (the √2, per W1's own convention). Flow-set noise is
  larger than the pooled figure suggests: the stored records give
  flow-set run-level SDs of 0.163 (W1-A2) and 0.32–0.35 (all four
  W3 carrier arms), so a 6-vs-6 flow-set gap has SE ≈ 9.4–20 pp —
  E1's 10.00 pp bar sits at ~1.1 down to ~0.5 gap-SE depending on
  the carrier's noise. Any single E1 verdict is low-powered:
  verdicts within ~1 gap-SE of the bar are flagged low-confidence
  in the narration, and the four-verdict pattern, not any single
  verdict, carries the headline. **Shared-reference caveat (W3's
  finding 4, carried verbatim):** all four E1 deficits share the
  single puml-neutral cell (n = 6), whose sampling error shifts all
  four coherently — as E4's two cells share it too; a
  coherent-shift false pattern is a real risk and one-carrier-only
  surprises are flagged low-confidence. **E2a's power, disclosed:**
  its tolerance (1 pooled slot ≈ 1.52 pp) is ≈ 0.22 gap-SE — under
  a true-zero alignment effect each carrier passes with p ≈ 0.59
  and the four-carrier conjunction fails with p ≈ 0.88, so an E2a
  miss is *expected under the null*; its failure branch
  pre-commits the noise-compatible reading rather than a
  negative-effect claim (adversarial finding 6).

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
  compile counts per cell; judged medians; every E1–E6/G1–G3
  input). **Pre-freeze equivalence obligations:** (1)
  prompt-equivalence — the puml-stored cell's assembled prompt is
  byte-identical to W1-A2's stored prompt (W1's report records the
  prompt text); for the four alternative-carrier F-stored cells,
  W3's report stores no prompt text (the stack_variants report
  writer omits it), so the obligation is **reconstruction-based**:
  each assembled prompt is byte-identical to the prompt
  reconstructed from the frozen GEN_PROMPT and W3's pinned carrier
  files under W3's substitution rule, with the reconstruction rule
  printed in the check output (adversarial finding 12); (2) each
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
the W5/W1b convention). **Analysis standards, as the template
mandates (adversarial finding 10):** gaps and orderings, never
absolute rates; per-condition aggregation is the headline unit; no
hard-demand partials on executed gradients (judged gradients may
carry the partial with both rationales cited). Committed outputs:
the carrier × frame rate matrix (pooled / per-generator / flow-set),
the per-carrier alignment-delta table, per-cell compile counts, and
the E-inputs.

## Calibration (mandatory, disclosed)

Inherited: W1's generation-calibration vets the pipeline **for the
five F-stored cells only** (identical pipeline there); the nine
F-neutral/F-native cells modify the generation prompt — the very
object calibration vets — and are **new conditions that cannot be
pre-run** (adversarial finding 8). Their run-time guard is G2b
below, not calibration. W3's carrier files are inherited as
adversarially revised and frozen. W3b-specific $0 checks before
freeze: smoke_test.py re-run; driver dry-run printing all 14 cell
inventories and the three frame strings; the three equivalence/diff
obligations under Design. **No scored, degraded or partial condition
may be executed pre-freeze — every F-neutral and F-native cell is a
new condition and none has ever been run.**

## Pre-registered expectations (mandatory)

- **W3b-E1 (the intrinsic-ordering test — the wave's headline):**
  under F-neutral, every alternative carrier's flow-set deficit vs
  the in-wave PlantUML-neutral cell is > 10.00 pp (strictly outside
  W3's inclusive equivalence bar), checked per carrier (four
  verdicts E1-stub / E1-mermaid / E1-english / E1-yaml). Any
  W3-record consequence of an E1 verdict is licensed per carrier by
  G3 (adversarial finding 5).
- **W3b-E2a (alignment no-harm, ×4; split from the drafted E2 —
  adversarial findings 2, 14):** for each alternative carrier,
  pooled(F-native) − pooled(F-stored) ≥ −1 pooled slot
  (−1/66 ≈ −1.52 pp) — at most one pooled slot below zero, stated
  on the measurement grid.
- **W3b-E2b (alignment materiality where the frame plausibly hurt —
  split from the drafted E2; adversarial finding 14):** for yaml
  specifically, the alignment gain pooled(F-native) −
  pooled(F-stored) is ≥ +9 pp pooled (the shared materiality bar;
  6 pooled slots = 9.09 pp clears it).
- **W3b-E3 (the non-compile mechanism, conditioned in-wave —
  adversarial finding 3):** reference count = opus-yaml compiles in
  the in-wave F-stored cell. **If the reference is ≤ 1 of 3** (the
  stored 0/3 behavior reproduced): opus-yaml compiling ≥ 2 of 3
  under F-native AND under F-neutral = frame-induced; ≤ 1 of 3
  under both = carrier-intrinsic; split = mixed, reported
  per-frame. **If the reference is ≥ 2 of 3:** the W3 non-compiles
  did not reproduce on this occasion — the cross-occasion
  instability branch fires (recorded prominently) and NO mechanism
  claim is made in either direction: there is no in-wave
  non-compile to explain.
- **W3b-E4 (the baseline's own frame-sensitivity):**
  |pooled(puml-neutral) − pooled(puml-stored)| ≤ 9 pp — PlantUML's
  lead is not an artifact of its aligned frame. The failure branch
  is sign-split and binding (adversarial findings 4, 13; matrix).
- **W3b-E5 (generator concordance on the alignment axis — §8.3
  discipline):** for each alternative carrier, the opus and haiku
  alignment deltas (native − stored) are same-sign, or every
  opposite-signed delta is at most one per-generator slot
  (1/33 ≈ 3.03 pp) from zero (grid-exact restatement, adversarial
  finding 2; W3-E3's wording).
- **W3b-E6 (judged, secondary, in-wave — re-anchored, adversarial
  finding 1):** for every carrier × generator where both cells are
  evaluable (≥ 2 judgeable runs each, per the judged-n
  conventions), the F-neutral and F-native judged-invention medians
  are each within 2 of the same carrier's **in-wave F-stored**
  median for that generator. Comparisons whose in-wave reference or
  target cell is not evaluable (e.g. opus-yaml if its F-stored cell
  again yields < 2 compiling runs) take the descriptive-only
  branch: medians reported, no verdict, never imputed.
  Cross-occasion comparison with stored medians (W3's where they
  exist; W1's opus 6 / haiku 5 for the puml carrier) is a run note,
  never an expectation input.

**Validity guards (pre-committed, not expectations):**

- **G1 (anchor sanity — run-note rule, not a blocker):** the in-wave
  puml-stored cell lands within ±15 pp pooled of W1-A2's stored
  0.439. Outside that band, a cross-occasion anomaly is recorded
  prominently; every contrast in E1–E5 remains in-wave-valid by
  construction (all cells same-occasion).
- **G2 (floor, derivation stated — adversarial finding 11):** each
  generator's in-wave puml-stored pool > 0.15; below, suspect
  harness defect — halt, investigate, disclose; any fix forces a
  conscious re-freeze. Derivation: 0.15 sits ≈ 4 per-generator
  run-level SEs (0.12/√3 ≈ 6.9 pp each) below the weaker stored
  anchor (haiku A2 0.4242, W1's record) — sampling noise alone
  cannot plausibly land there, so below-floor is read as harness
  defect, not signal.
- **G2b (frame-cell defect guard — adversarial finding 8):** if
  either generator's in-wave puml-neutral pool lands ≤ 0.15, the
  run halts for artifact inspection BEFORE any interpretation: a
  mechanical defect (non-parsing outputs, harness error) → fix +
  conscious re-freeze; mechanically sound artifacts → the number
  stands as a result and the inspection is disclosed in the run
  notes. The guard exists so a frame-phrase-induced pipeline defect
  cannot be narrated as frame-sensitivity.
- **G3 (record-edit licensing — the W1b reproduction discipline;
  adversarial finding 5):** editing W3's stored record for a
  carrier (shedding the frame caveat under E1-confirmed, or adding
  the "PlantUML-framed harness" scoping under E1-failed) is
  licensed only if that carrier's **in-wave F-stored** flow-set
  deficit vs the in-wave puml-stored cell exceeds 10.00 pp — i.e.
  this occasion reproduced a carrier deficit to decompose. A
  carrier whose stored-frame deficit does not reproduce gets the
  cross-occasion anomaly as its headline; its E1 verdict remains
  in-wave-valid and is reported, but W3's record is not edited on
  its account (W1b precedent: no attribution of an effect the
  occasion did not reproduce). Independent of G1, which concerns
  the pooled anchor only.

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| E1 (×4) | The carrier effect is intrinsic for that carrier: W3's headline sheds the frame caveat for it, dated — **if G3 licenses it** (an unreproduced carrier gets the cross-occasion-anomaly headline instead; W3's record unedited); the pilot Mermaid sentence hardens ("under aligned, neutral and misaligned frames alike") | That carrier's W3 deficit was frame-carried in material part: W3's claim for it gains the "PlantUML-framed harness" scoping — a published narrowing, **G3-gated identically**; the pilot sentence carries it; harness-alignment (naming the artifact's actual format in the prompt) is recorded as a measured lever. Verdicts within ~1 gap-SE of the bar carry the low-confidence flag (power note) |
| E2a | Alignment never hurts (×4): the no-harm leg of the hygiene claim is recorded | Magnitude-tiered, pre-committed (adversarial finding 6): every negative delta < 9 pp in magnitude → noise-compatible at this power (the conjunction fails p ≈ 0.88 under the null) — narrated as such, NO measured-negative-effect claim and no hygiene claim; any negative delta ≥ 9 pp pooled → a genuine surprise, recorded per-generator with the carrier named |
| E2b | Alignment materially helps the far carrier: "cheap hygiene for any non-PlantUML corpus" gains its materiality leg | The yaml alignment gain is submaterial on this occasion (actual delta quoted): no material-help claim; yaml's W3 deficit is NOT attributed to frame in material part, which feeds the E1-yaml/G3 reading (adversarial finding 14) |
| E3 | *(licensed branch — in-wave F-stored reference ≤ 1/3)* Both-clear: the program's only non-compiles were harness-frame artifacts — the YAML carrier's executed penalty is re-stated net of them; opus-yaml judged medians are reported, descriptive-only where E6's reference cell is non-evaluable | Neither-clear: non-compiles are carrier-intrinsic for opus — the W3 wording stands as written. Split: reported per-frame, no single-mechanism claim. **Reference ≥ 2/3: cross-occasion instability branch — no mechanism claim in either direction (adversarial finding 3)** |
| E4 | The baseline is frame-robust; every W3-relative delta stands on a stable reference | Sign-split, binding (adversarial findings 4, 13): Δ = pooled(puml-neutral) − pooled(puml-stored). **Δ ≤ −9 pp** (stored on top): PlantUML's lead is partly self-frame — every W3 delta gains the note. **Δ ≥ +9 pp** (neutral on top): the aligned frame was *hurting* the baseline — the opposite story, stated as such. Either direction triggers the dual-reference rule: every E1 delta is additionally computed against in-wave puml-stored, and any carrier whose E1 verdict flips between references is reported reference-dependent with NO headline claim |
| E5 | Alignment claims portable across tiers ("ordering, not magnitude") | Per-generator alignment language (extends the §8.3 partial fire to the frame axis) |
| E6 | Invention insensitive to frame at fixed carrier (in-wave) | The deviating cell named; judged-only caveat attached to any frame claim. Descriptive-only branch (no evaluable in-wave reference or target): reported not-evaluable, never imputed (adversarial finding 1) |

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
out of scope); the container slot stays PlantUML-named in all 14
cells, so no cell is PlantUML-free (adversarial finding 7); E1's
four verdicts share one reference cell and E4's two cells share it
too — the coherent-shift risk is disclosed in the power note
(adversarial finding 6); flow-set quantums coarse as disclosed;
single vendor pair; n = 3 per generator per cell;
capability-relative, dated — carrier and frame results re-measure
per model generation (charter §2 C1).

## Results (2026-08-11, $13.72)

**Run notes (recorded before the verdicts):**

- Clean completion: 84/84 runs, no abort, no judge errors; 170 of
  MAX_CALLS 250 (84 generations + 14 opus generation retries + 72
  judgements — every compiling artifact judged); spend $13.7229 of
  the $30 ceiling. Executed by a dedicated runner session on the
  frozen branch (freeze f1cdbfd; raw record commit 686fcb0:
  report.json, analysis.json, all 84 artifacts). The committed
  outputs (rate matrix, alignment-delta table, compile counts,
  per-frame orderings, every E/G input, semantic-only rates) are in
  results/W3B/wave_main/analysis.json.
- Credential context, one line: the wave ran under the environment's
  re-enabled key after a three-model live probe; one platform
  security prompt required a manual owner approval during the probe
  session; the wave itself ran unattended. No key material anywhere
  in the record.
- 12 non-compiling runs, ALL opus, concentrated by frame:
  yaml-stored 3/3, yaml-native 3/3, yaml-neutral 1/3,
  code-stub-neutral 3/3, mermaid-native 2/3. Failure mode (artifacts
  inspected): not truncation (stop_reason end_turn; the one
  max_tokens attempt was retried) and not refusal — output-contract
  collapse: bare pricing-formula fragments, echoed bundle-style
  section headers plus planning prose ("Let me analyze the
  specification and implement it."), typographic characters (em/en
  dashes, ≤) inside would-be code. Haiku compiled 42/42.
- The two "compiling" yaml-neutral opus artifacts are degenerate
  single-line formula fragments (parse-valid, undefined-name-dead,
  0/11 executed): compilation without substance. E3's neutral count
  carries this disclosure wherever quoted.
- Cross-occasion level shift, disclosed: every in-wave F-stored cell
  landed above its W3 stored value (pooled: code-stub 0.4242 vs
  0.3788; mermaid 0.4091 vs 0.3485; controlled-english 0.3788 vs
  0.2879; yaml 0.2121 vs 0.1364; flow-set same direction) while
  reproducing W3's stored-frame ORDER exactly. The puml-stored
  anchor reproduced W1-A2 to the slot: 29/66 = 0.4394, G1 delta
  0.0000.
- Judged run note (cross-occasion, never expectation arithmetic):
  in-wave stored medians sit within 0–2 of the stored records where
  comparable. The program's first-ever judgeable opus-yaml cells are
  the two degenerate neutral fragments (n = 2, median 2.0) —
  descriptive-only under E6's conventions.

**The cell matrix (pooled executed / flow-set; compiles opus+haiku):**

| Carrier | F-stored | F-neutral | F-native |
|---|---|---|---|
| PlantUML | .4394 / .9667 (3+3) | .3636 / .8000 (3+3) | ≡ stored |
| code-stub | .4242 / .9000 (3+3) | .0909 / .1667 (0+3) | .2424 / .5333 (3+3) |
| Mermaid | .4091 / .8667 (3+3) | .3788 / .8333 (3+3) | .2879 / .5333 (1+3) |
| controlled-english | .3788 / .7667 (3+3) | .3788 / .7667 (3+3) | .3485 / .7333 (3+3) |
| YAML | .2121 / .4667 (0+3) | .1818 / .3667 (2+3) | .1061 / .2000 (0+3) |

Per-frame flow-set orderings: F-stored puml > stub > mermaid >
english > yaml (W3's order, reproduced); F-neutral mermaid ≥ puml >
english > yaml > stub; F-native english > stub = mermaid > yaml.

**Validity guards:**

- **G1 PASS** — in-wave puml-stored 0.4394 vs W1-A2 stored 0.4394:
  delta 0.0000 exactly (within ±15 pp; run note above).
- **G2 PASS** — opus 0.4545, haiku 0.4242, both > 0.15.
- **G2b PASS** — puml-neutral opus 0.3939, haiku 0.3333, both >
  0.15; no defect inspection triggered, the frame cells are
  mechanically sound.
- **G3** — stored-frame flow deficits vs puml-stored: LICENSED
  controlled-english (20.00 pp > 10.00) and yaml (50.00 pp); NOT
  licensed code-stub (6.67 pp) and mermaid (10.00 pp exactly — the
  inclusive equivalence bar; not reproduced beyond it). Applied
  below: no W3-record re-scoping for code-stub or mermaid; their
  headline is the cross-occasion non-reproduction.

**Per-expectation verdicts (pre-committed interpretations applied,
nothing reinterpreted):**

- **E1 — two of four confirmed; per the power note the four-verdict
  pattern, not any single verdict, carries the headline.**
  - **E1-stub CONFIRMED** (deficit 63.33 pp > 10.00) — G3-unlicensed:
    the cross-occasion anomaly is stub's headline and W3's record is
    unedited on its account. Mechanism disclosed: the deficit is
    neutral-frame-induced collapse (opus 0/3 compiling — the
    output-contract failure above; haiku flow 0.3333), not a
    reproduced stored-frame deficit (stub-stored sat 6.67 pp from
    baseline — equivalent).
  - **E1-mermaid NOT CONFIRMED** (deficit −3.33 pp; mermaid-neutral
    landed ABOVE the reference) — G3-unlicensed: cross-occasion
    anomaly headline, W3's mermaid claim unedited. Near-bar
    low-confidence flag per the power note.
  - **E1-english NOT CONFIRMED** (deficit 3.33 pp ≤ 10.00) — G3
    LICENSED: W3's controlled-english claim gains the "under a
    PlantUML-framed harness" scoping, dated, at full prominence.
    Mechanism disclosed: english's own cells are frame-flat (flow
    .7667/.7667/.7333); the closure is baseline-side — PlantUML
    loses its aligned-frame flow advantage under the neutral frame.
    Low-confidence flag: 6.67 pp from the bar, inside one flow-set
    gap-SE.
  - **E1-yaml CONFIRMED** (deficit 43.33 pp > 10.00) — G3 LICENSED:
    intrinsic. W3's yaml claim SHEDS the frame caveat, dated: the
    deficit persists under aligned, format-silent and carrier-native
    frames alike.
- **E2a FAILED — the wave's surprise, published at full prominence.**
  Alignment deltas (native − stored, pooled): code-stub −18.18,
  mermaid −12.12, yaml −10.61, controlled-english −3.03.
  Pre-committed tiering applied: three carriers beyond materiality =
  measured NEGATIVE alignment effects, per-generator — stub: opus
  −15.15 (3/3 compiling; content-level) and haiku −21.21
  (content-level); mermaid: opus −30.30 (compile-borne, 1/3
  compiling) vs haiku +6.06; yaml: opus 0.00 (0/3 compile floor
  under both frames) and haiku −21.21 (content-level, 3/3
  compiling). controlled-english −3.03 (2 slots) takes the
  noise-compatible tier. NO hygiene claim: naming the artifact's
  actual format in the prompt measurably hurt on this occasion.
- **E2b FAILED** — the yaml alignment delta is −10.61 pp (the bar
  wanted ≥ +9; the actual is negative and material). No
  material-help claim; yaml's W3 deficit is NOT attributed to frame
  in material part — consistent with E1-yaml's intrinsic verdict.
- **E3 SPLIT, under the licensed condition** (in-wave F-stored
  opus-yaml 0/3 — the stored non-compile behavior reproduced
  cross-occasion). F-native 0/3, F-neutral 2/3: reported per-frame,
  no single-mechanism claim. The native frame recovered nothing; the
  neutral frame's two "compiles" are the degenerate one-line
  fragments (0/11 executed) — parse-validity partially restored,
  substance not.
- **E4 CONFIRMED** — |pooled(puml-neutral) − pooled(puml-stored)| =
  7.58 pp ≤ 9. The baseline is frame-robust on the pre-committed
  pooled bar. At equal visibility, the run note: the flow-set delta
  is −16.67 pp (5 of 30 slots, quantum-coarse) and per-generator
  pooled opus −6.06 / haiku −9.09 — so the shared-reference caveat
  (power note) stays active in every E1 narration. The dual-reference
  rule was pre-committed for failure only and is not triggered.
- **E5 FAILED** — mermaid's alignment deltas are opposite-signed
  beyond one per-generator slot (opus −30.30 vs haiku +6.06).
  Consequence applied: per-generator alignment language everywhere
  (the §8.3 partial fire extends to the frame axis). Disclosed
  pattern: under the stored frame haiku is near-flat across carriers
  (0.3939–0.4242 pooled) — the stored-frame carrier ordering is
  opus-borne.
- **E6 CONFIRMED** — every evaluable comparison within 2 of the
  in-wave F-stored median (largest |Δ| = 2: code-stub haiku native,
  6 vs 4). Descriptive-only cells, named: code-stub-neutral opus (0
  judgeable), mermaid-native opus (n = 1), yaml opus (no evaluable
  in-wave stored reference; neutral n = 2, median 2.0, on the
  degenerate fragments). Judged invention is frame-insensitive at
  fixed carrier where measurable.

**Consequences (matrix applied):**

1. **W3's standing headline survives only in per-carrier,
   per-generator form.** YAML's deficit is intrinsic (frame caveat
   shed — G3-licensed). Controlled-english's deficit is scoped to
   the PlantUML-framed harness (G3-licensed; baseline-side
   mechanism). Code-stub and Mermaid carry cross-occasion
   non-reproduction notes — their W3 stored-frame deficits did not
   reproduce beyond the equivalence bar on this occasion, and no
   re-scoping is licensed. The stored-frame ordering reproduced
   exactly while the neutral-frame ordering collapsed it.
2. **Alignment is not hygiene.** The measured direction on this
   occasion is harm (three carriers at materiality; opus collapses
   into non-code fragments under unfamiliar frames, haiku compiles
   but executes worse). The E1-failure branch's harness-alignment
   lever is recorded WITH ITS SIGN: the familiar stored frame
   outperformed the accurate native frames.
3. **Charter §2 C1 / checkability: unchanged** (pre-committed — this
   wave cannot re-promote). Where the outcome evidence points now
   splits per carrier: at harness-frame alignment for
   controlled-english (and open for stub/mermaid pending
   reproduction), at carrier syntax for yaml.
4. **Downstream edits made under the licenses** (dated, this
   commit): research-charter §6 carrier row + W3 wave-entry pointer;
   minimum-sufficient-stack §3; ROADMAP W3b entry ran-note.
   W3_PREREGISTRATION.md itself untouched — frozen occasion records
   are never edited (the W1/W1b precedent); scoping lives in the
   consolidation records.
5. **Pilot-facing:** the dated Mermaid sentence gains the
   cross-occasion note (second occasion: stored-frame deficit at the
   equivalence bar exactly; equivalent-or-better under the neutral
   frame). No alignment-hygiene recommendation exists anywhere.
