@skip
Feature: UC003 include and extend direction

  Scenario: reversed extend arrow is reported
    Given a use case diagram where the base case points to the extension with "<<extend>>"
    When the linter runs
    Then a "UC003" issue with severity "minor" is reported on that relationship

  Scenario: correct directions pass
    Given "(Checkout) ..> (Validate cart) : <<include>>"
    And "(Apply coupon) ..> (Checkout) : <<extend>>"
    When the linter runs
    Then no "UC003" issue is reported
