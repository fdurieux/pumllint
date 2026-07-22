Feature: UC001 use cases connected to actors

  Scenario: disconnected use case is reported
    Given the diagram:
      """
      @startuml uc
      title Use cases
      :Customer: as Customer
      :Auditor: as Auditor
      usecase (Submit application) as Submit
      Customer --> Submit : initiates
      @enduml
      """
    When the linter runs
    Then a "UC001" issue with severity "major" is reported on line 4

  Scenario: directly connected actor and use case pass
    Given the diagram:
      """
      @startuml uc
      title Use cases
      :Customer: as Customer
      usecase (Submit application) as Submit
      Customer --> Submit : initiates
      @enduml
      """
    When the linter runs
    Then no "UC001" issue is reported
