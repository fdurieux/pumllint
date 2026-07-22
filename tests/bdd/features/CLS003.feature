Feature: CLS003 relationship labels

  Scenario: unlabelled plain association is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Order "1..*" -- "1" Customer
      @enduml
      """
    When the linter runs
    Then a "CLS003" issue with severity "minor" is reported on line 5

  Scenario: labelled association passes
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class Order
      class Customer
      Customer "1" -- "1..*" Order : places
      @enduml
      """
    When the linter runs
    Then no "CLS003" issue is reported
