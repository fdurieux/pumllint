Feature: The exported seam frame and the EOD input contract

  Background:
    Given an empty store

  @JDL-071 @JDL-072 @JDL-075 @JDL-138 @JDL-079 @JDL-081
  Scenario: Exporting the two-split equity writes the adjusted mains with a float Volume
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    Then the export frame of eodhd/SPLT.US equals the expected frame "splt_run1_export"
    And the export frame of eodhd/SPLT.US has the dtypes:
      | column    | dtype   |
      | Date      | text    |
      | Open      | float64 |
      | High      | float64 |
      | Low       | float64 |
      | Close     | float64 |
      | Adj Close | float64 |
      | Volume    | float64 |
    When I run "jef-data export --symbol SPLT.US --output out.csv --store {store}"
    Then the exit code is 0
    And stdout is:
      """
      eodhd/SPLT.US: 30 row(s) -> out.csv
      note:  30 clean row(s) < recommended minimum 1115 (720 warm-up + 395 lags) - the default counter window needs more history (docs/DATA_CONTRACT.md §1)
      """
    And the file "out.csv" starts with:
      """
      Date,Open,High,Low,Close,Adj Close,Volume
      2024-01-02,19.8,20.2,19.6,20.0,19.9,99999.99999999999
      2024-01-03,19.84952380952381,20.25142857142857,19.64952380952381,20.05047619047619,19.9498,101000.0
      """

  @JDL-072 @JDL-075 @JDL-138
  Scenario: Exporting a series whose volumes are all integral writes an int64 Volume
    Given the universe fixture "divy.toml"
    And the "eodhd" provider replays "divy/run1"
    And sync ran at "2024-03-29T01:00:00Z"
    Then the export frame of eodhd/DIVY.US equals the expected frame "divy_export"
    And the export frame of eodhd/DIVY.US has the dtypes:
      | column    | dtype   |
      | Date      | text    |
      | Open      | float64 |
      | High      | float64 |
      | Low       | float64 |
      | Close     | float64 |
      | Adj Close | float64 |
      | Volume    | int64   |
    When I run "jef-data export --symbol DIVY.US --output divy.csv --store {store}"
    Then the file "divy.csv" starts with:
      """
      Date,Open,High,Low,Close,Adj Close,Volume
      2024-03-01,94.8,95.4,94.5,95.0,94.37,50000
      """

  @JDL-073 @JDL-074 @JDL-138 @JDL-078 @JDL-079
  Scenario: The export passes zero-volume rows through and the report announces the seam's drop
    Given the store holds "yahoo_small.csv" as yahoo/SMALL declared stock
    Then the export frame of yahoo/SMALL equals the expected frame "small_export"
    When I run "jef-data export --symbol SMALL --exchange yahoo --output small.csv --store {store}"
    Then the exit code is 0
    And stdout is:
      """
      yahoo/SMALL: 4 row(s) -> small.csv
      note:  1 zero-volume row(s) - dropped at load by policy
      note:  3 clean row(s) < recommended minimum 1115 (720 warm-up + 395 lags) - the default counter window needs more history (docs/DATA_CONTRACT.md §1)
      """
    And the file "small.csv" is:
      """
      Date,Open,High,Low,Close,Adj Close,Volume
      2024-01-02,10.0,11.0,9.5,10.5,10.4,1000
      2024-01-03,10.5,11.5,10.0,11.0,10.9,0
      2024-01-04,11.0,12.0,10.5,11.5,11.4,1200
      2025-01-02,12.0,12.5,11.5,12.25,12.2,1300
      """

  @JDL-138 @JDL-134
  Scenario: Exporting a series with no stored rows fails without writing the file
    When I run "jef-data export --symbol NONE.US --output none.csv --store {store}"
    Then the exit code is 1
    And stdout is empty
    And the file "none.csv" does not exist

  @JDL-135 @JDL-081 @JDL-080
  Scenario Outline: Validating a clean CSV, with and without enough history
    When I run "jef-data validate {fixtures}/csv/stock_feb.csv <flags>"
    Then the exit code is 0
    And stdout is:
      """
      {fixtures}/csv/stock_feb.csv: 22 rows
      <report>
      """

    Examples:
      | flags         | report |
      | --min-rows 22 | contract: clean |
      | --min-rows 23 | note:  22 clean row(s) < recommended minimum 23 (720 warm-up + 395 lags) - the default counter window needs more history (docs/DATA_CONTRACT.md §1) |
      |               | note:  22 clean row(s) < recommended minimum 1115 (720 warm-up + 395 lags) - the default counter window needs more history (docs/DATA_CONTRACT.md §1) |

  @JDL-135 @JDL-076 @JDL-077 @JDL-078 @JDL-081
  Scenario: Shape, numeric and date findings, errors before notes
    When I run "jef-data validate {fixtures}/csv/invalid_mix.csv"
    Then the exit code is 1
    And stdout is:
      """
      {fixtures}/csv/invalid_mix.csv: 4 rows
      ERROR: non-numeric values in ['Open']
      ERROR: 1 duplicate date(s) - forbidden by the contract
      note:  extra columns ['Extra'] are carried through; NaNs in them will drop rows at load (the transform drops any-NaN rows)
      note:  1 unparseable date(s) - those rows drop at load
      note:  dates not sorted ascending - the load transform sorts
      """

  @JDL-135 @JDL-079
  Scenario: Value findings when every column is numeric
    When I run "jef-data validate {fixtures}/csv/invalid_values.csv --min-rows 1"
    Then the exit code is 1
    And stdout is:
      """
      {fixtures}/csv/invalid_values.csv: 4 rows
      ERROR: negative prices in ['Open']
      ERROR: negative values in Volume
      ERROR: 1 row(s) with High < Low
      note:  1 zero-volume row(s) - dropped at load by policy
      note:  1 row(s) with NaN - dropped at load
      """

  @JDL-135 @JDL-076 @JDL-078
  Scenario Outline: Findings that stop the validation early
    When I run "jef-data validate {fixtures}/csv/<csv>"
    Then the exit code is 1
    And stdout is:
      """
      {fixtures}/csv/<csv>: <rows> rows
      ERROR: <error>
      """

    Examples:
      | csv              | rows | error |
      | missing_cols.csv | 1    | missing required columns: ['High', 'Low', 'Adj Close', 'Volume'] |
      | no_dates.csv     | 2    | no parseable dates in 'Date' |
