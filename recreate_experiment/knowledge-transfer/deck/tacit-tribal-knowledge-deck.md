# Preserving Tacit & Tribal Knowledge in Banking Systems

*A Framework for Operational Continuity Using AI-Assisted Reverse Engineering*

Author name / department

---

*Consolidated 2026-10-29 from two sources: the draft slide deck (eight slides,
no final storyline yet) and an LLM-generated outline structured as Objective →
Framework → Implementation → Tools/Risks → Next Steps. Where the two differ,
the deck's wording wins; the outline's variant is kept as a note in
`[brackets]`. The deck's own yellow highlights, which mark text its author
still wants to review, are carried as `[review]` markers. No organisation
name, logo or classification marking is reproduced.*

---

## TL;DR — Exec Summary

> "The bank faces **operational risk** when critical knowledge — embedded in
> code and held by a few SMEs — becomes unavailable.
>
> This framework uses **AI to reverse-engineer undocumented logic** from bank
> systems, then validates it with SMEs to create **living documentation**. The
> result: **reduced SME dependency**, **faster onboarding**, and **continuity**
> during transitions — all while keeping data on-premises for compliance."

## Definitions

- **Tacit Knowledge**: Personal, experience-based insights (e.g., intuition,
  problem-solving heuristics) that are hard to articulate or document.
- **Tribal Knowledge**: Informal, unwritten knowledge shared within a
  team/group (e.g., "how things really work here").

**Risk**: Both are vulnerable to loss when SMEs leave or are unavailable.

## Context — Problem, Goal, Scope

### Problem

The bank faces operational risk when **tacit knowledge** (individual
expertise) and **tribal knowledge** (team-level workarounds) become
unavailable due to:

- **SME turnover** (e.g. change department, retirements, resignations).
- **Competing priorities** (e.g. SMEs tied up in other projects).
- **Undocumented legacy systems** (e.g. COBOL, custom/historical banking
  logic).

### Goal

Automate the extraction of implicit knowledge from **bank product logic** and
**software codebases** to:

- Generate **actionable documentation** (e.g., architecture diagrams,
  functional specs).
- Reduce **SME dependency** by min. 30 % (target metric).
  *[Outline: 30–50 %. Deck's "min. 30 %" kept.]*
- Ensure **operational continuity** during transitions.

### Scope

- **Bank Product Knowledge**: Loan approval rules, compliance workflows,
  customer journey exceptions.
- **Codebase Knowledge**: Legacy system logic, API dependencies, technical
  debt.

## Framework

### Core Approach: AI-Assisted Reverse Engineering + SME Validation

| Step | Action | Output |
|---|---|---|
| 1. Code Analysis | Use static analysis tools and AI to parse dependencies, complexity, and logic. | Raw code metadata & artefacts (e.g. `[...]` `[review]`). *[Outline's example: call graphs.]* |
| 2. AI Extraction | Deploy LLMs to draft explanations, comments, and business rules. | Draft documentation artefacts. |
| 3. SME Validation | Experts review/correct AI-generated content. | Validated, context-rich documentation. |
| 4. Integration | Embed into CI/CD and knowledge repositories. | Living documentation system. |

### Documentation Artefacts

`[review]` *Deck note: "Examples & tools needs reviewing/correcting."*

| Type | Example | Tool |
|---|---|---|
| Architecture Diagrams | System-level flowcharts (e.g., payment processing workflow). | PlantUML, `[...]` `[review]` *[Outline: PlantUML, Mermaid.js]* |
| Functional Specs | AI-drafted explanations (e.g., "How does interest calculation work?"). | LLM + SME review |
| Data Flow Maps | Visualize data movement (critical for compliance/audits). | Lucidchart (air-gapped) `[review]` |
| Risk Flags | Highlight technical debt, deprecated functions, or untested edge cases. | SonarQube, pumllint, Aris linter tool *[Outline: SonarQube only]* |

### Why This Works

- **Tacit Knowledge**: Extracted from code comments, logic branches, and
  undocumented rules.
- **Tribal Knowledge**: Captured via SME reviews (e.g., "We use this
  workaround because of regulation X").
- **Continuity**: Documentation is **version-controlled** and
  **auto-updated** with code changes.

## Implementation

*Outline only; not yet in the deck.*

### Phase 1: Pilot (2–4 Weeks)

- **Target**: Non-critical but representative module (e.g., loan calculation
  engine).
- **Actions**:
  1. Run **SonarQube + Mistral-7B** to generate draft docs.
  2. **2–3 SMEs** validate 1–2 artefacts (e.g., architecture diagram +
     functional spec).
  3. Measure:
     - % accuracy of AI-generated content.
     - Time saved vs. manual documentation.

### Phase 2: Scale-Up (6–8 Weeks)

- Expand to **high-risk areas**:
  - Payment processing (compliance-critical).
  - Legacy systems (high SME dependency).
- Integrate with **CI/CD pipelines** to auto-update docs on code changes.

### Phase 3: Cultural Adoption (Ongoing)

- **Training**: "Documentation as Code" principle (e.g., "No PR merged without
  updated specs").
- **Incentives**:
  - Recognize top contributors (e.g., "Knowledge Preservation Champion").
  - Tie to performance metrics for tech leads.

## Tools & Risks

*Outline only; not yet in the deck.*

### Tools (On-Premises Only)

| Category | Tools | Purpose |
|---|---|---|
| Code Analysis | SonarQube, Cast Software | Parse dependencies, complexity. |
| Diagram Generation | PlantUML, Mermaid.js | Auto-generate architecture/data flow maps. |
| LLM Assistance | Mistral-7B (locally deployed) | Draft specs, comments, and business rules. |
| Collaboration | Confluence, GitLab Enterprise | SME review and version control. |

### Risks & Mitigations

| Risk | Mitigation |
|---|---|
| AI hallucinations | SME validation + deterministic tools (e.g., SonarQube). |
| Over-reliance on AI | Treat AI output as a "first draft" only. |
| SME bottlenecks | Prioritize reviews by impact; use junior devs for initial triage. |
| Legacy code complexity | Start with well-documented modules; iteratively tackle "spaghetti code." |
| Confidentiality | All tools deployed on-premises; no data leaves the bank. |

## Next Steps

*Outline only; not yet in the deck.*

| Action | Owner | Timeline |
|---|---|---|
| Identify pilot codebase | Tech Lead | Week 1 |
| Deploy SonarQube + Mistral-7B | DevOps | Week 2 |
| Define SME review process | Product Owner | Week 2 |
| Kickoff workshop (devs + SMEs) | Project Manager | Week 3 |
| Pilot review & metrics collection | Team | Weeks 4–6 |

## Key Metrics

1. **Reduction in SME dependency**
   - % drop in ad-hoc SME requests.
     *[Outline target: 30 % in 6 months.]*
2. **Speed of onboarding**
   - Reduction in time needed by new people on the team to understand¹ a
     specific scope. `[review: "understand", footnote 1]`
     *[Outline: time for new hires to understand a module, target 50 %
     faster.]*
3. **Level of coverage**
   - % of critical knowledge & information documented & validated.
     *[Outline names this "Risk Coverage"; its definition was cut off in the
     screenshot.]*
4. **Level of compliance**
   - % of artefacts² that is ready-for-audit. `[review: "artefacts", footnote 2]`

¹ ² *Footnote texts not visible in the deck photos.*

## Findings from the repository (pumllint)

*A third source, kept apart from the deck/outline consolidation above: what
the pumllint repository recorded on capturing tacit and tribal knowledge
between 2026-10-12 and 2026-10-27. Nothing here overrides the deck; the
last subsection says where the two agree and where they do not.*

### Where it comes from

| date | record | what it holds |
|---|---|---|
| 2026-10-12 | `docs/sdlc-tooling-landscape.md`, the METR paragraph | the older touchpoint: independent evidence that implicit repository knowledge is a measured cost |
| 2026-10-24 | PR #187, `recreate_experiment/rebuilds/codex-2026-10-24/EVALUATION-METHOD.md` §"Capturing tacit and tribal knowledge" (method 1.2) and §"Reverse-engineering within the SDD flow" (method 1.3) | the definitions, the elicitation and provenance protocol, the no-percentage rule, the observed / inferred / intended split |
| 2026-10-24 | `recreate_experiment/results/coverage/UNREALISED.md`; `docs/recreate-experiment.md` §"The other direction" | the measured size of what the code-side approach does not reach on one real application |
| 2026-10-24, revised 10-26 and 10-27 | PRs #190, #193, #197, `recreate_experiment/knowledge-transfer/DOMINIQUE-CASE.md`; summary in `docs/recreate-experiment.md` §"A case for the approach: a departing expert" | the method applied to a departing expert: the verdict, the plan, the measures, the question layer's answer policy, what linters can and cannot find |

### Definitions the method uses

- **Tacit knowledge**: practical know-how a person uses without fully
  stating it, such as how they recognise an invalid result or choose an
  exception.
- **Tribal knowledge**: project-specific understanding shared informally
  by a team, such as naming conventions, historical workarounds, deployment
  rituals or unwritten business rules.
- Both can be valuable, incorrect, outdated or disputed. **Nothing becomes
  authoritative because someone states it**: every captured item carries
  its source, date, confidence and validator, and a disputed or unvalidated
  item stays marked as such.

### What reverse engineering reaches, and what it does not

The Dominique case sorts an expert's knowledge into five kinds and rates
each instrument against them:

| kind | example | reverse engineering | the capture protocol | the question layer |
|---|---|---|---|---|
| what the systems do | which rule rejects a dossier, where the pricing grid lives | strong, measurable | — | answers well, with citations |
| why they do it | the 2019 workaround for the guarantee data nobody fixed | orphans and quirks as questions only | the register, if elicited | answers only what was recorded |
| domain and policy judgement | when a sole trader's turnover dip is a warning and when it is seasonal | nothing | partial: worked cases and counterexamples | risky: fluent, unaccountable, possibly regulated advice |
| history of decisions | why the covenant module was descoped twice | nothing | decision records, if elicited | fine, if recorded |
| the network | who owns the collateral data, who can grant an exception, who to call at 16:55 | nothing | not addressed by the method | nothing |

The code answers the first row. The second row it can only turn into
questions: an orphaned function, a quirk preserved, a guard nothing
reaches. Rows three to five come from people or not at all.

**Measured on one real application** (the data lane of the experiment's
reference system, 2026-10-24): the specification kit's 258-case suite
executes 1 379 of 1 520 statements (89 %). The 141 never executed fall
into four classes: 40 live-transport paths replay cannot reach, 33 the kit
specifies and no scenario exercises, **61 with no production caller in the
lane**, 6 internal guards. The record's reading: a rebuild that matches cell
for cell has been checked on 89 % of the statements, and the other 11 % is
where a defect or a workaround can sit unseen. Class C, the 61, "is where
the tribal knowledge sits": each row is a question for the subject matter
expert (deliberate orphan, test helper, cross-lane contract, or dead), and
its count is **the honest size of the tacit remainder for this lane**. The
clearest instance: a docstring reading "NOT A GATE. Do not give this a
production caller again", the record of two callers removed, which a
behaviour-first reading of the code never sees because nothing calls it.

### The capture protocol (method 1.2)

- **Elicitation shapes**: worked examples, counterexamples, exception
  walkthroughs, incident and repair stories, operational demonstrations,
  review by the domain or operations owner. The Dominique plan adds the
  shapes a person needs: quirk and orphan adjudication (each register entry
  classified deliberate, workaround for a data problem never fixed,
  temporary fix never refactored, or unknown), decision history, the network
  map, and the expert's own documents' linter findings taken as a block.
- **The register entry**, per item: stable ID and the concrete claim, rule,
  procedure or judgement; source or role, date, context, evidence,
  confidence; **elicited, directly observed, or merely inferred**; affected
  requirements, interfaces, invariants, operational outcomes; scope,
  exceptions, rationale, historical constraints; conflicts, open questions,
  validator, validation status; destination artefact and the test or
  example that demonstrates its meaning; the specification version in which
  it was accepted, revised or rejected.
- **Inference is not recovered knowledge.** An implementer's guess about
  an unspecified behaviour is a gap hypothesis. A missing dependency is not
  by itself evidence of tribal knowledge.
- **Observed, inferred, intended are three columns** (method 1.3): what the
  pinned system demonstrably does, a proposed explanation with its
  confidence, and what the responsible authority accepts. They may disagree;
  their provenance is preserved rather than merged into one requirement. A
  source defect never silently becomes desired behaviour: **a defect
  preserved for compatibility is a recorded decision** with scope and an
  acceptance example, and an independent rebuilder must reproduce it rather
  than silently repair it.
- **Knowledge lives in its normative home**: business rules and decision
  tables for policies; schemas, contracts and glossary for data semantics;
  state, process and sequence models for transitions; runbooks and
  dependency manifests for operations; decision records for rationale.
  Executable examples or checks wherever possible. The register links
  provenance and validation and **must not become a second, competing
  source of behavioural truth**.
- **Two transformations, evaluated separately**: code to artefacts
  (extraction fidelity: can consequential implemented behaviour be traced
  to explicit specifications, with inferences marked) and artefacts to
  recreated code (sufficiency: can an independent implementer derive the
  outcomes without undocumented project knowledge). The independent
  rebuilder works from the frozen package only; clarifications are
  recorded, never whispered.

### How a rule is lost: the enforcement state (added 2026-10-27)

Every rule item in the register carries where it is enforced, read from the
systems and controls, never from the expert's account:

- **system**: a loan system applies it. Verify, do not elicit; the expert's
  hours go to the *why*. Caveat: "system" means the code does it, defects
  included; the column says where a rule lives, never that it is right.
- **control**: a human step applies it (four-eyes check, checklist,
  reconciliation, sign-off). Capture the procedure as a runbook entry and
  name the successor operator; the item is lost when the operator leaves.
- **memory**: nothing applies it but the expert remembering to. The
  elicitation priority. Those a system or decision table could carry become
  automation candidates; those that are judgement stay worked cases and are
  never mechanised.

A system-enforced rule survives the departure with its reason missing; a
control-enforced one survives until its operator goes; a memory-only one
goes with the person.

### Measuring sufficiency

- **No percentage of all tacit knowledge captured.** The unknown population
  has no defensible denominator. Any ratio names a bounded, inventoried set
  of elicited items and shows how many were validated, externalised and
  checked. The readiness criterion: no known material project-specific
  knowledge dependency remains unresolved within the declared scope, with
  the residual uncertainty stated by name.
- **The grading test** (the person-side regeneration test): take the
  questions actually put to the expert over the last twelve months,
  de-duplicated, plus the successor's; run them through the question layer
  over the frozen corpus; the expert grades each answer correct and sourced,
  correct but unsourced, partial, wrong, correctly abstained, wrongly
  abstained. Every grade below correct-and-sourced becomes an elicitation
  item; repeat once. Report the bounded result with its denominator and the
  residual list by name.
- **The successor's questions are the blind test.** The expert's own grading
  of the corpus is repair, not proof. After departure every question the
  successor asks is logged: answered from the corpus, answered from elsewhere
  and added, or recorded as lost. A twelve-week drift report closes the case.
- **Outcomes always reported with the denominator**: inventory (items found,
  by source and class); capture (validated, externalised, backed by a check);
  adjudication (quirks and orphans by class); enforcement (rule items by
  state); document findings (found, attributed, routed, resolved as slip,
  choice, exception or open; the re-lint count); the grading test; the
  system side (kit gates green, regeneration result, coverage classes); after
  departure; effort, so the next case can be sized. Indicative effort for two
  or three loan systems: 30 to 40 hours of the expert over six weeks, 15 to
  20 facilitator days, 10 to 15 engineer days, the successor half-time.

### What the linters find, and cannot (Appendix E of the case)

| artefact | tool | finds | cannot find |
|---|---|---|---|
| PlantUML analysis models | pumllint lint, score, cross-diagram rules | unjoined decisions, unreachable branches, dead ends, participants that differ between diagrams, missing requirement links, the maturity level | a well-formed flow that is wrong |
| requirements documents | pumllint trace with the feature files; the glossary check; an EARS-pattern check | requirements no model realises, none a test verifies, terms used three times and defined nowhere | a precise, traced, verified requirement the business never meant |
| decision tables | the DMN gap and overlap check | inputs no rule covers, inputs two rules claim, outcomes left as a category | a complete table with a wrong row |
| BPMN processes | bpmnlint; ARIS EPCs through aris2puml first | structural faults, and refusals where the process does not reduce to blocks | process intent |
| the set together | the manifest and the precedence rule | drift between copies, contradictions with no stated winner | which copy was right |

A linter certifies that an artefact is well-formed, complete against its
inventory and consistent with its neighbours. It cannot tell a wrong rule
from a right one when both are well-formed: in the experiment a model set
scored at Level 5, 100/100, had 12 claims contradicted by the code it
documented. The one exception is structural completeness: a decision
table's missing row is a fact about the table, and the gap check found an
unspecified behaviour without running the program. The plan's use of the
linters (the routing step, 2026-10-26): lint the expert's documents, attribute
each finding by author, route hers to a session as one block, where each is
resolved as a slip to correct, a deliberate choice to record with its reason,
or an exception path to write as a register entry; then re-lint.

### The question layer

The LLM over the corpus is used twice: as the test instrument that measures
sufficiency, then as the channel through which the successor reads the
corpus. Its answer policy: **cite or abstain**; label every answer as system
behaviour, recorded decision, or who to ask; show the corpus version; never
apply a judgement item as a rule, present it as a worked case with its
author and date; log every question and route every abstention to the
backlog; credit-related answers are auditable. **The layer assists; a person
decides. It never signs off on anything.** The named risk: judgement captured
as a rule and served as fluent, unaccountable, possibly regulated advice.

### The verdict on the departing-expert case

Necessary and not yet sufficient. The method as written has no inventory of
what the expert knows that nobody else does, so the plan builds that
inventory first, from her traces (tickets resolved and routed to her,
requirements and tests she wrote, the questions colleagues asked her over
twelve months, incident reports) and the system-side registers, before any
interview; rates each item by consequence if lost and uniqueness; captures
against it in example-driven sessions with the successor present from the
first; measures by the grading test; freezes the corpus as of her last day
with the residual list in the handover, not in an appendix. Risks the plan
names, with controls: false confidence (the corpus answers most questions and
reads as complete); judgement served as advice; customer data in records;
staleness; **the single point of failure moving to the corpus and its owner**;
the expert's availability or goodwill; no successor or a late one; the
network knowledge decaying fastest. What the plan does not do: claim to
capture all of her knowledge; make the question layer an adviser; replace
the successor; prove the systems correct, only that what they do is written
down and a rebuild from the writing matches on the exercised behaviour.

### The older touchpoint: the independent evidence (2026-10-12)

METR, an independent AI-evaluation non-profit, ran the field's only rigorous
randomised controlled trial of AI-assisted development: 16 experienced
maintainers, 246 real issues in their own mature repositories, early-2025
tools. With AI the developers took 19 % longer, after forecasting a 24 %
speed-up and still believing in a 20 % speed-up afterwards. Of METR's five
likely contributors, the load-bearing one is **the developers' implicit
knowledge of their own repositories, context the AI never saw because
nothing forced it to be explicit**. The record's reading: the strongest
independent argument that tacit context is a real tax, and explicit,
machine-checkable context is the countermeasure. Always cited with its
update: METR's February 2026 continuation on late-2025 tools measured 18 %
and 4 % slower with intervals spanning zero and a disclosed selection effect
biasing its estimates downward; METR calls the new data "only very weak
evidence". What survives is the perception gap and the factor analysis; the
19 % headline is a 2025 artefact, not a constant.

### Bearing on the deck

Where the repository record supports, qualifies or contradicts the deck as
it stands. Decisions are the author's; this only lists them.

- **Supports** the TL;DR's split into AI extraction then SME validation, the
  "living documentation" that is version-controlled, the Risk Flags row's
  linters, the on-premises constraint, and the outline's "AI output is a
  first draft" mitigation. Adds the mechanism the deck lacks: provenance per
  item and the observed / inferred / intended split.
- **Qualifies "Why This Works"**. "Tacit knowledge: extracted from code
  comments, logic branches, and undocumented rules" is the first row of the
  five-kinds table only. The code yields the *what*; the *why* arrives as
  questions (orphans, quirks, guards), and judgement, decision history and
  the network do not arrive at all. The measured remainder on one real lane
  was 11 % of statements unexercised and 61 lines with no caller.
- **Qualifies the Goal and Key Metric 1**. "Reduce SME dependency by min.
  30 %" has a denominator only if it counts ad-hoc requests, as metric 1 does.
  The record's warning is against the other reading: a percentage of
  knowledge captured.
- **Contradicts Key Metric 3 as worded**. "% of critical knowledge &
  information documented & validated" is the ratio the method refuses: the
  unknown population has no denominator. The method's form is a bounded
  inventory with counts (found, validated, externalised, checked) and a
  residual list by name, plus the grading test's score over a real question
  set.
- **Adds to Key Metric 2**. Onboarding speed has a measured proxy in the
  plan: the successor's questions after departure, answered from the corpus
  versus answered from elsewhere versus lost.
- **Adds a missing step to the Core Approach**: an inventory of what the
  SMEs alone know, built from their traces before any review session, with
  consequence, uniqueness and enforcement state. Without it SME Validation
  spends the scarce hours on what is already written.
- **Adds a missing risk** to the outline's table: the single point of failure
  moving from the SME to the corpus and its owner, and the question layer
  serving judgement as advice. The plan's controls: a named owner, the
  corpus under the change process, cite-or-abstain, labelled answers, no
  sign-off by the layer.
- **Gives the deck its independent citation**: METR 2025 with its 2026
  update, for the claim that implicit knowledge is a real cost.
- **Terminology**: the deck's definitions ("hard to articulate", "how things
  really work here") and the method's ("used without fully stating it",
  "historical workarounds, deployment rituals, unwritten business rules")
  agree; the method adds that neither kind is authoritative because stated.

## Seven kinds of knowledge: grounded, asserted, deductive, inductive, abductive, tacit, tribal

*A fourth source, researched from the web on 2026-10-29 on the maintainer's ask and kept apart from the three above: definitions of the seven terms (grounded knowledge added on 2026-10-29 on the maintainer's ask, after the six were researched), how they overlap or complement one another, and terminology cautions for the deck. Nothing here overrides the deck; the "Stages of one process" paragraph says how the terms map onto the pipeline the deck describes.*

*Research note, 2026-10-29, web sources only. plato.stanford.edu, iep.utm.edu and en.wikipedia.org were not reachable from this session, so SEP/IEP/Wikipedia content is cited from search extracts, not the live pages.*

**Labels.** The asker's "deducted / inducted / abducted knowledge" are non-standard; the standard forms are *deduced / induced / abduced* (adjectives *deductive / inductive / abductive*). The rest of this note uses the standard terms.

| Asker's label | Standard term used here |
|---|---|
| asserted knowledge | asserted (testimonial) knowledge |
| deducted knowledge | deductive (deduced) knowledge |
| inducted knowledge | inductive (induced) knowledge |
| abducted knowledge | abductive (abduced) knowledge |
| tacit knowledge | tacit knowledge |
| tribal knowledge | tribal knowledge |
| grounded knowledge (added) | grounded (observed) knowledge |

### 1. Framing

The first five terms classify a piece of knowledge by **how it is justified or arrived at**. Epistemology lists the sources of knowledge as perception, memory, reason (inference) and testimony [SEP-Test; Audi]; deduction, induction and abduction are Peirce's three "elementary kinds of reasoning" [SEP-Abd-P], testimony (someone else's say-so) is a fourth source, and **grounded knowledge** names the first, perception, in the form it takes here: direct observation of the artefact. So the five do share an axis. The literature refines the second half of the framing: *tacit* and *tribal* sit on two axes, not one. Nonaka's model has an **epistemological dimension** (tacit versus explicit: can it be articulated?) and a separate **ontological dimension** (held by an individual, a group, an organisation) [Nonaka94]. "Tacit" is a point on the first; "tribal" names a position on the second (group-held) plus an articulation status (not written down). So the honest picture is three axes: *justification* (grounded/asserted/deductive/inductive/abductive), *articulation* (tacit/explicit) and *social holding* (individual/team/organisation). Any one claim has a value on each.

### 2. Definitions

**Grounded knowledge.** *Not a canonical term; this is the deck's own definition.* A claim whose justification is a traceable observation of the artefact itself, pinned to a version: a line of code read, a schema, a stored value, an execution trace. It is the observational source of knowledge (perception, extended to instruments [Votsis]) and the method document's **observed** column. "Grounded" carries related senses elsewhere, none of which owns the phrase: epistemology's knowledge as belief grounded in the facts [Pickel]; Harnad's symbol grounding, where a symbol means nothing until anchored bottom-up in sensory representations [Harnad90]; grounded theory in social science, theory derived from data rather than imposed on it (Glaser and Strauss, 1967; not verified against a source in this note); and LLM grounding, tying every answer to an external, checkable source rather than training memory [LLM-Ground]. For the deck, reserve "grounded" for observation of the pinned system: a citation to a document is asserted knowledge, by whoever wrote the document. *Example:* "the store writes `timestamp` as seconds under the pinned pandas" is grounded; it was read from the code and reproduced by execution. That the contract says milliseconds does not make it less grounded, only not intended.

**Asserted knowledge.** Three distinct senses exist; only the first is a kind of knowledge.
(a) *Testimonial sense.* Knowledge a hearer acquires by accepting a speaker's assertion on the speaker's authority, without working it out independently. The question since Hume (trust needs inductive backing) and Reid (1764, "principle of credulity": a standing, defeasible entitlement to believe what we are told) is whether a speaker's word alone can justify belief [SEP-Test; 1000WP]. (b) *Speech-act sense.* An assertion is the act of stating that something is so; Williamson (1996; 2000, ch. 11) argued assertion is governed by the **knowledge norm**: "assert p only if you know p" [IEP-KN; Williamson96]. A norm on speakers rather than a kind of knowledge, but it is why an SME's sign-off carries weight: to assert is to represent oneself as knowing. (c) *Knowledge-base sense.* In ontologies and expert systems, **asserted** axioms or facts are those explicitly entered; **inferred** (or *derived*) ones are computed by a reasoner. Protégé shows asserted and inferred class hierarchies side by side [Protégé]; the OWL working group noted tools must keep the two apart [W3C-OWL]; AI textbooks call the split primitive versus derived knowledge [Poole]. *Example:* "The settlement cut-off is 16:00 CET because the ops lead says so" is asserted knowledge; it was never derived from the code.

**Deductive knowledge.** Knowledge obtained by an argument in which, if the premises are true, the conclusion cannot be false (validity) [IEP-DI]. Peirce (1878) illustrated it with his bean bag: *Rule* (all beans from this bag are white) + *Case* (these beans are from this bag) gives *Result* (these beans are white) [Peirce1878]. Deduction is truth-preserving and introduces no new idea: it "merely evolves the necessary consequences of a pure hypothesis" [SEP-Abd-P]. Certainty: as high as the premises. *Example:* reading `if amount > limit: reject()` and concluding that any amount above the limit is rejected — certain, given the code and the runtime semantics.

**Inductive knowledge.** Knowledge obtained by generalising from observed instances to a rule; the premises make the conclusion probable, not certain (strength, not validity) [IEP-DI]. Peirce's form: *Case* + *Result* gives *Rule* — "all the beans in the bag were white", "an inversion of the deductive syllogism" [Peirce1878]. Induction is ampliative (says more than the data) and so defeasible by the next observation. *Example:* 10,000 replayed transactions show that every rejected payment has a reason code; "rejections always carry a reason code" is inductive, and one counter-example in the archive breaks it.

**Abductive knowledge.** A candidate for knowledge, obtained by proposing a hypothesis that would explain a surprising observation. Peirce's 1903 schema: "The surprising fact, C, is observed; but if A were true, C would be a matter of course; hence there is reason to suspect that A is true" (CP 5.189) [SEP-Abd-P]. It is "the only logical operation which introduces any new idea" (CP 5.171) [SEP-Abd-P], and Peirce's form from 1878 is *Rule* + *Result* gives *Case*. Modern usage often merges it with inference to the best explanation, a phrase Peirce never used [SEP-Abd]. Certainty: lowest of the three; it yields a hypothesis to test. *Example:* a legacy batch job skips records dated 29 February; the reverse engineer proposes "an upstream mainframe date library could not handle leap days" — plausible, explanatory, unproven.

**Tacit knowledge.** Michael Polanyi's term (*Personal Knowledge*, 1958; *The Tacit Dimension*, 1966): "we can know more than we can tell" [Polanyi66, p. 4]. His examples are recognising a face, riding a bicycle, a scientist's nose for a promising problem: skilled performance guided by particulars the performer attends *from*, not *to*, and so cannot fully specify. Nonaka (1994) and Nonaka and Takeuchi (1995) imported the term into management as one pole of the tacit/explicit pair and claimed it can be "externalised" through metaphor, analogy and models [Nonaka94; N&T95]. *Example:* a settlements operator who knows a reconciliation break "looks wrong" before any rule fires, or picks the right exception queue without being able to state the criteria.

**Tribal knowledge.** An informal industry term: "unwritten information that is not commonly known by others within a company" [Wiki-TK]; iSixSigma's definition adds that it is held only in employees' heads and assumed factual without data to verify it [iSixSigma via iConnect]. The name is an analogy with anthropology's tribes, popularised by the Six Sigma community, and sometimes considered derogatory [Wiki-TK]. There is no canonical academic source; the nearest scholarly concepts are *organisational memory* (Walsh and Ungson 1991: "stored information from an organization's history that can be brought to bear on present decisions") [W&U91] and Naur's *theory* of a program, which lives in the team and dies when the team disbands [Naur85]. *Example:* "never run the end-of-day job before the FX feed is confirmed, because of the 2014 incident" — known to the team, in no runbook.

### 3. Comparison table

| Term | Axis | Arrived at / held | Writable as is? | Typical failure mode | Validated by |
|---|---|---|---|---|---|
| Grounded (observed) | Justification | Direct observation of the pinned artefact | Yes, with its pointer (file, line, version, trace) | Observing the wrong thing (a dependency changed under the code); mistaking what the system does for what the business intends; drift once the pin moves | Re-observation at the pin; execution; the regeneration test |
| Asserted (testimonial) | Justification | Taken on a speaker's word | Yes, as a sourced statement | Trusting an unreliable or outdated source; hearsay chains | Checking the source's competence and sincerity; corroboration [SEP-Test] |
| Deductive | Justification | Necessary consequence of premises | Yes, with premises | True of the code, false of the business (wrong premises) | Re-derivation; checking premises |
| Inductive | Justification | Generalisation from cases | Yes, with sample and confidence | Over-generalisation; unseen counter-examples | More cases; search for counter-examples [IEP-DI] |
| Abductive | Justification | Hypothesis that would explain an observation | Yes, *as a hypothesis* | Mistaking a plausible story for a fact; rival explanations ignored [SEP-Abd] | Test, or an authority confirms it |
| Tacit | Articulation | Embodied skill or judgement, used without stating | Only partly, and with loss [Polanyi66; Tsoukas03] | Lost with the person; cannot be audited | Observed performance; apprenticeship; SME review of drafts |
| Tribal | Social holding + articulation | Shared informally within a team | Yes in principle (it is often sayable), but nobody has | Lost with turnover [Rigby16; Nassif17]; believed without evidence | Writing down, then checking against system and authority |

### 4. Overlap and complementarity

**Orthogonal pairs.** Each justification term is independent of the tacit/explicit and individual/group axes: a deduction can be explicit and personal, an abductive hunch tacit, a testimonial claim tribal. Grounded knowledge is by construction explicit and pointable, so it is the one kind that is never tacit; tacit and tribal knowledge are the kinds not yet grounded anywhere, which is why the pipeline exists.

**Grounded against the rest.** A deduction from code is grounded *and* inferred. An induction over traces is grounded and inferred, with a confidence. An abductive explanation of a quirk is inferred and not grounded until someone confirms it. A docstring, a comment or a colleague's account is asserted, however close to the code it sits: the record's timestamp case had four asserted artefacts saying milliseconds against one grounded reading saying seconds. Grounded is not intended: the reverse-cascade finding is that grounded knowledge inherits the code's defects as if they were decisions, so a grounded claim still needs the observed / inferred / intended split beside it, and a preserved defect stays a recorded decision. Tacit and tribal are also orthogonal in principle: much tribal knowledge is articulable but unwritten (a deployment ritual), whereas Polanyi's tacit knowledge resists articulation even by its holder.

**Nested or overlapping pairs.** Tacit knowledge often *consists of* inductively acquired pattern recognition: the operator's "this looks wrong" is a classifier trained on cases, held without the rule being stated. Tribal knowledge is *frequently* asserted knowledge: it propagates by testimony ("the old hands say..."), which is why iSixSigma flags it as assumed factual with no data behind it. Explicit knowledge (Nonaka) results from *externalising* tacit knowledge; on Nonaka's two dimensions, "tribal" is roughly *group-level, not-yet-explicit* knowledge, which may be tacit or merely unwritten.

**Stages of one process.** For the reverse-engineering plus LLM-drafting plus SME-validation pipeline, the four justification terms line up as stages:
1. *Observation* and *deduction* from code give what the system demonstrably does — the method document's **observed** claims.
2. *Induction* over traces and data gives generalised rules with confidence; *abduction* gives proposed explanations for quirks. Both are **inferred** claims. Brooks's model of program comprehension is exactly this hypothesis-and-beacon loop [Brooks83], and debugging literature calls abduction the only move that generates a candidate cause [Vinju19; HypoDeduce26].
3. An SME's confirmation converts an inferred claim into an **asserted** one in the testimonial sense (the SME vouches for it, under the knowledge norm of assertion), and, if the SME is the responsible authority, into an **intended** claim. In knowledge-base terms the claim moves from *inferred* to *asserted* provenance [Protégé; W3C-OWL].

This matches the method document's rule that an implementer's guess is "a gap hypothesis, not recovered tacit knowledge": a guess is abductive and unconfirmed, whereas recovered tacit knowledge is a claim about what a practitioner actually does, which only observed practice or the practitioner's confirmation can supply. The pipeline as a whole externalises tacit and tribal knowledge into explicit, asserted statements: Nonaka's externalisation step, and precisely the move Tsoukas calls lossy [Tsoukas03]; SME validation is the control on that loss.

### 5. Terminology cautions

- **"Grounded knowledge"** is not a fixed term in any literature; the deck should give its own definition (above) and say that LLM "grounding" is weaker: a citation to any source, where the deck means observation of the pinned system.

- **"Deducted / inducted / abducted"** are not used in logic or epistemology; "deducted" means subtracted and "abducted" means kidnapped. Use *deduced/inferred by deduction*, *induced*, *abduced*, or the adjectives *deductive/inductive/abductive knowledge*.
- **"Asserted knowledge"** is not a fixed term either; it borrows from three literatures. Say which sense is meant; for the pipeline the knowledge-base sense (entered by an authority, not derived) is the most useful.
- **"Tribal knowledge"** is an industry colloquialism with no canonical academic source; it was popularised by the Six Sigma community and is sometimes felt to be derogatory [Wiki-TK]. Academic alternatives: *organisational memory* [W&U91], *organisational* or *institutional knowledge*, Naur's *theory of the program* [Naur85], and the software-engineering literature on *turnover-induced knowledge loss* [Rigby16; Nassif17].
- **"Tacit"** has a strong and a weak sense. Polanyi's strong sense: knowledge that cannot be fully told even by its holder. The knowledge-management sense (Nonaka): knowledge not yet written down but convertible. Tsoukas (2003) argues the second misreads the first: tacit knowledge "cannot be 'captured', 'translated', or 'converted' but only displayed and manifested in what we do" [Tsoukas03]. A deck on *preserving* tacit knowledge should say which sense it means; most of what the pipeline recovers is tacit in the weak sense, and the strong-sense residue is what SME validation and apprenticeship exist for.

### 6. References

- [SEP-Abd] Douven, I., "Abduction", *Stanford Encyclopedia of Philosophy* (2011, rev.). https://plato.stanford.edu/entries/abduction/
- [SEP-Abd-P] "Peirce on Abduction", supplement to the above. https://plato.stanford.edu/entries/abduction/peirce.html
- [Peirce1878] Peirce, C. S., "Deduction, Induction, and Hypothesis", *Popular Science Monthly* 13 (Aug. 1878). https://en.wikisource.org/wiki/Popular_Science_Monthly/Volume_13/August_1878/Illustrations_of_the_Logic_of_Science_VI
- [IEP-DI] Shanahan, T., "Deductive and Inductive Arguments", *Internet Encyclopedia of Philosophy* (2022). https://iep.utm.edu/deductive-inductive-arguments/
- [SEP-Test] Adler, J., "Epistemological Problems of Testimony", *SEP* (2006, rev. 2012). https://plato.stanford.edu/entries/testimony-episprob/
- [1000WP] "Take My Word for It: On Testimony", *1000-Word Philosophy* (2014). https://1000wordphilosophy.com/2014/01/27/take-my-word-for-it-on-testimony/
- [SEP-Assert] Pagin, P. and Marsili, N., "Assertion", *SEP*. https://plato.stanford.edu/entries/assertion/
- [IEP-KN] Benton, M., "Knowledge Norms", *IEP*. https://iep.utm.edu/kn-norms/
- [Williamson96] Williamson, T., "Knowing and Asserting", *Philosophical Review* 105(4), 1996, 489–523; and *Knowledge and its Limits* (OUP, 2000), ch. 11.
- [Protégé] Protégé documentation, "Class Hierarchy" (asserted vs inferred views). https://protegeproject.github.io/protege/views/class-hierarchy
- [W3C-OWL] OWL Working Group list, Jan. 2009, on distinguishing asserted from inferred axioms. https://lists.w3.org/Archives/Public/public-owl-wg/2009Jan/0105.html
- [Poole] Poole, D. and Mackworth, A., *Artificial Intelligence: Foundations of Computational Agents*, §14.2 (primitive vs derived knowledge). https://artint.info/2e/html2e/ArtInt2e.Ch14.S2.SS3.html
- [Polanyi66] Polanyi, M., *The Tacit Dimension* (Doubleday, 1966), p. 4; *Personal Knowledge* (Chicago, 1958). Commentary: https://infed.org/dir/michael-polanyi-and-tacit-knowledge/
- [Nonaka94] Nonaka, I., "A Dynamic Theory of Organizational Knowledge Creation", *Organization Science* 5(1), 1994, 14–37. https://econpapers.repec.org/RePEc:inm:ororsc:v:5:y:1994:i:1:p:14-37
- [N&T95] Nonaka, I. and Takeuchi, H., *The Knowledge-Creating Company* (OUP, 1995). Summary of SECI: https://www.open.edu/openlearn/money-business/making-creativity-and-innovation-happen/content-section-7.1
- [Tsoukas03] Tsoukas, H., "Do we really understand tacit knowledge?", in Easterby-Smith and Lyles (eds), *Blackwell Handbook of Organizational Learning and Knowledge Management* (2003). https://mba.eci.ufmg.br/downloads/dowereally.pdf
- [Wiki-TK] "Tribal knowledge", *Wikipedia*. https://en.wikipedia.org/wiki/Tribal_knowledge
- [iSixSigma via iConnect] Shaughnessy, A., "Tribal Knowledge: Friend or Foe?", iConnect007 (quoting the iSixSigma dictionary). https://iconnect007.com/article/135500/the-shaughnessy-report-tribal-knowledgefriend-or-foe/135503/design
- [W&U91] Walsh, J. P. and Ungson, G. R., "Organizational Memory", *Academy of Management Review* 16(1), 1991, 57–91. Summary: https://kmt.helpjuice.com/organizational-memory-and-knowledge
- [Naur85] Naur, P., "Programming as Theory Building", *Microprocessing and Microprogramming* 15 (1985), 253–261. Notes: https://www.ratfactor.com/papers/naur1
- [Rigby16] Rigby, P. C., Zhu, Y. C., Donadelli, S. M. and Mockus, A., "Quantifying and Mitigating Turnover-Induced Knowledge Loss", *ICSE 2016*, 1006–1016.
- [Nassif17] Nassif, M. and Robillard, M., "Revisiting Turnover-Induced Knowledge Loss in Software Projects", *ICSME 2017*. https://www.cs.mcgill.ca/~martin/papers/icsme2017.pdf
- [Brooks83] Brooks, R., "Towards a theory of the comprehension of computer programs", *Int. J. Man-Machine Studies* 18 (1983), 543–554. Discussion: https://www.cs.kent.edu/~jmaletic/Prog-Comp/Papers/OBrien01.pdf
- [Chikofsky90] Chikofsky, E. J. and Cross, J. H., "Reverse Engineering and Design Recovery: A Taxonomy", *IEEE Software* 7(1), 1990, 13–17. https://program-transformation.org/Transform/ReverseAndReengineeringTaxonomy
- [Vinju19] Vinju, J., "Unroll: three ways of reasoning while debugging" (2019). https://homepages.cwi.nl/~jurgenv/2019/03/07/debugging-methods-of-reasoning.html
- [HypoDeduce26] "Abductive Reasoning for Neurosymbolic Fault Localization", *ICSE 2026 NIER*. https://conf.researchr.org/details/icse-2026/icse-2026-nier/38/Abductive-Reasoning-for-Neurosymbolic-Fault-Localization
- [Audi] Audi, R., *Epistemology: A Contemporary Introduction* (Routledge), on the standard sources of knowledge.
- [Votsis] Votsis, I., "Grounded Empiricism", *European Journal for Philosophy of Science* (2025). https://www.votsis.org/PDF/Votsis_Grounded_Empiricism.pdf
- [Pickel] Pickel, B., "Knowledge as Factually Grounded Belief" (PhilPapers record). https://www.philpapers.org/rec/PICKAF-2
- [Harnad90] Harnad, S., "The Symbol Grounding Problem", *Physica D* 42 (1990), 335–346. https://eprints.soton.ac.uk/250382/3/sgproblem1.html
- [LLM-Ground] Iguazio glossary, "What is LLM Grounding?" https://www.iguazio.com/glossary/llm-grounding/ ; Parallel, "Grounding (LLM)". https://parallel.ai/learn/grounding-llm

## The storyline, as built (2026-10-29)

*The deck built from this document: fourteen content slides (twelve, plus the
cascade slide and the lifecycle slide, both added on 2026-10-29) and a four-slide
appendix, at https://claude.ai/artifact/6NtCi1b9HBujfWuSAuKKe6 (private
until shared). Decisions taken by the maintainer on 2026-10-29: the
twelve-slide cut with an appendix; the systemic model present only through
its findings, never as its own slide; the departing-expert case told as the
pilot; Jeff Patton's ten-box opportunity canvas; plain language, full
sentences, no comma-spliced clauses. Two later changes: the deck covers
every layer of the lifecycle (business rules and processes, requirements,
architecture, code, operations), not code alone; and the slide on what the
automated checks saw in the degradation test was folded into the
validation-per-layer slide. The two bodies of work the deck joins: the
reverse-engineering research (the recreation experiment, the coverage
register, the departing-expert case, method 1.2 and 1.3) and the systemic
model (Legible's systemic impact model v0.2, tested against the experiment
on 2026-10-28, probed by the degradation test graded on 2026-10-29).*

### The spine

Five beats. The two research lines each carry one turn.

1. **The risk.** Knowledge lives at every layer of the lifecycle, and each
   layer loses it in its own way. A gap in any layer reaches the layers
   below it through the artefacts derived from it. Where a rule is enforced
   says how it is lost: a system keeps applying it without its reason, a
   control stops when its operator leaves, memory leaves with the person.
2. **The claim, with evidence.** What exists at each layer can be
   recovered and checked. For behaviour, the code is the truth: an
   independent rebuild from a code-only specification kit matched the
   original to the cell. *(reverse-engineering research)*
3. **The limit, with evidence.** Each layer gives only what it holds, never
   why. The code turns the why into questions, and judgement, history and
   the network do not arrive at all. Measured: a tenth of one real program
   is never exercised and its orphans are where the tribal knowledge sits.
   The cascade runs both ways: a gap upstream arrives in the code as a
   decision, and a defect in the code flows back into its documents.
   *(systemic model: the downstream cascade confirmed with one refinement,
   the reverse path it lacked, the green gate over drift)*
4. **The approach.** Four stages at every layer with a human turn in the
   middle: observe each layer and run its check, draft inferences with the
   LLM and mark them inferred, have the expert assert or reject each one,
   externalise what survives into its normative home with a check that does
   not depend on the layer it validates. An inventory first, so the expert's
   hours go to what nobody else knows.
5. **The measure and the plan.** No percentage of knowledge captured. A
   counted inventory with a named remainder, and two regeneration tests:
   the system rebuilt from the writing, and the successor's questions
   answered from the corpus. Then the pilot.

The opportunity canvas sits at the hinge between beats 3 and 4. The SWOT
follows the approach and precedes the plan.

### Slide sequence, as built

| # | slide | the sentence it lands | draws on |
|---|---|---|---|
| 0 | Cover | Title, subtitle, author placeholder, October 2026 | deck |
| 1 | Executive summary | Risk, claim, limit, approach, measure, one line each | this section |
| 2 | Knowledge lives at every layer, and a gap cascades downstream | Five layer cards (business rules and processes, requirements, architecture, code, operations), each with what it holds and what is lost; the enforcement state in the closing line | deck Context; enforcement state; the model's cascade |
| 3 | Where the knowledge sits, and what reaches it | The five-kinds table: what the systems do, why, judgement, decision history, the network, against reverse engineering, expert sessions and the AI question layer | Dominique case |
| 4 | What exists can be recovered and measured. For behaviour, the code is the truth. | One code base; a kit of 158 requirements, 14 contracts, 8 diagrams, 95 scenarios; a rebuild identical cell for cell; the diagrams fixed layout and interfaces, which is what that layer holds | recreation experiment |
| 5 | The code does not tell us why. The remainder has a size. | 89 % exercised, 141 lines never reached, 61 with no caller; the "not a gate" orphan | coverage register |
| 6 | The cascade runs both ways, and we measured both | Downstream: 15 defects planted upstream, 6 reaching the code through the layer the builder trusted; diagram-only defects attenuated. Upstream: the timestamp unit and the crash written as a requirement. Three labels at every layer | degradation test; model review F1, F2, F3; method 1.3 |
| 7 | Where knowledge capture acts on quality | Added 2026-10-29 after v0.3 of the systemic impact model merged: the reduced knowledge view drawn inline from the model's JSON, sixteen nodes in four lanes, four levers on the nodes the capture practices act on, solid lines measured and dashed lines hypotheses; later slides renumbered by one | Legible site, `model/knowledge-view.svg`, v0.3 |
| 8 | Opportunity canvas | Patton's ten boxes; boxes 1 and 4 are "what problem do we want to solve" and "how we go about it" | below |
| 9 | The framework: four stages at every layer, and a human turn in the middle | Stage 0 inventory, then observe (grounded knowledge per layer, with each check's findings), draft (inferred), validate (asserted and intended), externalise (explicit, checked, living) | deck Core Approach; method 1.2, 1.3 |
| 10 | Validation at every layer: what a check sees, and what only an independent one can | One row per layer with what its check finds and cannot; the degradation numbers (15, 6, 6 of 6 passed the kit's own tests, 6 of 6 failed the independent ones); no check caught a wrong value; a perfect score over 25 contradicted claims | linters appendix; degradation results; model review F4 |
| 11 | How we measure: counts with a remainder, never a percentage | The no-denominator rule; the system-side rebuild test; the person-side grading test; the four metrics reworded | method 1.2; Dominique measures |
| 12 | SWOT of the proposed approach | Three points per quadrant, below | |
| 13 | Three passes over the lifecycle | Added 2026-10-29, later the same day, on the maintainer's ask: the five layers as columns, upstream left and downstream right, and three rows over them. Build, left to right, with what each handoff loses in amber; recover, right to left, from the traces and the running system back to the rules, with a diamond on each card for what a person adds; validate, left to right again, one check per layer, the rebuild from the record alone, the comparison with what runs as a dashed return line. The texts are slide 2's layers and losses and slide 10's checks. A first version drew the pilot as a git branch graph with time on the axis; replaced the same day, because the maintainer wanted the lifecycle on the axis | slide 2; slide 10; Dominique plan |
| 14 | The pilot: one departing expert, eight weeks before and twelve after | Seven phases on a timeline, the definition of done, the indicative effort, what comes after | Dominique plan |
| A | Appendix divider | Contents | |
| A1 | Seven kinds of knowledge on three axes | The seven terms with axis, one line and an example; the cautions on grounded, tribal and the two senses of tacit | research section |
| A2 | The people side | Inventory first; session shapes; the question layer's answer policy | Dominique plan |
| A3 | Risks and mitigations | The outline's five plus the three the record adds, in red | outline; Dominique risks |
| A4 | Independent evidence and sources | METR with its 2026 update; the sources behind the deck | landscape; research note |

### Opportunity canvas, as built

| box | content |
|---|---|
| **1. What problem do we want to solve** | Knowledge about our systems is held by a few people and in code nobody reads fast. When they leave or are busy, the reasons behind rules and workarounds are lost. The result is operational risk, slow onboarding and audit exposure. |
| **2. Users** | The successor and the new joiner. The expert as source. The product owner and risk as accountable. Audit as reader. |
| **3. Solutions today** | Ad-hoc questions to the expert. Handover notes written in the last weeks. Wiki pages that drift from the code. |
| **4. How we go about it** | Observe what exists at every layer, from process models to code, and run the check for each. Let an on-premises AI draft rules and explanations, marked as drafts. The expert confirms, rejects or explains each item. Accepted items go to their proper home with a check. A test independent of the code runs beside the documentation. An inventory of what the expert alone knows comes first. |
| **5. How it is used** | The successor asks the AI layer, which cites a source or abstains. Engineers read the kit beside the code. Audit reads the register. |
| **6. Adoption** | One departing expert as the pilot. Then the compliance-critical and high-dependency systems. |
| **7. User metrics** | Successor questions answered from the corpus, elsewhere, or lost. Requests to the expert's former role. |
| **8. Business problem** | Key-person risk. Continuity through turnover. Audit-ready evidence of what the systems do and why. |
| **9. Budget** | Per case: 30 to 40 expert hours, 15 to 20 facilitator days, 10 to 15 engineer days. Tooling on premises. |
| **10. Business metrics** | Items found, validated, written down and checked, with the remainder named. Rebuild results. Audit findings. |

### SWOT, as built

| | helpful | harmful |
|---|---|---|
| **internal** | **Strengths.** What exists at each layer is recoverable, and an independent rebuild measures how much the layers together carry. Automated checks are cheap and decisive on structure: missing tests, gaps in decision tables, drift between diagrams. Every item carries its source, its date and who validated it. Everything runs on premises. | **Weaknesses.** Each layer gives only what it holds, never why. Judgement, history and the network need people. Documents derived from the code inherit its defects. A test calibrated on the same code hides them. The evidence so far is one program, one domain and single runs. |
| **external** | **Opportunities.** Departures and reorganisations are scheduled, so a pilot has a natural case. Audit and regulators reward provenance and a stated remainder. Rules that live only in memory become a backlog for automation. | **Threats.** False confidence: a corpus that answers most questions and reads as complete. The single point of failure moves from the expert to the corpus and its owner. The AI layer serves judgement as advice, in a regulated domain. |

### What the deck changes against the original draft

- "Why This Works" is gone. Its claim survives for the first row of the
  five-kinds table only, on slides 3, 5 and 6.
- The Context slide became the five-layer slide. The problem is no longer
  a code problem; the code is one layer of five.
- Key Metric 3 is reworded from a percentage of knowledge to inventory
  counts with a remainder. Metric 2 gains the successor's-questions proxy.
- The Core Approach gains a stage zero, the inventory, runs at every layer
  and names the kind of knowledge each stage produces.
- "Living documentation auto-updated with code changes" gains its
  condition: a check that does not depend on the layer it validates.
- The artefacts table became the validation-per-layer slide, one row per
  layer with what its check finds and cannot, and absorbed the
  degradation-test numbers.
- Three risks are added: false confidence, the corpus as the new single
  point of failure, judgement served as advice.
- The bank's name and logo appear nowhere. The author line is a placeholder.

---

## Editorial notes

- **Conflicts resolved in the deck's favour**: SME-dependency target
  (min. 30 % vs 30–50 %); Code Analysis action ("and AI" added by the deck)
  and output (deck's placeholder vs outline's "call graphs"); Architecture
  Diagrams tool (deck's placeholder vs Mermaid.js); Risk Flags tools (deck
  adds pumllint and the Aris linter tool); SME turnover examples (deck adds
  "change department"); legacy logic ("custom/historical" vs "custom").
- **Deck-only content**: the TL;DR, the Definitions slide, and the four
  Key Metrics as a separate slide.
- **Outline-only content**: Implementation (three phases), Tools
  (on-premises) and Risks & Mitigations, Next Steps with owners and weeks,
  and the targets on the metrics.
- **Repository findings** are a third source in their own section above; they were not merged into the deck/outline text and no priority rule was applied to them.
- **The seven-kinds research note** (six researched, grounded knowledge added on the maintainer's ask) is a fourth source in its own section above, from web research only; its reference list stays with it.
- **The storyline section** describes the deck as built on 2026-10-29, with the decisions taken; its canvas and SWOT are the slides' text.
- **Open review items the deck flags itself**: Code Analysis output
  example; Architecture Diagrams tool list; Lucidchart (air-gapped) as the
  data-flow tool; the whole Documentation Artefacts table; the word
  "understand" and the term "artefacts" in Key Metrics, each with a
  footnote still to be written.
