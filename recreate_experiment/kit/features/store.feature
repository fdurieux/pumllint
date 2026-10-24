Feature: The partitioned store - layout, schema, reconcile and import semantics

  Background:
    Given an empty store

  @JDL-057 @JDL-058 @JDL-040
  Scenario: A sync and an import leave exactly the documented files
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the store holds "yahoo_small.csv" as yahoo/SMALL declared stock
    Then the store holds exactly the files:
      """
      corporate_actions/dividends/SPLT.US.json
      corporate_actions/splits/SPLT.US.json
      market_data/exchange=eodhd/symbol=SPLT.US/.lock
      market_data/exchange=eodhd/symbol=SPLT.US/year=2024/data.parquet
      market_data/exchange=yahoo/symbol=SMALL/.lock
      market_data/exchange=yahoo/symbol=SMALL/year=2024/data.parquet
      market_data/exchange=yahoo/symbol=SMALL/year=2025/data.parquet
      """

  @JDL-059 @JDL-063
  Scenario: Every stored series reads back with the 21 columns in schema order
    Given the store holds "yahoo_small.csv" as yahoo/SMALL declared stock
    Then the stored dtypes of yahoo/SMALL are:
      | column                  | dtype               |
      | timestamp               | int64               |
      | datetime                | datetime64[ms, UTC] |
      | open                    | float64             |
      | high                    | float64             |
      | low                     | float64             |
      | close                   | float64             |
      | volume                  | float64             |
      | symbol                  | text                |
      | exchange                | text                |
      | asset_type              | text                |
      | asset_subtype           | text                |
      | adjustment_factor       | float64             |
      | open_raw                | float64             |
      | high_raw                | float64             |
      | low_raw                 | float64             |
      | close_raw               | float64             |
      | volume_raw              | float64             |
      | adjusted_close          | float64             |
      | cumulative_split_factor | float64             |
      | currency                | text                |
      | price_basis             | text                |

  @JDL-065 @JDL-067 @JDL-068 @JDL-093 @JDL-103 @JDL-098
  Scenario: The tail refresh reconciles newest-wins inside the window and keeps older history frozen
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the "eodhd" provider replays "splt/run2"
    When sync runs at "2024-02-14T12:00:00Z"
    Then the run is ok
    And the sync log is:
      """
      ok      SPLT eodhd/SPLT.US [eodhd]: actions fresh; 11 bar(s), 3 revised cell(s)
              revised 2024-02-08 close_raw: 21.35 -> 21.31
              revised 2024-02-08 adjusted_close: 21.2432 -> 21.2
              revised 2024-02-09 volume_raw: 128000 -> 777777
      1 leg(s), 0 failed -> store '{store}'
      """
    And the revisions of leg 1 are:
      | date       | column         | stored   | served   |
      | 2024-02-08 | close_raw      | 21.35    | 21.31    |
      | 2024-02-08 | adjusted_close | 21.2432  | 21.2     |
      | 2024-02-09 | volume_raw     | 128000.0 | 777777.0 |
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run2_stored"
    And the stored cells of eodhd/SPLT.US are:
      | date       | column    | value  |
      | 2024-01-10 | close_raw | 213.15 |
      | 2024-02-08 | close     | 21.31  |
      | 2024-02-09 | volume    | 777777.0 |
      | 2024-02-13 | close     | 21.5   |

  @JDL-065 @JDL-054 @JDL-068
  Scenario: An unchanged re-serve of pre-split rows produces no phantom revision
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the "eodhd" provider replays "splt/late2"
    When sync runs at "2024-02-13T18:00:00Z"
    Then the detail of leg 1 is "actions fresh; 10 bar(s), 0 revised cell(s)"
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run1_stored"

  @JDL-066 @JDL-067
  Scenario: Rows a provider serves outside the requested window are reconciled too
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the "eodhd" provider replays "splt/wide"
    When sync runs at "2024-02-13T18:00:00Z"
    Then the detail of leg 1 is "actions fresh; 13 bar(s), 1 revised cell(s)"
    And the revisions of leg 1 are:
      | date       | column    | stored | served |
      | 2024-01-25 | close_raw | 145.95 | 155.0  |
    And the stored cells of eodhd/SPLT.US are:
      | date       | column | value              |
      | 2024-01-25 | close  | 22.142857142857142 |

  @JDL-103
  Scenario: The run log echoes the first ten revisions and counts the rest
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the "eodhd" provider replays "splt/many"
    When sync runs at "2024-02-13T18:00:00Z"
    Then the detail of leg 1 is "actions fresh; 10 bar(s), 20 revised cell(s)"
    And the sync log line 12 starts with "        ... 10 more revised cell(s)"
    And the sync log line 2 starts with "        revised 2024-01-30 close_raw: 147 -> 147.01"

  @JDL-070 @JDL-137 @JDL-057
  Scenario: A Yahoo CSV import replaces the whole series and reports the CSV row count
    When I run "jef-data import-csv --csv {fixtures}/csv/yahoo_small.csv --symbol SMALL --asset-type stock --store {store}"
    Then the exit code is 0
    And stdout is:
      """
      {fixtures}/csv/yahoo_small.csv: 5 row(s) -> {store}/market_data/exchange=yahoo/symbol=SMALL/ (price_basis=split_adjusted)
      """
    And the stored series yahoo/SMALL equals the expected frame "small_stored"
    And the stored cells of yahoo/SMALL are:
      | date       | column      | value          |
      | 2024-01-03 | volume      | 0.0            |
      | 2024-01-04 | close       | 11.5           |
      | 2024-01-04 | currency    | USD            |
      | 2024-01-04 | price_basis | split_adjusted |
    When I run "jef-data import-csv --csv {fixtures}/csv/yahoo_shrunk.csv --symbol SMALL --asset-type etf --currency EUR --store {store}"
    Then the exit code is 0
    And the stored series yahoo/SMALL has 1 rows
    And every stored row of yahoo/SMALL has asset_type "etf"
    And every stored row of yahoo/SMALL has currency "EUR"
    And the store holds exactly the files:
      """
      market_data/exchange=yahoo/symbol=SMALL/.lock
      market_data/exchange=yahoo/symbol=SMALL/year=2024/data.parquet
      """

  @JDL-061 @JDL-070 @JDL-137
  Scenario Outline: An import refuses what it cannot store
    When I run "jef-data import-csv --csv {fixtures}/csv/<csv> --symbol BAD --asset-type stock --store {store}"
    Then the exit code is 1
    And stdout is empty
    And stderr ends with the line "<last line>"
    And the store holds exactly the files:
      """
      <files>
      """

    Examples:
      | csv              | last line | files |
      | bad_dates.csv    | StoreError: unparseable dates cannot be stored: ['05.01.2024'] | |
      | missing_cols.csv | StoreError: {fixtures}/csv/missing_cols.csv: not a 7-column Yahoo CSV, missing ['High', 'Low', 'Adj Close', 'Volume'] | |
