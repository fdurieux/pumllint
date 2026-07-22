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

**Rule ID scheme:** `<PACK><NNN>` — pack prefix identifies the diagram type scope.
IDs are stable once shipped; the spec follows the code, never the reverse.

**Reserved ranges:** `SEQ100–SEQ199` is reserved for the codegen-readiness profile
pack (SEQ101–SEQ109, shipped in v0.3.0, documented separately). Base-catalog
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
(`applies_to: *`); GEN004–GEN005 are sequence-scoped (they reason about lifelines).

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

**Rationale:** A sequence diagram with too many lifelines is doing too much and becomes
unreadable; it should be split per phase or use `ref over`. Option `max` (default 9)
sets the threshold.

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
```

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
into a referenced sub-diagram.

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
never finishes — almost always an authoring omission. Option `accept_detach` (default
true) treats `kill`/`detach` as terminals too.

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

**Pack status:** 🚫 Blocked — requires class diagram parsing, which is not yet
implemented (`parser/class_.py` does not exist; listed under "ideas not yet done").

### CLS001 — Naming conventions for classes and members
**Severity:** minor · **Status:** 🚫 Blocked (no class parser)

**Rationale:** Diagrams that disagree with the codebase's naming conventions create
friction between model and implementation; conventions are configurable per project.

```gherkin
Feature: CLS001 naming conventions

  Scenario: non-PascalCase class name is reported
    Given a configuration requiring PascalCase class names
    And a class diagram declaring "class order_service"
    When the linter runs
    Then a "CLS001" issue with severity "minor" is reported on the declaration

  Scenario: conforming names pass
    Given the same configuration
    And a class diagram declaring "class OrderService" with member "placeOrder()"
    When the linter runs
    Then no "CLS001" issue is reported
```

### CLS002 — Associations declare multiplicities
**Severity:** major · **Status:** 🚫 Blocked (no class parser)

**Rationale:** An association without multiplicities omits the cardinality
constraint — often the most important design decision the diagram exists to record.

```gherkin
Feature: CLS002 association multiplicities

  Scenario: association without multiplicities is reported
    Given a class diagram containing 'Order -- Customer'
    When the linter runs
    Then a "CLS002" issue with severity "major" is reported on that line

  Scenario: association with multiplicities passes
    Given a class diagram containing 'Order "1..*" -- "1" Customer'
    When the linter runs
    Then no "CLS002" issue is reported
```

### CLS003 — Relationship labels on associations
**Severity:** minor · **Status:** 🚫 Blocked (no class parser)

**Rationale:** Unlabelled associations state that two classes relate without saying
how; a role or verb label ("places", "owns") documents the intent.

```gherkin
Feature: CLS003 relationship labels

  Scenario: unlabelled plain association is reported
    Given a class diagram containing 'Order "1..*" -- "1" Customer' with no label
    When the linter runs
    Then a "CLS003" issue with severity "minor" is reported on that line

  Scenario: labelled association passes
    Given a class diagram containing 'Customer "1" -- "1..*" Order : places'
    When the linter runs
    Then no "CLS003" issue is reported
```

### CLS004 — No inheritance cycles
**Severity:** major · **Status:** 🚫 Blocked (no class parser)

**Rationale:** A cyclic generalization hierarchy is semantically invalid UML and
uncompilable in any target language, yet PlantUML renders it without complaint.

```gherkin
Feature: CLS004 inheritance cycles

  Scenario: inheritance cycle is reported
    Given a class diagram containing "A <|-- B", "B <|-- C", and "C <|-- A"
    When the linter runs
    Then a "CLS004" issue with severity "major" is reported citing the cycle

  Scenario: acyclic hierarchy passes
    Given a class diagram containing "A <|-- B" and "A <|-- C"
    When the linter runs
    Then no "CLS004" issue is reported
```

### CLS005 — Member count limit per class
**Severity:** minor · **Status:** 🚫 Blocked (no class parser)

**Rationale:** A class box with dozens of members is a "god class" smell in the
model just as in code, and unreadable when rendered.

```gherkin
Feature: CLS005 member count limit

  Scenario: class exceeding the member limit is reported
    Given a configuration with "max_members_per_class" set to 15
    And a class declaring 16 attributes and methods combined
    When the linter runs
    Then a "CLS005" issue with severity "minor" is reported on the class

  Scenario: class within the limit passes
    Given the same configuration and a class with 8 members
    When the linter runs
    Then no "CLS005" issue is reported
```

---

## STA — State diagram rules (applies_to: state)

**Pack status:** 🚫 Blocked — requires state diagram parsing, which is not yet
implemented.

### STA001 — Exactly one initial state
**Severity:** blocker · **Status:** 🚫 Blocked (no state parser)

**Rationale:** A state machine without a single unambiguous initial transition
(`[*] -->`) does not define where execution begins.

```gherkin
Feature: STA001 exactly one initial state

  Scenario: missing initial transition is reported
    Given a state diagram with no "[*] -->" transition at the top level
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported

  Scenario: duplicate initial transitions are reported
    Given a state diagram with two top-level "[*] -->" transitions
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported on the second one

  Scenario: single initial transition passes
    Given a state diagram with exactly one top-level "[*] --> Idle"
    When the linter runs
    Then no "STA001" issue is reported
```

### STA002 — No unreachable states
**Severity:** major · **Status:** 🚫 Blocked (no state parser)

**Rationale:** A state with no incoming transition (and not the initial state) is
dead model content — typically a leftover from refactoring.

```gherkin
Feature: STA002 unreachable states

  Scenario: state with no incoming transition is reported
    Given a state diagram declaring state "Suspended"
    And no transition targets "Suspended"
    When the linter runs
    Then a "STA002" issue with severity "major" is reported on the declaration

  Scenario: fully connected state machine passes
    Given a state diagram where every state is reachable from "[*]"
    When the linter runs
    Then no "STA002" issue is reported
```

### STA003 — Transitions labelled with event/guard/action
**Severity:** minor · **Status:** 🚫 Blocked (no state parser)

**Rationale:** An unlabelled transition says a state change can occur but not what
triggers it; the convention `event [guard] / action` keeps machines specifiable.

```gherkin
Feature: STA003 labelled transitions

  Scenario: unlabelled transition is reported
    Given a state diagram containing "Idle --> Active" with no label
    When the linter runs
    Then a "STA003" issue with severity "minor" is reported on that line

  Scenario: labelled transition passes
    Given a state diagram containing "Idle --> Active : powerOn [selfTestOk]"
    When the linter runs
    Then no "STA003" issue is reported
```

---

## UC — Use case diagram rules (applies_to: usecase)

### UC001 — Every use case connected to an actor
**Severity:** major · **Status:** ✅ Implemented (v0.1.0)

**Rationale:** A use case that no actor (directly or transitively via
include/extend) can reach delivers value to nobody — it should not exist.

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

**Rationale:** Use cases as verb–object phrases ("Place order") and actors as
nouns ("Customer") is the standard method convention; mixing forms confuses reading.

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
```

### UC003 — Correct include/extend direction
**Severity:** minor · **Status:** 🚫 Blocked (needs include/extend parsing)

**Rationale:** `<<include>>` points from base to included case; `<<extend>>` points
from extension to base. Reversed stereotypes are a frequent and silent modelling
error.

```gherkin
Feature: UC003 include and extend direction

  Scenario: reversed extend arrow is reported
    Given a use case diagram where the base case points to the extension with "<<extend>>"
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on that relationship

  Scenario: correct directions pass
    Given "(Checkout) ..> (Validate cart) : <<include>>"
    And "(Apply coupon) ..> (Checkout) : <<extend>>"
    When the linter runs
    Then no "UC003" issue is reported
```

---

## XD — Cross-diagram consistency rules (applies_to: sequence, cross-diagram)

XD rules build a participant symbol table across every sequence diagram in the
lint batch: the same entity must keep one identity — one declaration kind, one
stereotype, one spelling. They activate only when more than one diagram is
linted (SCORING.md §6); single-diagram runs score DIM-CON from naming rules
alone. For XD001/XD002 the **majority declaration wins** (ties resolve to the
first-seen form): violations are attributed to the *minority* sites and
reference an authoritative majority site, so a single outlier never indicts
the conforming rest. XD003 flags later case-variants of the first-seen
spelling.

### XD001 — Conflicting participant kind
**Severity:** major · **Status:** ✅ Implemented (v0.5.0)

**Rationale:** The same entity declared as `participant` in one diagram and
`database` (or `actor`, `queue`, …) in another has no single identity; readers
and code generators cannot tell which role is authoritative. Implicit
lifelines are ignored — they have no authored kind to conflict.

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
    Then a "XD001" issue with severity "major" is reported on line 8

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
```

### XD002 — Conflicting participant stereotype
**Severity:** minor · **Status:** ✅ Implemented (v0.5.0)

**Rationale:** Stereotypes carry semantic weight (SEQ107 keys failure-path
requirements off `<<external>>`); the same entity stereotyped `<<service>>`
here and `<<external>>` there splits its identity. A missing stereotype is not
a conflict — that is SEQ102's concern under the codegen profile.

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
    Then a "XD002" issue with severity "minor" is reported on line 7

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
```

## Rule summary

| ID | Severity | Scope | Summary | Status |
|----|----------|-------|---------|--------|
| GEN001 | minor | * | Diagram title required | ✅ v0.1.0 |
| GEN002 | info | * | Diagram name on @startuml | ✅ v0.1.0 |
| GEN003 | minor | * | No inline skinparam | ✅ v0.1.0 |
| GEN004 | minor | sequence | Participant naming convention | ✅ v0.1.0 |
| GEN005 | minor | sequence | Participant count limit | ✅ v0.1.0 |
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
| ACT001 | major | activity | Start node present | ✅ v0.2.0 |
| ACT002 | major | activity | Flow terminates | ✅ v0.2.0 |
| ACT003 | minor | activity | Decision branches labelled | ✅ v0.2.0 |
| ACT004 | critical | activity | Constructs terminated | ✅ v0.2.0 |
| ACT005 | minor | activity | Swimlane naming | ✅ v0.4.0 |
| ACT006 | minor | activity | Verb-first activity names | ✅ v0.4.0 |
| CLS001 | minor | class | Naming conventions | 🚫 parser |
| CLS002 | major | class | Multiplicities required | 🚫 parser |
| CLS003 | minor | class | Relationship labels | 🚫 parser |
| CLS004 | major | class | No inheritance cycles | 🚫 parser |
| CLS005 | minor | class | Member count limit | 🚫 parser |
| STA001 | blocker | state | Exactly one initial state | 🚫 parser |
| STA002 | major | state | No unreachable states | 🚫 parser |
| STA003 | minor | state | Transitions labelled | 🚫 parser |
| UC001 | major | usecase | Use cases connected to actors | ✅ v0.1.0 |
| UC002 | minor | usecase | Verb–object use cases, noun actors | ✅ v0.4.0 |
| UC003 | minor | usecase | Include/extend direction | 🚫 (needs include/extend parsing) |
| XD001 | major | sequence (cross) | Conflicting participant kind | ✅ v0.5.0 |
| XD002 | minor | sequence (cross) | Conflicting participant stereotype | ✅ v0.5.0 |
| XD003 | minor | sequence (cross) | Participant name case collision | ✅ v0.5.0 |

**Totals:** 35 base-catalog rules — 26 implemented (SEQ008/009/010, ACT005/006 and
UC002 shipped in v0.4.0; XD001–003 cross-diagram consistency in v0.5.0), 9 blocked
on new parsers (CLS×5, STA×3) or parser extensions (UC003). Separately:
SEQ101–SEQ109 codegen profile pack, ✅ v0.3.0.

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
  `unknown`/`activity`, per the existing parser contract. New CLS/STA parsers must
  follow the same never-re-type discipline.
- **Registry:** rules declare `applies_to` via the existing decorator; blocked
  rules should not be registered until their parser exists (avoid dead
  registrations surfacing in `--list-rules`).
- **Suppression:** inline `' pumllint: disable=…` and `disable-file` apply to all
  rules, per v0.2.0 semantics.
- **Reporting:** severity maps directly onto the SonarQube Generic Issue Import
  Format severity field; rule IDs become `ruleId`, rationale text becomes the rule
  description.
