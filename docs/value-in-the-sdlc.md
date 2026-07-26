# pumllint in the SDLC: a value-stream assessment

*Audience: IT management, transformation leads, quality and governance
owners. No familiarity with the tooling is assumed — technical terms are
introduced in plain language as they first appear. Structure: a two-page
executive brief, then the full
assessment, then a practice-domain-level mapping as an appendix. The
companion document [The case for pumllint](case-for-pumllint.md) covers
what the tool is, what it costs and what the evidence supports; this one
covers **where** the value lands in the software delivery life cycle,
mapped to the four aspects of the
[SAFe Continuous Delivery Pipeline](https://framework.scaledagile.com/continuous-delivery-pipeline).*

**How to read the claims.** Every value claim below carries one of three
tags, in decreasing order of strength:

- **[measured]** — backed by controlled experiments
  ([EVIDENCE.md](../EVIDENCE.md)): over 500 runs in which AI models wrote
  code from diagrams of varying quality, scored two independent ways —
  by AI judges, and by **actually running the generated code** against
  behavioural tests that were written down and locked before any result
  was seen — across three business scenarios.
- **[mechanism]** — a concrete causal chain exists, but it has not been
  measured inside an organisation. The [pilot plan](#pilot-turning-mechanism-into-your-numbers)
  is how these become your own numbers.
- **[hypothesis]** — plausible and worth testing; treat as unproven.

A value case that tags its own claims is unusual. That is deliberate: the
project's evidence discipline — correlations, never guarantees — is part
of what is being proposed for adoption.

---

## Executive brief

**What this is about.** Engineering teams record how systems work — which
components talk to which, in what order, what happens when a step fails —
as diagrams. Increasingly, those diagrams are not drawn in a drawing tool
but *written as plain text* using **PlantUML**, a widely used open-source
tool: the text lives next to the source code, is versioned and reviewed
like code, and the picture is rendered from it. **pumllint is an
automatic quality checker for those diagram files** — what software
engineers call a "linter". It reads each diagram and flags mistakes,
ambiguity and inconsistency, the way a grammar checker reads prose, and
it grades every diagram on a five-level maturity scale.

**Why now.** Design diagrams used to be decoration: helpful, optional,
and invisible when they went stale. Two shifts are making them
load-bearing. AI coding assistants now *read* diagrams as specifications
and write code from them — and the measured evidence below shows that the
quality of the diagram going in drives the quality of the code coming
out. AI assistants also *write* diagrams at near-zero cost — volume that
arrives with no quality control attached. Once a document type is
routinely read and written by machines, its quality stops being a
documentation nicety and becomes a property of the delivery pipeline.
Source code went through exactly this transition years ago: automatic
quality checks on every change are now universal, and nobody relies on
human reviewers to spot typos. Diagrams are among the last artefacts in
the pipeline with no such check. [mechanism]

**What the tool does.** Forty-two kinds of checks, covering real mistakes
that PlantUML itself happily accepts (a misspelled name that silently
becomes a second, phantom component), ambiguity (a decision branch
labelled "sometimes"), and inconsistency (the same service described
differently in two diagrams). On top of the checks sits the maturity
score: every diagram graded Level 1 (*Sketchy*) to Level 5
(*Generation-ready*), with a gap report listing exactly what to fix to
reach the next level. Enforcement fits existing reality: a minimum level
can be required for new work, while existing diagrams are covered by a
**ratchet** — today's state is accepted as the baseline, and the
automated checks fail only if a diagram gets *worse*. No cleanup project
is needed to start. One scope guard up front: the score measures how
disciplined and precise a diagram is, not whether the design it shows is
any good. It filters out untrustworthy diagrams; it does not replace
design review by architects — it frees that review to spend its time on
substance.

**Where the value lands**, mapped to the four aspects of the pipeline:

| Aspect | pumllint's role | Strength |
|---|---|---|
| **Continuous Exploration** | Ambiguity and inconsistency are caught while designs are being written, before anyone builds on a misreading; design reviews spend their rounds on the design itself instead of on decoding diagrams | Direct [mechanism] |
| **Continuous Integration** | Where the tool actually runs: the automated checks that already guard every code change now also guard the diagrams — an outdated or sloppy diagram fails the check just like broken code, and findings appear in the quality dashboards many organisations already run (SonarQube) | Direct [fact] |
| **Continuous Deployment** | No role while software is being deployed, verified or monitored. Indirect value only: when an incident hits, responders find diagrams that are up to date and show the failure paths | Inherited [hypothesis] |
| **Release on Demand** | Audit-ready evidence that design documentation is current and governed; the maturity trend becomes a management metric for documentation health; gap reports feed each team's improvement backlog | Supporting [mechanism] |

The asymmetry is deliberate honesty: pumllint is an upstream instrument.
Its downstream value is carried by the diagrams it disciplines, not by
anything it does downstream itself.

**The AI evidence, briefly.** In over 500 measured runs in
which AI models wrote code from diagrams, higher-maturity diagrams
produced measurably more faithful code — a solid statistical link
(correlation ≈ 0.65–0.70 when comparing diagrams of similar complexity,
≈ 0.4–0.5 before that adjustment), holding across two different AI
generators and two independent AI judges. Below Level 2 the relationship
is a cliff, not a slope: faithfulness drops by roughly a third, and
*invented* behaviour — business logic the diagram never specified —
roughly doubles; the drop is steeper with cheaper AI models. The cliff is
not an artifact of AI judges either: when the generated code was actually
*run* against pre-written behavioural tests, diagrams below Level 2
failed roughly one intended behaviour in three, versus about one in ten
above — and better prompting of the AI rescued moderately untidy diagrams
but never the below-cliff ones. A minimum-level gate in the pipeline is
the demonstrated countermeasure: it keeps exactly those diagrams away
from AI-assisted work. [measured]

**Cost.** Free and open source, with nothing to operate: no server, no
licence fee, no new system to run. Switching it on is a small
configuration change in the existing build pipeline, and findings flow
into quality dashboards already in place — nothing extra to build.
Details: [What adoption costs](case-for-pumllint.md#what-adoption-costs).

**The ask.** Approve a two-step, report-only pilot: (1) run the checker
read-only on one existing code repository and circulate its
self-contained maturity report to the architecture community; (2) record
today's levels as the baseline and let the pipeline block only
regressions. Both steps are reversible and cost close to nothing. Hard
minimum levels and the AI-readiness gate come only after the pilot has
produced the organisation's own numbers — see
[the pilot plan](#pilot-turning-mechanism-into-your-numbers).

---

## The full assessment

### Method, and one conditional to test first

Three choices frame this assessment.

**The unit of analysis is the development value stream** — the flow of
work from idea to released value — rather than a tool-feature list. For
each stage the question is: what diagram-related waste occurs here today
(rework, waiting, defects, stale inventory), and what does pumllint
change, through which mechanism, moving which flow metric?

**The structure is SAFe's Continuous Delivery Pipeline.** Its four
*aspects* — Continuous Exploration, Continuous Integration, Continuous
Deployment, Release on Demand — are the closest thing SAFe has to SDLC
phases (SAFe itself avoids the term, since the aspects overlap and run
concurrently rather than in sequence). The sixteen activities inside them
are the *practice domains* assessed by the SAFe DevOps Health Radar; the
[appendix](#appendix-the-sixteen-practice-domains) maps every one of them
honestly, including the ones where pumllint has nothing to offer.

**Claims stay inside the evidence.** The tag vocabulary from the top of
this document applies throughout. Where SAFe flow metrics are named (flow
time, flow efficiency, flow predictability), they identify the metric a
mechanism *should* move — measuring the movement is what the pilot is for.

And the conditional: **this case assumes models are, or are about to
become, load-bearing artefacts in your value stream** — used in reviews,
onboarding, audits, or AI-assisted work. In an organisation where diagrams
are genuinely throwaway sketches, a linter for them is worth little, and
this document would be the wrong purchase. Note, though, the direction of
travel: the moment any team feeds a diagram to an AI agent, or accepts one
an AI produced, the assumption has become true for that team — whether or
not anyone decided it.

### Continuous Exploration — where intent is formed

*CE is the aspect in which market and customer needs become prioritised
solution intent; its practice domains are Hypothesize, Collaborate &
Research, Architect and Synthesize. Models — sequence flows, state
machines, class models — are the Architect activity's principal written
output, and part of the architectural runway later trains run on.*

The waste, today: PlantUML is by its own admission a drawing tool, not a
modeling tool. It happily renders a message to `Custmer` — a typo that
silently becomes a phantom participant — an `alt` branch guarded by
"sometimes", and the same service appearing as `OrderService <<service>>`
in one diagram and `orderService <<gateway>>` in another. None of these
fails anything today. Each is a defect *born in design*: it will surface
later as a review round-trip spent decoding intent, as two teams
implementing two different readings of the same flow, or as rework
discovered at integration — the most expensive places to find it.

What changes with pumllint:

- **Ambiguity is surfaced at authoring time** — vague guards, prose
  instead of operation signatures, unlabelled arrows, structure narrated
  in notes rather than modelled. Design reviews then spend their rounds on
  whether the design is *right*, not on what the diagram *means*. Shorter
  review loops (flow time), fewer interpretation-rework cycles (flow
  efficiency). [mechanism]
- **One entity, one identity, across the whole model set.** The
  cross-diagram pack flags the same participant changing kind, stereotype
  or spelling between diagrams — the mechanism by which "shared" solution
  intent quietly stops being shared. [mechanism]
- **Traceability into governance.** Ownership tags and requirement/ADR
  links are checkable rules — bound to your convention, and deliberately
  dormant until you configure one (the tool never invents a house style).
  Models become artefacts that portfolio governance can actually navigate.
  [mechanism]
- **An enforceable definition of done for design artefacts.** SAFe's
  Built-in Quality principle explicitly extends beyond code to designs and
  models; a `--min-level` floor turns that from aspiration into a check —
  the same move coding standards made when CI started enforcing them.
  [mechanism]

### Continuous Integration — where the tool executes

*CI's practice domains are Develop, Build, Test End-to-End and Stage. This
aspect is where pumllint physically runs — its claims here are mostly
statements of fact about shipped integrations rather than mechanisms.*

- **Models get the same PR discipline as code.** Pre-commit hooks catch
  findings before they are committed; a published GitHub Action gates them
  in CI; exit codes make the gate scriptable anywhere else. [fact]
- **Model decay becomes a failing check instead of an archaeology
  project.** The ratchet compares every diagram against its recorded
  baseline and fails only on regression — so a brownfield model set can be
  brought under governance on day one, with no big-bang cleanup, and can
  only get better. [fact]
- **Findings land in the dashboards you already run.** The SonarQube
  export uses Sonar's generic-import format: existing quality gates and PR
  decoration, no Java plugin to build or maintain. [fact]
- **Mechanical toil is automated away.** `pumllint fix` repairs the
  findings where nothing has to be invented (names, titles, undeclared
  participants) — deterministically and idempotently; everything requiring
  judgment stays human. [fact]
- **Exceptions are auditable.** Suppressions live as reviewable comments
  in the diagram source, and CI can run with `--no-suppressions` to audit
  what is being silenced. [fact]

The flow effect claimed from all of the above: hygiene enforcement moves
from unreliable human policing (usually: nobody) to a machine step with
zero marginal cost — less rework reaching implementation (flow
efficiency), fewer late design surprises (flow predictability).
[mechanism]

### Continuous Deployment — inherited value only

*CD's practice domains are Deploy, Verify, Monitor and Respond. pumllint
plays no role in deploying, verifying or monitoring a solution, and this
section refuses to pretend otherwise.*

The one honest claim is inheritance: when an incident forces engineers to
reconstruct how a flow was *supposed* to work, they reach for the sequence
and state diagrams. Whether those help depends on properties enforced
upstream: that the diagrams are current (the ratchet), and that they model
failure paths at all — the codegen pack literally requires an error branch
on every call to an external system or database. An organisation whose
responders consult models gets this value; one whose responders never open
them does not. [hypothesis]

### Release on Demand — governance and measurement

*RoD's practice domains are Release, Stabilize, Measure and Learn. Value
here is supporting rather than direct — but it is where the maturity score
becomes a management instrument rather than an engineering one.*

- **Audit-ready design documentation.** Regulated and audited releases
  need evidence that design documentation is current and governed. A
  gated, ratcheted, badge-visible model set is demonstrable governance —
  a standing property of the pipeline, not a pre-audit scramble — and the
  deterministic HTML report is the circulate-to-auditors artefact.
  [mechanism]
- **Documentation health becomes measurable.** The model-set maturity
  level, its trend against baseline ("Level 3 → 4 since last baseline")
  and the repository badge add a number to the organisation's Measure
  activity that never existed before: are our models getting better or
  worse? [fact — that it measures; whether the number moves anything
  downstream is what the pilot tests]
- **Gap reports are ready-made improvement backlog.** Each team's route to
  the next level is enumerated, finding by finding — relentless
  improvement with the prioritisation already done. [mechanism]

### Preparing the value stream for AI and further automation

This is the strongest part of the case, because it is the only part with
measured evidence behind it — and because it converts the sceptic's
premise: if diagrams are decoration, why lint them? Answer: because they
are about to stop being decoration at both ends of the pipeline.

**1. Models as AI input — the measured case.** When a diagram is handed to
an AI coding agent as a specification, its maturity measurably drives the
outcome. Across more than 500 generation runs: fidelity of the generated
code correlates with the maturity composite at r ≈ 0.4–0.5 raw, and at
**r ≈ 0.65–0.70** per diagram once semantic difficulty (the guards and
failure paths a diagram demands) is held constant — stable across two
generator models and two independent judge models. Below Level 2 the
relationship is a cliff, not a slope: fidelity drops by roughly a third
and *invented business logic* — behaviour the diagram never specified —
roughly doubles. The cliff steepens under a cheaper generator: a weaker
model compensates less, so the gate matters more, not less, as
organisations push generation down the cost curve. `--min-level` is
therefore an evidence-backed **risk filter** for any spec-to-code
pipeline. One boundary kept deliberately honest: Level 5 is defined as
*method-convention complete — the diagram-side preconditions for faithful
generation* — never "guaranteed generation-ready", because a sequence
diagram underdetermines an implementation no matter how clean it is.
[measured] ([EVIDENCE.md](../EVIDENCE.md))

The same relationship holds when opinion is taken out of the measurement.
In a follow-up wave the generated code was **executed** against
hand-written behavioural tests encoding each diagram's intended behaviour
— tests written down and locked before any result was seen. Below Level 2
roughly one intended behaviour in three failed when the code ran, versus
about one in ten above; the gap reproduced in every measurement round
(16–25 percentage points across five rounds) and across three different
ways of prompting the generator. Two further findings sharpen the case.
First, **prompt engineering is not a substitute for diagram quality**:
pinning a stricter generation contract lifted moderately degraded
diagrams almost to pristine pass-rates but left below-cliff diagrams far
behind — no prompt can restore decision rules and failure paths the
diagram never specified. Second, the AI judges' scores and the execution
results agree on the overall maturity relationship but only weakly on
individual runs — so this document never merges the two into one number,
and neither should any evaluation you run. [measured]

**2. Models as AI output — the verifier.** AI assistants produce plausible
PlantUML at near-zero cost. That inverts the economics: generation stops
being scarce, and *verification* becomes the constraint. pumllint is the
deterministic verifier in that loop — lint, score, gap report, auto-fix —
and the codegen rules read as an anti-invention checklist: no elision
markers ("…", "TBD"), no prose where an operation signature belongs,
explicit failure paths, no vague guards. Machine-written models are held
to the same bar as human ones, at machine speed. [mechanism]

**3. A machine-actionable quality loop.** "Automation-ready" means
something specific here: every interface an automated remediation loop
needs already exists and is contract-pinned. Reports ship as JSON with
published schemas; rule IDs are stable; scores are pinned by golden tests;
gates are exit codes. The gap report is a machine-readable to-do list — an
agent can read findings, remediate, and re-score, and `pumllint fix`
already automates the subset where nothing has to be invented. [fact]

**4. The model set as AI context.** A model corpus with one identity per
entity and explicit semantics is what makes it usable as *context* for
assistants — retrieval, onboarding bots, review copilots. An inconsistent
corpus does not merely fail to help an LLM; it actively misleads it. This
is engineering judgment, not measurement — the one AI claim here that is.
[hypothesis]

Two methodological exports worth more than the tool itself. First, the
experiments found that same-model self-judging inflated fidelity scores
by roughly 15 points, so every number above comes from an independent
judge model. Second, an AI judge's *opinion* of code turned out not to be
a substitute for *running* it: judged faithfulness and executed test
results agreed on the overall trend but only weakly on individual pieces
of code (correlation ≈ 0.25). If your organisation is evaluating AI
tooling anywhere, both findings travel: *insist on independent judging,
and prefer execution over opinion wherever behaviour can be executed.*
[measured]

### Costs, frictions, and how they are contained

The cost side is short by design — zero runtime dependencies, no server,
no licence, a dozen lines of CI YAML, Sonar without a plugin ([details](case-for-pumllint.md#what-adoption-costs)).
The honest frictions are these:

- **Gate friction.** Any gate teams do not yet trust gets routed around.
  Containment is the rollout sequencing itself: advisory report first,
  then regression-only ratchet, then a floor — each step earns the next,
  and the convention-bound rules stay dormant until you configure your
  own conventions. [mechanism]
- **Suppression abuse.** Contained by making exceptions reviewable in
  diffs and auditable in CI; the suppression count is one of the pilot
  KPIs precisely so drift is visible.
- **Overselling.** Quality tooling fails two ways: ignored, or
  worshipped. The scope guard (model hygiene, not architecture quality)
  and the claim tags exist to prevent the second failure. A Level 5
  diagram can still describe a bad design — architecture review stays a
  human activity.
- **Tool risk.** Contained by stable contracts: rule IDs are stable,
  scores are pinned by a golden-score suite, JSON report shapes are
  pinned by published schemas — dashboards and gates do not drift
  silently under upgrades — and a stdlib-only codebase leaves no
  dependency tree to patch.

### Pilot: turning [mechanism] into your numbers

Every [mechanism] claim above is a hypothesis about *your* value stream.
The pilot is deliberately staged so that each step is cheap, reversible,
and produces the evidence for the next ([setup guide](setup-and-ci.md)):

| Phase | What happens | What you learn |
|---|---|---|
| **0 — Advisory** (a week) | One read-only CI step scores an existing repository; the HTML maturity report goes to the architecture community | The day-one maturity distribution of a real model set — the baseline every later claim is measured against |
| **1 — Ratchet** (a sprint) | Baseline committed; CI fails only on regression | Whether decay was actually happening, and what it costs to stop it (regressions caught, friction reported) |
| **2 — Floor** (a PI) | `--min-level 2` on the model set — the measured cliff — plus `--profile codegen --min-level 5` wherever diagrams feed AI generation | Gate hit-rates; whether AI-fed diagrams meet method-convention completeness |
| **Ongoing** | KPIs on the dashboard | Model-set level trend (the badge), share of diagrams at Level 3+, suppression count, regressions per PI |

This repository practises Phase 0 on itself. Its bundled example diagrams
— seven good/bad pairs, deliberately mixed quality — are scored by the
tool, and the resulting report is published as the live pilot example:
**[example maturity report](https://fdurieux.github.io/pumllint/example-maturity-report.html)**.
The good diagrams reach Level 4 (held from Level 5 only by the codegen
profile), every flawed one is caught at Level 2–3 with its gap report,
and the set as a whole scores Level 2 — the worst-member principle doing
its job:

![example model-set maturity](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/fdurieux/pumllint/main/docs/example-badge.json)

A test in the repository regenerates the report on every run and fails if
the published copy drifts from what the tool actually produces — the
pilot example is held to the same no-silent-drift standard as the scores
themselves.

Optionally, pair the KPIs with soft flow indicators: review round-trips on
diagram-touching PRs, incidents in which stale or ambiguous diagrams were
cited, onboarding feedback. Stated honestly: those indicators establish
plausibility, not proof — organisational attribution for any linter is
confounded. The hard evidence remains the [measured] generation results
plus your own maturity trend.

**The decision this document requests is Phases 0–1**: one CI step and one
committed baseline file. Everything stronger waits for your own numbers.

---

## Appendix: the sixteen practice domains

The [SAFe DevOps Health Radar](https://framework.scaledagile.com/continuous-delivery-pipeline)
assesses the pipeline at the resolution of its sixteen activities — the
practice domains, four per aspect. The same honesty rules apply at this
resolution. Legend:

- **●** direct — pumllint executes here, or its findings act here
- **◐** supporting — pumllint's outputs are used in this activity
- **○** inherited — value arrives only because upstream enforcement kept
  the artefacts trustworthy
- **—** no claim

| Aspect | Practice domain | Claim | Basis |
|---|---|---|---|
| Continuous Exploration | Hypothesize | — | Forming and testing business hypotheses is not a model linter's business |
| | Collaborate & Research | ◐ | A model set with one identity per entity is a shared design language that survives crossing team boundaries [mechanism] |
| | Architect | ● | The core action point: ambiguity, completeness, consistency and traceability rules act while solution intent is being written [mechanism] |
| | Synthesize | ◐ | Requirement/ADR-link and owner-tag rules bind models to backlog items and decisions — convention-gated, dormant until you configure yours [mechanism] |
| Continuous Integration | Develop | ● | Pre-commit hooks, editor-time CLI, deterministic auto-fix: findings surface at authoring cost, not review cost [fact] |
| | Build | ● | GitHub Action, exit codes, `--min-level` and ratchet gates, SonarQube export into existing quality gates [fact] |
| | Test End-to-End | ○ | Failure-path-complete sequence diagrams (the codegen pack requires error branches on external calls) double as end-to-end scenario sources [hypothesis] |
| | Stage | — | No claim |
| Continuous Deployment | Deploy | — | No claim |
| | Verify | — | No claim |
| | Monitor | — | No claim |
| | Respond | ○ | Responders inherit diagrams that are current (ratchet) and model failure paths — if your responders consult models at all [hypothesis] |
| Release on Demand | Release | ○ | Audited releases need evidence that design documentation is current and governed; a gated, ratcheted, badge-visible model set is that evidence [mechanism] |
| | Stabilize | ○ | Post-release problem-solving over trustworthy models — the same inheritance as Respond [hypothesis] |
| | Measure | ◐ | Model-set maturity level, trend and badge add documentation health to what the organisation measures [fact] |
| | Learn | ◐ | Gap reports are ready-made improvement backlog items; the trend shows whether the modelling practice actually improves [mechanism] |

Five of the sixteen practice domains carry no claim at all; only three
carry a direct one — and those three sit exactly where design defects are
cheapest to remove. An assessment that scored well everywhere should worry
you. Concentration plus stated limits is what a real instrument looks
like; it is also, not coincidentally, how this project treats its own
evidence.
