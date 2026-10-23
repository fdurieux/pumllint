# The recreation experiment — code → spec kit → code, graded by the original

*Dated experiment record, 2026-10-23. Pre-registration frozen before any
kit, recreation or comparison run (`recreate_experiment/PREREGISTRATION.md`
at `5c1fa55`; results appended below its frozen text as the phases
completed). Subject: J-F's daily asset load — `src/jef/data/` (≈ 3 500
lines, eleven modules, two packaged TOML files) and the acquisition half
of `deploy/daily.sh` — read at `8f6d6b0` as an oracle and never changed.
Lab machinery, kit, recreations and results: `recreate_experiment/`.
Nothing here ships; nothing enters J-F.*

## The question, and the answer in one paragraph

Can a specification stack reverse-engineered from working code —
requirements as code, contracts, UML, Gherkin — carry enough for an
independent agent to recreate the code, and where exactly does it fall
short? **On this program: yes, to the cell.** A fresh agent given only
the code tree (no documentation, no tests) produced a kit of 158
EARS-form requirements with stable ids, 14 contracts and two JSON
Schemas, 8 PlantUML diagrams at Level 5 under the codegen profile, and
95 Gherkin scenarios that pass 178/178 on the original and catch two
planted mutants. Two further fresh agents, one with the diagrams and one
without, rebuilt the program from that kit alone. Against 157 reference
artefacts frozen from the original over its recorded provider fixtures,
**every exported seam frame, every stored series, every health verdict,
every sync summary and every exit code was identical** in both arms, with
zero gate inversions; the seam frame routes bit-identically through the
original's loader. What diverged was the command-line *surface* nobody
specified — help text, the usage line of a parser error — and one
refusal path the kit was silent on, where both rebuilds refused cleanly
and the original crashes. **Zero code defects; two spec-defect classes;
and the diagrams changed nothing measurable in behaviour** — they fixed
the module layout and API shape, which is exactly what the original's
own API-level tests then measured. One revision of the kit, derived
again from the code alone, closed every divergence the kit could be held
responsible for: the third rebuild passed the kit's 197 scenarios on its
first run and left 11 of 157 artefacts non-identical, all by
construction. Set beside J-F's existing Level 5 model set for the same
lane, adjudicated against the source, the one-day code-only diagrams
won 20 of 33 disagreements and carry 12 claims the code contradicts;
the maintained set carries 25.

## Why this ran

Every wave of the research program so far (the C4 ladder, W1–W5) ran
the model→code hop forward on toy systems, graded by a hidden suite. This
ran it round trip on a real, operated program with a perfect oracle: the
original. A divergence can therefore be attributed — the kit failed to
carry a fact (spec defect), the kit carried it and the generator missed
it (code defect), a scenario asserts the wrong thing (test defect), or
the original is wrong. The maintainer named the subject and set the
conditions: the kit derived from the code alone (no existing J-F diagram
or document used — the subject already carries a Level 5 model set for
this lane, and J-F's trap T-0800 says a green gate "scores the set
against itself, never against the code"), the original's tests hidden
from the reverse engineer, two recreation arms, a closing round
authorised in advance.

The design adopts the 2026-10-20 note *AI-Assisted Testing in
Spec-Driven Development* verbatim: the spec is the test oracle; atomic
requirements with ids; code and tests from separate contexts;
assumptions listed, never silently resolved; deterministic oracles;
generated artefacts with provenance.

## Design

Four phases, four contexts. **Phase 0 (this session)**: freeze the
pre-registration; build the reverse engineer's clean room — a copy of
the code tree with `docs/`, `tests/`, every README and the ROADMAP
absent, installable on its own; build the comparison harness and freeze
the original's outputs. **Phase 1 (fresh Opus 5 @ xhigh agent)**: derive
the kit from that tree; write a hidden provenance map; calibrate the
scenarios to 100 % on the original; plant two mutants and show the
suite catches them; pass three pumllint gates. **Phase 2 (two fresh
Opus 5 @ xhigh agents)**: rebuild from a copy of the kit, placed outside
every repository, with no repository or package name in the brief;
Arm K with the diagrams, Arm K−UML without; at most three runs of the
kit's own suite; an assumptions file and a read log as measured
outputs. **Phase 3 (this session)**: score both arms through a fixed
adapter interface against the frozen reference; triage every
divergence with the provenance map. The orchestrating session never
wrote kit content: it had read parts of J-F's data contract while
planning, which is why the reverse engineering went to a fresh agent.

**Oracles.** 24 scenario groups, 157 artefacts: first fill of every leg
over the nine recorded fixtures (two equities with real split and
dividend histories, a crypto composite, Binance klines), tail refresh
with revised cells inside and outside the window, a real 4:1 split
through the adjustment pass, the crypto end-guard, a universe `end` cap
and an inverted window, a paused asset, stale and fresh actions, the
cross-venue spread at and over its threshold, a phantom-split jump, a
zero-volume run, the Yahoo CSV import and export (10 400 rows), dry
runs, 22 refusal cases, 24 CLI surface cases, 8 chain cases with every
external command stubbed as the original's own tests stub them. Plus
the original's own in-scope tests replayed against each rebuild through
an import shim (M9, reported not gated) and the seam-invariance proof
through the original's loader (M8). Wall-clock values were normalised
(ISO stamps, the chain's run stamp and stage epochs, the actions
`last_updated` field, paths); two reference runs compare identical.

## The kit (Phase 1)

| Artefact | Count |
|---|---|
| Requirements (`requirements.json`, ids `JDL-001`–`JDL-158`) | 158: contract 48, ritual 27, arithmetic 22, refusal 19, cli 17, chain 13, verdict 12; basis both 112, logic 45, prose 1 |
| Contracts | 14 documents + 2 JSON Schemas with validating examples + the two shipped TOML files + the harness interface |
| Diagrams | 8: component, class, four sequence, one activity, one state |
| Scenarios | 95 in 11 features (178 cases), 148 synthetic fixtures |

Gates, re-run by this session with pumllint 0.34.0: lint clean at
`--fail-on info`; Level 5 (Method-complete) 100/100 on all eight;
`trace` 158/158 realised and 158/158 verified, with `--features` joining
the scenario tags — the requirements-as-code gate. The syntax gate did
not run (no renderer here). Calibration: 178/178 on the original;
mutant m1 (bar fetch moved before the actions refresh, store-invisible
by construction) fails 2 scenarios; mutant m2 (crypto end-guard removed)
fails 11. The subject tree was byte-identical to J-F after the run; the
read log stayed inside the clean room; no line of 50+ characters is
shared between the subject's source and any kit file.

The reverse engineer's hidden notes record where the source's comments
and its logic disagree — the kit states the logic: the store's
`timestamp` column holds Unix seconds under the pinned pandas while its
schema comment says milliseconds; `ingest_yahoo_csv` reports a row count
that includes the duplicate dates it then drops; the health module
documents an `actions_missed_k` knob the CLI never exposes; the injected
clock drives the actions gate's comparison but the stamp it reads is
always the real clock. These are observations about the original,
handed to J-F as findings (§ What goes back), not changes.

## Results (Phases 2–3)

Both recreators stopped after their second suite run at 178/178 (first
runs 175/178, the same chain scenario in both: multi-line inline python
broke the recording stub). Arm K laid out 13 modules as the component
diagram names them; Arm K−UML chose one module per contract, 12
modules. Assumptions: 65 and 50 entries.

| Metric | K | K−UML |
|---|---|---|
| M1 exported seam frames identical | 14/14 | 14/14 |
| M2 / M3 gate inversions | 0 / 0 | 0 / 0 |
| M4 status documents identical | 17/17 | 17/17 |
| M5 sync summaries identical | 14/14 | 14/14 |
| M6 stored series / actions files identical | 13/13, 2/3 | 13/13, 2/3 |
| M7 CLI exit codes / CLI text identical | 52/52, 38/52 | 52/52, 38/52 |
| M7 chain exit codes / call logs identical | 8/8, 1/8 | 8/8, 1/8 |
| M8 seam invariance through the original loader | PASS | PASS |
| M9 original tests, API-level: modules importing, cases passing | 5/14, 18/50 | 1/14, 0/5 |
| M9 original tests, chain (black-box) | 10/10 | 10/10 |
| Artefacts not byte-identical | 22/157 | 22/157 |

The 22 are the same set in both arms:

| Artefacts | Class | Finding |
|---|---|---|
| 9 `--help` outputs, 2 parser-error usage lines | **spec defect (cli)** | the kit carried flags, defaults and messages, not the argparse surface |
| `export` of an absent series | **spec defect (refusal)**, and an original observation | kit silent; the original exits 1 with a raw pandas `AttributeError`; both rebuilds refuse with a clean `StoreError`, and both listed the gap as an assumption |
| 2 unwrapped tracebacks | not a defect | same exception class and message; paths and the module prefix differ by construction |
| 7 chain call logs | not a defect | identical commands, arguments and exit codes; the inline metadata parser is spelled differently |
| 1 actions file | harness defect | the interface's "stored fields" read two ways; dates and ratios identical |

Code defects: 0. Spec-defect classes: 2 (12 artefacts). M9's API-level
failures are signature-level by construction — keyword names, return
shapes, module names the kit left free — and are reported as
pre-registered, not triaged.

**Expectations.** E1 confirmed (M1 100 %, both arms). E2 confirmed
(M2 = 0). E4 confirmed trivially — two spec-defect classes against zero
code defects — with the honest caveat that on 157 artefacts the kit left
almost nothing to diverge on. E5 confirmed: K−UML equals K on every
pre-registered metric; the diagrams' measurable contribution is the
module layout and API shape (M9: 5 against 1 original test modules
importing), not behaviour. E6 at the bar: of the two spec-defect
classes, one was flagged as an assumption in both arms, M11 = 0.5. E7
confirmed. E3 pending (§ Post-hoc).

## Closing round

The reverse-engineering agent, resumed in its own context and still
reading only the code tree, folded the two spec-defect classes in as
dated additions: JDL-159 (the absent-series export ends in pandas'
unwrapped `AttributeError`, stated as the logic it is), JDL-160 (the
exact argparse declaration), JDL-161 (the exact parse-error form),
JDL-162 (`--help` verbatim, in a new `contracts/cli_help.md`). First
158 requirements byte-identical; scenarios 95 → 98 (197 cases);
197/197 on the original; gates green at 162/162 — all re-verified here.

A third fresh agent rebuilt from the revised kit: **197/197 on its
first and only suite run**, 30 assumptions. Against the reference,
M1–M6 and M8 unchanged at 100 %, CLI text 38/52 → **49/52**,
non-identical artefacts **22 → 11**: three tracebacks whose paths and
module prefix differ, seven chain call logs whose inline metadata
parser is spelled differently, one key spelling in the adapter. Spec
defects found per iteration: 2 → 0. The round removed every divergence
the kit could be held responsible for.

## Post-hoc: the kit's diagrams beside J-F's existing eight

Taken last. A fresh agent read both sets against the source and
adjudicated 33 disagreements (`recreate_experiment/results/review/`;
four verdicts spot-checked here, one overturned by running the code —
the stored `timestamp` is seconds, as the kit says and the source's
comment denies). Kit right 20, existing right 7, both right at
different altitude 3, both wrong 2, undecidable 1. **Claims the source
contradicts: 12 in the kit, 25 in the existing Level 5, 100/100, fully
traced set** — `select_legs` drawn on `Universe`, `base_path` for an
attribute named `root`, two invented dependencies, a failed sync and a
failed restore drawn as carrying on, re-adjustment triggered by a
subcommand that never re-adjusts, among them. Blind spots are
symmetric (15 and 16): only the existing set draws the store's write
path, the two-write actions refresh and the dashboard publish; only
the kit draws the CLI error paths, collector lifecycle, series basis
states and the status output.

Two readings. First, T-0800 measured: a green `diagrams-structure` job
sat on 25 contradicted claims, and a one-day code-only set beat it. The
gate scores the set against itself. Second, and more important for this
experiment: the kit's own 12 diagram defects were invisible to every
metric, because three rebuilds built from those diagrams matched the
original cell for cell. The contracts and scenarios carried the
behaviour; the diagrams carried names and layout. A diagram defect no
rebuild reproduces is a documentation defect, not a specification one —
the same fact E5 measured from the other side.

## What this does and does not show

- **Shown.** On a 3 500-line data layer with numeric, silent failure
  modes, a code-only reverse-engineered kit carried every behaviour the
  harness could observe: a different model, a different context, no
  access to the original, cell-identical output. The requirements-as-
  code gate (`pumllint trace` over diagrams and scenario tags) and the
  mutant calibration were cheap and decisive: the kit's own suite caught
  both planted defects before any recreation ran.
- **Shown, and uncomfortable for diagrams.** Removing the eight Level 5
  diagrams changed no behaviour. The W1 result — the written decision
  contract is the load-bearing artefact — holds on a real program: the
  arithmetic, the message strings and the scenarios did the carrying;
  the diagrams fixed names and layout.
- **Not shown.** Live-provider behaviour (provisional closes,
  pagination at scale, rate limits, timeouts), the lock timeout and the
  hand-run `load`/`sync-actions` paths are outside what fixtures and
  stubs reach; the kit declares them. One program, one domain, n = 1
  per arm: single runs, quoted as such. The reverse engineer and the
  comparison analyst were different contexts, but the comparison
  analyst and the pre-registration author were the same one.
- **For the pumlspec pilot, on hold.** The maintainer's pilot of
  PlantUML models as contract-grade specs for codegen, with
  manifest/lockfile provenance (the plan docs/sdd-manifest-evaluation.md
  evaluated on 2026-08-10), is on hold as of 2026-10-23. This experiment
  leaves one reading against its thesis for when it resumes: the models
  were not the contract-grade layer here; decision tables, message
  strings and boundary examples were. Nothing is queued from it.
- **The denominator problem.** Two spec-defect classes out of 158
  requirements says less about reverse-engineered specs in general than
  about this subject: a program whose comments already carry its
  decisions, written under a discipline that pins messages and
  arithmetic. The experiment should be repeated on a program with fewer
  comments before the "to the cell" claim travels.

## Re-evaluation against the maintainer's requirements-as-code stack (2026-10-23)

*Dated addition, on the maintainer's ask, after the experiment closed.
The maintainer's own list of requirements-as-code layers — EARS or
SBVR/RuleSpeak for statements and vocabulary, DMN decision tables with
hit policies and gap/overlap analysis for decisions, Gherkin `Rule:`
blocks with boundary outlines as acceptance examples, OpenAPI/JSON
Schema contracts, property-based invariants, TLA+/Alloy for state,
policy-as-code and rules-as-code where they apply, traceability by id
in git — was not available to this experiment while it ran; the kit was
derived from the code alone and the overlap below is convergence, not
use.*

**Where the kit stands against that list.**

| Layer | In the kit | How |
|---|---|---|
| EARS statements | yes | 130 of 162 requirements open with When / If / While / The … shall |
| Gherkin acceptance examples, boundary outlines | yes | 98 scenarios, 25 outlines with Examples at and past each threshold; glue drives the CLI and an adapter, never a UI |
| `Rule:` blocks | no | features group by theme; rules live only in `requirements.json` |
| Decision tables | informally | markdown pipe tables in eleven contracts; no hit policy, no gap or overlap analysis |
| Vocabulary (SBVR, RuleSpeak, a glossary) | no | terms inherited from the code, none defined |
| Contracts (JSON Schema) | yes | two schemas with validating examples; no API, so no OpenAPI |
| Invariants, property-based tests | no | arithmetic example-tested cell for cell, never property-tested |
| Traceability by id | yes | `requirements.json` as inventory, `pumllint trace --features` with fail-on gates |
| Spec-driven codegen | yes | three rebuilds from the kit alone |
| Manifest / lockfile | informally | kit hash, pins, model ids, briefs, read logs in the pre-registration; no format |
| Catala, OPA/Cedar, TLA+/Alloy | no | not applicable to this subject |

**Pros.** The core claim held under the hardest oracle available: three
rebuilds matched the original cell for cell, with no judge's charity
possible. Two of the listed layers did the carrying and were proven to
— EARS with stable ids plus boundary outlines sufficed for behaviour,
and the ablation isolated the diagrams' contribution as names and
layout. Traceability by id worked on shipped tooling and needed nothing
built. Two cheap guards paid: the planted mutants and the 100 %
calibration caught a kit that would otherwise have been trusted on its
gates, and the post-hoc read turned a standing trap into a number.
Independence was real: four contexts, two clean rooms, read logs, a
hidden provenance map, one disclosed breach.

**Cons.** Three listed layers were absent — vocabulary, a decision model
with gap analysis, `Rule:` structure — and the decisions lived in
markdown tables and prose, the informal form that drifts. Completeness
was never checked: examples sample a rule, nothing asked whether the
rule space was covered, and the two gaps that cost a closing round were
completeness gaps found by comparison with the original, not by the
kit. No invariants: a property layer over the adjustment pass was cheap
and untried. The subject was generous — comments already pinned every
decision, messages were exact strings — so "to the cell" says less
about reverse-engineered specs in general than about this codebase.
Single runs, one model. Harness debt showed in one interface ambiguity
and two post-hoc metrics, labelled after the fact.

**SWOT.**

- *Strengths.* A pre-registered, oracle-graded, clean-room design
  repeatable on any program with recorded fixtures; a reusable harness;
  a kit format already satisfying four of the ten layers; a measured
  ordering of artefact value — contracts and examples first, diagrams
  for structure.
- *Weaknesses.* An informal decision layer that cannot see its own
  gaps; no vocabulary; n = 1 per arm; the comparison analyst and the
  pre-registration author were the same context.
- *Opportunities.* One more wave on the same kit: decision tables as
  DMN with hit policies and gap analysis, outlines regrouped under
  `Rule:` blocks, a glossary file, a Hypothesis layer over the
  arithmetic — then measure whether the two completeness gaps would
  have been caught by the kit itself before any recreation. A second
  subject with sparse comments to test the generosity caveat. Both run
  on tooling that exists today and need no manifest format, so the
  pumlspec hold does not block them.
- *Threats.* Over-reading the result as "diagrams are worthless" (they
  fixed the module layout, which the original's API-level tests
  measured). Over-specification: W4 measured dilution past the knee,
  and a kit adding DMN, a glossary and properties on top of 162
  requirements may cross it. And the standing one: a green gate reads
  as truth — 25 contradicted claims sat under a Level 5 badge in a
  maintained set.

**Net.** The experiment answers the question as asked and misses the
half of the list that would have made the kit self-checking. The
follow-up wave is well-defined and cheap; nothing is queued from this
section, which records an evaluation and not a decision.

## Follow-up wave: the four missing layers, built and measured (2026-10-23)

*Dated addition. Pre-registration and results:
`recreate_experiment/WAVE2_PREREGISTRATION.md`; the pages quote it.*

The re-evaluation above named the half of the maintainer's list the kit
lacked. The wave built it, in the priority order the pre-registration
fixed and as additive kit revisions dated "wave 2", from the kit and the
code alone. No new recreation (amendment 1); the one expected negative
(the CLI-surface class, invisible to every layer) stated in advance.

- **Invariants** (`harness/invariants/`, Hypothesis through the adapter,
  no float tolerance): seven properties, 100 examples each; zero
  counter-examples on the original and, differentially, on all three
  rebuilds — K and K−UML included, since the properties export filled
  series only and never reach the one path those two got wrong.
- **DMN with gap analysis** (`kit/contracts/dmn/`, 13 tables, 63 rules;
  `harness/dmn_check.py`): the would-it-have-caught-it question answered
  on the round-1 kit — **0 gaps, 0 overlaps, 1 untyped output**. The
  round-1 kit had the (`export`, absent) row; it lacked the outcome. So
  completeness alone would have passed it; output typing catches it. The
  revised table then forced two cells neither kit revision had written
  (`differential` on an absent A or B side), measured on the original
  (the same traceback) and folded in as JDL-163 / X-10. Revised kit: 0 /
  0 / 0.
- **Gherkin `Rule:` blocks** (`kit/features/decisions.feature`, one Rule
  per table, 60 cases keyed to DMN rule ids): 257/257 on the original and
  on Arm K2 with the existing 197; 60 of 63 rows exercised, the three
  without an example named with their reason — one unreachable by
  construction, two because `load`'s happy path needs the live
  transport, which the kit's seams cannot replay: the kit's executable
  spec never covered `load`'s ingestion, a coverage finding the DMN
  layer surfaced. The pre-registered "≥ 3 rows the existing scenarios
  never exercised" measured 2 at requirement granularity (a lower bound).
- **Glossary** (`kit/contracts/glossary.md`, 63 terms;
  `harness/glossary_check.py`): 46 of a 60-term vocabulary recur in three
  or more requirements; 42 had no definition anywhere in the kit; 0
  after. The contracts described, they did not define.

One harness defect found by running the kit on the original with the
reference adapter: `actions_state` returned dataclass field names and a
re-serialised stamp, not the stored fields the interface promises; three
existing actions scenarios fail with the adapter as committed and pass
with the fix (no scenario changed). Kit gates after the wave: lint clean,
Level 5 on all 8 diagrams, trace 163/163 across 12 feature files.

**Reading.** Of the four, the decision layer paid for itself twice: it
answered the pre-registered question with a sharper verdict than the
one expected (the defect was an untyped outcome, not a gap — a
distinction the pre-registration did not draw), and it found a refusal
nobody had looked for. The invariants found nothing, which on a kit
already matched cell for cell is the expected shape of a passing
property suite, not evidence against the layer. The `Rule:` blocks and
the glossary are hygiene with a count attached. Nothing here is a J-F
finding beyond the two already filed; nothing is queued.

## What goes back to J-F

Findings, never changes: `jef-data export` on an absent series exits
with a raw traceback; `timestamp` holds seconds where the comment says
milliseconds; the import row count includes dropped duplicates;
`actions_missed_k` is documented but not exposed; the injected clock
does not reach the actions stamp. And 25 claims in `docs/diagrams/`'s
data-load and chain set that the source contradicts, each cited in
`recreate_experiment/results/review/REVIEW.md` (one of the reviewer's
own rows overturned here, so the list is a reading to re-verify in
J-F's own ritual — `tools/diagram_sources.py read`, per T-0800 — not a
patch). Filed on the maintainer's go, 2026-10-23: J-F issues
[#304](https://github.com/akantai/J-F/issues/304) (`timestamp` seconds vs
milliseconds), [#305](https://github.com/akantai/J-F/issues/305) (`export`
on an absent series), [#306](https://github.com/akantai/J-F/issues/306)
(the import row count), [#307](https://github.com/akantai/J-F/issues/307)
(`actions_missed_k`), [#308](https://github.com/akantai/J-F/issues/308)
(the injected clock and the actions stamp) and
[#309](https://github.com/akantai/J-F/issues/309) (the 25 diagram
claims, cited to symbols).
