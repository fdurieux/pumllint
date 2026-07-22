Feature: SEQ010 explicit participant ordering

  Scenario: participant introduced only by first use is flagged
    Given the configuration:
      """
      [rules.SEQ010]
      require_explicit_order = true
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      A -> B : go
      @enduml
      """
    When the linter runs
    Then a "SEQ010" issue with severity "info" is reported on line 4

  Scenario: all participants declared up front pass
    Given the configuration:
      """
      [rules.SEQ010]
      require_explicit_order = true
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : go
      @enduml
      """
    When the linter runs
    Then no "SEQ010" issue is reported
