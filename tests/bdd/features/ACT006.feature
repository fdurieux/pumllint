Feature: ACT006 verb-first activity names

  Scenario: noun-phrase activity is reported
    Given the configuration:
      """
      [rules.ACT006]
      verbs = ["Validate", "Receive", "Request", "Score"]
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Order validation;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT006" issue with severity "minor" is reported on line 6

  Scenario: verb-first activity passes
    Given the configuration:
      """
      [rules.ACT006]
      verbs = ["Receive", "Score", "Request"]
      """
    And the diagram:
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
    Then no "ACT006" issue is reported

  Scenario: a verb pattern arms the rule without a verbs list
    Given the configuration:
      """
      [rules.ACT006]
      verb_pattern = '^(Receive|Request|Score)\b'
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Order validation;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT006" issue with severity "minor" is reported on line 6

  Scenario: a listed verb passes beside a verb pattern
    Given the configuration:
      """
      [rules.ACT006]
      verbs = ["Order"]
      verb_pattern = '^(Receive|Request|Score)\b'
      """
    And the diagram:
      """
      @startuml loan-decision
      title Loan decision
      start
      :Receive application;
      if (Complete?) then (yes)
      :Order validation;
      else (no)
      :Request documents;
      endif
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT006" issue is reported
