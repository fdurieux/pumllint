# The SDD + generation-manifest recommendation, evaluated

*Dated fit evaluation, 2026-08-10. An externally authored recommendation
on AI-assisted code generation across the full SDLC — adopt spec-driven
development (SDD) with PlantUML user journeys and process models as
first-class requirement inputs; govern the generation toolchain with a
docker-compose-style manifest plus lockfile plus per-run records (its
working title: "llm-stack"); wire this tool in twice, as the input gate
before generation and as a deterministic assertion on generated
diagrams — was evaluated element-by-element against the working tree at
v0.26.0 and this project's decision records. The recommendation reached
the owner as a chat-authored analysis produced without repository
access, and that provenance shows. Verdict up front: **direction
corroborated, specifics stale. It independently re-derives the shape of
Arcs G–J and the two-repo split — another external convergence on
this plan — but its foundation phase designs a feature that shipped
twelve days earlier (`pumllint trace`), two of its three tool-roadmap
items already ship, its example "novel" contractual rules are shipped
rules, and its public-demand premise is contradicted by this repo's own
pre-registered demand scan. Two genuinely new candidates are recorded,
nothing is queued, no build trigger fires.** The decision record lives
in ROADMAP.md § Settled questions; this note is the evidence behind it.*

## Why this evaluation ran

Same reason as the spec-stack evaluation (2026-07-29): externally
authored recommendations in this territory get verified before any of
their content becomes work — the verify-absence rule. This one arrived
with a concrete six-phase build plan attached (~8–10 working sessions),
which raises the stakes of *not* checking: executed as written, the
plan would have re-designed one shipped feature, re-derived one shipped
architecture, and re-measured settled evidence. Recording the check
prevents re-litigation and keeps the parts the recommendation actually
contributes.

## What the recommendation says (compressed, so this note stands alone)

1. **The asymmetry claim.** SDD (Spec Kit-style: specify → plan →
   tasks → implement) rigorously versions the *spec* while leaving the
   *generator* — model snapshot, parameters, prompts, tool config —
   unversioned. When output changes, current tooling cannot answer
   "did the spec change or did the compiler change?" A manifest +
   lockfile + run-record triad closes the gap: spec hash × lockfile
   hash → output hash, per run.
2. **The pipeline.** Requirements as `.puml` journeys and process
   models plus EARS-style acceptance criteria → an SDD spec layer →
   generation governed by the manifest → verification (eval gates plus
   this tool).
3. **This tool's role.** Input direction: lint `.puml` before anything
   consumes it. Output direction: a deterministic assertion over
   LLM-generated PlantUML — with an explicit warning against
   LLM-judge-only gating.
4. **Three tool-roadmap implications:** configurable rulesets, an
   extension point, machine-readable output (JSON or SARIF plus
   meaningful exit codes).
5. **Six elaboration areas** (traceability/ID scheme; a three-tier
   rule taxonomy ending in a "contractual" tier; the
   parsed-vs-interpreted boundary; change impact; a scope threshold;
   an eval corpus) and a six-phase plan with phases 1 → 2 → 6 on the
   critical path.

## Verified element-by-element (the verify-absence scorecard)

| Its proposal | Working-tree fact |
|---|---|
| Phase 1 (its foundation): design stable IDs, decide inline-vs-sidecar, enforce presence and uniqueness — "the chain is asserted but not designed" | Shipped: `pumllint trace` (v0.25.0) — the coverage matrix in three directions, `--pattern` as the configurable ID grammar, `--requirements`/`--requirements-scan` inventory input, JSON with `pumllint schema trace`, three opt-in exit-code gates; reference carriers shared with GEN007 by construction; the JSON shape designed to extend toward the full requirement → process step → rule → component → contract → verification matrix without breaking v1 (Arc G) |
| "pumllint needs a config file: rule selection, severity, ID grammar as a parameter" | Ships: config auto-detection (toml/json/yaml), `--profile`, per-rule severity and patterns, dormant-until-configured convention rules (GEN006/007, UC002, ACT006) |
| "Needs machine-readable output — JSON or SARIF plus meaningful exit codes; the one thing worth speccing early" | Ships: JSON/sonar/badge/HTML reporters, report shapes schema-pinned since 0.18.0, exit codes documented and identical local/CI (0/1/2). SARIF specifically: absent, demand-gated like every other format request |
| "An extension point / plugin mechanism, deferred but not precluded" | Consciously parked, not undecided: the optional-extras door and the dormant-by-default rule pattern are the recorded posture until real pull |
| "Tier-3 contractual rules are the novel part nobody has" — examples: no orphaned actors, every branch covered, criterion IDs present | The codegen profile *is* that tier (SEQ101–109, blocker-grade); the named examples ship as UC001, ACT003/SEQ105/SEQ107 and GEN007; the deeper versions are specced and deliberately gated (obligations SEQ110–113 + ARC001–003; flow SEQ201/203) |
| A three-tier taxonomy: syntactic / conventional / contractual | A coarser re-derivation of the shipped architecture: six dimensions × severities × profiles × maturity levels |
| Phase 3: design the parsed-vs-LLM-interpreted boundary; skeleton the analyst agent's instruction file | Drawn and written: the deterministic-product-path working agreement, Arc H's verbalizer spec, and docs/agents.md (the ask-never-invent covenant, the precedence-of-evidence ladder) |
| Phases 5–6: build an eval corpus, gate with Promptfoo, "let the pilot reveal which rules catch defects" | The lab exists (pre-registration, frozen drivers, executed oracles, budget norms, the corpus-firing chassis); the warning against LLM-judge gating is a *measured result* here (judged↔executed r ≈ 0.25 / 0.002), not a caution. What is genuinely missing is only real-corpus cases — which is the census/pilot, the ROADMAP's standing next action; the which-artifacts-suffice question behind its eval-corpus idea is meanwhile a chartered lab program of its own (docs/research-charter.md, W0 kits shipped 2026-08-06) |

## Where it is wrong, and where it corroborates

**Corrected — public demand.** "The SDD community is already circling
this territory" (model-driven inputs to spec pipelines) is contradicted
for PlantUML by the pre-registered demand scan
([demand-scan-embedded-plantuml.md](demand-scan-embedded-plantuml.md)):
≈0.2% genuine embedding against a 2% bar, 0/25 sampled spec-kit repos,
Mermaid ahead 76–437× in the same directories. The fit is real where
EA-grade PlantUML already exists — a pilot-context fact, not an
ecosystem trend.

**Corrected — the compiler analogy.** "SDD gives you source control;
the manifest gives you the pinned toolchain" overclaims. Hosted model
snapshots retire, and generation is nondeterministic even fully
pinned — the same fact that makes unattended promote-on-delta
statistically unsound (ROADMAP § Settled questions). The triad
therefore yields **attribution for audit, never reproducibility**: it
answers "which spec, which generator, which output" after the fact; it
cannot re-produce the output. For a regulated adopter, attribution is
still precisely the point — but the claim language must say
attribution.

**Sourcing note.** Its industry framing rests on practitioner-tier
aggregators, including a tools-that-shipped-SDD enumeration checked
against no primary source — the pattern the landscape research was
burned by once and now guards against (a previously published
enumeration was refuted on primary documents; see
[sdlc-tooling-landscape.md](sdlc-tooling-landscape.md), revision
notes). Nothing load-bearing in this evaluation rests on those
citations; every verdict above grounds in repo records.

**Corroborates.** Written without repository access, it converges on:
per-artifact gating upstream of generation (Arcs G–J's premise); a
stable-ID traceability spine (Arc G); deterministic assertions over
LLM-judge gating (the evidence program's core result); a separate
pilot/application repo with a small interface back to the tool; and
its own cautions — visual notation is not a formal specification
language, ceremony has cost, don't design the universal DSL upfront —
which match the settled claim language and the promote-on-delta
rejection. Independent convergence is evidence the direction is
natural — a recurring pattern in these records: the spec-stack
evaluation (2026-07-29) converged the same way, and the
model-verification evaluation (2026-08-02) found its external note
likewise describing the already-shipped architecture.

## Recorded, not queued

1. **A portable run-record / generation-manifest format.** The lab
   already practices the discipline ad hoc — protocols and analyzers
   frozen in commits before scored runs, costs and model identities in
   EVIDENCE.md, manifest-aware per-unit profiles in the corpus-firing
   chassis — but no reusable format for adopter generation runs
   exists (verified: none in ROADMAP.md or docs/agents.md; the nearest
   artifact is the lab's wave pre-registration template,
   stack_experiment/PREREGISTRATION_TEMPLATE.md, scoped to measurement
   waves, not generation-time provenance). If a real pilot stabilizes
   one, that format becomes the first observed convention for the
   prompt/agent-config-linting adjacency, whose settlement notes "no
   convention exists to lint against" — at which point that trigger is
   re-examined. A pilot-repo artifact; nothing is built here before
   then.
2. **Model→spec change impact.** When a diagram changes, which spec
   sections, tasks and code regions are invalidated? Nothing in Arcs
   G–J covers invalidation semantics; `trace`'s link table is the
   substrate an impact design would build on. Write the design note
   only after at least one real diagram-edit event has flowed through
   a pilot pipeline — before that it is speculation.
3. **The scope threshold** it asked for ("when does this machinery
   apply vs. plain prompting") — absence verified this pass, then
   resolved immediately: written as the phase-4 scope test in
   [the pilot charter](pilot-charter.md), because that is the document
   the audience of that rule actually reads.

## Sequencing recorded (gates preserved)

Census and conventions workshop first — the standing next action, and
the demand instrument every gated item waits on. Trace adoption if an
ID convention emerges (zero build). Only if the charter's phase 4
(AI-generation scope) activates: a pilot repo inside the adopter's own
infrastructure, consuming the shipped, schema-pinned contracts — then
the manifest thin slice and one requirement end-to-end under
pre-registered decision rules and a stated budget ceiling; the
change-impact note after a real edit event; a decision gate filing
trigger observations back into ROADMAP § Settled questions. Kill-gates
at the census (no ID convention → the traceability thread stops, and
that is a result, not a failure), at phase-4 activation, and at the
decision gate. An EARS-shaped acceptance-criteria file written for a
piloted requirement doubles as the recorded re-litigate trigger for
the parked requirements DSL — "a concrete adopter with a requirements
corpus".

## Decision and triggers

**Recorded; no build starts from this note.** The recommendation's
plan phases 1–3 are declined as already shipped or settled; its
Promptfoo layer is declined as duplicating the in-repo lab; SARIF and
a plugin mechanism stay demand-gated. Re-litigate on: a
pilot-stabilized manifest format (re-examine the prompt-config-linting
adjacency); a real edit event through a pilot pipeline (write the
change-impact design); or public evidence of PlantUML-first SDD
adoption at scale (which would flip the demand-scan reading this note
relies on).
