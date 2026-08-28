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

  Scenario: a distinct name is exempt from case-collision, case-insensitively
    Given the configuration:
      """
      [rules.XD003]
      distinct = ["LEDGER"]
      """
    And the diagram:
      """
      @startuml one
      participant Ledger
      Ledger -> Ledger : sweep()
      @enduml
      @startuml two
      participant ledger
      ledger -> ledger : sweep()
      @enduml
      """
    When the linter runs
    Then no "XD003" issue is reported
