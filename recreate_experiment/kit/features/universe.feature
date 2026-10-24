Feature: The declarative universe - grammar, normalisation and refusals
  The universe file decides which assets and sources exist, how each source
  maps to a store series, and which declared class drives basis and calendar.
  It is parsed strictly: the first violation is a refusal.

  @JDL-001 @JDL-136 @JDL-004
  Scenario: The packaged universe lists its six pilot assets
    When I run "jef-data universe"
    Then the exit code is 0
    And stdout is:
      """
      AAPL (stock, USD, threshold -0.05)
        eodhd: AAPL.US
        yahoo-csv: experiments/AAPL.csv - committed; the goldens' ancestry (counter-720 gate)
      BTC (crypto, USD, threshold -0.05)
        eodhd: BTC-USD.CC
        binance: BTCUSDT - redundancy cross-check (D0 decision 3); base-asset volume
        yahoo-csv: experiments/BTC-USD_feb2024.csv - committed; drives the offline store-path pilot run
      TLT (bond_etf, USD, threshold -0.05)
        eodhd: TLT.US - no committed CSV - first fill needs the owner's key
      NVDA (stock, USD, threshold -0.05)
        eodhd: NVDA.US - no committed CSV - first fill needs the owner's key
      TSLA (stock, USD, threshold -0.05)
        eodhd: TSLA.US - no committed CSV - first fill needs the owner's key
      IBM (stock, USD, threshold -0.05)
        eodhd: IBM.US - no committed CSV - first fill needs the owner's key
      """

  @JDL-002 @JDL-003 @JDL-004 @JDL-005 @JDL-006 @JDL-007 @JDL-008 @JDL-009 @JDL-011
  Scenario: Defaults, dates and the class map normalise into one shape
    Given the universe file:
      """
      [defaults]
      currency = "EUR"

      [[asset]]
      name = "BOND"
      asset_class = "bond_etf"
      threshold = -1

        [[asset.source]]
        provider = "eodhd"
        symbol = "BOND.XETRA"
        start = "20240102"
        end = 2024-03-28
        note = "listed in Frankfurt"

        [[asset.source]]
        provider = "yahoo-csv"
        path = "snapshots/bond.csv"
        symbol = "BOND"
        exchange = "snap"
        modeled = true

      [[asset]]
      name = "COIN"
      asset_class = "crypto"
      currency = "USD"
      enabled = false

        [[asset.source]]
        provider = "binance"
        symbol = "COINUSDT"
        start = 2024-01-01T10:00:00Z
      """
    When the universe is loaded
    Then the loaded universe is:
      """
      {"defaults": {"store": "data", "currency": "EUR"},
       "assets": [
        {"name": "BOND", "asset_class": "bond_etf", "asset_type": "etf", "currency": "EUR",
         "threshold": -1.0, "enabled": true,
         "sources": [
          {"provider": "eodhd", "kind": "eod", "enabled": true, "modeled": false,
           "exchange": "eodhd", "symbol": "BOND.XETRA", "currency": "EUR",
           "note": "listed in Frankfurt", "start": "2024-01-02", "end": "2024-03-28"},
          {"provider": "yahoo-csv", "kind": "eod", "enabled": true, "modeled": true,
           "exchange": "snap", "symbol": "BOND", "currency": "EUR",
           "path": "snapshots/bond.csv"}]},
        {"name": "COIN", "asset_class": "crypto", "asset_type": "crypto", "currency": "USD",
         "threshold": -0.05, "enabled": false,
         "sources": [
          {"provider": "binance", "kind": "eod", "enabled": true, "modeled": false,
           "exchange": "binance", "symbol": "COINUSDT", "currency": "USD",
           "start": "2024-01-01T10:00:00+00:00", "end": null}]}]}
      """

  @JDL-136 @JDL-010
  Scenario: The listing marks paused assets, switched-off sources and notes
    Given the universe fixture "paused.toml"
    When I run "jef-data universe --universe universe.toml"
    Then the exit code is 0
    And stdout is:
      """
      SPLT (stock, USD, threshold -0.05)
        eodhd: SPLT.US
        yahoo-csv: snap/splt.csv [disabled] - an old snapshot
      GONE (stock, USD, threshold -0.05) [disabled]
        eodhd: GONE.US
        binance: GONEUSDT
      """

  @JDL-012 @JDL-013 @JDL-014 @JDL-015 @JDL-016 @JDL-017 @JDL-018 @JDL-019 @JDL-020 @JDL-021 @JDL-134
  Scenario Outline: A malformed universe is refused with its first violation
    Given the universe fixture "bad/<file>.toml"
    When I run "jef-data universe --universe universe.toml"
    Then the exit code is 1
    And stdout is empty
    And stderr is:
      """
      universe: <message>
      """

    Examples:
      | file | message |
      | toml_syntax | universe.toml: not valid TOML: Expected '=' after a key in a key/value pair (at line 1, column 6) |
      | top_key | universe.toml: unknown key(s) ['foo']; allowed: ['asset', 'defaults'] |
      | defaults_table | universe.toml: [defaults] must be a table |
      | defaults_key | universe.toml [defaults]: unknown key(s) ['bogus']; allowed: ['currency', 'store'] |
      | defaults_store | [defaults]: store must be a non-empty string, got '' |
      | no_assets | universe.toml: no [[asset]] entries |
      | asset_table | asset #1: must be a table |
      | asset_key | asset #1: unknown key(s) ['colour']; allowed: ['asset_class', 'currency', 'enabled', 'name', 'source', 'threshold'] |
      | asset_name | asset #1: missing required key 'name' |
      | asset_class_missing | asset 'X': missing required key 'asset_class' |
      | asset_class_bad | asset 'X': unknown asset_class 'forex'; allowed: ['bond_etf', 'crypto', 'stock'] |
      | threshold | asset 'X': threshold must be a number (documentation only), got True |
      | no_source | asset 'X': needs at least one [[asset.source]] |
      | enabled | asset 'X': enabled must be a boolean, got 'yes' |
      | source_table | asset 'X' source #1: must be a table |
      | source_key | asset 'X' source #1: unknown key(s) ['colour']; allowed: ['enabled', 'end', 'exchange', 'kind', 'modeled', 'note', 'path', 'provider', 'start', 'symbol'] |
      | provider_bad | asset 'X' source #1: unknown provider 'yahoo'; allowed: ['eodhd', 'binance', 'yahoo-csv'] |
      | kind | asset 'X' source #1: kind 'intraday' is not supported - only ['eod']; a non-EOD load is a new data contract, not a config value |
      | bare_ticker | asset 'X' source #1: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, BTC-USD.CC), got 'X' - bare tickers would blur store coordinates and the crypto/raw basis split |
      | modeled_type | asset 'X' source #1: modeled must be a boolean, got 'yes' |
      | csv_path | asset 'X' source #1: missing required key 'path' |
      | csv_window | asset 'X' source #1: start/end apply to collector sources only; a CSV import is whole-file |
      | collector_path | asset 'X' source #1: path applies to yahoo-csv sources only |
      | bad_date | asset 'X' source #1: start must be an ISO date (YYYY-MM-DD), got '2024-13-01' |
      | inverted | asset 'X' source #1: start 2024-02-01 is after end 2024-01-01 |
      | modeled_disabled | asset 'X': a modeled source must be enabled |
      | two_modeled | asset 'X': exactly one enabled source may be modeled = true, got 2 |
      | none_modeled | asset 'X': 2 enabled sources but none marked modeled = true - the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7) |
      | all_off | asset 'X': enabled but has no enabled source - nothing would feed the binning; to pause the asset, set enabled = false on the asset itself |
      | dupe_name | universe.toml: duplicate asset name(s) ['X'] |
      | dupe_coord | universe.toml: store series eodhd/X.US is claimed by both 'X' and 'Y' - two assets may never write the same partition |
      | first_wins | asset #1: unknown key(s) ['colour']; allowed: ['asset_class', 'currency', 'enabled', 'name', 'source', 'threshold'] |

  @JDL-022 @JDL-134
  Scenario: A universe path that does not exist is an unwrapped error
    When I run "jef-data universe --universe nowhere.toml"
    Then the exit code is 1
    And stdout is empty
    And stderr ends with the line "FileNotFoundError: [Errno 2] No such file or directory: 'nowhere.toml'"
