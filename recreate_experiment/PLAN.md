# Recreation experiment — reverse-engineer, specify, recreate, compare

*Plan, 2026-10-23, draft for the maintainer's go. Becomes
`PREREGISTRATION.md` (frozen, hashed) once the four decisions in §9 are
taken and before any recreation run. House protocol applies
(`stack_experiment/PREREGISTRATION_TEMPLATE.md`, research-charter.md §7):
oracles, expectations and the interpretation matrix are fixed before the
first scored run; failures are recorded with the same prominence as
confirmations. This directory is lab territory: nothing in it ships.*

## 1. Question and decision link

**Can a specification stack reverse-engineered from working code —
requirements as code, architecture and UML, contracts, Gherkin — carry
enough information for an independent agent to recreate the code, and
where exactly does it fall short?**

Every wave so far (C4 ladder, W1–W5) ran the hop *forward*: an authored
spec → generated code, graded by a hidden suite. This runs it *round
trip*: code → spec → code, graded by the original. The original is a
perfect oracle, so for the first time a divergence can be attributed:
a fact the artefacts failed to carry (spec defect), a fact they carried
and the generator missed (code defect), a scenario that asserts the
wrong thing (test defect) — or a defect in the original. The count and
class of the spec defects is the result: it says which information
classes a reverse-engineered spec loses, which is the mirror of the
charter's "which artefacts, which level of detail".

Decision link: the research charter's minimum-sufficient-stack answer
(docs/minimum-sufficient-stack.md) was measured on toy systems with
canonical or adversarial numbers. This is the first measurement on a
real, shipped program with a real corpus. Outcome branches in §7.
Feeds no product decision and queues no build; a defect found in the
original is reported to its repository as an issue, nothing more.

Register for the 2026-10-20 note *AI-Assisted Testing in Spec-Driven
Development*, whose rules this design adopts verbatim: the spec is the
test oracle; atomic requirements with stable IDs; code generation and
test generation in separate contexts; assumptions listed, never
resolved silently; deterministic oracles at run time; generated tests
committed with provenance (spec hash, generator, prompt).

## 2. The target: aris2puml, whole (recommended)

| Candidate | Size | Oracle in hand | Verdict |
|---|---|---|---|
| **aris2puml** (readers, structure, emit, report, diagnose, cli) | 1 550 lines, 7 modules, 136 tests | golden diagram; 136 tests; 9-EPC corpus + the SAP EPML collection (hundreds of models) under `census.py`; sidecar ↔ census agreement; pumllint lint of every output | **Take it.** Small enough to recreate in one agent run, large enough that the structuring pass is a real algorithm with refusal semantics — the place a recreation will *invent structure*, which is the failure class this chain exists to prevent, and a differential test sees it per model. |
| pumllint `trace` subcommand | 667 lines, one module | 20-odd tests, JSON schema | Fallback if the budget halves: one module, a clean contract, but no corpus-scale differential. |
| J-F `jef.binning` | ~3 000 lines | byte-exact goldens | Refused for this experiment: the logic is the quant's frozen intent and the goldens already *are* its recreation oracle; the interesting hop there is R, not Python, and h2o cannot run here. |

Out of scope inside aris2puml: `aris/export_epc.js` (untested, no oracle),
`tools/corpus/*` (lab tooling), the `--check` wiring beyond invoking
pumllint as a subprocess (pumllint is a dependency, not the subject).

## 3. Design — four phases, three contexts

```
 Phase 0  freeze        Phase 1  reverse-engineer      Phase 2  recreate        Phase 3  compare
 original + corpus  →   KIT (spec stack)           →   RC (clean room)      →   RC vs original
 reference outputs      this session, full access      fresh agent, kit only    this session
 hashed                 + provenance file (hidden)     + ASSUMPTIONS.md         differential + triage
```

**Independence is the design, not a wish.** The reverse engineer (this
session) sees everything. The recreator is a *fresh* agent (not a fork:
a fork inherits this context and with it the original source) started
with one directory, the kit, copied outside both repositories; the
prompt names no repository, no URL, no package name but the kit's own.
Leakage is checked after the fact: the recreator's report lists every
path it read; the recreated source is diffed against the original for
copied comments and docstrings, which the kit never carries. The
original's test suite and the corpus never enter the kit.

### 3.1 Arms (the improvement worth paying for)

| Arm | Kit contents | What it measures |
|---|---|---|
| **A — full kit** (mandatory) | requirements + contracts + UML + Gherkin | the question as asked |
| **B — no UML** (optional, same recreator model, fresh context) | requirements + contracts + Gherkin | whether the architecture/UML artefacts are *needed* to recreate, or only the requirements and tests are — the literal word in the ask |

Vary one thing at a time (charter E3). If budget allows a third arm, it
is *A minus Gherkin*, the tests-as-input question W1 already answered on
toys. Recommendation: run A; run B if A completes under half the ceiling.

### 3.2 Iteration policy

The recreator may run the kit's Gherkin suite against its own code and
iterate at most **k = 3** rounds; each round's pass count is recorded.
The stack lab found iteration repairs only what visible tests state, so
the hidden oracles are where the result lives.

## 4. Phase 1 — the kit (what "requirements as code" means here)

All of it in `recreate_experiment/kit/`, linted and traced by pumllint
itself before freeze (dogfooding; every gate below is a shipped command).

1. **`requirements.json`** — the requirements *as code*: an array of
   `{id, kind, statement, rationale?}` records. IDs `A2P-NNN`, stable,
   atomic; statements in EARS form ("When … the converter shall …";
   "If … then … shall refuse, naming …"). Kinds: `contract` (JSON v1,
   sidecar, manifest, file naming), `mapping` (one per row of the
   README's mapping table), `structure` (one per accepted shape),
   `refusal` (one per `StructureError` site — 24 — with the message
   verbatim and the node ids it names), `cli` (flags, exit codes, stdout
   rules, path slashes, `newline="\n"`), `approximation` (the three
   `APPROXIMATED` codes, the two `DROPPED`, `--strict` as set
   membership). Expected count 90–120. This file is also the inventory
   `pumllint trace --requirements` reads — no second format.
2. **`provenance.json`** — for each ID the original symbol it was read
   from. **Stays out of the kit** (it is the leakage channel); used in
   Phase 3 triage only.
3. **Contracts** (`contracts/`): JSON Schema for the version-1 input,
   the sidecar and the manifest; the mapping table; the refusal
   catalogue as a decision table (condition → message → ids named);
   the emitter's formatting rules (indentation, label joining, footer
   grammar, slug rule, duplicate-name rule); the CLI reference. One
   source per decision (W1b: in-bundle restatement drifts and dilutes).
4. **Architecture and UML** (`uml/`, PlantUML, each carrying its
   requirement IDs in the footer so `trace` can join them):
   component diagram (readers → model → structure → emit → report /
   diagnose → cli, with pumllint external); class diagram of the model
   (`Process`, `Node`, `Edge`, `Lane`, `Data`, `Note`, `StructureError`,
   the block types); **activity diagram of the structuring pass** — the
   load-bearing one: back-edge classification, entry regions, the
   walk, where each refusal fires; sequence diagram of one CLI run;
   state diagram of a process's outcome (converted / approximated /
   dropped / refused / refused-under-strict). Gate: `pumllint` exit 0
   and `score --profile codegen --min-level 5` on the behaviour
   diagrams, the lab's own bar.
5. **Gherkin** (`features/`): black-box over the CLI, one feature per
   requirement kind, scenarios tagged `@A2P-NNN`; inputs are small
   inline EPC JSON documents written for the scenario, expected outputs
   are inline PlantUML fragments or exact lines. pytest-bdd step
   definitions call the executable named by `A2P_UNDER_TEST`
   (`aris2puml` or `aris2puml-rc`), so one suite runs against both.
   The kit ships the features *and* the steps.
6. **Kit gates before freeze:** `pumllint trace kit/uml --requirements
   kit/requirements.json --features kit/features --fail-on-uncovered
   --fail-on-unverified` → every requirement modelled and verified;
   the Gherkin suite **100 % on the original**; one planted mutant
   (the "loop header is not an XOR join" refusal removed) → the suite
   must go red, proving it can see invented structure. Kit hash
   recorded.

Oracle-separation declaration (mandatory): kit scenarios use their own
inline inputs; the hidden oracles are the original's 136 tests and the
corpus. Any kit scenario whose input is a corpus model is declared
`same`; the target is none.

## 5. Phase 2 — recreation

Fresh `general-purpose` agent, **Opus 5 @ xhigh** (the structuring pass
is Opus-tier work by aris2puml's own table; a different model from the
reverse engineer also means different priors). Prompt: the kit, the
target (`aris2puml_rc`, console script `aris2puml-rc`, Python ≥ 3.11,
zero runtime dependencies, the CLI contract byte for byte), the
iteration policy, and the two obligations from the SDD note — an
`ASSUMPTIONS.md` naming every point where the kit was silent and what
was chosen, and a `READ.log` of every path opened. Provenance recorded:
model id, kit hash, prompt text, k used, cost.

## 6. Phase 3 — comparison (pre-registered metrics)

Reference set, frozen in Phase 0 with SHA-256 per file: the original's
`.puml`, sidecar and exit code for every model in (a) the two fixtures,
(b) the four BPMAI EPCs, (c) the five SAP EPCs (`fetch_sap.py`; the
proxy reached PyPI, so the download is expected to work — if not,
recorded), (d) the whole SAP EPML collection through `epml_to_json.py`
(hundreds of models: the corpus-scale differential; `census.py` on both
implementations must agree with each sidecar). Same inputs, same flags
(default; `--strict`; `--notes`; `--report`; `--manifest`).

| # | Metric | Unit | Severity when it fails |
|---|---|---|---|
| M1 | Outcome class agreement (converted / approximated / refused) | per model | — |
| M2 | **Invented structure**: RC converts where the original refuses | count | **1** — the failure class this chain exists to prevent |
| M3 | RC refuses where the original converts | count | 2 |
| M4 | Refusal message + named ids identical | per refused model | 3 |
| M5 | `.puml` byte-identical | per converted model | 4; non-identical ones classified: pumllint findings identical (semantic match) / differ |
| M6 | Sidecar and manifest JSON equal (modulo tool name) | per run | 3 |
| M7 | Original's 136 tests against RC, split CLI-level vs API-level | pass rate per split | reported, not gated — API tests depend on module names the UML specifies in Arm A only |
| M8 | Kit Gherkin on RC after k rounds | pass rate | reported |
| M9 | Assumptions listed vs. divergences: how many divergences the recreator had already flagged as a gap | ratio | the SDD note's "each assumption is a spec defect" claim, measured |

**Triage** of every M2–M6 divergence into one of four classes — spec
defect (the kit did not carry it; cite the missing or ambiguous
requirement), code defect (the kit carried it; cite the ID), test
defect (a kit scenario asserts the wrong thing), original defect
(aris2puml is wrong; file an issue, change nothing here) — using
`provenance.json`. The spec-defect list, grouped by requirement kind,
is the headline table.

**One closing round** (budget permitting): fold the spec defects back
into the kit (dated, additive), re-run the recreator on the revised
kit, re-measure M1–M6. One round only; the delta is the "spec defects
found per iteration" metric the SDD note asks for.

## 7. Pre-registered expectations and interpretation

- **E1** M1 ≥ 90 % on the corpus-scale set. Below: the kit's
  structure/refusal requirements are under-specified as a class.
- **E2** M2 = 0. Any count above zero means the refusal catalogue as a
  decision table is not sufficient and the algorithm's activity diagram
  must carry the walk — a direct answer on "which level of detail".
- **E3** M5 byte-identity ≥ 60 % of converted models, and ≥ 90 %
  semantic match (identical pumllint findings). The gap between the
  two is the emitter's formatting detail the kit under-specified.
- **E4** Spec defects outnumber code defects in triage. If reversed,
  the bottleneck is the generator, not the spec — the opposite of the
  SDD note's thesis, recorded as such.
- **E5** (Arm B only) Arm B's M1–M5 within 5 pp of Arm A's: the UML
  carries little the requirements + Gherkin do not. A larger gap,
  concentrated in structure/refusal models: the activity diagram is
  load-bearing, which is the W1 "behaviour artefact" result on a real
  program.
- **E6** M9 ≥ 0.5: half the divergences were already visible as
  listed assumptions, so assumption-listing is a cheap spec-defect
  detector. Below: assumption-listing misses most gaps.

Failed expectations are recorded as failures with the same prominence.

## 8. Budget, effort, timeline

- This session (Fable 5.1): Phases 0, 1, 3, 4 — the reverse engineering
  is the long part (~2 hours of agent time; the kit is ~120
  requirements, 5 diagrams, ~60 scenarios, 3 schemas).
- Recreation agent: Opus 5 @ xhigh, one run per arm, k ≤ 3; estimate
  one to two hours each.
- Ceiling: **two recreation runs plus one closing round**; stop and
  report when reached. No API spend outside the agent runs.
- Record: `docs/recreate-experiment.md` (dated, house style), a ROADMAP
  entry under the research program, the two artifact pages refreshed.
  aris2puml's ROADMAP gets a line only if an original defect is found.

## 9. Decisions needed before freeze

1. **Target:** aris2puml whole, as §2 recommends — or the `trace`
   fallback.
2. **Arm B** (no-UML ablation): run it, or Arm A alone.
3. **Home of the lab:** `pumllint/recreate_experiment/` as here (the
   research program lives in pumllint; nothing enters aris2puml), or a
   separate repository.
4. **Closing round:** authorised in advance under the ceiling, or
   decided after the first comparison.

## 10. Carried limitations

One program, one domain, one recreator model per arm, n = 1 run per
arm (a recreation is not cheaply repeatable, so single-run results are
quoted as single runs, never as rates). The reverse engineer and the
comparison analyst are the same context — mitigated by pre-registered
metrics and mechanical oracles, not removed. The corpus-scale set is
EPC-shaped by notation only for the BPMAI models; the SAP set is the
ARIS-shaped evidence. Capability-relative: re-measure per model
generation.
