Feature: XD001 conflicting participant kind

  Scenario: same entity declared with different kinds across diagrams
    Given the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      database OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then a "XD001" issue with severity "major" is reported on line 3
    And a "XD001" issue with severity "major" is reported on line 8

  Scenario: an authoritative kind reports only the non-conforming site
    Given the configuration:
      """
      [rules.XD001]
      authoritative = {OrderSvc = "database"}
      """
    And the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      database OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then a "XD001" issue is reported on line 3
    And no "XD001" issue is reported on line 8

  Scenario: consistent kinds across diagrams pass
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
    Then no "XD001" issue is reported

  Scenario: a distinct entity is never compared
    Given the configuration:
      """
      [rules.XD001]
      distinct = ["OrderSvc"]
      """
    And the diagram:
      """
      @startuml one
      participant Client
      participant OrderSvc
      Client -> OrderSvc : run()
      @enduml
      @startuml two
      participant Client
      database OrderSvc
      Client -> OrderSvc : query()
      @enduml
      """
    When the linter runs
    Then no "XD001" issue is reported
