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
