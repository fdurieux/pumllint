Feature: SEQ011 message count limit

  Scenario: diagram exceeding the message limit is reported
    Given the configuration:
      """
      [rules.SEQ011]
      max = 2
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : one
      B --> A : two
      A -> B : three
      @enduml
      """
    When the linter runs
    Then a "SEQ011" issue with severity "minor" is reported on line 7

  Scenario: diagram within the limit passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : one
      B --> A : two
      A -> B : three
      @enduml
      """
    When the linter runs
    Then no "SEQ011" issue is reported
