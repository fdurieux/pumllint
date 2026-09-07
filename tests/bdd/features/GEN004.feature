Feature: GEN004 participant naming convention

  Scenario: name violating the pattern is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant front_office
      A -> front_office : hi
      @enduml
      """
    When the linter runs
    Then a "GEN004" issue with severity "minor" is reported on line 4

  Scenario: a name declared after first use is still checked
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      A -> front_office : hi
      participant front_office
      @enduml
      """
    When the linter runs
    Then a "GEN004" issue with severity "minor" is reported on line 5

  Scenario: conforming name passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant FrontOffice
      A -> FrontOffice : hi
      @enduml
      """
    When the linter runs
    Then no "GEN004" issue is reported
