# Maturity Scoring Model (360° Assessment)

> Spec section for `RULES.md`. The scoring model is a **reporter-layer aggregation** over
> rule findings. It introduces no new analysis machinery: every score is derived from
> existing rule results plus diagram element counts already available in the semantic
> `Diagram` model. Rules remain the single source of truth.

## 1. Purpose

The maturity score answers two questions per diagram (and per model set):

1. **How disciplined is this model?** (method-convention quality, ARIS-style)
2. **Is it precise enough for LLM code generation?** (the level-5 claim)

The report is prescriptive: alongside the level, it emits a **gap report** listing the
concrete findings that block promotion to the next level.

## 2. Dimensions

Each rule carries a `dimension` attribute in the registry (new metadata field, defaulted
per pack, overridable per rule). Seven dimensions:

| ID      | Dimension              | Source of signal                                            | Default weight |
|---------|------------------------|-------------------------------------------------------------|----------------|
| DIM-SYN | Syntactic validity     | `plantuml -checkonly` exit code (external gate, pass/fail)  | gate           |
| DIM-SEM | Semantic correctness   | All pack findings not claimed by a more specific dimension  | 0.20           |
| DIM-CMP | Completeness           | Typed params/returns, multiplicities, guards, alt/error paths, orphan elements | 0.25 |
| DIM-CON | Consistency            | Naming conventions; cross-diagram entity identity           | 0.15           |
| DIM-TRC | Traceability           | Title, ID, ownership, requirement/ADR links (GEN pack)      | 0.10           |
| DIM-RDB | Readability            | Participant count, nesting depth, size thresholds           | 0.10           |
| DIM-AMB | Ambiguity              | Vague verbs, unlabeled arrows, structure hidden in notes    | 0.20           |

DIM-SYN is a **gate**, not a weighted dimension: if syntax fails, the diagram is Level 1
and no further scoring is reported.

## 3. Scoring formula

Per dimension *d*:

```
penalty(d)  = Σ severity_weight(f) for each finding f tagged with d
density(d)  = penalty(d) / max(1, element_count)
score(d)    = clamp(100 − K × density(d), 0, 100)
```

- `element_count` = participants + messages (SEQ), classes + relations (CLS), etc. —
  taken from the `Diagram` model, so large diagrams are not punished for size alone.
- `K` (scaling constant) default **50**, configurable.

Default severity weights (SonarQube-aligned):

| Severity | Weight |
|----------|--------|
| blocker  | 10     |
| major    | 5      |
| minor    | 2      |
| info     | 0.5    |

Composite:

```
composite = Σ weight(d) × score(d)   for d in weighted dimensions (weights sum to 1.0)
```

## 4. Maturity levels

| Level | Name             | Criteria                                                                  |
|-------|------------------|---------------------------------------------------------------------------|
| 1     | Sketchy          | Syntax gate fails, **or** composite < 40                                  |
| 2     | Structured       | Syntax passes and composite ≥ 40                                          |
| 3     | Disciplined      | Composite ≥ 60 **and** zero blocker findings                              |
| 4     | Precise          | Composite ≥ 75, zero blockers, DIM-CMP ≥ 70 **and** DIM-AMB ≥ 70          |
| 5     | Generation-ready | Composite ≥ 90, every dimension ≥ 80, zero blocker **and** zero major     |

**Caps (anti-gaming rules):**

- C1: Any blocker finding caps the level at **2**, regardless of composite.
- C2: Syntax gate failure forces level **1**, regardless of anything else.
- C3: Any single dimension score < 40 caps the level at **3** (no dimension may be
  sacrificed to inflate the composite).

All thresholds, weights, and caps are configurable under the `scoring:` key
(YAML/TOML/JSON, same precedence as rule config).

## 5. Gap report (prescriptive advice)

For the next level up, the reporter computes the **minimal blocking set**:

1. Unsatisfied caps first (e.g., "1 blocker finding — resolve SEQ003 at line 42").
2. Unsatisfied dimension thresholds, listing the highest-weight findings in that
   dimension until the threshold would be met.
3. Composite shortfall, listing highest-weight findings overall.

Output format (text reporter):

```
Level 3 (Disciplined) — 68/100
To reach Level 4 (Precise):
  • DIM-CMP is 61, needs ≥ 70 — fix:
      SEQ012 major  order.puml:18  message 'process()' has untyped parameters
      SEQ014 minor  order.puml:23  alt branch missing failure path
  • DIM-AMB is 66, needs ≥ 70 — fix:
      GEN020 minor  order.puml:9   arrow label 'handle data' uses vague verb
```

JSON reporter emits `score`, `level`, `dimensions{}`, and `gap_report[]` as a top-level
`maturity` object. SonarQube reporter: the Generic Issue Import Format carries issues,
not measures, so the maturity object is written to the JSON report only; optionally one
`info`-severity synthetic issue summarizing the level can be emitted for visibility.

## 6. CLI

```
pumllint score <paths> [--min-level N]
```

- `--min-level N` — exit non-zero if any scored unit is below level N (CI gate).
- Cross-diagram consistency (DIM-CON multi-file checks) activates when more than one
  file is passed; otherwise DIM-CON scores single-file naming rules only.

## 7. Acceptance criteria (Gherkin)

Structured for direct lift into `features/scoring.feature`. One promotion scenario and
one boundary/cap scenario per level threshold.

```gherkin
Feature: Maturity level assignment
  The scoring reporter aggregates rule findings into a 360 maturity level
  and a prescriptive gap report.

  Background:
    Given default scoring configuration

  # --- Level 1 / syntax gate ---

  Scenario: Syntax failure forces Level 1 regardless of findings
    Given a diagram that fails the plantuml -checkonly gate
    And the diagram would otherwise have a composite score of 95
    When the scoring reporter runs
    Then the maturity level is 1
    And no dimension scores are reported
    And the gap report states the syntax gate must pass first

  Scenario: Very low composite yields Level 1
    Given a syntactically valid diagram with composite score 35
    When the scoring reporter runs
    Then the maturity level is 1
    And the gap report lists the highest-weight findings needed to reach composite 40

  # --- Level 2 ---

  Scenario: Passing syntax with composite at threshold reaches Level 2
    Given a syntactically valid diagram with composite score 40
    And the diagram has one blocker finding
    When the scoring reporter runs
    Then the maturity level is 2

  Scenario: Blocker cap holds a high-scoring diagram at Level 2
    Given a syntactically valid diagram with composite score 92
    And every dimension score is at least 80
    And the diagram has one blocker finding
    When the scoring reporter runs
    Then the maturity level is 2
    And the gap report lists the blocker finding as the sole obstacle to Level 3

  # --- Level 3 ---

  Scenario: Composite 60 with zero blockers reaches Level 3
    Given a syntactically valid diagram with composite score 60
    And the diagram has no blocker findings
    When the scoring reporter runs
    Then the maturity level is 3

  Scenario: Weak dimension cap holds diagram at Level 3
    Given a syntactically valid diagram with composite score 78
    And the diagram has no blocker findings
    And dimension DIM-TRC has a score of 35
    When the scoring reporter runs
    Then the maturity level is 3
    And the gap report lists DIM-TRC findings required to lift the dimension above 40

  # --- Level 4 ---

  Scenario: Composite 75 with strong completeness and low ambiguity reaches Level 4
    Given a syntactically valid diagram with composite score 75
    And the diagram has no blocker findings
    And dimension DIM-CMP has a score of 70
    And dimension DIM-AMB has a score of 70
    And every dimension score is at least 40
    When the scoring reporter runs
    Then the maturity level is 4

  Scenario: High composite with ambiguous labels stays at Level 3
    Given a syntactically valid diagram with composite score 82
    And the diagram has no blocker findings
    And dimension DIM-AMB has a score of 65
    When the scoring reporter runs
    Then the maturity level is 3
    And the gap report lists DIM-AMB findings required to reach 70

  # --- Level 5 ---

  Scenario: Fully disciplined model reaches Generation-ready
    Given a syntactically valid diagram with composite score 91
    And every dimension score is at least 80
    And the diagram has no blocker findings
    And the diagram has no major findings
    When the scoring reporter runs
    Then the maturity level is 5

  Scenario: A single major finding blocks Generation-ready
    Given a syntactically valid diagram with composite score 94
    And every dimension score is at least 80
    And the diagram has exactly one major finding
    When the scoring reporter runs
    Then the maturity level is 4
    And the gap report lists the major finding as the sole obstacle to Level 5

  # --- CI gate ---

  Scenario: min-level gate fails the build below threshold
    Given a diagram scored at maturity level 3
    When pumllint score runs with --min-level 4
    Then the exit code is non-zero

  Scenario: min-level gate passes the build at threshold
    Given a diagram scored at maturity level 4
    When pumllint score runs with --min-level 4
    Then the exit code is zero
```

## 8. Implementation notes

- New registry metadata: `dimension=` parameter on the rule decorator, defaulted by pack
  (SEQ/CLS structural rules → DIM-CMP or DIM-SEM; GEN metadata rules → DIM-TRC, etc.).
  Existing rules need only a one-line annotation each.
- The scorer is a pure function `score(findings, diagram) -> MaturityResult` — trivially
  unit-testable and independent of reporters.
- Cross-diagram consistency (DIM-CON) is the only piece requiring new analysis
  (a symbol table across files); ship the scorer first with DIM-CON limited to
  single-file naming rules, and extend later.
