Feature: The read-only status verdicts - alerts, warnings, notes and the exit code
  Status runs through the harness adapter with an injected clock unless a
  scenario says it runs the executable. Alerts set the exit code; warnings
  and notes never do.

  Background:
    Given an empty store

  @JDL-114 @JDL-111 @JDL-112 @JDL-113 @JDL-130 @JDL-109 @JDL-127 @JDL-126 @JDL-107 @JDL-131
  Scenario: Never-filled series and the declared-class verdicts against the packaged evidence
    Given the universe fixture "classes.toml"
    When status runs at "2024-03-04T09:00:00Z"
    Then the status exit code is 1
    And the status document is:
      """
      {"schema_version": 1, "store": "{store}",
       "reports": [
        {"asset": "IBM", "exchange": "eodhd", "symbol": "IBM.US",
         "alerts": ["never filled - no stored rows (jef-data sync first)"],
         "warnings": ["declared class: declared asset_type 'etf' but the vendor says 'Common Stock' (-> 'stock'), recorded 2026-08-30 for eodhd/IBM.US - check the asset_class in universe.toml against docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2"],
         "notes": [], "declared_class_check": "disagree"},
        {"asset": "TLT", "exchange": "eodhd", "symbol": "TLT.US",
         "alerts": ["never filled - no stored rows (jef-data sync first)"], "warnings": [],
         "notes": ["declared class: vendor type 'ETF' agrees with declared asset_type 'etf', recorded 2026-08-30"],
         "declared_class_check": "agree"},
        {"asset": "BTC", "exchange": "eodhd", "symbol": "BTC-USD.CC",
         "alerts": ["never filled - no stored rows (jef-data sync first)"], "warnings": [],
         "notes": ["declared class: vendor type 'Currency' cannot confirm asset_type 'crypto', recorded 2026-08-30: the .CC (crypto) and .FOREX namespaces both serve it, so only the symbol's own namespace separates them and the evidence is not independent"],
         "declared_class_check": "not_comparable"},
        {"asset": "BTC", "exchange": "binance", "symbol": "BTCUSDT",
         "alerts": ["never filled - no stored rows (jef-data sync first)"], "warnings": [], "notes": []},
        {"asset": "SPLT", "exchange": "eodhd", "symbol": "SPLT.US",
         "alerts": ["never filled - no stored rows (jef-data sync first)"], "warnings": [],
         "notes": ["declared class: no vendor classification recorded - run tools/record_classifications.py"],
         "declared_class_check": "no_evidence"}],
       "pairs": [
        {"asset": "BTC", "kind": "cross_venue", "a": "eodhd/BTC-USD.CC", "b": "binance/BTCUSDT",
         "common_session": null, "spread": null, "threshold": 0.005, "alerts": [], "warnings": [],
         "notes": ["eodhd/BTC-USD.CC has no stored rows - spread not measured"]}],
       "alerts_total": 5, "warnings_total": 1}
      """

  @JDL-131 @JDL-111 @JDL-109 @JDL-110
  Scenario: A class disagreement on a healthy series warns without failing the day
    Given the universe file:
      """
      [[asset]]
      name = "IBM"
      asset_class = "bond_etf"

        [[asset.source]]
        provider = "eodhd"
        symbol = "IBM.US"
      """
    And the store holds "stock_feb.csv" as eodhd/IBM.US declared etf
    And the splits file of "IBM.US" stamped "2024-03-01T07:00:00Z" with no splits
    When status runs at "2024-03-04T09:00:00Z"
    Then the status exit code is 0
    And the status totals are 0 alerts and 1 warnings
    And report 1 has exactly the keys:
      """
      asset
      exchange
      symbol
      alerts
      warnings
      notes
      declared_class_check
      last_session
      missed_sessions
      rows
      """
    And report 1 has the fields:
      | key             | value        |
      | last_session    | "2024-03-01" |
      | missed_sessions | 0            |
      | rows            | 22           |

  @JDL-116 @JDL-115 @JDL-108 @JDL-117
  Scenario Outline: Weekday staleness counts the sessions strictly between the last bar and today
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
    When status runs at "<now>" with options "staleness_k=<k>"
    Then the status exit code is <rc>
    And report 1 has the fields:
      | key             | value        |
      | last_session    | "2024-03-01" |
      | missed_sessions | <missed>     |
    And report 1 has alerts:
      """
      <alert>
      """
    And report 1 has notes:
      """
      declared class: no vendor classification recorded - run tools/record_classifications.py
      <note>
      """

    Examples:
      | now                  | k | missed | rc | alert | note |
      | 2024-03-01T20:00:00Z | 2 | 0      | 0  |       | today-dated bar stored (pre-close serve? the next tail-refresh heals it) |
      | 2024-03-04T09:00:00Z | 2 | 0      | 0  |       | |
      | 2024-03-05T09:00:00Z | 2 | 1      | 0  |       | |
      | 2024-03-06T09:00:00Z | 2 | 2      | 1  | stale: 2 expected session(s) missing since 2024-03-01 (multi-day holidays can trip this - verify before acting) | |
      | 2024-03-05T09:00:00Z | 1 | 1      | 1  | stale: 1 expected session(s) missing since 2024-03-01 (multi-day holidays can trip this - verify before acting) | |

  @JDL-116 @JDL-115
  Scenario Outline: Crypto staleness counts every calendar day
    Given the universe file:
      """
      [[asset]]
      name = "CRY"
      asset_class = "crypto"

        [[asset.source]]
        provider = "eodhd"
        symbol = "CRY-USD.CC"
      """
    And the store holds "crypto_feb.csv" as eodhd/CRY-USD.CC declared crypto
    When status runs at "<now>"
    Then the status exit code is <rc>
    And report 1 has the fields:
      | key             | value    |
      | missed_sessions | <missed> |

    Examples:
      | now                  | missed | rc |
      | 2024-03-03T00:30:00Z | 1      | 0  |
      | 2024-03-04T00:30:00Z | 2      | 1  |

  @JDL-118 @JDL-119
  Scenario Outline: Zero-volume rows are noted, with the longest contiguous run when it exceeds one row
    Given the universe file:
      """
      [[asset]]
      name = "ZV"
      asset_class = "crypto"

        [[asset.source]]
        provider = "eodhd"
        symbol = "ZV-USD.CC"
      """
    And the store holds "<csv>" as eodhd/ZV-USD.CC declared crypto
    When status runs at "2024-01-21T00:30:00Z"
    Then the status exit code is 0
    And report 1 has notes:
      """
      declared class: no vendor classification recorded - run tools/record_classifications.py
      <note>
      """

    Examples:
      | csv             | note |
      | zero_single.csv | 2 zero-volume row(s), dropped at the seam by pinned policy |
      | zero_runs.csv   | 8 zero-volume row(s), dropped at the seam by pinned policy - largest contiguous run 3, 2024-01-07..2024-01-09 |

  @JDL-120 @JDL-121 @JDL-115
  Scenario Outline: The largest post-seam gap is counted in expected sessions and noted at the threshold
    Given the universe file:
      """
      [[asset]]
      name = "GAP"
      asset_class = "<class>"

        [[asset.source]]
        provider = "eodhd"
        symbol = "GAP.US"
      """
    And the store holds "gap_stock.csv" as eodhd/GAP.US declared stock
    And the splits file of "GAP.US" stamped "2024-03-01T07:00:00Z" with no splits
    When status runs at "2024-03-01T09:00:00Z" with options "gap_k=<k>"
    Then the status exit code is 0
    And report 1 has notes:
      """
      declared class: no vendor classification recorded - run tools/record_classifications.py
      1 zero-volume row(s), dropped at the seam by pinned policy
      <gap note>
      """

    Examples:
      | class  | k | gap note |
      | stock  | 5 | post-seam continuity: 5 expected session(s) absent between 2024-02-09 and 2024-02-19 - the seam's output splices across this hole; verify the provider era before modelling (docs/DATA_CONTRACT.md §1) |
      | stock  | 6 |          |
      | crypto | 9 | post-seam continuity: 9 expected session(s) absent between 2024-02-09 and 2024-02-19 - the seam's output splices across this hole; verify the provider era before modelling (docs/DATA_CONTRACT.md §1) |

  @JDL-122 @JDL-123
  Scenario Outline: Price resolution is measured over traded sessions and noted past its knobs
    Given the universe file:
      """
      [[asset]]
      name = "RES"
      asset_class = "crypto"

        [[asset.source]]
        provider = "eodhd"
        symbol = "RES-USD.CC"
      """
    And the store holds "<csv>" as eodhd/RES-USD.CC declared crypto
    When status runs at "2024-06-01T00:30:00Z"
    Then report 1 has the fields:
      | key        | value        |
      | resolution | <resolution> |
    And report 1 has notes:
      """
      declared class: no vendor classification recorded - run tools/record_classifications.py
      <note>
      """

    Examples:
      | csv            | resolution | note |
      | res_at.csv     | {"sessions": 100, "distinct": 20, "min_tick": 0.0056179775280898875, "flat_share": 0.0} | |
      | res_coarse.csv | {"sessions": 100, "distinct": 19, "min_tick": 0.005649717514124294, "flat_share": 0.0} | coarse price resolution: 19 distinct close(s) in 100 traded session(s), min tick 0.5650%, 0.0% flat - the provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8) |
      | flat_at.csv    | {"sessions": 81, "distinct": 61, "min_tick": 0.0045662100456621, "flat_share": 0.25} | |
      | flat_over.csv  | {"sessions": 81, "distinct": 60, "min_tick": 0.0045871559633027525, "flat_share": 0.2625} | coarse price resolution: 60 distinct close(s) in 81 traded session(s), min tick 0.4587%, 26.2% flat - the provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8) |

  @JDL-122
  Scenario: Resolution needs at least 60 traded sessions in its window
    Given the universe file:
      """
      [[asset]]
      name = "RES"
      asset_class = "crypto"

        [[asset.source]]
        provider = "eodhd"
        symbol = "RES-USD.CC"
      """
    And the store holds "res_at.csv" as eodhd/RES-USD.CC declared crypto
    When status runs at "2024-06-01T00:30:00Z" with options "resolution_window=59"
    Then report 1 lacks the field "resolution"
    When status runs at "2024-06-01T00:30:00Z" with options "resolution_window=60"
    Then report 1 has the fields:
      | key        | value |
      | resolution | {"sessions": 60, "distinct": 20, "min_tick": 0.0056179775280898875, "flat_share": 0.0} |
    When status runs at "2024-06-01T00:30:00Z" with options "resolution_window=100, resolution_k=0.21"
    Then report 1 has notes:
      """
      declared class: no vendor classification recorded - run tools/record_classifications.py
      coarse price resolution: 20 distinct close(s) in 100 traded session(s), min tick 0.5618%, 0.0% flat - the provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8)
      """

  @JDL-122 @JDL-123
  Scenario: Resolution reads the provider's own print, not the split-adjusted close
    Given the universe file:
      """
      [[asset]]
      name = "RES"
      asset_class = "stock"

        [[asset.source]]
        provider = "eodhd"
        symbol = "RES.US"
        start = 2024-01-01
      """
    And the "eodhd" provider replays "res"
    And sync ran at "2024-04-08T12:00:00Z"
    When status runs at "2024-04-08T12:00:00Z"
    Then report 1 has the fields:
      | key        | value |
      | resolution | {"sessions": 70, "distinct": 8, "min_tick": 0.0049504950495049506, "flat_share": 0.0} |
    And report 1 has notes:
      """
      declared class: no vendor classification recorded - run tools/record_classifications.py
      coarse price resolution: 8 distinct close(s) in 70 traded session(s), min tick 0.4950%, 0.0% flat - the provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8)
      """

  @JDL-124
  Scenario Outline: Phantom-split jumps are scanned over the newest window with a strict threshold
    Given the universe file:
      """
      [[asset]]
      name = "JMP"
      asset_class = "crypto"

        [[asset.source]]
        provider = "eodhd"
        symbol = "JMP-USD.CC"
      """
    And the store holds "jumps.csv" as eodhd/JMP-USD.CC declared crypto
    When status runs at "2024-05-11T00:30:00Z" with options "<options>"
    Then the status exit code is 1
    And report 1 has alerts:
      """
      <alerts>
      """

    Examples:
      | options                       | alerts |
      | window=10                     | phantom-split-shaped jump +66.7% on 2024-05-03 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)\nphantom-split-shaped jump +45.0% on 2024-05-08 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |
      | window=11                     | phantom-split-shaped jump +50.0% on 2024-04-26 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)\nphantom-split-shaped jump +66.7% on 2024-05-03 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)\nphantom-split-shaped jump +45.0% on 2024-05-08 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |
      | window=10, jump_threshold=0.5 | phantom-split-shaped jump +66.7% on 2024-05-03 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |

  @JDL-124 @JDL-125 @JDL-086
  Scenario Outline: A same-day split excuses a jump only where splits are read
    Given the universe file:
      """
      [[asset]]
      name = "JMP"
      asset_class = "<class>"

        [[asset.source]]
        provider = "eodhd"
        symbol = "JMP.XX"
      """
    And the store holds "jumps.csv" as eodhd/JMP.XX declared stock
    And the splits file of "JMP.XX" stamped "2024-05-10T07:00:00Z" with splits:
      | date       | split | ratio |
      | 2024-05-03 | 5/3   | 1.6666666666666667 |
    When status runs at "2024-05-11T00:30:00Z"
    Then report 1 has alerts:
      """
      <alerts>
      """

    Examples:
      | class  | alerts |
      | stock  | phantom-split-shaped jump +45.0% on 2024-05-08 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |
      | crypto | phantom-split-shaped jump +66.7% on 2024-05-03 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)\nphantom-split-shaped jump +45.0% on 2024-05-08 with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2) |

  @JDL-125 @JDL-115
  Scenario Outline: Corporate-actions freshness counts the refresh sessions missed since the stamp
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
    And the splits file of "FRS.US" stamped "<stamp>" with no splits
    When status runs at "<now>" with options "staleness_k=10"
    Then report 1 has alerts:
      """
      <alert>
      """

    Examples:
      | stamp                | now                  | alert |
      | 2024-03-01T07:00:00Z | 2024-03-04T00:30:00Z | |
      | 2024-03-01T07:00:00Z | 2024-03-05T00:30:00Z | |
      | 2024-03-01T07:00:00Z | 2024-03-06T00:30:00Z | corporate actions stale: 2 refresh session(s) missed since 2024-03-01 - run jef-data sync |
      | 2024-03-05T23:59:59Z | 2024-03-06T00:30:00Z | |

  @JDL-125
  Scenario: An actions-eligible series that never synced its actions alerts at any threshold
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
    When status runs at "2024-03-04T00:30:00Z"
    Then the status exit code is 1
    And report 1 has alerts:
      """
      corporate actions stale: never synced - run jef-data sync
      """

  @JDL-128 @JDL-129 @JDL-126 @JDL-131 @JDL-107
  Scenario Outline: The cross-venue close spread warns strictly above its threshold, or alerts when promoted
    Given the universe fixture "pair.toml"
    And the "eodhd" provider replays "pair/<set>"
    And the "binance" provider replays "pair/<set>"
    And sync ran at "2024-01-21T06:00:00Z"
    When status runs at "2024-01-21T06:00:00Z" with options "<options>"
    Then the status exit code is <rc>
    And there are 2 reports and 1 pairs
    And the status totals are <alerts> alerts and <warnings> warnings
    And pair 1 is:
      """
      {"asset": "PAIR", "kind": "cross_venue", "a": "eodhd/PAIR-USD.CC", "b": "binance/PAIRUSDT",
       "common_session": "2024-01-20", "spread": <spread>, "threshold": <threshold>,
       "alerts": [<alert>], "warnings": [<warning>],
       "notes": ["close spread <pct> on 2024-01-20 (eodhd/PAIR-USD.CC 100.25 vs binance/PAIRUSDT <b>)"]}
      """

    Examples:
      | set   | options                                      | rc | alerts | warnings | spread               | threshold | pct     | b     | alert | warning |
      | at    | spread_threshold=0.005                       | 0  | 0      | 0        | 0.005                | 0.005     | 0.5000% | 99.75 |       |         |
      | above | spread_threshold=0.005                       | 0  | 0      | 1        | 0.005501375343835931 | 0.005     | 0.5501% | 99.7  |       | "cross-venue close spread 0.5501% on 2024-01-20 exceeds 0.5000% (eodhd/PAIR-USD.CC 100.25 vs binance/PAIRUSDT 99.7) - feed problem or venue distress; verify before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)" |
      | above | spread_threshold=0.005, spread_alerts=true   | 1  | 1      | 0        | 0.005501375343835931 | 0.005     | 0.5501% | 99.7  | "cross-venue close spread 0.5501% on 2024-01-20 exceeds 0.5000% (eodhd/PAIR-USD.CC 100.25 vs binance/PAIRUSDT 99.7) - feed problem or venue distress; verify before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)" | |
      | above | spread_threshold=0.0056                      | 0  | 0      | 0        | 0.005501375343835931 | 0.0056    | 0.5501% | 99.7  |       |         |

  @JDL-128 @JDL-127
  Scenario Outline: The spread needs a common session inside both newest windows and a non-zero mid
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
    And the store holds "<a>" as eodhd/DUO-USD.CC declared crypto
    And the store holds "<b>" as binance/DUOUSDT declared crypto
    When status runs at "2024-06-01T00:30:00Z" with options "window=<window>"
    Then pair 1 is:
      """
      {"asset": "DUO", "kind": "cross_venue", "a": "eodhd/DUO-USD.CC", "b": "binance/DUOUSDT",
       "common_session": <session>, "spread": <spread>, "threshold": 0.005, "alerts": [], "warnings": [],
       "notes": ["<note>"]}
      """

    Examples:
      | a         | b         | window | session      | spread | note |
      | new_a.csv | old_b.csv | 10     | null         | null   | no common session in the newest 10 - spread not measured (see the staleness check) |
      | new_a.csv | old_b.csv | 13     | "2023-01-12" | 0.0    | close spread 0.0000% on 2023-01-12 (eodhd/DUO-USD.CC 10 vs binance/DUOUSDT 10) |
      | mid_a.csv | mid_b.csv | 10     | null         | null   | zero mid price on 2024-01-05 - spread not measured |

  @JDL-132 @JDL-145 @JDL-131
  Scenario: The status table of a filled, a mis-declared and a never-filled source
    Given the universe file:
      """
      [[asset]]
      name = "FUT"
      asset_class = "crypto"

        [[asset.source]]
        provider = "eodhd"
        symbol = "FUT-USD.CC"

      [[asset]]
      name = "IBM"
      asset_class = "bond_etf"

        [[asset.source]]
        provider = "eodhd"
        symbol = "IBM.US"

      [[asset]]
      name = "EMPTY"
      asset_class = "crypto"

        [[asset.source]]
        provider = "binance"
        symbol = "EMPTYUSDT"
      """
    And the store holds "future_crypto.csv" as eodhd/FUT-USD.CC declared crypto
    And the store holds "future_stock.csv" as eodhd/IBM.US declared etf
    And the splits file of "IBM.US" stamped "2099-02-01T00:00:00Z" with no splits
    When I run "jef-data status --universe universe.toml --store {store}"
    Then the exit code is 1
    And stdout is:
      """
      ok       FUT eodhd/FUT-USD.CC: last 2099-03-11, 0 missed, 70 row(s)
              res   50 distinct / 69 traded, min tick 0.5051%, 0.00% flat
              note  declared class: no vendor classification recorded - run tools/record_classifications.py
              note  1 zero-volume row(s), dropped at the seam by pinned policy
      WARN     IBM eodhd/IBM.US: last 2099-01-30, 0 missed, 22 row(s)
              WARN  declared class: declared asset_type 'etf' but the vendor says 'Common Stock' (-> 'stock'), recorded 2026-08-30 for eodhd/IBM.US - check the asset_class in universe.toml against docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2
      ALERT  EMPTY binance/EMPTYUSDT: last -, - missed, 0 row(s)
              ALERT never filled - no stored rows (jef-data sync first)
      3 source(s), 1 alert(s), 1 warning(s)
      """

  @JDL-132 @JDL-145 @JDL-107
  Scenario: The status table of a pair and of a CSV-only selection
    Given the universe fixture "csv_leg.toml"
    When I run "jef-data status --universe universe.toml --store {store} --provider yahoo-csv"
    Then the exit code is 0
    And stdout is:
      """
      0 source(s), 0 alert(s)
      """
    Given the universe fixture "pair.toml"
    When I run "jef-data status --universe universe.toml --store {store} --asset PAIR"
    Then the exit code is 1
    And stdout is:
      """
      ALERT   PAIR eodhd/PAIR-USD.CC: last -, - missed, 0 row(s)
              ALERT never filled - no stored rows (jef-data sync first)
              note  declared class: no vendor classification recorded - run tools/record_classifications.py
      ALERT   PAIR binance/PAIRUSDT: last -, - missed, 0 row(s)
              ALERT never filled - no stored rows (jef-data sync first)
      ok      PAIR cross-venue eodhd/PAIR-USD.CC vs binance/PAIRUSDT
              note  eodhd/PAIR-USD.CC has no stored rows - spread not measured
      2 source(s), 1 venue pair(s), 2 alert(s)
      """

  @JDL-130 @JDL-145 @JDL-089
  Scenario: The status JSON envelope on stdout, with the universe's default store
    Given the universe fixture "csv_leg.toml"
    When I run "jef-data status --universe universe.toml --json"
    Then the exit code is 1
    And the JSON on stdout is printed with 1-space indentation in document order
    And the JSON on stdout is:
      """
      {"schema_version": 1, "store": "dstore",
       "reports": [{"asset": "SMALL", "exchange": "eodhd", "symbol": "SMALL.US",
                    "alerts": ["never filled - no stored rows (jef-data sync first)"], "warnings": [],
                    "notes": ["declared class: no vendor classification recorded - run tools/record_classifications.py"],
                    "declared_class_check": "no_evidence"}],
       "pairs": [], "alerts_total": 1, "warnings_total": 0}
      """
