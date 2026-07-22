Feature: CLS001 naming conventions

  Scenario: non-PascalCase class name is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class order_service
      @enduml
      """
    When the linter runs
    Then a "CLS001" issue with severity "minor" is reported on line 3

  Scenario: non-conforming member name is reported
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class OrderService {
        +PlaceOrder()
      }
      @enduml
      """
    When the linter runs
    Then a "CLS001" issue with severity "minor" is reported on line 4

  Scenario: conforming names pass
    Given the diagram:
      """
      @startuml shop-model
      title Shop model
      class OrderService {
        +placeOrder()
      }
      @enduml
      """
    When the linter runs
    Then no "CLS001" issue is reported
