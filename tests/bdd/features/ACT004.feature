Feature: ACT004 terminated constructs

  Scenario: fork without end fork is reported
    Given the diagram:
      """
      @startuml pipeline
      title Pipeline
      start
      fork
      :Notify sales;
      fork again
      :Notify risk;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT004" issue with severity "critical" is reported on line 4

  Scenario: unclosed while is reported
    Given the diagram:
      """
      @startuml pipeline
      title Pipeline
      start
      while (more?) is (yes)
      :Process;
      stop
      @enduml
      """
    When the linter runs
    Then an "ACT004" issue with severity "critical" is reported on line 4

  Scenario: balanced constructs pass
    Given the diagram:
      """
      @startuml pipeline
      title Pipeline
      start
      fork
      :Notify sales;
      fork again
      :Notify risk;
      end fork
      stop
      @enduml
      """
    When the linter runs
    Then no "ACT004" issue is reported
