# Independent recreation: approach and input evaluation method

Method version: 1.3 (knowledge capture and reverse-engineering flow)  
Recorded: 24 October 2026  
Status: original protocol recorded before implementation; versions 1.1–1.3 clarify the SDD objective, knowledge externalization and reverse-engineering flow after the first run. The original baseline remains unchanged.  
Specification baseline: `88f656a39f47fe92a31e887e26888775658aa19b`.  
Output directory: `recreate_experiment/rebuilds/codex-2026-10-24/`.

## Research objective: a sufficient specification set for SDD

Amendment recorded on 24 October 2026 after the first recreation run.
The original baseline scores, protocol and run results remain historical
evidence; this clarification is not retroactive preregistration.

The objective is to identify the set of artefacts that lets an independent
developer or coding agent implement correct behaviour using those artefacts
as its only project-specific specification. The recreation is the experiment
used to evaluate that set. Per-file scores are supporting evidence; the main
research output is an actionable specification-package definition for
Spec-Driven Development (SDD).

"Artefacts only" permits ordinary programming knowledge, the declared
language/toolchain and pinned dependencies. It excludes undocumented
project-specific behaviour, prior implementations, hidden oracles and
unrecorded human clarification. A clarification that changes or supplies
behaviour becomes a versioned input artefact before it can support a
subsequent sufficiency claim.

### Candidate package and information obligations

These are information obligations, not a requirement to create a separate
document for every row or use every notation in every project.

| Information obligation | Candidate artefacts | Applicability |
|---|---|---|
| Purpose, scope and observable success | Requirements, boundaries, acceptance criteria, domain glossary | Every package |
| Data and interface meaning | Schemas, API/CLI contracts, units, types, invariants, compatibility rules | Wherever data or interfaces exist |
| Behaviour and decisions | Business rules, decision tables, state models, process/sequence descriptions | Wherever rules, states or ordering affect correctness |
| Computational semantics | Formulas, operation order where material, examples, boundary/error cases | Wherever numerical or algorithmic choices affect results |
| Execution and dependencies | Environment/version manifest, configuration, external contracts and supplied dependencies, operational requirements | Every runnable package, scaled to its context |
| Verification oracle | Executable acceptance cases, expected outputs with provenance, meaningful fixtures, test/injection interfaces | Every package |
| Navigation, authority and change control | Input manifest, reading path, source precedence, trace links and version history | Every package with multiple artefacts |

Record which obligations each artefact satisfies. Classify it as primary
normative content, independent verification evidence, or a derived view.
A generated diagram or summary can improve comprehension without supplying
additional independent behavioural facts. Duplicate information alone is
not evidence that another artefact is required.

### Sufficiency decision

Assess the package as a whole against the following criteria:

1. **Behavioural determinacy:** required externally observable choices can
   be derived without unresolved material guesses. Freedom in internal
   implementation is acceptable when it cannot change required outcomes.
2. **Input closure:** every material reference, interface, external
   prerequisite and validation resource is supplied, explicitly declared as
   an obtainable dependency, or explicitly excluded from the assessed scope.
   Merely calling a missing file "given" does not satisfy closure.
3. **Consistency and authority:** contradictions have a documented resolution
   rule; the implementer does not silently choose among competing meanings.
4. **Verifiability:** success has executable or otherwise inspectable evidence,
   with boundary/failure coverage appropriate to the requirements.
5. **Reproducibility:** the input version, environment, implementation and
   checks can be reproduced under the stated independence boundary.

Use qualified outcomes: demonstrated sufficient for the assessed scope;
sufficient only with recorded supplements/assumptions; not yet demonstrated;
or insufficient because a material gap is observed. A defect-free scorecard
or a green acceptance run alone cannot establish sufficiency.

Correctness has separate evidence layers: conformance to stated contracts;
internal consistency and independently derived invariants; and validity
against intended domain outcomes. Tests and contracts may share the same
incorrect assumption. Keep domain validity unverified where independent
evidence is absent.

### Convert findings into a package definition

For every unclear, missing, ambiguous or contradictory point, record:

- affected information obligation and requirement;
- whether it is missing content, incorrect content, conflicting content,
  missing external material, a verification gap, or harmless implementation
  freedom;
- material effect on observable behaviour and whether coding required a
  project-specific assumption or human intervention;
- the smallest content correction or additional artefact needed;
- where that information should have lived and how it should be validated;
- whether the correction requires rerunning affected scenarios.

Do not count every assumption entry as a specification failure. Separate
required quirks, harmless design choices and evaluation limitations from
material unresolved behavioural assumptions.

The final synthesis should state a proposed sufficient package, conditional
artefacts by project characteristic, observed gaps and required supplements,
and a checklist for deciding whether a specification is ready for coding.
It should also describe how changes propagate from normative artefacts
through trace links to implementation and regression checks. This makes
the result usable as an SDD workflow rather than only an experiment report.

### What the current recreation establishes

The run supplies evidence of conformance for 246 non-chain cases and 11
additional independent checks. All 257 supplied cases pass when the missing
shell externals are replaced by labelled test doubles, but the required
original-external integration run has 11 setup failures. Therefore the
unchanged input package has not demonstrated sufficiency for the complete
deployment/integration scope. The missing externals and excluded verification
resources are concrete package-closure issues; narrowing scope or supplying
the material must be explicit.

One successful recreation can support a scoped sufficiency claim. It cannot
prove that the proposed set is universally sufficient, or that every artefact
is necessary. Claims about a minimal set require separately designed removal
or comparison experiments and fresh independent implementations where
learning effects would otherwise bias the result. No such experiment has
been run or is silently implied by the present scores.

## Capturing tacit and tribal knowledge

Method version 1.2 amendment, recorded after the initial recreation on
24 October 2026. This is an extension of the research method, not a claim
that interviews or a new independent recreation have already taken place.

Tacit knowledge is practical know-how a person uses without fully stating
it, such as how they recognize an invalid result or choose an exception.
Tribal knowledge is project-specific understanding shared informally by a
team, such as naming conventions, historical workarounds, deployment rituals
or unwritten business rules. Both can be valuable, incorrect, outdated or
disputed; neither becomes authoritative merely because someone states it.

### Discovery and externalization

During specification preparation, elicit consequential decisions through
worked examples, counterexamples, exception walkthroughs, incident/repair
stories, operational demonstrations and review by the relevant domain or
operations owner. These are possible preparation activities, not authority
to contact people or inspect sources excluded from the current experiment.

For each candidate knowledge item, record:

- stable ID and the concrete claim, rule, procedure or judgement;
- source/person or role, date, context and evidence, with confidence;
- whether it was elicited, directly observed, or merely inferred;
- affected requirements, interfaces, invariants and operational outcomes;
- scope, exceptions, rationale and historical constraints;
- conflicts, unresolved questions, responsible validator and validation status;
- destination artefact and the test/example that can demonstrate its meaning;
- specification version in which it was accepted, revised or rejected.

Distinguish an inference from confirmed knowledge. An implementer's guess
about an unspecified behaviour is a gap hypothesis, not recovered tacit
knowledge. A missing dependency likewise is not automatically evidence of
tribal knowledge.

Externalize accepted knowledge in its normative home: business rules or
decision tables for policies; schemas/contracts/glossary for data semantics;
state/process/sequence models for transitions and ordering; runbooks and
dependency manifests for operations; decision records for rationale and
constraints. Add executable examples or checks where possible. A knowledge
register links provenance and validation; it must not become a second,
competing source of behavioural truth.

For example, the distinction between the injected run clock and the real
actions-file stamp is already explicit in this kit. That is useful
externalized implementation knowledge. It is not evidence that this
recreation discovered an unwritten team practice.

### Preserve the independent experiment

Keep elicitation and independent verification separate:

1. Freeze and version the candidate specification package after preparation.
2. Let the independent implementer use only that package and the declared
   toolchain, recording knowledge dependencies when information is absent.
3. Record material clarification requests, assumptions and their effects.
   Do not silently consult knowledgeable insiders to make the run succeed.
4. After adjudication, incorporate accepted clarifications into a new input
   version and link the affected checks. Preserve the original run and its
   sufficiency judgement.
5. Verify the revised version through affected regression checks. A stronger
   claim of independent artefacts-only sufficiency needs a fresh independent
   implementation where prior learning would otherwise supply the missing
   knowledge.

The implementer's accumulated understanding cannot be reset by merely
rerunning tests. A clarified version passing the same implementation's suite
is evidence of repair/regression, not a new blind recreation.

### Evaluation and scoring

For each artefact, assess whether consequential decisions depend on unwritten
knowledge, whether stated rules retain enough context and exceptions, and
whether an independent reader can apply them to examples. Link material
omissions to completeness, clarity and verifiability scores under the
existing rubric; do not retroactively add scores to the frozen baseline.

At set level, report known material knowledge dependencies, clarification
interventions, unsupported behavioural assumptions, and accepted items that
remain outside normative artefacts or verification evidence. Distinguish
these from ordinary internal design freedom and intentionally specified
quirks.

Do not report a percentage of all tacit knowledge captured: the unknown
population has no defensible denominator. Any ratio must name a bounded,
inventoried set of elicited items and show how many were validated,
externalized and checked. The readiness criterion is that no known material
project-specific knowledge dependency remains unresolved within the declared
scope, with residual uncertainty stated explicitly.

## Reverse-engineering within the SDD flow

Method version 1.3 amendment, recorded after the initial recreation on
24 October 2026. This describes an additional part of the research method;
it does not claim that an upstream source-to-specification audit has run.

For an existing system, reverse-engineering is an upstream way to discover
and validate specification content. For greenfield SDD, domain elicitation
and requirements engineering supply that content without a legacy reference.

| Stage | Activity | Output and evidence |
|---|---|---|
| Discover implemented behaviour | Inspect the original code, tests, configuration, interfaces and controlled execution traces | Versioned observations of rules, arithmetic, states, dependencies, boundaries and failure behaviour |
| Recover meaning and intent | Reconcile observations with domain and operational knowledge | Validated interpretations, rationale, exceptions, conflicts and open questions |
| Specify | Externalize accepted knowledge in the normative artefacts and executable examples | Candidate SDD package with source provenance, authority rules and trace links |
| Recreate independently | Freeze the package and implement using its artefacts only | Independent code, findings, assumptions and recorded interventions |
| Compare and adjudicate | Verify contracts and, in a separate validation role, compare observable behaviour with the original | Classified discrepancies, explicit compatibility decisions and versioned specification corrections |

### Two transformations, evaluated separately

1. **Code to artefacts:** assess extraction fidelity and completeness. Can
   consequential implemented behaviour be traced to explicit specifications?
   Are inferred rules marked as inferences, and is intended behaviour validated
   rather than merely assumed from the source?
2. **Artefacts to recreated code:** assess specification sufficiency and
   implementation conformance. Can an independent implementer derive the
   required outcomes without undocumented project knowledge?

Every extracted claim must distinguish:

- **Observed:** what the pinned original implementation demonstrably does.
- **Inferred:** a proposed explanation or generalized rule, with confidence.
- **Intended:** behaviour accepted by the responsible specification authority.

These statements may disagree. Preserve their provenance rather than merging
them into one apparently authoritative requirement. A source defect must not
silently become desired behaviour; preserving it for compatibility requires
an explicit decision, scope and acceptance example. Conversely, an independent
recreator must reproduce a clearly specified compatibility quirk rather than
silently repair it.

### Independence and discrepancy handling

The extraction role may inspect the original system. The independent
recreation role must not receive its source, hidden tests, prior recreated
code or historical outcomes. Use separate people or genuinely independent
execution contexts when testing that separation. Running both roles in the
same informed context cannot substantiate a blind reconstruction claim.

Freeze the specification and recreation revision before reference comparison.
A separate validator can hold the original implementation and additional
reference probes outside the recreator's inputs. Such probes provide
diagnostic evidence, not automatic authority over the stated requirements.
Any feedback or newly revealed behaviour becomes a recorded intervention;
changes to normative content create a new specification version.

For each discrepancy, record the input/setup, expected and actual outcomes,
evidence versions, affected requirements and one or more candidate causes:
extraction omission/error, inconsistent or ambiguous specification,
recreation implementation defect, original implementation defect, environment
mismatch, or invalid test oracle. Adjudicate using evidence and the stated
authority rules; do not automatically treat the original implementation as
correct.

Source-derived tests and contracts can share the same mistake. Evaluate
conformance, extraction fidelity and domain validity as separate evidence
layers, using independently justified invariants or validated domain examples
where available. Preserve unresolved validity as uncertainty.

The research output should identify information lost in each transformation
and the smallest artefact correction needed to prevent recurrence. Score the
affected artefacts with that evidence, preserving baseline scores and avoiding
double counting the same source fact across generated views.

### Status of this experiment

The completed run primarily evaluates artefacts to recreated code, subject
to the already documented external-script and validation limitations. No
independent audit of how faithfully the kit/handover were extracted from
the original code has been performed by this recreation. Documenting this
upstream stage does not authorize the recreator to inspect the excluded
original source or hidden material, nor does it establish a code-to-spec-to-code
round-trip correctness result.

## Purpose and scope

Recreate the program described by `recreate_experiment/handover/` and
`recreate_experiment/kit/`, and assess how well those inputs support an
independent implementation. The kit is the behavioural authority. Follow
the handover reading order and read the complete kit before writing code.

Assess each supplied artefact, including prose, requirements, diagrams,
decision models, schemas, configuration, examples, fixtures, feature files,
and acceptance-support code. Assess completeness of the set separately
from completeness of an individual file.

This protocol documents the agreed method; it does not add behavioural
requirements to the program or alter the supplied acceptance oracle.

## Independence and provenance

- Implementation inputs are limited to the handover, kit, and this new
  output directory, plus explicit user clarifications recorded here.
- Do not read, import, copy, search, or use prior recreated code, reference
  implementations, hidden tests, historical experiment outcomes, or other
  descriptions of this program. In particular, prior builds under
  `recreate_experiment/results/` and material under
  `recreate_experiment/hidden/` are excluded.
- Do not use external searches or network sources to fill behavioural gaps.
  Repository transport for the allowed inputs and publication of the new
  work are administrative operations, not additional specification inputs.
  Dependencies are limited to the kit's prescribed pins; obtaining them
  does not authorize consulting other implementations.
- Restrict reads and searches to allowed paths. Run the supplied kit suite
  against the independently installed package and its own adapter.
- Record input paths, revision, content hashes, read/use status, and any
  missing referenced files. Pin inputs before implementation; record later
  revisions and user clarifications explicitly.
- Record the model identifier and reasoning effort when verifiable. Record
  unavailable settings as unverified. The recommended setup is GPT-6.1
  with Extra High reasoning effort; recommendation is not proof of the
  actual setting.
- Keep the recreation's environment isolated from the prior packages with
  the same `jef` and `jef-data` names.
- Record any accidental exposure immediately, including what was seen,
  when, and its possible effect; do not claim perfect isolation afterward.

Pre-implementation exposure: the handover README and AGENTS instructions
were read, and repository path metadata was inspected to choose a separate
location. Prior implementation contents and experiment results were not
read. This is procedural independence, not a controlled blind experiment.

## Workflow and timing

1. Inventory all files in the permitted input set at the pinned revision.
   Distinguish primary sources, generated views, test oracles, and support
   tools. Record source/derivative relationships.
2. Before coding, read the required inputs and capture baseline scores,
   uncertainties, and set-level gaps. Contribution is initially unassessed.
3. During implementation, append evidence when an artefact resolves a
   decision, prevents an error, exposes a defect, or causes an assumption
   or rework. Record uncertainty while it is visible.
4. Run the supplied acceptance suite and link relevant failures and fixes
   to the input observations. Preserve baseline scores and explanations
   when revising a score.
5. At completion, publish final per-artefact assessments and a set-level
   synthesis, alongside the actual validation results and limitations.

Do not silently repair specification gaps or contradictions. Record them
in `ASSUMPTIONS.md`, explaining the choice and its justification. Changes
to the kit, if proposed, must remain distinct from the original baseline;
never claim a pass against an unchanged oracle if it was modified.

## Per-artefact scoring rubric

Score each dimension independently using integer scores from 0 to 5.

| Dimension | Question |
|---|---|
| Semantic correctness | Do rules, calculations, examples, and models express coherent, valid behaviour within the specified domain? |
| Completeness | Is the artefact sufficient for its stated scope, including boundaries, errors, defaults, and interfaces? |
| Consistency | Does it agree internally and with other applicable inputs? |
| Clarity | Can it be implemented without avoidable interpretation? |
| Verifiability | Can its claims be checked through concrete examples, contracts, invariants, or tests? |
| Implementation value | How directly did it help produce and validate the recreation? |

| Score | Anchor |
|---|---|
| 0 | Unusable for its stated purpose; fundamentally invalid or misleading |
| 1 | Major deficiencies; most relevant decisions require reconstruction |
| 2 | Substantial gaps; useful parts exist but significant assumptions are needed |
| 3 | Usable with explicit assumptions or interpretation |
| 4 | Strong; minor deficiencies with limited implementation impact |
| 5 | Precise and sufficient for its stated scope, supported by cited evidence |

Use `null` with a reason for unassessed, unverified, or not-applicable
dimensions; never encode missing knowledge as zero. Record confidence
(low/medium/high) and rationale for every dimension. Scores are ordinal
judgements, not calibrated measurements; do not average them into a
single apparently precise quality number.

Semantic correctness is distinct from agreement. A test and a contract
can agree and still share an error. Where no independent basis exists,
state that semantic correctness is unverified. Distinguish confirmed
defects, suspected defects, ambiguity, and intentional quirks. Required
quirks must be reproduced and must not be labelled defects merely because
another design would be preferable.

## Required record for every artefact

Maintain an entry with:

- Stable artefact ID, exact repository path, kind, baseline commit and hash.
- Role, stated scope, read status, use status, and parent/source links.
- Baseline and final dimension scores, per-dimension confidence,
  rationale, and supporting locations.
- Requirements, decisions, implementation locations, and test cases it
  supports; empty links must be explained.
- Strengths and specific weaknesses, with actionable corrections where
  justified.
- Linked findings, assumptions, and implementation or rework events.
- Contribution observations and limitations, including overlap with
  other artefacts.

Use findings with stable IDs, classification, severity, source locations,
affected requirements, implementation impact, chosen resolution, evidence,
and open/resolved status. Keep history when later evidence changes a
finding or score.

## Value and contribution

Record concrete events: a diagram revealed a dependency; a decision table
settled a branch; an example exposed arithmetic interpretation; a fixture
caught a collector error; conflicting texts required rework. Link the
event to the relevant code decision or validation evidence.

Classify observed contribution as decision guidance, interface definition,
error prevention, defect detection, validation, navigation, or redundancy.
Record negative effects such as ambiguity-driven rework as well as
benefits. Explain low or absent use; unread is not evidence of no value.

Derived summaries and original sources each receive an assessment, but
their shared information is attributed once in set-level coverage.
Readable generated views may contribute navigation or comprehension even
when they add no independent specification content.

These are observed contributions during one implementation. Do not claim
causal effect sizes, percentage quality improvement, unique necessity, or
comparative superiority without a separately designed controlled study.
Passing the suite does not prove full semantic correctness or input
completeness. No ablation study is authorized or implied by this protocol.

## Completeness of the input set

Assess the set against the declared requirements and end-to-end program
scope. Check for missing requirements, unreachable references, undefined
terms, missing interfaces, uncovered boundaries and failures, unresolved
contradictions, missing configuration or dependency information, and
insufficient installation or operational instructions.

Build a trace from requirements to specification evidence, relevant
design/decision artefacts, implementation, and validation. Distinguish
requirements specified but untested, tested but underspecified, and
behaviour implemented through assumptions. Document implicit requirements
discovered during implementation rather than treating the declared list
as necessarily exhaustive.

Report coverage counts with explicit denominators, source revision, and
exclusions. Separate file inventory coverage, requirement coverage,
acceptance-case coverage, and the number of unresolved findings. Do not
treat scenario counts as proof of semantic coverage. Use the rubric for
set-level dimensions where meaningful and explain each score independently.

## Deliverables and completion evidence

All recreation records live in this output directory:

| File | Content |
|---|---|
| `EVALUATION-METHOD.md` | This protocol and any explicitly recorded revisions |
| `INPUT-QUALITY.md` | Readable baseline/final per-artefact review and set-level synthesis |
| `input-quality.json` | Machine-readable inventory, scores, evidence, trace links, findings, and history |
| `ASSUMPTIONS.md` | Numbered gaps, choices, rationale, and linked findings |
| `README.md` | Implementation layout, provenance, environment, reproduction commands, actual results, and limitations |

Use `schema_version: "1.0"` in the JSON. Include `baseline_commit`,
`run_metadata`, `artefacts`, `findings`, `set_assessment`, and
`validation_runs`; represent unknowns explicitly. The readable review
and JSON must agree.

The handover currently states 163 requirements and 130 scenarios covering
257 acceptance cases, with completion defined as 257 passed, zero failed,
and zero skipped. Verify the actual pinned inventory and collected tests
before using these as denominators. Record exact commands, environment,
implementation revision, and actual results, including failures or skips.

Protocol completion requires an inventory entry for every supplied file,
evidence for assigned scores, explicit unknowns, traceable assumptions,
and documented independence limitations. It is separate from software
completion. This document records the method only; implementation,
assessment scores, and acceptance results remain pending.
