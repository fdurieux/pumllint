Feature: ACT005 swimlane naming convention

  Scenario: swimlane violating the configured pattern is reported
    Given the configuration:
      """
      [rules.ACT005]
      pattern = "^[A-Z][A-Za-z ]+$"
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      |billing|
      :Receive application;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT005" issue with severity "minor" is reported on line 4

  Scenario: conforming swimlane passes
    Given the configuration:
      """
      [rules.ACT005]
      pattern = "^[A-Z][A-Za-z ]+$"
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      |Billing|
      :Receive application;
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT005" issue is reported
