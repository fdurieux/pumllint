Feature: GEN008 note density

  Scenario: note-heavy diagram is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      note over A : step one
      note over A : step two
      note over B : step three
      note over B : step four
      @enduml
      """
    When the linter runs
    Then a "GEN008" issue with severity "minor" is reported on line 6

  Scenario: lightly annotated diagram passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      note over A : step one
      note over B : step two
      @enduml
      """
    When the linter runs
    Then no "GEN008" issue is reported

  Scenario: prose-heavy notes are reported when the length cap is configured
    Given the configuration:
      """
      [rules.GEN008]
      max_chars_per_element = 10
      """
    And the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : hi
      note over A : this single note narrates the whole protocol in long prose
      @enduml
      """
    When the linter runs
    Then a "GEN008" issue with severity "minor" is reported on line 6
