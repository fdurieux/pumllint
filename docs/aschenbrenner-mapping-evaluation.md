# *Situational Awareness*, mapped onto pumllint — the mapping evaluated

*Dated evaluation, 2026-08-01, written against `72cf222`
(post-v0.26.0). An externally authored analysis mapped Leopold
Aschenbrenner's *Situational Awareness* (June 2024) — a forecasting and
geopolitics essay, not an engineering document — onto this project
against a four-level capability ladder (Narrow AI → General-purpose AI →
AGI → ASI), and asked for a sense/nonsense verdict on its own mapping.
Verdict up front: **sense, with corrections. The mapping's conclusions
stand — maximum relevance in the current capability band, a governance
hedge that outlives the ambiguity-service window, the evidence harness
as the instrument that measures the window — but two of its citations
cannot be traced to any primary source on record, one artifact name is
wrong, one falsification claim is premature, and in several places it
argues by analogy where this repository holds measurements.** Bounds:
repo-internal claims were verified against the working tree; the essay
is characterized from its published text; the mapping's untraceable
citations are flagged below and carry no weight in this note.*

## Why this evaluation ran

This is the third externally authored analysis to be verified under the
house discipline (after the prose-pipeline reassessment and the
spec-stack recommendation, both 2026-07-29). Unlike those, it proposes
no build: it evaluates the product thesis's **capability horizon** — a
dimension the records cover only implicitly, in the multi-model
evidence waves and in the auto-improvement settlement's warning that a
fitness measurement "silently decays when the generation model version
changes." If the thesis is capability-relative, that fact and its
measuring instrument belong in a record, not in a conversation.
Verifying the mapping and recording the verdict prevents re-derivation.

## What the mapping says (compressed, so this note stands alone)

**Three essay elements transfer; the rest is analogy.**

1. *Unhobbling* — Aschenbrenner's term for capability gains that come
   from removing constraints around models (scaffolding, tools,
   context) rather than from the models themselves. The mapping calls
   pumllint "artifact-side unhobbling: it doesn't make the model
   smarter, it makes the input decidable," and cites the OpenAI
   harness-engineering account as industrial confirmation.
2. *The drop-in remote worker* — the essay's operationalization of AGI
   as fully delegable agents. The mapping: single-prompt full
   delegation (citing an Anthropic Economic Index "median 1 prompt"
   figure) removes iterative correction, so the upfront artifact
   carries the whole burden — "the SEQ100 thesis stated from the
   capability side."
3. *Counting the OOMs* — kept only for its second-order implication:
   better instruction-following makes vague or contradictory specs
   *more* damaging (the GPT-5-prompting-guide argument), so capability
   growth raises the stakes on spec quality — until it doesn't, which
   is the mapping question.

**The ladder mapping.** *Narrow AI*: no relevance — template-era
codegen needed no separate semantic gate, and pumllint is deliberately
deterministic tooling, the complement of AI rather than an instance.
*General-purpose AI (today, "inconsistent across areas")*: maximum
relevance — the regime where "almost right" failures dominate and
ambiguity measurably degrades outcomes; all of pumllint's evidence
lives here. *AGI*: transitional — a model matching capable humans
could resolve ambiguity itself, but *silently*; capability doesn't
restore the inquiry function, it hides its absence. Rules checking
intent clarity (DIM-AMB-style) lose ground; rules enforcing declared
policy (obligations, architecture conformance) survive as governance
instruments, and the gate's value shifts from "the model needs this"
to "the organisation needs this auditable." *ASI*: no engineering
payload; the essay's intelligence-explosion, security and geopolitical
chapters do not transfer.

**Its conclusion.** The sense: the essay independently supplies the
frame the vendor and research literature converged on — capability
gains shift human work toward specification and verification, and
mechanical checking of the artifacts at that interface is unhobbling
infrastructure. The nonsense: importing the essay's timelines or
superintelligence machinery into product reasoning; the mapping reads
the AGI-by-2027 trajectory as "not borne out as of mid-2026," which
widens the window where the tool's value peaks. Net: pumllint is a bet
on a window, with a hedge — the obligation/architecture designs are
the part that outlives the window. The falsifiable version: the
premise holds as long as ambiguity degrades generation more than model
capability compensates, measurable per model generation with the
fitness harness.

## Corroboration map — its claims against this repo's records

| Its claim | This repo's independent record |
|---|---|
| Value comes from engineering around the model, not the model | OpenAI harness-engineering account (sdlc-tooling-landscape rev. 3): architectural constraints "enforced mechanically via custom linters," lint errors feeding fix instructions back to the agent — with an artifact-class caveat the mapping drops (correction 5) |
| Ambiguity measurably degrades generation today | SWE-bench Verified: 38.3% of real issues underspecified; SpecFix (ASE 2025): +30.9% Pass@1 on repaired descriptions; this repo: hard-demand partial r ≈ 0.65–0.70, below-Level-2 executed cliff 21.9 pp pooled across three generators and two vendors (EVIDENCE.md) |
| Capability growth raises the stakes on spec quality | Both citable vendor guides converge (landscape rev. 3): "as generation gets more precise, ambiguous or contradictory inputs get more expensive, not less" |
| Silent resolution hides the missing inquiry function | Measured interventionally, not just argued: author-less repair (invention) −5.9 pp below the cliff, with-author +21.5 pp — asking vs. inventing ≈ 27 pp executed (EVIDENCE §Agent-repair); and X-R4: every repaired diagram passes the gate — "an input filter, never a content certifier" |
| Declared-policy rules survive; inferred-intent checks are capability-bound | The obligation/flow settlement (ROADMAP, 2026-07-30): the participant-pair sweep rejected *because no oracle exists without a declared policy table*; declared obligations (SEQ110–113) and architecture conformance (ARC001–003) decidable and specced, adopter-gated |
| The gate's value shifts toward organisational auditability | Already the shipped posture: `pumllint trace`, suppression disclosure, baseline/ratchet trends; DORA's verification-tax and guardrails framing (landscape rev. 2) is organisational, not model-facing |
| pumllint is deliberately not AI — the complement | Working agreement: "the product path is deterministic end-to-end"; no LLM call ever ships inside the product |
| The premise must be re-measured per model generation | The auto-improvement settlement already encodes it: fitness measurements decay on model-version change; measurement yes, unattended promotion never |

## Corrections

1. **"Orchid" is untraceable.** The mapping cites "(Orchid, SpecFix)"
   for ambiguity degrading pass rates. SpecFix is on record
   (ASE 2025, arXiv 2505.07270, verified in the landscape doc's
   rev. 3). "Orchid" appears nowhere in this repository's sources and
   could not be identified as a real study in this pass. Under the
   house rule — every load-bearing claim verified against its
   primary — it carries no weight until a primary is supplied. The
   claim it was drafted to support stands anyway, on SWE-bench
   Verified and SpecFix.
2. **The AEI "median 1 prompt" figure is conversation-side.** Nothing
   in this repository's evidence base carries it. It is directionally
   consistent with the Anthropic Economic Index's published
   automation-vs-augmentation findings, but the specific statistic
   needs its primary cited before it bears the delegation argument.
3. **"Phase 2 fitness harness" misnames a built artifact.** In the
   recorded phase numberings, Phase 2 is either the conformance gate
   (prose-pipeline evaluation — explicitly *not* an arc, because it
   already shipped) or the obligation/flow rule builds (Phases 2–4,
   adopter-gated). The instrument the mapping means is the **Arc D
   harness** — `tools/codegen_experiment.py` plus the frozen
   acceptance suites in `tools/acceptance/` — which is built, and is
   the instrument behind every evidence wave on record (original,
   deepening, execution-oracle, agent-repair, cross-vendor). Nothing
   about the window measurement is pending except running it again
   when models change.
4. **"Not borne out as of mid-2026" is premature falsification** — an
   ironic defect in a text that ends by demanding falsifiability. A
   2027 claim can be *behind schedule* in mid-2026; it cannot yet be
   scored false. The inference it feeds — the high-value band is wider
   than the essay projected — survives on the weaker, honest phrasing.
5. **The harness-engineering citation drops this repo's own recorded
   caveat.** The landscape doc reads that account as corroborating the
   *mechanism* (mechanically checked in-repo artifacts) while
   cautioning on the *artifact class*: at that team's scale "the
   designs were written, not drawn" — no hand-authored models anywhere
   in the tree. Citing it as clean industrial confirmation of a
   diagram linter over-claims relative to the repo's own record.
6. **The AGI row's mechanism smuggles in a disposition assumption.**
   "Could resolve ambiguity itself — but silently" assumes
   human-level systems retain today's don't-ask disposition; capable
   humans resolve ambiguity by *asking* when stakes warrant, and
   whether future models do is a product decision, not a capability
   fact. The argument that survives any disposition — and the better
   one for the row — is that even a *correct* silent resolution
   breaks spec↔implementation traceability: the artifact no longer
   says what the system does, which is precisely the auditability
   need the row lands on. Relatedly, "decidable at any capability
   level" mis-sorts the rules: DIM-AMB checks are exactly as
   deterministic as the declared-policy checks. What is
   capability-relative is their *payoff* — whether their findings
   still predict downstream failure — not their decidability. The
   mapping's own falsifiable-version paragraph gets this right; its
   table cell does not.
7. **The delegation argument is half-stated.** Single-prompt
   delegation is where the gate's value peaks — but this repo ran the
   author-less arm explicitly as the *worst case*, and its best
   measured outcome is the with-author Q&A loop (repaired-L1 executed
   0.857 vs 0.583 author-less). The honest framing keeps both halves:
   the delegation regime raises the gate's value, *and* the recipe's
   whole point (docs/agents.md, ask-never-invent) is to refuse that
   regime's silence by keeping an author reachable.
8. **Crown-jewel provenance.** The recorded line (prose-pipeline
   evaluation) assigns crown-jewel status to SEQ101–109, not the
   harness. Reassigning it to the harness is the mapping's own
   judgment — defensible (Arc F is viable *because* the harness
   exists; every external critique to date was answered with a wave,
   not an argument) — recorded here as a judgment, not an echo.

## Where the mapping under-claims — measurements it argued past

- **Scaffold-resistance is the measured form of "artifact-side
  unhobbling."** The execution-oracle wave found entry-contract
  pinning lifts moderately degraded diagrams to ≈ pristine but does
  not rescue below-cliff diagrams — "prompt engineering cannot restore
  guards and failure paths the diagram never specified"
  (EVIDENCE.md). That is the strongest available version of the
  mapping's own unhobbling claim: artifact quality is not
  substitutable by harness-side scaffolding, so gating the artifact is
  not one more scaffold.
- **The window trend line already has data points.** Under the same
  judge, the judged-fidelity cliff narrows only modestly from the
  weaker to the stronger generator (haiku 15.5 → opus 12.7 points);
  on the vendor-neutral executed oracle the cliff is statistically
  indistinguishable across vendors (opus pooled 21.9 pp, gemini
  20.9 pp). D2's recorded reading — "a weaker generator compensates
  less … the gate matters more, not less, for cheaper models" — has a
  contrapositive that bounds the band: within 2025–26-era models,
  capability compensation is real but marginal. The window is
  measurably not closing yet; the mapping presents as future
  measurement what is already a seeded trend line.
- **The inquiry-function claim is a replicated experiment here, not a
  critique.** Asking vs. inventing ≈ 27 pp of executed correctness
  below the cliff, from paired interventional arms (EVIDENCE
  §Agent-repair). The mapping cites the argument; the repo holds the
  measurement.

## One sharpening adopted: the window, defined by consumer failure mode

The Narrow and AGI rows are empty or transitional for the *same*
reason, and naming it defines the window more precisely than the
ladder does. Deterministic consumers — MDA-era generators, compilers —
**reject** malformed input loudly: the toolchain was its own gate, so
no separate one was needed. Today's probabilistic consumers **absorb
and confabulate**: failure is silent and plausible (DORA's
verification-tax clause — output "that looks remarkably similar to
correct code" — and this repo's below-Level-2 result: fidelity down by
roughly a third, invented business logic doubled). A hypothetical
inquiry-capable consumer would **repair** — at which point the
surviving requirement is that resolutions be on the record, not in the
model's head. pumllint's high-value window is exactly the
absorb-and-confabulate regime; the declared-policy packs serve any
regime in which an organisation states standards worth enforcing.

## The falsifiable premise, recorded

**Premise:** pumllint's generation-gate thesis holds as long as
ambiguity and incompleteness degrade generation more than model
capability compensates. **Instrument:** the Arc D harness, re-run per
model generation — the same discipline the auto-improvement
settlement already mandates for any fitness claim (quote correlations
and per-oracle cliffs; never merge judged and executed numbers).
**Current state:** three generators across two vendors show at most
marginal narrowing (previous section). **Response protocol if a wave
shows material narrowing:** that is the window-closing signal — the
recorded hedge activates as a *positioning* shift toward the
governance packs (obligations, architecture conformance,
traceability), decided by a human over the evidence dossier, never by
an unattended loop; the ambiguity-service rules remain shipped and
decidable, with their claim language re-scoped to match what the
current wave supports.

## Terminology hygiene

The mapping's four-level **capability ladder** is its own
(conversation-side) frame and lives nowhere in this repository. It
must not be conflated with DORA's **AI Capabilities Model**
(sdlc-tooling-landscape rev. 2), which names seven *organisational*
capabilities that moderate AI's value, not capability tiers of models.
Any future doc citing either should keep the names apart.

## Decision and triggers

**Recorded; nothing queued; nothing in the plan changes.** The hedge
the mapping recommends already exists as the gated obligation/ARC
designs; the instrument it calls for already exists as Arc D practice;
the auditability positioning is already shipped surface (`trace`,
suppression disclosure, ratchet). Triggers: (a) primaries supplied for
the two untraceable citations upgrade or retire those claims —
until then they are not to be repeated in repo docs; (b) a future
evidence wave showing the executed cliff materially narrowed fires
the response protocol above — a reviewed decision, never automatic;
(c) the obligation/flow and pilot-census triggers recorded in the
ROADMAP are unaffected by this note and fire on their own terms.
