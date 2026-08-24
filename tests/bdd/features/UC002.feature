Feature: UC002 use case and actor naming

  Scenario: noun-phrase use case is reported
    Given the configuration:
      """
      [rules.UC002]
      verbs = ["Place", "Manage"]
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Order placement)
      Customer --> (Order placement) : does
      @enduml
      """
    When the linter runs
    Then a "UC002" issue with severity "minor" is reported on line 4

  Scenario: conforming names pass
    Given the configuration:
      """
      [rules.UC002]
      verbs = ["Place"]
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Place order)
      Customer --> (Place order) : does
      @enduml
      """
    When the linter runs
    Then no "UC002" issue is reported

  Scenario: an aliased use case is judged by its label, not the alias
    Given the configuration:
      """
      [rules.UC002]
      verbs = ["Place", "Manage"]
      """
    And the diagram:
      """
      @startuml uc
      title Use cases
      actor Customer
      usecase (Order placement) as UC1
      Customer --> UC1 : does
      @enduml
      """
    When the linter runs
    Then a "UC002" issue with severity "minor" is reported on line 4
