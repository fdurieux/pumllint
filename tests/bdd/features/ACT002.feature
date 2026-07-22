Feature: ACT002 flow terminates

  Scenario: diagram without any stop or end node is reported
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
      @enduml
      """
    When the linter runs
    Then an "ACT002" issue with severity "major" is reported on line 8

  Scenario: diagram reaching a terminal passes
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
    Then no "ACT002" issue is reported
