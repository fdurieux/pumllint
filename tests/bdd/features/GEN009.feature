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
