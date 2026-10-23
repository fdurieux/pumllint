Feature: The command-line surface and its argument errors

  @JDL-133
  Scenario Outline: Argument errors are the parser's, with exit code 2
    When I run "<command>"
    Then the exit code is 2
    And stdout is empty
    And stderr contains "usage: jef-data"
    And stderr contains "error: "

    Examples:
      | command |
      | jef-data |
      | jef-data frobnicate |
      | jef-data import-csv --csv x.csv --symbol X |
      | jef-data load --symbol X.US --asset-type bond_etf |
      | jef-data sync --tail ten |
      | jef-data status --window 1.5 |
      | jef-data status --spread-threshold wide |
      | jef-data validate |
      | jef-data export --symbol X |
      | jef-data differential --b-csv x.csv |

  @JDL-137 @JDL-070
  Scenario: An import into a chosen exchange tag keeps the declared labels
    Given an empty store
    When I run "jef-data import-csv --csv {fixtures}/csv/stock_feb.csv --symbol FEB.US --exchange eodhd --asset-type etf --currency CHF --store {store}"
    Then the exit code is 0
    And stdout is:
      """
      {fixtures}/csv/stock_feb.csv: 22 row(s) -> {store}/market_data/exchange=eodhd/symbol=FEB.US/ (price_basis=split_adjusted)
      """
    And every stored row of eodhd/FEB.US has exchange "eodhd"
    And every stored row of eodhd/FEB.US has symbol "FEB.US"
    And every stored row of eodhd/FEB.US has asset_type "etf"
    And every stored row of eodhd/FEB.US has currency "CHF"
    And every stored row of eodhd/FEB.US has asset_subtype ""

  # revision 2026-10-23 (closing round): the three scenarios below

  @JDL-159 @JDL-138 @JDL-134
  Scenario: Exporting a series the store does not hold ends in pandas' own AttributeError
    Given an empty store
    When I run "jef-data export --symbol GHOST --exchange eodhd --output x.csv --store {store}"
    Then the exit code is 1
    And stdout is empty
    And the last line of stderr is "AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?"
    And the file "x.csv" does not exist
    And the store holds exactly the files:
      """
      """

  @JDL-161 @JDL-160 @JDL-133
  Scenario Outline: Parser errors print the failing parser's usage and one error line
    Given the terminal is 80 columns wide
    When I run "<command>"
    Then the exit code is 2
    And stdout is empty
    And stderr is the lines "<stderr>"

    Examples:
      | command | stderr |
      | jef-data | usage: jef-data [-h]\n                {validate,sync-actions,load,adjust,import-csv,export,differential,sync,status,universe}\n                ...\njef-data: error: the following arguments are required: command |
      | jef-data universe --bogus | usage: jef-data [-h]\n                {validate,sync-actions,load,adjust,import-csv,export,differential,sync,status,universe}\n                ...\njef-data: error: unrecognized arguments: --bogus |
      | jef-data export --symbol X | usage: jef-data export [-h] --symbol SYMBOL [--exchange EXCHANGE] --output\n                       OUTPUT [--store STORE]\njef-data export: error: the following arguments are required: --output |
      | jef-data sync --tail ten | usage: jef-data sync [-h] [--universe UNIVERSE] [--store STORE]\n                     [--asset ASSET] [--provider PROVIDER] [--dry-run]\n                     [--tail TAIL] [--force-actions] [--base-url BASE_URL]\n                     [--summary-json PATH]\njef-data sync: error: argument --tail: invalid int value: 'ten' |
      | jef-data status --window 1.5 | usage: jef-data status [-h] [--universe UNIVERSE] [--store STORE]\n                       [--asset ASSET] [--provider PROVIDER]\n                       [--staleness STALENESS]\n                       [--jump-threshold JUMP_THRESHOLD] [--window WINDOW]\n                       [--resolution-window RESOLUTION_WINDOW]\n                       [--resolution-k RESOLUTION_K] [--flat-k FLAT_K]\n                       [--gap-k GAP_K] [--spread-threshold SPREAD_THRESHOLD]\n                       [--spread-alerts] [--json]\njef-data status: error: argument --window: invalid int value: '1.5' |

  @JDL-162 @JDL-160
  Scenario Outline: Every --help prints its verbatim text and exits 0
    Given the terminal is 80 columns wide
    When I run "<command>"
    Then the exit code is 0
    And stderr is empty
    And stdout is the "<help>" block of contracts/cli_help.md

    Examples:
      | command                        | help                           |
      | jef-data --help                | jef-data --help                |
      | jef-data -h                    | jef-data --help                |
      | jef-data validate --help       | jef-data validate --help       |
      | jef-data sync-actions --help   | jef-data sync-actions --help   |
      | jef-data load --help           | jef-data load --help           |
      | jef-data adjust --help         | jef-data adjust --help         |
      | jef-data import-csv --help     | jef-data import-csv --help     |
      | jef-data export --help         | jef-data export --help         |
      | jef-data differential --help   | jef-data differential --help   |
      | jef-data sync --help           | jef-data sync --help           |
      | jef-data sync -h               | jef-data sync --help           |
      | jef-data status --help         | jef-data status --help         |
      | jef-data universe --help       | jef-data universe --help       |

