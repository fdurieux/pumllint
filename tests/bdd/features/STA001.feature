Feature: STA001 exactly one initial state

  Scenario: missing initial transition is reported
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      state Open
      state Closed
      Open --> Closed : close
      @enduml
      """
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported on line 1

  Scenario: duplicate initial transitions are reported
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      [*] --> Closed
      Open --> Closed : close
      @enduml
      """
    When the linter runs
    Then a "STA001" issue with severity "blocker" is reported on line 4

  Scenario: single initial transition passes
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      Open --> Closed : close
      Closed --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA001" issue is reported

  Scenario: initial transitions inside composite states are not top-level
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Operating
      state Operating {
        [*] --> Idle
        Idle --> Busy : work
      }
      Operating --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA001" issue is reported
