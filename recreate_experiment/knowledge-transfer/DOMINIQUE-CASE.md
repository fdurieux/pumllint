# Knowledge transfer for a departing expert: the Dominique case

*Written 2026-10-24. A plan, not a record of a run. It applies the
knowledge-capture method of `recreate_experiment/rebuilds/codex-2026-10-24/
EVALUATION-METHOD.md` (versions 1.2 and 1.3) and the experiment's own
instruments (the specification kit, the quirks list, the unrealised-code
register) to one case: a person leaving, not a system being rebuilt. Names
and figures are illustrative.*

## The case

Dominique is a business analyst in professional loans with twenty years in
the bank: twelve as an adviser in a branch, eight as the analyst for the
loan systems. She is leaving in eight weeks. The question is whether
reverse engineering of the loan systems plus the documented approach for
capturing tacit and tribal knowledge is a sufficient transfer, and whether
a question-answering layer over the captured material (a large language
model reading the diagrams, documents and code) can stand in for her.

The short answer, argued in the earlier assessment and built into this
plan: the approach is necessary and not yet sufficient, because it has no
inventory of what she knows that nobody else does. The plan below builds
that inventory first, captures against it, and measures the residual. The
language-model layer is used twice: as the test instrument that measures
sufficiency, and then as the channel through which the successor reads the
corpus. It never signs off on anything.

## What has to be captured

Her knowledge is five kinds, and the instruments reach them unevenly.

| kind | example | reverse engineering | the capture protocol | the question layer |
|---|---|---|---|---|
| what the systems do | which rule rejects a dossier, where the pricing grid lives | strong, measurable | — | answers well, with citations |
| why they do it | the 2019 workaround for the guarantee data nobody fixed | orphans and quirks as questions only | the register, if elicited | answers only what was recorded |
| domain and policy judgement | when a sole trader's turnover dip is a warning and when it is seasonal | nothing | partial: worked cases and counterexamples | risky: fluent, unaccountable, possibly regulated advice |
| history of decisions | why the covenant module was descoped twice | nothing | decision records, if elicited | fine, if recorded |
| the network | who owns the collateral data, who can grant an exception, who to call at 16:55 | nothing | not addressed by the method | nothing |

Rows three to five are most of what twelve years in a branch produce, and
they are where this plan adds steps the method does not have.

## Principles carried over from the method

1. **Code is the truth for behaviour.** What the loan systems do is read
   from the systems, verified by regeneration, never from memory.
2. **Nothing is authoritative because she said it.** Every captured item
   carries its source, date, confidence and validator; an item disputed or
   unvalidated stays marked as such.
3. **A bounded inventory, an explicit residual, no percentage.** "We
   captured 80 % of her knowledge" has no denominator. The result is: this
   many items inventoried, this many validated, this many externalised and
   checked, these left open.
4. **Observed, inferred, intended are kept apart.** What a system does,
   what someone thinks it means, and what the bank wants are three columns.
5. **Knowledge lives in its normative home.** Rules in decision tables,
   terms in the glossary, flows in process models, rationale in decision
   records, operations in runbooks, examples as executable tests. The
   register links them; it is never a second source of truth.
6. **Freeze and version.** The corpus is pinned as of her last day; later
   changes are new versions, so drift is visible.
7. **The successor's questions are the blind test.** Her own grading of the
   corpus is repair, not proof; the successor's fresh questions are.
8. **A defect preserved is a decision, not an accident.** Any quirk kept
   for compatibility carries a recorded decision, scope and example.

## The plan

Eight weeks before departure to twelve weeks after. Durations assume one
facilitator, one engineer, the successor part-time and four to six hours of
Dominique's week; adjust to the real notice period, keeping the order.

### Phase 0 — Mandate and scope (week 1)

*Steps.* Name the knowledge owner (the product owner for professional
loans), the facilitator (an analyst who runs the sessions and writes the
records), the engineer (reverse engineering and the question layer), the
successor, a second validator (her line manager or a peer analyst) and the
compliance and data-protection contacts. Fix the scope: which systems,
which products, which processes, what is excluded. Agree the three
classifications every item will get: codifiable rule, documented judgement,
relational. Agree the boundary for judgement: what the bank's policy leaves
to humans is captured as worked cases for training, never as a rule the
question layer may apply. Agree how customer cases are anonymised before
they enter any record.

*Why.* Without an owner the corpus has no maintainer after she leaves;
without the judgement boundary the plan captures regulated advice into an
answering system; without anonymisation it cannot use her best material,
real dossiers.

*Materials in.* Organisation chart, system inventory, policy on advice and
on data protection.
*Materials out.* A one-page scope note; a roles table; the classification
and anonymisation rules.
*Outcome.* The plan can start, and every later artefact has an owner.

### Phase 1 — Inventory from traces (weeks 1–2)

*Steps.* Mine Dominique's work products before interviewing her: the
tickets she resolved and the ones routed to her; the requirements, change
requests and test cases she wrote; the questions colleagues asked her in
mail and chat over the last twelve months; the release notes and incident
reports she contributed to. Each distinct thing she knew becomes a
candidate register entry with two ratings: consequence if lost, and
uniqueness (does anyone else know it). In parallel, run the system-side
extraction for the in-scope systems: the specification kit, its quirks
list, its unrealised-code register and the rebuilders' assumption files,
all of which are lists of questions a system cannot answer about itself.

*Why.* Interviews find what she remembers to mention; traces find what she
was actually asked. The experiment showed the same on the system side: the
code's own orphans and quirks were the sharpest questions, and an outside
rebuild found in a day a gap three internal rounds had missed.

*Materials in.* Ticket system export, document repositories, mail and chat
archives (with the data-protection contact's agreement), the kit and its
registers.
*Materials out.* The candidate inventory: one row per item, with source,
date, consequence, uniqueness, and a provisional class.
*Outcome.* The denominator. Every later claim of coverage is against this
list, and the list is dated.

### Phase 2 — Classify and prioritise (week 2)

*Steps.* With the owner and the successor, triage the inventory: confirm
or change each item's class, name its normative home, drop what is already
documented and validated, park what is low-consequence and not unique.
Order the rest by consequence times uniqueness. Group into session themes:
eligibility and pricing rules; exceptions and workarounds; incident
history; decision history; the network; the quirks and orphans of the
systems.

*Why.* Her hours are the scarce resource. Spending them on what is already
written, or on what three colleagues also know, is the failure mode.

*Materials out.* The prioritised inventory and the session plan.
*Outcome.* A schedule that fits the notice period, with the high-consequence
unique items first.

### Phase 3 — Elicitation (weeks 3–6)

*Steps.* Two to three sessions a week, ninety minutes each, one theme per
session, the successor present from the first. Session shapes, chosen per
theme:

- *Worked case.* An anonymised dossier walked end to end: what she looks
  at, in what order, what decides. Produces decision-table rows and
  glossary entries for the rule parts, and a worked example with her
  reasoning for the judgement parts.
- *Counterexample.* The same case with one fact changed until the outcome
  flips; the flipping fact is the rule's real boundary.
- *Exception walk.* Every known deviation from the standard flow: who may
  grant it, under what evidence, how it is recorded.
- *Incident replay.* A past incident from detection to resumption: what was
  seen, who was called, what was tried, what fixed it, what was never fixed.
  Produces runbook entries and, often, a quirk's rationale.
- *Quirk and orphan adjudication.* Each entry of the systems' quirks list
  and unrealised-code register: deliberate, workaround for a data problem
  never fixed, temporary fix never refactored, or unknown. The unknowns are
  the tribal remainder; they stay listed as unknown.
- *Decision history.* The initiatives that were tried, descoped or
  reversed, and why. Produces decision records.
- *Network map.* For every data set, rule and process in scope: who owns it,
  who can change it, who can grant an exception, who to call. Produces a
  decision-rights and ownership map, with named roles, not only names.

Each session ends with the facilitator writing the register entries and
the normative artefacts the same day; Dominique validates within two days;
the second validator reads anything marked judgement or disputed. The
executable half is built as it comes: a rule becomes a decision-table row
and an acceptance example; a term becomes a glossary row; a flow becomes a
process model that passes the model gates.

*Why.* Examples elicit what questions do not. A rule stated in the abstract
is wrong at its edges; the counterexample finds the edge. Writing the same
day keeps the record hers to correct while she still remembers what she
meant. The successor's presence makes the session a handover, not an
archive.

*Materials in.* The session plan, anonymised dossiers, incident reports,
the quirks list and the unrealised-code register, the ownership data.
*Materials out.* The knowledge register (validated entries), decision
tables, glossary, process models, decision records, runbook entries, the
ownership map, executable examples, and a list of items marked unknown or
disputed.
*Outcome.* The captured half of the inventory, each item in its normative
home with provenance, and the residual named rather than hidden.

### Phase 4 — Corpus and question layer (weeks 4–7, overlapping)

*Steps.* Assemble the corpus: the specification kits, the registers, the
decision records, the models, the glossary, the ownership map, the
runbooks, the answered-question archive. Pin it with a hash manifest. Build
the question layer as a retrieval-grounded reader with these properties:
every answer cites its sources; answers are labelled by class (what the
system does; what was decided and why; who to ask); where no source
supports an answer it abstains and says what it would need; every question
is logged, and every unanswered or low-confidence one goes to a backlog;
access is controlled and every answer touching credit judgement is
auditable; the corpus version is shown with each answer, and a stale
manifest is a visible warning.

*Why.* The layer's value is reach: people who would have called her get an
answer with a source. Its danger is fluency where she would have said "it
depends". Citations, abstention and logging are what turn the danger into
a backlog.

*Materials out.* The corpus, versioned; the question layer; its answer
policy; the question log.
*Outcome.* A queryable corpus and, from week 7, the instrument for the next
phase.

### Phase 5 — The grading test (weeks 7–8)

*Steps.* Take the real question set: the questions actually put to her
over the last twelve months, de-duplicated, plus any the successor has
already raised. Run them through the question layer over the frozen
corpus. Dominique grades each answer: correct and sourced; correct but
unsourced; partial; wrong; correctly abstained; wrongly abstained. Every
grade below correct-and-sourced becomes an elicitation item for the
remaining sessions. Repeat once after those sessions. Report the bounded
result: questions in the set, answered correctly with a source, partial,
wrong, abstained, and the residual list by name.

*Why.* This is the person-side regeneration test. It turns "is the
transfer sufficient" into a number with a denominator she and the owner
can read, and it finds the gaps while she can still fill them.

*Materials out.* The question set, the graded answers, the residual list,
the second-round result.
*Outcome.* A measured sufficiency statement in the method's own form: a
bounded set, a count validated, externalised and checked, a residual.

### Phase 6 — Freeze and handover (week 8)

*Steps.* Version the corpus "as of her last day"; the manifest is the
version's fingerprint. Publish the residual list as part of the handover,
not as an appendix. The owner signs the handover; the successor is in role
with the corpus, the question layer and the residual list. Dominique's
remaining availability after departure, if any, is agreed in writing and
limited to the residual.

*Why.* A handover without a stated residual is the green suite with a
missing file: it reads as complete. The frozen version is what later drift
is measured against.

*Materials out.* The frozen corpus, the handover note with the residual,
the sign-off.
*Outcome.* A dated, owned, measured state at the moment the dependency on
her ends.

### Phase 7 — After departure (weeks +1 to +12)

*Steps.* The successor works with the corpus and the question layer; every
question the successor asks is logged, and every one the layer cannot
answer is the blind test's finding. The owner reviews the backlog weekly:
items answered from elsewhere are added to the corpus as new versions;
items nobody can answer are recorded as lost, by name. The corpus is tied
to the change process: a change to a system regenerates its kit and
re-runs its gates and coverage; a change to a rule or an owner updates the
table or the map and the manifest. At twelve weeks, a drift check: the
grading test re-run on the successor's question set, reported in the same
form.

*Why.* The successor's questions are the only independent test the method
admits; the weekly review turns them into either knowledge or an honest
loss record; the change-process tie is what keeps the corpus from becoming
the next set of contradicted diagrams.

*Materials out.* The successor's question log, the weekly backlog
decisions, corpus versions, the twelve-week drift report.
*Outcome.* The dependency on one person replaced by a maintained corpus, a
person in role, and a known list of what was lost.

## Roles

| role | who | does |
|---|---|---|
| knowledge owner | product owner, professional loans | scope, priorities, sign-off, maintains the corpus after departure |
| facilitator | an analyst from the team | runs the sessions, writes register entries and normative artefacts the same day |
| engineer | one developer | reverse engineering of the in-scope systems, the corpus, the question layer, the gates |
| Dominique | the departing expert | sessions, validation within two days, grading |
| successor | the incoming analyst | present in every session, asks the questions, owns the backlog after departure |
| second validator | line manager or peer analyst | reads every judgement and disputed item |
| compliance, data protection | as named | the judgement boundary, anonymisation, audit of the question layer |

## Materials, consolidated

*Inputs.* Ticket exports, document repositories, mail and chat archives,
release notes, incident reports, anonymised dossiers, the in-scope systems'
code and configuration, their specification kits and registers, the
organisation and ownership data, the policies on advice and data
protection.

*Outputs.* The candidate and prioritised inventory; the knowledge register;
decision tables; the glossary; process models that pass the model gates;
decision records; runbook entries; the ownership and decision-rights map;
executable examples; the quirks and orphans adjudicated; the corpus with
its manifest; the question layer and its answer policy; the question set
and graded answers; the residual list; the handover note; the question log
and drift report after departure.

## Expected outcomes and measures

Reported in the method's form, always with the denominator:

- inventory: items found, by source and by class;
- capture: items validated, externalised to a normative home, backed by an
  executable example or check;
- adjudication: quirks and orphans classified as deliberate, workaround,
  temporary or unknown;
- grading test: questions in the set; answered correctly with a source;
  partial; wrong; abstained correctly; abstained wrongly; the residual by
  name, before and after the second round;
- system side: the kit gates green, the regeneration result, the coverage
  register's classes;
- after departure: the successor's questions asked, answered from the
  corpus, answered from elsewhere and added, recorded as lost;
- effort: hours of hers, the facilitator's days, the engineer's days, so
  the next case can be sized.

Indicative effort for a scope of two or three loan systems: 30 to 40 hours
of Dominique's time over six weeks, 15 to 20 facilitator days, 10 to 15
engineer days, the successor half-time. These are estimates to be replaced
by the measured figures.

## Risks and controls

| risk | control |
|---|---|
| false confidence: the corpus answers most questions and reads as complete | the residual list is part of the handover; the grading result is reported with its denominator; the successor's questions are the blind test |
| judgement captured as rule, and served as advice | the classification in phase 0; judgement items are worked cases marked as such; the answer policy labels classes and abstains; audit on credit-related answers |
| customer data in records | anonymisation before any record; data-protection sign-off in phase 0 |
| staleness after departure | manifest versions; change-process tie; twelve-week drift check |
| the single point of failure moves to the corpus and its owner | an owner named in phase 0, the successor in role, the corpus in the bank's repositories under its change process |
| her availability or goodwill in the notice period | the inventory from traces first, so sessions spend her hours on the unique items; the schedule agreed with her in week 1 |
| no successor, or one who arrives late | the plan still produces the corpus and the residual; the blind test waits for whoever asks the first questions |
| the network knowledge decays fastest | the ownership map names roles, is owned by the product owner, and is reviewed in the weekly backlog |

## Definition of done

The transfer is done when all of the following hold, and reported:

1. the inventory exists, dated, with every item classified and prioritised;
2. every high-consequence unique item is validated and in its normative
   home, or named in the residual list as unknown, disputed or lost;
3. every system in scope has a specification kit with green gates, a
   regeneration result, and an adjudicated quirks and unrealised-code
   register;
4. the grading test has been run twice and reported with its denominator;
5. the corpus is frozen as of her last day, with a manifest, an owner and a
   change-process tie;
6. the successor is in role, with the question log running;
7. the twelve-week drift report exists.

## What this plan does not do

It does not claim to capture all of her knowledge; it bounds what was
asked for and says what was not found. It does not make the question layer
an adviser: credit judgement stays with accountable people, and the layer
labels and cites. It does not replace the successor; it equips one. And it
does not prove the loan systems are correct, only that what they do is
written down and that a rebuild from the writing matches on the exercised
behaviour.

## Appendix A — register entry

```
id:            KT-0042
claim:         A guarantee recorded before 2019-06 has no legal-form code;
               the eligibility rule treats a missing code as "personal".
class:         codifiable rule (workaround for a data problem never fixed)
source:        Dominique, session 4 (incident replay), 2026-11-18
elicited/observed/inferred: elicited; confirmed observed in GUAR-LOAD line 212
confidence:    high
affects:       JDL-0xx (eligibility), decision table ELIG-3 row r7
normative home: decision table ELIG-3; decision record DR-017 (why not fixed)
example/check: scenario "Guarantee without legal-form code is personal"
validator:     second validator, 2026-11-20
status:        validated; decision pending on whether to fix the data
version:       corpus 2026-12-19
```

## Appendix B — session prompts

Worked case: "Take me through this dossier as you would on a Tuesday
morning. Stop at every point where you decide something." Counterexample:
"Change one thing so that you would decide differently. Which thing?"
Exception walk: "When does the standard flow not apply, and who says so?"
Incident replay: "What did you see first? Who did you call? What did you
try that did not work? What is still like that today?" Quirk adjudication:
"The system does this. Was that chosen, a workaround, a stopgap, or do you
not know?" Decision history: "What did we try and stop? Why?" Network:
"If this number is wrong at four o'clock on a Friday, who can fix it?"

## Appendix C — grading rubric

| grade | meaning |
|---|---|
| correct, sourced | the answer is what she would say, and cites the artefact that says it |
| correct, unsourced | right answer, no artefact behind it: the knowledge is in the corpus only by accident |
| partial | right direction, missing a condition or exception she would have named |
| wrong | she would contradict it |
| abstained, rightly | no artefact answers this, and the layer said so: an elicitation item |
| abstained, wrongly | an artefact answers it and the layer did not find it: a retrieval defect |

## Appendix D — answer policy of the question layer

Cite or abstain. Label every answer: system behaviour, recorded decision,
or who to ask. Show the corpus version. Never apply a judgement item as a
rule; present it as a worked case with its author and date. Log every
question; route every abstention to the backlog. Credit-related answers
are auditable. The layer assists; a person decides.
