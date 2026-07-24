# Does the maturity score predict codegen outcome?

Phase 10e experiment record — 2026-07-22. Raw data: `experiment_results/report.json`
(75 runs, zero failures, $5.24 API spend). Harness: `tools/codegen_experiment.py`.
Deepened 2026-07-24 (Arc D, v0.17.0) — see "Deepening" below; analysis:
`tools/analyze_evidence.py`, `experiment_results/analysis.json`.

## Deepening — pre-registered expectations (written 2026-07-24, before the waves ran)

Three additional waves address the §Limitations items. Recorded before any
wave result was seen:

- **D1 (complexity normalization):** controlling for *hard demand* (the
  judge's count of guards + failure paths expected — the obligations a
  generator can get semantically wrong), the composite↔fidelity partial
  correlation is at least as strong as the raw r. Rationale: the synthetic
  confound *suppresses* the raw correlation (trivial diagrams score high
  fidelity at any maturity), so the control should recover signal, not
  destroy it.
- **D2 (generator robustness):** the below-composite-40 cliff reproduces
  under a weaker generator (`claude-haiku-4-5`), plausibly with a larger
  drop — a weaker generator has less capacity to compensate for diagram
  flaws.
- **D3 (judge robustness):** a second judge (`claude-haiku-4-5`) re-scoring
  the same artifacts agrees on the *ranking* (fidelity correlation between
  judges substantial, r ≥ 0.5) even if its absolute fidelity scale is
  offset; the composite↔fidelity correlation survives the judge swap.

## Deepening — waves and results (2026-07-24)

Three waves, 243 runs, zero failures, $10.19 total; a third scenario family
(`insurance_claim`, L5→L1 via the corpus mutation ladder) joined the pool:

| Wave | Gen | Judge | Diagrams | Runs | Cost |
|---|---|---|---|---|---|
| main2 | opus-4-8 | sonnet-5 | 31 (incl. insurance family) | 93 | $7.38 |
| rejudge | opus-4-8 (main2 artifacts) | **haiku-4-5** | 31 | 93 | $0.40 |
| gen-haiku | **haiku-4-5** | sonnet-5 | 19 | 57 | $2.41 |

**Replication first:** main2 independently reproduces the original result —
raw r = 0.414 (was 0.489), cliff 60.8 vs 73.5 (was 59.2 vs 75.1), identical
level ordering with the same synthetic-L3 outlier.

**D1 — confirmed, and it is the headline.** Controlling for *hard demand*
(guards + failure paths expected) the per-diagram partial correlation lands
in a tight band across every wave — **0.66 / 0.70 / 0.65 / 0.68** (original,
main2, haiku-gen, haiku-judge) — versus raw per-diagram r of 0.54 / 0.46 /
0.22 / 0.58. The synthetic-triviality confound was *suppressing* the true
relationship; held at fixed semantic difficulty, maturity predicts fidelity
at r ≈ 0.65–0.70 regardless of which generator wrote the code or which judge
scored it. (Controlling for *total* demand instead weakens r to ~0.3 — total
obligation count co-varies with maturity in this corpus, so the two controls
bracket the raw number; hard demand is the semantically defensible control
and the one pre-registered.)

**D2 — confirmed.** Under the weaker generator the cliff reproduces and
steepens: below composite 40 fidelity is 56.6 vs 72.1 above (opus: 60.8 vs
73.5), and the level gradient excluding the synthetic bucket is cleanly
monotone (70.2 / 64.3 / 63.2 / 56.6). The weak generator's raw r (0.203) is
dominated by the synthetic outlier in a 19-diagram sample; the hard-demand
partial recovers 0.554. A weaker generator compensates less, so low-maturity
diagrams cost *more* — the gate matters more, not less, for cheaper models.

**D3 — confirmed.** Over the same 93 artifacts the two judges' fidelity
scores correlate at r = 0.715 with a nearly constant offset — haiku scores
~9 points more leniently (means 79.2 vs 70.2, mean |diff| 10.5) — and the
composite↔fidelity correlation is essentially unchanged under the swap
(0.490 haiku vs 0.414 sonnet; per-diagram 0.58 vs 0.46). Absolute fidelity
is judge-relative; rankings and correlations are not.

**Larger n:** pooling the two identical-config waves gives 168 runs over 38
diagrams, 18 of them at n = 6 (per-diagram means tightened from ±8 toward
±5); pooled per-diagram r = 0.472, hard-demand partial 0.619 — consistent
with the per-wave numbers.

Analysis: `tools/analyze_evidence.py` → `experiment_results/analysis.json`;
wave reports under `experiment_results/wave_*/report.json` (the original
`experiment_results/report.json` is unchanged).

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

Addressed by the 2026-07-24 deepening: complexity normalization (hard-demand
partial correlations), a third scenario family (insurance_claim), n = 6 on
the 18 diagrams shared across identical-config waves, and a second generator
plus a second judge (haiku-4-5), all reproducing the findings.

Still standing: all models are Claude-family (no cross-vendor generator or
judge); the generation prompt is fixed (one prompting style); the judge
rubric, while schema-constrained, is still an LLM judgment — absolute
fidelity numbers are judge-relative (~±10 between judges) and only rankings
and correlations should be quoted.

## What the product may claim

Supported by this data (updated after the deepening):

- *"Maturity scores correlate with the fidelity of generated code — raw
  r ≈ 0.4–0.5 across replications; at fixed semantic difficulty (guards and
  failure paths held constant) the per-diagram correlation is **r ≈ 0.65–0.70,
  stable across two generators and two judges**."*
- *"Diagrams below Level 2 measurably degrade generation: fidelity drops by
  roughly a third and invented business logic roughly doubles."* The cliff
  reproduced in every wave, and is **steeper for a weaker generator** —
  the gate matters more, not less, for cheaper models.
- The `--min-level` CI gate is evidence-backed **as a risk filter**: its
  demonstrated value is keeping low-maturity diagrams out, which is exactly
  what a CI gate is for.
- Quote correlations and the cliff, never absolute fidelity values —
  absolute fidelity is judge-relative (two judges differ by ~9 points on
  identical code while agreeing on ranking, r = 0.715).

**Not supported:** "Level 5 ⇒ generation-ready" as an absolute. Under a
strict independent judge, even pristine L5 diagrams average ~72 fidelity
with ~3 judge-flagged inventions per run — a sequence diagram underdetermines
an implementation, and the generator fills the gap by design. Level 5 should
continue to be described as **"method-convention complete — the diagram-side
preconditions for faithful generation"**, with the cliff finding as the
quantified payoff.
