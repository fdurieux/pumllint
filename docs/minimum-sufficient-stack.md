# The measured minimum sufficient specification stack

*Dated consolidation record, 2026-08-11 — verified revision: draft
b3bf80c (findings-before-verdicts), independent adversarial pass
against it — **9 findings: 4 major, 5 minor, all adopted in this
revision** (the pass recomputed every table from the raw analyses,
not only from the Results prose). This is the document the research
charter
([research-charter.md](research-charter.md)) converges on: the
measured answer to "which artifacts, which level of detail, which
syntax" for the model→code hop, consolidated from the five frozen
wave records (stack_experiment/W1–W5_PREREGISTRATION.md § Results,
2026-08-10/11, ≈$32.65 total) and the standing pre-charter evidence
(EVIDENCE.md; the C4 ladder; the agent-repair waves). Every number
here traces to a frozen record; nothing is new measurement. House
discipline: this document is revised in place, dated, as later waves
land, and it quotes gaps and orderings, never absolute rates as
portable facts — the absolutes below are suite-relative and appear
only to make the gaps legible. It changes no product behavior and
queues no build.*

## The answer in one paragraph

For the model→code hop, on this lab's systems, with this model
generation (dated): the minimum sufficient stack is **a task brief,
the structure skeleton, one behavior artifact, and a written decision
contract** — the ladder's +contract rung, structure present at every
measured rung — for a strong generator that is the knee of the curve
(adding acceptance
examples moved it nothing it could not already do), while a weak
generator additionally needs **acceptance examples as input** to
reach its plateau and is the only one that pays for excess. Structure
alone is orientation, not outcome. The carrier of the behavior
artifact matters — the measured ordering puts the PlantUML sequence
diagram first — and no amount of prose, enumeration or padding past
the knee buys anything: for the weak generator it actively destroys
(−26 to −32 pp). None of this is rescued or invalidated by a
test-running agentic loop at k ≤ 2: iteration repairs only what
visible tests state, hidden decision points keep material gaps, and
a below-cliff artifact is not repaired at all. Keep every decision
stated exactly once, gate the inputs, and stop writing at the knee.

## 1. Which artifacts — the measured portfolio

Single-shot executed ladder on the adversarial-threshold system
(CargoQuote, pooled over two generators, n = 6–10 per arm; W1):

| Rung | Pooled executed | Increment | Leave-one-out drop |
|---|---|---|---|
| brief | 0.136 | — | — |
| + structure | 0.121 | −1.5 pp | 5.2 pp |
| + behavior | 0.439 | **+31.8 pp** | 11.8 pp |
| + contract | 0.818 | **+37.9 pp** | **55.2 pp** |
| + tests (full) | 0.945 | +12.7 pp | 12.7 pp |

- **The written decision contract is the load-bearing artifact**
  wherever decisions are idiosyncratic: the largest additive
  increment, the largest removal drop of the program, and the
  artifact that cuts judged invention (medians 6→3 and 5→3 at its
  arrival; the C4 wave's R3→R4 mean 6.00→4.00 agrees). W1 closed
  the C4 wave's canonical-threshold confound: the earlier "0.0 pp
  executed" for companion specs was the generator guessing guessable
  values, not contract worthlessness. *Dated addition, 2026-08-11
  (W1b, the contract-bundle decomposition):* within the four-file
  bundle, **the decision tables are the component that carries it**
  — +40.9 pp pooled added alone over A2 (largest of the four, both
  generators concordant), the only component whose removal hurt
  (+12.1 pp), with the gains/losses concentrated in the DT-numeric
  scenario sets and the judged invention cut localizing to them
  (5→3 / 4→2). The OpenAPI schema mirror held the validation bounds
  at exactly 0.0 loss when the tables left (sanctioned redundancy is
  a real fallback carrier), while removing each OTHER component —
  companion prose, OpenAPI, state model — IMPROVED pooled results by
  10.6–21.2 pp on this occasion (states haiku-borne, −36.4 pp;
  A2+tables alone scored 0.818 pooled, equal to W1's stored full
  bundle): in-bundle excess carriage, the dilution result's sharpest
  in-stack form, and the executed citation for one-source-per-
  decision (E5: component marginals are subadditive — haiku-borne).
  Scoping that travels with every quote: attribution is
  suite-relative (the suite's normative source is decision_table.md;
  5/11 scenarios grade DT-only numerics), single-shot, one system,
  dated. Record: stack_experiment/W1B_PREREGISTRATION.md § Results.
- **The behavior artifact is material everywhere but system-relative
  in rank:** +31.8 pp here, +29.2 pp when dynamics arrived in the C4
  ladder, and the 16–25 pp below-cliff penalty within the sequence
  family (three generators, two vendors) — but the pre-registered
  "single biggest lever" claim FAILED on the adversarial system
  (the contract led), and the two generators disagree about which
  of the two matters more. Portfolio claims are quoted
  per-generator (charter §8.3, partially fired).
- **Acceptance examples as generation input carry real,
  leakage-controlled value:** +12.7 pp pooled with ~98% of the net
  gain on scenarios the examples do not give away — and they are
  the weak generator's biggest per-token lever (+40.6 pp/ktok,
  vs its +29.1 pp on this rung while the strong generator sat at
  ceiling).
- **Structure alone is orientation, not outcome:** −1.5 pp additive,
  the smallest removal drop (5.2 pp), consistent with the C4
  finding that edge recall is perfect from the bare container
  diagram. It earns its place for misread-prevention and as the
  skeleton the conforming prompt pins classes to — not as an
  executed-correctness lever.
- **The decision/Q&A record** (pre-charter: ≈ +27 pp executed vs
  inventing without an author, ≈ +21.5 pp vs the untouched diagram —
  the latter is the decision-relevant contrast for adding the
  record) remains the one artifact class no wave re-measured; its
  standing evidence is unchanged.

## 2. Which level of detail — the knee, and the far side

Three tiers plus a fourth clause, all measured:

1. **Below the cliff** (a degraded behavior artifact): 16–25 pp
   executed penalty, scaffold-resistant, and — W5 — not repaired by
   test-driven iteration at k ≤ 2 (identical rates to single-shot;
   its own smoke tests still failing after two revisions).
2. **From arrival to the knee:** behavior and contract arrivals
   carry the curve (+31.8, +37.9 pp).
3. **The knee:** pooled at the full stack; **per-generator — the
   strong generator's knee is the +contract rung, i.e. brief +
   structure + behavior + contract** (1.000 there; acceptance
   examples added −3.6 pp at its ceiling), **the weak generator's
   knee is the full stack including the examples** (0.636 → 0.927).
   No structure-less bundle was measured anywhere in the program.
4. **Past the knee, detail is at best free and at worst toxic**
   (W4): accurate redundant restatement −6.7 pp pooled, irrelevant
   context −11.2, accurate exhaustive enumeration −14.3 — and the
   damage is entirely the weak generator's (−10.9 / −26.1 /
   −32.1 pp) while the strong generator held its ceiling.
   Redundancy does not need to be wrong to hurt; the pre-registered
   guess that irrelevant padding would be the worst diluter was
   itself wrong — accurate enumeration was worse. Dose bound: all
   measured at ≤ 1.45× full-stack size.

## 3. Which syntax — the carrier is not free

At fixed, audited information, one behavior artifact rendered five
ways (W3, A2 rung, vs the PlantUML baseline):

| Carrier | Pooled Δ | Flow-sensitive Δ |
|---|---|---|
| PlantUML sequence | — | — |
| code-stub skeleton | −6.1 pp | −16.7 pp |
| Mermaid sequence | −9.1 pp | −20.0 pp |
| controlled English | −15.2 pp | −33.3 pp |
| structured YAML | −30.3 pp | −66.7 pp |

Carrier equivalence was REFUTED: every alternative lost on the
flow-sensitive scenarios, YAML lost even on semantic-only scoring,
and the strong generator produced non-compiling code from YAML in
3 of 3 runs — the only non-compiles of the single-shot W1–W4
program (W5's loop saw one intermediate non-compile, repaired by
compile feedback; zero non-compiling finals). Checkability is
therefore demoted to one carrier criterion among several (the
charter's own pre-commitment); the carrier question is decided on
outcome evidence, and on the only outcome evidence anywhere, the
diagram notations lead the data/prose renderings, with PlantUML
ahead of Mermaid by 9 pp pooled / 20 pp flow-sensitive in this
lab's single measurement. Capability-relative; re-measured per
model generation.

*Dated decomposition, 2026-08-11 (W3b, carrier × prompt-frame, all
14 cells in-wave, $13.72 —
[record](../stack_experiment/W3B_PREREGISTRATION.md)): the table
above is partly a harness-frame result, per-carrier. Under the
frozen PlantUML-typed frame the W3 ordering reproduced exactly
(anchor delta 0.0); under a format-silent frame it collapsed
(Mermaid ≥ PlantUML ≈ controlled English, code-stub last via a
generator output-contract failure). Licensed re-scopings: **YAML's
deficit is intrinsic** — it persists under aligned, silent and
native frames alike, and opus's 0/3 non-compiles reproduced and
extend to the yaml-native frame; **controlled English's deficit is
scoped to the PlantUML-framed harness** — its own cells are
frame-flat and the gap closes because the baseline loses its
aligned-frame advantage. Code-stub's and Mermaid's stored-frame
deficits did not reproduce beyond the equivalence bar on this
second occasion (no re-scoping licensed; the sentence above now
carries that non-reproduction note). Two surprises, published at
full prominence: **prompt-carrier alignment measurably hurt** —
naming the carrier's actual format cost −10.6 to −18.2 pp pooled on
three of four carriers (opus collapses into non-code fragments
under unfamiliar frames; haiku compiles fine but executes worse) —
so frame wording is a real lever with a treacherous sign, not
hygiene; and **the stored-frame carrier ordering is opus-borne** —
haiku is near-flat across carriers under the stored frame
(0.394–0.424 pooled), so every carrier claim here is per-generator
(§8.3 discipline extended to the frame axis).*

## 4. One source per decision — conflicts and redundancy

- W2: injected contradictions were **never surfaced** — 0 of 18
  runs said anything; silent resolution is total, which is the
  measured backing for "stop-and-ask must be harness-enforced"
  (agents.md carries the dated citation). The resolutions mostly
  favored the right sources — decision table over stale prose 6/6,
  five-source majority over a stale sentence 5/6, formula over a
  stale worked example 12/12 slots — and damage stayed local.
- W1's below-cliff-vs-absent arm: an exact null, unresolved and
  underpowered — prose flow was present in both arms, so it
  measured artifact absence within a redundant stack, not
  information erasure, and **no direction is supported** (the
  frozen branch's own words). The W4 dilution evidence therefore
  carries the guidance alone: **one authoritative carrier per
  decision; deliberate redundancy is a cost and, for weak
  generators, a measured risk — not a safety net you can bank
  on.**

## 5. The workflow transfer — it all survives agency

W5, the external-validity keystone (k ≤ 2 test-driven iteration,
visible smoke subset, hidden grading): the cliff (+31.3 pp), the C4
behavior-arrival gap (+46.7 pp) and the contract lever (+54.2 pp)
all survived on hidden scenarios; charter §8.4 did not fire.
Compensation was strictly visible-bounded — the clearest case took
its smoke set to the ceiling while its hidden set moved 0.0 pp —
and judged invention on uncovered behavior persisted. Standing
claims are worded "single-shot and k ≤ 2 agentic"; deeper
tool-using iteration is the recorded residual risk.

## 6. What this does not say

One invented system per substrate, toy scale, n = 3–5 per
generator-arm; two generators, one vendor (cross-vendor robustness
is measured for the cliff only); single-shot plus k ≤ 2 agency —
not long-horizon harnesses; judged numbers are judgments, never
merged with executed ones; every carrier and generator claim decays
per model generation and re-measures on the standing instrument;
suite-relative absolutes are not portable. The prose→model,
maintenance, and spec→tests hops are unmeasured here (W6/W7 remain
gated); deployment/operations remain position-paper territory.

## 7. Product consequences (wording only; every build stays gated)

- **Claim language** already updated in place, dated: charter §§2,
  4, 5, 6, 7, 8; agents.md precedence section; "single-shot and
  k ≤ 2 agentic" scope program-wide.
- **Rule-pack rationale:** contract-presence conventions now have
  outcome grounding; the codegen profile's gate-first posture has
  its strongest citation yet (below-cliff artifacts resist even
  test-driven repair). No rule ships from this — demand gates
  unchanged.
- **Pilot-facing sentences** (for the census conversation, dated
  and suite-relative): the written decision contract is the
  highest-value artifact to require **for a strong generator and in
  the pooled and leave-one-out views — the weak generator's largest
  single-shot additive lever was the behavior artifact, so quote
  per-generator (W1-E8a's standing rule)**; PlantUML is defensible on
  outcome evidence, not just tooling; a stale example or sentence
  will be silently resolved, so gate and deduplicate sources;
  don't mandate detail past the knee — over-specification harms
  the cheaper models an adopter will actually run at scale.
- **The falsifier ledger, for honesty at a glance:** §8.1 open
  (external-evidence-gated; the lab contrast was an unresolved
  null); §8.2 did not fire (dilution measured); §8.3 partially
  fired (per-generator claims, generator axis); §8.4 did not fire
  (cliff survives agency); §8.5 not triggered (knees landed as
  pre-registered). The verdict tally, counted by the records' own
  labels (guards excluded; W1-E8b exploratory and W1-E5's null as
  their own categories): **five FAILED** (W1 E1/E4/E8a, W3 E1/E2),
  **two not-confirmed branches** (W2-E4, W5-E1), **one unresolved
  null** (W1-E5), and **eighteen CONFIRMED** — every failure
  published in its wave record with the same prominence as the
  confirmations.

## Records

W1–W5: stack_experiment/W*_PREREGISTRATION.md § Results (frozen
pre-registrations with adversarial-pass provenance; raw runs and
analyses under stack_experiment/results/). Pre-charter evidence:
EVIDENCE.md, docs/c4-codegen-detail-experiment.md,
docs/evidence-explained.md. Frame: docs/research-charter.md
(§§ updated in place, dated).
