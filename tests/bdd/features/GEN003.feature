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
