# Wave pre-registration — W2: redundancy and conflict

*DRAFT for verification, 2026-08-10 — NOT yet frozen. Freeze = the
commit carrying this file (verified), the driver
(tools/stack_variants.py) and the variant-file hashes, after the
adversarial pass is adopted; owner gave the W2–W4 go 2026-08-10
("run W2 to W4 as well"). Once a scored run exists, editing anything
above Results invalidates the wave. Template:
PREREGISTRATION_TEMPLATE.md.*

**Shared frozen base (inherited from W1, by import — not copied):**
generators `claude-opus-4-8` and `claude-haiku-4-5-20251001`, judge
`claude-sonnet-5` @16000; prompt **stack-bundle-v2** (REQUEST_CONTRACT
byte-identical by import); frozen suite
tools/acceptance/cargo_quote_suite.py
(`113ab6ac…9b501`) + runner (`f6cc907e…2fe7c88`) + OVERLAYS
driver-side; retry-once; shared definitions (materiality ≥ 9 pp
pooled; rate-based net gains; tie quantums) as frozen in
W1_PREREGISTRATION.md. W1's generation-calibration (opus 11/11/11,
haiku 10/9/11 on pristine A4 under this exact configuration) carries:
W2 changes inputs, not oracles or configuration.

## Question and decision link (mandatory)

**Question:** When two artifacts of the stack contradict each other —
a stale numeric restatement, a stale behavioral sentence, a stale
worked example — does single-shot generation resolve silently, follow
the precedence-of-evidence ladder, or surface the conflict; and is
the damage local to the conflicted decision or global?

**Decision links:** first measurement of the precedence-of-evidence
ladder (docs/agents.md, adopted 2026-07-29, never tested — its
"when sources conflict, stop and ask" rule is currently an argument,
not a result); demand evidence for the gated sequence↔contract
cross-check candidate (spec-stack evaluation — evidence for its
trigger, never a build); W5 design input (whether conflicts are what
agentic iteration must catch); wording in agents.md and
value-in-the-sdlc gains a measured citation either way.

## Design (mandatory)

- **Conditions (3; each = pristine A4 with ONE file swapped for a
  single-change variant — diff-verified single-change, diffs in the
  freeze commit):**

  | Arm | Conflict injected | Ladder classes in tension |
  |---|---|---|
  | C1-numeric | spec.md flow step 4 gains "risk index of 45 or below issues the quote" — DT-S says 41/42 | prose spec (2/6) vs decision table (1) |
  | C2-behavioral | spec.md step 6 becomes "Refusals are not notified" — diagram note, DT-S note 2 AND the spec's own AC row 3 say refusal IS notified | one stale prose sentence vs diagram + DT + AC majority |
  | C3-stale-test | acceptance.feature G5 price 1878.00 → 1866.00 (computed with a stale 0.85 base rate) — DT-P says 0.87 | worked example (1) vs normative formula (1): the ladder cannot decide |

  **Control:** W1 A4 (declared reuse — identical bundle, prompt,
  models, suite; pooled 0.945, and every discriminator scenario below
  at 10/10). **Pre-registered discriminators:** C1 →
  review_boundary_42 (risk 42 must hold, not quote — a
  45-implementation quotes it); C2 → refuse_boundary_67 (must_call
  notification); C3 → price_exact_heavy + price_exact_both (overlays
  require DT-true prices; the stale 0.85 rate fails both).

- **Units and n:** 3 arms × 2 generators × 3 runs = 18 scored runs;
  pooled n = 6 per arm; per-scenario pooled quantum 1/6 ≈ 16.7 pp.
- **Conflict-surfacing scan (deterministic, pre-registered):**
  CONFLICT_MARKER_RE =
  `(?i)conflict|contradict|inconsist|discrepan|mismatch` over each
  generated module (code + comments); a run "surfaces" iff it
  matches. The judged oracle stays the C4 rubric, unchanged.
- **Driver:** tools/stack_variants.py (imports the W1 base; live
  MAX_CALLS 120; per-wave ceiling; full-record storage under
  results/W2/wave_main/). Variant-file sha256 pinned at freeze.

## Oracles (mandatory)

As W1 (frozen suite, runner, overlays, full + semantic-only rates;
judged quoted as judgments; gaps/orderings, never absolutes). W1-A4
baseline numbers frozen above.

## Calibration (mandatory, disclosed)

Inherited: W1 attempt-2 generation-calibration PASSED under the
identical configuration; W2 adds input variants only. W2-specific $0
checks, already run: each variant differs from its pristine source by
exactly the injected change (diff-verified, recorded in the freeze
commit); C3's stale price 1866.00 recomputed as the 0.85-rate value
of G5's request (0.85·600 + 1.13·1200 = 1866.00); no scored or
degraded condition has been executed pre-freeze.

## Pre-registered expectations (mandatory)

- **W2-E1 (silent resolution dominates):** fewer than 5 of the 18
  runs surface the conflict per the marker scan.
- **W2-E2 (numeric conflict — the table wins):** C1
  review_boundary_42 pooled ≥ 4/6 → the decision table beat the
  stale prose (precedence-consistent); ≤ 2/6 → the prose won;
  3/6 → split, recorded as such.
- **W2-E3 (behavioral conflict — the majority wins):** C2
  refuse_boundary_67 pooled ≥ 4/6 → diagram + DT + AC majority beat
  the stale sentence; ≤ 2/6 → the stale sentence won; 3/6 → split.
- **W2-E4 (stale example anchors):** mean pooled rate of
  price_exact_heavy and price_exact_both under C3 drops ≥ 9 pp vs
  the W1-A4 baseline (1.000) → Gherkin anchoring measured (a stale
  worked example poisons the formula); within 9 pp → the formula
  wins and worked examples are calibration-safe here.
- **W2-E5 (locality):** each arm's mean pooled rate over its
  NON-discriminator scenarios stays within 9 pp of the W1-A4
  same-set baseline → conflict damage is local; any breach → a
  conflict destabilizes unrelated decisions (worse; recorded with
  the affected scenarios named).

## Interpretation matrix (mandatory, pre-committed)

| Expectation | Confirmed → | Not confirmed → |
|---|---|---|
| W2-E1 | agents.md's "stop and ask must be enforced, it is not emergent" gains its first measurement; harness-enforcement wording cited | Models self-surface conflicts at a measurable rate: agents.md wording updated to say so, dated; the surfacing rate quoted |
| W2-E2 | Precedence ladder's contract-over-prose step matches model behavior for numerics; ladder wording gains the citation | The stale prose won or split: the ladder is normative but NOT descriptive — enforcement argument strengthens; recorded as demand evidence for the gated sequence↔contract cross-check (build stays gated) |
| W2-E3 | Majority evidence wins behavioral conflicts; same citation | Stale sentence won or split: single stale sentences can flip behavior silently — strongest possible demand evidence for the cross-check candidate (still no build; trigger evidence recorded) |
| W2-E4 | Anchoring measured: stale worked examples are a poisoning vector; W1's tests-as-input row gains the caveat, dated; pilot charter's acceptance-criteria guidance notes stale-example risk | Formula wins: worked examples calibration-safe at this dose; recorded, no caveat |
| W2-E5 | Conflicts are local: per-artifact gating rationale unchanged | Global destabilization: recorded with scenarios named; strengthens the redundancy-is-harmful reading ahead of W4 |

## Budget (mandatory)

Ceiling **$10** (hard, live guard); estimate ≈ $4.5 (18 A4-size
generations of which 9 haiku + 18 judgements at 16k, per W1 recorded
per-call costs); MAX_CALLS 120 (live counter incl. retries). Costs
recorded in Results.

## Carried limitations (mandatory)

As W1 (one system, toy scale, single-shot, LLM judge, one vendor,
capability-relative, n = 3/generator/arm — pooled 6; per-scenario
quantum 16.7 pp is coarse: single-flip effects are visible, sub-flip
effects are not). One injected conflict per arm — interaction of
multiple conflicts unmeasured.

## Results ([date], $[cost])

*Written strictly after the freeze; run notes before verdicts;
pre-committed interpretations applied, never reinterpreted.*
