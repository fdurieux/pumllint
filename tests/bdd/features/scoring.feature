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
    And the codegen profile is active
    And every dimension score is at least 80
    And the diagram has no blocker findings
    And the diagram has no major findings
    When the scoring reporter runs
    Then the maturity level is 5

  Scenario: A single major finding blocks Generation-ready
    Given a syntactically valid diagram with composite score 94
    And the codegen profile is active
    And every dimension score is at least 80
    And the diagram has exactly one major finding
    When the scoring reporter runs
    Then the maturity level is 4
    And the gap report lists the major finding as the sole obstacle to Level 5

  # --- Integrity caps (C4-C7) ---

  Scenario: An empty diagram cannot score
    Given a syntactically valid diagram with zero modelled elements
    When the scoring reporter runs
    Then the maturity level is 1
    And the gap report states the diagram has no modelled content

  Scenario: An unrecognized diagram type caps at Structured
    Given a diagram whose type is not recognized
    And the diagram would otherwise have a composite score of 100
    When the scoring reporter runs
    Then the maturity level is 2

  Scenario: A near-empty diagram cannot claim Precise
    Given a clean sequence diagram with 2 modelled elements
    When the scoring reporter runs
    Then the maturity level is 3
    And the gap report states Level 4 requires at least 3 elements

  Scenario: Generation-ready requires the codegen profile
    Given a clean sequence diagram scored without the codegen profile
    And the diagram would otherwise reach Level 5
    When the scoring reporter runs
    Then the maturity level is 4
    And the gap report states Level 5 requires the codegen profile

  # --- CI gate ---

  Scenario: min-level gate fails the build below threshold
    Given a diagram scored at maturity level 3
    When pumllint score runs with --min-level 4
    Then the exit code is non-zero

  Scenario: min-level gate passes the build at threshold
    Given a diagram scored at maturity level 4
    When pumllint score runs with --min-level 4
    Then the exit code is zero
