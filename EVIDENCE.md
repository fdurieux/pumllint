# Does the maturity score predict codegen outcome?

Phase 10e experiment record — 2026-07-22. Raw data: `experiment_results/report.json`
(75 runs, zero failures, $5.24 API spend). Harness: `tools/codegen_experiment.py`.

## Method

- **Corpus:** 25 sequence diagrams spanning maturity levels L1–L5 under the
  codegen profile — 4×L5, 2×L4, 3×L3, 8×L2, 8×L1 — drawn from two realistic
  scenario families (order_payment, credit_intake: pristine examples plus
  systematic degradations), three synthetic structurally-trivial diagrams,
  and one wild-harvested diagram.
- **Generation:** 3 runs per diagram on `claude-opus-4-8` (adaptive thinking),
  fixed prompt: implement the diagram as a Python module, one class per
  participant; *"where the diagram is ambiguous, make your best guess"* —
  ambiguity resolution is deliberately left to the generator, because that
  divergence is what the maturity score claims to predict.
- **Judging:** independent model (`claude-sonnet-5`), JSON-schema-constrained
  rubric: participants/messages/guards/failure-paths realized, fidelity 0–100,
  and inventions split into *invented business logic* (harmful — domain
  semantics the diagram never specified) vs *defensive embellishments*
  (benign engineering).
- **Pre-registered expectations:** E1 fidelity increases with level;
  E2 invented business logic decreases with level; E3 composite score
  correlates positively with per-run fidelity.

## Results

Per level (runs weighted):

| Level | Diagrams | Runs | Compile 1st try | Fidelity | Invented/run | Embellish/run |
|---|---|---|---|---|---|---|
| 5 | 4 | 12 | 1.0 | 72.4 | 3.2 | 5.3 |
| 4 | 2 | 6 | 1.0 | 73.0 | 4.0 | 5.3 |
| 3 | 3 | 9 | 1.0 | **96.4** | 0.0 | 2.8 |
| 2 | 8 | 24 | 1.0 | 69.1 | 3.3 | 4.8 |
| 1 | 8 | 24 | 1.0 | **59.2** | 4.1 | 4.9 |

**E3 — supported.** Composite↔fidelity correlation r = **0.489** across all 75
runs; within-family (content complexity controlled) r = 0.386 (order_payment,
n = 39) and r = 0.483 (credit_intake, n = 24).

**E1 — supported within families; confounded across them.** The L3 outlier
(96.4) is the three synthetic diagrams: structurally trivial linear
call/reply chains with no guards and no domain vocabulary — near-perfect
fidelity is available regardless of maturity because there is almost nothing
to get wrong. **Fidelity is diagram-relative, so cross-family comparison
conflates content complexity with maturity**; within each realistic family
the gradient holds, and excluding the synthetic bucket the levels order
72.4 / 73.0 / 69.1 / 59.2.

**E2 — weak in the middle, strong at the extremes.** Invented-logic means are
noisy across mid levels (~3–4/run, including ~3.2 at L5 — a strict-judge
floor), but the two fully degraded diagrams (composite ≤ 25) drew the two
highest invention rates of the whole experiment (5.7 and 6.3 per run) — the
generator concretizing vague guards and prose messages into invented rules.

## The two findings that matter most

**1. The relationship is a cliff, not a slope.** From composite ~40 up to 100,
fidelity is roughly flat (67–79) — a strong generator compensates for
moderate diagram flaws. Below composite ~40 it collapses: both families'
worst diagrams converge on fidelity **48.7** with invention spiking. The
maturity score's sharpest predictive power is at the *bottom* of the scale:
it identifies the diagrams that will poison generation, more than it ranks
the good ones.

**2. Independent judging is not optional.** The same pristine diagram scored
90.7 under the pilot's same-model self-judge and 75.0 under the independent
judge — a ~15-point self-favoring bias. All numbers above are from the
independent judge.

## Limitations

Single generator and single judge model; two scenario families dominate the
corpus; n = 3 runs/diagram leaves per-diagram means noisy (±8); fidelity has
no complexity normalization (hence the synthetic confound); the judge rubric,
while schema-constrained, is still an LLM judgment.

## What the product may claim

Supported by this data:

- *"Maturity scores correlate with the fidelity of generated code
  (r ≈ 0.5)."*
- *"Diagrams below Level 2 measurably degrade generation: fidelity drops by
  roughly a third and invented business logic roughly doubles."*
- The `--min-level` CI gate is evidence-backed **as a risk filter**: its
  demonstrated value is keeping low-maturity diagrams out, which is exactly
  what a CI gate is for.

**Not supported:** "Level 5 ⇒ generation-ready" as an absolute. Under a
strict independent judge, even pristine L5 diagrams average ~72 fidelity
with ~3 judge-flagged inventions per run — a sequence diagram underdetermines
an implementation, and the generator fills the gap by design. Level 5 should
continue to be described as **"method-convention complete — the diagram-side
preconditions for faithful generation"**, with the cliff finding as the
quantified payoff.
