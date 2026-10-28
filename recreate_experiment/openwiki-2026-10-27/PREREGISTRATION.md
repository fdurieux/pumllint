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

### Step 2 — 2026-10-28

- Clean room rebuilt from J-F `8f6d6b0` (`/home/user/j-f`, a fresh clone)
  for each run; `make_clean_room.py` printed 23 files, subject tree sha256
  `535982e6…` each time, and every room's git tree is `1619e2f2…`.
  `run_openwiki.sh`'s own `subject_tree_sha256` (`436624d7…`) is a
  different formula over the same files (`sha256sum` lines of
  `git ls-files`), not a different tree.

### Step 3 — Arm W generated 2026-10-28; W-A not run

- **Credentials.** `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` both unset.
  The environment's proxy injects an OpenAI key for `api.openai.com`
  (`GET /v1/models` 200 with a dummy bearer, 134 models, `gpt-5.6-terra`
  listed); `api.anthropic.com` bypasses the proxy and answers 401 with no
  key. **W possible, W-A not:** no Anthropic key. W ran with
  `OPENAI_API_KEY=sk-proxy` (a placeholder the proxy replaces) and
  `ANTHROPIC_API_KEY` unset, so `run_openwiki.sh` saw exactly one
  credential.
- **Environment.** Node's built-in `fetch` ignores `HTTPS_PROXY` unless
  `NODE_USE_ENV_PROXY=1`; the runs set it. OpenWiki 0.7.2 installed with
  `npm install -g openwiki@0.7.2` (`deepagents` 1.13.2).
- **Tool fixes before the run counted** (`tools/run_openwiki.sh`): the
  pinned-version check read `openwiki --version`, which 0.7.2 does not
  have; it now reads the installed `package.json`. A page-less run lost
  `PROVENANCE.json` (`pipefail` over `find` on a missing `.claims/`); the
  sidecar count now runs only when the directory exists.
- **Attempt 1 failed** (09:38, 396 s, exit 1, no page): kept as written in
  `results/W-attempt1-failed/`. Page 1's first worker attempt got `502
  upstream request failed` from the session proxy, which cuts any
  request with no response byte within 30 s (a bare non-streaming
  `POST /v1/responses` at `xhigh` fails at 30.4 s; the same request with
  `stream: true` returns 200 after 128 s). OpenWiki sends provider `openai`
  non-streaming. Its pre-retry restore then aborted the run on ENOENT,
  hiding the 502: OpenWiki defects D1 and D2, in
  `results/W-attempt1-failed/OPENWIKI_DEFECTS.md`. A diagnostic copy that
  logged the swallowed error was run once in a throwaway room; its wiki
  was not read and is not a result.
- **Deviation from §2, chosen by the owner 2026-10-28.** W is not quite
  "the tool as shipped": one line of `dist/config/constants.js` makes
  `providerUsesStreaming` true for provider `openai`
  (`tools/openwiki-0.7.2-stream-openai.patch`; file sha256 `6bc886cb…`
  pristine, `9cac4d1b…` patched). Provider, model, Responses API,
  reasoning effort, tools, prompts and page concurrency are unchanged;
  only the transport streams. The alternatives were rejected: the
  `openai-compatible` route also turns off strict tool calling, and a
  local owner run would have deferred the arm.
- **Arm W, run 2** (09:58:59–10:23:14 UTC, **1455 s**, exit 0): `openai`,
  `gpt-5.6-terra`, `xhigh`, page concurrency 1, telemetry off. **16 pages**
  (9 content pages and 7 indexes: the root and six sections) and **9
  claim sidecars**; `.page-manifest.json`, `AGENTS.md`. OpenWiki also wrote
  `.github/workflows/openwiki-update.yml` into the subject (its scheduled
  `--update` workflow, outside §2's artefact), copied to
  `results/W/room-extras/`. Committed **unread** under `results/W/`;
  `MANIFEST.sha256` (32 files) sha256 `60529e10…`. Nothing in the wiki
  has been read; the only thing looked at was the run's progress, as a
  count of page files.

### Step 4 — W-R launched 2026-10-28, before any grading

- Launched about 10:32 UTC, after #198 merged and before anyone read the
  wiki beyond the page count. **One arm only** (W); W-A does not exist.
- **Inputs.** The recreator's wiki directory holds `openwiki/` and
  `AGENTS.md` extracted with `git archive` from the commit that carries
  `results/W/` (byte-identical to it, 29 files counting
  `HARNESS_INTERFACE.md`), plus `../kit/contracts/HARNESS_INTERFACE.md`.
  Its output directory starts with only `events.sh` and `dashboard.sh`
  from J-F `8f6d6b0`. Its venv is Python 3.12 with the three exact pins
  and `setuptools`, as the kit arms had.
- **Brief.** `tools/WR_RECREATOR_PROMPT.md` with `{WIKI}`, `{VENV}` and
  `{OUT}` filled in; sha256 of the text sent:
  `736a0fdb707d9d33…`. Nothing else is in the prompt.
- **Recreator.** A fresh `general-purpose` agent, the Agent tool's `opus`
  alias at effort `xhigh`. §2 names the kit arms' model. The alias
  resolves to whichever Opus model the session serves, so the recreator
  may not be the exact model the kit arms ran on. That confound is
  carried into M7 beside the §6 model bound.
- **Correction, 2026-10-28.** "As the kit arms had" above is wrong. The
  kit arms' venvs carried the data lane's pins: pandas, numpy,
  `requests==2.34.2` and `pyarrow==25.0.1` (J-F's `[data]` extra; kit
  `contracts/pins.md`). W-R's venv was built from the clean room's
  reduced `pyproject.toml`, which carries `[project].dependencies` only
  (pandas, numpy, scikit-learn), so it had neither `requests` nor
  `pyarrow`. The full list is in `results/W-R/VENV.pip-list.txt`. M7 has to
  carry this beside the model bound.

### Step 4 — W-R finished 2026-10-28, committed ungraded

- 10:32 → 11:05 UTC: **1970 s**, 80 tool calls, 378 931 tokens.
  Committed as written under `results/W-R/`, nothing graded and nothing
  run against the reference:
  - `rc/` is the build: `pyproject.toml`, the `jef_data_rc` package (18
    files, laid out after the wiki's `src/jef/data`), `adapter_rc.py`,
    `daily-rc.sh`, **`ASSUMPTIONS.md` (117 entries)** and `READ.log` (34
    paths);
  - `PROMPT.sent.txt` is the brief as sent (`736a0fdb…`);
  - `VENV.pip-list.txt` lists the venv;
  - `MANIFEST.sha256` covers 91 files (sha256 `be49fb84…`).
- **Reading rule.** All 34 `READ.log` paths are under the wiki or the
  output directory.
- **Disclosed deviation.** The agent reported writing a test shim outside
  `{OUT}` (`testshim-outside-out/`): a pickle-backed stand-in for
  `pyarrow` and its own fixtures. It read those files to test its build
  without the missing module; they hold nothing from the subject. They
  are committed as found, and `READ.log` does not list them. It installed
  nothing, and its `pyproject.toml` declares pandas, numpy and
  scikit-learn unversioned: "the wiki gives no versions".
- **What it says it could not test.** Every store-opening command fails
  in its venv with `ModuleNotFoundError: pyarrow`, and nothing was run
  against real Parquet. That follows from the venv correction above, not
  only from the wiki.
- **Owner decision, 2026-10-28: grade both.** W-R1 (above) is kept as an
  arm. A second rebuild, **W-R2**, runs the same brief over the same wiki
  in a venv carrying the kit arms' pins, and M7 grades both. That gives
  two samples of rebuild-from-wiki and a direct reading of what the
  missing pins cost W-R1. W-R2 was launched about 11:11 UTC, the wiki
  still unread:
  - **Wiki:** a byte-identical copy of W-R1's, checked against
    `results/W/` and `../kit/contracts/HARNESS_INTERFACE.md`.
  - **Output directory:** starts with the two externals from J-F
    `8f6d6b0`.
  - **Venv:** Python 3.12 with pandas 3.0.5, numpy 2.4.6, scikit-learn
    1.9.0, `requests==2.34.2`, `pyarrow==25.0.1` and setuptools. That is
    the kit's `contracts/pins.md` plus the clean room's scikit-learn, a
    superset of both arms' environments.
  - **Brief:** identical to W-R1's apart from the directory name; sha256
    of the text sent `1446203917d35cbb…`.
  - **Recreator:** a fresh `general-purpose` agent, the `opus` alias at
    `xhigh`, as for W-R1.

### Step 4 — W-R2 finished 2026-10-28, committed ungraded

- 11:11 → 11:40 UTC: **1688 s**, 68 tool calls, 347 951 tokens.
  Committed as written under `results/W-R2/`, nothing graded and nothing
  run against the reference:
  - `rc/` is the build: the `jef_data_rc` package laid out after the
    wiki's `src/jef/data`, `adapter_rc.py`, `daily-rc.sh`,
    **`ASSUMPTIONS.md` (94 entries, A0–A93)** and `READ.log` (37 paths);
  - `PROMPT.sent.txt` (`1446203917d35cbb…`), `VENV.pip-list.txt`;
  - `MANIFEST.sha256` covers 94 files (sha256 `dd15fa9a…`).
- **Reading rule.** 31 `READ.log` paths are under the wiki or the output
  directory. 6 are the agent's own test outputs in `wr-W2/scratch/`,
  outside `{OUT}`; those files hold nothing from the subject and are kept
  as found in `scratch-outside-out/`. Disclosed, like W-R1's shim.
- **Disclosed, and a datum for M6.** The `.claims` sidecars carry sha256
  hashes of the cited source lines. The agent noted that these could be
  brute-forced to recover source text. It checked the hash format once,
  against a line the wiki already quotes (`set -euo pipefail`), and then
  deliberately did not use them (A0). So a grounded claim's evidence
  hash is not only "staleness, not truth" (H6): for a short or guessable
  line it is a partial disclosure of the source. M6 records this.
- Its `pyproject.toml` again declares pandas, numpy and scikit-learn
  unversioned ("the wiki gives no version pins"). In its venv pandas 3
  imports `pyarrow` itself; the package imports neither `pyarrow` nor
  `requests` at package level.

### Step 5 — M1 worksheet, 2026-10-28

- **Size.** W has **128 Grounded Claims on 9 pages**, all with evidence.
  That is fewer than the 150 §3 names, so M1 grades every claim; the seed
  selects nothing.
- **Shown to the owner ungraded before any verdict**, at the owner's
  request. Two owner decisions followed, recorded here before grading:
  - **Compound claims.** OpenWiki's claims are not atomic: one packs
    about ten checks. One verdict per claim stays the headline, as §3
    registers it: TRUE only if every part holds; PARTIAL if a part has a
    wrong condition, number or name; FALSE if a part is contradicted or
    invented. Each row also records `parts` (its sub-assertions) and
    `failed` (how many do not hold). The part-level precision is a
    secondary figure, reported beside the registered ones, never in
    their place.
  - **`in_kit`.** M3's column, which `claims_worksheet.py` did not write,
    is added as a tool fix: YES or NO on TRUE rows only.
- **Tool changes**, the same commit as the blank worksheet:
  - `claims_worksheet.py` writes `parts`, `failed` and `in_kit`.
  - `claims_tally.py` refuses an inconsistent row: TRUE with failed
    parts, FALSE or PARTIAL with none, `in_kit` missing on TRUE or
    present elsewhere. It prints the part-level figure and M3's count.
    Both behaviours were checked on a synthetic filled copy before
    commit.
- The worksheet is committed **blank** at `results/W/m1/`, with
  `claims.all.json` and `claims.sample.json` (identical here, since all
  claims are graded). The verdicts follow in their own commit.

### M1 — claim precision, graded 2026-10-28

- **Grader:** this session (§6 bound), against the clean-room tree
  (`make_clean_room.py` output, git tree `1619e2f2…`). Every source file
  was read in full before any verdict. Each row's `note` names the
  symbols read. A source-level claim about the clean room (claim 115,
  "no test files") is graded against that tree.
- **Result:** TRUE 127, PARTIAL 1, FALSE 0, UNVERIFIABLE 0 of 128.
  - **Strict precision 127/128 = 0.992**, **lenient 128/128 = 1.000**:
    **H1 held**, both thresholds exceeded.
  - **Part-level** (secondary figure): 426 of 427 sub-assertions hold
    (0.998), 3.34 per claim, up to 13 in one claim.
  - **The one PARTIAL is claim 13.** It credits `BaseCollector` with the
    replay and recording transports, which are separate classes in the
    same module.
- **Wording looseness graded TRUE, so a re-grader can disagree:**
  - 23: an all-unparseable `Date` column is an error, not a note;
  - 49: "no verdict" is the code's own phrase for `unmapped`;
  - 86: "the configured number" of refresh sessions is a
    `check_source` parameter that the CLI never exposes (J-F #307, kit
    JDL-125 "fixed");
  - 119: "warns" means a detail clause;
  - 120: the stamp is checked on every run and refreshed once per UTC day.
- **`in_kit` rule.** NO when at least one part of a TRUE claim is stated
  in no kit requirement and no kit contract. That covers
  `requirements.json` and `contracts/`, including the shipped verbatim
  externals and `universe.toml`; diagrams and features are excluded.
  Every NO was checked by searching the kit for the fact.
- **Result: 18 of 127 TRUE claims are not in the kit:** 1, 2, 3, 4, 7, 9,
  42, 43, 47, 52, 70, 80, 81, 92, 103, 112, 115, 127. By kind:
  - **structure** (9): packaging and package-root surface, `python -m`,
    the lazy imports, the injection seams;
  - **behaviour** (6): `modeled_source()`'s implicit choice and its
    relation to sync, a class correction not being a migration,
    non-transactional publish, no cross-file transaction;
  - **configuration** (2): the reduced `pyproject` dependencies, the
    EventBridge/CloudWatch placement;
  - **repository** (1): no checked-in tests.

  This is M3's datum; its write-up follows M2, in §5's order.
- **Independent check.** 20 rows, seeded (20261027) over the 128, are
  offered to the maintainer for a re-grade: 7, 8, 11, 13, 21, 26, 34, 40,
  45, 49, 52, 54, 59, 60, 66, 99, 105, 108, 111, 127.

### M2 — coverage, graded 2026-10-28

- **Grader:** this session (§6 bound), from the wiki alone. That means
  the nine content pages and the 128 claims, never the clean room or the
  kit's contracts. Each row's `page` cell names the page and section
  that states it. Page initials: Q quickstart, A architecture, E the EOD
  data model, U universe and classification, C collectors, D the daily
  run, H store health, T testing and replay, W universe sync.
- **Rule, strict, fixed before the first verdict:**
  - FULL = the requirement's condition and its outcome are both stated.
  - PARTIAL = the behaviour is stated but a part the requirement pins is
    missing: an exact message or identifier string, a default, an
    explicit edge case, an order.
  - NONE = not stated, or contradicted.
- **Result:** FULL 40, PARTIAL 111, NONE 12 of 163.
  - **Strict coverage 40/163 = 0.245.** **Lenient 151/163 = 0.926.**

  | kind | FULL | PARTIAL | NONE | n | strict | round 1 |
  |---|---|---|---|---|---|---|
  | arithmetic | 13 | 8 | 1 | 22 | 0.59 | 22/22 |
  | chain | 7 | 6 | 0 | 13 | 0.54 | 13/13 |
  | contract | 11 | 35 | 2 | 48 | 0.23 | 48/48 |
  | ritual | 6 | 21 | 0 | 27 | 0.22 | 27/27 |
  | cli | 2 | 14 | 4 | 20 | 0.10 | 17/20 |
  | verdict | 1 | 11 | 0 | 12 | 0.08 | 12/12 |
  | refusal | 0 | 16 | 5 | 21 | 0.00 | 19/21 |
  | all | 40 | 111 | 12 | 163 | 0.245 | 158/163 = 0.969 |

  Round 1 states its own 158 by construction. The five it lacks are
  JDL-159..163 (`../kit/CHANGES.md`): the absent-series tracebacks, the
  argparse surface, parse errors, `--help`. The wiki states none of the
  five either.
- **H2 split:**
  - **The strict threshold held** (0.245 < 0.40).
  - **The lenient threshold failed** (0.926, against a prediction below
    0.60). The wiki names nearly every behaviour, but it does not pin
    one. 58 of the 111 PARTIAL notes name a missing message, format or
    output string. The rest miss a default, an edge case or an order.
  - **The kind ordering came out half right:**
    - `refusal` is lowest, as predicted: no refusal is FULL, because none
      of its messages is quoted.
    - `arithmetic` is highest, against the prediction: the adjustment
      factor, the calendar, the crypto end cap and the Binance pagination
      are written out exactly.
    - `cli` is fifth of seven, against the prediction: the subcommands
      are listed, but their output and parse-error behaviour are not.
- **Contradictions, graded NONE, plus one PARTIAL:**
  - 060: the wiki gives bar `timestamp` as Unix milliseconds; the kit
    pins seconds.
  - 043: the testing page says action saves take `now`; the kit says the
    run clock never reaches the stamp.
  - 127 (PARTIAL): the wiki says `common_session` is kept on a zero mid;
    the code leaves it null.

  These are M4's input. Neither M1 grade moves, because neither sentence
  is a Grounded Claim.
- **Independent check:** 20 rows, seeded (20261027) over the 163, are
  offered to the maintainer for a re-grade: 7, 8, 11, 13, 21, 26, 34, 40,
  49, 54, 59, 60, 66, 99, 105, 108, 111, 127, 142, 154.

### M3 — inverse coverage, written up 2026-10-28

- **Datum:** the M1 worksheet's `in_kit` column (graded with M1). 18 of
  the 127 TRUE claims are `NO`. The write-up is
  `results/W/m3/inverse-coverage.md`.
- **18 claims, 13 facts.** The wiki restates a fact on more than one
  page; the quickstart repeats the architecture page.
- **By kind, claims (facts):** structure 9 (6), behaviour 6 (4),
  configuration 2 (2), repository 1 (1), naming 0.
  - `repository` is not a pre-registered kind. It was added at grading
    for claim 115, which describes the checkout, not the code.
- **By the origin of the gap:**
  - **3 facts (claims 1, 4, 80, 115) are clean-room artefacts.** They are
    true of the subject tree that `make_clean_room.py` builds, not of
    J-F: the `jef.data*` package include, the dependency list without
    extras, the missing tests. The wiki read the subject faithfully; the
    gap is the experiment's construction.
  - **3 facts (claims 47, 70, 127) are undrawn consequences** of
    requirements the kit states:
    - a class correction is not a migration (JDL-065);
    - the final uploads are not a transaction (JDL-158);
    - there is no cross-file atomicity (JDL-058, JDL-042).
  - **7 facts are code the kit leaves out by scope.** These are the
    package-root surface, `python -m`, lazy imports, the injection seams,
    the storage-seam docstring and the EventBridge placement comment.
    Two of them, `modeled_source` and `validate_or_raise`, are on the kit
    author's own "Unused code" list (`../hidden/NOTES.md`). No kit
    scenario, adapter or harness step reaches any of the seven.
- **Reading:** no fact the wiki adds is a CLI-observable behaviour that
  the kit gets wrong or leaves undecided.
  - **What the wiki adds:** what a maintainer of the package wants
    (shape, seams, deployment placement) and three failure-mode
    inferences.
  - **What the kit holds instead:** what a rebuild must reproduce. M2
    measured how much of that the wiki pins: 40 of 163.
  - **So the two artefacts overlap less than either covers.** The wiki's
    share outside the kit (18 of 127 TRUE claims, 0.14) is small, and
    none of it is boundary behaviour.
- No hypothesis was registered for M3; it is descriptive.
