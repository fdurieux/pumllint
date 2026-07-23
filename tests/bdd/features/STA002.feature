Feature: STA002 unreachable states

  Scenario: state with no incoming transition is reported
    Given the diagram:
      """
      @startuml door
      title Door lifecycle
      [*] --> Open
      Open --> [*]
      state Suspended
      @enduml
      """
    When the linter runs
    Then a "STA002" issue with severity "major" is reported on line 5

  Scenario: fully connected state machine passes
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
    Then no "STA002" issue is reported
