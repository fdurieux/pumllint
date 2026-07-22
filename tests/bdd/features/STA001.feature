@skip
Feature: STA001 exactly one initial state

  Scenario: missing initial transition is reported
    Given a state diagram with no "[*] -->" transition at the top level
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported

  Scenario: duplicate initial transitions are reported
    Given a state diagram with two top-level "[*] -->" transitions
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported on the second one

  Scenario: single initial transition passes
    Given a state diagram with exactly one top-level "[*] --> Idle"
    When the linter runs
    Then no "STA001" issue is reported
