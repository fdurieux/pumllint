Feature: UC003 include and extend direction

  Scenario: reversed extend arrow is reported
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: --> (Checkout)
      (Checkout) ..> (Apply coupon) : <<extend>>
      @enduml
      """
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on line 5

  Scenario: reversed include arrow is reported
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: --> (Checkout)
      (Validate cart) ..> (Checkout) : <<include>>
      @enduml
      """
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on line 5

  Scenario: include or extend involving an actor is reported
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: ..> (Checkout) : <<include>>
      @enduml
      """
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on line 4

  Scenario: correct directions pass
    Given the diagram:
      """
      @startuml checkout
      title Checkout
      usecase (Checkout)
      :Customer: --> (Checkout)
      (Checkout) ..> (Validate cart) : <<include>>
      (Apply coupon) ..> (Checkout) : <<extend>>
      @enduml
      """
    When the linter runs
    Then no "UC003" issue is reported
