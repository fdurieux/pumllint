# Universe grammar (`universe.toml`)

The universe is the declarative, acquisition-only configuration that `sync`,
`status` and `universe` execute. The packaged default is
[`universe.toml`](universe.toml) (verbatim copy; it must ship byte-identical
inside the rebuilt package and be the default of every `--universe` flag).
Parsing is strict: any violation is a refusal (UniverseError), never a silent
skip. Requirements: JDL-001 … JDL-022.

## 1. Tables and keys

### Top level

| key | type | required | notes |
|---|---|---|---|
| `defaults` | table | no | §1.1 |
| `asset` | array of tables | yes (≥ 1) | §1.2 |

No other top-level key is allowed.

### 1.1 `[defaults]`

| key | type | default | constraint |
|---|---|---|---|
| `store` | string | `"data"` | non-empty |
| `currency` | string | `"USD"` | non-empty |

### 1.2 `[[asset]]`

| key | type | default | constraint |
|---|---|---|---|
| `name` | string | — (required) | non-empty; unique across the file |
| `asset_class` | string | — (required) | `stock` \| `crypto` \| `bond_etf` |
| `currency` | string | `defaults.currency` | non-empty |
| `threshold` | integer or float (not boolean) | `-0.05` | documentation only; normalised to float; no behaviour reads it |
| `enabled` | boolean | `true` | a disabled asset is skipped by every command except `universe` |
| `source` | array of tables | — (required, ≥ 1) | §1.3 |

`asset_class` → store `asset_type`: `stock` → `stock`, `crypto` → `crypto`,
`bond_etf` → `etf`.

### 1.3 `[[asset.source]]`

| key | type | default | applies to | constraint |
|---|---|---|---|---|
| `provider` | string | — (required) | all | `eodhd` \| `binance` \| `yahoo-csv` |
| `symbol` | string | — (required) | all | non-empty; for `eodhd` must contain `.` (`TICKER.EXCHANGE`) |
| `path` | string | — | `yahoo-csv` only (required there) | non-empty; relative paths resolve against the working directory when the leg runs |
| `exchange` | string | `eodhd` / `binance` / `yahoo` per provider | all | non-empty; the store partition tag |
| `start` | date | none | `eodhd`, `binance` | first-fill floor only |
| `end` | date | none | `eodhd`, `binance` | persistent cap on every fetch |
| `kind` | string | `"eod"` | all | only `eod` |
| `enabled` | boolean | `true` | all | |
| `modeled` | boolean | `false` | all | see §2 |
| `note` | string | none | all | non-empty; shown by `universe` |

A source's currency is its asset's currency (not configurable per source).
`price_basis` and `volume_basis` are never configurable (adjustment.md §1).

### 1.4 Dates

`start` / `end` accept a TOML local date (`2024-01-02`) or a string that
Python 3.11+ `date.fromisoformat` accepts (`"2024-01-02"`, `"20240102"`); both
normalise to `YYYY-MM-DD`. A TOML date-time (e.g. `2024-01-01T10:00:00Z`) is
accepted and carried as its full ISO text (`2024-01-01T10:00:00+00:00`). Any
other value (integer, malformed string) is a refusal. `start` > `end`
(compared as normalised text) is a refusal.

## 2. The modeled-source rules (per asset)

1. A source marked `modeled = true` must be enabled.
2. At most one enabled source is marked modeled.
3. An enabled asset with ≥ 2 enabled sources must mark exactly one.
4. An enabled asset must have ≥ 1 enabled source (pause an asset with
   `enabled = false` on the asset itself).

Rules 3 and 4 do not apply to a disabled asset. The modeled marker drives no
behaviour of this program beyond these checks (it designates the series the
downstream binning consumes).

## 3. Cross-asset rules

* Asset names are unique.
* No two different assets may declare the same (exchange tag, symbol) store
  coordinate (an asset may repeat one across its own sources).

## 4. Validation order and refusal texts

The first violation found stops parsing. Order and texts are requirements
JDL-012, JDL-013, JDL-014,
JDL-015, JDL-016, JDL-017,
JDL-018, JDL-019, JDL-020,
JDL-021; refusals.md tabulates them. The location prefix
(`where`) is:

| context | `where` |
|---|---|
| file-level checks | `{origin}` = the path as given, or `packaged universe.toml` |
| defaults unknown key | `{origin} [defaults]` |
| defaults value checks | `[defaults]` |
| asset before its name is read (table check, unknown keys, name) | `asset #{n}` (1-based) |
| asset after its name is read | `asset '{name}'` |
| source | `asset '{name}' source #{n}` (1-based) |

Lists in messages render as Python lists of quoted strings (`['a', 'b']`);
values as Python repr (`'x'`, `True`, `5`).

## 5. Normalised form

The parsed universe (what `load_universe` returns and every command consumes):

```json
{"defaults": {"store": "data", "currency": "USD"},
 "assets": [
  {"name": "SPLT", "asset_class": "stock", "asset_type": "stock",
   "currency": "USD", "threshold": -0.05, "enabled": true,
   "sources": [
    {"provider": "eodhd", "kind": "eod", "enabled": true, "modeled": false,
     "exchange": "eodhd", "symbol": "SPLT.US", "currency": "USD",
     "start": "2024-01-02", "end": null}]}]}
```

A source carries `note` (after `currency`) only when declared; a `yahoo-csv`
source carries `path` instead of `start`/`end`.

## 6. The `universe` listing

`jef-data universe` prints, per asset, `{name} ({asset_class}, {currency},
threshold {threshold})` (threshold as Python float text, e.g. `-0.05`,
`-1.0`) plus ` [disabled]`; then per source `  {provider}: {path or symbol}`
plus ` [disabled]` plus ` - {note}`. The packaged universe prints:

```
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
```
