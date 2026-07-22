Feature: CLS002 association multiplicities

  Scenario: association without multiplicities is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Order -- Customer : places
      @enduml
      """
    When the linter runs
    Then a "CLS002" issue with severity "major" is reported on line 5

  Scenario: association with multiplicities passes
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Order "1..*" -- "1" Customer : places
      @enduml
      """
    When the linter runs
    Then no "CLS002" issue is reported
