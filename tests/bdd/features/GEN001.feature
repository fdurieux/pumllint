Feature: GEN001 diagram must have a title

  Scenario: diagram without a title is reported
    Given the diagram:
      """
      @startuml demo
      participant Customer
      participant FrontOffice
      Customer -> FrontOffice : hello
      @enduml
      """
    When the linter runs
    Then a "GEN001" issue with severity "minor" is reported on line 1

  Scenario: diagram with a title passes
    Given the diagram:
      """
      @startuml demo
      title Order Processing
      participant Customer
      participant FrontOffice
      Customer -> FrontOffice : hello
      @enduml
      """
    When the linter runs
    Then no "GEN001" issue is reported
