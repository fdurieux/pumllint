Feature: SEQ004 terminated blocks

  Scenario: alt block without end is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      alt happy
      A -> B : go
      @enduml
      """
    When the linter runs
    Then a "SEQ004" issue with severity "critical" is reported on line 5

  Scenario: properly nested and closed blocks pass
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      alt happy
      loop retry
      A -> B : go
      end
      end
      @enduml
      """
    When the linter runs
    Then no "SEQ004" issue is reported
