# The case for pumllint

*Audience: IT management, architecture leads, quality/governance owners.
What's in it for you, what it costs, and what the evidence actually
supports. No familiarity with the tooling is assumed — technical terms are
introduced in plain language as they first appear.*

## The problem

Your teams document how systems work as diagrams — the sequence of calls
between services, data models, state machines, use cases. Increasingly
they write those diagrams as plain text using **PlantUML**, a widely used
open-source tool: the text lives next to the source code, is versioned and
reviewed like code, and the picture is rendered from it. Those diagrams
drive reviews, onboarding, audits — and increasingly, AI-assisted code
generation.

But PlantUML is, by its own admission, a drawing tool, not a modeling
tool: it checks whether a diagram can be *drawn*, not whether it makes
*sense*. It happily renders:

- a message to `Custmer` — a typo that silently becomes a second, phantom
  component in the diagram;
- a decision branch guarded by "sometimes";
- a data model that inherits from itself in a circle — a logical
  impossibility;
- the same service called `OrderService` (a service) in one diagram and
  `orderService` (a gateway) in another.

No automated check we could find catches any of these today (the
survey and its limits: "What else is out there", below). Each one
costs you later:
review time spent decoding intent, wrong assumptions propagating into
implementations, and — if the diagrams feed an AI coding assistant —
invented behaviour filling the gaps.

## What pumllint is

An **automatic quality checker for those diagram files** — what software
engineers call a "linter". Source code has been guarded by such checkers
for years (ESLint, SonarQube); pumllint applies the same idea to design
diagrams:

- **42 kinds of checks** across sequence, activity, use-case, class and
  state diagrams, plus a **cross-diagram consistency pack** (one entity,
  one identity, across the whole set of diagrams) and an opt-in
  **AI-readiness pack** (is this diagram precise enough to implement
  without guessing?).
- A **maturity score**: every diagram is graded Level 1 (*Sketchy*) to
  Level 5 (*Method-complete*) across seven dimensions (completeness,
  ambiguity, consistency, traceability, …), with a gap report that lists
  exactly which findings block the next level. The set of diagrams is
  scored by its **worst** member — a model is only as trustworthy as its
  weakest diagram.
- **Enforcement that fits existing reality**: it runs inside the automated
  checks that already guard every code change, can hold new work to a
  minimum level, and covers existing diagrams with a **ratchet** — today's
  levels are recorded as the baseline, and a check fails only when a
  diagram gets *worse*. No big-bang cleanup required to start.

## The evidence

This is the part most quality tools cannot offer. The maturity model was
tested empirically ([EVIDENCE.md](../EVIDENCE.md)): hundreds of runs in
which AI models implemented systems from diagrams at different maturity
levels, with independent AI judges scoring how faithfully the generated
code matched the diagram.

- Maturity scores **correlate with how faithful the generated code is**: a
  solid statistical link (correlation ≈ 0.49 overall, and ≈ 0.65–0.70 once
  diagrams of similar complexity are compared with each other), stable
  across two generator models and two independent judges.
- There is a **cliff below Level 2**: faithfulness drops by roughly a
  third, and the amount of *invented business logic* — behaviour the
  diagram never specified — roughly **doubles**. A minimum-level gate
  keeps exactly those diagrams out of your AI pipeline.
- The cliff is **not an AI-judge artifact, and not a one-vendor
  artifact**. In follow-up studies the generated code was actually *run*
  against hand-written tests encoding each diagram's intended behaviour
  (tests written down and locked before any result was seen). Below
  Level 2, roughly **one intended behaviour in three failed** when the
  code executed, versus about one in ten above — consistently across six
  measurement rounds, three ways of prompting, and AI models from **two
  different vendors** (Anthropic and Google). Notably, better prompting
  rescued moderately untidy diagrams but **never the below-cliff ones**:
  no prompt can restore decision rules the diagram simply doesn't
  contain.
- **Repair was tested too — in both directions.** A follow-up experiment
  had an AI assistant repair the worst diagrams using the tool's own gap
  report (the "what to fix" list every score comes with). When the
  assistant **guessed** the missing decisions, the generated code got
  *worse* than leaving the diagram alone — a wrong rule written into a
  diagram looks exactly like a right one, and the code generator follows
  it faithfully. When the assistant could **ask the diagram's author**
  instead, repaired bad diagrams reached 86% of intended behaviours when
  run (versus 64% untouched), and mid-grade diagrams became
  indistinguishable from the best ones. The difference between guessing
  and asking: about **27 percentage points of working behaviour**.
  Practical consequence: the gap report tells teams *what* to fix; the
  decisions themselves must come from people who know the intent.

Three honesty notes, deliberately part of the product's claim language:

- These are **correlations under a measured setup**, not guarantees.
  Absolute scores vary by judge (~9-point differences in leniency were
  observed); the *ranking* is what is stable.
- Level 5 means **method-convention complete** — the diagram-side
  preconditions for faithful generation are met. It is never marketed as
  "guaranteed generation-ready", and Level 5 cannot even be claimed unless
  the AI-readiness checks are actually running.
- The gate checks that decisions are **stated**, not that they are
  *right*: in the repair experiment, diagrams repaired with confident
  wrong guesses still passed it. That boundary was measured on purpose —
  the gate is an entry filter for AI pipelines; the content stays the
  author's responsibility.

## What adoption costs

Very little, by design:

- **Nothing to operate.** No server, no database, no licence fee. The tool
  is a single self-contained program (pure Python, standard library only)
  with no third-party components to patch or audit.
- **Drop-in integration**: switching it on is a small configuration change
  in the build pipeline your teams already run; ready-made integrations
  are published for GitHub and for the checks that run on a developer's
  machine before a change is shared ([setup guide](setup-and-ci.md)).
- **SonarQube without a plugin**: if you run SonarQube quality dashboards,
  findings flow straight into them — existing dashboards, quality gates
  and the annotations reviewers see on each change, with nothing extra to
  build or maintain.
- **No big-bang cleanup**: the baseline/ratchet mode accepts the status quo
  on day one and only defends against getting worse.
- **Reduced toil**: the tool auto-repairs the mechanical findings (missing
  names and titles, undeclared components) — deterministically, never
  inventing content.

## Governance properties

- **Stable contracts.** The checks, the scores and the machine-readable
  report formats are treated as public contracts, pinned by the tool's own
  test suites — your dashboards and gates will not drift silently under
  upgrades.
- **Auditable exceptions.** A team can silence a specific finding, but
  only through a visible comment in the diagram itself — reviewable in
  every change — and the pipeline can run in an audit mode that reports
  everything being silenced.
- **Prescriptive, not punitive.** The gap report tells each team exactly
  which findings to fix to reach the next level — the score is a to-do list,
  not just a grade.
- **Visible progress.** A quality badge on each repository's front page,
  trend annotations ("Level 3 → 4 since last baseline"), and a
  self-contained HTML maturity report designed for architecture reviews —
  readable in any browser, no tooling needed.

## What it is not

- Not a syntax checker — PlantUML's own built-in check still verifies that
  a diagram renders at all; pumllint checks whether it makes sense. The
  two run side by side in the pipeline.
- Not a diagram generator or renderer.
- Not a style nitpicker by default: convention rules (ownership tags,
  requirement links, naming verbs) stay **dormant until you configure your
  organisation's convention** — the tool never invents a house style for you.

## What else is out there

Short answer: for this specific job, nothing we could find.

- **Existing PlantUML tooling stops at "does it draw?"** A landscape
  survey (July 2026, ~100 sources reviewed) found editors, renderers and
  syntax validators — including validators built so AI assistants can
  check their own diagram output — but no tool that checks whether a
  PlantUML diagram makes *sense*, and none that scores diagram quality.
  (Honesty note: a survey can establish "none found", not "none exists" —
  small or private tools may sit below the radar.)
- **The pattern itself is proven elsewhere.** For API contract files,
  a rule-based checker of exactly this kind — a tool called Spectral —
  is established enterprise practice: teams block changes on it in their
  pipelines. pumllint applies that same proven pattern to design
  diagrams, a slot that was simply unoccupied.
- **The AI-specification trend has the need, but not the gate.** The
  2025–26 wave of "spec-driven development" tools (GitHub Spec Kit, AWS
  Kiro and others) is built on the idea that AI implements what a written
  specification says — which makes the quality of the specification the
  bottleneck. The quality checks those tools themselves provide are
  AI-generated opinions: a different answer every run, so they cannot
  serve as a pass/fail gate. pumllint's score is deterministic — the same
  diagrams get the same score, every time — which is what makes it usable
  as an enforcement gate and auditable afterwards.
- **"Couldn't our AI just write us one?"** Increasingly, yes — the
  largest published AI-first build to date (OpenAI, February 2026,
  roughly a million lines of code) enforced its own architecture with
  checkers the AI wrote itself. That works, and nothing here argues
  against it. The difference is what stands behind the rules. We
  investigated having an AI write this tool's own checks, and the risk
  turned out not to be that it invents nonsense — that gets caught
  immediately — but that it writes a check which satisfies the two or
  three examples it was shown, quietly gets the general case wrong, and
  is then reviewed by the same AI that wrote it. Three things keep that
  in hand here and are simply absent from a checker generated last week:
  every rule carries written acceptance examples, the scores are frozen
  by tests so no new rule can shift them silently, and each candidate
  rule is run across a reference collection to show where it fires
  before anyone accepts it. Two more are impossible for a
  single-repository tool by construction: scores that mean the same
  thing in another team's repository — a Level 3 here is a Level 3
  there, which is what makes a portfolio view possible — and published
  evidence that the checks relate to real outcomes. Writing your own
  checks is not the disagreement; this tool ships a guide for adding
  rules to it. The apparatus around the rules is the product.

This finding is drawn. The chart below places pumllint among the
checking tools of neighbouring diagram notations — one dot per tool, each
checking its own notation — on a Gartner-style quadrant whose positions
are computed from a published scoring rubric, not judged:

![Positioning quadrant of diagram-as-code checkers: the Leaders quadrant
is empty; pumllint sits deep in Visionaries; the incumbents cluster in
Challengers](positioning-quadrant.svg)

Read candidly, the top-right is empty: the tools with an installed base
stop at syntax or findings, and the tools with the semantic depth —
pumllint furthest among them — have not yet earned the adoption. That
empty quadrant is this section's "nothing we could find", extended across
the neighbouring notations and scored. The rubric, the per-tool scores,
and what would move each dot are in
[Positioning pumllint](positioning-quadrant.md).

## Suggested rollout

1. **Week 1:** run the scorer read-only on one existing repository and
   circulate the HTML maturity report. This costs one step in the build
   pipeline and produces the conversation-starter. A live example of
   exactly this artefact — this repository's own diagrams, scored by the
   tool itself — is published here:
   [example maturity report](https://fdurieux.github.io/pumllint/example-maturity-report.html).
2. **Week 2:** record today's levels as the committed baseline — the
   pipeline now blocks regressions only.
3. **When ready:** require Level 2 as the floor for the whole diagram set
   (the evidence-backed cliff), and Level 5 with the AI-readiness checks
   for any diagram feeding code generation.
4. **Track:** the badge and the set-level trend become your KPI; the gap
   reports are each team's backlog.

---

*Where do these benefits land in your delivery pipeline? The companion
assessment [pumllint in the SDLC](value-in-the-sdlc.md) maps them across
the four aspects of the SAFe Continuous Delivery Pipeline — every claim
tagged measured / mechanism / hypothesis — and ends in a staged pilot
measurement plan.*
