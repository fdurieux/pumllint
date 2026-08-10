# Wave pre-registration — W2: redundancy and conflict

*FROZEN 2026-08-10, before any scored run — the freeze is the commit
titled "Lab: W2–W4 frozen" carrying this file, the revised driver and
the variant files. Provenance: draft 2cf7d65
(findings-before-verdicts); independent adversarial pass against it —
**9 findings: 3 major, 6 minor, all adopted in this revision.** Owner
go for W2–W4 given 2026-08-10 in the working session ("run W2 to W4
as well"); this preamble is its durable record, fixed by the freeze
commit. Editing anything above Results after a scored run invalidates
the wave. Template: PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base (inherited from W1, by import — not copied):**
generators `claude-opus-4-8` and `claude-haiku-4-5-20251001`, judge
`claude-sonnet-5` @16000 (the **C4-wave judge schema** — the naming
collision with this wave's C1–C3 arms is coincidental); prompt
**stack-bundle-v2** (REQUEST_CONTRACT byte-identical by import);
frozen suite tools/acceptance/cargo_quote_suite.py
(`113ab6ac…9b501`) + runner (`f6cc907e…2fe7c88`) + OVERLAYS
driver-side; retry-once; shared definitions (materiality ≥ 9 pp
pooled; rate-based net gains; tie quantums) as frozen in
W1_PREREGISTRATION.md. **Prompt identity (adversarial finding 1,
adopted):** the driver bundles every file under its pristine
kit-relative label — variant paths never appear in the model input —
and `--dry-run` mechanically proves each arm's prompt equals the
reused W1-A4 prompt with only the injected content substituted
(verified OK, all arms). W1's generation-calibration (opus 11/11/11,
haiku 10/9/11 on pristine A4 under this exact configuration)
therefore carries: W2 changes injected content only.

## Question and decision link (mandatory)

**Question:** When two artifacts of the stack contradict each other —
a stale numeric restatement, a stale behavioral sentence, a stale
worked example — does single-shot generation resolve silently, follow
the higher-authority source, or surface the conflict; and is the
damage local to the conflicted decision or global?

**Decision links:** first measurement bearing on the
precedence-of-evidence ladder (docs/agents.md, adopted 2026-07-29,
never tested — its "when sources conflict, stop and ask" rule is
currently an argument, not a result); demand evidence for the gated
sequence↔contract cross-check candidate (spec-stack evaluation —
evidence for its trigger, never a build); W5 design input; wording in
agents.md and value-in-the-sdlc gains a measured citation either way.
**Attribution scoping (adversarial finding 3, adopted):** the bundle
never contains the ladder itself, but it does contain two in-band
deference cues that survive in the variants by design — C1 retains
spec.md's "all numeric rules live in the decision tables … never
restates a number" sentence (made self-contradictory by the
injection: realistic drift), and C3 retains the Gherkin Background
"Given the tariff and screening rules of decision_table.md are in
force". A "table wins" outcome is therefore evidence for
**DT-over-prose under in-band deference hints**, not clean ladder
evidence, and every confirmed branch below is worded accordingly.

## Design (mandatory)

- **Conditions (3; each = pristine A4 with ONE file's content swapped
  for a single-change variant — diff-verified single-change; prompt
  labels pristine per the preamble):**

  | Arm | Conflict injected | Authority classes in tension (agents.md ladder) |
  |---|---|---|
  | C1-numeric | spec.md flow step 4 gains "risk index of 45 or below issues the quote" — DT-S says 41/42 | spec prose (class 2/6) vs decision table (class 1) |
  | C2-behavioral | spec.md step 6 becomes "Refusals are not notified" — the diagram note, DT-S note 2, the state machine's notifyRefusal transitions, Gherkin G3 AND the spec's own AC row 3 all say refusal IS notified | one stale prose sentence vs a five-source majority |
  | C3-stale-test | acceptance.feature G5 price 1878.00 → 1866.00 (computed with a stale 0.85 base rate; recomputed: 0.85·600 + 1.13·1200 = 1866.00) — DT-P says 0.87 | worked example (class 1) vs normative formula (class 1): the ladder cannot decide |

  **Control:** W1 A4 (declared reuse — bundle/prompt identity proven
  mechanically; pooled 0.945, every discriminator scenario below at
  10/10). **Pre-registered discriminators:** C1 → review_boundary_42
  (risk 42 must hold; a 45-implementation quotes and notifies,
  failing overlay and must_not_call); C2 → refuse_boundary_67
  (must_call notification); C3 → price_exact_heavy +
  price_exact_both (overlays require DT-true 3186 / 8652.4; the
  stale rate yields 3146.00 / 8616.79 — both fail).

- **Units and n:** 3 arms × 2 generators × 3 runs = 18 scored runs;
  pooled n = 6 per arm.
- **Conflict-surfacing scan (deterministic, pre-registered):**
  CONFLICT_MARKER_RE =
  `(?i)conflict|contradict|inconsist|discrepan|mismatch` over each
  generated module; a run "surfaces" iff it matches.
- **Driver:** tools/stack_variants.py (live MAX_CALLS 120; wave
  ceiling; full-record storage under results/W2/wave_main/; kit
  hashes recorded in every report). Variant sha256, pinned:
  C1_spec.md `5c11198d07abd603427c277bc898529b97a77eeb41ccac66e3a7d51c4dc40c5d`;
  C2_spec.md `131ed6f6b15c3136e93c59e6ea20da11819a5da3dce3b05d9ce4fc47000ee1a3`;
  C3_acceptance.feature `8cc5aec8a9af801ff6e6ec3bfa35b99bb2ec74c6ad0e47e2a2fef6f49a004d5c`.

## Oracles (mandatory)

As W1 (frozen suite, runner, overlays, full + semantic-only rates;
judged quoted as judgments; gaps/orderings, never absolutes).
**Oracle-separation declaration (adversarial finding 2, adopted):**
every arm carries tests-as-input. C1/C2 use the pristine
acceptance.feature — W1's declared overlap
(cargo_quote/tests_input/oracle_overlap.md) carries unchanged. C3
swaps that file: G5's declared relationship changes from "adjacent —
exercises P1+P4 only, values do not reveal the graded points" to
**adjacent-contradicting on P1** — the stale example now actively
misleads about the base rate, which is precisely what E4 measures;
all other G-rows carry unchanged.

## Calibration (mandatory, disclosed)

Inherited: W1 attempt-2 generation-calibration PASSED under the
identical configuration. W2-specific $0 checks, run and adopted:
single-change diffs verified; C3 stale arithmetic recomputed;
**marker base-rate scan (finding 5): the marker regex matches 0 of
the 72 stored W1 generations, and 0 of the three W2 input bundles —
zero false-positive and zero echo base rate**; prompt-identity check
OK for all three arms. No scored or degraded condition has been
executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W2-E1 (silent resolution dominates):** fewer than 5 of the 18
  runs surface the conflict per the marker scan.
- **W2-E2 (numeric conflict):** C1 review_boundary_42 pooled ≥ 4/6 →
  the decision table beat the stale prose (under in-band deference
  hints); ≤ 2/6 → the prose won; 3/6 → split, recorded as such.
- **W2-E3 (behavioral conflict):** C2 refuse_boundary_67 pooled
  ≥ 4/6 → the five-source majority beat the stale sentence; ≤ 2/6 →
  the stale sentence won; 3/6 → split.
- **W2-E4 (stale example anchors), stated in flip units (finding 4):**
  C3's two price scenarios pool 12 slots (quantum 8.33 pp).
  ≥ 2 of 12 slots fail → anchoring measured; exactly 1 of 12 →
  below bar, recorded verbatim as a marginal single-slot event
  (NOT "calibration-safe"); 0 of 12 → the formula wins and worked
  examples are calibration-safe at this dose. (W1-A4 baseline:
  0 of 20 slots failed.)
- **W2-E5 (locality):** each arm's mean pooled rate over its
  NON-discriminator scenarios stays within 9 pp of the W1-A4
  same-set baseline (C1/C2: 0.940; C3: 0.933) → conflict damage is
  local; any breach → a conflict destabilizes unrelated decisions
  (worse; recorded with the affected scenarios named).

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W2-E1 | agents.md's "stop and ask must be enforced, it is not emergent" gains its first measurement; harness-enforcement wording cited | Models self-surface conflicts at a measurable rate: agents.md wording updated to say so, dated; the surfacing rate quoted |
| W2-E2 | DT-over-prose **under in-band deference hints** matches the ladder's direction for numerics; agents.md citation carries exactly that scope | The stale prose won or split: even in-band deference did not protect the numeric — the enforcement argument strengthens; recorded as demand evidence for the gated sequence↔contract cross-check (build stays gated) |
| W2-E3 | Majority evidence beats a single stale sentence; same scoped citation | Stale sentence won or split: one sentence can silently flip behavior against five agreeing sources — strongest demand evidence for the cross-check candidate (still no build) |
| W2-E4 | Anchoring measured: stale worked examples are a poisoning vector; W1's tests-as-input row gains the dated caveat; pilot-charter acceptance-criteria guidance notes stale-example risk | Formula wins at this dose: recorded, no caveat; the single-slot branch is recorded verbatim if it occurs |
| W2-E5 | Conflicts are local: per-artifact gating rationale unchanged | Global destabilization: recorded with scenarios named; strengthens the redundancy-risk reading alongside W4 |

## Budget (mandatory)

Ceiling **$10** (hard, live guard); estimate ≈ $4.5 — derived from
the per-call figures recorded in W1's pre-registration Budget
(themselves C4-precedent estimates; W1's measured actuals are lower,
so the estimate is conservative — adversarial finding 7). MAX_CALLS
120 (live counter incl. retries). Costs recorded in Results.

## Carried limitations (mandatory)

As W1 (one system, toy scale, single-shot, LLM judge, one vendor,
capability-relative; n = 3/generator/arm, pooled 6). Granularity
(finding 4's correction): E2/E3 read per-scenario pools with quantum
1/6 ≈ 16.7 pp — single-flip effects visible; E4's metric has quantum
1/12 ≈ 8.3 pp; E5's mean has quantum ≈ 1.7 pp — sub-flip effects on
E5 are visible but weakly powered. One injected conflict per arm —
interactions of multiple conflicts unmeasured. The in-band deference
cues (Design) bound every authority claim.

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
