# Recreation experiment — reverse-engineer, specify, recreate, compare

*FROZEN 2026-10-23, before any kit, recreation or comparison run. Every
decision in §10 is taken (below). Editing anything above § Results after
this point invalidates the wave; re-freeze consciously and say so.*

**Decisions taken by the maintainer, 2026-10-23:** target `src/jef/data/`
plus the acquisition half of `deploy/daily.sh`; the lab lives in
`pumllint/recreate_experiment/` and J-F is never changed; the kit is
derived from the code alone, no existing J-F diagram or document is an
input, and the existing model set is met only in the post-hoc
comparison; `tests/` stays hidden from the reverse engineer; two
recreation runs (Arm K and Arm K−UML); the closing round is authorised
in advance under the ceiling.

*Plan, 2026-10-23 (revised twice the same day: the target is J-F's daily
asset load, named by the maintainer after the first draft proposed
aris2puml; then, on the maintainer's instruction, the kit is derived from
the code alone — no existing diagram or document of J-F is read for it,
and Arm E is dropped).
Frozen as `PREREGISTRATION.md`. House protocol applies (`stack_experiment/PREREGISTRATION_TEMPLATE.md`,
research-charter.md §7): oracles, expectations and the interpretation
matrix are fixed before the first scored run; failures are recorded with
the same prominence as confirmations. This directory is lab territory:
nothing in it ships, and nothing in it enters J-F.*

## 1. Question and decision link

**Can a specification stack reverse-engineered from working code —
requirements as code, architecture and UML, contracts, Gherkin — carry
enough information for an independent agent to recreate the code, and
where exactly does it fall short?**

Every wave so far (C4 ladder, W1–W5) ran the hop *forward*: an authored
spec → generated code, graded by a hidden suite. This runs it *round
trip*: code → spec → code, graded by the original. The original is a
perfect oracle, so for the first time a divergence can be attributed: a
fact the artefacts failed to carry (spec defect), a fact they carried
and the generator missed (code defect), a scenario asserting the wrong
thing (test defect), or a defect in the original. The count and class
of the spec defects is the result: which information classes a
reverse-engineered spec loses — the mirror of the charter's "which
artefacts, which level of detail".

Two things make this target sharper than a toy. **The kit is derived
from the code alone, on the maintainer's instruction** (2026-10-23): the
reverse engineer reads `src/jef/data/`, `deploy/daily.sh`, the two
packaged TOML files and the pins in `pyproject.toml` — never `docs/`,
`docs/diagrams/`, the README or the ROADMAP, and (recommended, §10
decision 1) never `tests/`. J-F's existing eight data-load diagrams and
its data contract are not inputs to anything here; they are compared with
the kit only after the recreation is scored (§6, the side result). And
**the subject's failure class is silent and numeric**: a wrong cell in
the frame the binning consumes, or a health gate that says green on a red
day, feeds the model wrong values with no error anywhere. The
differential test sees both per series and per scenario.

Register for the 2026-10-20 note *AI-Assisted Testing in Spec-Driven
Development*, whose rules this design adopts verbatim: the spec is the
test oracle; atomic requirements with stable IDs; code and tests
generated in separate contexts; assumptions listed, never silently
resolved; deterministic oracles at run time; generated tests committed
with provenance (spec hash, generator, prompt).

Decision link: the research charter's minimum-sufficient-stack answer
(docs/minimum-sufficient-stack.md) was measured on toy systems. This is
its first measurement on a real, operated program with a real
documentation discipline behind it. Feeds no product decision in either
repository and queues no build; a defect found in the original is
reported to J-F as an issue, nothing more.

## 2. The target: J-F's daily asset load

**In scope — `src/jef/data/` (≈ 3 500 lines of Python plus two TOML
files) and the acquisition half of `deploy/daily.sh`:**

| Module | Lines | What it is |
|---|---|---|
| `universe.py` + `universe.toml` | 308 + 129 | the declarative asset universe, strict parser, `modeled_source`, pause semantics |
| `collectors/` (base, eodhd, binance) | 516 | transports (HTTP, Replay, Recording), rate limiter, retries, redaction, symbol normalisation |
| `actions.py` | 183 | the corporate-actions store, split parsing, `sync_actions` |
| `adjust.py` | 97 | the CRSP pass: cumulative split factors, back-adjusted prices, forward-adjusted volume |
| `store.py` | 456 | `ParquetStore`: raw columns immutable, per-symbol lock, temp-file + `os.replace`, `ingest_bars`, `reconcile_bars`, `reapply_adjustment`, `to_contract_frame` |
| `contract.py` | 142 | `validate()`: the seven-column seam contract |
| `health.py` | 518 | `jef-data status`: staleness, phantom-split scan, actions age, post-seam gap, cross-venue spread, declared-class check |
| `classification.py` + `classifications.toml` | 211 + 84 | the vendor-evidence cross-check |
| `differential.py` | 82 | cross-provider series comparison |
| `sync.py` | 408 | `select_legs`, `_run_leg`, `run_sync`: the acquisition ritual — actions before load on raw-basis legs, first-fill floor, tail refresh newest-wins, `end` cap, crypto end-guard, once-per-UTC-day actions gate, independent per-leg failure |
| `cli.py` | 577 | `jef-data` with its ten subcommands and exit codes |
| `deploy/daily.sh` | 181 | the chain `sync → status → binning → publish-on-green`; in scope as a shell artefact with every external command stubbed exactly as `tests/test_daily_chain.py` stubs it |

**Out of scope, by rule:** `jef.binning` (the frozen quant's logic:
its recreation oracle is the goldens, and the discipline there is AST
identity, not re-derivation); `jef.events` and `jef.dashboard`
(telemetry and publish — the chain sources `events.sh`/`dashboard.sh`
and the recreation treats both as given externals); AWS and the venue
(stubbed, as in the original's own tests); the provider networks (the
hosted session has no `EODHD_API_KEY` and is geo-blocked by Binance,
T-0702; every run replays the recorded fixtures).

Why this target works as a lab subject: zero live calls needed (the
collectors are tested against recorded fixtures with a hashed
manifest); the oracle that matters is a DataFrame, compared cell for
cell; the original's own in-scope test modules (sync, store, store
reconcile and robustness, actions, adjust, health, universe, contract,
classification, differential, the two collectors, the rate limiter, the
seam invariance, the daily chain — some 4 000 lines) are a hidden
grading suite nobody has to write; and the frozen Yahoo CSV
(`experiments/AAPL.csv`) gives one bit-exactness oracle for free — the
original proves `load_eod_store` ≡ `load_eod_csv` on it
(`test_seam_invariance.py`), and the recreated store must pass the
same proof.

## 3. Design — four phases, four contexts

```
 Phase 0  freeze         Phase 1  reverse-engineer      Phase 2  recreate         Phase 3  compare
 original + fixtures  →  KIT (spec stack)           →   RC (clean room)       →   RC vs original
 reference outputs       this session, full access      fresh agent, kit only     this session
 hashed                  + provenance file (hidden)      + ASSUMPTIONS.md          differential + triage
```

**Independence is the design, not a wish.** Two clean rooms, not one.
*The reverse engineer* is a fresh agent started on a scratch copy of the
code tree from which `docs/`, `tests/`, every README and the ROADMAP have
been deleted, so it cannot read what it must not; it derives the kit and
the hidden `provenance.json` from that tree. This orchestrating session
has read parts of J-F's data contract and diagram index while planning,
which is exactly why it does not write the kit: it runs the kit gates,
the recreations and the comparison. *The recreator* is a second fresh
agent (never a fork: a fork inherits context) started with one directory,
the kit, copied outside every repository; its prompt names no repository,
URL or package name but the kit's own. Leakage is checked after the fact
on both: each agent's report lists every path it read; the recreated
source is diffed against the original for copied comments and
docstrings, which no kit carries. The original's tests and recorded
fixtures never enter a kit — the kit's scenarios carry their own small
fixtures in the recorded-fixture file shape the kit documents.

The source carries prose: docstrings and comments quote decisions and
cite the contract by section. That is code and stays in. Each kit
requirement records whether it rests on logic read, on comment prose, or
on both, so behaviour read from the program can be told apart from
behaviour read from the author's notes.

### 3.1 Arms

| Arm | Kit contents | What it measures |
|---|---|---|
| **K — the kit** (mandatory) | requirements as code + contracts + UML + Gherkin, all derived from the code tree under §4 | the question as asked |
| **K−UML** (optional) | K without the diagrams | whether the architecture/UML artefacts are *needed* — the literal word in the ask |

Same recreator model, fresh context per arm; one variable per contrast
(charter E3). An arm that hands a recreator J-F's existing documentation
(the first revision's Arm E) is dropped on the maintainer's instruction
not to use the existing diagrams; its question — what that documentation
carries — is answered instead by the post-hoc comparison in §6.

### 3.2 Iteration policy

The recreator may run the kit's Gherkin suite against its own code, at
most **k = 3** rounds, each round's
pass count recorded. The stack lab found iteration repairs only what
visible tests state, so the hidden oracles are where the result lives.

## 4. Phase 1 — the kit (what "requirements as code" means here)

All of it in `recreate_experiment/kit/`, linted and traced by pumllint
before freeze (every gate below is a shipped command).

1. **`requirements.json`** — the requirements *as code*: an array of
   `{id, kind, arc, statement, rationale?}` records. IDs `JDL-NNN`,
   stable, atomic; `arc` carries J-F's own unit of work (`ARC-D2`,
   `ARC-D4`, `ARC-D5`, `ARC-D7`, `ARC-O2`, `ARC-O4`) so the kit joins
   the repository's inventory. Statements in EARS form ("When a
   raw-basis leg has no actions stamp, sync shall refresh actions
   before the first bar fetch"; "If … then `status` shall exit 1 and
   name …"). Kinds: `contract` (the seven-column frame, the load
   transform verbatim, the store schema, the universe grammar, the
   sidecar JSONs), `arithmetic` (CRSP factors, volume raw-ization,
   zero-volume policy, the spread formula, the gap-k calibration — one
   numeric rule each, stated exactly once, W1b's lesson), `ritual`
   (actions before load, tail newest-wins, frozen outside the tail,
   `start` floor vs `end` cap, crypto end-guard, once-per-day actions
   gate, independent leg failure), `verdict` (every alert, warning and
   note `status` can emit, with its threshold and knob), `refusal`
   (every parse-time and run-time refusal with its message), `cli`
   (subcommands, flags, exit codes, `--json`/`--summary-json` shapes,
   `--dry-run` needs no key), `chain` (daily.sh's order, publish on
   green only, the exec guard, the hard cap, ledger emits as given
   externals). Expected count 120–160. This file is also the inventory
   `pumllint trace --requirements` reads.
2. **`provenance.json`** — for each ID the original symbol it was read
   from. **Stays out of every kit** (the leakage channel); Phase 3
   triage only.
3. **Contracts** (`contracts/`): JSON Schemas for `sync --summary-json`
   and `status --json`; the universe and classifications TOML grammars
   as a schema plus the two shipped files; the store's column schema
   and partition layout; the recorded-fixture file shape (request key →
   response) so the recreator can build a replay transport; the `jef-data`
   CLI reference; the refusal catalogue as a decision table. One source
   per decision.
4. **Architecture and UML** (`uml/`, PlantUML, requirement IDs in the
   footer), every diagram drawn from the code tree: component diagram;
   class diagram of the data model (`ParquetStore`,
   `CorporateActionsStore`, `SplitEvent`, the collectors and transports,
   `Universe`/`Asset`/`Source`, the health report); **sequence diagrams
   of `run_sync` and of one leg** (`_run_leg`: the load-bearing ones);
   activity diagram of basis resolution and the CRSP pass; sequence
   diagram of `status`; state diagram of a stored series; sequence of
   the daily chain. Gate: `pumllint` exit 0 and `score --profile codegen
   --min-level 5`. The reverse engineer never sees J-F's `pumllint.toml`
   either: the kit carries its own configuration.
5. **Gherkin** (`features/`): black-box over `jef-data` and `daily.sh`,
   one feature per requirement kind, scenarios tagged `@JDL-NNN`;
   inputs are small recorded-fixture-shaped JSON files written for the
   scenario (a two-split equity, a crypto series with a zero-volume run,
   a tail revision between two runs, a stale actions stamp, a paused
   asset) plus a clock the steps inject (`now`); expected outcomes are
   exit codes, cells of the exported frame, and fields of the two JSON
   reports. pytest-bdd step definitions run the executable named by
   `JDL_UNDER_TEST` (`jef-data` or `jef-data-rc`, `daily.sh` or
   `daily-rc.sh`), so one suite runs against both. **These features
   live in the lab only.** J-F refuses Gherkin pipeline-wide (console
   excepted); nothing from `features/` is proposed for J-F.
6. **Kit gates before freeze:** `pumllint trace kit/uml --requirements
   kit/requirements.json --features kit/features --fail-on-uncovered
   --fail-on-unverified` → every requirement modelled and verified; the
   Gherkin suite **100 % on the original**; two planted mutants must turn
   it red — the actions-before-load order reversed (T-0604's silent
   defect) and the crypto end-guard removed (§7.3's in-progress-day
   bar) — proving the oracle sees the two silent classes. Kit hash
   recorded.

Oracle-separation declaration (mandatory): kit scenarios use their own
fixtures and clock; the hidden oracles are the original's in-scope tests,
the recorded fixtures and `experiments/AAPL.csv`. Any kit scenario whose
input reproduces a recorded fixture is declared `same`; the target is
none.

## 5. Phase 2 — recreation

Fresh `general-purpose` agent, **Opus 5 @ xhigh** (J-F's own table puts
data/ops legs at Opus 5 high–xhigh; a different model from the reverse
engineer also means different priors). Prompt: the kit, the target
(package `jef_data_rc`, console script `jef-data-rc`, a `daily-rc.sh`,
Python ≥ 3.11 with pandas 3.0.5 / numpy 2.4.6 / pyarrow 25.0.1 /
requests 2.34.2 pinned as the kit states), the iteration policy, and
the two obligations from the SDD note — `ASSUMPTIONS.md` naming every
point where the kit was silent and what was chosen, and `READ.log`
listing every path opened. Provenance recorded per arm: model id, kit
hash, prompt text, k used, cost.

## 6. Phase 3 — comparison (pre-registered metrics)

**Environment.** A Python 3.12 venv with J-F's exact pins and the
deterministic numeric runtime its conftest sets (T-0001: `.[test,data]`,
venv activated). No network: every provider call replays fixtures; AWS,
`jef-binning` and the ECS metadata probe are stubs on PATH exactly as in
`tests/test_daily_chain.py`.

**Reference set, frozen in Phase 0 with SHA-256 per artefact.** Two
kinds of input: (a) the recorded fixtures (AAPL and TLT EOD, splits and
dividends; BTC-USD.CC EOD; the Binance klines; the AAPL search), hashed
in `tests/data/fixtures/manifest.json`; (b) the committed Yahoo CSV
`experiments/AAPL.csv`. Over them, a scripted scenario set run on both
implementations with an injected clock: first fill of every leg; a
second run with a revised cell inside the tail and one outside it; a
split event arriving between runs; the zero-volume-run series; the
crypto end-guard at the UTC boundary; a universe `end` cap; a paused
asset, named and unnamed by `--asset`; a selection matching nothing;
`--dry-run` without a key; `status` with fresh, stale and never-synced
actions; `status` on a series two sessions stale; the cross-venue spread
at and above the threshold; the phantom-split scan; `import-csv` of the
Yahoo file followed by `export`; the daily chain green, red at sync, red
at status, red at one asset. Expected count 25–35 scenarios.

| # | Metric | Unit | Severity when it fails |
|---|---|---|---|
| M1 | **Seam frame identical** cell for cell: `to_contract_frame` / `jef-data export` of every stored series, both implementations | per series per scenario | **1** — a different number flows into the model silently |
| M2 | **Gate inversion**: RC `status` exits 0 where the original exits 1 (the chain would publish a red day) | count | **1** |
| M3 | Reverse inversion: RC exits 1 where the original exits 0 | count | 2 |
| M4 | `status --json` identical (verdicts, alerts, warnings, notes, values) | per scenario | 3; non-identical ones classified: same verdicts, different values or wording |
| M5 | `sync --summary-json` identical (legs, rows, revised cells, dropped) | per scenario | 3 |
| M6 | Store equal beyond the seam: `*_raw` columns, partitions, the actions files | per series | 2 — raw history is the immutable record |
| M7 | Exit codes and refusal messages identical on every refusal scenario | per scenario | 2 |
| M8 | Seam invariance: RC's store path ≡ the original's CSV path on `experiments/AAPL.csv`, bit-exact | pass/fail | **1** |
| M9 | Original's in-scope tests against RC, split black-box (CLI, chain) vs API-level | pass rate per split | reported; API-level depends on the names the UML specifies, so K−UML is expected lower by construction |
| M10 | Kit Gherkin on RC after k rounds | pass rate | reported |
| M11 | Assumptions listed vs divergences: how many divergences the recreator had already flagged as a gap | ratio | the SDD note's "each assumption is a spec defect", measured |

**Triage** of every M1–M8 divergence into one of four classes — spec
defect (the kit did not carry it; cite the missing or ambiguous
requirement), code defect (the kit carried it; cite the ID), test defect
(a kit scenario asserts the wrong thing), original defect (J-F is wrong;
file an issue, change nothing here) — using `provenance.json`. The
spec-defect list, grouped by requirement kind, is the headline table;


**The side result, taken last.** Only after every arm is scored, the
kit's diagrams and contracts are set beside J-F's existing eight
data-load diagrams and its data contract: two specification sets derived
independently from the same code. Every disagreement is a defect signal
in one of them (the SDD note's principle), classified by hand — kit
wrong, existing wrong, both right at different altitudes — and reported
to J-F as findings, not changes. Taken last so it cannot influence the
kit.

**One closing round** (budget permitting): fold Arm K's spec defects
back into the kit (dated, additive), re-run the recreator, re-measure
M1–M8. One round only; the delta is the SDD note's "spec defects found
per iteration".

## 7. Pre-registered expectations and interpretation

- **E1** Arm K: M1 identical on 100 % of series. Below: the kit lost a
  numeric rule — name it; the `arithmetic` kind is the suspect.
- **E2** Arm K: M2 = 0. Any count above zero: the `verdict`
  requirements are under-specified (threshold, knob or clock semantics)
  — the answer on "which level of detail" for a health gate.
- **E3** The post-hoc comparison finds at least one disagreement between
  the kit and J-F's existing diagrams that the source settles against
  the existing diagram. Confirmed: a Level 5 gate did not catch it
  (T-0800 measured, not argued). None found: the existing set is
  faithful on everything the kit models — recorded as such.
- **E4** Spec defects outnumber code defects in triage (every arm). If
  reversed: the bottleneck is the generator, not the spec — the
  opposite of the SDD note's thesis, recorded as such.
- **E5** (K−UML only) within 5 pp of K on M1/M2: the UML carries little
  the requirements, contracts and Gherkin do not. A larger gap,
  concentrated in `ritual` scenarios: the `_run_leg` sequence diagram
  is load-bearing, the W1 "behaviour artefact" result on a real program.
- **E6** M11 ≥ 0.5: assumption-listing is a cheap spec-defect detector.
- **E7** M8 passes in Arm K. Fails: the load transform or the CRSP
  arithmetic was carried imprecisely — the single most consequential
  spec defect the experiment can find, since it is the seam the goldens
  stand on.

Failed expectations are recorded as failures with the same prominence.

## 8. What this experiment never does

No file under J-F changes: not `experiments/`, not `tests/golden/`, not
the data layer, not the docs — the repository is read as an oracle and
run in a scratch venv. A defect found in the original is an issue with
a reproducer, filed on the maintainer's go. The kit's Gherkin is lab
material and is not proposed for J-F. No live provider call: fixtures
only. Nothing here touches the venue, its bucket, or any schedule.

## 9. Budget, effort, timeline

- This session (Fable 5.1): Phases 0, 3, 4 and the kit gates.
- Reverse-engineering agent: **Opus 5 @ xhigh** (the kit's accuracy on
  the arithmetic and the verdicts is the whole experiment), one run on
  the stripped code tree; ≈ 140 requirements, 7–9 diagrams, ≈ 30
  scenarios with fixtures, 4 schemas; about three hours of agent time,
  then the gates and the mutant calibration here.
- Recreation agent: Opus 5 @ xhigh, one run per arm, k ≤ 3; one to two
  hours each.
- Ceiling: **one reverse-engineering run, two recreation runs plus one
  closing round**; stop and report when reached. No API spend outside the agent runs.
- Record: `docs/recreate-experiment.md` in pumllint (dated, house
  style), a ROADMAP entry under the research program, the two artifact
  pages refreshed. J-F receives nothing unless the maintainer asks for
  an evaluation record there (then `docs/EVALUATION_RECREATION.md` in
  J-F's house frame, with the ontology page regenerated if its gate
  counts the file, T-0006).

## 10. Decisions (all taken, see the header)

1. **Are the original's tests part of "the codebase" the reverse
   engineer may read?** Recommended: no — `tests/` stays hidden, so the
   original's suite remains an untouched grading oracle and the kit's
   Gherkin is derived from behaviour, not from existing assertions; an
   edge case the tests pin and the reverse engineer misses then surfaces
   in the comparison as a spec defect, which is the experiment working.
2. **Arms:** K alone, or K and K−UML.
3. **Closing round:** authorised in advance under the ceiling, or
   decided after the first comparison.

Settled by the maintainer on 2026-10-23: the scope is `src/jef/data/`
plus the acquisition half of `daily.sh`; the lab lives in
`pumllint/recreate_experiment/` and J-F is never changed; the kit is
derived from the code alone, no existing diagram or document used.

## 11. Carried limitations

One program, one domain, one recreator model per arm, n = 1 run per arm
(a recreation is not cheaply repeatable, so results are quoted as single
runs, never as rates). The reverse engineer and the comparison analyst
are the same context — mitigated by pre-registered metrics and
mechanical oracles, not removed. The scenario set replays nine recorded
fixture files and one CSV; it cannot see live-provider behaviour
(provisional closes, pagination at scale, rate limits in anger), only
the code paths the fixtures and stubs reach. Capability-relative:
re-measure per model generation.

## Results

*(appended as the phases complete; nothing above this line changes)*

### Phase 0 — frozen 2026-10-23

- Pre-registration frozen at pumllint `5c1fa55`
  (sha256 `4f14e9a0…1982` of this file at that commit).
- Subject: J-F at `8f6d6b0` (= `origin/main`), read-only throughout; the
  working tree showed zero tracked changes before and after the reference run.
- Reverse engineer's clean room: a copy of `src/jef/data/`, `deploy/daily.sh`,
  the two sourced scripts as marked externals, and a reduced `pyproject.toml`
  with the pins, installed into its own venv; no `docs/`, `tests/`, README or
  ROADMAP present. The reverse-engineering agent: Opus 5 @ xhigh, fresh
  context, brief in the Agent call of this session.
- Comparison harness (`harness/`): 24 scenario groups, **157 artefacts**,
  through the adapter interface fixed in `harness/HARNESS_INTERFACE.md`
  (given to the reverse engineer verbatim, to be copied into the kit). Inputs
  derived from the subject's nine recorded fixtures plus six derived variants
  (windowless AAPL dividends, a revised TLT tail, a TLT jump, a two-bar BTC
  tail with one revised close, a zero-volume BTC run) and 18 universe files
  (`harness/INPUTS.sha256.json`, 36 files). Reference outputs:
  `harness/REFERENCE.MANIFEST.sha256.json`. Two reference runs compare
  identical after normalising wall-clock values (ISO stamps, the chain's run
  stamp and stage epochs, the actions `last_updated` field, store and tmp
  paths); those are the pre-registered exclusions.
- M8 on the reference: PASS (10 400 rows through the original loader).
- One observation on the original, to be triaged with the rest:
  `jef-data export` on a series the store does not hold exits 1 with a raw
  `AttributeError` traceback instead of a message (scenario
  `s21_cli_refusals/export_empty`).
- Deviation from §4 item 1, minor: the `arc` field cannot be filled by a
  reverse engineer who sees no roadmap, so `requirements.json` carries
  `id`, `kind`, `statement`, `basis`, `rationale?` and no `arc`.
- Recreator brief recorded verbatim in `harness/RECREATOR_PROMPT.md`.

### Phase 1 — the kit, frozen 2026-10-23

Produced by one fresh Opus 5 @ xhigh agent on the stripped code tree
(169 tool calls, 88 minutes). Kit hash (sha256 over the sorted
`sha256sum` list of its 192 files): `7ca3c135a83157ad…`; the no-UML copy
(`uml/` and `pumllint.toml` removed, the README's diagram paragraph
dropped): `c83bbd02f7765571…`. Committed as `recreate_experiment/kit/`
with the hidden record in `recreate_experiment/hidden/` (pumllint
`1451c05`).

| Artefact | Count |
|---|---|
| Requirements (`requirements.json`) | 158: contract 48, ritual 27, arithmetic 22, refusal 19, cli 17, chain 13, verdict 12; basis both 112, logic 45, prose 1 |
| Contracts | 14 documents + 2 JSON Schemas with examples + the two shipped TOML files + the harness interface |
| Diagrams | 8 (component, class, 4 sequence, 1 activity, 1 state); 231 lines for the class diagram, 19–73 for the rest |
| Scenarios | 95 in 11 features (23 outlines), 178 test cases; 148 synthetic fixture files |

**Gates, re-run by this session with pumllint 0.34.0 from the kit
directory (not taken from the agent's report):** lint `--fail-on info`
no findings, exit 0; score Level 5 (Method-complete) 100/100 on all 8
diagrams; trace 158/158 realised and 158/158 verified, exit 0. The
syntax gate (DIM-SYN) did not run: no PlantUML renderer here. The kit's
own `pumllint.toml` raises `max-elements` to 80 for the one class
diagram (70 elements).

**Calibration, re-run by this session:** the suite passes **178/178**
on the subject (54 s). Mutant m1 (bar fetch moved before the
corporate-actions refresh; store-invisible by construction): **2
failures**. Mutant m2 (crypto end-guard removed): **11 failures**.
Both mutant trees differ from the subject by the one intended edit.

**Clean-room checks:** the subject tree is byte-identical to J-F's
`src/jef/data/` and `deploy/daily.sh` after the run; J-F's checkout has
zero tracked changes; the read log (127 lines) names nothing outside
the tree, the kit directory and the interface file; zero lines of 50+
characters are shared between the subject's source and any kit file;
the only document references in the kit are inside message strings
the program itself emits (the subject's messages cite its own
documents by section), which the recreator must reproduce byte for
byte. One integrity note from the agent's record: eleven `.pyc` files
appeared in the subject copy's `__pycache__` during its run although
every command set `PYTHONDONTWRITEBYTECODE=1`; it deleted exactly
those and no source changed (verified above).

**Observations on the original, parked for triage** (from the agent's
`hidden/NOTES.md`, "comment says one thing, logic another"): the
store's `timestamp` column holds Unix seconds under the pinned pandas
while its schema comment says milliseconds; `ingest_yahoo_csv` reports
a row count that includes duplicate dates it then drops; the health
module documents an `actions_missed_k` knob the CLI never exposes; the
docstring of `run_sync` says the injected clock drives the actions
gate, but the stamp the gate reads is always the real clock. Plus the
Phase 0 one: `export` on an absent series exits with a raw traceback.

**Scope the harness cannot reach, declared by the kit (NOTES.md):** the
live transport, the rate limiter and the 30 s timeout; connection-error
retries and non-JSON bodies; the refusal past 100 Binance pages; the
300 s lock timeout; the happy paths of hand-run `load` and
`sync-actions`; the `unmapped` class verdict. These requirements are
folded into the nearest observable one and are a known hole in M10.

Recreations launched 2026-10-23, both Opus 5 @ xhigh, fresh contexts,
brief as recorded (`harness/RECREATOR_PROMPT.md`), k ≤ 3: Arm K on the
full kit (venv `.rc-k-venv`), Arm K−UML on the no-UML copy (venv
`.rc-kminusuml-venv`). The two given externals were placed beside each
output directory before launch.

