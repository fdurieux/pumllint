@skip
Feature: CLS004 inheritance cycles

  Scenario: inheritance cycle is reported
    Given a class diagram containing "A <|-- B", "B <|-- C", and "C <|-- A"
    When the linter runs
    Then a "CLS004" issue with severity "major" is reported citing the cycle

  Scenario: acyclic hierarchy passes
    Given a class diagram containing "A <|-- B" and "A <|-- C"
    When the linter runs
    Then no "CLS004" issue is reported
