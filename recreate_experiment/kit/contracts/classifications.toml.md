# Vendor-classification evidence grammar (`classifications.toml`)

The packaged file [`classifications.toml`](classifications.toml) (verbatim
copy; ship it byte-identical inside the rebuilt package) is the only input of
the status command's declared-class check (JDL-113,
JDL-111, JDL-112). There is no flag to replace it.

## Grammar

| key | type | required | constraint |
|---|---|---|---|
| `schema` | integer | yes | must equal `1` |
| `provenance` | string | no | free text, unused |
| `instrument` | array of tables | no (default empty) | must be an array |

No other top-level key is allowed.

`[[instrument]]`:

| key | type | required | notes |
|---|---|---|---|
| `exchange` | string | yes, non-empty | the store partition tag (e.g. `eodhd`) |
| `symbol` | string | yes, non-empty | the store symbol (e.g. `AAPL.US`) |
| `code` | string | yes, non-empty | vendor query code (recorded, never used for lookup) |
| `query_exchange` | string | yes, non-empty | vendor query exchange (recorded) |
| `vendor_type` | string | yes, non-empty | the vendor's instrument type, e.g. `Common Stock`, `ETF`, `Currency` |
| `isin` | string | no | default `""` |
| `name` | string | no | default `""` |
| `last_verified` | TOML date or `YYYY-MM-DD` string | no | rendered into verdict messages as `, recorded {last_verified}` |

Rows are keyed by (`exchange`, `symbol`); a repeated key is an error. Errors
(ClassificationError) would surface as a traceback from `status`; the packaged
file is valid, so a rebuild only needs to parse it correctly.

Parse error texts (for completeness): `{origin}: not valid TOML: {msg}`,
`{origin}: unknown key(s) [...]; allowed: ['instrument', 'provenance', 'schema']`,
`{origin}: schema must be 1, got {value!r}`, `{origin}: [[instrument]] must be a list`,
`instrument #{n}: must be a table`, `instrument #{n}: unknown key(s) [...]; allowed: [...]`,
`{where}: missing required key '{k}'`, `{where}: {k} must be a string, got {v!r}`,
`{where}: {k} must be non-empty`, `{where}: last_verified must be YYYY-MM-DD, got {v!r}`,
`{origin}: duplicate entry for {exchange}/{symbol}`; `origin` is
`packaged classifications.toml`, `where` is `instrument '{symbol}'` once the
symbol is read.

## Mapping used by the verdict

| vendor_type | maps to store asset_type | verdict family |
|---|---|---|
| `Common Stock` | `stock` | agree / disagree |
| `ETF` | `etf` | agree / disagree |
| `Currency` | — | `not_comparable` (shared by .CC crypto and .FOREX) |
| anything else | — | `unmapped` |
| (no row) | — | `no_evidence` |

The packaged rows: `eodhd/AAPL.US` Common Stock, `eodhd/BTC-USD.CC`
Currency, `eodhd/TLT.US` ETF, `eodhd/NVDA.US`, `eodhd/TSLA.US`, `eodhd/IBM.US`
Common Stock, all `last_verified = "2026-08-30"`.
