Feature: SEQ003 balanced activations

  Scenario: activate without matching deactivate
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      activate B
      @enduml
      """
    When the linter runs
    Then a "SEQ003" issue with severity "major" is reported on line 6

  Scenario: deactivate without a prior activate
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      deactivate B
      @enduml
      """
    When the linter runs
    Then a "SEQ003" issue with severity "major" is reported on line 6

  Scenario: balanced activation passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      activate B
      B --> A : ok
      deactivate B
      @enduml
      """
    When the linter runs
    Then no "SEQ003" issue is reported
