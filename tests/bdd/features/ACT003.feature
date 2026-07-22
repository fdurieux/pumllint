Feature: ACT003 labelled decision branches

  Scenario: unlabelled then-branch is reported
    Given the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then
      :Score applicant;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT003" issue with severity "minor" is reported on line 5

  Scenario: fully labelled decision passes
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
    Then no "ACT003" issue is reported
