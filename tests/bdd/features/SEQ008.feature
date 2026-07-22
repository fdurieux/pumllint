Feature: SEQ008 fragment nesting depth

  Scenario: nesting beyond the configured depth is reported
    Given the configuration:
      """
      [rules.SEQ008]
      max_nesting_depth = 3
      """
    And the diagram:
      """
      @startuml demo
      participant A
      participant B
      alt cond1
      loop cond2
      opt cond3
      par cond4
      A -> B : ping
      end
      end
      end
      end
      @enduml
      """
    When the linter runs
    Then a "SEQ008" issue with severity "minor" is reported on line 7

  Scenario: nesting within the limit passes
    Given the configuration:
      """
      [rules.SEQ008]
      max_nesting_depth = 3
      """
    And the diagram:
      """
      @startuml demo
      participant A
      participant B
      alt cond1
      loop cond2
      A -> B : ping
      end
      end
      @enduml
      """
    When the linter runs
    Then no "SEQ008" issue is reported
