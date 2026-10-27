# Pre-registration: OpenWiki's generated wiki against the specification kit

*Frozen 2026-10-27, before any OpenWiki artefact for this subject exists.
Nothing above the Results section changes after the first artefact lands;
corrections go into Results, dated. Maintainer-facing.*

## 1. Question

LangChain's OpenWiki (`npm install -g openwiki`, 0.7.2) generates a
Markdown wiki for a repository so coding agents read it before the source.
Since 0.7 each page carries **Grounded Claims**: atomic statements pinned to
`repo://path#Lx-Ly` evidence with content hashes, re-checked for staleness
on `--update`. This programme's approach produces a **specification kit**
from the same kind of input: requirements as code, contracts, diagrams,
decision tables, a glossary, and an executable acceptance suite graded
against the original. The question is what each artefact set is worth to
two readers, a maintainer who needs to know what the system does and a
builder who must rebuild it, and what each one's machine checks actually
prove.

Three sub-questions, each with a measure below:

1. **Accuracy.** Of what the wiki states, how much is true of the code?
2. **Coverage.** Of what the code does (the kit's 163 verified
   requirements), how much does the wiki state, and does it state anything
   the kit lacks?
3. **Sufficiency.** Can a fresh agent rebuild the lane from the wiki alone,
   as it could from the kit, graded cell for cell against the original?

## 2. Subject and inputs

- **Subject:** the clean-room tree the kit's reverse engineer saw
  (`../PREREGISTRATION.md`, Phase 0): J-F at `8f6d6b0`, `src/jef/data/`,
  `deploy/daily.sh`, the two sourced scripts copied verbatim and marked as
  given externals (`deploy/EXTERNALS.md`), a reduced `pyproject.toml`
  (name, Python floor, the three exact pins, the `jef-data` script). No
  `docs/`, `tests/`, README, ROADMAP or CLAUDE.md. Built by
  `tools/make_clean_room.py`, which also makes it a one-commit git
  repository, since OpenWiki resolves evidence from a git top level.
  **23 files; subject tree sha256
  `535982e69fc071eae6ed532606759b2eb857993eda72f578f3fb453db1bb9fbd`**
  (over the sorted path+sha256 list, before the git metadata). OpenWiki
  therefore sees exactly what the kit's author saw: code, no tests, no
  prose. This is the one condition under which the two are comparable.
- **Arm K, the kit:** `../kit/` at `MANIFEST.sha256` sha256
  `74bbe194c1cca628…` (207 files): 163 requirements (contract 48, ritual
  27, arithmetic 22, refusal 21, cli 20, chain 13, verdict 12), 14
  contract documents and two JSON Schemas, 8 PlantUML diagrams at Level 5,
  12 feature files with 131 scenarios and 258 test cases, 7 DMN files
  (13 tables, 63 rules) with gap, overlap and output-typing checks, a
  63-term glossary, and the handover set (`../handover/`, 12 known quirks).
  The kit is the product of four rounds (2026-10-23 to 10-24: the
  reverse-engineering agent, two in-house rebuilds, an outside rebuild,
  the follow-up wave); **round 1 alone** (158 requirements, 178 cases,
  kit hash `7ca3c135…`, one Opus 5 @ xhigh agent, 88 minutes) is the fair
  comparator for a single OpenWiki run and is reported beside the current
  kit wherever a measure depends on the round.
- **Arm W, the wiki:** one `openwiki --print --init` over the clean room,
  by `tools/run_openwiki.sh`, which checks the pinned version, exactly one
  provider credential, a clean subject, page concurrency 1, telemetry off,
  and records `PROVENANCE.json` (version, provider, model, effort, subject
  hash, duration, exit code, page and sidecar counts) and `run.log`. The
  artefact is `openwiki/` (pages, `.claims/` sidecars, `.page-manifest.json`)
  plus the `AGENTS.md` OpenWiki writes.
  - **Provider and model.** OpenWiki as shipped defaults to OpenAI
    `gpt-5.6-terra`, and its reasoning-effort knob exists only for the
    OpenAI gpt-5.6 family (`src/config/reasoning.ts`); Anthropic models run
    with no effort setting. The kit's agent was Opus 5 @ xhigh. Neither
    choice matches it exactly, so: **W is the tool as shipped**
    (`openai`, `gpt-5.6-terra`, `OPENWIKI_REASONING_EFFORT=xhigh`) when an
    OpenAI key is available; **W-A** (`anthropic`, `claude-opus-5`, effort
    unsupported) when an Anthropic key is; both when both are. The model
    confound is named here and carried into every conclusion: a difference
    between W and K is a difference between two pipelines on two models,
    never attributed to the pipeline alone.
  - **Not given to OpenWiki:** `HARNESS_INTERFACE.md`, the kit, the hidden
    suite, J-F's tests, docs or history. Nothing is added to
    `openwiki/INSTRUCTIONS.md`; the run is the default run.
- **Arm W-R, the rebuild from the wiki:** one fresh `general-purpose`
  agent, Opus 5 @ xhigh (the kit arms' recreator model), given the
  `openwiki/` directory and `AGENTS.md` of W (or W-A, one arm per wiki) plus
  `../kit/contracts/HARNESS_INTERFACE.md`, the interface the kit's reverse
  engineer was also given, so the harness can drive the build. The brief is
  `../harness/RECREATOR_PROMPT.md` with the kit paragraph replaced by a
  wiki paragraph and the three permitted acceptance-suite runs **removed**:
  the wiki ships no suite, and that absence is part of what is measured.
  Same clean-room rules (read only the wiki and the output directory, no
  network, `ASSUMPTIONS.md` and `READ.log` as measured outputs).

## 3. Measures

Tools are under `tools/`; worksheets are committed with their verdicts
under `results/<arm>/`, so every judgement is on the record.

| # | Measure | Instrument | Denominator |
|---|---|---|---|
| M1 | **Claim precision.** A seeded sample (seed 20261027, 150 claims or all when fewer) of W's Grounded Claims, each verified against the clean room by reading the cited evidence and the symbol it names: TRUE, FALSE, PARTIAL (true with a wrong condition, number or name), UNVERIFIABLE (not decidable from the tree). Strict = TRUE / graded; lenient = (TRUE + PARTIAL) / graded; graded excludes UNVERIFIABLE. | `claims_worksheet.py`, `claims_tally.py` | sampled claims |
| M2 | **Coverage.** Each of the kit's 163 requirements mapped onto the wiki: FULL (condition and outcome stated), PARTIAL, NONE, with the page or claim that states it. By kind. The grader reads the wiki only. Reported beside round 1's own coverage of the same 163 (158 of 163 by construction: the five added after round 1 are named in `../kit/CHANGES.md`). | `coverage_worksheet.py`, `coverage_tally.py` | 163 |
| M3 | **Inverse coverage.** Among the M1 sample's TRUE claims, those whose content no kit requirement or contract states (a column `in_kit` on the claims worksheet: YES, NO). What the wiki knows that the kit does not, with the kind of fact (structure, naming, behaviour, configuration). | the M1 worksheet | TRUE claims in the sample |
| M4 | **Defects surfaced.** The six J-F issues the kit's rounds filed (#304–#309): for each, whether the wiki states the behaviour as a fact, flags it as an anomaly, or says nothing. | hand table | 6 |
| M5 | **Quirks stated.** The handover's 12 known quirks: stated, flagged, absent. | hand table | 12 |
| M6 | **What the machine checks prove.** An inventory, per arm, of every automated check and the property it establishes: for the kit, the 258 cases against the original (behaviour), the DMN gap/overlap/typing checks (completeness of the decision logic), `trace` (every requirement realised and verified), the glossary check, the manifest; for the wiki, claim evidence hashes (the cited lines are unchanged: staleness, not truth), front-matter, link and Mermaid validation (well-formedness), the `--update` run. Qualitative; no score. | hand table | — |
| M7 | **Rebuild sufficiency.** W-R graded exactly as the kit arms were: the hidden acceptance suite (258 cases) on W-R's build, the harness differential against the frozen reference (`../harness/run_arm.sh`: seam frame cell for cell, M8 and M9 of the first pre-registration), `ASSUMPTIONS.md` count, `READ.log`. Comparator: the kit arms (K, K−UML, K2 at round 1: 178/178 after revision; K2 third rebuild 197/197 first time; the outside rebuild 246/246 non-chain first time). | `../hidden/run_suite.sh`, `../harness/run_arm.sh` | 258 cases; reference cells |
| M8 | **Cost.** W's wall-clock duration and, where the run log carries them, tokens; the kit's round 1 was 88 minutes and 169 tool calls. | `PROVENANCE.json`, `run.log` | — |
| M9 | **Drift detection** (optional, needs a second owner run). The two Phase 1 mutants applied to a copy of the clean room (`../hidden/MUTANTS.md`: m1 bar fetch moved before the actions refresh; m2 crypto end-guard removed), then `openwiki --update`: claims reported stale, pages rewritten. Comparator: the kit's suite fails 2 and 11 cases. | `run.log` of the update | 2 mutants |

## 4. Expectations, written before the artefact

- **H1 (accuracy).** Strict precision at or above 0.85 and lenient at or
  above 0.95: the claims are written from the code with line evidence, so
  the failure mode is a wrong condition or number, not invention.
- **H2 (coverage).** Strict coverage below 0.40 and lenient below 0.60 of
  the 163; lowest for the `refusal` and `arithmetic` kinds, highest for
  `contract` and `cli`. A wiki describes what the code is for and how it
  is organised; the kit's requirements are boundary behaviours, message
  strings and exit codes, which a page summarises away.
- **H3 (defects).** At most one of the six issues flagged as an anomaly;
  at most three described as behaviour. Documentation generated from code
  explains the code as written; it has no oracle to disagree with it. The
  kit found the six by running the original against its own statements.
- **H4 (quirks).** At most four of the twelve quirks stated. The ones
  visible in a docstring or a comment (the seconds-not-milliseconds
  timestamp, the row-count-with-duplicates) are the likely ones; the
  clock split and the inverted-window short-circuit need execution.
- **H5 (sufficiency).** W-R passes fewer than 70 % of the 258 cases and
  differs from the reference in at least one seam-frame cell. The kit
  arms passed cell for cell with the suite in hand; a rebuild from prose
  and claims, with no suite to run, reproduces structure and loses
  arithmetic order, message bytes and exit codes.
- **H6 (machine checks).** No wiki check proves a behavioural property.
  The evidence hash proves the cited lines are unchanged; it says nothing
  about whether the statement about them was ever true. This is T-0800 in
  the wiki's own terms, and it is the one expectation that follows from
  the design, not from a guess.
- **H7 (drift, if run).** m2 edits a guard a claim is likely to cite and
  is flagged stale; m1 reorders two calls without changing any cited
  line's content and is not flagged. Staleness detection sees edits, not
  behaviour.
- **What would surprise.** Strict precision below 0.70 (grounding does
  not keep the statements honest); strict coverage above 0.60 (the wiki
  reaches boundary behaviour); W-R above 90 % (prose plus claims suffice
  for a cell-exact rebuild, and the kit's suite is a convenience, not the
  substance). Any of these is reported as the headline.

## 5. Procedure and order

1. This file committed and its commit recorded in Results before any run.
2. Clean room built (`make_clean_room.py`), hash checked against §2.
3. Arm W (and W-A when a second key exists) generated by
   `run_openwiki.sh`; `openwiki/`, `AGENTS.md`, `run.log`, `PROVENANCE.json`
   committed under `results/W/` (or `results/W-A/`) **unread**.
4. W-R launched from the committed wiki before the grader reads the wiki
   beyond its index: the grader's reading cannot leak into the rebuild.
5. M1 worksheet generated and graded; verdicts committed. Then M2, M3,
   M4, M5, M6 in that order; each worksheet committed before the next
   starts.
6. W-R graded (M7); M8 from the provenance; M9 if the owner runs the
   update.
7. Results appended here; the record (`docs/recreate-experiment.md`) gets
   its dated section; the ROADMAP research-track bullet its annotation.

## 6. Bounds and confounds, stated in advance

- **Model.** W and K run on different models and effort settings (§2);
  W-R runs on the kit arms' model. Every difference is pipeline × model.
- **Rounds.** K is four rounds of revision; W is one run. Round-1 figures
  are reported beside K's wherever a measure depends on it (M2, M7, M8).
- **Grader.** This session graded the kit's rounds and knows the subject;
  the M1 and M2 worksheets record every verdict with the symbol read, so
  a second reader can re-grade. A sample of 20 rows per worksheet is
  offered to the maintainer for an independent check.
- **Scope.** Nothing here measures what OpenWiki is built for: whether a
  coding agent working *on the repository* is faster or better with the
  wiki in context. OpenWiki's own `evals/deepswe` harness measures that,
  against DeepSWE tasks; this experiment measures the artefact, not the
  agent that consumes it.
- **Execution.** This session cannot run OpenWiki: no model credential is
  present in the environment, and the run belongs to the owner (a key in
  the environment's secrets for a later session, or a local run with the
  paste block given in chat). Nothing in Results is estimated or mocked;
  until the artefact lands, Results holds only step 1.

## Results

*(appended as the steps complete; nothing above this line changes)*

### Step 1 — frozen 2026-10-27

- Pre-registration frozen at pumllint `5337265` (PR #195, squash-merged
  on a green matrix); sha256 of this file at that commit, above this
  Results section unchanged since: `cf7df94a…9aae` (full value:
  `cf7df94a797fe3c26fb571d7a8b88e80fb0a651526f9b267232a1f22bdfc9aae`).
- The clean room was built once here as a tooling check
  (`make_clean_room.py` over J-F `8f6d6b0`): 23 files, subject tree
  sha256 `535982e6…` as §2 states. No OpenWiki run: no model credential in
  this environment. The owner was given the two routes (a key in the
  environment's secrets for a later session, or the local paste block).
