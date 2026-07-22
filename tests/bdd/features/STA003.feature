@skip
Feature: STA003 labelled transitions

  Scenario: unlabelled transition is reported
    Given a state diagram containing "Idle --> Active" with no label
    When the linter runs
    Then a "STA003" issue with severity "minor" is reported on that line

  Scenario: labelled transition passes
    Given a state diagram containing "Idle --> Active : powerOn [selfTestOk]"
    When the linter runs
    Then no "STA003" issue is reported
