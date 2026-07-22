@skip
Feature: STA002 unreachable states

  Scenario: state with no incoming transition is reported
    Given a state diagram declaring state "Suspended"
    And no transition targets "Suspended"
    When the linter runs
    Then a "STA002" issue with severity "major" is reported on the declaration

  Scenario: fully connected state machine passes
    Given a state diagram where every state is reachable from "[*]"
    When the linter runs
    Then no "STA002" issue is reported
