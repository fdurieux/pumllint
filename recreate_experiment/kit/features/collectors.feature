Feature: Provider collectors replayed from recorded fixtures
  Collectors are driven through the harness adapter, whose collectors replay
  the recorded-fixture files under features/fixtures/http and never reach
  the network. Requests must match a recorded request identity exactly.

  Background:
    Given an empty store

  @JDL-029 @JDL-032 @JDL-024 @JDL-026
  Scenario: EODHD bars drop glitch rows, keep the first duplicate and sort by date
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is ok
    And the detail of leg 1 is "2 split(s), 1 dividend(s); 30 bar(s), 0 revised cell(s)"
    And the stored series eodhd/SPLT.US has 30 rows
    And the stored cells of eodhd/SPLT.US are:
      | date       | column    | value  |
      | 2024-01-04 | close_raw | 211.05 |
      | 2024-01-05 | close_raw | 211.57 |
      | 2024-01-10 | close_raw | 213.15 |
      | 2024-01-10 | volume    | 106000.0 |
      | 2024-01-24 | close_raw | 145.6  |

  @JDL-026 @JDL-023
  Scenario: The replayer keys on file content, walks subdirectories and skips manifest.json
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/replay"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is ok
    And the detail of leg 1 is "2 split(s), 1 dividend(s); 30 bar(s), 0 revised cell(s)"
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run1_stored"

  @JDL-025 @JDL-024
  Scenario: Every recorded fixture of the kit is named and laid out by its request identity
    Then every fixture file under "http" except the replay probes is named slug_digest and holds a request and a response

  @JDL-026 @JDL-024 @JDL-101
  Scenario: A request no fixture answers fails the leg and names what is known
    Given the universe file:
      """
      [[asset]]
      name = "SPLT"
      asset_class = "stock"

        [[asset.source]]
        provider = "eodhd"
        symbol = "SPLT.US"
        start = 2024-01-03
      """
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is not ok
    And leg 1 failed
    And the detail of leg 1 is:
      """
      CollectorError: no recorded fixture for GET /api/eod/SPLT.US {'fmt': 'json', 'from': '2024-01-03', 'order': 'a', 'period': 'd'}
      known fixtures:
        /api/div/SPLT.US {'fmt': 'json'}
        /api/eod/SPLT.US {'fmt': 'json', 'from': '2024-01-02', 'order': 'a', 'period': 'd'}
        /api/splits/SPLT.US {'fmt': 'json'}
      """

  @JDL-027 @JDL-028 @JDL-090
  Scenario: A 503 is retried five times, then the leg fails before any bar is fetched
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/splits503"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is not ok
    And the detail of leg 1 is "CollectorError: splits SPLT.US: HTTP 503 after 5 attempts"
    And the store holds exactly the files:
      """
      """

  @JDL-090 @JDL-028
  Scenario: When both the actions and the bars would fail, the actions failure is what the leg reports
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/both_fail"
    When sync runs at "2024-02-13T12:00:00Z"
    Then leg 1 failed
    And the detail of leg 1 is "CollectorError: splits SPLT.US: HTTP 503 after 5 attempts"

  @JDL-028 @JDL-090 @JDL-042
  Scenario: A 404 on the bars fails the leg after the corporate actions were refreshed
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/eod404"
    When sync runs at "2024-02-13T12:00:00Z"
    Then the run is not ok
    And the detail of leg 1 is "CollectorError: eod SPLT.US: HTTP 404: {"error": "Ticker Not Found."}"
    And the actions state of "SPLT.US" is:
      """
      {"splits": [{"date": "2024-01-17", "split": "3.000000/2.000000", "ratio": 1.5},
                  {"date": "2024-02-01", "split": "7/1", "ratio": 7.0}],
       "dividends": [{"currency": "USD", "date": "2024-01-25", "declarationDate": "2024-01-10",
                      "paymentDate": "2024-02-05", "period": "Quarterly", "recordDate": "2024-01-26",
                      "unadjustedValue": 0.24, "value": 0.24}]}
      """
    And the store holds exactly the files:
      """
      corporate_actions/dividends/SPLT.US.json
      corporate_actions/splits/SPLT.US.json
      """

  @JDL-032 @JDL-038 @JDL-028
  Scenario Outline: A bar endpoint answering something other than a JSON list fails the leg
    Given the universe fixture "<universe>"
    And the "<provider>" provider replays "<set>"
    When sync runs at "<now>" with options "assets=<asset>"
    Then leg 1 failed
    And the detail of leg 1 is "<detail>"

    Examples:
      | universe     | provider | set             | now                  | asset | detail |
      | splt.toml    | eodhd    | splt/notlist    | 2024-02-13T12:00:00Z | SPLT  | CollectorError: eod SPLT.US: expected a JSON list |
      | binance.toml | binance  | binance_notlist | 2024-07-01T00:30:00Z | LIM   | CollectorError: klines LIMUSDT: expected a JSON list |

  @JDL-033
  Scenario Outline: A split string that is not NEW/OLD fails the leg
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/<set>"
    When sync runs at "2024-02-13T12:00:00Z"
    Then leg 1 failed
    And the detail of leg 1 is "<detail>"

    Examples:
      | set       | detail |
      | badsplit  | ValueError: unparseable split string: '4:1' |
      | zerosplit | ValueError: degenerate split string: '0/1' |

  @JDL-036 @JDL-037 @JDL-039 @JDL-035 @JDL-100 @JDL-086 @JDL-044
  Scenario: Binance klines become pre-adjusted bars dated by their UTC open time
    Given the universe fixture "pair.toml"
    And the "eodhd" provider replays "pair/at"
    And the "binance" provider replays "pair/at"
    When sync runs at "2024-01-21T06:00:00Z"
    Then the run is ok
    And the detail of leg 2 is "20 bar(s), 0 revised cell(s)"
    And the stored series binance/PAIRUSDT equals the expected frame "pair_binance_stored"
    And the stored cells of binance/PAIRUSDT are:
      | date       | column                  | value          |
      | 2024-01-01 | timestamp               | 1704067200     |
      | 2024-01-01 | open                    | 89.95          |
      | 2024-01-01 | close                   | 89.95          |
      | 2024-01-01 | adjusted_close          | 89.95          |
      | 2024-01-01 | volume                  | 12.5           |
      | 2024-01-01 | volume_raw              | 12.5           |
      | 2024-01-01 | cumulative_split_factor | 1.0            |
      | 2024-01-01 | price_basis             | split_adjusted |
      | 2024-01-01 | asset_type              | crypto         |
      | 2024-01-20 | close                   | 99.75          |
    And the actions state of "PAIRUSDT" is empty
    And the actions state of "PAIR-USD.CC" is empty

  @JDL-038
  Scenario: Binance pages ascending from the declared start until a short page
    Given the universe fixture "binance.toml"
    And the "binance" provider replays "binance"
    When sync runs at "2024-01-16T00:30:00Z" with options "assets=PGS"
    Then the run is ok
    And the detail of leg 1 is "1110 bar(s), 0 revised cell(s)"
    And the stored cells of binance/PGSUSDT are:
      | date       | column | value |
      | 2021-01-01 | close  | 20.5  |
      | 2023-09-27 | close  | 24.5  |
      | 2023-09-28 | close  | 30.5  |
      | 2024-01-15 | close  | 30.5  |

  @JDL-096 @JDL-036
  Scenario: A first fill without a start that lands on the page limit says it is a trailing window
    Given the universe fixture "binance.toml"
    And the "binance" provider replays "binance"
    When sync runs at "2024-07-01T00:30:00Z" with options "assets=LIM"
    Then the run is ok
    And the detail of leg 1 is "first fill hit the provider page limit (1000 bars, no start declared) - the series is a trailing window, not history; 1000 bar(s), 0 revised cell(s)"
    And the stored series binance/LIMUSDT has 1000 rows

  @JDL-030 @JDL-102 @JDL-101 @JDL-099 @JDL-144 @JDL-103 @JDL-106
  Scenario: Without an EODHD key every EODHD leg fails and the CSV leg still lands
    Given the universe fixture "csv_leg.toml"
    And the work directory holds the CSV "yahoo_small.csv" as "snap/small.csv"
    When I run "jef-data sync --universe universe.toml --store {store} --summary-json red.json"
    Then the exit code is 1
    And stdout is:
      """
      FAILED  SMALL eodhd/SMALL.US [eodhd]: ValueError: EODHD API key required: pass api_key= or set EODHD_API_KEY
      ok      SMALL yahoo/SMALL [yahoo-csv]: 5 row(s) imported
      2 leg(s), 1 failed -> store '{store}'
      """
    And the stored series yahoo/SMALL has 4 rows
    And the JSON file "red.json" is written sorted with 1-space indentation
    And the JSON file "red.json" is:
      """
      {"legs": [{"asset": "SMALL", "detail": "ValueError: EODHD API key required: pass api_key= or set EODHD_API_KEY", "exchange": "eodhd", "ok": false, "provider": "eodhd", "revised_cells": 0, "revisions": [], "symbol": "SMALL.US"},
                {"asset": "SMALL", "detail": "5 row(s) imported", "exchange": "yahoo", "ok": true, "provider": "yahoo-csv", "revised_cells": 0, "revisions": [], "symbol": "SMALL"}],
       "legs_failed": 1, "legs_total": 2, "ok": false, "revised_cells_total": 0, "schema_version": 1}
      """

  @JDL-031 @JDL-142 @JDL-141 @JDL-134
  Scenario Outline: The hand-run load normalises the symbol and refuses a declaration it cannot trust
    Given EODHD_API_KEY is set to "test-key-not-real"
    When I run "jef-data load --symbol <symbol> <declared> --store {store}"
    Then the exit code is 1
    And stdout is empty
    And stderr is:
      """
      load: <message>
      """
    And the store holds exactly the files:
      """
      """

    Examples:
      | symbol     | declared          | message |
      | AAPL       |                   | AAPL.US: asset_type is required (one of ['crypto', 'etf', 'stock']). The ticker carries no instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly like equities - so the old 'stock' default was a guess written into the store as a fact, and TLT is in this repo's universe as an explicit override because that guess got it wrong. Only EODHD's .CC crypto namespace is evidence enough to infer from |
      | EUR/USD    |                   | EURUSD.FOREX: asset_type is required (one of ['crypto', 'etf', 'stock']). The ticker carries no instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly like equities - so the old 'stock' default was a guess written into the store as a fact, and TLT is in this repo's universe as an explicit override because that guess got it wrong. Only EODHD's .CC crypto namespace is evidence enough to infer from |
      | BTC-USD.CC | --asset-type stock | BTC-USD.CC is in EODHD's .CC crypto namespace but was declared asset_type='stock'; that combination cannot be true, and guessing either way decides whether split adjustment runs on pre-adjusted prices (docs/DATA_CONTRACT.md §2) |
      | btc/usdt   | --asset-type etf   | BTC-USDT.CC is in EODHD's .CC crypto namespace but was declared asset_type='etf'; that combination cannot be true, and guessing either way decides whether split adjustment runs on pre-adjusted prices (docs/DATA_CONTRACT.md §2) |

  @JDL-031 @JDL-030 @JDL-141 @JDL-143 @JDL-134
  Scenario Outline: Unwrapped collector errors of the hand-run EODHD commands
    Given EODHD_API_KEY is set to "<key>"
    When I run "<command>"
    Then the exit code is 1
    And stdout is empty
    And stderr ends with the line "<last line>"

    Examples:
      | key | command | last line |
      | k   | jef-data load --symbol XYZ/ABC --store {store} | CollectorError: cannot infer exchange for pair symbol 'XYZ/ABC' |
      |     | jef-data load --symbol AAPL.US --asset-type stock --store {store} | ValueError: EODHD API key required: pass api_key= or set EODHD_API_KEY |
      |     | jef-data sync-actions --symbol AAPL.US --store {store} | ValueError: EODHD API key required: pass api_key= or set EODHD_API_KEY |
