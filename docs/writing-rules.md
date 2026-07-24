# Writing rules — a programming guide

*Audience: developers extending the linter. Covers the architecture you'll
touch, the role of the Gherkin blocks, and a complete end-to-end example of
adding a rule.*

## The 60-second architecture

```
.puml source ──parser──▶ Diagram model ──rules──▶ Violations ──reporters──▶ text/json/sonar/…
                                          ▲
                              engine: config merge, profiles,
                              suppressions, rule discovery
```

Two design decisions shape everything you'll write:

1. **Rules never see raw text.** The parser (`pumllint/parser/`) turns each
   `@startuml…@enduml` block into a semantic
   [`Diagram`](../pumllint/model.py) — participants, messages, blocks,
   classes, states, directives. Your rule reasons over that model, so parser
   improvements benefit every rule and rules stay a few lines long.
2. **A rule has a declarative half and an imperative half.** The metadata
   (name, description, severity, dimension, scope, profiles) lives in
   [`pumllint/rules/catalog.toml`](../pumllint/rules/catalog.toml); the
   Python class carries only its `id` and its `check()` algorithm. The
   `@register` decorator joins the two at import time, and `discover()`
   auto-imports every module under `pumllint/rules/` — there is nothing else
   to wire up.

## Anatomy of a rule

```python
from pumllint.rules import Rule, register

@register
class NoSelfMessage(Rule):
    id = "SEQ006"                       # the catalog join key — all you author here

    def check(self, diagram):           # yields Violations
        allowed = set(self.options.get("allowed", []))
        for m in diagram.messages:
            if m.source and m.source == m.target and m.source not in allowed:
                yield self.violation(diagram, m.line, f"Self-message on '{m.source}'")
```

What the base class gives you:

- `self.options` — the rule's merged config from `pumllint.yaml` (with any
  `severity:` override already extracted into `self.severity`).
- `self.violation(diagram, line, message)` — constructs a `Violation` carrying
  your rule's id, severity and scoring dimension.
- Catalog-stamped attributes: `name`, `description`, `default_severity`,
  `dimension`, `applies_to`, `profiles`. The engine uses `applies_to` to skip
  your rule on other diagram types, and keeps profile-gated rules dormant
  until their profile is selected.

For rules that reason **across** diagrams (the XD pack), subclass
`CrossDiagramRule` and implement `check_all(diagrams)` instead; the engine
activates these only when more than one diagram is linted.

## The Gherkin layer: RULES.md is an executable spec

Every rule in [RULES.md](../RULES.md) carries a ` ```gherkin ` block. This is
not documentation decoration — it is the rule's **acceptance test**:

- `tools/extract_features.py` lifts each block into
  `tests/bdd/features/<ID>.feature`.
- `tests/bdd/test_features.py` binds those files to a small **canonical step
  vocabulary** and runs them against the real engine under pytest-bdd.
- A sync test fails CI if the committed `.feature` files drift from RULES.md
  — so the spec and the linter's behaviour can never silently disagree.
- Rules specified but not yet implemented are marked ⏳/🚫 in RULES.md and
  emitted with a `@skip` tag: you can specify first and implement later.

Why this design: the spec stays in one human-readable place (RULES.md, next
to each rule's rationale), reviewers can read acceptance criteria without
opening test code, and adding a rule requires **no new step definitions** —
only scenarios written in the fixed vocabulary:

```gherkin
Given the diagram:            # docstring: PlantUML source
Given the configuration:      # docstring: rule config, in TOML
Given the "codegen" profile is active

When the linter runs

Then no issues are reported
Then no "SEQ006" issue is reported
Then a "SEQ006" issue is reported
Then a "SEQ006" issue with severity "minor" is reported
Then a "SEQ006" issue is reported on line 3
Then a "SEQ006" issue with severity "minor" is reported on line 3
```

Note the `Given the configuration:` docstring is **TOML**, and `Then` steps
match exactly (both "a" and "an" work). If your rule needs an assertion this
vocabulary can't express, extend `test_features.py` deliberately — the
vocabulary is meant to grow slowly.

## End-to-end example: adding GEN010 `title-max-length`

A worked example (not shipped code): flag diagram titles longer than a
configurable maximum, because over-long titles wrap in renders and make
review references unwieldy.

### Step 0 — Design decisions first

- **ID:** next free number in the pack whose scope matches. Applies to every
  diagram type → `GEN` pack → `GEN010`. IDs are stable once shipped; never
  reuse or renumber.
- **Severity:** violates a recommended convention, nothing is broken →
  `minor` (see the severity table in RULES.md).
- **Dimension:** which maturity dimension does the finding erode? A long
  title is a readability concern → `DIM-RDB`. Every rule carries exactly one
  dimension; this is how the scorer buckets your findings (SCORING.md §2).
- **Default or dormant?** Two settled patterns to choose from:
  - *Convention-gated* (like GEN006/GEN007): if the rule enforces a house
    convention that has no universal default, ship it **dormant** — it only
    activates when the project configures a pattern. An always-on convention
    rule would demote every existing diagram by fiat.
  - *Tail guard* (like GEN008/GEN009): a sensible universal default that no
    reasonable diagram trips. GEN010 fits here — default `max = 60` is
    generous.

### Step 1 — Specify it in RULES.md

Add the rule section, rationale, and the Gherkin acceptance block:

````markdown
### GEN010 — Title length limit
**Severity:** minor · **Status:** ⏳ Planned

**Rationale:** Over-long titles wrap in rendered output and make diagrams
awkward to reference in reviews. Keep the title a label; narrative belongs
in a note or the accompanying document.

```gherkin
Feature: GEN010 title length limit

  Scenario: over-long title is reported
    Given the diagram:
      """
      @startuml demo
      title This title rambles on far past any reasonable length for a diagram heading in a review
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then a "GEN010" issue with severity "minor" is reported on line 2

  Scenario: short title passes
    Given the diagram:
      """
      @startuml demo
      title Order Processing
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then no "GEN010" issue is reported

  Scenario: configured maximum is respected
    Given the configuration:
      """
      [rules.GEN010]
      max = 10
      """
    And the diagram:
      """
      @startuml demo
      title Order Processing
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then a "GEN010" issue is reported on line 2
```
````

Then regenerate and commit the feature file:

```bash
python tools/extract_features.py     # writes tests/bdd/features/GEN010.feature
```

At this point `pytest` runs your scenarios and (correctly) skips or fails
them — the spec exists before the code, which is the intended order.

### Step 2 — Declare it in catalog.toml

```toml
[GEN010]
name = "title-max-length"
description = "Title exceeds the configured maximum length"
severity = "minor"
dimension = "DIM-RDB"
applies_to = ["*"]
profiles = []            # [] = base catalog, always active
```

Every registered rule **must** have a catalog entry — `@register` raises
without one, and `tests/test_catalog.py` guards catalog↔registry parity both
ways.

### Step 3 — Implement it

Governance rules live in `pumllint/rules/common/governance.py` (or drop a new
module anywhere under `pumllint/rules/` — discovery walks the package):

```python
@register
class TitleMaxLength(Rule):
    id = "GEN010"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        title = diagram.title          # a Directive (kind/value/line), or None
        if title is None:
            return                     # missing title is GEN001's finding, not ours
        max_len = self.options.get("max", 60)
        if len(title.value) > max_len:
            yield self.violation(
                diagram, title.line,
                f"Title is {len(title.value)} characters (max {max_len})",
            )
```

Idioms to copy from the existing packs:

- **One concern per rule** — GEN010 stays silent on a *missing* title; that
  is GEN001's finding. No double reporting (the same agreement keeps
  XD004/XD005 out of XD002/XD003's territory).
- **Options with defaults** via `self.options.get(...)` — every threshold a
  project might reasonably tune should be an option, documented in the
  README rules table.
- **Point at the most actionable line** — the title line, not line 1.

### Step 4 — Run the tests, all of them

```bash
python tests/run_tests.py    # zero-dependency unit/integration suite
python -m pytest             # + the executable RULES.md spec (needs `pip install -e ".[test]"`)
```

The first command must pass with the **stdlib only** — the zero-dependency
promise covers product code *and* its core tests. Don't add imports outside
the standard library.

### Step 5 — Face the golden-score contract

**Scores are a public contract.** `tests/test_golden_scores.py` pins the
maturity score of every calibration-corpus unit. A new always-on rule that
fires anywhere in the corpus will shift scores and fail that test — *by
design*, so score changes are always a conscious act. Your options:

- If the corpus shouldn't trip the rule (tail guard with a generous default,
  like GEN010): the golden test passes untouched — verify, and say so in the
  changelog.
- If scores legitimately move: inspect the diff, and re-freeze deliberately
  with `python tools/calibrate.py --freeze tests/golden_scores.json`. The
  re-freeze commit is where reviewers scrutinize *how much* your rule demotes
  existing diagrams.
- If the rule would demote broad swaths of reasonable diagrams: that's the
  signal to make it convention-gated (dormant without config) or
  profile-gated (`profiles = ["codegen"]`) instead.

Read the "Working agreements" section of [ROADMAP.md](../ROADMAP.md) before
changing anything score-adjacent.

### Step 6 — Document it

- Add the row to the README rules table (ID, name, default severity, what it
  catches, notable options).
- Flip the RULES.md status to ✅ with the version.

That's the complete loop: **spec → catalog → code → tests → golden check →
docs.** For a typical rule it's an afternoon, most of it spent on Step 0.

## Beyond single rules

- **New output format** = one class decorated with `@reporter` in
  `pumllint/reporters/`. If it's machine-read, consider whether its shape
  should join the JSON-Schema contract (`pumllint/schemas/`).
- **New diagram type** = a parser module + a rule pack, the same pattern as
  activity/class/state before it. The settled parser discipline: a type is
  detected by constructs **no other form uses**, a diagram is never re-typed
  once detected, and ambiguous constructs (arrows) bind only after the type
  is known. Add corpus fixtures and extend `tools/gen_corpus.py` so the
  golden contract covers the new type's scoring.
- **Profile-gated packs**: set `profiles = ["yourprofile"]` in the catalog;
  everything else (config, suppressions, reporters, scoring) works
  identically for gated rules. The `SEQ100–199` range is reserved for the
  codegen pack — reserve a range if you ship a pack.
