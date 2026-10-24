Feature: The sync ritual - selection, windows, ordering, containment and reporting

  Background:
    Given an empty store

  @JDL-084 @JDL-086 @JDL-007 @JDL-001
  Scenario: The packaged universe expands into nine ordered legs
    Given the packaged universe
    When the legs are selected
    Then the legs are:
      """
      [{"asset": "AAPL", "provider": "eodhd", "exchange": "eodhd", "symbol": "AAPL.US", "path": null, "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": true},
       {"asset": "AAPL", "provider": "yahoo-csv", "exchange": "yahoo", "symbol": "AAPL", "path": "experiments/AAPL.csv", "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": false},
       {"asset": "BTC", "provider": "eodhd", "exchange": "eodhd", "symbol": "BTC-USD.CC", "path": null, "asset_type": "crypto", "currency": "USD", "start": null, "end": null, "actions": false},
       {"asset": "BTC", "provider": "binance", "exchange": "binance", "symbol": "BTCUSDT", "path": null, "asset_type": "crypto", "currency": "USD", "start": "2017-08-01", "end": null, "actions": false},
       {"asset": "BTC", "provider": "yahoo-csv", "exchange": "yahoo", "symbol": "BTC-USD", "path": "experiments/BTC-USD_feb2024.csv", "asset_type": "crypto", "currency": "USD", "start": null, "end": null, "actions": false},
       {"asset": "TLT", "provider": "eodhd", "exchange": "eodhd", "symbol": "TLT.US", "path": null, "asset_type": "etf", "currency": "USD", "start": null, "end": null, "actions": true},
       {"asset": "NVDA", "provider": "eodhd", "exchange": "eodhd", "symbol": "NVDA.US", "path": null, "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": true},
       {"asset": "TSLA", "provider": "eodhd", "exchange": "eodhd", "symbol": "TSLA.US", "path": null, "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": true},
       {"asset": "IBM", "provider": "eodhd", "exchange": "eodhd", "symbol": "IBM.US", "path": null, "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": true}]
      """

  @JDL-084
  Scenario: Asset and provider filters keep universe order and skip paused assets and switched-off sources
    Given the packaged universe
    When the legs are selected with options "assets=TLT|BTC, providers=binance|eodhd"
    Then the legs are:
      """
      [{"asset": "BTC", "provider": "eodhd", "exchange": "eodhd", "symbol": "BTC-USD.CC", "path": null, "asset_type": "crypto", "currency": "USD", "start": null, "end": null, "actions": false},
       {"asset": "BTC", "provider": "binance", "exchange": "binance", "symbol": "BTCUSDT", "path": null, "asset_type": "crypto", "currency": "USD", "start": "2017-08-01", "end": null, "actions": false},
       {"asset": "TLT", "provider": "eodhd", "exchange": "eodhd", "symbol": "TLT.US", "path": null, "asset_type": "etf", "currency": "USD", "start": null, "end": null, "actions": true}]
      """
    Given the universe fixture "paused.toml"
    When the legs are selected
    Then the legs are:
      """
      [{"asset": "SPLT", "provider": "eodhd", "exchange": "eodhd", "symbol": "SPLT.US", "path": null, "asset_type": "stock", "currency": "USD", "start": "2024-01-02", "end": null, "actions": true}]
      """

  @JDL-085 @JDL-087 @JDL-144 @JDL-145 @JDL-134
  Scenario Outline: Selection refusals of sync and status
    Given the universe fixture "paused.toml"
    When I run "jef-data <command> --universe universe.toml --store {store} <flags>"
    Then the exit code is 1
    And stdout is empty
    And stderr is:
      """
      <command>: <message>
      """

    Examples:
      | command | flags                     | message |
      | sync    | --asset NOPE              | unknown asset 'NOPE'; universe has ['GONE', 'SPLT'] |
      | status  | --asset SPLT --asset NOPE | unknown asset 'NOPE'; universe has ['GONE', 'SPLT'] |
      | sync    | --provider yahoo          | unknown provider 'yahoo'; allowed: ['eodhd', 'binance', 'yahoo-csv'] |
      | status  | --asset NOPE --provider x | unknown asset 'NOPE'; universe has ['GONE', 'SPLT'] |
      | sync    | --asset GONE              | selection matched no enabled asset/source legs |
      | status  | --provider binance        | selection matched no enabled asset/source legs |
      | sync    | --tail 0 --asset NOPE     | tail must be >= 1 session, got 0 |

  @JDL-094 @JDL-098 @JDL-088
  Scenario Outline: A universe end caps the first fill, and wins the minimum against the crypto end-guard
    Given the universe fixture "<universe>"
    And the "eodhd" provider replays "<set>"
    When sync runs at "<now>"
    Then the run is ok
    And the detail of leg 1 is "<detail>"
    And the stored series eodhd/<symbol> has <rows> rows

    Examples:
      | universe      | set         | now                  | symbol      | rows | detail |
      | splt_end.toml | splt/endcap | 2024-02-13T12:00:00Z | SPLT.US     | 14   | 2 split(s), 1 dividend(s); 14 bar(s), 0 revised cell(s) |
      | zero_end.toml | zero/endcap | 2024-02-10T08:00:00Z | ZERO-USD.CC | 20   | 20 bar(s), 0 revised cell(s) |

  @JDL-095 @JDL-097 @JDL-105 @JDL-104
  Scenario: A series with rows past its declared end fetches nothing and stays green
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the universe fixture "splt_end.toml"
    When sync runs at "2024-02-14T12:00:00Z" with options "dry_run=true"
    Then the sync log is:
      """
      plan for store '{store}' (1 leg(s)):
          SPLT eodhd/SPLT.US: sync-actions + load (reconcile tail of 10 session(s) from 2024-01-30 to 2024-01-19 - INVERTED: end predates the stored tail, nothing to fetch)
      """
    When sync runs at "2024-02-14T12:00:00Z"
    Then the run is ok
    And the detail of leg 1 is "actions fresh; end 2024-01-19 predates the stored tail (from 2024-01-30); nothing fetched - a pinned window with rows past its end, the fix is the declaration; 0 bar(s), 0 revised cell(s)"
    And the stored series eodhd/SPLT.US equals the expected frame "splt_run1_stored"

  @JDL-098 @JDL-088
  Scenario: An equity bar dated on the run's UTC day is ingested and flagged
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    When sync runs at "2024-02-12T18:00:00Z"
    Then the run is ok
    And the detail of leg 1 is "2 split(s), 1 dividend(s); 30 bar(s), 0 revised cell(s); today-dated bar ingested (pre-close fetch?)"

  @JDL-093 @JDL-087
  Scenario: The tail window starts at the oldest of the newest N stored sessions
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    When sync runs at "2024-02-14T12:00:00Z" with options "dry_run=true, tail=3"
    Then the sync log is:
      """
      plan for store '{store}' (1 leg(s)):
          SPLT eodhd/SPLT.US: sync-actions + load (reconcile tail of 3 session(s) from 2024-02-08)
      """
    When sync runs at "2024-02-14T12:00:00Z" with options "dry_run=true, tail=1"
    Then the sync log is:
      """
      plan for store '{store}' (1 leg(s)):
          SPLT eodhd/SPLT.US: sync-actions + load (reconcile tail of 1 session(s) from 2024-02-12)
      """
    When sync runs at "2024-02-14T12:00:00Z" with options "tail=0"
    Then the sync is refused with "tail must be >= 1 session, got 0"

  @JDL-104 @JDL-105 @JDL-106 @JDL-094
  Scenario: A dry run plans every leg shape from local state only
    Given the universe fixture "plan.toml"
    When sync runs at "2024-03-01T06:00:00Z" with options "dry_run=true"
    Then the run is ok
    And the sync log is:
      """
      plan for store '{store}' (5 leg(s)):
          SPLT eodhd/SPLT.US: sync-actions + load (first fill from 2024-01-02 to 2024-01-19)
          DIVY eodhd/DIVY.US: sync-actions + load (first fill, full history)
          DIVY snap/DIVY: import snap/divy.csv (whole file, idempotent)
          PAIR eodhd/PAIR-USD.CC: load (first fill from 2024-01-01 to 2024-02-29)
          PAIR binance/PAIRUSDT: load (first fill, full history to 2024-02-29)
      """
    And the sync summary is:
      """
      {"schema_version": 1, "legs_total": 5, "legs_failed": 0, "revised_cells_total": 0, "ok": true,
       "legs": [
        {"asset": "SPLT", "provider": "eodhd", "exchange": "eodhd", "symbol": "SPLT.US", "ok": true, "detail": "planned", "revised_cells": 0, "revisions": []},
        {"asset": "DIVY", "provider": "eodhd", "exchange": "eodhd", "symbol": "DIVY.US", "ok": true, "detail": "planned", "revised_cells": 0, "revisions": []},
        {"asset": "DIVY", "provider": "yahoo-csv", "exchange": "snap", "symbol": "DIVY", "ok": true, "detail": "planned", "revised_cells": 0, "revisions": []},
        {"asset": "PAIR", "provider": "eodhd", "exchange": "eodhd", "symbol": "PAIR-USD.CC", "ok": true, "detail": "planned", "revised_cells": 0, "revisions": []},
        {"asset": "PAIR", "provider": "binance", "exchange": "binance", "symbol": "PAIRUSDT", "ok": true, "detail": "planned", "revised_cells": 0, "revisions": []}]}
      """
    And the store holds exactly the files:
      """
      """

  @JDL-101 @JDL-103 @JDL-106 @JDL-102
  Scenario: One failing leg does not stop the others and the run turns red
    Given the universe fixture "mixed.toml"
    And the "eodhd" provider replays "mixed"
    When sync runs at "2024-03-29T01:00:00Z"
    Then the run is not ok
    And the sync log is:
      """
      FAILED  SPLT eodhd/SPLT.US [eodhd]: CollectorError: eod SPLT.US: HTTP 404: {"error": "Ticker Not Found."}
      ok      DIVY eodhd/DIVY.US [eodhd]: 0 split(s), 3 dividend(s); 20 bar(s), 0 revised cell(s)
      2 leg(s), 1 failed -> store '{store}'
      """
    And the sync summary is:
      """
      {"schema_version": 1, "legs_total": 2, "legs_failed": 1, "revised_cells_total": 0, "ok": false,
       "legs": [
        {"asset": "SPLT", "provider": "eodhd", "exchange": "eodhd", "symbol": "SPLT.US", "ok": false, "detail": "CollectorError: eod SPLT.US: HTTP 404: {\"error\": \"Ticker Not Found.\"}", "revised_cells": 0, "revisions": []},
        {"asset": "DIVY", "provider": "eodhd", "exchange": "eodhd", "symbol": "DIVY.US", "ok": true, "detail": "0 split(s), 3 dividend(s); 20 bar(s), 0 revised cell(s)", "revised_cells": 0, "revisions": []}]}
      """

  @JDL-106 @JDL-098
  Scenario: The summary carries every revision as plain numbers
    Given the universe fixture "splt.toml"
    And the "eodhd" provider replays "splt/run1"
    And sync ran at "2024-02-13T12:00:00Z"
    And the "eodhd" provider replays "splt/run2"
    When sync runs at "2024-02-14T12:00:00Z"
    Then the sync summary is:
      """
      {"schema_version": 1, "legs_total": 1, "legs_failed": 0, "revised_cells_total": 3, "ok": true,
       "legs": [{"asset": "SPLT", "provider": "eodhd", "exchange": "eodhd", "symbol": "SPLT.US", "ok": true,
                 "detail": "actions fresh; 11 bar(s), 3 revised cell(s)", "revised_cells": 3,
                 "revisions": [{"date": "2024-02-08", "column": "close_raw", "stored": 21.35, "served": 21.31},
                               {"date": "2024-02-08", "column": "adjusted_close", "stored": 21.2432, "served": 21.2},
                               {"date": "2024-02-09", "column": "volume_raw", "stored": 128000.0, "served": 777777.0}]}]}
      """

  @JDL-099 @JDL-070
  Scenario: A committed CSV leg imports its whole file without any collector
    Given the universe file:
      """
      [[asset]]
      name = "SMALL"
      asset_class = "stock"

        [[asset.source]]
        provider = "yahoo-csv"
        path = "{fixtures}/csv/yahoo_small.csv"
        symbol = "SMALL"
      """
    When sync runs at "2024-03-01T06:00:00Z"
    Then the run is ok
    And the detail of leg 1 is "5 row(s) imported"
    And the stored series yahoo/SMALL equals the expected frame "small_stored"

  @JDL-144 @JDL-089 @JDL-104 @JDL-106
  Scenario: The CLI dry run uses the universe's default store and still writes the summary
    Given the universe fixture "csv_leg.toml"
    When I run "jef-data sync --universe universe.toml --dry-run --summary-json plan.json"
    Then the exit code is 0
    And stdout is:
      """
      plan for store 'dstore' (2 leg(s)):
         SMALL eodhd/SMALL.US: sync-actions + load (first fill, full history)
         SMALL yahoo/SMALL: import snap/small.csv (whole file, idempotent)
      """
    And the JSON file "plan.json" is written sorted with 1-space indentation
    And the JSON file "plan.json" is:
      """
      {"legs": [{"asset": "SMALL", "detail": "planned", "exchange": "eodhd", "ok": true, "provider": "eodhd", "revised_cells": 0, "revisions": [], "symbol": "SMALL.US"},
                {"asset": "SMALL", "detail": "planned", "exchange": "yahoo", "ok": true, "provider": "yahoo-csv", "revised_cells": 0, "revisions": [], "symbol": "SMALL"}],
       "legs_failed": 0, "legs_total": 2, "ok": true, "revised_cells_total": 0, "schema_version": 1}
      """

  @JDL-099 @JDL-101 @JDL-144
  Scenario: A committed CSV leg whose file is missing fails that leg alone
    Given the universe fixture "csv_leg.toml"
    When I run "jef-data sync --universe universe.toml --store {store} --provider yahoo-csv"
    Then the exit code is 1
    And stdout is:
      """
      FAILED  SMALL yahoo/SMALL [yahoo-csv]: FileNotFoundError: [Errno 2] No such file or directory: 'snap/small.csv'
      1 leg(s), 1 failed -> store '{store}'
      """

  @JDL-064 @JDL-093 @JDL-109
  Scenario: The tail window and the latest session read across year files
    Given the universe file:
      """
      [[asset]]
      name = "SMALL"
      asset_class = "stock"

        [[asset.source]]
        provider = "eodhd"
        symbol = "SMALL.US"
      """
    And the store holds "yahoo_small.csv" as eodhd/SMALL.US declared stock
    When sync runs at "2025-01-03T06:00:00Z" with options "dry_run=true, tail=3"
    Then the sync log is:
      """
      plan for store '{store}' (1 leg(s)):
         SMALL eodhd/SMALL.US: sync-actions + load (reconcile tail of 3 session(s) from 2024-01-03)
      """
    When status runs at "2025-01-03T06:00:00Z"
    Then report 1 has the fields:
      | key             | value        |
      | last_session    | "2025-01-02" |
      | missed_sessions | 0            |
      | rows            | 4            |
