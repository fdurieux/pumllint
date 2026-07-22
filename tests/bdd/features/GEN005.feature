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
