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

## End-to-end example: GEN009 `max-elements`

A walkthrough of a real shipped rule — GEN009 flags diagrams that have grown
past readable size, whatever their type. It shipped in v0.12.0; every
artifact below is quoted from the repo, so you can open the files and see
the same thing in context.

### Step 0 — Design decisions first

- **ID:** next free number in the pack whose scope matches. Size is a
  concern for every diagram type → `GEN` pack → `GEN009`. IDs are stable
  once shipped; never reuse or renumber.
- **Severity:** an oversized diagram violates a recommended convention,
  nothing is broken → `minor` (see the severity table in RULES.md).
- **Dimension:** which maturity dimension does the finding erode? Size is a
  readability concern → `DIM-RDB`. Every rule carries exactly one dimension;
  this is how the scorer buckets your findings (SCORING.md §2).
- **Default or dormant?** Two settled patterns to choose from — v0.12.0
  shipped examples of both, side by side:
  - *Convention-gated* (GEN006 `owner-tag`, GEN007 `requirement-link`): a
    rule enforcing a house convention with no universal default ships
    **dormant** — it only activates when the project configures its
    `pattern`. An always-on ownership-tag requirement would have demoted
    every existing diagram below the Level 5 dimension gate by fiat.
  - *Tail guard* (GEN008 `note-density`, GEN009): a sensible universal
    default that no reasonable diagram trips. GEN009 fits here — `max = 60`
    semantic elements is generous.

### Step 1 — Specify it in RULES.md

The rule's section carries its rationale and the Gherkin acceptance block
(RULES.md, GEN009):

````markdown
### GEN009 — Element count limit
**Severity:** minor · **Status:** ✅ Implemented (v0.12.0)

**Rationale:** Past a certain size a diagram of any type stops being readable;
the semantic element count (the same one the maturity scorer uses as its density
denominator) is the type-neutral measure. Option `max` (default 60).

```gherkin
Feature: GEN009 element count limit

  Scenario: oversized diagram is reported
    Given the configuration:
      """
      [rules.GEN009]
      max = 3
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      A -> B : again
      @enduml
      """
    When the linter runs
    Then a "GEN009" issue with severity "minor" is reported on line 1

  Scenario: normal-sized diagram passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      A -> B : again
      @enduml
      """
    When the linter runs
    Then no "GEN009" issue is reported
```
````

Two things worth noticing: the first scenario uses the
`Given the configuration:` step (TOML docstring) to lower the threshold —
that's how you make a tail guard testable without a 60-element fixture; and
the same 6-element diagram serves both scenarios, so the pair isolates the
option's effect.

Then regenerate and commit the feature file:

```bash
python tools/extract_features.py     # writes tests/bdd/features/GEN009.feature
```

At this point `pytest` runs your scenarios and (correctly) fails them —
writing the spec before the code is the intended order; a not-yet-implemented
rule can also sit in RULES.md as ⏳ Planned, which emits its feature with a
`@skip` tag.

### Step 2 — Declare it in catalog.toml

From `pumllint/rules/catalog.toml`:

```toml
[GEN009]
name = "max-elements"
description = "Diagram has more semantic elements than the configured maximum"
severity = "minor"
dimension = "DIM-RDB"
applies_to = ["*"]
profiles = []            # [] = base catalog, always active
```

Every registered rule **must** have a catalog entry — `@register` raises
without one, and `tests/test_catalog.py` guards catalog↔registry parity both
ways.

### Step 3 — Implement it

The whole implementation, from `pumllint/rules/common/governance.py`:

```python
@register
class MaxElements(Rule):
    """Diagram grown past readable size, whatever its type.

    Option: ``max`` (default 60 semantic elements — the same count the
    maturity scorer uses as its density denominator).
    """

    id = "GEN009"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        limit = int(self.options.get("max", 60))
        count = diagram.element_count
        if count > limit:
            yield self.violation(
                diagram,
                diagram.start_line,
                f"Diagram has {count} elements (max {limit}) — split it along "
                "phases, subsystems or scenarios",
            )
```

Idioms to copy:

- **Reuse the model's vocabulary instead of inventing your own.** GEN009
  doesn't define "size" per diagram type — it uses `Diagram.element_count`,
  the exact count the maturity scorer already uses as its density
  denominator. One definition, shared everywhere.
- **Options with defaults** via `self.options.get(...)` — every threshold a
  project might reasonably tune should be an option, documented in the
  README rules table.
- **Point at the most meaningful line.** GEN009 reports on
  `diagram.start_line` because the finding is about the diagram as a whole;
  a rule about one construct points at that construct's line instead.
- **Say what to do, not just what's wrong** — "split it along phases,
  subsystems or scenarios" makes the finding a suggestion, not a scolding.

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
design*, so score changes are always a conscious act. How v0.12.0's three
new default-on rules played out is the case study:

- GEN008, GEN009 and SEQ011 were designed as tail guards precisely so that
  **no calibration-corpus unit trips them** — the golden test passed
  untouched, which was verified and recorded (SCORING.md §9) rather than
  assumed.
- GEN006/GEN007 would have moved scores massively had they shipped
  always-on — every corpus diagram lacks an owner tag. That is *why* they
  are convention-gated: the golden-score impact analysis is the moment this
  choice gets forced.
- If your rule's score shifts are legitimate, inspect the diff and re-freeze
  deliberately with `python tools/calibrate.py --freeze
  tests/golden_scores.json`. The re-freeze commit is where reviewers
  scrutinize *how much* your rule demotes existing diagrams.

Read the "Working agreements" section of [ROADMAP.md](../ROADMAP.md) before
changing anything score-adjacent.

### Step 6 — Document it

- Add the row to the README rules table — GEN009's reads: *"More semantic
  elements than `max` (default 60), any diagram type."*
- Flip the RULES.md status to ✅ with the version (v0.12.0 for GEN009).

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
