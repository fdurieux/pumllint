Feature: GEN010 duplicate diagram name

  Scenario: two diagrams in one file with the same name are both reported
    Given the diagram:
      """
      @startuml order
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      @startuml order
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then a "GEN010" issue with severity "minor" is reported on line 1
    And a "GEN010" issue with severity "minor" is reported on line 7

  Scenario: distinct names pass
    Given the diagram:
      """
      @startuml order
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      @startuml shipment
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then no "GEN010" issue is reported

  Scenario: unnamed diagrams are GEN002's, not GEN010's
    Given the diagram:
      """
      @startuml
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      @startuml
      title Demo
      participant A
      participant B
      A -> B : hi
      @enduml
      """
    When the linter runs
    Then no "GEN010" issue is reported
