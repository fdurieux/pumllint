Feature: ACT001 start node present

  Scenario: diagram with actions but no start node is reported
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT001" issue with severity "major" is reported on line 3

  Scenario: diagram with a start node passes
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT001" issue is reported
