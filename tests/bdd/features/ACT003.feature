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

  Scenario: loop whose looping outcome is unlabelled is reported
    Given the diagram:
      """
      @startuml dossier-check
      title Dossier check
      start
      repeat
      :Check dossier;
      repeat while (Document missing?) not (Dossier complete)
      :Approve dossier;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT003" issue with severity "minor" is reported on line 6

  Scenario: loop whose exit is unlabelled is reported unless the else option is off
    Given the diagram:
      """
      @startuml dossier-check
      title Dossier check
      start
      repeat
      :Check dossier;
      repeat while (Document missing?) is (Document missing)
      :Approve dossier;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT003" issue with severity "minor" is reported on line 6

  Scenario: while loop without an is label is reported
    Given the diagram:
      """
      @startuml dossier-check
      title Dossier check
      start
      :Check dossier;
      while (Document missing?)
      :Contact customer;
      endwhile (Dossier complete)
      :Approve dossier;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT003" issue with severity "minor" is reported on line 5

  Scenario: fully labelled loops pass
    Given the diagram:
      """
      @startuml dossier-check
      title Dossier check
      start
      repeat
      :Check dossier;
      repeat while (Document missing?) is (Document missing) not (Dossier complete)
      while (Signature missing?) is (Signature missing)
      :Request signature;
      endwhile (Signed)
      :Approve dossier;
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT003" issue is reported
