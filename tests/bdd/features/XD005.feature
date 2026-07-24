Feature: XD005 cross-type stereotype conflict

  Scenario: class and sequence stereotypes disagree
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService <<service>>
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant OrderService <<gateway>>
      participant Client
      Client -> OrderService : place()
      @enduml
      """
    When the linter runs
    Then a "XD005" issue with severity "minor" is reported on line 9

  Scenario: agreeing stereotypes pass
    Given the diagram:
      """
      @startuml model
      title Model
      class OrderService <<service>>
      class Customer
      Customer "1" -- "1..*" OrderService : uses
      @enduml
      @startuml flow
      title Flow
      participant OrderService <<service>>
      participant Client
      Client -> OrderService : place()
      @enduml
      """
    When the linter runs
    Then no "XD005" issue is reported
