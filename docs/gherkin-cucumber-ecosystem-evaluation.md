# The Gherkin / Cucumber ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `c1b1af9` (v0.30.0).
Twenty-seventh in the series, and the first whose subject is **already
inside the project**. Twenty-six notes asked whether pumllint should
reach into a neighbouring ecosystem. This one asks a question none of
them could: **pumllint already depends on Gherkin — is it using it
well, and what does the ecosystem's own health say about pumllint's?***

**Verdict up front: nothing to adopt, nothing to refuse — the dependency
is already there and, measured against the ecosystem's own linter, it is
clean. The two findings worth having are elsewhere.**

**(1) Turning the method on ourselves: 562 → 0.** `gherkin-lint` 4.2.4
run over this repository's 43 generated feature files reports **562
findings** under its defaults. Declare the project's actual conventions
— the indentation it really uses, and scenario-name uniqueness scoped
per feature rather than across the corpus — and the same tool reports
**zero, exit 0**. **Every single finding was a configuration
disagreement; not one was a defect.** That is the prose-linting note's
lesson again, now quantified on this project's own artefacts.

**(2) A pattern reaching its third instance, with its exception
identified — and the exception is the uncomfortable part.** In three
ecosystems now, **the parser is alive and the standalone linter is stale
or absent**:

| Ecosystem | Parser | Linter |
|---|---|---|
| DMN | `dmn-js` **17.10.2** (2026-08-25) | `dmnlint` **1.0.0**, 4 versions, **2 rules** |
| FEEL | `feelin` **7.0.1**, 99 versions (2026-05-29) | *(none)* |
| **Gherkin** | `@cucumber/gherkin` **42.0.1**, 72 versions (**2026-08-05**) | `gherkin-lint` **4.2.4**, 73 versions, last shipped **2023-12-20** |

**BPMN is the counter-example**, and it is decisive for what the pattern
means: `bpmnlint` is at 11.13.0 with 27 rules and shipped 2026-08-19.
**The thing that distinguishes it is embedding.** `bpmnlint` is not
really a standalone CLI that happens to be popular — it is the modeler's
live feedback, wired in through `bpmn-js-bpmnlint`, that also ships a
CLI. The three stale entries are standalone CLIs whose artefacts get
their feedback elsewhere: a Gherkin feature is executed as a test, a DMN
table is analysed by the modeler, a FEEL expression is parsed by the
editor.

**The pattern, stated with its exception: a standalone linter CLI goes
stale unless it is also the feedback where authoring happens.** pumllint
is a standalone CLI with no editor integration — LSP is recorded as Arc
E, wait-for-pull. **This note does not conclude that pumllint should
build one**; §7 explains why the inference does not go through. It
records the pattern because the pattern is about this project, not about
Gherkin.

*Bounds. **`gherkin-lint` 4.2.4 was installed and executed** against this
repository's real `tests/bdd/features/`; the 562 and the 0 are both runs.
Version histories are from the npm registry. **The vitality pattern is
four data points with one counter-example, offered as a pattern to test
and not a law** — the Structurizr turn withdrew a generalization built
on two. **No claim is made about why any maintainer stopped shipping**;
"stale" here means only "no published release since the date given". No
Cucumber test suite was run, and `reqnroll`/`SpecFlow`/Behave were not
examined. Per session scope no GitHub repository was read.*

## 0. Why this one is different

Every prior note in this series had the same shape: an outside ecosystem,
and a question about whether pumllint should reach into it. Gherkin
cannot be asked that question, because the answer is already yes and has
been for a long time.

`RULES.md` carries Gherkin blocks as each rule's acceptance criteria.
`tools/extract_features.py` turns them into **43 feature files carrying
122 scenarios** under `tests/bdd/features/`, which `pytest-bdd` executes
as part of the full suite. `CLAUDE.md` makes regeneration a standing
obligation, and `.github/workflows/tests.yml` enforces it:

```
python tools/extract_features.py
  || (echo "::error::tests/bdd/features is stale — run: python tools/extract_features.py"; exit 1)
```

So Gherkin is not a candidate. It is **the executable form of this
project's own specification**, gated in CI. The interesting questions are
therefore inward-facing, and the series has never asked one before.

## 1. The ecosystem, and a pattern

### 1.1 Parser alive, linter stale

| Package | Role | Versions | First | Latest |
|---|---|---|---|---|
| `@cucumber/gherkin` | parser | 72 | 2020-01-10 | **2026-08-05** |
| `gherkin-lint` | linter | 73 | 2016-04-13 | **2023-12-20** |

Near-identical release *counts*, two and a half years apart in
*recency*. The parser shipped three weeks before this note, at major
version **42**. The linter last shipped in 2023.

This is the third ecosystem in four notes with that shape (see the
table above), and it would be easy to call it a law. The Structurizr
turn is the reason not to: a generalization drawn from two points was
withdrawn when the third refuted it. So the honest procedure is to look
for the counter-example first.

### 1.2 The counter-example, and what it explains

**BPMN.** `bpmnlint` 11.13.0, 27 rules, shipped 2026-08-19 — thoroughly
alive, and the fourth note's ground (2) for refusing BPMN was precisely
that its linting niche is *occupied*.

What is different? **`bpmnlint` is embedded.** The BPMN note's own tool
table records it: *"`bpmnlint` embedded via `bpmn-js-bpmnlint` — live
feedback while modelling"*. It is the modeler's feedback loop that also
ships a CLI, not a CLI that people remember to run.

Now read the three stale entries the same way, and each has a *different*
feedback loop that the linter is not part of:

- **Gherkin** — a feature file is **executed as a test**. A malformed or
  wrong scenario fails the suite immediately, loudly, in the place the
  author is already looking.
- **DMN** — the table is **analysed by the modeler** (and by
  `dmn-check`), where the solver can live. The DMN note recorded this as
  "the work went to the analysers".
- **FEEL** — the expression is **parsed by the editor**, live.

**The unifying reading: a standalone linter CLI is a feedback loop of
last resort. It stays healthy only where it is also the feedback at the
point of authoring; otherwise whatever else gives the author feedback
first will absorb the maintenance.** One pattern, three confirmations,
one counter-example that explains rather than contradicts it.

That is a claim about linters in general, and this project is a linter.
§7 is where that gets faced honestly.

## 2. Turning the method on ourselves

Twenty-six notes have run other people's tools on toy corpora. This one
runs another ecosystem's linter on **this repository's real artefacts**.

**Under `gherkin-lint`'s defaults:**

```
559  indentation
  3  no-dupe-scenario-names
---
562 findings                                                          (exit 1)
```

**The 559.** `gherkin-lint`'s default indentation config is:

```js
const defaultConfig = { 'Feature': 0, 'Background': 0, 'Rule': 0,
                        'Scenario': 0, 'Step': 2, ... }
```

It expects `Scenario` at **column 0** — flush with `Feature`, not nested
inside it. This project's generated features nest: `Feature` 0,
`Scenario` 2, `Step` 4. That is the shape Cucumber's own documentation
displays, and it is the shape a reader expects. **The disagreement is a
style default, and it is configurable.**

**The 3.** Three scenario names recur across files:

| | |
|---|---|
| `diagram within the limit passes` | SEQ011 and GEN005 |
| `conforming names pass` | UC002 and CLS001 |
| `a distinct entity is never compared` | XD001 and XD002 |

Each pair is **two analogous rules** — two limit rules, two naming rules,
two distinct-entity rules — in a per-rule file layout where the `Feature:`
line names the rule. Within a file every name is unique; the repetition
is across files, and `gherkin-lint`'s own rule ships an `in-feature`
scope for exactly this.

**Declare both conventions and the corpus is clean:**

```
$ gherkin-lint -c rc-with-project-conventions tests/bdd/features/
                                                                      (exit 0)
```

**562 → 0. Not one finding was a defect.**

Two things follow, and the second is the useful one.

**The generated Gherkin is sound by the ecosystem's own standard.** That
is worth knowing and was not known: `extract_features.py` produces
features that a real Gherkin linter accepts without complaint once told
the house style.

**And the ratio is the lesson.** 559 of 562 findings were a linter's
default disagreeing with a defensible local convention. This is the
prose-linting note's result — external linter findings were convention,
not correctness — reproduced at a different scale in a different
ecosystem, on this project's own files. **A linter run without its
configuration is not a measurement of quality; it is a measurement of
whose defaults you inherited.** pumllint's own defaults are equally
opinionated, and an adopter running `pumllint` cold on a mature diagram
corpus will have exactly this experience.

## 3. Boundaries

1. **Inside, not adjacent.** Gherkin is a dependency of this project's
   test harness, not a candidate artefact class. No boundary question
   arises.
2. **Executed vs described.** A Gherkin feature is executed. The BPMN
   note's structural ground applies here more cleanly than it did there:
   there is no gap between the specification and its execution for a
   linter to stand in — the test run *is* the check.
3. **Convention vs defect.** §2. The boundary between them is a
   configuration file, in both directions.

## 4. Overlap

Almost none, and that is expected: `gherkin-lint`'s 32 rules are about
*feature-file hygiene* — tags, file names, indentation, empty
backgrounds, duplicate names, scenario counts. pumllint's 51 are about
*diagram semantics*. The one structural correspondence worth recording is
`no-dupe-scenario-names` ↔ the **XD family**: both are
identity-and-duplication checks across a batch of files, and both had to
decide the same question — *is duplication across files a defect, or only
within one?* `gherkin-lint` made it configurable. The XD rules answered
it for their domain. Same question, two artefacts, independently
recognised as needing an answer.

## 5. Sense — three true things

**S1. This project's generated Gherkin is clean by the ecosystem's own
linter** (§2). Newly established.

**S2. The 562 → 0 ratio is a warning about linters generally, including
this one.** §2's closing paragraph. It is the most transferable thing in
the note.

**S3. The vitality pattern has a counter-example that explains it.**
§1.2. Three confirmations plus BPMN, with embedding as the discriminator,
is a better-founded pattern than the withdrawn viewpoint generalization
ever was — and it is still offered as a pattern to test.

## 6. Nonsense — three moves to refuse

**N1. "Add `gherkin-lint` to CI."** It last shipped in 2023, it reports
zero findings on the corpus once configured, and the corpus is
**generated** — its shape is `extract_features.py`'s output, not an
author's choice. Linting a generated artefact checks the generator, and
the generator is already checked by the staleness gate in
`tests.yml` plus the suite that executes the features.

**N2. "The corpus has 559 indentation problems."** It has zero. §2.
Quoting the default-config number as a finding about this repository
would be exactly the error §2 exists to name.

**N3. "The vitality pattern says pumllint needs an LSP."** §7. The
inference does not go through, and treating a four-point pattern as a
roadmap input would be the Structurizr error with a bigger n.

## 7. The uncomfortable part, faced

§1.2's pattern is about standalone linter CLIs. pumllint is a standalone
linter CLI. The temptation is to read the pattern as a warning that it
will go the way of `gherkin-lint` unless it becomes editor feedback.

**Three reasons that inference does not go through, and one reason the
pattern is still worth recording.**

**The artefacts differ in where feedback already exists.** Each stale
linter sat beside a loop that *already told the author*: a failing test,
a modeler's analysis, a live parser. PlantUML's authoring loop tells you
whether the diagram *renders* — the case document's central observation
is that existing tooling "stops at 'does it draw?'". **There is no
incumbent feedback loop absorbing the maintenance here**, which is the
condition the pattern says matters.

**The gate is the point, not a consolation.** pumllint's designed home is
CI and pre-commit — the composite action, both hooks, the exit-code
contract. `gherkin-lint` went stale as a *gate people forgot to run*;
this project's gate is the product.

**Four points is four points.** The pattern is offered as a predictor to
test, exactly as "derived vs drawn views" was after the last
generalization was withdrawn.

**And yet it is worth recording**, because it sharpens what the recorded
LSP item is *for*. The pattern's claim is not "ship an LSP or die" — it
is that **the point of authoring is where a checker's maintenance gets
funded**. If the LSP item is ever picked up, this is the argument for it,
and it is a better one than "editors are nice to have". Still Arc E,
still wait-for-pull, still no constituency. §8 grades it.

## 8. Fit — graded

### F1 — adopt `gherkin-lint` in CI. **No.** N1.

### F2 — lint `RULES.md`'s Gherkin blocks at source rather than the generated features. **No, and for a better reason than F1.**

The blocks are authored by hand, so this is not linting a generated
artefact. But the acceptance bar for them is already thicker than
`gherkin-lint`'s: the ROADMAP's "thickened Gherkin bar" governs what a
rule's block must contain before an implementer sees it, and the
extracted features must *execute*. A hygiene linter adds nothing above a
test that runs.

### F3 — an editor integration / LSP. **Unchanged: Arc E, wait-for-pull, no constituency.**

§7 gives it a **better argument** than it had, and no more demand than it
had. Recorded, not queued, exactly as before.

### F4 — scenario-name uniqueness across the corpus. **No — and worth saying why.**

The three duplicates are analogous scenarios in analogous per-rule files,
where the `Feature:` line disambiguates. Enforcing global uniqueness
would push names toward `SEQ011: diagram within the limit passes`,
restating the filename in every scenario. **The redundancy is the
point of the per-rule layout.**

### Fit against declared constraints

| Constraint | Reading |
|---|---|
| **Zero dependencies** | F1 would add a stale Node dependency to CI for zero findings. |
| **Demand-driven / Arc E bar** | F3 is the only live item and it stays gated. |
| **Deterministic product path** | Untouched. |

## 9. SWOT

**Strengths (internal, favourable)**

- The generated Gherkin is **clean by the ecosystem's own linter** (§2),
  now measured rather than assumed.
- The specification-as-executable-test loop is **already CI-gated** —
  staleness check plus execution — which is the strongest form of the
  thing `gherkin-lint` exists to approximate.

**Weaknesses (internal, unfavourable)**

- **No authoring-point feedback**, which §1.2's pattern identifies as the
  condition under which standalone checkers get maintained. §7 argues the
  pattern does not straightforwardly apply; it does not argue the
  weakness is imaginary.
- pumllint's own defaults are as opinionated as `gherkin-lint`'s (§2),
  and an adopter running it cold on a mature corpus will meet the 559,
  not the 0. There is no measurement of *that* experience on file.

**Opportunities (external, favourable)**

- None. Gherkin is a dependency, not a market.

**Threats (external, unfavourable)**

- **The cold-run experience** (above) is the realistic adoption risk this
  note surfaces, and it is not a Gherkin problem — it is a general one,
  found here because this was the first note to run a linter on a real
  corpus rather than a toy.

## 10. Decision, recorded candidates, triggers

**Decision: nothing to adopt and nothing to refuse. The Gherkin
dependency stands as it is, and is measured sound.**

**Never build:**

- A `gherkin-lint` CI step (F1, N1) — stale tool, zero findings,
  generated artefact.
- Global scenario-name uniqueness (F4) — it would fight the per-rule file
  layout.

**Recorded, not queued:**

1. **The linter-vitality pattern (§1.2)** — parser alive / standalone
   linter stale, three instances, with **BPMN as the explaining
   counter-example** and **embedding at the point of authoring** as the
   discriminator. Offered as a predictor to test; **not** a roadmap
   input (N3).
2. **§7's argument for the LSP item** — if F3 is ever picked up, the
   pattern is the argument. Does not change its gating.
3. **The cold-run gap (§9)** — no measurement exists of what pumllint's
   defaults report on a large, mature, third-party diagram corpus. §2
   suggests the number would be large and mostly conventional. Recorded
   as a **measurement that does not exist**, not as a candidate.

**Re-litigate on:**

- `gherkin-lint` being superseded by a maintained successor that the
  Cucumber project itself ships — which would flip §1.2's third instance
  and is the cleanest test of the pattern.
- An adopter reporting the cold-run experience, which would turn
  candidate 3 into a real question about default profiles.
- The LSP item's own trigger, unchanged.

## Related reading

- [The prose-linting ecosystem, evaluated](prose-linting-ecosystem-evaluation.md)
  — the immediately preceding note; §2's convention-vs-defect ratio is
  its lesson at a different scale.
- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md) — the first
  instance of the vitality pattern, and where "the analysers took the
  work" was recorded.
- [The FEEL expression language ecosystem, evaluated](feel-expression-language-evaluation.md)
  — the second instance.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  counter-example, and the source of the "embedded in the modeler"
  observation §1.2 turns into the discriminator.
- [The Structurizr DSL viewpoints ecosystem, evaluated](structurizr-viewpoints-evaluation.md)
  — the withdrawn generalization that is the reason §1.2 hunts its
  counter-example before stating a pattern.
