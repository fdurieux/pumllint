@skip
Feature: CLS002 association multiplicities

  Scenario: association without multiplicities is reported
    Given a class diagram containing 'Order -- Customer'
    When the linter runs
    Then a "CLS002" issue with severity "major" is reported on that line

  Scenario: association with multiplicities passes
    Given a class diagram containing 'Order "1..*" -- "1" Customer'
    When the linter runs
    Then no "CLS002" issue is reported
