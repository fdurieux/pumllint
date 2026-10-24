# The leg dictionary

`select_legs(universe, assets=None, providers=None)` (harness interface)
returns the legs in order (requirement JDL-084): for each enabled asset
in universe order, for each enabled source in source order, skipping assets
outside the asset filter and sources outside the provider filter. Filter
refusals: JDL-085. Each leg is a dict with exactly these keys:

| key | type | derivation |
|---|---|---|
| `asset` | str | the asset's `name` |
| `provider` | str | the source's `provider` |
| `exchange` | str | the source's store partition tag (declared `exchange`, else the provider default `eodhd` / `binance` / `yahoo`) |
| `symbol` | str | the source's `symbol`, verbatim |
| `path` | str or null | the yahoo-csv source's `path`; null for collector sources |
| `asset_type` | str | the asset's declared class mapped: stock→`stock`, crypto→`crypto`, bond_etf→`etf` |
| `currency` | str | the asset's currency (declared, else `defaults.currency`, else `USD`) |
| `start` | str or null | the normalised source `start`; null when undeclared and for yahoo-csv |
| `end` | str or null | the normalised source `end`; null when undeclared and for yahoo-csv |
| `actions` | bool | `provider == "eodhd" and asset_type != "crypto"` (JDL-086) |

Example (the packaged universe, first three legs):

```json
[{"asset": "AAPL", "provider": "eodhd", "exchange": "eodhd", "symbol": "AAPL.US", "path": null, "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": true},
 {"asset": "AAPL", "provider": "yahoo-csv", "exchange": "yahoo", "symbol": "AAPL", "path": "experiments/AAPL.csv", "asset_type": "stock", "currency": "USD", "start": null, "end": null, "actions": false},
 {"asset": "BTC", "provider": "eodhd", "exchange": "eodhd", "symbol": "BTC-USD.CC", "path": null, "asset_type": "crypto", "currency": "USD", "start": null, "end": null, "actions": false}]
```

`run_sync` returns one result per leg: the leg dict plus `ok` (bool), `detail`
(str) and, except on a dry run, `revisions` (list of revision records,
store.md §6).

## Notes for the adapter you ship (HARNESS_INTERFACE.md)

* `load_universe`, `select_legs` and `run_sync` refusals (universe, filter,
  empty selection, `tail` below 1) surface as raised exceptions whose `str()`
  is the bare message of refusals.md (no `sync: ` / `status: ` prefix, which
  only the command line adds).
* `run_sync(..., now=...)`: `now` replaces the run clock (today = its UTC
  date) for the window, the end-guard, the actions gate and the today-dated
  check; it does NOT reach the corporate-actions stamp, which is always the
  real wall clock (requirement JDL-043). `out` receives exactly the lines
  the command prints (requirement JDL-103, JDL-104).
* `status_json(..., now=...)`: `now` replaces the real clock of the status
  checks; the returned document is the parsed `status --json` output and the
  exit code the command would return.
* `actions_state(store, symbol)`: `splits` and `dividends` are the stored
  lists verbatim (store.md §8), `last_updated` the splits file's stamp (null
  when the file is absent).
* `stored_frame` returns the 21 columns of store.md §3 in order (zero rows
  for an absent series); `export_frame` the frame of seam_frame.md §1.
* `import_csv` returns the CSV row count the command reports.
* `make_collector` collectors: rate limiting off and backoff sleeps
  suppressed (fixtures.md §5); everything else is the real collector.
