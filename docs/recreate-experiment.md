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

*2026-10-24, on the maintainer's ask:* the kit compiled into a handover set
for a development squad working without AI assistance and for an AI coding
agent, `recreate_experiment/handover/`: a reading path, the eight diagrams
rendered (PlantUML's built-in layout, no Graphviz), the requirements by kind
with their realising diagram and verifying scenarios, the decision tables
rendered, the traceability report, a definition of done with the commands
that prove it, the quirks to reproduce rather than fix, and the agent brief
the three rebuilds were made from, generalised. The three generated
documents come from `build.py` over the kit (`--check` says when they are
stale); `--zip` packs kit, handover and the four checking tools as one
archive. Nothing in the kit changed.

## A fourth rebuild, from outside (2026-10-24)

*Dated addition. The rebuild and its review:
`recreate_experiment/rebuilds/codex-2026-10-24/` (pumllint
[#183](https://github.com/fdurieux/pumllint/pull/183)); the kit
corrections it caused: `recreate_experiment/kit/CHANGES.md`, revision
2026-10-24.*

The maintainer had the kit and the handover set rebuilt once more by a
different vendor's model (recorded as `gpt-6.1-sol-wm`, effort
unverified), under a protocol it pre-registered itself: inputs limited to
`kit/` and `handover/` at `88f656a`, every input blob hash-pinned, no
access to the original, the hidden tests, the earlier rebuilds or their
results, and a six-dimension 0–5 review of each of the 221 input files
with "null, never zero" for what it could not assess. The data behaviour
passed first time: 246 of 246 non-chain cases on the diagnostic run after
a transport-added newline was removed, and all 11 chain cases once the
author wrote labelled test doubles for the two scripts the kit names as
given externals and did not carry. Twelve assumptions, ten findings
against the kit, all verified here against the kit, the original and the
handover:

- **One major gap the harness had hidden for three rounds.** `events.sh`
  and `dashboard.sh` are "given externals" in `chain.md`, and the chain
  scenarios copy them from beside the script under test; the in-house
  harness copied them from J-F at run time, so no arm noticed the kit did
  not ship them, and the handover said "the suite stubs them", which it
  does not. Now shipped verbatim in `kit/contracts/externals/`, the wording
  corrected, and the suite re-run on the original and on Arm K2 with the
  shipped copies: 258/258 each.
- **Seven bookkeeping errors of wave 2 and the handover:** the README's
  requirement count, two rows numbered X-10, the change log missing wave
  2, the actions-gate DMN's stamp domain with no later-than-today value
  (JDL-091 counts such a stamp as fresh; one Examples row added), the
  transport drawn as an object in the data model and written as a tuple in
  `collectors.md` and JDL-023 (the diagram was right; the prose and the
  requirement's text now say the object), a lost `\u00a7` in the JSON
  escaping example, and DONE.md naming tools outside the two folders the
  protocol allowed.
- **One harness limitation, now removed:** the chain scenarios' call
  logger split a multi-line argument into several records; it escapes
  newlines now, and `chain.md` states the one-line `python3 -c` the
  original uses.
- **One inherent note:** the packaged universe names two CSV snapshots the
  program's own package does not carry either; the README now calls them
  deployment inputs.

Two readings. The review's usefulness scores land where the experiment's
own K−UML arm did: contracts with exact strings and worked arithmetic at
4–5, the decision tables at 3, the diagrams and generated views unscored
as "navigation". And three of the rebuild's assumptions (an empty provider
response, duplicate timestamps handed to a reconcile, numeric knob ranges)
are silences the three earlier rebuilds also met and resolved the same
way; they are recorded as candidates, not added. The rebuild's own code is
about 700 lines of deliberately minified Python with a generated parser:
correct under the suite, not a codebase for a squad, and kept as evidence.
Its eleven extra tests include the `load` happy path through a fake
collector, the row the wave-2 DMN pass named as uncovered.

Two more things its method asked for, added the same day: a written
precedence rule for disagreements between the suite, the requirements,
the contracts, the decision tables and glossary, and the diagrams (the
kit implied the order and never stated it), and `MANIFEST.sha256` with a
stdlib tool to verify a copy byte for byte, the check the rebuild had to
build for itself.

The wave-2 invariants were then run against this rebuild as well
(2026-10-24, a fresh environment on the kit's pins): the six intrinsic
properties pass at 100 examples each, and the differential property
passes, 7/7, with Arm K2 as the reference — the original and this rebuild
are both named `jef` and cannot share a process, so equality to the
original is transitive through K2, which had matched it on the same seven
properties, rather than measured directly.

## The other direction: what the kit does not reach (2026-10-24)

*Dated addition, on the maintainer's ask, after the knowledge-capture
discussion. Register and numbers:
`recreate_experiment/results/coverage/UNREALISED.md`, `coverage.json`.*

`trace` says every requirement is verified; it says nothing about the code
no requirement reaches. Measured: the kit's 258 cases run against the
original under branch coverage execute 1 379 of the data lane's 1 520
statements (89 %), leaving 141 never executed and 49 branches taken one
way only. The 141 fall into four classes. **40** are the program's live
half — HTTP, the rate limiter, retries after a connection error, the
`load` and `sync-actions` happy paths — which replay cannot reach by
construction. **33** are behaviour the kit states and no scenario
exercises (the lock timeout, the leftover-file sweep, the 100-page refusal,
a non-JSON body, the status table's pair lines, the resolution fallback,
two Binance edges, the whole grammar of `classifications.toml`): the
requirement-granular "verified" hid a clause-level gap, as the wave-2
record anticipated. **61** have no caller in the lane: deliberate orphans,
test-only helpers, a cross-lane API, the fixture recorder. **6** are guards
the store's own writes make unreachable; one statement is unspecified as
well as unexercised, the fourth rebuild's assumption A-08.

Two readings. Regeneration validates exercised behaviour: a rebuild that
matches cell for cell has been checked on 89 % of the statements, and the
other 11 % is where a defect or a workaround can sit unseen. And the
clearest instance of knowledge the code states and no derived artefact
carried is in class C: `needs_update`'s docstring, "NOT A GATE. Do not
give this a production caller again", the record of two callers removed
on 2026-08-30 — history a reverse-engineered kit can only reproduce if
the reverse engineer reads orphans, which a behaviour-first reading does
not. For the knowledge-capture approach this register, not the suite, is
the list of questions for the subject matter expert, and its class-C
count is the honest size of the tacit remainder for this lane.

## A case for the approach: a departing expert (2026-10-24)

*Dated addition, on the maintainer's ask. The plan:
`recreate_experiment/knowledge-transfer/DOMINIQUE-CASE.md`. Revised
2026-10-26: the linter routing step written out as a five-step procedure
(lint, attribute, route, resolve, re-lint) with its findings table,
session prompt, measure and role assignments. Revised 2026-10-27: an
enforcement state (system, control, memory) on every rule item of the
register and in Phase 2's triage, each state with its own handling, after
J-F's rule-to-gate register showed the same column answers the question
for a system's rules.*

The knowledge-capture method of the fourth rebuild (EVALUATION-METHOD 1.2
and 1.3) and the experiment's instruments, applied to a person rather than
a system: a professional-loans analyst with twenty years in the bank
leaving in eight weeks, and a question-answering layer over the captured
material proposed as her stand-in. The assessment: necessary, not yet
sufficient, because nothing in the method builds the inventory of what
she knows that nobody else does. The plan builds it from her own work
products first, captures against it in example-driven sessions with the
successor present, measures sufficiency by a graded question set with its
denominator, freezes the corpus as of her last day, and makes the
successor's questions the blind test. The question layer cites, abstains
and logs; it never signs off. Illustrative names and figures; a plan, not
a run.

## A tool read against the record: mneme's Architecture Audit (2026-10-26)

*Dated addition, on the maintainer's ask. A reading of the source, not a
run: the session's permission gate refused installing code from an
external repository, so nothing below is measured on this repository or
on J-F. Source read at `MnemeHQ/mneme` HEAD `1b5dc50` (2026-10-26),
`pyproject.toml` version 0.10.0, MIT, Python 3.11+.*

**What it is.** A CLI that keeps architectural decisions in
`.mneme/project_memory.json`, blocks an agent's edit when the text
contains a forbidden token, and runs an "Architecture Audit" sorting
each decision into four tiers: *Protected*, *Mneme-ready*, *Requires
modelling*, *Guidance*. The README's promise, "see where your
architecture is actually protected — and where it still depends on
people remembering the rules", is the claim read here.

**What "protected" means in the code** (`mneme/enforcer.py`,
`_assess_protection_tier`, the ADR-026 block above it). A decision is
Protected on exactly two kinds of evidence: its own installed rule — one
rule type exists, `FORBID_LITERAL`, a character sequence matched without
normalisation (ADR-019; `FORBID_NUMERIC_ABOVE` is audit-only and
unreleased) — or a GitHub Actions / GitLab workflow file in which a line
mentioning the token is chained to `exit 1` in one of three grep-and-fail
shapes (`_ci_verified_linkage`). A declared pytest selector annotates the
decision and, by their ADR-024, never protects: the audit executes no
repository code and no trusted verifier exists yet. Intent is a word
list: any of *should*, *may*, *can*, *prefer*, *consider*, *generally*
makes the decision Guidance, which no evidence can lift. The package
depends on the `anthropic` SDK; the tiering itself is regex-only, and
where the SDK is used was not checked.

**Desk-check against this programme's own rules**, by mneme's regexes:

| rule | tier | why |
|---|---|---|
| J-F: no `logging` in `src/` | Mneme-ready | "no logging" is a single-term prohibition; path scope exists (ADR-020) |
| J-F: never switch R to OpenBLAS/MKL | Mneme-ready | single token; no workflow line to verify it |
| J-F: never edit `experiments/`; never re-freeze `tests/golden/legacy/` | Requires modelling | a path rule, not a literal |
| J-F: strict projection AST-identical to the frozen source | Requires modelling or Guidance | gated by `tests/test_consolidation.py`, which the audit cannot count |
| pumllint: all output through `_out`/`_err`, never a bare `print()` | Mneme-ready via "no print", then false positives | the literal occurs legitimately in tests and docs |
| pumllint: forward-slash paths, `as_posix()` never `str(path)` | Requires modelling | two terms |
| both: exit codes 0/1/2 are a contract | Guidance | no obligation word, no literal |

The audit would report almost nothing in J-F as protected while the AST
proofs, `tests/test_traps.py`, `test-tier-ranges.R`, the paste-block
checker and the diagram gates all exist. It scores the enforcement
shapes it knows, not enforcement — T-0800 in a new coat, a tick that
measures the tool against itself.

**Verdict.** The question is sound and this programme has not answered
it in one place: for each rule in a CLAUDE.md, which gate enforces it,
by symbol, and which rely on memory. The tool does not answer it for
these repositories, whose gates are tests, not grep-and-exit workflow
steps. The transferable shape is a rule-to-gate table, hand-built once
and then kept honest by a test that every rule names a gate or is marked
*memory only* — J-F's `docs/VERIFICATION.md` covers the contract items,
not the sixty-odd iron and working rules. A J-F candidate, outside both
of these repositories; not queued here. For pumllint the parallel is
`trace`'s verification column: requirement → scenario → verified is the
same three-tier reading, applied to models instead of decisions, and it
already counts what the audit cannot — a test.

**Bounds.** Not run. The desk-check applies the published regexes to
seven rules by hand; a live `mneme audit` on a J-F checkout would settle
the tiers it actually assigns, and the one-term "no print" false-positive
rate is a guess until a check is run on the docs tree.

## OpenWiki against the kit: pre-registered, awaiting the artefact (2026-10-27)

*Dated addition, on the maintainer's ask. Pre-registration:
`recreate_experiment/openwiki-2026-10-27/PREREGISTRATION.md`; tools beside it.
Nothing measured yet.*

LangChain's OpenWiki (0.7.2; a Node CLI built on Deep Agents that writes a
Markdown wiki with "Grounded Claims", each claim pinned to `repo://` line
evidence with content hashes) is to be run over the **same clean-room
tree** the kit's reverse engineer saw (J-F `8f6d6b0`, `src/jef/data/`,
`deploy/daily.sh`, the two externals marked, a reduced `pyproject.toml`;
23 files, subject sha256 `535982e6…`), and its wiki compared with the kit
on three questions: accuracy (M1, a seeded sample of its claims verified
against the code), coverage (M2, the 163 requirements mapped onto the wiki,
by kind; M3 the inverse), and sufficiency (M7, a fresh Opus 5 @ xhigh agent
rebuilding the lane from the wiki alone, graded by the hidden suite and the
harness cell for cell, as the kit arms were). Also measured: the six filed
defects and the twelve quirks (M4, M5), what each arm's machine checks
prove (M6; the expectation that the evidence hash proves staleness, never
truth, is T-0800 in the wiki's terms), cost (M8) and, if the owner runs
the update, drift detection on the two Phase 1 mutants (M9).
Expectations are frozen in §4: precision high (≥ 0.85 strict), coverage
low (< 0.40 strict, lowest on refusals and arithmetic), at most one defect
flagged, at most four quirks stated, the rebuild under 70 % of the 258
cases. The model confound is stated up front: OpenWiki's effort knob exists
only for OpenAI's gpt-5.6 family, so Arm W is the tool as shipped and the
kit's Opus 5 @ xhigh is not matched; every difference is pipeline × model.

**Blocked on one thing:** a model credential. The session can install and
run the CLI (checked: `openwiki --help` at 0.7.2 on Node 22.22.0) but the
environment carries no provider key, so the generation is the owner's,
either as a key in the environment's secrets for a later session or as a
local run with the paste block given in chat; the wiki lands under
`results/W/` unread, and the rebuild starts before the grader reads it.
The tools were dry-run on OpenWiki's own wiki (748 claims, 22 pages) to
prove the sidecar parser; nothing from that is a result.

## OpenWiki against the kit: the results (2026-10-28)

*Dated addition. The pre-registration's Results section
(`recreate_experiment/openwiki-2026-10-27/PREREGISTRATION.md`) is the
record; this is the reading. Steps 3 and 4 and measures M1 and M2 were run
and graded by a sibling session the same day; M3 to M8 and the verdict by
this one.*

**What ran.** OpenWiki 0.7.2 over the clean room with OpenAI's
`gpt-5.6-terra` at `xhigh`, one owner-approved one-line patch to make its
provider stream past the session proxy's 30-second cut: 9 content pages,
128 Grounded Claims, 24 minutes. The Anthropic arm did not run (no key).
Two fresh Opus agents then rebuilt the lane from the wiki alone, one in a
venv missing two pins by a setup error, one with them, both before anyone
read the wiki; both are graded.

**What the wiki is.** Accurate and unpinned. 127 of 128 claims TRUE, one
PARTIAL, none FALSE (precision 0.992 strict, 1.000 lenient; the claims are
compound, 3.3 parts each, 426 of 427 parts hold). Against the kit's 163
requirements it states 40 fully, 111 partially and 12 not at all: 0.245
strict, 0.926 lenient. The partials are a missing message, default, edge
or order, 58 of them an exact string. Refusals are the lowest kind, as
predicted; arithmetic the highest, against the prediction: the factor
rule, the calendar, the crypto guard and the pagination are written out
exactly. Of the five applicable filed defects it states one as design
(#307) and repeats the docstring's wrong unit on another (#304); of the
twelve quirks it states three, none flagged, one contradicted. Eighteen
TRUE claims state what no kit document does, nine of them structure.

**What a rebuild from it is.** Two rebuilds, 34 and 31 of the kit's 258
cases. And: every export seam frame identical to the original cell for
cell (14 of 14, both arms; the exported frame routes bit-identically
through the original loader over 10 400 rows); every stored frame
identical after one unit conversion and a column reorder, because both
rebuilds wrote `timestamp` in milliseconds, exactly the wiki's one
contradicted claim; every status verdict, total and gate exit identical
on all 17 status artefacts; every revision record identical; the chain's
exits identical in all 8 cases. The 227 suite failures are message bytes
(41), usage and `--help` text (29), the adapter returning an object where
the interface describes a mapping (42, every sync scenario through the
adapter), JSON shapes (12), the chain's skipped ECS lookup (8), paths and
echo lines (13), column order (4), and sixteen refusals that exit 2 where
the original exits 1. Not one failure is a wrong number, date, verdict or
revision. The suite measures conformance to the specification's bytes;
the differential measures outcomes; both are true of the same build.

**One inversion.** The wiki rebuilds pass 26 of the original's own
API-level tests through the shim; the kit rebuilds passed 18, 0 and 5.
The wiki names the modules, classes and seams, so the rebuilt package is
laid out like the original and the original's unit tests import; the kit
says what the program does and leaves the layout to the builder. Black
box, all arms are 10 of 10.

**Against the expectations.** H1, H3, H4 and H6 held. H2 held on the
strict bound and failed on the lenient one. H5 held on the suite and
failed on the cells: the pre-registration guessed that prose and claims
would lose arithmetic order, message bytes and exit codes; they lost
message bytes and one exit-code convention and kept the arithmetic. H7
was not run.

**What it means for the programme.** The two artefacts answer different
questions. The wiki tells a maintainer where things are and what the
code says about itself, with a staleness check on every claim and
nothing that can tell a true claim from a docstring's error. The kit
pins what a consumer depends on, the bytes, defaults and exit codes, and
ships the suite that proves them, at three to four times the cost of the
first round and with no layout. On this subject, the arithmetic survived
either route; what the kit bought was the message layer and the proof,
and what the wiki bought was the map. A rebuild from the wiki is a
working program with the original's data and a stranger's messages.

**Bounds.** One model behind the wiki, another behind the rebuilds, a
third behind the kit; one run of each; a grader who wrote the kit's
suite; a 30-second proxy that forced the streaming patch. The two
contradicted statements in the wiki carry current evidence hashes, which
is H6 in one line. Independent re-grades of 20 claims and 20 requirements
are offered in the Results section.
## An external causal model tested against the record (2026-10-28)

*Dated addition, on the maintainer's ask. Record:
`recreate_experiment/legible-model-review-2026-10-28/REVIEW.md`.*

*Legible: systemic impact model* v0.2 is a qualitative causal model of
how the tools and practices on <https://fdurieux.github.io/> affect
software quality and DORA metrics. It has four layers (artefact quality,
product quality, quality in use, delivery performance), an explicit
defect cascade, 70 signed edges and 8 feedback loops. Its pumllint
evidence pin (`9d728c8`) predates this experiment's entry in
`EVIDENCE.md`, so the experiment is out-of-sample evidence for it. It
reaches the artefact → product leg only: nothing here deploys, so
quality in use and every DORA path stay hypotheses.

The model's hedges held:
- propagation was conditional;
- downstream faults arose independently;
- matching specifications and tests proved nothing without an
  independent oracle.

Its shared-premise concealment claim (C06) has a measured instance:
- The closing round, derived from the code, wrote the original's raw
  traceback on `export` of an absent series into the spec as JDL-159.
- K2 reproduced the crash, the suite stands at 257/257, and the
  harness scored it as a divergence closed.
- J-F #305 calls the same behaviour a defect.
- K and K−UML, given a silent spec, had refused cleanly.

Three gaps, each tied to a measurement:
- **The cascade flows one way.** The store's `timestamp` holds seconds
  under the pinned pandas 3.0.5 (`datetime64[us]`, divided by
  `10**6`). The comment, docstring, J-F's data contract and OpenWiki's
  wiki say milliseconds; the kit, from the logic, says seconds. One
  dependency-made defect reached two derived artefacts in opposite
  directions.
- **Attenuation by load-bearing role is not representable.** Twelve
  diagram defects reached no rebuild's behaviour, because contracts and
  scenarios carried it (the E5 ablation, read from the other side).
- **"Green but wrong" starts only from repair.** The measured case was
  a green gate over drift: J-F #309's 25 claims under Level 5 100/100.

The record proposes the interventional follow-up — plant known defects
in the kit by layer, rebuild, grade against the frozen reference — and
does not pre-register it.

## Degrading the kit: pre-registered, awaiting the plant (2026-10-28)

*Dated addition, on the maintainer's go ("all six arms, rebuilds at
xhigh"). Pre-registration:
`recreate_experiment/degradation-2026-10-28/PREREGISTRATION.md`. Nothing
planted or measured yet.*

The intervention the Legible review asked for. Six fresh agents rebuild
the program, each from a different copy of the kit:

| arm | what is wrong in its kit |
|---|---|
| C | nothing; the kit as committed, today's baseline |
| D1 | three defects in the diagrams only |
| D2 | three in the requirements, contracts and decision tables, with the suite intact |
| D3 | three wrong values planted consistently in every layer |
| D4 | three in the suite only |
| D5 | three omissions in every layer |

The defect types are a wrong value, a missing rule and an ambiguous
wording; D3 and D5 specialise. Sites are not chosen by hand:

- **The walk.** A sha256 order over the requirement ids decides which
  behaviour each slot degrades. Admission requires that both the
  harness and the kit's suite observe the behaviour, and that the
  observing artefacts are ones the K2 rebuild reproduced byte for byte.
- **The mutant.** Each defect is paired with a mutant of the original,
  so propagation is read by byte equality: ORIGINAL, PLANTED or OTHER.

Before any rebuild, every degraded kit is run through the gates: lint,
score, trace, the DMN check, the glossary check, and calibration of its
suite on the original. For the rebuild window, the subject and the lab
leave the container.

Expectations are frozen per arm under the model as drawn and as
corrected. The two readings part most sharply on D1, where defects
propagate as drawn and are attenuated by role as corrected, and on D4:
as drawn there is no edge from a wrong test to the code, while as
corrected the suite pulls the code with it.

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
