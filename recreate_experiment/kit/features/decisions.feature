Feature: The decision tables, row by row - revision 2026-10-23 (wave 2)
  Each Rule is one DMN decision table of contracts/dmn/ (same name). Every
  Examples table carries a `row` column naming the DMN rule it exercises
  (rN = the table's N-th rule); a plain Scenario names its row in a
  `# dmn-row:` comment. harness/dmn_coverage.py joins the two and reports
  the rows no example reaches. Three rows have no example, each for a
  stated reason: volume_raw_source r2 (no raw-basis collector other than
  EODHD exists, the row is contract only) and command_by_store_state r4,
  r5 (`load`'s happy path runs the live transport, which the kit's seams
  cannot replay; the existing suite reaches only its refusals).

  Background:
    Given an empty store

  Rule: price_basis_resolution

    @JDL-053 @JDL-055 @JDL-086 @JDL-100
    Scenario Outline: The provider and the declared class decide the basis and the actions part
      Given the universe fixture "<universe>"
      And the "<provider>" provider replays "<set>"
      When sync runs at "<now>" with options "providers=<provider>"
      Then the run is ok
      And every stored row of <exchange>/<symbol> has price_basis "<basis>"
      And the detail of leg 1 starts with "<detail_start>"

      Examples:
        | row | universe  | provider | set       | now                  | exchange | symbol      | basis          | detail_start |
        | r1  | splt.toml | eodhd    | splt/run1 | 2024-02-13T12:00:00Z | eodhd    | SPLT.US     | raw            | 2 split(s), 1 dividend(s); 30 bar(s) |
        | r2  | divy.toml | eodhd    | divy/run1 | 2024-03-29T01:00:00Z | eodhd    | DIVY.US     | raw            | 0 split(s), 3 dividend(s); 20 bar(s) |
        | r3  | zero.toml | eodhd    | zero/run1 | 2024-02-10T08:00:00Z | eodhd    | ZERO-USD.CC | split_adjusted | 40 bar(s) |
        | r4  | pair.toml | binance  | pair/at   | 2024-01-21T06:00:00Z | binance  | PAIRUSDT    | split_adjusted | 20 bar(s) |

    @JDL-099 @JDL-070
    Scenario Outline: A yahoo-csv leg is always split_adjusted
      Given the universe fixture "csv_leg.toml"
      And the work directory holds the CSV "yahoo_small.csv" as "snap/small.csv"
      When I run "jef-data sync --universe universe.toml --store {store} --provider yahoo-csv"
      Then the exit code is 0
      And stdout contains the line "<log_line>"
      And every stored row of yahoo/SMALL has price_basis "split_adjusted"

      Examples:
        | row | log_line |
        | r5  | ok      SMALL yahoo/SMALL [yahoo-csv]: 5 row(s) imported |

  Rule: volume_raw_source
    # r2 (raw basis, a collector other than EODHD) has no example: no such
    # collector exists; the row states the contract for one.

    @JDL-056 @JDL-055
    Scenario Outline: volume_raw is raw-ized only for EODHD raw-basis series
      Given the universe fixture "<universe>"
      And the "eodhd" provider replays "<set>"
      When sync runs at "<now>"
      Then the stored cells of eodhd/<symbol> are:
        | date   | column     | value        |
        | <date> | volume_raw | <volume_raw> |

      Examples:
        | row | universe  | set       | now                  | symbol      | date       | volume_raw        |
        | r1  | splt.toml | splt/run1 | 2024-02-13T12:00:00Z | SPLT.US     | 2024-01-02 | 9523.809523809523 |
        | r3  | zero.toml | zero/run1 | 2024-02-10T08:00:00Z | ZERO-USD.CC | 2024-01-09 | 3080.0            |

  Rule: command_by_store_state
    # r4, r5 (`load` on an absent / filled series) have no example: the
    # command's happy path needs a live EODHD transport.

    @JDL-093
    Scenario Outline: A collector leg first-fills an absent series
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      When sync runs at "2024-02-13T12:00:00Z"
      Then the run is ok
      And the detail of leg 1 is "<detail>"

      Examples:
        | row | detail |
        | r1  | 2 split(s), 1 dividend(s); 30 bar(s), 0 revised cell(s) |

    @JDL-099 @JDL-070
    Scenario Outline: A CSV leg overwrites whatever is there
      Given the universe fixture "csv_leg.toml"
      And the work directory holds the CSV "yahoo_small.csv" as "snap/small.csv"
      And the store holds "stock_feb.csv" as yahoo/SMALL declared stock
      When I run "jef-data sync --universe universe.toml --store {store} --provider yahoo-csv"
      Then the exit code is 0
      And stdout contains the line "<log_line>"
      # 5 CSV rows, one a duplicate date: only the first is stored (JDL-070)
      And the stored series yahoo/SMALL has 4 rows

      Examples:
        | row | log_line |
        | r3  | ok      SMALL yahoo/SMALL [yahoo-csv]: 5 row(s) imported |

    @JDL-093 @JDL-065
    Scenario Outline: A collector leg tail-refreshes a filled series
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      And sync ran at "2024-02-13T12:00:00Z"
      And the "eodhd" provider replays "splt/run2"
      When sync runs at "2024-02-14T12:00:00Z"
      Then the run is ok
      And the detail of leg 1 is "<detail>"

      Examples:
        | row | detail |
        | r2  | actions fresh; 11 bar(s), 3 revised cell(s) |

    @JDL-069 @JDL-159 @JDL-163 @JDL-134
    Scenario Outline: The store commands on an absent series
      Given the store holds "yahoo_small.csv" as yahoo/SMALL declared stock
      When I run "<command>"
      Then the exit code is 1
      And stdout is empty
      And stderr contains "<stderr_part>"

      Examples:
        | row | command | stderr_part |
        | r6  | jef-data adjust --symbol GHOST.US --store {store} | StoreError: nothing stored for eodhd/GHOST.US |
        | r12 | jef-data export --symbol GHOST --exchange eodhd --output x.csv --store {store} | AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'? |
        | r13 | jef-data differential --a-symbol GHOST --a-exchange eodhd --b-csv {fixtures}/csv/diff_b.csv --store {store} | AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'? |
        | r14 | jef-data differential --a-symbol SMALL --a-exchange yahoo --b-symbol GHOST --b-exchange yahoo --store {store} | AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'? |

    # dmn-row: r8
    @JDL-070 @JDL-137
    Scenario: import-csv overwrites, whatever the store held
      Given the store holds "yahoo_small.csv" as eodhd/FEB.US declared stock
      When I run "jef-data import-csv --csv {fixtures}/csv/stock_feb.csv --symbol FEB.US --exchange eodhd --asset-type etf --store {store}"
      Then the exit code is 0
      And stdout contains the line "{fixtures}/csv/stock_feb.csv: 22 row(s) -> {store}/market_data/exchange=eodhd/symbol=FEB.US/ (price_basis=split_adjusted)"
      And the stored series eodhd/FEB.US has 22 rows

    @JDL-069 @JDL-138 @JDL-082 @JDL-134
    Scenario Outline: The store commands on a filled raw-basis series
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      And sync ran at "2024-02-13T12:00:00Z"
      When I run "<command>"
      Then the exit code is <rc>
      And stdout contains the line "<stdout_line>"

      Examples:
        | row | command | rc | stdout_line |
        | r7  | jef-data adjust --symbol SPLT.US --store {store} | 0 | eodhd/SPLT.US: 30 row(s) re-derived from *_raw with 2 split(s) |
        | r9  | jef-data export --symbol SPLT.US --exchange eodhd --output out.csv --store {store} | 0 | eodhd/SPLT.US: 30 row(s) -> out.csv |
        | r15 | jef-data differential --a-symbol SPLT.US --a-exchange eodhd --b-csv {fixtures}/csv/diff_b.csv --store {store} | 1 | differential: eodhd/SPLT.US vs {fixtures}/csv/diff_b.csv (relative tolerance 0.0001) |
        | r16 | jef-data differential --a-symbol SPLT.US --a-exchange eodhd --b-symbol SPLT.US --b-exchange eodhd --store {store} | 0 | VERDICT: within tolerance, aligned |

    @JDL-114 @JDL-110
    Scenario Outline: Status on an absent and on a filled series
      Given the universe file:
        """
        [[asset]]
        name = "STK"
        asset_class = "stock"

          [[asset.source]]
          provider = "eodhd"
          symbol = "STK.US"
        """
      And the store holds "<csv>" as eodhd/<stored_as> declared stock
      And the splits file of "STK.US" stamped "2024-03-04T00:00:00Z" with no splits
      When status runs at "2024-03-04T09:00:00Z"
      Then the status exit code is <rc>
      And report 1 has alerts:
        """
        <alerts>
        """

      Examples:
        | row | csv           | stored_as | rc | alerts |
        | r10 | stock_feb.csv | OTHER.US  | 1  | never filled - no stored rows (jef-data sync first) |
        | r11 | stock_feb.csv | STK.US    | 0  | |

  Rule: fetch_start

    @JDL-093 @JDL-105 @JDL-104
    Scenario Outline: The first fill starts at the universe start, or is open
      Given the universe fixture "<universe>"
      When sync runs at "2024-02-14T12:00:00Z" with options "dry_run=true"
      Then the sync log is:
        """
        plan for store '{store}' (1 leg(s)):
            <plan>
        """

      Examples:
        | row | universe  | plan |
        | r1  | splt.toml | SPLT eodhd/SPLT.US: sync-actions + load (first fill from 2024-01-02) |
        | r2  | divy.toml | DIVY eodhd/DIVY.US: sync-actions + load (first fill, full history) |

    @JDL-093 @JDL-105
    Scenario Outline: A filled series starts at the oldest of its newest tail sessions
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      And sync ran at "2024-02-13T12:00:00Z"
      When sync runs at "2024-02-14T12:00:00Z" with options "dry_run=true, tail=<tail>"
      Then the sync log is:
        """
        plan for store '{store}' (1 leg(s)):
            <plan>
        """

      Examples:
        | row | tail | plan |
        | r3  | 3    | SPLT eodhd/SPLT.US: sync-actions + load (reconcile tail of 3 session(s) from 2024-02-08) |

  Rule: fetch_end

    @JDL-094 @JDL-105
    Scenario Outline: The fetch end is the ISO minimum of the universe end and the crypto end-guard
      Given the universe fixture "<universe>"
      When sync runs at "2024-02-10T08:00:00Z" with options "dry_run=true"
      Then the sync log is:
        """
        plan for store '{store}' (1 leg(s)):
            <plan>
        """

      Examples:
        | row | universe      | plan |
        | r1  | zero_end.toml | ZERO eodhd/ZERO-USD.CC: load (first fill from 2024-01-01 to 2024-01-20) |
        | r2  | zero.toml     | ZERO eodhd/ZERO-USD.CC: load (first fill from 2024-01-01 to 2024-02-09) |
        | r3  | splt_end.toml | SPLT eodhd/SPLT.US: sync-actions + load (first fill from 2024-01-02 to 2024-01-19) |
        | r4  | divy.toml     | DIVY eodhd/DIVY.US: sync-actions + load (first fill, full history) |

  Rule: bar_request

    # dmn-row: r1
    @JDL-095
    Scenario: A filled series whose end predates its tail sends no request and stays green
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      And sync ran at "2024-02-13T12:00:00Z"
      And the universe fixture "splt_end.toml"
      When sync runs at "2024-02-14T12:00:00Z"
      Then the run is ok
      And the detail of leg 1 is "actions fresh; end 2024-01-19 predates the stored tail (from 2024-01-30); nothing fetched - a pinned window with rows past its end, the fix is the declaration; 0 bar(s), 0 revised cell(s)"

    # dmn-row: r2
    @JDL-093
    Scenario: A filled series with a well-ordered window sends its request
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      And sync ran at "2024-02-13T12:00:00Z"
      And the "eodhd" provider replays "splt/run2"
      When sync runs at "2024-02-14T12:00:00Z"
      Then the run is ok
      And the detail of leg 1 is "actions fresh; 11 bar(s), 3 revised cell(s)"

    # dmn-row: r3
    @JDL-095
    Scenario: An empty series sends its request even when the end-guard falls before the declared start
      Given the universe fixture "zero.toml"
      And the "eodhd" provider replays "zero/run1"
      When sync runs at "2023-12-25T08:00:00Z"
      Then the run is not ok
      And the detail of leg 1 starts with "CollectorError: no recorded fixture for GET /api/eod/ZERO-USD.CC"

  Rule: actions_gate

    # dmn-row: r1
    @JDL-086 @JDL-098
    Scenario: A leg that is not actions-eligible has no actions part
      Given the universe fixture "zero.toml"
      And the "eodhd" provider replays "zero/run1"
      When sync runs at "2024-02-10T08:00:00Z"
      Then the run is ok
      And the detail of leg 1 starts with "40 bar(s)"

    # dmn-row: r2
    @JDL-091
    Scenario: force-actions refreshes whatever the stamp says
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      And sync ran at "2024-02-13T12:00:00Z"
      And the "eodhd" provider replays "splt/run2"
      When sync runs at "2024-02-14T12:00:00Z" with options "force_actions=true"
      Then the run is ok
      And the detail of leg 1 starts with "2 split(s), 1 dividend(s); "

    # dmn-row: r3
    @JDL-091
    Scenario: No stamp means refresh
      Given the universe fixture "splt.toml"
      And the "eodhd" provider replays "splt/run1"
      When sync runs at "2024-02-13T12:00:00Z"
      Then the run is ok
      And the detail of leg 1 starts with "2 split(s), 1 dividend(s); "

    @JDL-091
    Scenario Outline: A stamp from an earlier UTC day refreshes, one from today or later skips
      Given the universe fixture "splt.toml"
      And the splits file of "SPLT.US" stamped "<stamp>" with no splits
      And the "eodhd" provider replays "splt/run1"
      When sync runs at "<now>"
      Then the run is ok
      And the detail of leg 1 starts with "<detail_start>"

      Examples:
        | row | stamp                | now                  | detail_start |
        | r4  | 2024-02-12T23:59:59Z | 2024-02-13T00:00:01Z | 2 split(s), 1 dividend(s); |
        | r5  | 2024-02-13T00:00:00Z | 2024-02-13T23:59:59Z | actions fresh; |
        | r5  | 2024-02-14T00:00:00Z | 2024-02-13T12:00:00Z | actions fresh; |

  Rule: staleness_check

    # dmn-row: r1
    @JDL-114 @JDL-109
    Scenario: A never-filled series alerts and its report ends there
      Given the universe fixture "splt.toml"
      When status runs at "2024-03-04T09:00:00Z"
      Then the status exit code is 1
      And report 1 has alerts:
        """
        never filled - no stored rows (jef-data sync first)
        """
      And report 1 lacks the field "last_session"

    @JDL-116
    Scenario Outline: Missed sessions below the threshold pass, at it alert
      Given the universe file:
        """
        [[asset]]
        name = "STK"
        asset_class = "stock"

          [[asset.source]]
          provider = "eodhd"
          symbol = "STK.US"
        """
      And the store holds "stock_feb.csv" as eodhd/STK.US declared stock
      And the splits file of "STK.US" stamped "<now>" with no splits
      When status runs at "<now>"
      Then the status exit code is <rc>
      And report 1 has the fields:
        | key             | value    |
        | missed_sessions | <missed> |
      And report 1 has alerts:
        """
        <alert>
        """

      Examples:
        | row | now                  | missed | rc | alert |
        | r2  | 2024-03-05T09:00:00Z | 1      | 0  | |
        | r3  | 2024-03-06T09:00:00Z | 2      | 1  | stale: 2 expected session(s) missing since 2024-03-01 (multi-day holidays can trip this - verify before acting) |

  Rule: actions_freshness_check

    @JDL-125 @JDL-086
    Scenario Outline: Only actions-eligible legs are checked; the stamp's age decides
      Given the universe file:
        """
        [[asset]]
        name = "FRS"
        asset_class = "<class>"

          [[asset.source]]
          provider = "eodhd"
          symbol = "<symbol>"
        """
      And the store holds "stock_feb.csv" as eodhd/<symbol> declared <type>
      When status runs at "<now>" with options "staleness_k=10"
      Then report 1 has alerts:
        """
        <alert>
        """

      Examples:
        | row | class  | symbol     | type   | now                  | alert |
        | r1  | crypto | FRS-USD.CC | crypto | 2024-03-06T00:30:00Z | |
        | r2  | stock  | FRS.US     | stock  | 2024-03-04T00:30:00Z | corporate actions stale: never synced - run jef-data sync |

    @JDL-125
    Scenario Outline: Refresh sessions missed since the stamp, below and at the fixed threshold of 2
      Given the universe file:
        """
        [[asset]]
        name = "FRS"
        asset_class = "stock"

          [[asset.source]]
          provider = "eodhd"
          symbol = "FRS.US"
        """
      And the store holds "stock_feb.csv" as eodhd/FRS.US declared stock
      And the splits file of "FRS.US" stamped "2024-03-01T07:00:00Z" with no splits
      When status runs at "<now>" with options "staleness_k=10"
      Then report 1 has alerts:
        """
        <alert>
        """

      Examples:
        | row | now                  | alert |
        | r3  | 2024-03-05T00:30:00Z | |
        | r4  | 2024-03-06T00:30:00Z | corporate actions stale: 2 refresh session(s) missed since 2024-03-01 - run jef-data sync |

  Rule: phantom_jump_check

    @JDL-124
    Scenario Outline: A zero previous close is skipped; the threshold is strict; an unexplained jump alerts
      Given the universe file:
        """
        [[asset]]
        name = "JMP"
        asset_class = "crypto"

          [[asset.source]]
          provider = "eodhd"
          symbol = "JMP-USD.CC"
        """
      And the store holds "<csv>" as eodhd/JMP-USD.CC declared crypto
      When status runs at "2024-05-11T00:30:00Z" with options "<options>"
      Then report 1 has alerts:
        """
        <alerts>
        """

      Examples:
        | row | csv                 | options                       | alerts |
        | r1  | zero_close_jump.csv | window=10                     | phantom-split-shaped jump -100.0% on 2024-05-02 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |
        | r2  | jumps.csv           | window=10, jump_threshold=0.5 | phantom-split-shaped jump +66.7% on 2024-05-03 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |
        | r4  | jumps.csv           | window=10                     | phantom-split-shaped jump +66.7% on 2024-05-03 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)\nphantom-split-shaped jump +45.0% on 2024-05-08 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |

    # dmn-row: r3
    @JDL-124 @JDL-086
    Scenario: A same-day stored split excuses the jump of an actions-eligible leg
      Given the universe file:
        """
        [[asset]]
        name = "JMP"
        asset_class = "stock"

          [[asset.source]]
          provider = "eodhd"
          symbol = "JMP.US"
        """
      And the store holds "jumps.csv" as eodhd/JMP.US declared stock
      And the splits file of "JMP.US" stamped "2024-05-11T00:00:00Z" with splits:
        | date       | split | ratio |
        | 2024-05-03 | 5/3   | 1.6666666666666667 |
      When status runs at "2024-05-11T00:30:00Z"
      Then report 1 has alerts:
        """
        phantom-split-shaped jump +45.0% on 2024-05-08 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)
        """

  Rule: cross_venue_spread_check

    # dmn-row: r1
    @JDL-127
    Scenario: A pair without a common session is not measured
      Given the universe file:
        """
        [[asset]]
        name = "DUO"
        asset_class = "crypto"

          [[asset.source]]
          provider = "eodhd"
          symbol = "DUO-USD.CC"
          modeled = true

          [[asset.source]]
          provider = "binance"
          symbol = "DUOUSDT"
        """
      And the store holds "new_a.csv" as eodhd/DUO-USD.CC declared crypto
      And the store holds "old_b.csv" as binance/DUOUSDT declared crypto
      When status runs at "2024-06-01T00:30:00Z" with options "window=10"
      Then pair 1 is:
        """
        {"asset": "DUO", "kind": "cross_venue", "a": "eodhd/DUO-USD.CC", "b": "binance/DUOUSDT",
         "common_session": null, "spread": null, "threshold": 0.005,
         "alerts": [], "warnings": [],
         "notes": ["no common session in the newest 10 - spread not measured (see the staleness check)"]}
        """

    @JDL-129 @JDL-131
    Scenario Outline: A measured spread is always noted, warns strictly above the threshold, alerts when promoted
      Given the universe fixture "pair.toml"
      And the "eodhd" provider replays "pair/<set>"
      And the "binance" provider replays "pair/<set>"
      And sync ran at "2024-01-21T06:00:00Z"
      When status runs at "2024-01-21T06:00:00Z" with options "<options>"
      Then the status totals are <alerts> alerts and <warnings> warnings

      Examples:
        | row | set   | options                                    | alerts | warnings |
        | r2  | at    | spread_threshold=0.005                     | 0      | 0        |
        | r3  | above | spread_threshold=0.005                     | 0      | 1        |
        | r4  | above | spread_threshold=0.005, spread_alerts=true | 1      | 0        |

  Rule: status_exit_and_flag

    # dmn-row: r1
    @JDL-132 @JDL-131
    Scenario: Any alert sets exit 1 and flags the row ALERT
      Given the universe fixture "splt.toml"
      When I run "jef-data status --universe universe.toml --store {store}"
      Then the exit code is 1
      And stdout contains the line "ALERT   SPLT eodhd/SPLT.US: last -, - missed, 0 row(s)"

    @JDL-132 @JDL-131
    Scenario Outline: Warnings alone flag WARN at exit 0; nothing flags ok
      Given the universe file:
        """
        [[asset]]
        name = "<name>"
        asset_class = "<class>"

          [[asset.source]]
          provider = "eodhd"
          symbol = "<symbol>"
        """
      And the store holds "<csv>" as eodhd/<symbol> declared <type>
      And the splits file of "<symbol>" stamped "2099-02-01T00:00:00Z" with no splits
      When I run "jef-data status --universe universe.toml --store {store}"
      Then the exit code is 0
      And stdout contains the line "<line>"

      Examples:
        | row | name | class    | symbol     | type   | csv              | line |
        | r2  | IBM  | bond_etf | IBM.US     | etf    | future_stock.csv | WARN     IBM eodhd/IBM.US: last 2099-01-30, 0 missed, 22 row(s) |
        | r3  | FUT  | crypto   | FUT-USD.CC | crypto | future_crypto.csv | ok       FUT eodhd/FUT-USD.CC: last 2099-03-11, 0 missed, 70 row(s) |

  Rule: refusal_routing

    @JDL-134 @JDL-013 @JDL-085 @JDL-142 @JDL-069 @JDL-133
    Scenario Outline: Where an error is raised decides how the user sees it
      Given the universe fixture "<universe>"
      And EODHD_API_KEY is set to "test-key-not-real"
      When I run "<command>"
      Then the exit code is <rc>
      And stdout is empty
      And stderr contains "<stderr_part>"

      Examples:
        | row | universe                 | command | rc | stderr_part |
        | r1  | bad/asset_class_bad.toml | jef-data sync --universe universe.toml --store {store} | 1 | sync: asset |
        | r2  | splt.toml                | jef-data status --universe universe.toml --store {store} --asset NOPE | 1 | status: unknown asset 'NOPE'; universe has ['SPLT'] |
        | r4  | splt.toml                | jef-data load --symbol AAPL --store {store} | 1 | load: AAPL.US: asset_type is required |
        | r5  | splt.toml                | jef-data adjust --symbol GHOST.US --store {store} | 1 | StoreError: nothing stored for eodhd/GHOST.US |
        | r6  | splt.toml                | jef-data export --symbol X | 2 | usage: jef-data export |

    # dmn-row: r3
    @JDL-101 @JDL-103
    Scenario: An error inside a leg fails that leg only
      Given the universe fixture "mixed.toml"
      And the "eodhd" provider replays "mixed"
      When sync runs at "2024-03-29T01:00:00Z"
      Then the run is not ok
      And the sync log line 1 starts with "FAILED  SPLT eodhd/SPLT.US [eodhd]: CollectorError:"
      And leg 2 is ok
