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
