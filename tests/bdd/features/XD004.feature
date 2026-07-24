Feature: XD004 cross-type name collision

  Scenario: class and sequence participant differ only by case
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant orderService
      participant Client
      Client -> orderService : place()
      @enduml
      """
    When the linter runs
    Then a "XD004" issue with severity "minor" is reported on line 9

  Scenario: consistent spelling across types passes
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant OrderService
      participant Client
      Client -> OrderService : place()
      @enduml
      """
    When the linter runs
    Then no "XD004" issue is reported
