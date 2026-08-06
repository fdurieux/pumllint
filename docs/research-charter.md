# Research charter — the minimum sufficient specification stack

*Dated reframing record, 2026-08-06. This document performs the reframing
of the research objective for this project — from "maximise the
effectiveness of an end-to-end AI-assisted software delivery lifecycle"
to a form that can be measured, falsified, and re-measured. It restates
the objective, defines its terms, maps it onto the evidence this
repository already holds, sketches the wave program that answers what
remains open, and records what would falsify the frame itself. House
discipline applies to this charter as it does to externally authored
recommendations: it receives an adversarial verification pass before
acceptance (§9 — running at the time of this draft's commit), and no
wave runs from this charter alone — every wave freezes its own
pre-registration and interpretation matrix before any scored run.
Status: draft for owner review on the research-planning branch;
unverified until §9 carries the pass's actual findings.*

## 1. The objective as posed

> Determine which artifacts are needed, which level of detail, which
> syntax, in order to maximise the effectiveness of an end-to-end
> AI-assisted software delivery lifecycle.

The question is real, timely, and externally corroborated — DORA 2026
names the "verification tax" as the most immediate barrier to AI ROI;
SWE-bench Verified found 38.3% of real issue descriptions
underspecified; SpecFix gained +30.9% Pass@1 by repairing task
descriptions; the spec-driven-development wave has made specification
quality the bottleneck. It is also the natural next stratum of this
repository's evidence program, which has so far measured quality *within*
one artifact class (the sequence maturity→outcome relationship) and
detail *within* one artifact family (the C4 ladder). But as literally
posed the objective cannot be run.

## 2. Why it cannot run as posed

Three framing errors (E1–E3) and two method corrections (C1–C2), each
grounded in this repository's own measurements:

**E1 — "maximise" has no oracle.** The C4 detail ladder measured a
plateau (R4−R3 = 0.0 pp executed on the canonical-threshold suite) and a
floor: no rung is hallucination-free — ≈ 4 judged inventions/run at full
SDD-grade companion-spec detail, ≈ 3.2/run even at pristine sequence L5
(a diagram underdetermines an implementation by design). The far side —
over-specification: context dilution, redundant restatement drifting
stale, conflicting sources — is unmeasured and plausibly net-negative:
the repair waves measured what happens when wrong content enters an
authoritative artifact (one invented guard took a near-pristine executor
from 0.93 to 0.40). A maximisation target also structurally pressures
any gate calibrated to it toward rule-count creep — demanding ever more
detail — against this project's dormant-by-default philosophy.
Correction: the target is **minimum sufficiency** — the knee of the
dose–response curve, with the far side measured (W4), never assumed
monotone.

**E2 — "end-to-end" is not one measurable thing.** Effectiveness is
measurable per *hop*, and only where an oracle can be constructed. The
design→code hop is built (frozen acceptance suites, sandboxed
execution). The prose→model hop is specified (ROADMAP Arc J, gated).
The maintenance hop is constructible but unbuilt. Deployment and
operations have no lab oracle at all — that territory can only be an
evidence-annotated engineering position (the sdlc-tooling-landscape
discipline), and this charter says so instead of claiming it.
Correction: the hop map in §5 scopes every claim.

**E3 — "which artifacts" confounds genre with information.** This
repository's recorded sharpening of the external spec-stack
recommendation: *constraint-grade vs orientation-grade is a maturity
level, not an artifact genre*. The sequence evidence puts ~21.9 pp of
executed correctness between constraint-grade and orientation-grade
diagrams of the *same type*; the C4 ladder moved executed outcomes
+29.2 pp *within* one genre by adding behavioral content (R2→R3).
Comparing artifact classes without holding information content constant
therefore measures nothing. Correction: the unit of analysis is the
**information** (decisions, thresholds, failure policy, signatures);
artifact classes and syntaxes are **carriers**. Every design varies
carrier at fixed information, or information at fixed carrier — never
both at once.

**C1 — carrier results are capability-relative.** A carrier comparison
partly measures the generator's training priors, so its results decay
per model generation. This is a consequence to engineer for, not an
objection: pivotal contrasts are re-measured per model generation (the
standing Arc D re-measurement instrument recorded in the
capability-horizon settlement), and the *durable* carrier criterion is
checkability (§4), which is an engineering argument the experiments can
only license, not replace.

**C2 — "effectiveness" must be a vector, not a scalar.** A scalar
fitness score invites Goodhart — the shape the auto-improvement
settlement already rejected (a judge-routed fitness optimizes
judge-pleasing artifacts and silently decays across model versions).
The vector and its proxies are declared in §4; executed correctness is
primary, everything else is tracked and reported separately.

## 3. The objective, reframed

> **For each measurable hop of an AI-assisted delivery lifecycle,
> determine the minimum sufficient information set, the carriers that
> make that information cheapest to author, check, and consume, and the
> per-artifact gates required for the stack to be net-positive — where
> sufficiency is measured as marginal executed correctness under frozen
> oracles, the remaining effectiveness components are tracked as a
> declared vector, and every claim is dated and re-measured per model
> generation.**

The original three questions map onto the reframed terms:

- *Which artifacts* → which information must exist for the hop, and in
  which carrier (§6; waves W1, W3).
- *Which level of detail* → the dose–response knee, including the far
  side (§6; waves W1, W4).
- *Which syntax* → carrier effects at fixed information, plus the
  checkability criterion (wave W3).

## 4. Definitions

- **Hop** — one artifact-to-artifact transformation in the lifecycle
  (prose→model, model→code, spec+code→change, spec→tests) for which a
  deterministic or executable oracle can be constructed and frozen
  before any scored run.
- **Information vs carrier** — an *information unit* is a decision the
  downstream generator would otherwise have to invent: a threshold, a
  guard semantic, a failure policy, an operation signature, a state
  transition, a boundary. A *carrier* is the artifact class and syntax
  that transports it (sequence diagram, C4, OpenAPI, decision table,
  Gherkin, controlled English, prose). Stack claims are about
  information; carrier claims must hold information constant.
- **Effectiveness vector** — the declared components and their proxies:
  1. **Executed correctness** (primary) — pass-rate against frozen,
     pre-registered acceptance suites; quoted as gaps, orderings and
     correlations, never absolutes (suite-relative).
  2. **Invention rate** (secondary) — judged invented-business-logic
     per run; quoted strictly as a judgment and never merged with
     executed numbers (judged↔executed agreement is weak same-vendor,
     r ≈ 0.25, and zero cross-vendor).
  3. **Cost** — artifact tokens (authoring proxy) and context tokens
     consumed (consumption proxy); marginal pp per thousand tokens is
     the comparison unit.
  4. **Maintenance** — edit distance and drift under a controlled
     change request (measured only by W7; until then unclaimed).
  5. **Checkability** — whether a deterministic verifier exists for
     the carrier, and what fraction of the stack's information units it
     can see. The EC5 lesson makes this measurable: v0.23.0 scored
     every rung of a C4 ladder spanning 50 pp of executed outcome at
     Level 1, indistinguishably — a gate that cannot see an information
     class must say so.
  - Human review value and organizational effects stay
    [mechanism]/[hypothesis]-tagged (the value-in-the-sdlc discipline);
    no lab oracle exists at this scale and none is claimed.
- **Minimum sufficiency** — the smallest information set for a hop such
  that every further increment's marginal executed contribution falls
  below the measuring wave's pre-registered materiality threshold
  (threshold frozen per wave, before any scored run), with the far side
  measured rather than assumed harmless.
- **Gate** — a deterministic, per-artifact verification that runs in CI
  and certifies that decisions are *stated*, never that they are right
  (the measured scope of the existing gate, X-R4). Under this charter
  gates are constitutive: for stack-level claims, an ungated artifact
  does not count as present, because the standing evidence says
  below-cliff artifacts are not merely insufficient but harmful
  (fidelity down by roughly a third, invented business logic roughly
  doubled, 16–25 pp executed). This is the frame's sharpest commitment
  and a named falsification target (§8.1).

## 5. The hop map

| Hop | Oracle | Status |
|---|---|---|
| Prose intent → model/spec | planted-ambiguity localization: precision/recall of k-way model divergence against injected ambiguities | Specified (ROADMAP Arc J), gated on the Arc I meter — listed for completeness, runs on its own trigger |
| Model/spec → code | frozen acceptance suites, sandboxed execution (plus mechanical structural conformance where a declared graph exists) | **Built** (Arc D harness, `tools/acceptance/`) |
| Spec + code → change (maintenance) | delta acceptance suites over an existing generated codebase; spec↔code drift | Constructible, unbuilt (W7, gated) |
| Spec → tests | adequacy of generated suites against a frozen reference suite | Constructible, **not queued** — the adjacent-verifier settlement classes test-oracle quality as sibling-tool territory; any lab measurement here must not imply a product |
| Build/deploy/operate | none constructible in this lab | Out of scope for measurement — position-paper territory only |

Orthogonal to the hops is the **workflow dimension**: everything
measured to date is single-shot generation; real AI-assisted delivery
is agentic (the agent runs tests and iterates). W5 measures whether the
standing claims survive that transfer.

## 6. What is already answered (evidence-graded)

Grades: **[measured]** = this repo's ladder/variant/interventional
waves, execution-graded; **[measured, confounded]** = measured with a
named confound; **[external]** = literature only; **[built]** = shipped
machinery, outcome-side unmeasured; **[ecosystem]** = usage counts, not
outcomes.

| Information / artifact | Evidence | Grade |
|---|---|---|
| Behavioral interaction content (flows, branches, failure paths) at method-convention completeness | +29.2 pp executed when dynamics arrive (C4 R2→R3); 16–25 pp executed cliff below Level 2 within the sequence family, scaffold-resistant, three generators, two vendors | [measured] — the single biggest lever |
| Written decision contract (thresholds, validation, error policy, API) | Judged invention −⅓ at the companion-spec rung (7.00 → 4.00/run, largest drop R3→R4); 0.0 pp executed on a canonical-threshold suite — but the R2 invented-cap incident (`MAX_AMOUNT = 50000`, plausible, wrong, confidently implemented, invisible to the suite) shows it is the only carrier that pins *idiosyncratic* rules | [measured, confounded] — the canonical-threshold confound is the recorded follow-up, fixed by W0's adversarial-threshold system |
| The decision/Q&A record — authored answers to gap-report questions | Ask-vs-invent ≈ 27 pp executed below the cliff (0.857 vs 0.583); invention halved but not eliminated with an author available (98 → 45); 61% of the asking that drove recovery was exploratory, beyond the gap report | [measured] — the conversation is a load-bearing artifact; no stack row currently captures it |
| Acceptance tests as generation *input* | +9.15–29.57% correctness in function-level benchmarks (external); in-house, suites have only ever been the oracle, never an input | [external] — untested here; W1 arm |
| Structural diagrams (context/container) | Group-edge recall 1.00 at every rung including bare R0 under a conforming prompt (EC1); annotations +8.3 pp executed (R0→R1), invention-flat | [measured] — orientation and misread-prevention value; not an outcome lever |
| Stable-ID traceability | `pumllint trace` shipped (Arc G) | [built] — outcome-side unmeasured |
| Per-artifact gates as a necessity | Below-cliff artifacts actively degrade generation; every author-less-repaired diagram passed the gate while executing 36.6 pp below pristine — the gate certifies statedness, not correctness | [measured] — the positioning claim |
| Carrier/syntax effects | None — no outcome evidence anywhere, including here. Ecosystem only: Mermaid dominates embedded-markdown specs 55–437×; standalone `.puml` outnumbers embedded PlantUML 16× | [ecosystem] — W3's territory |

The standing detail answer, consolidated: the measured bar is
**method-convention completeness** — every decision stated somewhere
reachable, no elisions, typed participants, guards with semantics,
failure paths on external calls, signatures not prose. Below it, the
cliff (prompting cannot restore what the artifact never contained);
above it, executed returns plateau while a written contract keeps
cutting invention; a residual floor remains at any detail level.

## 7. Open questions → waves

House measurement standards carry over unchanged: pre-registered
expectations and pre-committed interpretation matrices frozen before any
scored run; execution primary, judgments quoted as judgments, never
merged; pooled tiers carry claims, never single runs; quote gaps and
orderings, never absolutes; per-wave cost ceilings; all costs recorded.
One standard is added from re-deriving the existing analyses: for
*executed* outcomes, judge-counted demand is a **mediator, not a
confound** — degradation removes the very guards being counted — so
hard-demand partials apply to judged gradients only; the design control
for execution is same-family frozen suites. Carried limitations, stated
once: toy-scale systems, LLM stand-ins for author and judge, k = 1
repairs, n = 3 runs per unit, single-shot generation everywhere below
W5.

- **W0 — charter + kits ($0, no API).** Owner review of this charter;
  the **adversarial-threshold reference system** (non-canonical
  decision rules a generator's priors cannot guess — the recorded fix
  for the companion-spec confound) with its frozen suite; artifact kits
  for the missing carriers (OpenAPI contract, Gherkin acceptance set,
  state model, decision table); wave pre-registration templates.
- **W1 — artifact-portfolio ablation (~$15–25).** Additive ladder
  (brief → +structure → +behavior → +contract → +tests-as-input) *and*
  leave-one-out from the full stack, on the adversarial-threshold
  system; two generators (the weak-generator amplification is a known
  effect). Output: marginal pp per artifact and per thousand artifact
  tokens, both directions. Feeds: the spec-stack recommendation becomes
  measured; rule-pack selection; the package-level lint observation.
- **W2 — redundancy and conflict (~$5–10).** Controlled contradictions
  between artifact pairs and duplicated-but-stale restatements; measure
  silent-resolution vs ask vs error. First measurement of the
  precedence-of-evidence ladder (adopted 2026-07-29, never tested);
  supplies demand evidence for the recorded sequence↔contract
  cross-check candidate — whose build still follows its own trigger.
- **W3 — carrier equivalence (~$10).** The same information rendered as
  PlantUML, Mermaid, structured YAML, controlled English
  (verbalizer-shaped), and code-stub skeletons. Pre-registered
  expectation: deltas < 10 pp above the cliff. Confirmation licenses
  checkability as the deciding carrier criterion; refutation is a
  headline either way. Informs the Mermaid sibling-stack record and
  Arc H's value case — both keep their own triggers.
- **W4 — dose–response, including the far side (~$10).** Ladder from
  minimal past SDD-grade into deliberate over-specification (redundant
  restatement, irrelevant context, exhaustive enumeration); locate the
  knee; measure dilution. Completes E1's correction with data.
- **W5 — the agentic condition (~$25–40; needs a new loop driver,
  disclosed harness work).** Re-run the pivotal contrasts (below-cliff
  vs L5 sequence; C4 R0 vs R3/R4) with an agent that can execute a
  visible smoke subset and iterate, graded by the frozen hidden suite.
  Pre-registered expectations: partial compensation for suite-covered
  behavior; invention on uncovered behavior persists; artifact value
  shifts from generation input toward decision record and review
  oracle. The external-validity keystone: it decides how every standing
  claim must be worded for the workflows people actually run.
- **W6 / W7 — gated, unchanged.** W6 is Arc J exactly as specified in
  the ROADMAP (requirements hop; needs the Arc I meter in lab form) —
  this charter does not pre-empt its trigger. W7 is the maintenance hop
  (change request against existing code + artifacts, spec-updated vs
  prose-only): novel, measured nowhere, gated on W5's driver and owner
  go.

Priority: W0 → W1 → W5, with W2–W4 as adjuncts between. Program ceiling
≈ $120; the entire recorded evidence program to date cost ≈ $55, so the
estimates are grounded. Per-wave ceilings freeze in each
pre-registration. Results land as dated research records in docs/
(EVIDENCE.md discipline), converging on one consolidated document — the
measured minimum sufficient stack — plus its product consequences (rule
selection, claim language, agents.md updates), each following existing
gates.

## 8. What would falsify this frame

Recorded now so failure cannot be reinterpreted later:

1. **Ungated stacks perform adequately.** Already the recorded
   re-litigation trigger of the spec-stack evaluation. If a mandated
   but unverified artifact stack measures fine, gates are not
   constitutive and §4's sharpest commitment falls.
2. **Redundancy is harmless or positive (W4).** Then "minimum" loses
   its outcome edge over "more is fine" and retreats to a cost-only
   argument — the charter must be reworded accordingly.
3. **Marginal contributions are unstable across systems and generators
   (W1).** Then no portable minimum exists; every stack claim becomes
   per-context, and the consolidated document must say so instead of
   recommending.
4. **The cliff collapses under agency (W5).** Then the gate thesis
   narrows to single-shot workflows — the window-closing signal of the
   capability-horizon settlement arriving via workflow rather than
   capability; the response is that settlement's: a reviewed
   repositioning, never an unattended one.
5. **The knee cannot be located at feasible n (W4).** If dose–response
   noise at this budget swamps the materiality threshold, "minimum
   sufficiency" is not operationalizable here; record it and stop —
   an abort criterion, not a hand-wave.

## 9. Conflict-of-interest note and verification record

This frame converges on the product's own thesis (per-artifact
deterministic gates). That convergence is corroboration *risk*, not
evidence: a frame adopted because it flatters the tool would be exactly
the motivated reasoning the settled-questions discipline exists to
catch. The discipline here is §8 — three of its five falsifiers (W1,
W4, W5) have a genuine chance of hurting the product's positioning, and
their outcomes get recorded with the same prominence as confirmations.
Precedent that this is practiced, not promised: X3, XV1, X-R1, X-R2,
X-R3a, X-A1 and X-A4 all failed and are published as failures.

Because this charter is internally authored, it gets the same
treatment external recommendations get before anything acts on them: an
independent adversarial pass instructed to refute it — verify every
number against the repository's records, hunt unfalsifiable or
motivated statements, and check consistency with the settled questions
and gates. **Result: pending — the pass is running at the time of this
draft's commit.** Its findings and their dispositions will replace this
paragraph in the verified revision; until that revision lands, this
charter is a draft and must not be acted on. (Committed in this state,
findings-before-verdicts style, so the draft is preserved and the
verification is auditable against it rather than silently folded in.)

## 10. Decision and triggers

- **This charter changes no product behavior and queues no build.** The
  product path stays deterministic and demand-gated per the working
  agreements; measurement and lab machinery stay in `tools/` per the
  packaging settlement.
- **Acceptance of this charter is owner go on W0 only.** Every funded
  wave (W1–W5) takes its own go, with its own frozen pre-registration
  and ceiling. W6/W7 keep their prior ROADMAP triggers.
- **Prerequisites:** `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (plus
  `GEMINI_API_KEY`/`GOOGLE_API_KEY` for any cross-vendor leg) in the
  research environment; the harness's cost guards stay on.
- **On acceptance,** the ROADMAP gains a one-line pointer to this
  charter; the charter is the research program's source of truth and is
  revised in place, dated, as waves land.
- **Re-litigate the frame** on any §8 trigger firing — or on evidence
  that the reframing itself suppressed a question the original
  phrasing would have caught.
