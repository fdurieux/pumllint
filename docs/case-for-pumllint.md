# The case for pumllint

*Audience: IT management, architecture leads, quality/governance owners.
What's in it for you, what it costs, and what the evidence actually supports.*

## The problem

Your teams document designs as PlantUML diagrams: sequence flows, class
models, state machines, use cases. Those diagrams drive reviews, onboarding,
audits — and increasingly, AI-assisted code generation. But PlantUML is, by
its own admission, a drawing tool, not a modeling tool. It happily renders:

- a message to `Custmer` — a typo that silently becomes a phantom participant;
- an `alt` branch guarded by "sometimes";
- a class hierarchy with an inheritance cycle;
- the same service called `OrderService <<service>>` in one diagram and
  `orderService <<gateway>>` in another.

None of these fail any build today. Each one costs you later: review time
spent decoding intent, wrong assumptions propagating into implementations,
and — if the diagrams feed a code generator or an AI coding agent — invented
behaviour filling the gaps.

## What pumllint is

A semantic linter for PlantUML, in the same product category as ESLint or
SonarQube rules for code, but for models:

- **42 base rules** across sequence, activity, use-case, class and state
  diagrams, plus a **cross-diagram consistency pack** (one entity, one
  identity, across the whole model set) and an opt-in **codegen-readiness
  pack** (is this diagram precise enough to implement without guessing?).
- A **maturity score**: every diagram is graded Level 1 (*Sketchy*) to
  Level 5 (*Generation-ready*) across seven dimensions (completeness,
  ambiguity, consistency, traceability, …), with a prescriptive gap report
  that lists exactly which findings block the next level. The model set is
  scored by its **worst** diagram — the set is only as trustworthy as its
  weakest link.
- **CI enforcement** that fits brownfield reality: a hard floor
  (`--min-level`) for new work, and a **ratchet** mode that records today's
  levels as a baseline and fails only on *regression* — no big-bang cleanup
  required to start.

## The evidence

This is the part most linters cannot offer. The maturity model was tested
empirically ([EVIDENCE.md](../EVIDENCE.md)): hundreds of code-generation runs
where LLMs implemented systems from diagrams at different maturity levels,
with independent LLM judges scoring how faithfully the generated code matched
the diagram.

- Maturity scores **correlate with generation fidelity**: raw r ≈ 0.49
  overall; after normalizing for how much hard logic a diagram demands,
  per-diagram correlation is **r ≈ 0.65–0.70**, stable across two generator
  models and two independent judges.
- There is a **cliff below Level 2**: fidelity drops by roughly a third, and
  the amount of *invented business logic* — behaviour the diagram never
  specified — roughly **doubles**. A `--min-level 2` gate keeps exactly those
  diagrams out of your generation pipeline.

Two honesty notes, deliberately part of the product's claim language:

- These are **correlations under a measured setup**, not guarantees. Absolute
  fidelity numbers vary by judge (~9-point leniency offsets were observed);
  the *ranking* is what is stable.
- Level 5 means **method-convention complete** — the diagram-side
  preconditions for faithful generation are met. It is never marketed as
  "guaranteed generation-ready", and Level 5 cannot even be claimed unless
  the codegen rule pack is actually running.

## What adoption costs

Very little, by design:

- **Zero runtime dependencies.** Pure Python ≥ 3.11 standard library (PyYAML
  only if you prefer YAML config). No server, no database, no license fee,
  nothing to operate.
- **Drop-in CI**: a published GitHub Action, pre-commit hooks, and
  CI-friendly exit codes. Typical integration is a dozen lines of YAML
  ([setup guide](setup-and-ci.md)).
- **SonarQube without a plugin**: findings export in Sonar's Generic Issue
  Import format, landing in your existing dashboards, quality gates and PR
  decoration — no Java plugin to build or maintain.
- **No big-bang cleanup**: the baseline/ratchet mode accepts the status quo
  on day one and only defends against getting worse.
- **Reduced toil**: `pumllint fix` auto-repairs the mechanical findings
  (missing names/titles, undeclared participants) — deterministically, never
  inventing content.

## Governance properties

- **Stable contracts.** Rule IDs are stable once shipped; scores are pinned
  by a golden-score test suite; the JSON report shapes are pinned by
  published JSON Schemas. Your dashboards and gates will not drift silently
  under upgrades.
- **Auditable exceptions.** Suppressions live as reviewable comments in the
  diagram source (like `eslint-disable`), and CI can run with
  `--no-suppressions` to audit what is being silenced.
- **Prescriptive, not punitive.** The gap report tells each team exactly
  which findings to fix to reach the next level — the score is a to-do list,
  not just a grade.
- **Visible progress.** A shields.io badge per repository, trend annotations
  ("Level 3 → 4 since last baseline"), and a self-contained HTML maturity
  report designed for architecture reviews — no CLI needed to consume it.

## What it is not

- Not a syntax checker — PlantUML's own `-checkonly` remains the syntax gate
  (recommended as a companion CI step).
- Not a diagram generator or renderer.
- Not a style nitpicker by default: convention rules (ownership tags,
  requirement links, naming verbs) stay **dormant until you configure your
  organisation's convention** — the tool never invents a house style for you.

## Suggested rollout

1. **Week 1:** run `pumllint score` read-only on an existing repository;
   circulate the HTML report. This costs one CI step and produces the
   conversation-starter.
2. **Week 2:** commit a baseline (`--baseline maturity.json`) — CI now blocks
   regressions only.
3. **When ready:** add `--min-level 2` as a floor for the model set (the
   evidence-backed cliff), and `--profile codegen --min-level 5` for any
   diagram feeding code generation.
4. **Track:** the badge and the model-set level trend become your KPI;
   the gap reports are each team's backlog.

---

*Where do these benefits land in your delivery pipeline? The companion
assessment [pumllint in the SDLC](value-in-the-sdlc.md) maps them across
the four aspects of the SAFe Continuous Delivery Pipeline — every claim
tagged measured / mechanism / hypothesis — and ends in a staged pilot
measurement plan.*
