Feature: SEQ007 unlabelled block condition

  Scenario: opt block without a condition is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      opt
      A -> B : go
      end
      @enduml
      """
    When the linter runs
    Then a "SEQ007" issue with severity "minor" is reported on line 5

  Scenario: loop with a condition passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      loop until queue empty
      A -> B : go
      end
      @enduml
      """
    When the linter runs
    Then no "SEQ007" issue is reported
