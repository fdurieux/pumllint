@skip
Feature: CLS003 relationship labels

  Scenario: unlabelled plain association is reported
    Given a class diagram containing 'Order "1..*" -- "1" Customer' with no label
    When the linter runs
    Then a "CLS003" issue with severity "minor" is reported on that line

  Scenario: labelled association passes
    Given a class diagram containing 'Customer "1" -- "1..*" Order : places'
    When the linter runs
    Then no "CLS003" issue is reported
