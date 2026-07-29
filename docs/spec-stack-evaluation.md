# The AI-ready specification stack, evaluated

*Dated fit evaluation, 2026-07-29. An externally authored recommendation
on preparing specifications for AI-assisted code generation — a layered
artifact stack (feature spec, glossary, process variants, Gherkin, DMN,
C4, sequence diagrams, API/event contracts, state models, ADRs, quality
scenarios, repo instructions, tests, traceability map) with the operating
principle "L2 for context, L3 for behavioural scope, atomic system
responsibilities for implementation boundaries, executable
contracts/tests for precision" — was evaluated against this repository's
evidence and decision records, in the frame of semantic hardening of
SDLC-upstream artifacts. Verdict up front: **sense — it independently
corroborates most of this project's standing decisions, and this repo
holds interventional evidence for its central thesis that is stronger
than the correlational studies it cites. Its one structural blind spot
is exactly this project's category: every artifact in its stack is
mandatory to *exist*, but only code gets a verification gate.** One new
candidate is recorded (not queued), two Arc G refinements and one
docs/agents.md addendum are adopted; nothing else in the plan changes.
Repo-internal claims verified against the working tree; the
recommendation's external citations were checked for consistency with
prior research passes here, not re-fetched against primary sources this
pass.*

## Why this evaluation ran

The recommendation reached the owner as advice for organizing
specification artifacts upstream of AI code generation — the same
territory as the tooling-landscape research (which positioned
deterministic verifiers for AI-read artifacts as the pipeline's
under-built layer) and the prose-pipeline evaluation (Arcs G–J). If a
mainstream, well-sourced recommendation of this kind contradicted the
plan, that would matter; it turns out to *corroborate* the plan at
nearly every point of contact, and its blind spot sharpens the
project's positioning claim. Recording both prevents re-derivation.

## What the recommendation says (compressed, so this note stands alone)

1. The best preparation for AI codegen is not more documentation but a
   **layered, traceable, partly executable specification in which the
   AI has fewer decisions left to invent** — a chain from customer
   outcome through process, behaviour/rules, architecture/contracts, to
   code and automated verification.
2. **"Diagrams provide orientation; contracts, schemas, examples and
   tests provide constraints."** Its evidence: a repository-level study
   naming insufficient requirement understanding and missing project
   context as principal causes of code hallucination (arXiv 2409.20550).
3. A **fourteen-row artifact stack**, each row mandatory in its scope,
   each mapped to the failure it prevents (invented scope, invented
   APIs, illegal state transitions, silently replaced architecture, …).
4. **Process-level discipline**: L2 process for scope, L3 variant as
   the minimum useful level for feature generation, atomic system
   responsibilities before implementation; below that, express detail
   through contracts, decision tables, state models, sequence diagrams
   and tests — not by decomposing prose further.
5. **C4 posture**: Context + Container as the maintained baseline,
   Component only for the container being changed, code-level diagrams
   rarely; sequence diagrams for every architecturally important
   interaction including rejection, timeout and compensation paths —
   and they should reference real `operationId`s, event names and
   components, "otherwise it remains explanatory rather than
   constraining." Prefer text models (C4-PlantUML, Structurizr DSL,
   PlantUML, Mermaid) over images.
6. **DSL per concern**: BPMN for coordination, Gherkin (declarative)
   for observable behaviour, DMN for decisions, OpenAPI/AsyncAPI +
   schema languages for contracts, state tables/SCXML for lifecycles,
   IaC for infrastructure — rather than one heavy formalism.
7. **Traceability as "the missing artifact"**: a stable-ID matrix
   (requirement → process step → rule/scenario → component → contract →
   verification), machine-readable (YAML/JSON), synchronized from the
   organization's canonical process repository into the code repo so an
   agent can retrieve only the relevant context.
8. **Repository instruction file** (AGENTS.md-style) with commands,
   conventions, boundaries, definition of done — plus an explicit
   **precedence of evidence** (approved contracts/tests > feature spec
   > ADRs > source > process docs > general docs) and the rule that an
   agent must never resolve a conflict between sources silently.
9. **Tests as the strongest practical control**, citing a study where
   supplying tests during generation improved correctness 9.15–29.57%
   (function-level benchmarks; arXiv 2402.13521), with the warning that
   incomplete tests become an incorrect oracle; protect acceptance
   tests from being rewritten to make generated code pass.

## Corroboration map — its recommendations against this repo's records

| Its claim | This repo's independent record |
|---|---|
| Fewer decisions left to invent | The codegen pack's purpose (SEQ101–109); measured interventionally: invention is net-negative below the cliff, ask-vs-invent ≈ 27 pp executed (EVIDENCE §Agent-repair) |
| Execution as the control; weak tests = wrong oracle | Execution-oracle wave; judged ≠ executed (r ≈ 0.25 within-vendor, ≈ 0.002 cross-vendor); oracle-quality note in ROADMAP § Settled questions |
| Protect acceptance tests from the implementer | Arc F's implementer diff gate — the oracle is read-only for the agent that must satisfy it |
| Sequence diagrams must cover rejection/timeout/failure paths | SEQ107 (missing failure path), SEQ104/105/106 — the mechanical form of the same checklist |
| "Reference real `operationId`s, else explanatory not constraining" | SEQ103 (prose-message) is the lint for exactly this; C4 detail ladder: behavioral content +29 pp executed |
| C4 Context + Container as the baseline forms | C4 pack evaluation — fit verified, census-gated |
| Text models over images | The category precondition (parse → model); demand scan recorded the ecosystem split, Mermaid as a sibling stack under the Arc E bar |
| Stable-ID traceability matrix, machine-readable | Arc G, ship-first — independently derived here as the pipeline's "empty niche" |
| Repo instruction file; never resolve conflicts silently | docs/agents.md drop-in block; the ask-never-invent covenant, measured; precedence addendum adopted from this recommendation (2026-07-29) |
| DSL per concern, no heavy formalism | Reinforces the parked purpose-built requirements DSL (EARS/SBVR lesson, prose-pipeline evaluation) |

## One sharpening: the orientation/constraint line runs *through* artifacts, not between types

Its crispest sentence — diagrams orient, contracts constrain — is right
as a default and wrong as a taxonomy, and this repo measured the
boundary. The C4 detail-ladder experiment moved *executed* outcomes
+29 pp with behavioral content inside diagrams; the sequence evidence
puts ~21.9 pp of executed correctness between constraint-grade and
orientation-grade diagrams of the *same type*. The recommendation
concedes this without noticing, in its own `operationId` sentence:
whether a diagram constrains is a **property of its semantic precision,
and that property is mechanically checkable** — it is what the maturity
levels measure and what the codegen profile gates. Constraint-grade vs
orientation-grade is a level, not a genre.

## The structural gap: mandatory-to-exist is not mandatory-to-be-sound

Only one row of its stack gets a gate (tests/CI, for code). For every
upstream row, existence is treated as sufficiency — and its own
flowchart places "Automated verification" once, *after* "Code". This
repo's evidence says the omission is not merely incomplete but risky:
below Level 2, diagrams **actively degrade** generation (fidelity down
by roughly a third, invented business logic doubling, 21.9 pp executed
cliff). A mandated artifact stack without per-artifact verification
feeds the generator orientation-grade inputs dressed as constraints —
compliance theater with measured downside. The hardening layer mostly
exists per artifact class (schema validation and Spectral-style linting
for OpenAPI/AsyncAPI, DMN validation, executable Gherkin, this tool for
the PlantUML/C4 slice — the only deterministic checker for hand-written
files, per the C4 evaluation); the recommendation simply never
assembles it. The one-sentence fix to its model, and this project's
positioning claim in its frame: **each artifact in the stack ships with
its verifier, and a feature package is not generation-ready until its
artifacts pass their gates.** Its "minimum AI-ready feature package"
checklist is itself lintable — file presence plus stable-ID
cross-referencing is exactly the shape of Arc G's matrix generalized to
the package level (recorded as an observation, not a build item).

## What changes here

- **Arc G refinements (adopted).** The requirements-inventory input
  explicitly accepts a structured snapshot file (ID list in
  text/JSON/YAML) — in practice the synchronized export from a
  canonical process/requirements repository, which is where the ID
  universe lives in a real deployment — alongside the pattern-scan
  path; and the JSON report schema keeps stable IDs first-class so the
  matrix can extend toward requirement → process step → rule →
  component → contract → verification without breaking the v1 shape.
- **New candidate, recorded not queued: sequence ↔ contract
  cross-check.** Verify that sequence-diagram message signatures
  correspond to real operations in an OpenAPI/AsyncAPI document (the
  XD family's identity discipline extended across artifact classes).
  The lighter cousin of the parked diagram↔code conformance item: the
  target is machine-readable data, not an implementation language
  (JSON parseable with the stdlib; YAML via the same optional PyYAML
  the config loader already uses). Trigger, mirroring the conformance
  item: a user with both artifact classes in one repo asking to gate
  drift between them.
- **docs/agents.md addendum (adopted).** The precedence-of-evidence
  ladder and the never-resolve-conflicts-silently rule join the agent
  recipe — this repo had measured *why* asking wins but had no
  tie-breaking protocol for conflicting sources; the recommendation
  supplies one.
- **Nothing else moves.** The C4 pack stays census-gated (its C4
  mandate is the demand shape the census detects), Mermaid stays a
  recorded sibling stack, the purpose-built requirements DSL stays
  parked — reinforced, since the recommendation's own DSL-per-concern
  table shows the ecosystem already covers each concern with tooling a
  new DSL would have to beat.

## Citation check (bounded)

The two load-bearing studies (arXiv 2409.20550 on hallucination causes
and repository context; arXiv 2402.13521 on test-driven generation) are
real and characterized accurately, with one caveat to carry: the
9.15–29.57% test-supply improvement is from function-level benchmarks,
not repository-level work. The C4, Cucumber, OMG BPMN/DMN, arc42, ASVS
and GitHub-instructions references are used within what those sources
say. None of this was re-fetched against primary sources this pass;
directional confidence is high, figures are quoted as the
recommendation's own.

## Decision and triggers

**Recorded; no build starts from this note.** The adopted refinements
land in ROADMAP Arc G and docs/agents.md in the same change as this
note. Re-litigate on: the sequence↔contract trigger firing (build
decision then follows the Arc C/E bars); or evidence that a mandated
artifact stack *without* per-artifact gates performs adequately — which
would weaken the positioning claim this evaluation sharpened.
