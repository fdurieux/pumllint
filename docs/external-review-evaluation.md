# The two-stage external project review, evaluated

*Dated evaluation, 2026-08-11. An externally authored two-stage review
of this repository reached the owner as a chat-authored analysis with
live web access to the raw repository files, produced inside the
reviewer's own research conversation on specification-driven AI codegen
for an enterprise adopter programme in a regulated domain. **Stage 1**
was written against `main` at the W1-results state (W2–W4 frozen,
unrun); **stage 2** after the W2–W4 results landed (2026-08-11) and
before any W5 run. Both stages were assessed here claim-by-claim
against the repository's own md record — EVIDENCE.md, the research
charter, the four wave pre-registrations' § Results, agents.md,
SCORING.md/README.md, and the docs shelf — on five dimensions: sense,
nonsense, fit, gap, priorities. Verdict up front: **the most accurate
external assessment this repository has received. Every checked figure
traces to its source — roughly forty numbers across W1–W4, the C4
ladder, the sequence cliff and the judge-validity record, zero
misquotes — and both of its repo-facing defect findings are real and
were previously unrecorded: the Level-5 naming contradiction
(`scoring.py` names the level "Generation-ready" while agents.md states
it is "deliberately not called" that) and the EVIDENCE.md / stack-program
boundary (EVIDENCE.md carries zero stack-wave content). Its priority
call — W5 next — matches the charter's recorded priority. Its
weaknesses are of attribution and scoping, not fact: it re-recommends
design elements the program already carries, drops house scopings in
its summaries, and its capstone "target architecture" and closing
"conceptual lesson" claims overstate derivation from the waves (both
graded under stage 2: two boxes gained measured rationales, the
carrier lineup and two further boxes stay hypothesis, the agentic
keystone is untested, the measured author/decision loop has no box,
and the lesson's dilution side omits its dose and generator scoping),
while its forward programme is written for its own platform ambition —
sound there, mostly not pull here. Three
doc-hygiene candidates and two wave candidates are recorded below;
nothing is queued; no product behavior changes.** Source retained by
the owner; not linked here.*

## Why this evaluation ran

Same rule as every externally authored assessment in this territory
(spec-stack 2026-07-29, model-verification 2026-08-02, SDD-manifest
2026-08-10): verify before any content becomes work. This one differs
from its predecessors in two ways that raise the value of checking: it
had **live repository access** (its predecessors reasoned without it),
and it is **longitudinal** — stage 2 re-scores stage 1's own claims
against evidence that landed in between, which makes its calibration
itself checkable.

## What the review says (compressed, so this note stands alone)

**Stage 1** (pre-W2–W4 results): a scored assessment of the project as
linter, as research programme, and as component of the reviewer's own
ambition ("zero undetected unsupported behaviour"). Headlines: keep
pumllint but do not make it the centre — the generalizable concept is
per-artifact deterministic verification plus deliberate context
selection plus independent oracles; the repository's most important
finding is that the gate verifies statedness, never truth; the
sequence evidence is credible within boundaries; W1's contract headline
is real but the A3 bundle is too coarse to attribute; per-generator
disagreement suggests a stable information model with
capability-dependent context selection; rename Level 5; tighten two
overbroad sentences in case-for-pumllint; a ~30-row assessment of the
docs shelf; finish W2–W4, then prioritise W5; design (not yet execute)
a domain benchmark.

**Stage 2** (post-W2–W4, pre-W5): re-reads the published results and
raises its scores. Headlines: W1–W4 now identify an operating envelope
with three measured failure mechanisms (underspecification →
invention; inconsistency → silent resolution; overspecification →
dilution, weak-generator-borne); conflict detection must run before
generation, not be delegated to agent obedience; W3 overturned the
reviewer's own carrier-neutrality expectation and demotes
"machine-readable to a parser" as a proxy for "legible to an LLM";
W4 supports minimum-sufficient context projection ("context compiler")
and model-specific generation profiles; EVIDENCE.md's boundary with the
stack programme should be made explicit; next: W5 first, then A3
decomposition, a W3 prompt-frame follow-up, and the adopter-domain
benchmark in parallel.

## Verification record

Every load-bearing claim was checked against the working tree at
c55e468/07f36aa. No misquoted number was found. The distinctive checks:

| Review claim | Checked against | Verdict |
|---|---|---|
| W1 ladder 0.136/0.121/0.439/0.818/0.945; marginals −1.5/+31.8/+37.9/+12.7; opus contract +54.6 vs behavior +24.2, haiku inverse; opus −3.6 at A4; E1 failed and published | W1_PREREGISTRATION.md § Results | exact |
| W2: 0/18 surfaced; table over stale prose 6/6; majority over stale sentence "effectively 6/6 regarding the contradiction itself"; 12/12 price slots | W2_PREREGISTRATION.md § Results | exact — the 5/6 with the type-bug miss is faithfully rendered, and the review correctly reports that no run adopted a stale value |
| W3 table (0.439/0.379/0.348/0.288/0.136 pooled; 93.3/76.7/73.3/60.0/26.7 flow-set); opus-from-YAML 3/3 non-compiles, only non-compiles in the programme; frozen-prompt PlantUML frame recorded as a limitation | W3_PREREGISTRATION.md Design + § Results | exact — the prompt-frame asymmetry it warns about is the pre-registration's own disclosed limitation (finding 3) |
| W4: pooled −6.7/−11.2/−14.3; haiku −10.9/−26.1/−32.1; opus flat-to-ceiling; knees pooled A4 / opus A3 / haiku A4; accurate enumeration hurt more than irrelevant context | W4_PREREGISTRATION.md § Results | exact, including the recorded directional miss (O2 predicted likeliest, O3 worse) |
| C4 rungs .417/.500/.625/.917/.917; +29 pp R2→R3; canonical-threshold confound; CargoQuote as its fix | c4-codegen-detail-experiment.md, stack_experiment/README.md | exact |
| Cliff 16–25 pp, 21.9 pooled, 20.9 cross-vendor; scaffold-resistant; judged↔executed r ≈ 0.25 same-vendor / ~0 cross-vendor while judges agree with each other | EVIDENCE.md, charter §6 | exact |
| Level 5 formally named "Generation-ready" while claim language says otherwise | scoring.py:54, score.schema.json:37 (enum), SCORING.md:111 vs SCORING.md §9, README.md:80, agents.md ("deliberately not called") | **real, previously unrecorded** — ROADMAP's working agreement records the claim-language settlement but not the level-name tension; agents.md's sentence is literally false while the name stands |
| EVIDENCE.md contains no W1–W4 stack-wave content while the charter carries the synthesis | grep over EVIDENCE.md: zero mentions of the waves, stack_experiment, or CargoQuote | **real** — the boundary exists in practice (charter §7 dated notes + pre-registration § Results) but is stated nowhere in EVIDENCE.md itself |
| case-for-pumllint: "No automated check catches any of these today" is overbroad; the same doc later softens to "none we could find" | case-for-pumllint.md ("The problem" vs "What else is out there") | both quotes verified; the tension is real |
| Docs-shelf rows (dogfooding "craft is not truth"; SDD-manifest "attribution, never reproducibility"; spec-stack blind spot; model-verification's category-error scoping) | respective docs | all accurate |

## Stage 1, assessed

**Sense.** The centre of the assessment is right, and it is the hard
part to get right from outside: it identifies the gate's measured scope
(states-its-decisions, never correctness) as the repository's most
important finding rather than the cliff number, which matches what the
repair waves actually established and what agents.md's honesty section
says. Its handling of W1 is the sharpest external restatement of this
programme's own discipline: the A3 rung bundles four files, so
"written contracts matter" is supported while "OpenAPI matters more
than sequence diagrams" and "state models add X pp" are not — worded
almost exactly as the house claim-language rules would demand, without
having been told them. Its per-generator reading (a stable information
model with capability-dependent context selection) anticipates where
charter C1 and the §8.3 partial fire already point. The Level-5 naming
catch is genuine (see the verification row), and the sharpest form of
it is agents.md's sentence, which asserts a naming decision the code
does not implement. The case-for-pumllint overbreadth flag is valid on
its first target and matches the honesty-note style the same document
already uses elsewhere.

**Nonsense.** Little that is factually wrong; the failures are
attribution and scope. Its "one more dimension I would add" — visible
specification vs hidden oracle — is already a designed element of the
programme it is reviewing: W1's pre-declared VALUE9/LEAK2 partition
(which the same section praises) and the charter's W5 sketch ("a
visible smoke subset … graded by the frozen hidden suite"). Its second
case-for charge — that calling SDD tools' quality checks "AI-generated
opinions" is too sweeping because an SDD *workflow* can contain
deterministic validation — partially misreads the sentence's scope,
which is the checks *those tools themselves offer* (accurate for the
named tools); the tightening is still compatible with house style and
is recorded as optional below. Its ROADMAP row ("far too large to
become agent context") prescribes current practice: nothing routes
ROADMAP into agent context; agents.md is the agent surface and
docs/README.md labels ROADMAP a reference/decision record. The
numerical scores (8.5/10 etc.) are judgments and are treated here as
judgments.

**Fit.** Strong. Its architectural conclusion — keep pumllint narrow,
build any multi-artifact platform above it, never inside it — is the
packaging settlement and the deterministic-product-path working
agreement, independently re-derived (the same external convergence the
SDD-manifest evaluation recorded). Its "critical next step" for the
pilot charter matches the recorded next action (2026-07-30:
measurement, not code) and README's own "1.0 waits for contact with a
foreign corpus." Notably, the review *practices* the house claim
discipline — quotes gaps and orderings, keeps judged and executed
apart, scopes per-generator — which is independent evidence that the
discipline is legible from the artifacts alone.

**Gap.** Four omissions matter. It never mentions the adversarial-pass
instrument (drafts committed findings-before-verdicts; 17/9/11/11
findings, all adopted) — the mechanism that makes the numbers it
praises trustworthy, and the strongest part of the methodology it
scores 8/10. The ask-vs-invent result (≈27 pp executed; the author
loop) appears in its opening and then vanishes from its synthesis and
its forward programme, though it is this repository's closest existing
analogue to the review's own "unresolved-decision objects." It
proposes several new experiment families with no cost treatment, where
every house wave carries a pre-registered ceiling. And it checks none
of its recommendations against the settled-questions ledger — it lands
mostly clear, but by scoping luck rather than by the verify-absence
method this shelf exists for.

**Priorities.** "Finish W2–W4, then prioritise W5; design but do not
yet execute the domain benchmark" — this is the charter's own recorded
priority (W0 → W1 → W5, W2–W4 as adjuncts between), reached
independently. Convergent, not novel; no conflict.

**The documentation-architecture coda (§15), graded.** Stage 1 closes
its shelf table with: significant duplication is emerging across
README, EVIDENCE, evidence-explained, case-for, findings-and-scores,
agents, the charter and the fit evaluations; "humans can understand
their different audiences. An AI agent may not"; and per-document YAML
metadata (id, status, scope, audience, authority, supersedes,
derived_documents) "would substantially reduce future context
ambiguity." Three verdicts. *The diagnosis is sense — and the review
corroborated it itself.* The headline figures do recur across five or
more documents, by deliberate audience design (the recorded split,
docs/README.md § How this split was chosen); the discipline keeping
them aligned is prose convention, with no mechanical guard beyond the
version-pin docs test — and the review's own two defect findings are
both instances of exactly this class: a cross-document contradiction
(agents.md against scoring.py) and a missing scope declaration
(EVIDENCE.md). The diagnosis also gains, in stage 2, evidence the
review never connects back to it: W4's dilution result is the
outcome-side form of "overlapping restatements are not free." *The
asymmetry claim is half right.* This repo's answer for agents is a
dedicated entry surface (agents.md), not shelf-wide inference — and
the strongest counterexample to "an AI agent may not" is the reviewer
itself, whose ~30-row shelf table classifies every document's audience
and authority correctly from the artifacts alone. The live exposure is
narrower than claimed: an agent consuming a retrieval slice outside
agents.md — a harness property, not a shelf property. *The remedy is
misfit, three ways.* First, it mechanizes routing, not consistency:
metadata declares authority relationships but detects no contradiction
— of the two demonstrated defects it would have prevented only the
missing scope note, never the naming contradiction (a document can
carry `authority: primary` and still contradict another document's
sentence). Second, the format fights the toolchain: machine-readable
in this repository means stdlib-parseable, and the stdlib parses no
YAML — the recorded reason a root pumllint.yaml is barred — so any
metadata this repo's own tooling consumed would be JSON/TOML or a
single index file; and the only consumer of per-document authority
metadata is context-selection tooling that does not exist here.
Third, "substantially reduce" is an unmeasured strength claim that the
review's own later evidence cuts twice: W2 measured that in-band
authority signals do not make deference *surface* (0/18; "stop-and-ask
is harness work" generalizes — honoring an `authority:` field is
harness work too), and W4 measured that uniformly added material is
dose, with a real far side for weak generators. The house-shaped
residue: the recorded candidates already cover both demonstrated
instances; if this drift class recurs, the discipline-consistent
mechanism is detection, not declaration — a claim-language guard test
extending the existing version-pin pattern (stdlib, deterministic,
CI-native). Noted with that trigger; not a candidate today.

## Stage 2, assessed

**Sense.** The numerical fidelity is complete (verification table).
Beyond fidelity, three readings add genuine value. First, the
three-mechanism synthesis — underspecification, inconsistency,
overspecification as separately measured failure modes bounding an
operating envelope — is a fair and quotable consolidation of W1+W2+W4
that the repository itself has not yet written down in one sentence
(the charter carries it as dated notes in three places). Second, its
W2 handling is unusually honest for an external reading: it reports
the 0/18 silence headline *and* that the models chose the
authoritative source nearly everywhere, then argues silent resolution
is unacceptable anyway on governance grounds — arriving at exactly
agents.md's updated position ("stop-and-ask is harness work; it does
not emerge on its own") with an independent rationale (a silently
correct choice is still an unauthorised decision). Third, its W3
caution is the pre-registration's own disclosed limitation, correctly
weaponised: what W3 measured is carrier performance *inside a
PlantUML-framed harness*, so "PlantUML won here" licenses neither
"PlantUML everywhere" nor carrier-blind tooling choices — and its
four-axis carrier framework (semantic completeness, LLM legibility,
mechanical checkability, human maintainability) is a sound
generalisation of C1's demotion branch. The EVIDENCE.md boundary
observation is verified and correctly hedged ("may be intentional").
Its external-validity restraint (5 → 5.5, with the carried-limitations
list reproduced accurately) polices its own enthusiasm.

**Nonsense.** Four precision notes, none fatal. (1) Its W2 capsule
drops the in-band deference scoping: the frozen record words the
numeric outcome as "the decision table beat the stale prose **under
in-band deference hints**" — deliberately not clean precedence-ladder
evidence — and the review's "6/6" summaries omit that bound. (2) Its
"duplication itself can damage generation even when it has not
drifted" leans on O1's −6.7 pp pooled, which sits *below* the
programme's own 9 pp materiality bar (W4-E2: O1 did not breach; the
measured dilution citation is O2/O3, weak-generator-borne); the strong
form of its argument properly rests on O3, which it also cites — the
capsule just doesn't distinguish them. (3) "W4 now provides direct
experimental support for a context compiler" overstates: W4 measured
dose harm at fixed content (1.12–1.45×), not selection or retrieval;
the support is real but indirect. (4) Its W1 capsule ("the large gains
are constraint information") quotes pooled numbers without the
per-generator scoping that the §8.3 partial fire requires of
consolidated claims — a discipline the review itself states correctly
in its own stage-1 §7 and stage-2 §9.

**Fit.** Its revised objective — "minimise the interpretation the AI
must perform while minimising the irrelevant or duplicated material it
must process" — is a faithful compression of charter §3. Its
single-source-of-truth-for-AI-reasons argument extends the kit's own
design rule (numbers live only in the decision table) into an adoption
argument this shelf can quote. Its model-profile proposal ("model
version is part of the build configuration") is the capability-relative
discipline (C1, the re-measure-per-generation instrument)
operationalised. Its conflict architecture (validate the package
before the LLM sees it) is consistent with the recorded, still-gated
sequence↔contract cross-check candidate — and it correctly does not
ask pumllint to become that cross-spec verifier.

**Gap.** It does not engage the W5 pre-registration draft (committed
minutes after the W2–W4 results commit): the visible/hidden smoke
subsets, k ≤ 2 revision loop, in-wave single-shot baselines and the
disclosed substrate deviation go unexamined, so its "W5 should now be
the immediate priority" recommends the programme's already-recorded
state rather than reviewing its design. It misses W2-E5 (conflict
damage stayed local), which is directly relevant to its own
conflict-gate architecture — locality is the beginning of a
blast-radius argument it could have made. It misses W1-E5's
below-cliff-vs-absent exact null and its prose-redundancy scoping,
the one standing result that cuts *against* simple redundancy-harm
narratives and would have sharpened its §8. And the external-validity
leg its own stage 1 called critical — a foreign corpus, the pilot —
vanishes from its stage-2 forward plan; its domain benchmark partially
substitutes for the reviewer's programme, but the repo-side leg is
simply absent.

**Priorities.** W5 first: matches the charter, again convergent. Its
two lab follow-ups map cleanly onto follow-ups this programme has
already recorded without queueing: **A3 decomposition** is W1-E4's
"interaction follow-up recorded, not queued" given a concrete factorial
shape, and **the W3 prompt-frame follow-up** is what the W3 matrix's
"the carrier question reopens on outcome evidence" implies. Both fit
the charter frame and would each need their own pre-registration,
ceiling and owner go (charter §10). The domain benchmark belongs to
the reviewer's programme: this lab's substrate is domain-neutral by
construction (CargoQuote exists to kill domain priors), and the review
itself specifies the discipline a domain substrate would need
(non-canonical values). The priorities miss is the dropped pilot leg,
noted above.

**The "target architecture" claim, graded box-by-box.** Stage 2's §16
draws a six-stage pipeline — enterprise knowledge → specification
graph (BPMN/DMN/OpenAPI/state/schemas/sequence) → per-artifact
verifiers → cross-spec verifier (conflict/drift/IDs) → context
compiler (task + model specific) → coding agent → independent
verification (contract/acceptance/invariant tests) — and claims "W1–W4
collectively point toward" it. Graded with the value-in-the-sdlc
vocabulary (measured / mechanism / hypothesis):

| Stage in the diagram | What the waves actually say | Grade |
|---|---|---|
| Multi-carrier specification graph (BPMN, DMN, OpenAPI, state, schemas, sequence) | No wave touched BPMN/DMN/AsyncAPI. W1 measured information-*class* marginals at one fixed carrier per class; W3 refuted carrier equivalence for the one class it varied — and the nearest analog to enterprise machine formats, structured YAML at fixed information, was the worst performer (−30.3 pp pooled; opus non-compiling 3/3). Carrier choice is reopened on outcome evidence, per information class — the diagram's lineup is the reviewer's prior, not a wave result | hypothesis |
| Per-artifact verifiers | Sequence gate's input-filter value is measured (cliff, repair waves); EC5 supports "a gate must declare what it cannot see." But W1-E5 (below-cliff vs absent) returned an exact null in a prose-redundant stack — "gates are constitutive" stays the charter's declared risk policy, unstrengthened by W1–W4; verifiers for the other carriers are unbuilt and unmeasured here | mechanism, one leg measured, the necessity leg unresolved |
| Cross-spec verifier (conflict / drift / IDs) | The strongest wave→architecture link: W2's 0/18 means surfacing never emerges — if required, it must be mechanical (agents.md's updated conclusion). Scoped: the structured/majority source won every resolution at this n, the stale example was ignored 12/12, damage stayed local (W2-E5) — the measured case is governance/surfacing, not outcome loss; drift at W2's dose was outcome-harmless; IDs are unmeasured (`trace` is [built], outcome-side unmeasured) | need measured, harm not; IDs hypothesis |
| Context compiler (task + model specific) | The *rationale* is measured: W4 dilution at 1.12–1.45× doses, weak-generator-borne (−26/−32 pp); per-generator knees (opus A3, haiku A4); opus −3.6 at A4. The *mechanism* — task-scoped selection/retrieval — no wave varied; it is the reviewer's own stage-1 "selective-context experiment," still future work | rationale measured, mechanism hypothesis |
| Coding agent | Every measured result is single-shot; W5 exists because §8.4 ("the cliff collapses under agency") is live. The box the whole pipeline routes through is the untested keystone — by the review's own statement, W5 decides how every standing claim must be worded | untested (W5) |
| Independent verification (contract / acceptance / invariant tests) | Deterministic execution over LLM opinion is grounded in the judge-validity record (r ≈ 0.25 same-vendor, ~0 cross-vendor); the hidden/visible separation is designed into W1's partition and W5. No wave has property/invariant arms — that leg is unmeasured | method-grounded; invariants hypothesis |

Two structural observations complete the grading. The derivation runs
backwards: the §16 picture is stage 1's own §19/§26 "specguard"
architecture, drawn before W2–W4 ran; the honest stage-1 → stage-2
diff is that the waves upgraded exactly two boxes from argument to
measured rationale (cross-spec verifier via W2; context compiler via
W4) and confirmed the rest rather than producing it — legitimate
updating, but "collectively point toward" reads as derivation. And the
diagram omits the one lever the lab measured as largest below the
cliff: the author/decision loop (ask-vs-invent ≈ 27 pp executed;
charter §6 — "the conversation is a load-bearing artifact; no stack
row currently captures it"). The pipeline runs fully automated from
enterprise knowledge to code; its only stop-for-humans path is the
conflict hard stop (§2) — but the measured recovery mechanism for
*underspecification* is asking, not verifying, and no box carries it.

**The closing "conceptual lesson", graded.** Stage 2 ends: "The
problem is not maximizing documentation. It is minimizing the amount
of interpretation the AI must perform — while simultaneously
minimizing the amount of irrelevant or duplicated material it has to
process." As a compression it is faithful — arguably the review's most
quotable sentence, and its first half is exactly the charter's own
reframing (Fit, above). Four scopings before this shelf could quote
it. (1) *Attribution:* it is a pre-registered frame **confirmed**, not
a lesson **discovered** — charter §2 E1 formulated minimum sufficiency
before the waves ran, §8.2 was its named falsifier, and W4 is that
falsifier *not firing*; a frame that survived pre-committed
falsification outranks a post-hoc reading, so the review under-sells
the epistemic status of the very sentence it sharpens. (2) *The two
sides carry asymmetric evidence:* the too-little side (supply the
decisions the generator would otherwise invent) is generator-general —
the cliff spans three generators and two vendors — while the too-much
side is, at the measured doses (≤ 1.45×), weak-generator-borne, the
strong generator flat-to-ceiling; the recorded consolidation
discipline (W1-E8a, W4's matrix) requires every consolidated claim to
say so, and this sentence does not. Within the too-much side,
"duplicated" is the weakest leg: accurate redundancy (O1, −6.7 pp
pooled) sat under the programme's 9 pp materiality bar — the measured
breaches were irrelevant (O2) and enumerated (O3) material. (3) *The
two-sided form loses the third mechanism its own headline stated:*
W2's silent arbitration is interpretation of a different kind —
choosing between contradictory sources, performed well and silently —
and folding it into "interpretation" drops the governance point that
made it a finding. (4) *"Zero hallucinations":* the measured record
puts a floor under the ambition (no rung or configuration was
hallucination-free — ≈ 4 judged inventions/run at full companion-spec
detail, ≈ 3.2 even at pristine L5; the with-author repair arm halved
invention, 98 → 45, without eliminating it), and the measured
below-cliff recovery mechanism is *asking* — routing absent decisions
to a human — which neither "minimize interpretation" nor "minimize
material" expresses. The reviewer's own programme phrased the honest
target better than its closing line does: zero *undetected,
unauthorized* invention.

## What this evaluation records (candidates, nothing queued)

**Doc-hygiene candidates — claim language and boundaries, no product
behavior:**

1. **Reconcile the Level-5 name with the settled claim language.** The
   contradiction is real: `pumllint/scoring.py:54` and the score-JSON
   schema enum say "Generation-ready"; SCORING.md §9, case-for's
   honesty note and agents.md say the level *means* method-convention
   complete, and agents.md flatly states it is "deliberately not
   called 'generation-ready'". Two honest resolutions: rename the
   level (the review suggests Codegen-constrained /
   Specification-complete; "Method-complete" would match the settled
   description verbatim) — a **public-contract change** touching the
   schema enum, scoring.py, test_scoring.py + the BDD feature, the
   README/SCORING/case-for/findings-and-scores sweep and a regenerated
   example report, so it takes its own deliberate decision; or keep
   the name and fix the sentences that misdescribe it (cheap, but
   preserves the tension the reviewer tripped over). Minimum honest
   fix either way: agents.md's "deliberately not called" sentence must
   stop being false.
2. **State EVIDENCE.md's boundary.** One scope paragraph: EVIDENCE.md
   is the sequence-maturity product-evidence record; the stack
   programme's primary records are the wave pre-registrations'
   § Results with the charter as synthesis. This also serves the
   charter §7 commitment that the waves converge on one consolidated
   document — the boundary note is that document's placeholder.
3. **Tighten case-for-pumllint's problem statement.** "No automated
   check catches any of these today" gains the survey scoping the same
   document already uses ("nothing we could find", with the honesty
   note). The SDD-checks sentence is accurate as scoped to the named
   tools; an optional precision ("the quality checks those tools
   themselves provide") would close the reading the reviewer
   demonstrated.

**Wave candidates, recorded under charter discipline (own
pre-registration, ceiling and go if ever queued):** W3b — carrier ×
prompt-frame factorial separating intrinsic carrier effect from
prompt-carrier alignment; A3 decomposition — contract information
classes (companion spec, decision tables, OpenAPI, state model)
isolated factorially. Both were already implied by the frozen records'
own follow-up language; the review supplies their concrete shapes.

**Explicitly not for this repository** (the reviewer says so too):
BPMN/DMN/AsyncAPI carriers, the cross-spec verifier platform, the
unsupported-behaviour-coverage metric, the context compiler, document
metadata systems, the domain benchmark. They belong to the adopter
programme; where repo-side analogues exist they are the shipped
`trace`, the census/pilot kit, and agents.md's ladder — all
demand-gated as recorded.

*The decision record lives in ROADMAP.md § Settled questions; this
note is the evidence behind it.*
