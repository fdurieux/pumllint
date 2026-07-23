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
