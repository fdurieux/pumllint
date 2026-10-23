# Collectors: endpoints, parameters, pagination, retries, bars

Requirements: JDL-023 … JDL-039. Recorded-fixture
identity: fixtures.md.

## 1. Common plumbing (both collectors)

* **Transport**: `request(method, url, params) -> (status: int, text: str)`,
  `close()`. Live: a `requests` session, timeout 30 s; connection errors and
  timeouts become a retryable TransportConnectionError (token redacted).
* **Rate limiting** (live traffic; disabled in the harness): each collector
  owns a limiter allowing 1000 requests per sliding 60 s window — when full,
  sleep `60 - (now - oldest)` seconds, then drop expired entries — and 100000
  requests per UTC day; the next request after the daily budget raises
  DailyBudgetExhausted `daily API budget of 100000 spent ({UTC date}); the
  per-minute window cannot lend quota across days`. The limiter is acquired
  before every attempt, retries included.
* **Retry policy** (`get_json`): up to 5 attempts (`max_retries = 4`).
  | outcome of an attempt | action |
  |---|---|
  | connection error / timeout | retry; after the 5th: CollectorError `{label}: network failure after 5 attempts: {error}` |
  | HTTP 429 or ≥ 500 | retry; after the 5th: CollectorError `{label}: HTTP {status} after 5 attempts` |
  | other non-200 | CollectorError `{label}: HTTP {status}: {text[:200]}` (no retry) |
  | 200, body not JSON | CollectorError `{label}: response is not JSON: {text[:200]}` |
  | 200, JSON | return the parsed body |
  Backoff before retry k (k = 0..3): sleep `2.0 × 2**k` s (2, 4, 8, 16).
* **Secrets**: the token travels only as the `api_token` query parameter;
  it is excluded from fixture keys and replaced by `***` in every error text.
* **Labels**: `eod {SYM}`, `splits {SYM}`, `div {SYM}`, `klines {symbol}`.

## 2. EODHD

* Base URL: `https://eodhd.com/api` (trailing `/` stripped; `sync --base-url`
  and the `--base-url` flags of `load`/`sync-actions` override it).
* Key: constructor argument, else environment `EODHD_API_KEY`; missing or
  empty → ValueError `EODHD API key required: pass api_key= or set
  EODHD_API_KEY` at construction.
* Every request carries `api_token={key}` and `fmt=json`.

| call | path | extra params |
|---|---|---|
| bars | `/eod/{SYM}` | `period=d`, `order=a`, `from={start}` if any, `to={end}` if any |
| splits | `/splits/{SYM}` | none (the sync never passes from/to) |
| dividends | `/div/{SYM}` | none |
| search (not used by any command) | `/search/{query}` | `exchange` |

* **Symbol normalisation** (applied to SYM before every call):
  dotted → unchanged; `BASE/QUOTE` → `BASEQUOTE.FOREX` if both fiat, else
  `BASE-QUOTE.CC` if QUOTE is a crypto quote (USD USDT EUR BTC ETH BUSD USDC),
  else CollectorError `cannot infer exchange for pair symbol '{s}'`; bare →
  `{s}.US`. Fiat set: USD EUR GBP JPY CHF AUD NZD CAD SEK NOK DKK PLN CZK HUF
  TRY ZAR MXN SGD HKD CNY INR BRL KRW RUB. (Universe eodhd symbols always
  contain a dot, so inside `sync` this is the identity.)
* **Bars** (`/eod/` response, a JSON list of objects with `date, open, high,
  low, close, adjusted_close, volume`): non-list → CollectorError `eod {SYM}:
  expected a JSON list`. Drop rows whose `close` is missing, null, 0 or
  negative (a non-numeric close raises ValueError). Keep the first row of each
  `date` string; return rows unmodified, sorted ascending by `date` text.
  Prices are raw (unadjusted); `volume` is served split-adjusted
  (volume basis `split_adjusted`); `adjusted_close` is splits+dividends.
* **Splits**: list of `{date, split}` → split events (adjustment.md §2),
  sorted ascending by date (stable).
* **Dividends**: list of objects, stored verbatim, sorted by `date` text
  (missing → `""`).

## 3. Binance

* Endpoint: `GET https://api.binance.com/api/v3/klines`; no key; volume basis
  `raw`; page limit `limit = 1000` (exposed as the collector attribute
  `limit`, which the sync's page-limit check reads).
* Params per page: `symbol` (verbatim), `interval=1d`, `limit=1000`,
  `startTime={cursor}` (omitted on a first page without a start),
  `endTime={end_ms}` (omitted without an end).
* `start_ms` = Unix ms of the start date at 00:00 UTC;
  `end_ms` = Unix ms of the end date at 00:00 UTC + 86 400 000 − 1
  (e.g. end 2024-01-20 → `1705795199999`).
* **Pagination**: cursor₀ = start_ms (or none). After each page: empty →
  stop; else `last_open = int(rows[-1][0])`; stop when `len(rows) < 1000` or
  (end_ms given and `last_open + 86400000 > end_ms`); else cursor =
  `last_open + 86400000`. A 101st page is refused: CollectorError
  `pagination exceeded 100 pages - refusing to truncate silently; raise
  max_pages if the range is real`. Non-list page → CollectorError
  `klines {symbol}: expected a JSON list`.
* **Bars**: kline row `[openTime ms, open, high, low, close, volume, ...]`
  (numbers or numeric strings; elements after index 5 are ignored) →
  `{date: UTC date of openTime as YYYY-MM-DD, open, high, low, close: floats,
  adjusted_close: close, volume: float}`; drop close ≤ 0; first bar per date
  wins; sorted ascending by date. Volume is in base-asset units.

## 4. Bar record handed to the store

Both collectors return a list of dicts with at least `date` (`YYYY-MM-DD`),
`open`, `high`, `low`, `close`, `volume` and optionally `adjusted_close`,
ascending, one per date. The store reads exactly those keys (store.md §4).
