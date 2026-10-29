# Degrading the kit: a pre-registered test of the systemic model's cascade

*Frozen before any defect is selected or planted, and before any rebuild.
Opened 2026-10-28 on the maintainer's go: "all six arms, rebuilds at
xhigh". Origin: the Legible model review
(`../legible-model-review-2026-10-28/REVIEW.md`, open question 2), which
found the model's cascade (v0.2) observational on this experiment's
evidence and proposed an intervention. Subject, kit, harness and reference
are this directory's parent's, unchanged.*

## 1. Question

When a defect is planted in one layer of a specification kit, does it
reach the code an independent agent rebuilds from that kit? Which layer's
defects propagate, which are attenuated, which are concealed, and what
does each gate see before any rebuild? Two readings of the Legible model
make different predictions (§7):

- **as drawn** (v0.2): derived-artefact defects propagate to code when
  consumed (E50, E51); independent tests detect (E54, E57); tests that
  share a wrong premise conceal (E52, E53, E69). There is no edge from a
  wrong test to the code, and no distinction between artefact roles.
- **as corrected** (REVIEW.md F1–F7): attenuation by load-bearing role
  (F3); a green gate over a defective artefact (F4); omission answered by
  invention, recorded as assumptions (F5); oracle calibration as an
  interruption point (F7). Added here, because a rebuild iterates its code
  to the suite: a wrong test pulls the code with it (`testdef → codedef`,
  +, condition "the suite is the build target").

## 2. Kit layers

The kit at `../kit/` (manifest 207 files), as the precedence rule in its
README orders them:

| layer | files |
|---|---|
| L1 suite | `features/**` (scenarios, step glue, fixtures, expected frames) |
| L2 requirements | `requirements.json` |
| L3 contracts | `contracts/*.md`, the JSON Schemas, the packaged TOML files, `CHANGES.md` |
| L4 decisions and vocabulary | `contracts/dmn/**`, `contracts/glossary.md` |
| L5 diagrams | `uml/**` |

`README.md`, `features/README.md`, `pumllint.toml`, `tools/` and
`contracts/externals/` are never edited, and neither is
`HARNESS_INTERFACE.md`. `MANIFEST.sha256` is regenerated with the kit's
own `tools/manifest.py` after every plant, so every kit verifies.

## 3. Arms

Six rebuilds, one fresh agent each:

| arm | planted in | defects |
|---|---|---|
| C | nothing (the kit as committed) | none; today's baseline |
| D1 | L5 only | one W, one M, one A |
| D2 | L2, L3 and L4; L1 and L5 intact | one W, one M, one A |
| D3 | every layer that states the value, consistently | three W |
| D4 | L1 only | one W, one M, one A |
| D5 | every layer that states the clause, consistently | three M |

D3 plants wrong values only: a consistent omission is D5's, and an
ambiguity cannot be consistent with a scenario that pins the value.

## 4. Defects

**Types.**

- **W, a wrong value.** The requirement pins a value: a number, an exit
  code, a literal the program emits or compares (message text, key, flag
  default), or an enumeration member. Every mention of that value in the
  targeted layers is replaced by one alternative of the same type. A
  number stays in the same order of magnitude; a string stays fluent. The
  alternative collides with no other value that the same statement,
  table or scenario pins.
- **M, a missing rule.** One clause of a requirement with more than one
  clause is deleted from every targeted layer, condition and outcome
  together. A clause is a condition with its outcome: "when/if/while …
  shall …", an "unless …", or a sentence of that shape. A DMN row
  carrying the clause is deleted; the input domain is left as written. A
  scenario or Examples row exercising only the clause is deleted, and so
  is a fixture used only by it. No requirement id is removed or
  renumbered, so the id inventory and the trace gate are untouched.
- **A, an ambiguous wording.** A pinned value or precise condition is
  reworded so that it admits at least two readings, the original among
  them. In L1 this means an assertion loosened so that both readings pass
  it.

**The mutant.** Each defect is paired with a mutant of the original, made
in a copy of J-F's `src/jef/data` that is never installed over the
subject:

- W: the wrong value;
- M: the clause's behaviour removed, its absence read literally (the
  condition no longer tested, its outcome never produced);
- A: the alternative reading.

The mutant's **observing set** is the set of harness artefacts where the
mutant's run differs from the reference.

**Admissibility, tested in this order; every rejection logged with its
test and one line of reason:**

- **T1, type fit** — judgement, per the definitions above.
- **T2, layer fit** — mechanical. The value or clause text appears in:
  - D1: ≥ 1 `uml/*.puml`;
  - D2: `requirements.json` and ≥ 1 L3 file;
  - D3 and D5: `requirements.json` and ≥ 1 L1 file;
  - D4: ≥ 1 L1 file.
- **T3, observed by both observers.**
  - The observing set has ≥ 1 artefact, and all of them are among the 146
    artefacts that Arm K2 reproduced byte-identically
    (`../results/K2/compare.json`).
  - The pristine kit's suite fails ≥ 1 scenario on the mutant.
- **T4, disjoint** — the observing set shares no artefact with an earlier
  accepted defect of the same arm.

**Selection.**

- **Order.** Requirement ids are ordered by
  `sha256("20261028:" + id)`, hex ascending, a total order anyone can
  recompute.
- **Slots,** filled in this order: D1-W, D1-M, D1-A, D2-W, D2-M, D2-A,
  D3-W1, D3-W2, D3-W3, D4-W, D4-M, D4-A, D5-M1, D5-M2, D5-M3.
- **Walk.** Each slot walks the order from the top and takes the first
  requirement passing T1–T4. A requirement serves one slot at most. A
  slot no requirement can fill is reported empty, and its arm runs with
  fewer defects.

**Consistency checks, before any rebuild (V):**

- **V1.** Each kit's diff against the pristine kit touches only the arm's
  permitted layers.
- **V2.** D1's and D2's suites are untouched and pass on the original.
- **V3.** D3's suite passes in full on the combined three-W mutant and
  fails on the original.
- **V4.** D4's suite passes in full on its W mutant and fails on the
  original. Its A edit passes both the original and the A mutant.
- **V5.** D5's suite passes in full on the original and on the combined
  absence mutant.

A plant that fails V is repaired before any rebuild; the repair is logged.

**Hidden until grading.** The plant bundle holds the selection walk, the
edits as patches against the pristine kit, the mutants as patches against
J-F `8f6d6b0`, the observing sets and the V results. Its sha256 is pushed
to this repository before the first rebuild launches. The bundle itself
is committed at grading and must match that hash.

## 5. Procedure

1. **Freeze.** This file, by PR, merged on a green matrix.
2. **Plant.**
   - Walk the order, build and validate each defect's mutant, plant the
     edits, regenerate each kit's manifest and run V.
   - Run the gate readouts on each kit: lint at `--fail-on info`;
     `score --min-level 5`; `trace` with `--features --fail-on-uncovered
     --fail-on-unverified`; `../harness/dmn_check.py`;
     `../harness/glossary_check.py`; and calibration, the kit's suite on
     the original.
   - Push the bundle hash.
3. **Isolate.** For the rebuild window, the following leave the container
   as an encrypted archive, restored after the six agents report: the
   subject clone, its venv, the reference runs, the hidden inputs, the
   lab with the bundle, and both repository clones. Prior arms relied on
   the brief and a read log; this is new.
4. **Rebuild.**
   - Each kit sits outside every repository, in its own randomly named
     directory, with its own Python 3.12 venv seeded with pip and
     setuptools and carrying the pins of `contracts/pins.md`, pytest and
     pytest-bdd 9.0.0. The two given externals are placed beside the
     output directory.
   - Six fresh `general-purpose` agents, model alias `opus`, effort
     `xhigh`, are launched in parallel. The brief is
     `../harness/RECREATOR_PROMPT.md` verbatim with `{KIT}`, `{VENV}` and
     `{OUT}` filled in, and nothing else is in the prompt. k ≤ 3 suite
     runs.
5. **Grade, on one UTC date.**
   - Re-run the reference. 152 of its 157 artefacts must match
     `../harness/REFERENCE.MANIFEST.sha256.json`; the other five carry the
     wall clock or a path and are compared within the day. Re-run each
     mutant the same day.
   - Then, per arm: `../harness/run_impl.py` and `compare.py` against the
     reference; M8 through the original loader; the arm's own kit suite;
     the pristine kit suite; per-defect outcomes; assumptions and reads.

## 6. Measures

| id | measure |
|---|---|
| G1–G6 | per degraded kit, before any rebuild: lint, score, trace, `dmn_check`, `glossary_check` (each green or red, with what it names), calibration (pass / total on the original) |
| R1 | the rebuilder's suite runs (pass / total each, runs used) |
| R2 | M1–M7 as `compare.py` computes them against the reference, and the non-identical set |
| R3 | M8, seam invariance through the original loader |
| R4 | the arm's own kit suite on the rebuild, our run |
| R5 | the pristine kit suite on the rebuild, our run |
| R6 | per defect, on its observing set: **ORIGINAL** (byte-identical to the reference), **PLANTED** (byte-identical to the mutant), **OTHER** (neither) |
| R7 | per defect, **FLAGGED**: an `ASSUMPTIONS.md` entry names its value, its clause, or the disagreement between two of the kit's documents about it |
| R8 | reads outside `{KIT}` and `{OUT}`, from `READ.log` and the agent's own report |
| R9 | cost: wall time, tool calls, tokens, as the Agent tool reports them |

Propagation, attenuation and concealment are read from R6 together with
R1 and R4: **concealed** means PLANTED with the arm's own suite green.

## 7. Expectations

| id | arm | as drawn | as corrected | pre-registered expectation |
|---|---|---|---|---|
| X1 | D1 | propagation where the diagram is consumed (E51) | attenuated by role (F3) | 0 of 3 PLANTED; refuted at ≥ 2 |
| X2 | D2 | detected by the independent suite (E57, E54) | same, by the suite's precedence | ≥ 2 of 3 ORIGINAL, ≥ 1 FLAGGED |
| X3 | D3 | concealed (E52, E53) | concealed; calibration interrupts (F7) | 3 of 3 PLANTED; R4 all pass; G6 red; G1–G5 green |
| X4 | D4 | no edge from tests to code: ORIGINAL | the suite pulls the code | W PLANTED and FLAGGED; M and A ORIGINAL; G6 red |
| X5 | D5 | invention lowers fidelity (E32) | invention, recorded (F5) | ≥ 2 of 3 not ORIGINAL; ≥ 1 FLAGGED; G3 green; G4 red where a deleted row leaves a finite-domain gap |
| X6 | C | — | — | M1–M6 at 100 %; the non-identical set within K2's eleven |
| X7 | all | — | a green gate over a defective kit (F4) | G1–G3 green on ≥ 4 of the 5 degraded kits; G5 green on all 5 |

Every expectation is reported held, split or failed, with the counts.
Which reading predicted better is tallied per arm, not pooled.

## 8. Bounds, stated in advance

- **Single runs.** n = 1 per arm and three defects per arm. Fifteen
  defects in all, one rebuild each.
- **Selection bias, by design.** Selection is restricted to behaviours
  both observers see. The experiment cannot speak to defects in
  behaviour no scenario or harness artefact reaches (the 141 statements
  of `../results/coverage/UNREALISED.md` among them).
- **The precedence rule is in every kit.** The kit's own precedence rule
  (README, revision 2026-10-24) is present in every arm, so outcomes
  measure a kit that declares which layer wins. An arm without it is not
  run.
- **One context plants and grades.** This session plants the defects,
  writes the mutants and grades. It is not a rebuilder. The pre-
  registration's author and the analyst are the same context, as in
  every earlier wave.
- **The model confound.** The `opus` alias resolves to the model this
  session serves, not to the Opus 5 the K arms ran on. C is the baseline
  for that.
- **Six agents at once.** Their kits are in separate random directories,
  but nothing mechanically stops one reading another's. The read log is
  the audit.
- **Not removable.** The network is not blocked. This session's own
  transcript stays on disk during the window.
- **Not run.** M9, the original's API-level tests, is not run: its
  failures are signature-level by construction and say nothing about a
  planted behaviour.

## Results

*(appended as the steps complete; nothing above this line changes)*

### The plant's hash (2026-10-29, before any rebuild)

The fifteen slots are filled and the five kits are planted; V1–V5 hold. The plant bundle (the walk, the
kit patches, the mutants, the observing sets, the V results and the gate readouts) stays hidden until
grading. Its hash, the sha256 of the `SHA256SUMS` that lists its 188 files:

`fbe131a5ddf251d90ffd96d067a6f4a53604a4d2fa2224408326c944e227f2c3`

The bundle is committed at grading and must reproduce this hash.

### Grading (2026-10-29)

*Graded on one UTC date by the session that planted (§8). The bundle is committed as `plant/`: its
`SHA256SUMS` hashes to the value above, and `sha256sum -c SHA256SUMS` passes on all 188 files. Per arm,
`results/<arm>/`: the rebuild as written (`rc/`), `compare.json`, `m8.txt`, the arm's own suite (`r4.txt`)
and the pristine suite (`r5.txt`), the agent's report verbatim, its usage, the run's manifest, and the
non-frame artefacts that differ (`diffs/`; each frame's difference is counted per column in
`compare.json`). Per defect, `results/r6.json`. The grading tools and their outputs, `results/grading/`.*

**The window** (UTC):

| when | what |
|---|---|
| 07:11–07:14 | 65 paths archived, encrypted (497 MB), verified, removed: the subject clone, its venv and the uv cache of its editable build; the pumllint clone and a third clone (`fdurieux.github.io`); the session's uploads; the lab (the bundle, the reference runs, the hidden inputs, the mutant trees) and every other scratch file |
| 07:17:34 | six agents launched in parallel, each brief §5.4's |
| 07:42:41–07:50:48 | the six reports, D3 first, D4 last |
| 08:18:16 | restored, 65 of 65 |
| 08:18–08:30 | graded |

**The isolation's bound, found at grading.** The vault emptied the disk, not the context. Each agent's
context carried the session's project instructions, both repositories' `CLAUDE.md` (48,732 characters),
from the session's cache after the clones had left. Read against the fifteen defects, it states one:
D2-M's dry run (`jef-data sync --dry-run` plans offline), which D2's kit also states, in the `--dry-run`
help that P2 kept. Its `--asset` lines are `jef-binning`'s and `jef fetch`'s, and "a source's `end` caps
every fetch" holds with or without the crypto guard. No verdict needs it to be explained.

**Reference and mutants, the same day.** The reference re-run matches 152 of the frozen manifest's 157;
the five that differ are the wall-clock and path artefacts of §5.5 (`s10_aapl_split/actions_AAPL.US.json`,
`s22_cli_surface/cli_dry_run_packaged.json`, `s23_cli_on_store/cli_status_json_now.json` and
`cli_status_table.json`, `s24_chain/chain_no_bucket.json`), compared within the day. The fifteen accepted
mutants, the two combined ones and the two null baselines were re-run: each accepted mutant still differs
from the day's reference on its whole observing set; null (an unmodified copy) reproduces 154 of 157 and
nullc 153, the three traceback-path artefacts and `chain_no_bucket`, none of them in any observing set.

**Per arm** (R1–R5, R9):

| arm | R1 runs | R2 identical | outside K2's eleven | R3 M8 | R4 own suite | R5 pristine suite | R9 wall, calls, tokens |
|---|---|---|---|---|---|---|---|
| C | 258/258, 258/258 | 147/157 | 0 | pass | 258/258 | 258/258 | 31.3 min, 90, 555,407 |
| D1 | 258/258, 258/258 | 147/157 | 0 | pass | 258/258 | 258/258 | 32.8 min, 76, 527,665 |
| D2 | 258/258, 258/258 | 147/157 | 0 | pass | 258/258 | 258/258 | 32.2 min, 89, 536,140 |
| D3 | 258/258, 258/258 | 124/157 | 23 | **fail** (Volume) | 258/258 | **241/258** | 25.1 min, 75, 472,335 |
| D4 | 256/256, 256/256 | 141/157 | 6 | pass | 256/256 | **254/258** | 33.2 min, 91, 577,176 |
| D5 | 256/256, 256/256 | 133/157, 7 missing | 14 | pass | 256/256 | **238/258** | 31.0 min, 82, 545,887 |

- **R1.** Every first run was green. Every arm made one confirming run and left the third unused, so no
  failing run ever pulled code toward the suite.
- **R2.** C, D1 and D2 differ on ten of K2's eleven only; the eleventh, `s10`'s actions file, which K2 missed
  by its split keys, is identical in all six arms. M1–M6 are at 100 % in C, D1 and D2. D3: M1 1/14, M6
  stored 8/13, M7 exit 50/52 and text 44/52. D4: M5 11/14, other 33/36. D5: M5 12/14, M7 text 47/52, other
  31/34; s13 and s16 stop after the sync (below).
- **Nothing else moved.** In every degraded arm the non-identical set outside K2's eleven is exactly the
  union of the observing sets of the defects that propagated: D3 23 = 1 + 10 + 12, D4 6, D5 14 = 13 + 1.
- **R3.** D3's exported seam frame differs on Volume, the planted int32; every other arm's routes
  bit-identically through the original loader.
- **R5.** The pristine suite's failures are the propagated defects' scenarios: D3's 17 (the layout
  listings, the float32 mains, the int64 Volume), D4's 4 (`row(s) imported`), D5's 20 (the end-guard's,
  and the paused asset's listing).
- **R9.** 3,214,610 tokens and 503 tool calls in all; the arms ran concurrently, 25 to 33 minutes each.

**Per defect** (R6 on the observing set of n artefacts; R7 from `ASSUMPTIONS.md`):

| arm | slot | req | the defect | n | R6 | R7 | the entry |
|---|---|---|---|---|---|---|---|
| D1 | W | JDL-095 | `predates` → `precedes` (L5) | 2 | ORIGINAL | no | |
| D1 | M | JDL-134 | the `sync: {message}` refusal arrow (L5) | 16 | ORIGINAL | no | |
| D1 | A | JDL-049 | `raw` dropped from three steps (L5) | 2 | ORIGINAL | no | |
| D2 | W | JDL-060 | bar dates UTC → America/New_York | 13 | ORIGINAL | yes | A-01 names the contradiction; the suite wins by the precedence |
| D2 | M | JDL-102 | lazy collector construction | 5 | ORIGINAL | in part | A-12 builds lazily at the first leg needing the provider; the dry-run half is not named |
| D2 | A | JDL-073 | `every stored row` → `every usable stored row` | 6 | ORIGINAL | yes | A-22: "usable" undefined, every stored row exported |
| D3 | W1 | JDL-057 | `market_data` → `marketdata` | 1 | PLANTED | no | |
| D3 | W2 | JDL-047 | float64 → float32 price division | 10 | PLANTED | value only | entry 6 decides which float32 division, never doubts float32 |
| D3 | W3 | JDL-072 | integral export Volume int64 → int32 | 12 | 8 PLANTED, 4 OTHER | value only | entry 29: int32 "without an overflow guard (the kit states int32 only)" |
| D4 | W | JDL-099 | `imported` → `loaded` (L1) | 6 | PLANTED | yes | A-01: the requirement and the example disagree with the suite; the suite wins |
| D4 | M | JDL-118 | the zero-volume NOTE's outline (L1) | 1 | ORIGINAL | no | |
| D4 | A | JDL-003 | two exact-message rows loosened to a prefix (L1) | 2 | ORIGINAL | no | |
| D5 | M1 | JDL-094 | the crypto end-guard | 13 | PLANTED | yes | A-01 and A-16 name four residues; the requirement wins by the precedence |
| D5 | M2 | JDL-136 | the paused asset's ` [disabled]` | 1 | PLANTED | no | |
| D5 | M3 | JDL-084 | the asset filter | 6 | ORIGINAL | no | A-14 covers empty filter lists only |

D4-W's mutant is D3-099, built during D3's walk. R7 is read as frozen: an entry that names the value
counts. "In part" and "value only" qualify it; read strictly, D2 FLAGGED 2 of 3 and D3 0 of 3.

- **D3-W3's four OTHER.** `s22_cli_surface/cli_differential_csv.json` and `cli_export_aapl.json`,
  `s23_cli_on_store/cli_differential_tolerance.json` and `cli_differential_venues.json`. Exit and stdout
  equal D3-072's and D3-all's byte for byte. Stderr adds NumPy's `RuntimeWarning: invalid value
  encountered in cast` from the rebuild's `seam_frame`, which casts an array (`volume.astype(np.int32)`)
  where the mutant casts a pandas Series (`volume.astype("int32")`), which does not warn. Same planted
  value; the same out-of-range volumes land on INT32_MIN in both. The measure counts them OTHER, and so
  does this record (`results/grading/fields.txt`).
- **D5-M1's seven absences.** In s13 and s16 the rebuild and M-094 both send an open-ended request the
  recorded fixtures do not hold. The leg fails with the same `sync_out.txt` and `sync_summary.json` bytes,
  the store stays empty, and the harness's export step raises `Can only use .dt accessor with datetimelike
  values` in both. The seven artefacts after that step exist in neither run. `r6.py` counts an absence
  shared with the mutant as PLANTED, a reading made at grading; read strictly, 6 PLANTED and 7
  unclassified, with no ORIGINAL or OTHER either way.

**Propagation, attenuation, concealment** (R6 with R1 and R4). Six of the fifteen propagated: D3's three
(W3 with its four OTHER), D4-W, D5-M1 and D5-M2. All six are concealed: PLANTED with the arm's own suite
green in R4 and in every R1 run. The pristine suite fails on all six (R5). The other nine were attenuated:
D1's three, D2's three, D4-M, D4-A and D5-M3.

Every outcome is the one the kit's precedence rule gives, a silent layer counting as no statement: the code
took each behaviour from the highest-ranked layer that stated it.

- D1 (L5) and D2 (L2–L4) lost to the intact suite.
- D3's values were in every layer.
- D4-W won from L1. Its M and A lost: L1 went silent or permissive, and L2 still states the NOTE and the
  restriction.
- D5-M1 has no guard: the rewritten JDL-094 states the open end, the residues rank below it, and P4 left
  the suite neutral.
- D5-M2 had no statement left.
- D5-M3 kept the filter. The suite is neutral, and two surviving statements still presume the filter:
  JDL-085's refusal of an unknown asset name and the `--asset` help that P2 kept.

Three agents cite the rule in the entry that decided the outcome: D2's and D4's A-01, "the suite wins"; D5's
A-01, "the requirement outranks the contracts/DMN/diagrams".

**Gates before any rebuild** (G1–G6, `plant/plant.md`):

| kit | G1 lint | G2 score | G3 trace | G4 dmn_check | G5 glossary_check | G6 calibration |
|---|---|---|---|---|---|---|
| D1 | green | green | green | green | green | 258/258 |
| D2 | green | green | green | green | green | 258/258 |
| D3 | green | green | green | green | green | **241/258** |
| D4 | green | green | **red**: JDL-118, JDL-119 unverified | green | green | **252/256** |
| D5 | green | green | green | **red**: `fetch_end`, 2 gaps for declared_crypto = true | green | 256/256 |

No gate sees D1 or D2, and neither propagated. Calibration sees the two kits whose suites carry wrong values
(D3, D4). It cannot see D5: V5 makes D5's suite pass on the original by construction. D5-M2 propagated with
every gate green and the arm's own suite green; only the pristine suite saw it.

**R8, reads.** Every `READ.log` names every kit file (208; 206 in D4, 209 in D5). The only other entries
are an agent's own overflowed tool outputs (D2, D4) and D4's own scratch files. The six transcripts (503
tool calls) were read for every path outside the arm's directory: none reaches another arm, the vault,
either repository, the subject's venv, the lab or this session's transcript. The outside paths are the
agent's own overflowed outputs (C, D1, D2, D4), `/tmp` as a working directory (D2, D3, D4), and the shared
scratchpad root, where D2 and D5 kept scratch files (D5 its smoke tests and suite runs, unlogged).

**Expectations:**

| id | verdict | counts |
|---|---|---|
| X1 | held | 0 of 3 PLANTED (refuted at ≥ 2) |
| X2 | held | 3 of 3 ORIGINAL; FLAGGED W and A, M in part |
| X3 | split | 2 of 3 PLANTED, W3 mixed (8 PLANTED, 4 OTHER); R4 258/258; G6 241/258; G1–G5 green |
| X4 | held | W PLANTED 6/6 and FLAGGED (A-01); M ORIGINAL 1/1; A ORIGINAL 2/2; G6 252/256 |
| X5 | held | M1 and M2 PLANTED, M3 ORIGINAL; M1 FLAGGED; G3 green; G4 red on `fetch_end`'s two deleted rows |
| X6 | held | 147/157; M1–M6 at 100 %; the ten non-identical within K2's eleven |
| X7 | held | G1–G3 green on 4 of 5 (D4's G3 red); G5 green on 5 of 5 |

Six held, one split, none failed.

**Which reading predicted better, per arm:**

| arm | as drawn | as corrected | better |
|---|---|---|---|
| D1 | propagation where consumed: failed; every diagram was read (READ.log; A-01 and A-05 cite `component.puml`) and none propagated | attenuation by role: held | corrected |
| D2 | detection by the suite: held | the same, by the suite's precedence: held (A-01 cites it) | tie |
| D3 | concealment: held, W3 in part | concealment: held; calibration interrupts: held, G6 red | corrected, by the clause the drawn reading lacks |
| D4 | no edge from tests to code: failed on the W | the suite pulls the code: held on the W, with M and A ORIGINAL | corrected |
| D5 | invention lowers fidelity: fidelity fell, by literal omission, not invention | invention, recorded: recorded (A-01, A-16), no invention | tie; neither mechanism as worded |

The corrected reading predicted better on three arms; two are ties; the drawn reading won none. Two
refinements to carry back to the model: the `testdef → codedef` edge held, but its mechanism is the
declared precedence, not iteration (R1: no run ever failed); and F5 split, with omission recorded but never
answered by invention (D5 has no OTHER).

**What the frozen text got wrong.** §4: "No requirement id is removed or renumbered, so the id inventory
and the trace gate are untouched." D4 refutes it: deleting a requirement's only scenario leaves the
requirement unverified (G3 red on JDL-118 and JDL-119). Nothing above the line changes.

**The plant's residues.** The plant left statements of three deleted clauses in place:

- **By design, P2:** the `--dry-run` help (D2-M); the sync help's "crypto end-guarded at the previous UTC
  day" (D5-M1); the `--asset` help (D5-M3).
- **By design, the M definition:** the DMN output domain keeps `today_minus_1` (D5-M1).
- **Another requirement's clause:** JDL-085's unknown-asset refusal (D5-M3); JDL-095's empty-series
  request and the DMN's `bar_request` r3, reachable only under the guard (D5-M1).
- **Missed:** `zero_end.toml`'s comment "an end below the guard" (D5-M1), found by the D5 agent.
- **The stated hint:** every crypto end falls the day before its scenario's clock (D5-M1), which the D5
  agent read as "the suite cannot tell the two apart".

The D5 agent named four of them and still built no guard, by the precedence. The D2 repair after V2
(`plant/plant.md`) is the plant's other correction.

**Beside the measures: the pristine kit's own residues.** Five arms report inconsistencies the plant did
not make, all in the committed kit:

- the transport's `(status, text)` in the glossary and `component.puml`, against the 2026-10-24 response
  object (D1, D2, D3, D4);
- JDL-132's `{missed_sessions or -}`, against the status table's `0 missed` (D2, D3, D4, D5);
- the README's reading order, numbered 1, 2, 5, 3, 4 (D1, D4);
- `refusals.md`'s X-11 listed before X-10 (D1, D2, D4).

C names none of the four. They are for the kit's owner; no measure counts them.

**Bounds, as they bit.** n = 1 throughout. C, the model confound's baseline, is one artefact better than K2
(147 against 146). One context planted, graded, and wrote the grading readings after seeing the runs: the
shared absence in R6, "in part" and "value only" in R7. Each is stated beside its strict alternative, and
no verdict turns on one. The isolation bound is above.
