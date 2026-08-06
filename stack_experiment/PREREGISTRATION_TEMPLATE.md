# Wave pre-registration — [W_n: name]

*Frozen [date], commit [hash], BEFORE any scored run. Once a scored
(non-calibration) run exists, editing anything above the Results
section invalidates the wave — re-freeze consciously and say so. The
template encodes the house protocol (EVIDENCE.md discipline +
research-charter.md §7 standards); sections marked (mandatory) may not
be deleted.*

## Question and decision link (mandatory)

- The single question this wave answers, in one sentence.
- Which research-charter §, product decision, or gated ROADMAP item its
  outcome feeds — and what changes under each outcome branch (see
  Interpretation matrix). A wave with no decision link does not run.

## Design (mandatory)

- **Conditions/arms:** [list; for ladders state what each rung adds;
  for ablations state the leave-one-out set. Vary information at fixed
  carrier, or carrier at fixed information — never both at once
  (charter §2 E3).]
- **Units and n:** [diagrams/systems × runs per condition; pooled tiers
  carry the claims, never single runs.]
- **Models, exact IDs:** generator(s) [...], judge [...] — independent
  from the generator; repair/author roles if any, each firewalled as in
  the agent-repair protocol.
- **Prompts:** [named variant(s); the entry contract
  `handle(request)` stays byte-identical to the stored waves for
  cross-program comparability unless this section says otherwise.]
- **Oracle-separation declaration** (mandatory when any condition
  includes tests-as-input): the input-tests ↔ grading-suite
  relationship, per scenario (same / adjacent / disjoint), with the
  analysis split by class. For CargoQuote:
  stack_experiment/cargo_quote/tests_input/oracle_overlap.md.

## Oracles (mandatory)

- **Primary — execution:** suite file + hash at freeze; runner
  unchanged (tools/acceptance/runner_child.py); full and semantic-only
  pass-rates both reported; overlays listed.
- **Secondary — judged:** schema + rubric; judgments quoted as
  judgments, never merged with executed numbers.
- **Analysis standards:** quote gaps, orderings and correlations,
  never absolute rates; per-diagram/per-condition aggregation is the
  headline unit; NO hard-demand partials on executed gradients
  (mediator, not confound — charter §7); judged gradients may carry
  the hard-demand partial with both rationales cited.

## Calibration (mandatory, disclosed)

- What ran before this freeze: deterministic smoke
  (stack_experiment/smoke_test.py result), generation-calibration
  (pristine artifacts only, count + cost), every adapter/suite fix
  made, and the statement that no degraded/partial condition was
  executed pre-freeze.

## Pre-registered expectations (mandatory)

- E1/X1 ...: [direction + bar, e.g. "gap >= 10 pp", "r positive"].
  Number every expectation; each must be checkable from the report
  files alone.

## Interpretation matrix (mandatory, pre-committed)

- [Per expectation outcome branch — including the failure branches —
  what is concluded and what changes where. Failed expectations are
  recorded as failures with the same prominence as confirmations.]

## Budget (mandatory)

- Ceiling $[..] (hard, enforced by the harness cost guard); estimate
  $[..]; MAX_CALLS [..]; costs recorded per phase in the results.

## Carried limitations (mandatory)

- Toy-scale systems; LLM stand-ins for author and judge; n = [..];
  k = 1 repairs where applicable; single-shot generation [unless this
  wave is W5]; capability-relative — pivotal contrasts re-measured per
  model generation (charter §2 C1).

## Results ([date], $[cost])

*Written strictly after the freeze. Run notes recorded before the
verdicts (harness incidents, retries, protocol deviations — however
embarrassing). Then per-expectation verdicts: confirmed / failed, with
the pre-committed interpretation applied, never reinterpreted.*
