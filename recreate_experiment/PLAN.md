# Recreation experiment — reverse-engineer, specify, recreate, compare

*Plan, 2026-10-23 (revised the same day: the target is J-F's daily asset
load, named by the maintainer after the first draft proposed aris2puml).
Draft for the maintainer's go. Becomes `PREREGISTRATION.md` (frozen,
hashed) once the decisions in §10 are taken and before any recreation
run. House protocol applies (`stack_experiment/PREREGISTRATION_TEMPLATE.md`,
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

Two things make this target sharper than a toy. **The subject already
carries a pumllint-gated model set** — eight data-load diagrams at
Level 5, 100/100 under the codegen profile, a requirement inventory, a
source join — and a normative contract (`docs/DATA_CONTRACT.md`). J-F's
own trap T-0800 says the green gate "scores the set against itself,
never against the code". A recreation from those artefacts alone is the
first measurement of what they carry (§3.1, Arm E). And **the subject's
failure class is silent and numeric**: a wrong cell in the frame the
binning consumes, or a health gate that says green on a red day, feeds
the model wrong values with no error anywhere. The differential test
sees both per series and per scenario.

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

## 3. Design — four phases, three contexts

```
 Phase 0  freeze         Phase 1  reverse-engineer      Phase 2  recreate         Phase 3  compare
 original + fixtures  →  KIT (spec stack)           →   RC (clean room)       →   RC vs original
 reference outputs       this session, full access      fresh agent, kit only     this session
 hashed                  + provenance file (hidden)      + ASSUMPTIONS.md          differential + triage
```

**Independence is the design, not a wish.** The reverse engineer (this
session) sees everything. The recreator is a *fresh* agent (not a fork:
a fork inherits this context and with it the original source), started
with one directory, the kit, copied outside every repository; the
prompt names no repository, URL or package name but the kit's own.
Leakage is checked after the fact: the recreator's report lists every
path it read; the recreated source is diffed against the original for
copied comments and docstrings, which no kit carries. The original's
tests and the recorded fixtures never enter a kit — the kit's scenarios
carry their own small fixtures in the same recorded-fixture file shape.

### 3.1 Arms

| Arm | Kit contents | What it measures |
|---|---|---|
| **E — existing documentation** (cheap, recommended) | `docs/DATA_CONTRACT.md`, `docs/DATA_LOADER_PLAN.md`, `docs/DAILY_OPS_PLAN.md`, the `jef-data` entries of `docs/COMMANDS.md`, the eight `data_*.puml` diagrams plus `ops_daily_chain.puml`, `requirements.txt`, `universe.toml`, `classifications.toml`. Nothing written for this experiment. | what the house's own documentation discipline carries — T-0800's question, measured rather than argued |
| **K — the kit** (mandatory) | requirements as code + contracts + UML + Gherkin, reverse-engineered under §4 | the question as asked |
| **K−UML** (optional) | K without the diagrams | whether the architecture/UML artefacts are *needed* — the literal word in the ask |

Same recreator model, fresh context per arm; one variable per contrast
(charter E3). Recommendation: run E and K; add K−UML if K completes
under half the ceiling. E costs no kit work and turns a standing trap
into a number.

### 3.2 Iteration policy

The recreator may run the kit's Gherkin suite (Arm K) or nothing (Arm E
has no executable tests, by construction — that is part of what E
measures) against its own code, at most **k = 3** rounds, each round's
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
   footer): component diagram; class diagram of the data model
   (`ParquetStore`, `CorporateActionsStore`, `SplitEvent`, the
   collectors and transports, `Universe`/`Asset`/`Source`, the health
   report); **sequence diagrams of `run_sync` and of one leg**
   (`_run_leg`: the load-bearing ones); activity diagram of basis
   resolution and the CRSP pass; sequence diagram of `status`; state
   diagram of a stored series; sequence of the daily chain. The
   existing nine diagrams are the starting point, re-read against the
   source per T-0800 (`tools/diagram_sources.py read`), corrected and
   extended where the read finds a gap — and every such correction is
   itself a finding about Arm E. Gate: `pumllint` exit 0 and `score
   --profile codegen --min-level 5`, the subject's own bar.
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
| M9 | Original's in-scope tests against RC, split black-box (CLI, chain) vs API-level | pass rate per split | reported; API-level depends on the names the UML specifies, so Arm E and K−UML are expected lower by construction |
| M10 | Kit Gherkin on RC after k rounds | pass rate | reported |
| M11 | Assumptions listed vs divergences: how many divergences the recreator had already flagged as a gap | ratio | the SDD note's "each assumption is a spec defect", measured |

**Triage** of every M1–M8 divergence into one of four classes — spec
defect (the kit did not carry it; cite the missing or ambiguous
requirement), code defect (the kit carried it; cite the ID), test defect
(a kit scenario asserts the wrong thing), original defect (J-F is wrong;
file an issue, change nothing here) — using `provenance.json`. The
spec-defect list, grouped by requirement kind, is the headline table;
for Arm E it is grouped by the document that should have carried it.

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
- **E3** Arm E below Arm K on M1 and M2 by ≥ 20 pp of series/scenarios.
  Confirmed: the documentation carries the decisions but not the
  arithmetic and the verdict thresholds, the W1/W1b result on a real
  program. Refuted (E within 5 pp of K): the existing documentation
  already *is* a sufficient spec and the kit buys little — recorded as
  a result for the house discipline, with the kit's residual value
  located in whatever E still lost.
- **E4** Spec defects outnumber code defects in triage (both arms). If
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

- This session (Fable 5.1): Phases 0, 1, 3, 4. Phase 1 is the long
  part — ≈ 140 requirements, 7–9 diagrams re-read and corrected against
  source, ≈ 30 scenarios with their fixtures, 4 schemas, the mutant
  calibration; about three hours of agent time.
- Recreation agent: Opus 5 @ xhigh, one run per arm, k ≤ 3; one to two
  hours each; Arm E likely shorter (less to read, more to guess).
- Ceiling: **three recreation runs plus one closing round**; stop and
  report when reached. No API spend outside the agent runs.
- Record: `docs/recreate-experiment.md` in pumllint (dated, house
  style), a ROADMAP entry under the research program, the two artifact
  pages refreshed. J-F receives nothing unless the maintainer asks for
  an evaluation record there (then `docs/EVALUATION_RECREATION.md` in
  J-F's house frame, with the ontology page regenerated if its gate
  counts the file, T-0006).

## 10. Decisions needed before freeze

1. **Scope:** `src/jef/data/` plus the acquisition half of `daily.sh`
   as §2 draws it — binning, events, dashboard and AWS out.
2. **Arms:** E and K as recommended; K−UML in or out.
3. **Home of the lab:** `pumllint/recreate_experiment/`, J-F untouched —
   or a record in J-F too.
4. **Closing round:** authorised in advance under the ceiling, or
   decided after the first comparison.

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
