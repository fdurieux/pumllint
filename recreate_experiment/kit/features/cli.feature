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
