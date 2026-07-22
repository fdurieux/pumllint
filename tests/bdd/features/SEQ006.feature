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
