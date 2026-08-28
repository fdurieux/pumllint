Feature: XD002 conflicting participant stereotype

  Scenario: same entity stereotyped differently across diagrams
    Given the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<external>>
      participant Client
      Client -> Payments : refund()
      @enduml
      """
    When the linter runs
    Then a "XD002" issue with severity "minor" is reported on line 2
    And a "XD002" issue with severity "minor" is reported on line 7

  Scenario: an authoritative stereotype reports only the non-conforming site
    Given the configuration:
      """
      [rules.XD002]
      authoritative = {Payments = "service"}
      """
    And the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<external>>
      participant Client
      Client -> Payments : refund()
      @enduml
      """
    When the linter runs
    Then a "XD002" issue is reported on line 7
    And no "XD002" issue is reported on line 2

  Scenario: consistent stereotypes across diagrams pass
    Given the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<service>>
      participant Client
      Client -> Payments : refund()
      @enduml
      """
    When the linter runs
    Then no "XD002" issue is reported

  Scenario: a distinct entity is never compared
    Given the configuration:
      """
      [rules.XD002]
      distinct = ["Payments"]
      """
    And the diagram:
      """
      @startuml one
      participant Payments <<service>>
      participant Client
      Client -> Payments : pay()
      @enduml
      @startuml two
      participant Payments <<external>>
      participant Client
      Client -> Payments : pay()
      @enduml
      """
    When the linter runs
    Then no "XD002" issue is reported
