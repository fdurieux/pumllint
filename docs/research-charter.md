# Research charter — the minimum sufficient specification stack

*Dated reframing record, 2026-08-06. This document performs the reframing
of the research objective for this project — from "maximise the
effectiveness of an end-to-end AI-assisted software delivery lifecycle"
to a form that can be measured, falsified, and re-measured. It restates
the objective, defines its terms, maps it onto the evidence this
repository already holds, sketches the wave program that answers what
remains open, and records what would falsify the frame itself. House
discipline applies to this charter as it does to externally authored
recommendations: it received an adversarial verification pass before
acceptance (§9 — 17 findings, all adopted in this revision), and no
wave runs from this charter alone — every wave freezes its own
pre-registration and interpretation matrix before any scored run.
Status: verified revision, accepted (owner go on W0); acceptance
recorded 2026-08-10 — see ROADMAP § Working agreements. W1 ran
2026-08-10 (frozen pre-registration, calibration record and results:
stack_experiment/W1_PREREGISTRATION.md); §§4, 6, 7 and 8 carry its
dated updates in place.*

## 1. The objective as posed

> Determine which artifacts are needed, which level of detail, which
> syntax, in order to maximise the effectiveness of an end-to-end
> AI-assisted software delivery lifecycle.

The question is real, timely, and externally corroborated — DORA 2026
names the "verification tax" as the most immediate barrier to AI ROI;
SWE-bench Verified found 38.3% of real issue descriptions
underspecified; SpecFix gained +30.9% Pass@1 on the ~44% of task
descriptions it modified (+4.09% absolute, function-level benchmarks);
the spec-driven-development wave has made specification
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
monotone. *Measured 2026-08-11: W4 confirmed far-side dilution at
1.12–1.45× doses (pooled −6.7 / −11.2 / −14.3 pp for redundant /
irrelevant / enumerated over-specification), borne entirely by the
weak generator (haiku −26 / −32 pp under irrelevant context and
ACCURATE exhaustive enumeration while the strong generator held its
ceiling); W2 measured conflicts resolving silently — 0 of 18 runs
surfaced an injected contradiction. Records:
stack_experiment/W2_PREREGISTRATION.md and W4_PREREGISTRATION.md,
§ Results.*

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
capability-horizon settlement), and the *candidate* durable carrier
criterion is checkability (§4) — an engineering argument the
experiments must license before it decides anything: W3's confirmation
licenses it; a W3 refutation demotes it to one criterion among several
and reopens the carrier question on outcome evidence. *W3 ran
2026-08-11 and refuted equivalence: checkability is demoted as
pre-committed, and the carrier question is open on outcome evidence —
PlantUML ≥ code-stub ≈ Mermaid > controlled English > YAML, every
alternative losing on flow-sensitive scenarios (record:
stack_experiment/W3_PREREGISTRATION.md § Results).*

**C2 — "effectiveness" must be a vector, not a scalar.** A scalar
fitness score invites Goodhart — the shape the auto-improvement
settlement already rejected (a judge-routed fitness optimizes
judge-pleasing artifacts and silently decays across model versions).
The vector and its proxies are declared in §4; executed correctness is
primary, everything else is tracked and reported separately.

## 3. The objective, reframed

> **For each measurable hop of an AI-assisted delivery lifecycle,
> determine the minimum sufficient information set, the carriers that
> make that information cheapest to author and consume and mechanically
> checkable, and the per-artifact gates required for the stack to be
> net-positive — where
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
     executed numbers, per the house standard. (The measured agreement
     figures — weak same-vendor r ≈ 0.25, zero cross-vendor — are for
     judged *fidelity* vs execution; no invention↔execution
     correlation has been computed.)
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
  does not count as present. Stated honestly, that commitment is a
  **risk policy, not an evidence-entailed result**: the standing
  evidence shows below-cliff artifacts are harmful *relative to their
  pristine siblings* (fidelity down by roughly a third, invented
  business logic roughly doubled, 16–25 pp executed) — no wave has
  compared a below-cliff artifact against artifact *absence*, and
  ungated does not mean below-cliff (an ungated artifact can be
  pristine; unverified means the tier is unknown). W1 therefore
  carries a below-cliff-vs-absent arm to supply the missing contrast.
  This is the frame's sharpest commitment and a named falsification
  target (§8.1). *W1 ran the arm (2026-08-10): an exact null — the
  below-cliff stack and the artifact-absent stack executed
  identically (pooled n = 10 vs 10), with prose flow present in both
  arms per the kit's declared spec.md overlap; the contrast did not
  resolve the commitment either way, and the risk-policy label
  stands.*

## 5. The hop map

| Hop | Oracle | Status |
|---|---|---|
| Prose intent → model/spec | planted-ambiguity localization: precision/recall of k-way model divergence against injected ambiguities | Specified (ROADMAP Arc J); recorded trigger: **Arcs H and I shipped** — listed for completeness, runs on its own gate |
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
| Behavioral interaction content (flows, branches, failure paths) — its *presence* is the measured lever; method-convention completeness is the sequence-family bar, above C4's qualitative-guard ceiling | +29.2 pp executed when dynamics arrive (C4 R2→R3, qualitative guards only); 16–25 pp executed cliff below Level 2 within the sequence family, scaffold-resistant, three generators, two vendors; W1 (2026-08-10, adversarial thresholds): behavior arrival +31.8 pp pooled while the written contract led (+37.9) | [measured] — the biggest lever on canonical-threshold systems; system-relative per W1 (E1 failed, published: stack_experiment/W1_PREREGISTRATION.md § Results) |
| Written decision contract (thresholds, validation, error policy, API) | Judged invention −⅓ at the companion-spec rung (R3→R4: 6.00 → 4.00/run, the ladder's largest drop; full ladder 7.00 → 4.00); 0.0 pp executed on a canonical-threshold suite — but the R2 invented-cap incident (`MAX_AMOUNT = 50000`, plausible, wrong, confidently implemented, invisible to the suite) shows it is the only carrier that pins *idiosyncratic* rules; **W1 (2026-08-10, adversarial thresholds): +37.9 pp pooled executed A2→A3 (opus +54.6, haiku +21.2), net gains concentrated in contract-classed scenarios; the wave's largest leave-one-out drop (−55.2 pp); judged invention medians fell 6→3 / 5→3** | [measured] — the canonical-threshold confound is resolved (EC3 closed by W1): executed-real where priors cannot guess |
| The decision/Q&A record — authored answers to gap-report questions | Ask-vs-invent: +27.4 pp executed below the cliff vs the author-less arm (0.857 vs 0.583) and +21.5 pp vs untouched (0.642) — the second is the decision-relevant contrast for adding the record; invention halved but not eliminated with an author available (98 → 45); 61% of the asking that drove recovery was exploratory, beyond the gap report | [measured] — the conversation is a load-bearing artifact; no stack row currently captures it |
| Acceptance tests as generation *input* | +9.15–29.57% correctness in function-level benchmarks (external); in-house, W1 (2026-08-10): +12.7 pp pooled A3→A4, ~98% of net gain in value-bearing scenarios and leakage share ≈ nil under the pre-declared overlap split; generator-split — the strong generator sat at ceiling (−3.6), the weak gained +29.1 | [measured] — this lab, this scale (one system, single-shot); external figures kept for context |
| Structural diagrams (context/container) | Group-edge recall 1.00 at every rung including bare R0 under a conforming prompt (EC1); annotations +8.3 pp executed (R0→R1), invention-flat | [measured] — orientation and misread-prevention value; a modest outcome effect, not the main lever |
| Stable-ID traceability | `pumllint trace` shipped (Arc G) | [built] — outcome-side unmeasured |
| Per-artifact gates as a necessity | Below-cliff artifacts actively degrade generation vs their pristine siblings; all 16 author-less-repaired diagrams passed the gate while the repaired-L1 tier executed 36.6 pp below pristine (repaired-L2: 10.8 pp) — the gate certifies statedness, not correctness | [measured] — the positioning claim, with §4's harm-vs-absence caveat |
| Carrier/syntax effects | W3 (2026-08-11, one behavior artifact at the A2 rung, fixed information, audited translations): carrier matters — vs the PlantUML baseline, code-stub −6.1 pp, Mermaid −9.1, controlled English −15.2, structured YAML −30.3 pooled; on flow-sensitive scenarios every alternative lost 17–67 pp, and opus generated non-compiling code from YAML 3/3. Ecosystem context retained: Mermaid dominates spec directories 76–437×; standalone `.puml` outnumbers embedded 16× | [measured] — first outcome evidence; equivalence refuted, checkability demoted per C1 |

The standing detail answer, consolidated — three tiers, not two:
**below Level 2**, the cliff (16–25 pp executed, scaffold-resistant:
prompting cannot restore what the artifact never contained); **from
Level 2 up to the bar**, a monotone, scaffold-compressible gradient
(pooled executed 0.756 / 0.910 / 0.949 at L2/L4/L5; entry-contract
pinning lifted L2 to ≈ pristine); **at and beyond the bar** —
method-convention completeness: every decision stated somewhere
reachable, no elisions, typed participants, guards with semantics,
failure paths on external calls, signatures not prose — executed
returns plateau (canonical-threshold-confounded at the measured rung)
while a written contract keeps cutting invention; a residual floor
remains at any detail level. *Dated updates: W1 (2026-08-10) resolved
the canonical-threshold confound — on adversarial thresholds the
contract rung is executed-real (+37.9 pp pooled) and the plateau
begins at the full stack, with knees per-generator (strong at
+contract, weak at +tests). W4 (2026-08-11) measured the far side:
beyond the full stack more text never helped and diluted the weak
generator severely — the three-tier answer gains a fourth clause:
past sufficiency, detail is at best free for strong generators and
actively harmful for weak ones at ≤ 1.45× doses.*

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
for execution is same-family frozen suites. Attribution, per the
verification pass: the record's own rationale is that the triviality
confound does not exist under a fixed family suite; the mediator
reading — which additionally explains the observed collapse of the
executed partial (raw per-diagram r 0.545 → 0.081 pooled) — is
interpretation added by this charter, not stated by the record. Carried limitations, stated
once: toy-scale systems, LLM stand-ins for author and judge, k = 1
repairs, n = 3 runs per unit, single-shot generation everywhere below
W5.

- **W0 — charter + kits ($0, no API).** Owner review of this charter;
  the **adversarial-threshold reference system** (non-canonical
  decision rules a generator's priors cannot guess — the recorded fix
  for the companion-spec confound) with its frozen suite; artifact kits
  for the missing carriers (OpenAPI contract, Gherkin acceptance set,
  state model, decision table); wave pre-registration templates.
- **W1 — artifact-portfolio ablation (~$15–30).** Additive ladder
  (brief → +structure → +behavior → +contract → +tests-as-input) *and*
  leave-one-out from the full stack, on the adversarial-threshold
  system; two generators (the weak-generator amplification is a known
  effect). Two design obligations from the verification pass: a
  **below-cliff-vs-absent arm** (a degraded artifact versus no
  artifact at all — the contrast §4's gate policy currently lacks),
  and the **tests-as-input rung pre-commits its separation from the
  grading oracle** in the pre-registration (disjoint scenarios, or a
  declared-overlap analysis — the W5 visible/hidden split applied
  here), else the rung measures oracle leakage, not artifact value.
  Output: marginal pp per artifact and per thousand artifact tokens,
  both directions. Feeds: the spec-stack recommendation becomes
  measured; rule-pack selection; the package-level lint observation.
  *Ran 2026-08-10 ($12.18 of the $30 ceiling): frozen record,
  verdicts and marginal tables in
  stack_experiment/W1_PREREGISTRATION.md § Results — E2/E3/E6/E7
  confirmed, E1/E4/E8a failed and published, E5 an unresolved null;
  §6 and §8 carry the dated consequences.*
- **W2 — redundancy and conflict (~$5–10).** Controlled contradictions
  between artifact pairs and duplicated-but-stale restatements; measure
  silent-resolution vs ask vs error. First measurement of the
  precedence-of-evidence ladder (adopted 2026-07-29, never tested);
  supplies demand evidence for the recorded sequence↔contract
  cross-check candidate — whose build still follows its own trigger.
  *Ran 2026-08-11 ($3.58): silent resolution total (0/18 surfaced);
  the decision table beat stale prose 6/6, the five-source majority
  beat a stale sentence 5/6 (the miss was a type bug, not stale
  adoption), the stale worked example was ignored 12/12 slots;
  conflicts stayed local. Record:
  stack_experiment/W2_PREREGISTRATION.md § Results.*
- **W3 — carrier equivalence (~$10).** The same information rendered as
  PlantUML, Mermaid, structured YAML, controlled English
  (verbalizer-shaped), and code-stub skeletons. Pre-registered
  expectation: deltas < 10 pp above the cliff. Confirmation licenses
  checkability as the deciding carrier criterion; refutation is a
  headline either way. Informs the Mermaid sibling-stack record and
  Arc H's value case — both keep their own triggers. The code-stub arm
  brushes a recorded never-build (free-form executable code as the
  pipeline intermediate, prose-pipeline settlement): it is a lab
  measurement only, and a favorable result changes claim language,
  never that settlement, absent explicit re-litigation. *Ran
  2026-08-11 ($4.21): equivalence REFUTED — see C1's dated demotion
  note and the §6 carrier row; record:
  stack_experiment/W3_PREREGISTRATION.md § Results.*
- **W4 — dose–response, including the far side (~$10).** Ladder from
  minimal past SDD-grade into deliberate over-specification (redundant
  restatement, irrelevant context, exhaustive enumeration); locate the
  knee; measure dilution. Completes E1's correction with data. *Ran
  2026-08-11 ($3.82): dilution measured (see E1's dated note); knees
  as pre-registered — pooled at the full stack, strong generator at
  +contract, weak at +tests. Record:
  stack_experiment/W4_PREREGISTRATION.md § Results.*
- **W5 — the agentic condition (~$25–40; needs a new loop driver,
  disclosed harness work).** Re-run the pivotal contrasts (below-cliff
  vs L5 sequence; C4 R0 vs R3/R4) with an agent that can execute a
  visible smoke subset and iterate, graded by the frozen hidden suite.
  Pre-registered expectations: partial compensation for suite-covered
  behavior; invention on uncovered behavior persists; artifact value
  shifts from generation input toward decision record and review
  oracle. The external-validity keystone: it decides how every standing
  claim must be worded for the workflows people actually run.
- **W6 / W7 — gated, unchanged.** W6 is Arc J (requirements hop),
  whose recorded trigger is **Arcs H and I shipped** — this charter
  does not pre-empt or relax that gate; treating a lab-form Arc I
  prototype as sufficient would be an explicit owner decision, not
  something this charter grants. W7 is the maintenance hop
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
   constitutive and §4's sharpest commitment falls. No queued wave can
   fire this from inside the program — it waits on external evidence;
   W1's below-cliff-vs-absent arm probes only the harm-vs-absence
   component beneath it.
2. **Redundancy is harmless or positive (W4).** Then "minimum" loses
   its outcome edge over "more is fine" and retreats to a cost-only
   argument — the charter must be reworded accordingly. *Did not
   fire: W4 (2026-08-11) measured real dilution at ≤ 1.45× doses —
   "minimum" keeps its outcome edge, dose- and generator-scoped
   (see E1's dated note).*
3. **Marginal contributions are unstable across systems and generators
   (W1).** Then no portable minimum exists; every stack claim becomes
   per-context, and the consolidated document must say so instead of
   recommending. *Partially fired in W1 (2026-08-10), generator axis:
   the two generators disagreed on the largest additive increment
   (strong: contract; weak: behavior) while agreeing on the
   leave-one-out top and bottom — stack claims are quoted
   per-generator until re-measured.*
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
catch. The discipline here is §8 — four of its five falsifiers are testable
in-program (§8.3 by W1, §8.2 and §8.5 by W4, §8.4 by W5), each with a
genuine chance of hurting the product's positioning, and their
outcomes get recorded with the same prominence as confirmations; the
fifth (§8.1, the frame's sharpest commitment) has no full in-program
test — it waits on external evidence, with W1's below-cliff-vs-absent
arm as a partial probe.
Precedent that this is practiced, not promised: X3, XV1, X-R1, X-R2,
X-R3a, X-A1 and X-A4 all failed and are published as failures.

Because this charter is internally authored, it got the same treatment
external recommendations get before anything acts on them: an
independent adversarial pass instructed to refute it — verify every
number against the repository's records, hunt unfalsifiable or
motivated statements, and check consistency with the settled questions
and gates. The draft was committed *before* the pass reported
(findings-before-verdicts style), so the verification is auditable
against it rather than silently folded in. **Result: 17 findings — 4
major, 13 minor — all 17 adopted in this revision.** The majors: (1)
the consolidated detail answer had collapsed a measured three-tier
dose–response into two — the cliff sits below Level 2, three levels
beneath the method-convention bar, with a scaffold-compressible
gradient between (§6 restated); (2) the constitutive-gates commitment
was argued from harm-vs-pristine evidence while needing a
harm-vs-absence contrast no wave has run — relabeled a risk policy,
and W1 gained the missing arm (§4, §7); (3) W1's tests-as-input rung
had no declared separation from the grading oracle — its
pre-registration must now pin one (§7); (4) Arc J's recorded trigger
(Arcs H and I *shipped*) had been restated weaker while claiming
deference — corrected to the recorded gate (§5, §7). Representative
minors: the 55× Mermaid figure was the global-markdown population, not
spec directories (76–437×); the ask-vs-invent row quoted only the
flattering contrast (+27.4 pp vs author-less; +21.5 pp vs untouched is
the decision-relevant one); the judged↔executed r-values belong to
fidelity, not invention; C1 had pre-declared checkability "durable"
ahead of W3's verdict and is now conditioned on it; the mediator
standard is now labeled as this charter's interpretation alongside the
record's own rationale. The reviewer's overall verdict, quoted: "the
quantitative spine is genuine — every headline number traces to its
source and the reframing itself survives — but it does not survive
intact" without these fixes.

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
