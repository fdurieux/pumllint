# Does the maturity score predict codegen outcome?

*No-background-assumed walkthrough of this file's program and findings:
[docs/evidence-explained.md](docs/evidence-explained.md).*

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

## Execution oracle — pre-registered expectations (written 2026-07-26, before any scored run)

Everything above measures fidelity through an LLM judge. This wave adds the
harder oracle the code-eval literature trusts: **execution against
hand-written acceptance tests**. One suite per scenario family, derived from
the pristine diagram — degraded variants describe the *same intended
system* (degradation removes information; it does not change what the
system is supposed to do), so one suite scores code generated from every
variant of its family. The hypothesis: code generated from degraded
diagrams fails more of the intended behavior *when actually run*, because
where the diagram went vague the generator guessed, and wrong guesses
produce observably wrong outcomes.

**Setup** (normative detail in `tools/acceptance/runner_child.py`'s
docstring and `tools/acceptance/suites.py`): 12 scenarios —
order_payment 4 (happy, not-found, payment-error-with-compensation,
zero-total), insurance_claim 5 (happy, policy-lapsed, risk-service-error,
over-coverage-limit, storage-error), credit_intake 3 (flow-shape only: the
accept/reject threshold is unspecified even in the pristine diagram, so
branch direction cannot be asserted). Each (artifact, scenario) runs in a
sandboxed child process (`python -I`, sockets disabled, stdin closed, 15 s
timeout). Guard-else branches the diagram leaves underspecified
(zero_total, over_coverage_limit) assert only the interaction contract
(charge/store must not happen) with the outcome unconstrained. Synthetic
and wild diagrams have no ground truth and are excluded. **Unrunnable is a
failed scenario** — but every failure carries a stage
(import_error / no_entry / construct_error / crash / timeout /
wrong_outcome / missing_call / forbidden_call), and two metrics are
reported: **full pass-rate** (primary — all stages count) and
**semantic-only pass-rate** (secondary — conditioned on the adapter stages
succeeding), so adapter artifacts stay visible instead of hiding in the
signal.

**Calibration protocol (executed before this freeze):** the adapter and
suites were developed against the nine pristine-example artifacts only
(`L5_order_payment_codegen_good`, `L5_insurance_claim_good`,
`L2_credit_intake_good` × 3 runs, wave main2). Three adapter bugs were
found and fixed (sys.modules registration for dataclass artifacts;
score-ranked constructor matching so `order_db` resolves to `OrderDB`, not
`Order`; builtin exception type names excluded from outcome
classification) and two suite arg bugs (protean customer objects; the
over-limit scenario overriding every amount carrier). Final calibration:
**36/36** (`execution_results/calib/execution.json`). No degraded
artifact was executed before this freeze.

**Expectations:**

- **X1 (gradient):** per-run execution pass-rate increases with maturity
  level within each realistic family; composite↔pass-rate correlation is
  positive (pooled and per-diagram).
- **X2 (cliff):** below composite ~40 the mean pass-rate is at least
  10 pp lower than above it — the judged-fidelity cliff reproduces under
  execution.
- **X3 (judge audit):** per-run judged fidelity correlates with executed
  pass-rate at r ≥ 0.4 over the family artifacts (wave main2). If this
  fails, the prior waves' fidelity signal is in question and the write-up
  must say so.
- **X4 (adapter honesty):** X1's sign holds on the semantic-only pass-rate
  as well — the gradient must not be an artifact of runnability stages.
- **XB (Phase B, prompt variation):** with the entry point pinned
  (`handle(request)`) and under both prompt variants (V1 keeps the
  class-per-participant scaffold, V2 drops it), X1's sign reproduces.
  Pinning is scaffolding, so the good–bad gap may compress — the
  pre-registered claim is the sign, not the magnitude.

Absolute pass-rates are **suite-relative** (the analogue of judge-relative
fidelity): quote gradients and correlations, never bare percentages, and
never compare across families. Phase A costs $0 (stored artifacts only);
Phase B regenerates family diagrams with the pinned prompt (~$8/variant).

## Execution oracle — Phase A results (2026-07-26, stored artifacts, $0 API)

756 scenario runs over 148 family artifacts from the three stored waves
(original 228, main2 336, gen_haiku 192), zero harness errors; analysis in
`tools/analyze_execution.py` → `execution_results/analysis.json`. Pooled
identical-config (original + main2, opus generation) per-level pass-rate:

| Level | Diagrams | Artifact runs | Executed pass-rate |
|---|---|---|---|
| 5 | 8 | 24 | 0.949 |
| 4 | 4 | 12 | 0.910 |
| 2 | 13 | 39 | 0.756 |
| 1 | 9 | 27 | 0.642 |

(The families have no L3 diagrams — the L3 bucket was the synthetic set,
which has no suite by design.)

**X1 — confirmed in the identical-config waves.** The gradient is monotone
in both opus waves and pooled; composite↔pass-rate per-diagram r = 0.545
pooled (0.371 / 0.510 per wave), per-run r = 0.411. Under gen_haiku the
full-rate correlation stays positive (per-diagram 0.374) but the level
table is non-monotone at the top — 4 diagrams per level is thin.

**X2 — confirmed in every wave.** The cliff survives the oracle swap:
pass-rate below composite 40 vs above is 15.9 pp (original), 25.4 pp
(main2), 19.7 pp (gen_haiku), 21.9 pp pooled (0.642 vs 0.861). Below the
cliff roughly one intended behavior in three fails when the code runs;
above it, roughly one in ten.

**X3 — FAILED.** Per-run r(judged fidelity, executed pass-rate) = 0.185 /
0.328 / −0.002 (original / main2 / gen_haiku), 0.25 pooled — all below the
pre-registered 0.4. A post-hoc check at diagram granularity is no better
(0.351 / 0.347 / −0.035). Stated plainly: **judged fidelity is not a proxy
for executed correctness** at artifact granularity. Both oracles
independently show the maturity gradient and the cliff — the product-level
relationship is oracle-robust — but they disagree on individual artifacts,
so the two must always be quoted separately, and prior waves' fidelity
numbers are structural-faithfulness judgments, not correctness
measurements.

**X4 — confirmed where it matters, failed under gen_haiku.** In the
identical-config waves every failure was semantic (adapter stages ≈ 0), so
the semantic-only correlation is identical (0.545) by construction. Under
gen_haiku the semantic-only per-diagram r collapses to −0.027: haiku's
low-maturity brokenness concentrates in import failures (both
import_errors are runs of one L1 diagram), which the pre-registered
taxonomy conservatively classes as adapter stages even though
does-not-import is arguably the strongest behavioral failure there is.
The 16-diagram haiku sample carries little weight either way; the
identical-config result is the load-bearing one.

**Post-hoc observation (not pre-registered):** the hard-demand partial is
≈ 0 for execution (0.081 pooled) — in hindsight, expected: D1's
triviality confound does not exist under a fixed family suite, because a
degraded diagram faces the *same tests* as its pristine sibling; there is
no easier-oracle-for-easier-diagrams effect to control away. The raw
per-diagram r is the right execution statistic.

## Execution oracle — Phase B results (2026-07-26, fresh waves, $15.03)

Two fresh opus-4-8 waves over the 28 family diagrams (3 runs each, sonnet-5
judge kept), generation prompt pinned to the `handle(request)` entry
contract: **V1 pinned_structured** keeps the class-per-participant scaffold
($6.77, 167/168 runs — one judge-response parse error, logged in the wave
report), **V2 pinned_minimal** drops it ($8.26, 168/168). Pre-generation
amendment, committed before any artifact existed (4de71b6): the suites'
request dicts gained synonym keys so classless artifacts are not penalized
for key-name guesses — stubs, expectations and outcome rules untouched.

| Executed pass-rate | L5 | L4 | L2 | L1 | cliff@40 | per-diagram r |
|---|---|---|---|---|---|---|
| legacy prompt (pooled A) | 0.949 | 0.910 | 0.756 | 0.642 | 21.9 pp | 0.545 |
| V1 pinned_structured | 0.963 | 0.959 | 0.946 | 0.762 | 19.4 pp | 0.334 |
| V2 pinned_minimal | 0.963 | 0.981 | 0.935 | 0.714 | 24.3 pp | 0.490 |

**XB — confirmed.** Under both prompt variants the gradient's sign
reproduces (positive per-diagram correlation; L1 clearly lowest; V2's
L4/L5 inversion is 0.02 at n = 4 diagrams) and the cliff clears the 10 pp
bar in both (19.4 / 24.3 pp). The judged oracle agrees: fidelity gradients
66.2/66.3/64.4/**51.2** (V1) and 63.6/65.7/61.6/**47.1** (V2), composite↔
fidelity r = 0.604 / 0.635 — so the maturity→outcome relationship now
stands across **three prompt styles, two oracles, and two generators**.

**The pre-registered compression happened — but only above the cliff.**
Pinning the entry contract lifted moderately degraded diagrams almost to
pristine level (L2: 0.756 legacy → 0.946/0.935 pinned) while below-cliff
diagrams barely moved (L1: 0.642 → 0.762/0.714). Read plainly:
**scaffolding rescues diagrams with moderate hygiene findings; it does not
rescue diagrams below the cliff** — their missing guards and failure paths
stay missing no matter how the generator is prompted. This narrows the
per-diagram correlation above the cliff (hence V1's r = 0.334) and is
precisely the compression the pre-registration anticipated; the cliff, not
the slope, remains the robust product claim.

**Post-hoc:** judge↔execution per-run agreement rises under the pinned
contract (r = 0.390 / 0.415 vs 0.25 legacy) — a standardized entry point
appears to remove some measurement noise — but stays at the X3 threshold:
the oracles remain complementary, not interchangeable.

## Cross-vendor wave — pre-registered expectations (written 2026-07-26, before any scored run)

Every number above comes from Claude-family models on both sides of the
experiment. This committed follow-up (ROADMAP Arc D) swaps the vendor on
each side in turn:

- **Generator wave:** `gemini-3.1-pro-preview` generates the 28 family
  diagrams — legacy prompt, 3 runs, sonnet-5 judge; identical to wave
  main2's family subset except the generator vendor. Model-choice caveat,
  recorded up front: Google has retired `gemini-2.5-pro` (the stable
  pro-class SKU) for new API keys, so the strongest model available to
  this key is a *preview* SKU — the exact id and date are recorded here
  because preview models are not a stable reproduction target.
- **Judge wave:** the same Gemini model re-judges wave main2's stored
  artifacts (judge-only cost) — the cross-vendor mirror of D3.
- **Execution oracle** over the Gemini-generated artifacts — the
  vendor-neutral leg: no LLM of any vendor is in that scoring loop.
- Harness: stdlib REST shim (`_gemini_call`), thinking tokens billed and
  counted as output; smoke-tested on trivial calls only (~$0.005) before
  this freeze. Cost guard unchanged ($25); estimate ≈ $12.

**Expectations:**

- **XV1 (generator, judged):** composite↔fidelity correlation positive
  under the Gemini generator; the below-composite-40 cliff reproduces in
  direction with a judged-fidelity gap ≥ 8 points (precedent: opus 12.7,
  haiku 15.5).
- **XV2 (generator, executed):** X1/X2 signs hold on the Gemini
  artifacts — positive per-diagram composite↔pass-rate correlation and a
  cliff@40 gap ≥ 10 pp. This is the load-bearing cross-vendor claim.
- **XV3 (judge):** Gemini re-judging main2's artifacts agrees with
  sonnet-5 on ranking — between-judge per-run fidelity correlation
  r ≥ 0.5 (the D3 bar; sonnet↔haiku was 0.715). Absolute offset
  unconstrained, as before.

Absolute fidelity and pass-rate numbers are not comparable across
vendors; only signs, gaps and correlations are claimed. No bar is set on
per-run judged-vs-executed agreement (X3 precedent: expected weak).

## Cross-vendor wave — results (2026-07-26, $8.66)

Generator wave $6.20 (167/168 runs — one sonnet judge response
unterminated, logged and excluded), rejudge $2.46 (93/93).

**XV2 — confirmed, and it is the cross-vendor headline.** On the
execution oracle — the leg with no LLM of any vendor in the scoring
loop — the Gemini-generated artifacts show the same cliff as every
Claude wave: executed pass-rate 0.643 below composite 40 vs 0.852 above,
a **20.9 pp gap** (bar ≥ 10; opus pooled was 21.9), per-diagram
composite↔pass-rate r = 0.354 with the level gradient in the expected
order (0.932 / 0.963 / 0.699 / 0.643). The below-Level-2 cliff is now
demonstrated for **three generators across two vendors**, on the oracle
that measures behavior rather than opinion.

**XV1 — FAILED.** The sonnet-5 judge saw almost none of it: judged
fidelity is nearly flat across levels (66.7 / 66.9 / 66.5 / 63.4),
below-vs-above-40 gap **3.2 points** (bar ≥ 8), composite↔fidelity
r = 0.133. The execution result rules out the charitable reading (a
generator so strong the cliff vanished — it didn't; the executed cliff
is fully present). What failed is the *judge on cross-vendor code*:
per-run judged-fidelity↔executed-pass-rate agreement on the Gemini
artifacts is **r = 0.002 — zero**. Sonnet judging opus code tracked
execution weakly (r ≈ 0.25); sonnet judging Gemini code does not track
it at all. LLM-judged fidelity degrades across the vendor boundary,
plausibly because the judge's structural rubric is calibrated to the
generation idiom it knows.

**XV3 — confirmed.** Gemini re-judging main2's stored (opus-written)
artifacts agrees with sonnet-5 on ranking: between-judge per-run
r = **0.682** (bar ≥ 0.5; sonnet↔haiku was 0.715), with a large leniency
offset (means 89.5 vs 70.2, mean |diff| 19.4 — twice haiku's). Under the
Gemini judge the composite↔fidelity correlation is 0.572 — the maturity
relationship survives a cross-vendor judge swap.

**The uncomfortable synthesis, stated plainly:** the two judges agree
with each other (0.682) far better than either agrees with what the code
actually does when run (0.25 same-vendor, 0.002 cross-vendor).
**Inter-judge reliability is not validity.** The maturity→outcome claims
survive because the execution oracle carries them; the judged numbers
remain useful for ranking and for the invention taxonomy, and are quoted
strictly as judgments.

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

Resolved 2026-07-26: the fixed-prompt limitation (gradient and cliff
reproduce across three prompt styles) and the Claude-family-only
limitation (the executed cliff reproduces under a Gemini generator —
20.9 pp — and the maturity↔fidelity ranking survives a Gemini judge).
Cross-vendor scope is honest but narrow: one non-Claude model
(`gemini-3.1-pro-preview`, a preview SKU — Google had retired the stable
pro model for new API keys at run time), one vendor.

Still standing: the judge rubric is an LLM judgment — absolute fidelity
is judge-relative (offsets of ~9 points between Claude judges, ~19
between vendors), and **judged fidelity must never be treated as
correctness**: its per-run agreement with execution is weak same-vendor
(r ≈ 0.25) and zero on cross-vendor code (r = 0.002), even though judges
agree with each other on ranking (0.68–0.72) — reliability without
validity. Execution pass-rates are suite-relative (three families, 12
hand-written scenarios). Quote rankings, gaps and correlations; never
absolute numbers, and never one oracle as a stand-in for the other.

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
- *(2026-07-26, execution oracle)* — *"The cliff is not a judge artifact:
  under hand-written acceptance tests actually executed against the
  generated code (frozen, pre-registered suites), diagrams below the cliff
  lose ~16–25 pp of executed pass-rate (21.9 pp pooled across the opus
  waves) — roughly one intended behavior in three failing when the code
  runs, versus one in ten above the cliff. The cliff reproduces across
  three prompt styles and is scaffold-resistant: pinning an entry contract
  lifts moderately degraded diagrams (L2 ≈ pristine under pinning) but
  does not rescue below-cliff diagrams — prompt engineering cannot restore
  guards and failure paths the diagram never specified."*
- *(2026-07-26, cross-vendor)* — *"The executed cliff is vendor-robust:
  under a Gemini generator it is 20.9 pp — the same magnitude as under
  Claude generators (16–25 pp) — so the below-Level-2 gate is not a
  one-vendor artifact. Three generators, two vendors, one behavioral
  oracle."*
- Quote correlations and the cliff, never absolute fidelity values —
  absolute fidelity is judge-relative (two judges differ by ~9 points on
  identical code while agreeing on ranking, r = 0.715). Executed
  pass-rates are likewise suite-relative. **Never merge the two oracles
  into one number**: their per-run agreement is weak (r ≈ 0.2–0.3, the
  pre-registered X3 threshold failed) — judged fidelity measures
  structural faithfulness, execution measures behavioral correctness, and
  each must be quoted as what it is.

**Not supported:** "Level 5 ⇒ generation-ready" as an absolute. Under a
strict independent judge, even pristine L5 diagrams average ~72 fidelity
with ~3 judge-flagged inventions per run — a sequence diagram underdetermines
an implementation, and the generator fills the gap by design. Level 5 should
continue to be described as **"method-convention complete — the diagram-side
preconditions for faithful generation"**, with the cliff finding as the
quantified payoff.
