@skip
Feature: CLS001 naming conventions

  Scenario: non-PascalCase class name is reported
    Given a configuration requiring PascalCase class names
    And a class diagram declaring "class order_service"
    When the linter runs
    Then a "CLS001" issue with severity "minor" is reported on the declaration

  Scenario: conforming names pass
    Given the same configuration
    And a class diagram declaring "class OrderService" with member "placeOrder()"
    When the linter runs
    Then no "CLS001" issue is reported
