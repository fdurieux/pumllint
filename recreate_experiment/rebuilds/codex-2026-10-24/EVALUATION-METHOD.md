# Independent recreation: approach and input evaluation method

Method version: 1.0  
Recorded: 24 October 2026  
Status: protocol recorded before implementation; no evaluation scores or results yet.  
Specification baseline: `88f656a39f47fe92a31e887e26888775658aa19b`.  
Output directory: `recreate_experiment/rebuilds/codex-2026-10-24/`.

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
