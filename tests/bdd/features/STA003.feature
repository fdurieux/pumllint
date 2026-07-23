Feature: STA003 labelled transitions

  Scenario: unlabelled transition is reported
    Given the diagram:
      """
      @startuml device
      title Device power
      [*] --> Idle
      Idle --> Active
      Active --> [*]
      @enduml
      """
    When the linter runs
    Then a "STA003" issue with severity "minor" is reported on line 4

  Scenario: labelled transition passes
    Given the diagram:
      """
      @startuml device
      title Device power
      [*] --> Idle
      Idle --> Active : powerOn [selfTestOk]
      Active --> [*]
      @enduml
      """
    When the linter runs
    Then no "STA003" issue is reported
