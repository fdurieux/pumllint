Feature: Basis resolution and the split adjustment, cell for cell
  Raw-basis series derive their main columns from the immutable *_raw
  columns and the stored split events; pre-adjusted series are stored as
  served and never adjusted. All values are exact float64.

  Background:
    Given an empty store

  @JDL-045 @JDL-046 @JDL-047 @JDL-048 @JDL-054 @JDL-056 @JDL-053 @JDL-060 @JDL-062 @JDL-059
  Scenario: A two-split equity is stored raw and adjusted around both effective dates
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is ok
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run1_stored"
    And the stored cells of eodhd/SPLT.US are:
      | date       | column                  | value               |
      | 2024-01-02 | timestamp               | 1704153600          |
      | 2024-01-02 | datetime                | 2024-01-02T00:00:00+00:00 |
      | 2024-01-02 | cumulative_split_factor | 10.5                |
      | 2024-01-02 | close_raw               | 210.0               |
      | 2024-01-02 | close                   | 20.0                |
      | 2024-01-02 | open                    | 19.8                |
      | 2024-01-02 | volume_raw              | 9523.809523809523   |
      | 2024-01-02 | volume                  | 99999.99999999999   |
      | 2024-01-02 | adjusted_close          | 19.9                |
      | 2024-01-02 | adjustment_factor       | 0.09476190476190476 |
      | 2024-01-16 | volume                  | 110000.00000000001  |
      | 2024-01-17 | cumulative_split_factor | 7.0                 |
      | 2024-01-17 | open                    | 20.344285714285714  |
      | 2024-01-17 | volume_raw              | 15857.142857142857  |
      | 2024-01-17 | volume                  | 111000.0            |
      | 2024-02-01 | cumulative_split_factor | 1.0                 |
      | 2024-02-01 | close                   | 21.1                |
      | 2024-02-01 | adjustment_factor       | 0.9949999999999999  |
      | 2024-02-01 | symbol                  | SPLT.US             |
      | 2024-02-01 | exchange                | eodhd               |
      | 2024-02-01 | asset_type              | stock               |
      | 2024-02-01 | asset_subtype           |                     |
      | 2024-02-01 | currency                | USD                 |
      | 2024-02-01 | price_basis             | raw                 |

  @JDL-050 @JDL-053 @JDL-056
  Scenario: An ETF with dividends and no splits is raw basis with factor 1 and dividends never applied
    Given the universe fixture "divy.toml"
    And the "eodhd" provider replays "divy/run1"
    When sync runs at "2024-03-29T01:00:00Z"
    Then the stored series eodhd/DIVY.US equals the expected frame "divy_stored"
    And every stored row of eodhd/DIVY.US has price_basis "raw"
    And every stored row of eodhd/DIVY.US has asset_type "etf"
    And every stored row of eodhd/DIVY.US has cumulative_split_factor "1.0"
    And the stored cells of eodhd/DIVY.US are:
      | date       | column            | value              |
      | 2024-03-01 | close             | 95.0               |
      | 2024-03-01 | adjusted_close    | 94.37              |
      | 2024-03-01 | adjustment_factor | 0.9933684210526317 |
      | 2024-03-01 | volume            | 50000.0            |
      | 2024-03-28 | adjusted_close    | 96.9               |

  @JDL-055 @JDL-053 @JDL-094
  Scenario: An EODHD crypto series is stored as served, end-guarded at the previous UTC day
    Given the universe fixture "zero.toml"
    And the "eodhd" provider replays "zero/run1"
    When sync runs at "2024-02-10T08:00:00Z"
    Then the run is ok
    And the stored series eodhd/ZERO-USD.CC equals the expected frame "zero_stored"
    And every stored row of eodhd/ZERO-USD.CC has price_basis "split_adjusted"
    And every stored row of eodhd/ZERO-USD.CC has cumulative_split_factor "1.0"
    And the stored cells of eodhd/ZERO-USD.CC are:
      | date       | column     | value  |
      | 2024-01-09 | volume_raw | 3080.0 |
      | 2024-01-09 | volume     | 3080.0 |
      | 2024-01-10 | volume     | 0.0    |
      | 2024-02-09 | close      | 1.64   |

  @JDL-053 @JDL-086 @JDL-094 @JDL-084
  Scenario: The declared class, never the .CC suffix, decides basis, actions and guard
    Given the universe fixture "ns.toml"
    And the "eodhd" provider replays "ns"
    When the legs are selected
    Then the legs are:
      """
      [{"asset": "WEIRD", "provider": "eodhd", "exchange": "eodhd", "symbol": "WEIRD.XX", "path": null,
        "asset_type": "crypto", "currency": "USD", "start": null, "end": null, "actions": false},
       {"asset": "CCSTK", "provider": "eodhd", "exchange": "eodhd", "symbol": "CCSTK-USD.CC", "path": null,
        "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": true}]
      """
    When sync runs at "2024-05-11T06:00:00Z"
    Then the run is ok
    And the detail of leg 1 is "10 bar(s), 0 revised cell(s)"
    And the detail of leg 2 is "1 split(s), 0 dividend(s); 8 bar(s), 0 revised cell(s)"
    And the stored series eodhd/WEIRD.XX equals the expected frame "weird_stored"
    And the stored series eodhd/CCSTK-USD.CC equals the expected frame "ccstk_stored"
    And the stored cells of eodhd/CCSTK-USD.CC are:
      | date       | column                  | value |
      | 2024-05-03 | cumulative_split_factor | 2.0   |
      | 2024-05-03 | close                   | 6.25  |
      | 2024-05-06 | cumulative_split_factor | 1.0   |
      | 2024-05-06 | price_basis             | raw   |
    And every stored row of eodhd/WEIRD.XX has price_basis "split_adjusted"
    And the actions state of "WEIRD.XX" is empty

  @JDL-049 @JDL-069 @JDL-097 @JDL-065 @JDL-054
  Scenario: A split synced after the first fill re-derives every price but only re-raw-izes the tail's volume
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/late1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the "eodhd" provider replays "splt/late2"
    When sync runs at "2024-02-14T12:00:00Z" with options "force_actions=true"
    Then the run is ok
    And the detail of leg 1 is "2 split(s), 1 dividend(s); 10 bar(s), 2 revised cell(s)"
    And the revisions of leg 1 are:
      | date       | column     | stored   | served             |
      | 2024-01-30 | volume_raw | 120000.0 | 17142.85714285714  |
      | 2024-01-31 | volume_raw | 121000.0 | 17285.714285714286 |
    And the stored series eodhd/SPLT.US equals the expected frame "late_stored"
    And the stored cells of eodhd/SPLT.US are:
      | date       | column     | value             |
      | 2024-01-02 | close      | 20.0              |
      | 2024-01-02 | volume_raw | 66666.66666666667 |
      | 2024-01-02 | volume     | 700000.0          |
      | 2024-01-30 | volume     | 119999.99999999999 |

  @JDL-049 @JDL-139 @JDL-041 @JDL-069
  Scenario: The adjust command re-derives the mains from raw with whatever splits are stored
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the splits file of "SPLT.US" stamped "2024-02-13T12:00:00Z" with splits:
      | date       | split | ratio |
      | 2024-02-01 | 7/1   | 7.0   |
    When I run "jef-data adjust --symbol SPLT.US --store {store}"
    Then the exit code is 0
    And stdout is:
      """
      eodhd/SPLT.US: 30 row(s) re-derived from *_raw with 1 split(s)
      """
    And the stored cells of eodhd/SPLT.US are:
      | date       | column                  | value             |
      | 2024-01-02 | cumulative_split_factor | 7.0               |
      | 2024-01-02 | close                   | 30.0              |
      | 2024-01-02 | volume                  | 66666.66666666666 |
      | 2024-01-02 | volume_raw              | 9523.809523809523 |
    Given the splits file of "SPLT.US" stamped "2024-02-13T12:00:00Z" with splits:
      | date       | split             | ratio |
      | 2024-01-17 | 3.000000/2.000000 | 1.5   |
      | 2024-02-01 | 7/1               | 7.0   |
    When I run "jef-data adjust --symbol SPLT.US --store {store}"
    Then stdout is:
      """
      eodhd/SPLT.US: 30 row(s) re-derived from *_raw with 2 split(s)
      """
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run1_stored"

  @JDL-051 @JDL-139 @JDL-069 @JDL-134
  Scenario Outline: The adjust command refuses what it must not adjust
    Given the store holds "yahoo_small.csv" as eodhd/SMALL.US declared stock
    When I run "jef-data adjust --symbol <symbol> --store {store}"
    Then the exit code is 1
    And stdout is empty
    And stderr ends with the line "<last line>"

    Examples:
      | symbol   | last line |
      | SMALL.US | AdjustmentRefused: price_basis ['split_adjusted'] is already adjusted at the provider - applying split events would double-adjust (docs/DATA_CONTRACT.md §2) |
      | NONE.US  | StoreError: nothing stored for eodhd/NONE.US |

  @JDL-052 @JDL-101
  Scenario: A degenerate stored split ratio fails the leg before anything is written
    Given the splits file of "SPLT.US" stamped "2024-02-13T00:00:00Z" with splits:
      | date       | split | ratio |
      | 2024-01-17 | 0/1   | 0.0   |
    And the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is not ok
    And the detail of leg 1 is "AdjustmentRefused: split 2024-01-17 has degenerate ratio 0.0"
    And the stored series eodhd/SPLT.US has 0 rows
