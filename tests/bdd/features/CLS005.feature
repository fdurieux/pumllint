Feature: CLS005 member count limit

  Scenario: class exceeding the member limit is reported
    Given the configuration:
      """
      [rules.CLS005]
      max = 3
      """
    And the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order {
        +id: UUID
        +total: Money
        +lines: List
        +place()
      }
      @enduml
      """
    When the linter runs
    Then a "CLS005" issue with severity "minor" is reported on line 3

  Scenario: class within the limit passes
    Given the configuration:
      """
      [rules.CLS005]
      max = 3
      """
    And the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order {
        +id: UUID
        +place()
      }
      @enduml
      """
    When the linter runs
    Then no "CLS005" issue is reported
