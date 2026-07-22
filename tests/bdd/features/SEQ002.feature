Feature: SEQ002 unused participants

  Scenario: declared participant never referenced is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      actor Customer
      participant FrontOffice
      participant Notary
      Customer -> FrontOffice : Submit
      @enduml
      """
    When the linter runs
    Then a "SEQ002" issue with severity "minor" is reported on line 5

  Scenario: every declared participant is used
    Given the diagram:
      """
      @startuml demo
      title Demo
      actor Customer
      participant FrontOffice
      Customer -> FrontOffice : Submit
      @enduml
      """
    When the linter runs
    Then no "SEQ002" issue is reported
