Feature: The corporate-actions store and its once-per-UTC-day refresh
  Splits and dividends are synced per symbol for actions-eligible legs
  (EODHD, declared class not crypto), before the bars, at most once per UTC
  calendar day unless forced. The stamp is the real wall clock.

  Background:
    Given an empty store

  @JDL-040 @JDL-041 @JDL-042 @JDL-043 @JDL-033 @JDL-034
  Scenario: A first sync writes both actions files in the documented envelope
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is ok
    And the actions file "corporate_actions/splits/SPLT.US.json" is:
      """
      {"symbol": "SPLT.US", "exchange": "eodhd", "last_updated": "<stamp>",
       "splits": [{"date": "2024-01-17", "split": "3.000000/2.000000", "ratio": 1.5},
                  {"date": "2024-02-01", "split": "7/1", "ratio": 7.0}]}
      """
    And the actions file "corporate_actions/dividends/SPLT.US.json" is:
      """
      {"symbol": "SPLT.US", "exchange": "eodhd", "last_updated": "<stamp>",
       "dividends": [{"currency": "USD", "date": "2024-01-25", "declarationDate": "2024-01-10",
                      "paymentDate": "2024-02-05", "period": "Quarterly", "recordDate": "2024-01-26",
                      "unadjustedValue": 0.24, "value": 0.24}]}
      """
    And the actions stamp of "SPLT.US" is the real UTC time of the run

  @JDL-034 @JDL-042
  Scenario: Dividends are stored verbatim in date order and splits may be absent
    Given the universe fixture "divy.toml"
    And the "eodhd" provider replays "divy/run1"
    When sync runs at "2024-03-29T01:00:00Z"
    Then the detail of leg 1 is "0 split(s), 3 dividend(s); 20 bar(s), 0 revised cell(s)"
    And the actions state of "DIVY.US" is:
      """
      {"splits": [],
       "dividends": [{"currency": "USD", "date": "2024-03-01", "period": "Monthly", "unadjustedValue": 0.3, "value": 0.3},
                     {"currency": "USD", "date": "2024-03-15", "period": "Monthly", "unadjustedValue": 0.31, "value": 0.31},
                     {"currency": "USD", "date": "2024-03-28", "period": "Monthly", "unadjustedValue": 0.32, "value": 0.32}]}
      """

  @JDL-091 @JDL-092 @JDL-044 @JDL-041
  Scenario: A stamp from the same UTC day skips the refresh and the stored splits are used
    Given the splits file of "SPLT.US" stamped "2024-02-13T00:00:00Z" with splits:
      | date       | split | ratio |
      | 2024-02-01 | 7/1   | 7.0   |
    And the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T23:59:59Z"
    Then the run is ok
    And the detail of leg 1 is "actions fresh; 30 bar(s), 0 revised cell(s)"
    And the actions stamp of "SPLT.US" is "2024-02-13T00:00:00Z"
    And the stored cells of eodhd/SPLT.US are:
      | date       | column                  | value |
      | 2024-01-02 | cumulative_split_factor | 7.0   |
      | 2024-01-02 | close                   | 30.0  |
      | 2024-01-02 | volume_raw              | 14285.714285714286 |
      | 2024-01-02 | volume                  | 100000.0 |

  @JDL-091
  Scenario: A stamp from an earlier UTC day refreshes, a second before midnight or not
    Given the splits file of "SPLT.US" stamped "2024-02-12T23:59:59Z" with no splits
    And the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T00:00:01Z"
    Then the detail of leg 1 is "2 split(s), 1 dividend(s); 30 bar(s), 0 revised cell(s)"
    And the actions stamp of "SPLT.US" is the real UTC time of the run
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run1_stored"

  @JDL-091 @JDL-043
  Scenario: A later run on an earlier injected day finds the real-clock stamp fresh unless forced
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run2"
    And sync ran at "2024-02-13T12:00:00Z"
    When sync runs at "2024-02-14T12:00:00Z" with options "force_actions=true"
    Then the detail of leg 1 is "2 split(s), 1 dividend(s); 11 bar(s), 3 revised cell(s)"
    When sync runs at "2024-02-15T12:00:00Z" with options "tail=11"
    Then the detail of leg 1 is "actions fresh; 11 bar(s), 0 revised cell(s)"
