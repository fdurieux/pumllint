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
