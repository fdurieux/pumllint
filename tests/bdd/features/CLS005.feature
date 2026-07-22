@skip
Feature: CLS005 member count limit

  Scenario: class exceeding the member limit is reported
    Given a configuration with "max_members_per_class" set to 15
    And a class declaring 16 attributes and methods combined
    When the linter runs
    Then a "CLS005" issue with severity "minor" is reported on the class

  Scenario: class within the limit passes
    Given the same configuration and a class with 8 members
    When the linter runs
    Then no "CLS005" issue is reported
