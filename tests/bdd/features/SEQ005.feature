Feature: SEQ005 message labels

  Scenario: message without a label is reported
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B
      @enduml
      """
    When the linter runs
    Then a "SEQ005" issue with severity "minor" is reported on line 5

  Scenario: labelled message passes
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : requestQuote()
      @enduml
      """
    When the linter runs
    Then no "SEQ005" issue is reported

  Scenario: unlabelled dotted return is tolerated
    Given the diagram:
      """
      @startuml demo
      title Demo
      participant A
      participant B
      A -> B : query
      B --> A
      @enduml
      """
    When the linter runs
    Then no "SEQ005" issue is reported
