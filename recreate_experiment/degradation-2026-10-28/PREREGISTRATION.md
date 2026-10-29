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
