# pumllint — Rule Specification

Semantic validation rules for PlantUML diagrams, modelled on ARIS-style semantic
checks: every rule has a stable ID, a severity, a scope (`applies_to`), a
method-convention rationale, Gherkin acceptance criteria, and an implementation
status against the current codebase (v0.5.0).

Syntax validation is out of scope — it is delegated to `plantuml -checkonly` as a
separate CI gate.

**This spec is executable.** The ` ```gherkin ` block under each rule is not
decoration: `tools/extract_features.py` lifts every block into
`tests/bdd/features/<ID>.feature`, and pytest-bdd runs them against the real
linter (see the canonical step vocabulary in `tests/bdd/test_features.py`).
Implemented rules (✅) run for real; blocked/planned rules (🚫/⏳) are emitted
with a `@skip` tag. A sync test fails if the committed features drift from this
file, so RULES.md and the test suite can never silently disagree. After editing a
Gherkin block, regenerate with `python tools/extract_features.py`.

## Conventions

**Severity levels** (map 1:1 to SonarQube Generic Issue Import Format):

| Severity | Meaning |
|----------|---------|
| `blocker` | Diagram is semantically broken or misleading; must fail the build |
| `major`   | Violates a mandatory modelling standard |
| `minor`   | Violates a recommended convention |
| `info`    | Advisory; improves maintainability |

**Rule ID scheme:** `<PACK><NNN>` — the pack prefix identifies the rule's scope:
a diagram type (SEQ, ACT, CLS, STA, UC), a cross-cutting concern (GEN governance,
XD cross-diagram), or a declared convention (`ARC` is reserved for architecture
conformance against a configured layer policy; no ARC rule is shipped).
IDs are stable once shipped; the spec follows the code, never the reverse.

**Reserved ranges:** `SEQ100–SEQ199` is reserved for the codegen-readiness profile
pack (SEQ101–SEQ109, shipped in v0.3.0, documented separately). `SEQ200–SEQ299`
is reserved for a structural flow pack (design spec on file, unqueued — see
ROADMAP *Settled questions*, obligation & flow checking). Base-catalog
sequence rules use `SEQ001–SEQ099`.

**Status legend:**
- ✅ **Implemented** — shipped, with the version
- ⏳ **Planned** — specified here, not yet implemented
- 🚫 **Blocked** — requires parser support that does not exist yet

**Scoping:** each rule declares `applies_to`. The linter detects the diagram type
from the first type-discriminating construct after `@startuml` (or an explicit
hint) and skips rules whose scope does not match.

---

## GEN — Governance rules

Cross-cutting governance checks. GEN001–GEN003 apply to every diagram type
(`applies_to: *`); GEN004 is sequence-scoped (it reasons about lifelines), and
GEN005 covers sequence and use-case diagrams.

### GEN001 — Diagram must have a title
**Severity:** minor · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** Untitled diagrams cannot be referenced unambiguously in reviews,
documentation, or SonarQube issue lists. A title is the diagram's primary key in
human communication.

```gherkin
Feature: GEN001 diagram must have a title

  Scenario: diagram without a title is reported
    Given the diagram:
      """
      @startuml demo
      participant Customer
      participant FrontOffice
      Customer -> FrontOffice : hello
      @enduml
      """
    When the linter runs
    Then a "GEN001" issue with severity "minor" is reported on line 1

  Scenario: diagram with a title passes
    Given the diagram:
      """
      @startuml demo
      title Order Processing
      participant Customer
      participant FrontOffice
      Customer -> FrontOffice : hello
      @enduml
      """
    When the linter runs
    Then no "GEN001" issue is reported
```

### GEN002 — Diagram name on @startuml
**Severity:** info · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** `@startuml my-diagram-name` gives the diagram a stable identity that
drives deterministic export filenames; a bare `@startuml` leaves rendered artifacts
named by position, which churn as diagrams are added or reordered.

```gherkin
Feature: GEN002 unnamed diagram

  Scenario: bare @startuml is reported
    Given the diagram:
      """
      @startuml
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then a "GEN002" issue with severity "info" is reported on line 1

  Scenario: named @startuml passes
    Given the diagram:
      """
      @startuml order-processing
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then no "GEN002" issue is reported
```

### GEN003 — No inline skinparam
**Severity:** minor · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** Per-diagram `skinparam` styling fragments the corporate style guide and
produces inconsistent rendered documentation. Styling belongs in a shared theme
`!include`. Option `allowed` whitelists skinparam prefixes tolerated inline.

```gherkin
Feature: GEN003 inline skinparam

  Scenario: inline skinparam is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      skinparam backgroundColor white
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then a "GEN003" issue with severity "minor" is reported on line 3

  Scenario: whitelisted skinparam passes
    Given the configuration:
      """
      [rules.GEN003]
      allowed = ["backgroundColor"]
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      skinparam backgroundColor white
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then no "GEN003" issue is reported
```

### GEN004 — Participant naming convention
**Severity:** minor · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** Declared participant names that disagree with the project convention
create friction between the model and the code it describes. Options: `pattern` (regex,
default PascalCase-with-dots) and `per_kind` (per participant-kind regex overrides).

```gherkin
Feature: GEN004 participant naming convention

  Scenario: name violating the pattern is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant front_office
      A -> front_office : hi
      @enduml
      """
    When the linter runs
    Then a "GEN004" issue with severity "minor" is reported on line 4

  Scenario: conforming name passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant FrontOffice
      A -> FrontOffice : hi
      @enduml
      """
    When the linter runs
    Then no "GEN004" issue is reported
```

### GEN005 — Participant count limit
**Severity:** minor · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** A diagram with too many elements on one canvas is doing too much and
becomes unreadable. The threshold is **per diagram type**, because the elements
being counted are not comparable: a sequence diagram counts *lifelines*
(default 9, split per phase or use `ref over` — which pumllint does not parse,
so the extracted file must be linted in its own right), while a use-case diagram counts
actors *plus* goals (default 15, split per actor goal or into packages). The two
shared a budget until a third-party corpus met it on first contact — three
actors with seven goals is a textbook-sized diagram, and 3 + 7 > 9 reported it.
Option `max` sets one threshold for every type; `per_type` (a map of diagram
type to limit) overrides it for one type and is the narrower of the two.
`per_type` is keyed by *diagram* type — GEN004's `per_kind` is keyed by
*participant* kind.

In use-case diagrams only *declared* elements count — link endpoints materialize
implicitly, and punishing an undeclared endpoint is UC-territory, not a size
question.

```gherkin
Feature: GEN005 participant count limit

  Scenario: diagram exceeding the participant limit is reported
    Given the configuration:
      """
      [rules.GEN005]
      max = 3
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant P0
      participant P1
      participant P2
      participant P3
      participant P4
      participant P5
      P0 -> P1 : hi
      @enduml
      """
    When the linter runs
    Then a "GEN005" issue with severity "minor" is reported on line 1

  Scenario: diagram within the limit passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant P0
      participant P1
      participant P2
      participant P3
      participant P4
      participant P5
      P0 -> P1 : hi
      @enduml
      """
    When the linter runs
    Then no "GEN005" issue is reported

  Scenario: use-case diagram exceeding the participant limit is reported
    Given the configuration:
      """
      [rules.GEN005]
      max = 3
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Place order)
      usecase (Cancel order)
      usecase (Track order)
      Customer --> (Place order) : does
      @enduml
      """
    When the linter runs
    Then a "GEN005" issue with severity "minor" is reported on line 1

  Scenario: implicit link endpoints do not count against the use-case limit
    Given the configuration:
      """
      [rules.GEN005]
      max = 3
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Place order)
      usecase (Cancel order)
      Customer --> (Refund order) : asks
      @enduml
      """
    When the linter runs
    Then no "GEN005" issue is reported

  Scenario: a textbook use-case diagram passes on the use-case budget
    Given the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      actor Support
      actor Auditor
      usecase (Place order)
      usecase (Cancel order)
      usecase (Track order)
      usecase (Refund order)
      usecase (Review order)
      usecase (Export orders)
      usecase (Audit orders)
      Customer --> (Place order) : does
      @enduml
      """
    When the linter runs
    Then no "GEN005" issue is reported

  Scenario: per_type overrides the budget for one diagram type
    Given the configuration:
      """
      [rules.GEN005.per_type]
      usecase = 3
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Place order)
      usecase (Cancel order)
      usecase (Track order)
      Customer --> (Place order) : does
      @enduml
      """
    When the linter runs
    Then a "GEN005" issue with severity "minor" is reported on line 1
```

### GEN006 — Ownership tag
**Severity:** minor · **Status:** ✅ Implemented (v0.12.0)

**Rationale:** A diagram nobody owns rots silently; an ownership tag (team,
maintainer) in the title, header, footer, caption or a note keeps it accountable.
There is no universal ownership convention, so the rule is dormant until option
`pattern` (regex) supplies the project's convention.

```gherkin
Feature: GEN006 ownership tag

  Scenario: diagram without an ownership tag is reported
    Given the configuration:
      """
      [rules.GEN006]
      pattern = '(?i)owner\s*:'
      """
    And the diagram:
      """
      @startuml payment-flow
      title Payment flow
      participant A
      participant B
      A -> B : pay
      @enduml
      """
    When the linter runs
    Then a "GEN006" issue with severity "minor" is reported on line 1

  Scenario: tagged diagram passes
    Given the configuration:
      """
      [rules.GEN006]
      pattern = '(?i)owner\s*:'
      """
    And the diagram:
      """
      @startuml payment-flow
      title Payment flow
      footer Owner: team-payments
      participant A
      participant B
      A -> B : pay
      @enduml
      """
    When the linter runs
    Then no "GEN006" issue is reported

  Scenario: without a configured pattern the rule is dormant
    Given the diagram:
      """
      @startuml payment-flow
      title Payment flow
      participant A
      participant B
      A -> B : pay
      @enduml
      """
    When the linter runs
    Then no "GEN006" issue is reported
```

### GEN007 — Requirement/ADR link
**Severity:** minor · **Status:** ✅ Implemented (v0.12.0)

**Rationale:** A diagram that realizes no traceable requirement or decision cannot
be checked against intent. Reference schemes are project-specific (`REQ-123`,
`ADR-0007`, ticket keys, URLs), so the rule is dormant until option `pattern`
(regex) supplies the scheme; the diagram name, title, header, footer, caption and
notes are searched.

```gherkin
Feature: GEN007 requirement link

  Scenario: diagram without a requirement reference is reported
    Given the configuration:
      """
      [rules.GEN007]
      pattern = 'REQ-\d+|ADR-\d+'
      """
    And the diagram:
      """
      @startuml payment-flow
      title Payment flow
      participant A
      participant B
      A -> B : pay
      @enduml
      """
    When the linter runs
    Then a "GEN007" issue with severity "minor" is reported on line 1

  Scenario: referenced diagram passes
    Given the configuration:
      """
      [rules.GEN007]
      pattern = 'REQ-\d+|ADR-\d+'
      """
    And the diagram:
      """
      @startuml payment-flow
      title Payment flow — realizes REQ-142
      participant A
      participant B
      A -> B : pay
      @enduml
      """
    When the linter runs
    Then no "GEN007" issue is reported
```

### GEN008 — Note density
**Severity:** minor · **Status:** ✅ Implemented (v0.12.0)

**Rationale:** Notes annotate; they should not carry the model. A diagram whose
structure is narrated in prose defeats both readers and downstream generators.
Options: `min_notes` (default 4 — smaller counts never fire) and `max_ratio`
(default 0.5 notes per semantic element). A third, opt-in length test —
`max_chars_per_element`, no default — fires when the total characters of note
prose exceed the cap × element count whatever the note count; it exists for
sets whose few notes carry the model in prose. Configuring it is a deliberate
scoring decision.

```gherkin
Feature: GEN008 note density

  Scenario: note-heavy diagram is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      note over A : step one
      note over A : step two
      note over B : step three
      note over B : step four
      @enduml
      """
    When the linter runs
    Then a "GEN008" issue with severity "minor" is reported on line 6

  Scenario: lightly annotated diagram passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      note over A : step one
      note over B : step two
      @enduml
      """
    When the linter runs
    Then no "GEN008" issue is reported

  Scenario: prose-heavy notes are reported when the length cap is configured
    Given the configuration:
      """
      [rules.GEN008]
      max_chars_per_element = 10
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      note over A : this single note narrates the whole protocol in long prose
      @enduml
      """
    When the linter runs
    Then a "GEN008" issue with severity "minor" is reported on line 6
```

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

The five size caps form one family and share an option convention — a new cap
rule takes `max`:

| Rule | Caps | Option | Default |
|---|---|---|---|
| GEN005 max-participants | participants | `max` | 9 |
| GEN009 max-elements | semantic elements | `max` | 60 |
| SEQ008 fragment-nesting-depth | fragment nesting depth | `max_nesting_depth` (alias `max`) | 3 |
| SEQ011 max-messages | messages | `max` | 30 |
| CLS005 max-members-per-class | members per class | `max` | 15 |

On ordinary sequence diagrams GEN009 is dominated by SEQ011: `element_count`
is participants + messages, so with ≤30 participants any diagram past 60
elements already has more than 30 messages, and both findings are
minor/DIM-RDB — the second carries no information the first did not. (The
dominance is conditional: 61 participants and no messages fires GEN009 alone.)

---

## SEQ — Sequence diagram rules (applies_to: sequence)

Base catalog `SEQ001–SEQ099`. The codegen-readiness profile pack (SEQ101–SEQ109,
v0.3.0) is specified separately and is dormant unless the `codegen` profile is
selected.

### SEQ001 — No undeclared participants
**Severity:** critical · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** Implicit participant creation hides typos (a misspelled participant
silently becomes a new lifeline) and defeats declaration-order control. Option
`only_if_any_declared` (default true) keeps the rule quiet in files that declare
nothing, so ad-hoc sketches aren't punished.

```gherkin
Feature: SEQ001 undeclared participants

  Scenario: message references an undeclared participant
    Given the diagram:
      """
      @startuml demo
      participant A
      participant B
      A -> C : ping
      @enduml
      """
    When the linter runs
    Then a "SEQ001" issue with severity "critical" is reported on line 4

  Scenario: all message endpoints are declared
    Given the diagram:
      """
      @startuml demo
      participant A
      participant B
      A -> B : ping
      @enduml
      """
    When the linter runs
    Then no "SEQ001" issue is reported
```

### SEQ002 — No unused participants
**Severity:** minor · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** A participant declared but never involved in any message or activation
is dead weight: it clutters the rendered lifelines and usually signals an incomplete
refactoring.

```gherkin
Feature: SEQ002 unused participants

  Scenario: declared participant never referenced is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      actor Customer
      participant FrontOffice
      participant Notary
      Customer -> FrontOffice : Submit
      @enduml
      """
    When the linter runs
    Then a "SEQ002" issue with severity "minor" is reported on line 5

  Scenario: every declared participant is used
    Given the diagram:
      """
      @startuml demo
      title Demo
      actor Customer
      participant FrontOffice
      Customer -> FrontOffice : Submit
      @enduml
      """
    When the linter runs
    Then no "SEQ002" issue is reported
```

### SEQ003 — Balanced activate/deactivate
**Severity:** major · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** Unbalanced activations render misleading lifeline bars and usually
indicate a missing return or copy-paste error — an unterminated flow. Covers
`activate`/`deactivate`/`return`/`destroy` and the `++`/`--` arrow shortcuts.

```gherkin
Feature: SEQ003 balanced activations

  Scenario: activate without matching deactivate
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      activate B
      @enduml
      """
    When the linter runs
    Then a "SEQ003" issue with severity "major" is reported on line 6

  Scenario: deactivate without a prior activate
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      deactivate B
      @enduml
      """
    When the linter runs
    Then a "SEQ003" issue with severity "major" is reported on line 6

  Scenario: balanced activation passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      activate B
      B --> A : ok
      deactivate B
      @enduml
      """
    When the linter runs
    Then no "SEQ003" issue is reported
```

### SEQ004 — All grouping blocks terminated
**Severity:** critical · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** An unterminated `alt`/`opt`/`loop`/`par`/`group`/`box` block changes the
meaning of everything that follows it; the diagram no longer says what the author
intended.

```gherkin
Feature: SEQ004 terminated blocks

  Scenario: alt block without end is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      alt happy
      A -> B : go
      @enduml
      """
    When the linter runs
    Then a "SEQ004" issue with severity "critical" is reported on line 5

  Scenario: properly nested and closed blocks pass
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      alt happy
      loop retry
      A -> B : go
      end
      end
      @enduml
      """
    When the linter runs
    Then no "SEQ004" issue is reported
```

### SEQ005 — Every message labelled
**Severity:** minor · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** An unlabelled arrow documents that communication happens but not what is
communicated — the diagram loses its specification value. Dotted return arrows are
tolerated by default (option `allow_unlabelled_returns`, default true).

```gherkin
Feature: SEQ005 message labels

  Scenario: message without a label is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B
      @enduml
      """
    When the linter runs
    Then a "SEQ005" issue with severity "minor" is reported on line 5

  Scenario: labelled message passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : requestQuote()
      @enduml
      """
    When the linter runs
    Then no "SEQ005" issue is reported

  Scenario: unlabelled dotted return is tolerated
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : query
      B --> A
      @enduml
      """
    When the linter runs
    Then no "SEQ005" issue is reported
```

### SEQ006 — No self-messages
**Severity:** minor · **Status:** ✅ Implemented (v0.2.0)

**Rationale:** Self-messages (`A -> A`) typically model internal computation, which
belongs in an activity diagram or a note — not on the interaction surface. Where a
self-call is genuinely intended, it can be suppressed inline.

```gherkin
Feature: SEQ006 no self-messages

  Scenario: self-message is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> A : recompute()
      @enduml
      """
    When the linter runs
    Then a "SEQ006" issue with severity "minor" is reported on line 5

  Scenario: message between distinct participants passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : recompute()
      @enduml
      """
    When the linter runs
    Then no "SEQ006" issue is reported
```

### SEQ007 — Unlabelled block condition
**Severity:** minor · **Status:** ✅ Implemented (v0.2.0)

**Rationale:** An `alt`/`opt`/`loop`/`break`/`critical` block without a condition/label
states that something happens conditionally or repeatedly without saying under which
condition. Option `kinds` overrides which block kinds require a label (`group` and `box`
may legitimately be bare).

```gherkin
Feature: SEQ007 unlabelled block condition

  Scenario: opt block without a condition is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      opt
      A -> B : go
      end
      @enduml
      """
    When the linter runs
    Then a "SEQ007" issue with severity "minor" is reported on line 5

  Scenario: loop with a condition passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      loop until queue empty
      A -> B : go
      end
      @enduml
      """
    When the linter runs
    Then no "SEQ007" issue is reported
```

### SEQ008 — Maximum fragment nesting depth
**Severity:** minor · **Status:** ✅ Implemented (v0.4.0)

**Rationale:** Deeply nested fragments (alt inside loop inside par …) are a
readability cliff; beyond a configurable depth the interaction should be extracted
into a referenced sub-diagram. Option `max_nesting_depth` (default 3); `max` is
accepted as an alias per the cap-family convention, and `max_nesting_depth`
wins when both are set.

```gherkin
Feature: SEQ008 fragment nesting depth

  Scenario: nesting beyond the configured depth is reported
    Given the configuration:
      """
      [rules.SEQ008]
      max_nesting_depth = 3
      """
    And the diagram:
      """
      @startuml demo
      participant A
      participant B
      alt cond1
      loop cond2
      opt cond3
      par cond4
      A -> B : ping
      end
      end
      end
      end
      @enduml
      """
    When the linter runs
    Then a "SEQ008" issue with severity "minor" is reported on line 7

  Scenario: nesting within the limit passes
    Given the configuration:
      """
      [rules.SEQ008]
      max_nesting_depth = 3
      """
    And the diagram:
      """
      @startuml demo
      participant A
      participant B
      alt cond1
      loop cond2
      A -> B : ping
      end
      end
      @enduml
      """
    When the linter runs
    Then no "SEQ008" issue is reported
```

### SEQ009 — Return messages pair with a call
**Severity:** minor · **Status:** ✅ Implemented (v0.4.0)

**Rationale:** A dashed return arrow (`-->`) with no preceding call in the opposite
direction usually indicates arrow-style misuse or a modelling error. This base rule
detects *orphans only*; strict reply discipline (naming the returned value) is the
codegen-profile rule SEQ109. Implementation can reuse `pair_calls_and_replies()`
from the v0.3.0 semantic model.

```gherkin
Feature: SEQ009 return messages pair with calls

  Scenario: orphaned return message is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      B --> A : result
      @enduml
      """
    When the linter runs
    Then a "SEQ009" issue with severity "minor" is reported on line 5

  Scenario: paired call and return pass
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : query
      B --> A : result
      @enduml
      """
    When the linter runs
    Then no "SEQ009" issue is reported
```

### SEQ010 — Explicit participant ordering
**Severity:** info · **Status:** ✅ Implemented (v0.4.0)

**Rationale:** When lifeline order is implied by first use, an innocent message
reordering reshuffles the whole diagram. Explicit declaration pins the layout.
Note: overlaps with SEQ001 when SEQ001 is enabled at blocker; SEQ010 exists for
configurations that relax SEQ001 but still want ordering pinned.

```gherkin
Feature: SEQ010 explicit participant ordering

  Scenario: participant introduced only by first use is flagged
    Given the configuration:
      """
      [rules.SEQ010]
      require_explicit_order = true
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      A -> B : go
      @enduml
      """
    When the linter runs
    Then a "SEQ010" issue with severity "info" is reported on line 4

  Scenario: all participants declared up front pass
    Given the configuration:
      """
      [rules.SEQ010]
      require_explicit_order = true
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      @enduml
      """
    When the linter runs
    Then no "SEQ010" issue is reported
```

### SEQ011 — Message count limit
**Severity:** minor · **Status:** ✅ Implemented (v0.12.0)

**Rationale:** Too many messages means the scenario is doing too much on one page —
the message-count twin of GEN005's participant limit. The finding is anchored on
the first message past the limit. Option `max` (default 30). On ordinary
sequence diagrams this rule dominates GEN009's element cap — see the
cap-family table under GEN009.

```gherkin
Feature: SEQ011 message count limit

  Scenario: diagram exceeding the message limit is reported
    Given the configuration:
      """
      [rules.SEQ011]
      max = 2
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : one
      B --> A : two
      A -> B : three
      @enduml
      """
    When the linter runs
    Then a "SEQ011" issue with severity "minor" is reported on line 7

  Scenario: diagram within the limit passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : one
      B --> A : two
      A -> B : three
      @enduml
      """
    When the linter runs
    Then no "SEQ011" issue is reported
```

---

## ACT — Activity diagram rules (applies_to: activity)

### ACT001 — Start node present
**Severity:** major · **Status:** ✅ Implemented (v0.2.0)

**Rationale:** An activity diagram with actions but no `start` node leaves the entry
point implicit — the reader cannot tell where the process begins. PlantUML renders it
anyway. (The rule flags a *missing* start; it does not yet detect duplicate starts.)

```gherkin
Feature: ACT001 start node present

  Scenario: diagram with actions but no start node is reported
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT001" issue with severity "major" is reported on line 3

  Scenario: diagram with a start node passes
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT001" issue is reported
```

### ACT002 — Flow terminates
**Severity:** major · **Status:** ✅ Implemented (v0.2.0)

**Rationale:** An activity flow that never reaches `stop`/`end` models a process that
never finishes — almost always an authoring omission. `kill`/`detach` count as
terminals (the parser folds them into `stop`/`end`); there is no option to
change that.

```gherkin
Feature: ACT002 flow terminates

  Scenario: diagram without any stop or end node is reported
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      @enduml
      """
    When the linter runs
    Then an "ACT002" issue with severity "major" is reported on line 8

  Scenario: diagram reaching a terminal passes
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT002" issue is reported
```

### ACT003 — Decision branches labelled
**Severity:** minor · **Status:** ✅ Implemented (v0.2.0)

**Rationale:** An `if`/`else` without branch labels ("yes"/"no" or guard text) does
not specify the decision logic — the core information an activity diagram carries.
Option `require_else_label` (default true) also flags a bare `else`.

```gherkin
Feature: ACT003 labelled decision branches

  Scenario: unlabelled then-branch is reported
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT003" issue with severity "minor" is reported on line 5

  Scenario: fully labelled decision passes
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT003" issue is reported
```

### ACT004 — Constructs terminated
**Severity:** critical · **Status:** ✅ Implemented (v0.2.0)

**Rationale:** An unclosed `if`/`while`/`repeat`/`fork`/`switch`/`partition` leaves the
flow dangling; the rendered diagram silently diverges from the intended semantics. The
activity twin of SEQ004 — PlantUML errors on some of these but tolerates others (notably
unclosed `partition` braces).

```gherkin
Feature: ACT004 terminated constructs

  Scenario: fork without end fork is reported
    Given the diagram:
      """
      @startuml pipeline
      title Pipeline
      start
      fork
      :Notify sales;
      fork again
      :Notify risk;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT004" issue with severity "critical" is reported on line 4

  Scenario: unclosed while is reported
    Given the diagram:
      """
      @startuml pipeline
      title Pipeline
      start
      while (more?) is (yes)
      :Process;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT004" issue with severity "critical" is reported on line 4

  Scenario: balanced constructs pass
    Given the diagram:
      """
      @startuml pipeline
      title Pipeline
      start
      fork
      :Notify sales;
      fork again
      :Notify risk;
      end fork
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT004" issue is reported
```

### ACT005 — Swimlane naming convention
**Severity:** minor · **Status:** ✅ Implemented (v0.4.0)

**Rationale:** Swimlanes represent organizational responsibility; inconsistent lane
names ("billing", "Billing dept.", "BILLING") fragment ownership mapping.

```gherkin
Feature: ACT005 swimlane naming convention

  Scenario: swimlane violating the configured pattern is reported
    Given the configuration:
      """
      [rules.ACT005]
      pattern = "^[A-Z][A-Za-z ]+$"
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      |billing|
      :Receive application;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT005" issue with severity "minor" is reported on line 4

  Scenario: conforming swimlane passes
    Given the configuration:
      """
      [rules.ACT005]
      pattern = "^[A-Z][A-Za-z ]+$"
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      |Billing|
      :Receive application;
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT005" issue is reported
```

### ACT006 — Activities phrased verb-first
**Severity:** minor · **Status:** ✅ Implemented (v0.4.0)

**Rationale:** The classic ARIS/EPC function convention: activities are named
"verb + object" ("Validate order"), keeping models action-oriented and uniform.

```gherkin
Feature: ACT006 verb-first activity names

  Scenario: noun-phrase activity is reported
    Given the configuration:
      """
      [rules.ACT006]
      verbs = ["Validate", "Receive", "Request", "Score"]
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Order validation;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT006" issue with severity "minor" is reported on line 6

  Scenario: verb-first activity passes
    Given the configuration:
      """
      [rules.ACT006]
      verbs = ["Receive", "Score", "Request"]
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT006" issue is reported
```

---

## CLS — Class diagram rules (applies_to: class)

**Pack status:** ✅ Implemented (v0.9.0) — `parser/class_.py` recognizes the
governance-relevant subset: `class`/`abstract class`/`interface`/`enum`
declarations (with alias and stereotype), brace bodies with members, the
`X : member` shorthand, and relation arrows with multiplicities and labels.

### CLS001 — Naming conventions for classes and members
**Severity:** minor · **Status:** ✅ Implemented (v0.9.0)

**Rationale:** Diagrams that disagree with the codebase's naming conventions create
friction between model and implementation; conventions are configurable per project.
Options: `class_pattern` (regex, default PascalCase) and `member_pattern` (regex,
default lower-case/underscore start). Enum members are exempt (constant conventions
vary too much to default).

```gherkin
Feature: CLS001 naming conventions

  Scenario: non-PascalCase class name is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class order_service
      @enduml
      """
    When the linter runs
    Then a "CLS001" issue with severity "minor" is reported on line 3

  Scenario: non-conforming member name is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class OrderService {
        +PlaceOrder()
      }
      @enduml
      """
    When the linter runs
    Then a "CLS001" issue with severity "minor" is reported on line 4

  Scenario: conforming names pass
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class OrderService {
        +placeOrder()
      }
      @enduml
      """
    When the linter runs
    Then no "CLS001" issue is reported
```

### CLS002 — Associations declare multiplicities
**Severity:** major · **Status:** ✅ Implemented (v0.9.0)

**Rationale:** An association without multiplicities omits the cardinality
constraint — often the most important design decision the diagram exists to record.
Applies to associations, aggregations and compositions; both ends must carry a
quoted multiplicity. Generalization/realization/dependency edges are exempt.
Presence only: the multiplicity *value* is not validated — any quoted string
satisfies the rule.

```gherkin
Feature: CLS002 association multiplicities

  Scenario: association without multiplicities is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Order -- Customer : places
      @enduml
      """
    When the linter runs
    Then a "CLS002" issue with severity "major" is reported on line 5

  Scenario: association with multiplicities passes
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Order "1..*" -- "1" Customer : places
      @enduml
      """
    When the linter runs
    Then no "CLS002" issue is reported
```

### CLS003 — Relationship labels on associations
**Severity:** minor · **Status:** ✅ Implemented (v0.9.0)

**Rationale:** Unlabelled associations state that two classes relate without saying
how; a role or verb label ("places", "owns") documents the intent. Plain
(including directed) associations only — aggregation, composition and
generalization already carry semantics in the arrow itself.

```gherkin
Feature: CLS003 relationship labels

  Scenario: unlabelled plain association is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Order "1..*" -- "1" Customer
      @enduml
      """
    When the linter runs
    Then a "CLS003" issue with severity "minor" is reported on line 5

  Scenario: labelled association passes
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Customer "1" -- "1..*" Order : places
      @enduml
      """
    When the linter runs
    Then no "CLS003" issue is reported
```

### CLS004 — No inheritance cycles
**Severity:** major · **Status:** ✅ Implemented (v0.9.0)

**Rationale:** A cyclic generalization hierarchy is semantically invalid UML and
uncompilable in any target language, yet PlantUML renders it without complaint.
Extension (`<|--`) and realization (`<|..`) edges both participate; the finding
cites the full cycle path.

```gherkin
Feature: CLS004 inheritance cycles

  Scenario: inheritance cycle is reported
    Given the diagram:
      """
      @startuml taxonomy
      title Taxonomy
      A <|-- B
      B <|-- C
      C <|-- A
      @enduml
      """
    When the linter runs
    Then a "CLS004" issue with severity "major" is reported on line 3

  Scenario: acyclic hierarchy passes
    Given the diagram:
      """
      @startuml taxonomy
      title Taxonomy
      A <|-- B
      A <|-- C
      @enduml
      """
    When the linter runs
    Then no "CLS004" issue is reported
```

### CLS005 — Member count limit per class
**Severity:** minor · **Status:** ✅ Implemented (v0.9.0)

**Rationale:** A class box with dozens of members is a "god class" smell in the
model just as in code, and unreadable when rendered. Option: `max` (default 15).

```gherkin
Feature: CLS005 member count limit

  Scenario: class exceeding the member limit is reported
    Given the configuration:
      """
      [rules.CLS005]
      max = 3
      """
    And the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order {
        +id: UUID
        +total: Money
        +lines: List
        +place()
      }
      @enduml
      """
    When the linter runs
    Then a "CLS005" issue with severity "minor" is reported on line 3

  Scenario: class within the limit passes
    Given the configuration:
      """
      [rules.CLS005]
      max = 3
      """
    And the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order {
        +id: UUID
        +place()
      }
      @enduml
      """
    When the linter runs
    Then no "CLS005" issue is reported
```

---

## STA — State diagram rules (applies_to: state)

**Pack status:** ✅ Implemented (v0.10.0) — `parser/state.py` recognizes the
governance-relevant subset: `state` declarations (with alias and stereotype),
composite `state Foo { ... }` bodies with concurrent-region separators, `[*]`
pseudo-state endpoints, and transition arrows with labels.

### STA001 — Exactly one initial state
**Severity:** blocker · **Status:** ✅ Implemented (v0.10.0)

**Rationale:** A state machine without a single unambiguous initial transition
(`[*] -->`) does not define where execution begins — and with two, it defines it
twice. Initial transitions inside composite-state bodies are those composites'
own entry points and do not count toward the top level.

```gherkin
Feature: STA001 exactly one initial state

  Scenario: missing initial transition is reported
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      state Open
      state Closed
      Open --> Closed : close
      @enduml
      """
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported on line 1

  Scenario: duplicate initial transitions are reported
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      [*] --> Closed
      Open --> Closed : close
      @enduml
      """
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported on line 4

  Scenario: single initial transition passes
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      Open --> Closed : close
      Closed --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA001" issue is reported

  Scenario: initial transitions inside composite states are not top-level
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Operating
      state Operating {
        [*] --> Idle
        Idle --> Busy : work
      }
      Operating --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA001" issue is reported
```

### STA002 — No states without an incoming transition
**Severity:** major · **Status:** ✅ Implemented (v0.10.0)

**Rationale:** A state with no incoming transition (and not the initial state) is
dead model content — typically a leftover from refactoring. Self-transitions do
not count as incoming: a state only reachable from itself is still dead. The
test is in-degree, not reachability from `[*]`: a group of states disconnected
from the initial state but pointing at each other is not reported.

```gherkin
Feature: STA002 unreachable states

  Scenario: state with no incoming transition is reported
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      Open --> [*]
      state Suspended
      @enduml
      """
    When the linter runs
    Then a "STA002" issue with severity "major" is reported on line 5

  Scenario: fully connected state machine passes
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      Open --> Closed : close
      Closed --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA002" issue is reported
```

### STA003 — Transitions labelled with event/guard/action
**Severity:** minor · **Status:** ✅ Implemented (v0.10.0)

**Rationale:** An unlabelled transition says a state change can occur but not what
triggers it; the convention `event [guard] / action` keeps machines specifiable.
Initial and final transitions (`[*]` endpoints) are conventionally unlabelled and
exempt.

```gherkin
Feature: STA003 labelled transitions

  Scenario: unlabelled transition is reported
    Given the diagram:
      """
      @startuml device
      title Device power
      [*] --> Idle
      Idle --> Active
      Active --> [*]
      @enduml
      """
    When the linter runs
    Then a "STA003" issue with severity "minor" is reported on line 4

  Scenario: labelled transition passes
    Given the diagram:
      """
      @startuml device
      title Device power
      [*] --> Idle
      Idle --> Active : powerOn [selfTestOk]
      Active --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA003" issue is reported
```

---

## UC — Use case diagram rules (applies_to: usecase)

### UC001 — No orphan actors or use cases
**Severity:** major · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** An actor or use case participating in no relationship delivers
value to nobody — it should not exist. The check is membership, not
reachability: any link counts, so a use case connected only to another use
case (e.g. via include/extend) is linked even with no actor path to it, and
a diagram with no links at all is not examined.

```gherkin
Feature: UC001 use cases connected to actors

  Scenario: disconnected use case is reported
    Given the diagram:
      """
      @startuml uc
      title Use cases
      :Customer: as Customer
      :Auditor: as Auditor
      usecase (Submit application) as Submit
      Customer --> Submit : initiates
      @enduml
      """
    When the linter runs
    Then a "UC001" issue with severity "major" is reported on line 4

  Scenario: directly connected actor and use case pass
    Given the diagram:
      """
      @startuml uc
      title Use cases
      :Customer: as Customer
      usecase (Submit application) as Submit
      Customer --> Submit : initiates
      @enduml
      """
    When the linter runs
    Then no "UC001" issue is reported
```

### UC002 — Use case and actor naming
**Severity:** minor · **Status:** ✅ Implemented (v0.4.0)

**Rationale:** Use cases as verb–object phrases ("Place order") is the standard
method convention; mixing forms confuses reading. Only use-case names are
checked — actor naming is a convention the rule does not enforce — and the
rule is dormant until a `verbs` whitelist is configured. A use case declared
with an alias (`usecase (Place order) as UC1`) is judged by its display
label, never by the alias.

```gherkin
Feature: UC002 use case and actor naming

  Scenario: noun-phrase use case is reported
    Given the configuration:
      """
      [rules.UC002]
      verbs = ["Place", "Manage"]
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Order placement)
      Customer --> (Order placement) : does
      @enduml
      """
    When the linter runs
    Then a "UC002" issue with severity "minor" is reported on line 4

  Scenario: conforming names pass
    Given the configuration:
      """
      [rules.UC002]
      verbs = ["Place"]
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Place order)
      Customer --> (Place order) : does
      @enduml
      """
    When the linter runs
    Then no "UC002" issue is reported

  Scenario: an aliased use case is judged by its label, not the alias
    Given the configuration:
      """
      [rules.UC002]
      verbs = ["Place", "Manage"]
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Order placement) as UC1
      Customer --> UC1 : does
      @enduml
      """
    When the linter runs
    Then a "UC002" issue with severity "minor" is reported on line 4
```

### UC003 — Correct include/extend direction
**Severity:** minor · **Status:** ✅ Implemented (v0.11.0)

**Rationale:** `<<include>>` points from base to included case; `<<extend>>` points
from extension to base. Reversed stereotypes are a frequent and silent modelling
error. Both relate use cases only — an actor endpoint is always wrong. Direction
is judged against actor connectivity (the base case is the one an actor reaches
through a plain association) and only when that evidence is unambiguous: exactly
one endpoint actor-connected. Arrows written right-to-left (`A <.. B`) are
normalized before judging. The evidence recognizes only declared actors — the
`:Name:` form or an `actor` declaration; an endpoint written as a bare
identifier is not typed as an actor, and the rule stays silent for want of
evidence.

```gherkin
Feature: UC003 include and extend direction

  Scenario: reversed extend arrow is reported
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: --> (Checkout)
      (Checkout) ..> (Apply coupon) : <<extend>>
      @enduml
      """
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on line 5

  Scenario: reversed include arrow is reported
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: --> (Checkout)
      (Validate cart) ..> (Checkout) : <<include>>
      @enduml
      """
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on line 5

  Scenario: include or extend involving an actor is reported
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: ..> (Checkout) : <<include>>
      @enduml
      """
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on line 4

  Scenario: correct directions pass
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: --> (Checkout)
      (Checkout) ..> (Validate cart) : <<include>>
      (Apply coupon) ..> (Checkout) : <<extend>>
      @enduml
      """
    When the linter runs
    Then no "UC003" issue is reported
```

---

## XD — Cross-diagram consistency rules (cross-diagram)

XD rules build an entity symbol table across the lint batch: the same entity
must keep one identity — one declaration kind, one stereotype, one spelling.
XD001–003 walk the participant tables of sequence diagrams; XD004–005
(v0.13.0) span diagram *types* — sequence/use-case participants, class
classifiers and activity swimlanes name entities, while state names stay out
on purpose (states are modes of an entity, not entities). All activate only
when more than one diagram is linted (SCORING.md §6); single-diagram runs
score DIM-CON from naming rules alone. For XD001/XD002/XD005 **no side is
elected**: every conflicted site is reported symmetrically, each message
listing every variant with counts, because electing a majority indicts the
conforming sites once a drift has spread (issue #36, v0.29.0). The per-entity
`authoritative` option pins the intended value; with it set, only the
non-conforming sites are reported. XD003/XD004 flag later case-variants of
the first-seen spelling. Every XD rule also accepts a `distinct` list — the
negative form of `authoritative`: names listed there are deliberately
*different* entities that happen to share a spelling (a bounded-context
`Order` here, a work-order `Order` there), so no cross-diagram comparison
applies to them (XD003/XD004 match case-insensitively, like their joins).
Declarations pumllint cannot see are a separate concern: the preprocessor is
never expanded, so a diagram whose declarations live behind `!include` parses
with only implicit entities and every XD rule goes quiet — the CLI disclosure
warning (stderr, exit codes untouched) says so per run.

### XD001 — Conflicting participant kind
**Severity:** major · **Status:** ✅ Implemented (v0.5.0)

**Rationale:** The same entity declared as `participant` in one diagram and
`database` (or `actor`, `queue`, …) in another has no single identity; readers
and code generators cannot tell which role is authoritative. Implicit
lifelines are ignored — they have no authored kind to conflict. A conflict is
symmetric evidence: every conflicted site is reported, each message listing
all variants with counts, and no side is elected — a majority vote indicts
the conforming sites once a drift has spread. The per-entity `authoritative`
option (`authoritative = {OrderSvc = "database"}`) pins the intended value:
with it set, only non-conforming sites are reported. The pin resolves
conflicts only — an entity whose sites all agree is never compared against it.

```gherkin
Feature: XD001 conflicting participant kind

  Scenario: same entity declared with different kinds across diagrams
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      database OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then a "XD001" issue with severity "major" is reported on line 3
    And a "XD001" issue with severity "major" is reported on line 8

  Scenario: an authoritative kind reports only the non-conforming site
    Given the configuration:
      """
      [rules.XD001]
      authoritative = {OrderSvc = "database"}
      """
    And the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      database OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then a "XD001" issue is reported on line 3
    And no "XD001" issue is reported on line 8

  Scenario: consistent kinds across diagrams pass
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      participant OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then no "XD001" issue is reported

  Scenario: a distinct entity is never compared
    Given the configuration:
      """
      [rules.XD001]
      distinct = ["OrderSvc"]
      """
    And the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      database OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then no "XD001" issue is reported
```

### XD002 — Conflicting participant stereotype
**Severity:** minor · **Status:** ✅ Implemented (v0.5.0)

**Rationale:** Stereotypes carry semantic weight (SEQ107 keys failure-path
requirements off `<<external>>`); the same entity stereotyped `<<service>>`
here and `<<external>>` there splits its identity. A missing stereotype is not
a conflict — that is SEQ102's concern under the codegen profile. As in XD001,
every conflicted site is reported symmetrically (all variants with counts, no
side elected), and the per-entity `authoritative` option
(`authoritative = {Payments = "service"}`) pins the intended stereotype so
only non-conforming sites are reported. The pin resolves conflicts only.

```gherkin
Feature: XD002 conflicting participant stereotype

  Scenario: same entity stereotyped differently across diagrams
    Given the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<external>>
      participant Client
      Client -> Payments : refund()
      @enduml
      """
    When the linter runs
    Then a "XD002" issue with severity "minor" is reported on line 2
    And a "XD002" issue with severity "minor" is reported on line 7

  Scenario: an authoritative stereotype reports only the non-conforming site
    Given the configuration:
      """
      [rules.XD002]
      authoritative = {Payments = "service"}
      """
    And the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<external>>
      participant Client
      Client -> Payments : refund()
      @enduml
      """
    When the linter runs
    Then a "XD002" issue is reported on line 7
    And no "XD002" issue is reported on line 2

  Scenario: consistent stereotypes across diagrams pass
    Given the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<service>>
      participant Client
      Client -> Payments : refund()
      @enduml
      """
    When the linter runs
    Then no "XD002" issue is reported

  Scenario: a distinct entity is never compared
    Given the configuration:
      """
      [rules.XD002]
      distinct = ["Payments"]
      """
    And the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<external>>
      participant Client
      Client -> Payments : pay()
      @enduml
      """
    When the linter runs
    Then no "XD002" issue is reported
```

### XD003 — Participant name case collision
**Severity:** minor · **Status:** ✅ Implemented (v0.5.0)

**Rationale:** `OrderSvc` in one diagram and `Ordersvc` in another are almost
certainly the same entity spelled differently — PlantUML treats them as two
lifelines, so the model silently forks the entity's identity. Implicit
participants are included: spelling drift usually enters via arrows.

```gherkin
Feature: XD003 participant name case collision

  Scenario: names differing only by case across diagrams
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      participant Ordersvc
      Client -> Ordersvc : query()
      @enduml
      """
    When the linter runs
    Then a "XD003" issue with severity "minor" is reported on line 8

  Scenario: identical spelling across diagrams passes
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      participant OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then no "XD003" issue is reported

  Scenario: a distinct name is exempt from case-collision, case-insensitively
    Given the configuration:
      """
      [rules.XD003]
      distinct = ["LEDGER"]
      """
    And the diagram:
      """
      @startuml one
      participant Ledger
      Ledger -> Ledger : sweep()
      @enduml
      @startuml two
      participant ledger
      ledger -> ledger : sweep()
      @enduml
      """
    When the linter runs
    Then no "XD003" issue is reported
```

### XD004 — Cross-type name collision
**Severity:** minor · **Status:** ✅ Implemented (v0.13.0)

**Rationale:** A class `OrderService` next to a sequence lifeline `orderService`
is almost certainly the same entity drifting apart across models. First-seen
spelling is authoritative; pairs where both sites are sequence participants are
XD003's territory and skipped here.

```gherkin
Feature: XD004 cross-type name collision

  Scenario: class and sequence participant differ only by case
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant orderService
      participant Client
      Client -> orderService : place()
      @enduml
      """
    When the linter runs
    Then a "XD004" issue with severity "minor" is reported on line 9

  Scenario: consistent spelling across types passes
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant OrderService
      participant Client
      Client -> OrderService : place()
      @enduml
      """
    When the linter runs
    Then no "XD004" issue is reported

  Scenario: a distinct name is exempt from cross-type collision, case-insensitively
    Given the configuration:
      """
      [rules.XD004]
      distinct = ["orderservice"]
      """
    And the diagram:
      """
      @startuml classes
      class OrderService
      @enduml
      @startuml seq
      participant orderService
      participant Client
      Client -> orderService : run()
      @enduml
      """
    When the linter runs
    Then no "XD004" issue is reported
```

### XD005 — Cross-type stereotype conflict
**Severity:** minor · **Status:** ✅ Implemented (v0.13.0)

**Rationale:** `class OrderService <<service>>` versus `participant OrderService
<<gateway>>` is one entity with two contracts; downstream generators cannot tell
which is authoritative. Every conflicted site is reported symmetrically (all
variants with counts, no side elected), and the per-entity `authoritative`
option pins the intended stereotype, as in XD001/XD002; conflicts confined
to sequence diagrams are XD002's territory and skipped here.

```gherkin
Feature: XD005 cross-type stereotype conflict

  Scenario: class and sequence stereotypes disagree
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService <<service>>
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant OrderService <<gateway>>
      participant Client
      Client -> OrderService : place()
      @enduml
      """
    When the linter runs
    Then a "XD005" issue with severity "minor" is reported on line 3
    And a "XD005" issue with severity "minor" is reported on line 9

  Scenario: agreeing stereotypes pass
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService <<service>>
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant OrderService <<service>>
      participant Client
      Client -> OrderService : place()
      @enduml
      """
    When the linter runs
    Then no "XD005" issue is reported

  Scenario: bounded-context homonyms declared distinct are never compared
    Given the configuration:
      """
      [rules.XD005]
      distinct = ["Order"]
      """
    And the diagram:
      """
      @startuml sales
      class Order <<aggregate>>
      @enduml
      @startuml checkout
      participant Order <<work-order>>
      participant Client
      Client -> Order : place()
      @enduml
      """
    When the linter runs
    Then no "XD005" issue is reported
```

## Rule summary

| ID | Severity | Scope | Summary | Status |
|----|----------|-------|---------|--------|
| GEN001 | minor | * | Diagram title required | ✅ v0.1.0 |
| GEN002 | info | * | Diagram name on @startuml | ✅ v0.1.0 |
| GEN003 | minor | * | No inline skinparam | ✅ v0.1.0 |
| GEN004 | minor | sequence | Participant naming convention | ✅ v0.1.0 |
| GEN005 | minor | sequence, usecase | Participant count limit | ✅ v0.1.0 |
| GEN006 | minor | * | Ownership tag (pattern-gated) | ✅ v0.12.0 |
| GEN007 | minor | * | Requirement/ADR link (pattern-gated) | ✅ v0.12.0 |
| GEN008 | minor | * | Note density | ✅ v0.12.0 |
| GEN009 | minor | * | Element count limit | ✅ v0.12.0 |
| SEQ001 | critical | sequence | No undeclared participants | ✅ v0.1.0 |
| SEQ002 | minor | sequence | No unused participants | ✅ v0.1.0 |
| SEQ003 | major | sequence | Balanced activate/deactivate | ✅ v0.1.0 |
| SEQ004 | critical | sequence | Grouping blocks terminated | ✅ v0.1.0 |
| SEQ005 | minor | sequence | Messages labelled | ✅ v0.1.0 |
| SEQ006 | minor | sequence | No self-messages | ✅ v0.2.0 |
| SEQ007 | minor | sequence | Unlabelled block condition | ✅ v0.2.0 |
| SEQ008 | minor | sequence | Max fragment nesting depth | ✅ v0.4.0 |
| SEQ009 | minor | sequence | Returns pair with calls | ✅ v0.4.0 |
| SEQ010 | info | sequence | Explicit participant ordering | ✅ v0.4.0 |
| SEQ011 | minor | sequence | Message count limit | ✅ v0.12.0 |
| ACT001 | major | activity | Start node present | ✅ v0.2.0 |
| ACT002 | major | activity | Flow terminates | ✅ v0.2.0 |
| ACT003 | minor | activity | Decision branches labelled | ✅ v0.2.0 |
| ACT004 | critical | activity | Constructs terminated | ✅ v0.2.0 |
| ACT005 | minor | activity | Swimlane naming | ✅ v0.4.0 |
| ACT006 | minor | activity | Verb-first activity names | ✅ v0.4.0 |
| CLS001 | minor | class | Naming conventions | ✅ v0.9.0 |
| CLS002 | major | class | Multiplicities required | ✅ v0.9.0 |
| CLS003 | minor | class | Relationship labels | ✅ v0.9.0 |
| CLS004 | major | class | No inheritance cycles | ✅ v0.9.0 |
| CLS005 | minor | class | Member count limit | ✅ v0.9.0 |
| STA001 | blocker | state | Exactly one initial state | ✅ v0.10.0 |
| STA002 | major | state | No unreachable states | ✅ v0.10.0 |
| STA003 | minor | state | Transitions labelled | ✅ v0.10.0 |
| UC001 | major | usecase | Use cases connected to actors | ✅ v0.1.0 |
| UC002 | minor | usecase | Verb–object use cases, noun actors | ✅ v0.4.0 |
| UC003 | minor | usecase | Include/extend direction | ✅ v0.11.0 |
| XD001 | major | sequence (cross) | Conflicting participant kind | ✅ v0.5.0 |
| XD002 | minor | sequence (cross) | Conflicting participant stereotype | ✅ v0.5.0 |
| XD003 | minor | sequence (cross) | Participant name case collision | ✅ v0.5.0 |
| XD004 | minor | * (cross) | Cross-type name collision | ✅ v0.13.0 |
| XD005 | minor | * (cross) | Cross-type stereotype conflict | ✅ v0.13.0 |

**Totals:** 42 base-catalog rules — **all 42 implemented** (SEQ008/009/010,
ACT005/006 and UC002 shipped in v0.4.0; XD001–003 cross-diagram consistency in
v0.5.0; CLS001–005 class pack in v0.9.0; STA001–003 state pack in v0.10.0;
UC003 in v0.11.0 closed the original catalog; GEN006–009 and SEQ011 thickened
DIM-TRC/DIM-RDB in v0.12.0 — GEN006/007 are convention-gated and dormant until
a pattern is configured; XD004–005 cross-*type* entity identity in v0.13.0).
Separately: SEQ101–SEQ109 codegen profile pack, ✅ v0.3.0.

## Implementation notes

- **ID stability:** SEQ006/SEQ007 keep their shipped v0.2.0 meanings
  (no-self-message, unlabelled-block-condition). The formerly drafted
  nesting-depth and return-pairing rules were renumbered to SEQ008/SEQ009, and
  explicit-ordering to SEQ010. The spec follows the code.
- **Guard/label rules:** SEQ005 is `unlabelled-message` (arrow has no colon label);
  SEQ007 is `unlabelled-block-condition` (a fragment has no guard). They inspect
  different constructs and never double-report a line. SEQ007 covers
  `alt`/`opt`/`loop`/`break`/`critical` by default (option `kinds`).
- **SEQ009 vs SEQ109:** the base rule stays lenient (orphaned returns only); the
  codegen profile's SEQ109 enforces strict reply discipline (dashed arrow + named
  value). Both can build on `pair_calls_and_replies()`.
- **Type detection:** infer diagram type from the first discriminating construct
  after `@startuml`; activity parsing only engages while the type is
  `unknown`/`activity`, per the existing parser contract. The class parser
  (v0.9.0) follows the same never-re-type discipline: its markers are classifier
  declarations (`class`/`abstract class`/`interface`/`enum`) and generalization
  arrows (`<|--` and friends — no other diagram form uses `<|`); ambiguous plain
  arrows (`A --> B`) bind as class relations only once the diagram is already
  typed `class`, so sequence messages keep their meaning. The state parser
  (v0.10.0) does the same with the `state` keyword and `[*]` pseudo-state as its
  markers.
- **Registry:** rules declare `applies_to` via the existing decorator; blocked
  rules should not be registered until their parser exists (avoid dead
  registrations surfacing in `--list-rules`).
- **Suppression:** inline `' pumllint: disable=…` and `disable-file` apply to all
  rules, per v0.2.0 semantics.
- **Reporting:** severity maps directly onto the SonarQube Generic Issue Import
  Format severity field; rule IDs become `ruleId`, rationale text becomes the rule
  description.
