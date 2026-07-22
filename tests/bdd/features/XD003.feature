Feature: XD003 participant name case collision

  Scenario: names differing only by case across diagrams
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      participant Ordersvc
      Client -> Ordersvc : query()
      @enduml
      """
    When the linter runs
    Then a "XD003" issue with severity "minor" is reported on line 8

  Scenario: identical spelling across diagrams passes
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      participant OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then no "XD003" issue is reported
