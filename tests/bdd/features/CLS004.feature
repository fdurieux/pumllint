Feature: CLS004 inheritance cycles

  Scenario: inheritance cycle is reported
    Given the diagram:
      """
      @startuml taxonomy
      title Taxonomy
      A <|-- B
      B <|-- C
      C <|-- A
      @enduml
      """
    When the linter runs
    Then a "CLS004" issue with severity "major" is reported on line 3

  Scenario: acyclic hierarchy passes
    Given the diagram:
      """
      @startuml taxonomy
      title Taxonomy
      A <|-- B
      A <|-- C
      @enduml
      """
    When the linter runs
    Then no "CLS004" issue is reported
