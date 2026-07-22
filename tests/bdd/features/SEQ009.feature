Feature: SEQ009 return messages pair with calls

  Scenario: orphaned return message is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      B --> A : result
      @enduml
      """
    When the linter runs
    Then a "SEQ009" issue with severity "minor" is reported on line 5

  Scenario: paired call and return pass
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : query
      B --> A : result
      @enduml
      """
    When the linter runs
    Then no "SEQ009" issue is reported
