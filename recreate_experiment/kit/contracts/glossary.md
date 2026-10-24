# Glossary (revision 2026-10-23 (wave 2))

One definition per term, from the code's own meaning; the contracts and the
requirements use the terms in these senses and nowhere redefine them.
`harness/glossary_check.py` lists the terms that recur across requirements
without a row here. Where a term is also a stored column or a config key,
the identifier is given in code font.

| term | meaning | where it is specified |
|---|---|---|
| store | The on-disk Parquet market-data store plus the corporate-actions files under one root directory (`--store`, default the universe's `defaults.store`). | store.md |
| store coordinate | The pair `exchange tag / symbol` that names one series; two assets may never claim the same one. | store.md §1, universe.toml.md |
| exchange tag | The first half of a store coordinate: the provider's tag (`eodhd`, `binance`) or the declared `exchange` of a yahoo-csv source (default `yahoo`). | store.md §1 |
| series | Every stored row of one store coordinate, read back sorted by `timestamp` with later duplicates dropped; "absent" or "never filled" when it has no year file. | store.md §5 |
| year file | `market_data/exchange=E/symbol=S/year=YYYY/data.parquet`, the unit a write rewrites. | store.md §1, §6 |
| lock | The exclusive advisory lock on a series' `.lock` file every read-modify-write holds, waited for up to 300 s. | store.md §6, JDL-058 |
| universe | The TOML declaration of assets and their sources (`--universe`, default the packaged file), loaded and normalised before any leg runs. | universe.toml.md |
| asset | One `[[asset]]` entry: a name, a declared `asset_class`, `enabled`, and one or more sources. | universe.toml.md |
| source | One `[[asset.source]]` entry: a provider, a symbol (or a path for yahoo-csv), optional `start`/`end`, `enabled`, `modeled`. | universe.toml.md |
| enabled | The `enabled` flag of an asset or source; a disabled asset is "paused", a disabled source is "switched off"; neither yields a leg. | universe.toml.md, JDL-084 |
| modeled | The source flag marking the one feed the binning reads; exactly one enabled source per asset with several enabled sources. | universe.toml.md, JDL-020 |
| leg | One (asset, source) pair the selection produced: the unit the sync runs, logs and reports, in universe order. | leg.md, sync.feature |
| collector | The provider client that fetches bars (and, for EODHD, splits and dividends) through a transport: `eodhd`, `binance`. A yahoo-csv leg has none. | collectors.md |
| transport | The HTTP layer under a collector: `request(method, url, params) -> (status, text)`; live, or a replay of recorded fixtures. | collectors.md, fixtures.md |
| fixture | A recorded request/response file the replay transport serves instead of the network; `fixtures/http/<set>/`. | fixtures.md |
| replay | Running a collector over recorded fixtures; a request with no fixture is a CollectorError. | fixtures.md §5 |
| declared asset_type | The store's instrument type derived from the asset's `asset_class` (`stock -> stock`, `bond_etf -> etf`, `crypto -> crypto`), or `--asset-type` for `load`; decides basis, actions eligibility and the end-guard, never the symbol suffix. | adjustment.md §1, JDL-086 |
| basis | Short for price_basis, below. | adjustment.md §1 |
| price_basis | How a series' prices are stored: `raw` (as served, split-adjusted on read-back by the stored splits) or `split_adjusted` (already adjusted at the provider; never re-adjusted). | adjustment.md §1 |
| volume basis | Whether the collector serves volume raw or split-adjusted; decides whether `volume_raw` is the served volume or the served volume divided by the cumulative split factor. | adjustment.md §2 |
| raw columns | `open_raw, high_raw, low_raw, close_raw, volume_raw` and `adjusted_close`: the as-served values, the only columns a reconcile compares and the only source of the main OHLCV. | store.md §4, adjustment.md §4 |
| cumulative split factor | `cumulative_split_factor`: the product of the ratios of the stored splits dated strictly after a row; 1.0 on and after the last split. | adjustment.md §3 |
| adjustment_factor | `adjusted_close / close_raw` per row, as stored. | adjustment.md §4 |
| adjusted_close | The provider's own adjusted close, stored as served and never recomputed. | store.md §4 |
| split event | One stored split: `date`, `split` (the provider's string, e.g. `7/1`), `ratio`. | store.md §8, JDL-033 |
| dividend | One stored dividend entry, the provider's object verbatim; stored, never applied. | store.md §8 |
| corporate actions | The splits and dividends of a symbol, under `corporate_actions/{splits,dividends}/`, with their freshness stamp. | store.md §8 |
| stamp | `last_updated` of the splits file: the real wall-clock UTC time of the last refresh; the actions gate and the freshness check read it. | store.md §8, JDL-043, JDL-091 |
| actions-eligible | A leg whose provider is `eodhd` and whose declared asset_type is not `crypto`; only such legs sync and check corporate actions. | JDL-086 |
| actions gate | The once-per-UTC-day decision to refresh an eligible leg's actions: forced, no stamp, or a stamp dated before today. | JDL-091, dmn/actions_gate.dmn |
| run clock | The real current UTC time, or the `now` a harness injects; read once at the start of a run. | JDL-088 |
| today | The UTC calendar date of the run clock, taken once per run and used by the end-guard, the actions gate and the today-dated check. | JDL-088 |
| end-guard | For a leg whose declared asset_type is crypto, the fetch end `today - 1 day`, so the in-progress UTC day is never ingested. | JDL-094 |
| window | A leg's fetch window: start (universe start, open, or the tail) to end (universe end, end-guard, or open). | JDL-093, JDL-094, dmn/sync_window.dmn |
| first fill | The fetch of a leg whose series is absent: from the universe start (or open) to the end. | JDL-093, JDL-105 |
| tail | `--tail N` (default 10): the newest N stored sessions of a filled series; the fetch of such a series starts at the oldest of them. | JDL-093, store.md §5 |
| tail refresh | The sync of a filled collector leg: fetch from the tail's oldest session to the end and reconcile the served rows. | JDL-093, JDL-105 |
| inverted window | A filled series whose fetch start is later than its fetch end: nothing is requested, the leg stays green and says so. | JDL-095 |
| page limit | Binance's klines page size (`limit`); a first fill with no declared start that returns exactly one page is a trailing window and says so. | JDL-036, JDL-096 |
| reconcile | The write of served bars into a filled series: served rows replace stored rows whose raw columns differ, new timestamps are appended, stored rows not served are untouched. | store.md §6, JDL-065 |
| revision | One replaced cell of a reconcile: `{date, column, stored, served}`; counted, echoed (first ten), never a failure. | JDL-067, JDL-103 |
| re-adjust | Re-deriving a raw-basis series' main OHLCV from its raw columns with the stored splits (`adjust`, `load`, raw sync legs). | store.md §6, JDL-069 |
| overwrite | Replacing a whole series with a CSV's rows (`import-csv`, yahoo-csv legs). | store.md §6, JDL-070 |
| normalise | Turning a user-typed symbol into EODHD's canonical `TICKER.EXCHANGE` (`aapl` -> `AAPL.US`, `btc/usd` -> `BTC-USD.CC`). | collectors.md §2 |
| dry run | `sync --dry-run`: the plan, one line per leg from local state only; no collector, no write. | JDL-104, JDL-105 |
| plan | The dry run's per-leg line: the action (`sync-actions + load`, `load`, `import`) and the window. | JDL-105 |
| summary document | The JSON `sync --summary-json` writes after every run that returns: totals, `ok`, one object per leg with its revisions. | sync_summary.schema.json, JDL-106 |
| seam frame | The export projection of a series: `Date, Open, High, Low, Close, Adj Close, Volume`, the frame the binning reads; `export` writes it, `differential` compares it. | seam_frame.md |
| refusal | An error raised to the user: wrapped (`{command}: {message}`, exit 1), a traceback (exit 1), a failed leg (the run exits 1), or a parser error (exit 2). | refusals.md, dmn/refusal_routing.dmn |
| wrapped | A refusal printed as `{command}: {message}` on stderr with exit 1 (universe, selection and `load` declaration errors). | refusals.md |
| traceback | A refusal that escapes a command unhandled: a Python traceback whose last line names the exception and message, exit 1. | refusals.md |
| alert | A status finding that sets exit 1 (`ALERT`); the day stops. | JDL-131, status.feature |
| warning | A status finding reported with `WARN` that never sets the exit code (a class disagreement, a spread breach not promoted). | JDL-132 |
| note | A status observation (`note`) that never sets the exit code: zero volume, a continuity gap, coarse resolution, a measured spread, a class verdict. | JDL-110 |
| verdict | The last line of a differential report (`VERDICT: within tolerance, aligned`, else a finding) that decides its exit code; also the declared-class verdict of a status report. | cli.md differential, JDL-111 |
| expected session | A trading day the series should hold: weekdays for stock and etf, every calendar day for crypto; staleness, continuity and freshness count them. | JDL-115 |
| staleness | The status check counting expected sessions strictly between the last stored session and today; alerts at `--staleness` (default 2). | JDL-116 |
| phantom jump | A one-day |move| above `--jump-threshold` on a date with no stored same-day split: the signature of a missed corporate action. | JDL-124 |
| resolution | The price-resolution measurement over the newest traded closes: sessions, distinct values, minimum tick, flat share. | JDL-122, JDL-123 |
| pair | Two live feeds of one asset compared by status: the cross-venue close spread on their latest common session. | JDL-126 … JDL-129 |
| spread | `|close_a - close_b| / mid` of a pair on its common session; noted always, a warning (or alert) strictly above `--spread-threshold`. | JDL-129 |
| chain | `deploy/daily.sh`: the scheduled sequence sync → status → publish, with its guards and traps. | chain.md |
| stage | One step of the chain (`sync`, `status`, …), each emitting its ledger line red or green. | chain.md |
