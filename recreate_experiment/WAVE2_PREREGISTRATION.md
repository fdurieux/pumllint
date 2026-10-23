# Wave 2 — the four missing layers, prioritised, built and measured

*Frozen 2026-10-23, before any layer is built or any result exists.
Follows `PREREGISTRATION.md` (the recreation experiment) and its
re-evaluation section in `docs/recreate-experiment.md`, which named four
layers of the maintainer's requirements-as-code stack the kit lacked:
property-based invariants, DMN decision tables with gap and overlap
analysis, Gherkin `Rule:` blocks, a vocabulary. The maintainer asked for
them to be prioritised, planned with a SWOT, amended as needed, and
implemented. Results are appended below the frozen text.*

## 1. Question and decision link

**Would the kit have caught its own two spec defects before any
recreation, had it carried the four layers — and what does each layer
buy on a real program?** The recreation experiment found two defect
classes by comparing rebuilds with the original: an unspecified CLI
surface and one unspecified refusal path (`export` on an absent series).
Examples sample a rule and cannot see the rule space; this wave adds the
layers that can, and measures whether they would have.

Feeds the research charter's "which artefacts" question from the
specification side. Changes no product behaviour, queues no build; the
pumlspec pilot is on hold and nothing here depends on it.

## 2. Priority order, with reasons

| # | Layer | Why this rank | Cost |
|---|---|---|---|
| 1 | **Property-based invariants** (Hypothesis, through the harness adapter) | Highest value per hour: executable at once against the original and all three existing rebuilds; upgrades the core claim from "identical on 14 fixture series" to "identical on a searched input space"; the only layer that can find a *behavioural* divergence the fixtures missed | low — the adapter already exposes every function; one strategy per input shape |
| 2 | **DMN decision tables + gap/overlap analysis** | Targets the completeness failure directly; the `export`-on-absent gap is a missing row in a command × store-state table, which gap analysis sees and examples never will | medium — tables are transcribed from the kit's existing contracts; a small DMN 1.3 reader with a completeness checker is lab tooling |
| 3 | **Gherkin `Rule:` blocks** | Structure, not information; its measurable use is the rule → example join, and the id tags already give that through `trace`. Kept, narrowed (§4) | low–medium |
| 4 | **Vocabulary / glossary** | Cheapest and least measurable; defends against term drift the experiment did not suffer. Kept, with one metric | low |

## 3. Design

All four layers are **additive revisions of the kit** under
`recreate_experiment/kit/` (dated "revision 2026-10-23 (wave 2)"), derived
from the kit's own contracts and the subject's code only — no J-F
document is read for them, as the maintainer ruled for the kit. The 162
requirements, the 98 scenarios and the 8 diagrams are not changed.

**Layer 1 — invariants** (`harness/invariants/`): Hypothesis strategies
generate recorded-fixture-shaped provider responses (bar series with
random prices, volumes including zeros, random split events with ratios
drawn from a realistic set and degenerate ones excluded by the kit's
refusal rule), universe files and clocks; properties run through the
adapter interface, so each runs on the original and on any rebuild. Two
classes: (a) *intrinsic* — adjustment identities (`close ==
close_raw / cumulative_split_factor`, `volume == volume_raw *
cumulative_split_factor`, factor exactly 1.0 on and after the last
split, non-increasing backwards), raw columns unchanged by
re-adjustment, idempotence (a second sync on the same fixtures changes
no cell and logs zero revisions), seam row count = stored rows minus
zero-volume and NaN rows, crypto request `end` ≤ yesterday UTC,
`status` exit 1 iff some alert fired, warnings never move the exit;
(b) *differential* — for every generated input the original's and a
rebuild's exported frame, stored frame, summary and status document are
identical, the pre-registered M1/M4/M5/M6 equality applied to a searched
space. **No float tolerance anywhere**: identities are checked as
exact recomputation with the same operations, and differential checks
are exact equality, so cell-level drift cannot hide.

**Layer 2 — DMN** (`kit/contracts/dmn/`): standard DMN 1.3 XML decision
tables for the kit's decisions — basis resolution (provider × declared
class → price basis, volume basis, actions eligibility, end-guard);
command × store state → outcome (`export`, `adjust`, `differential`,
`load`, `sync` leg × absent / raw / pre-adjusted); the sync window
(series empty, `start` declared, `end` declared, crypto → window form);
the actions gate (stamp present, stamp date < today, force → refresh or
fresh); the status verdicts (staleness, actions age, jump, spread with
its promote flag, declared-class comparison); refusal routing. Hit
policy UNIQUE unless a table needs FIRST, declared per table.
`harness/dmn_check.py`: a stdlib reader for that XML and the FEEL subset
the tables use (enumerations, `-`, comparisons, ranges, booleans) that
enumerates the input space (finite domains exhaustively; numeric domains
by the interval partition the rules induce plus boundary points) and
reports **gaps** (no rule matches) and **overlaps** (several match under
UNIQUE). The measurement that answers the question: the command ×
store-state table is first written **from the round-1 kit only** (the
kit as committed at pumllint `1451c05`, before the closing round: its
`refusals.md` rows X-01..X-08 and `cli.md`), and the checker is run on
it; then from the revised kit.

**Layer 3 — `Rule:` blocks** (`kit/features/decisions.feature`): one new
feature whose `Rule:` blocks are the DMN tables' rule groups, each with
one Scenario Outline whose Examples are the table's rows (every row
exercised, boundary points included), running through the same steps and
adapter. A row with no example is a reported gap of the examples against
the model. The existing 11 features are not restructured: the
calibration of 197 cases is not put at risk for a grouping, and the id
tags already carry the rule → example join through `trace`.

**Layer 4 — glossary** (`kit/contracts/glossary.md` + `harness/
glossary_check.py`): terms defined once from the code's own meaning (leg,
series, basis, tail, window, end-guard, stamp, seam frame, raw columns,
cumulative split factor, revision, verdict/alert/warning/note, modeled
source, paused asset, …); the checker lists terms that recur across
requirements without a definition, before and after.

## 4. Amendments to the follow-up as first named

1. **No new recreation in this wave.** The question — would the kit have
   caught its own gaps — is answered by analysis on the round-1 kit, with
   no agent run. A recreation from the layered kit would measure a
   different thing, dilution past the knee (W4), and is recorded as an
   optional third step, not run here.
2. **One expected negative, stated now.** The CLI-surface gap (help
   text, usage lines) is not a decision and not an invariant; none of the
   four layers can see it. The wave measures the refusal-path gap and
   says so of the other.
3. **`Rule:` blocks narrowed** to the new decisions feature (§3); the
   calibrated suite is left as it is.
4. **Exactness rule for invariants**: no tolerance, as above.
5. **Lab-only dependency**: Hypothesis is installed in the lab venvs and
   named in the harness README; it never enters a kit's pins or
   pumllint's own extras.

## 5. Pre-registered expectations

- **W2-E1** Layer 1 intrinsic properties: zero counter-examples on the
  original over the default Hypothesis budget (100 examples per property,
  fixed seed recorded). A counter-example is a finding about the original
  or about the property, triaged and recorded either way.
- **W2-E2** Layer 1 differential properties: zero counter-examples
  against Arm K2; against Arms K and K−UML, counter-examples only in the
  classes already known (the `export`-on-absent path, which K and K−UML
  refuse cleanly; CLI prose is outside the adapter and not reached).
- **W2-E3** Layer 2 on the round-1 kit: the command × store-state table
  shows **exactly one gap**, (`export`, absent series), and zero
  overlaps. Confirmed: a decision model with gap analysis would have
  caught the refusal-path defect before any recreation. Any other gap
  is a further kit finding; zero gaps refutes the layer's claimed value
  on this subject.
- **W2-E4** Layer 2 on the revised kit: zero gaps, zero overlaps across
  all tables, or each remaining gap is a named kit finding.
- **W2-E5** Layer 3: every DMN row is exercised by at least one Examples
  row that passes on the original and on Arm K2; rows the existing 98
  scenarios never exercised are counted — expectation ≥ 3, the measured
  example-coverage gap of round one.
- **W2-E6** Layer 4: ≥ 10 terms used in three or more requirements had
  no definition anywhere in the kit; after the glossary, zero.

## 6. SWOT of the wave

- **Strengths.** Every layer runs on tooling already in the lab or in
  the standard library plus Hypothesis; the adapter interface makes the
  invariants portable across all three rebuilds at no extra cost; the
  round-1 kit is frozen in git, so the "would it have caught" question is
  answerable without reconstruction; the metrics are counts a reader can
  re-run.
- **Weaknesses.** The DMN checker is home-made, not Camunda or Drools:
  it proves gaps in the tables as written, and its FEEL subset is only
  what the tables use. Transcribing contracts into tables is done by the
  same context that ran the comparison, so a transcription error could
  manufacture or hide a gap — mitigated by deriving the round-1 table
  from the committed round-1 files only, with the diff shown. One
  subject, one day.
- **Opportunities.** A kit whose decisions are tables with proven
  completeness is a different kind of specification from one whose
  decisions are prose; if W2-E3 confirms, the decision layer becomes the
  recommended T3 carrier for any future kit, and the differential
  property harness becomes the standing comparison tool, replacing the
  24 hand-written scenario groups.
- **Threats.** Over-specification: four layers on top of 162
  requirements is more text than the knee (W4) suggests a generator
  wants — which is exactly why no recreation runs here. Property
  generators that only reach the fixtures' shapes find nothing and read
  as assurance; the strategies must be reviewed for breadth, and the
  review recorded. Hypothesis under exact equality may flag legitimate
  nondeterminism (wall-clock stamps), which the harness already excludes;
  any new exclusion is a pre-registered-exclusion change and is written
  down.

## 7. Budget and order of work

Build and measure in priority order, 1 → 2 → 3 → 4; stop and report
with partial results if the session's budget runs out. Each layer's
result is appended as it lands. Record: this file's Results, a dated
section in `docs/recreate-experiment.md`, the ROADMAP's research-track
bullet annotated, the two artifact pages refreshed after the merge.

## Results

*(appended as layers land; nothing above this line changes)*
