# The harness adapter — how the comparison harness drives an implementation

The experiment compares two implementations of the same program: the subject
and a recreation. Scenarios that only need the command line run the executable
named by the environment variable `JDL_UNDER_TEST` (default `jef-data`) and the
chain script named by `JDL_CHAIN` (default: the subject's `deploy/daily.sh`;
`events.sh` and `dashboard.sh` are expected beside it). Scenarios that must
inject a clock or replay recorded provider traffic cannot go through the
command line, which has no such switches. They go through a small Python
module, **the adapter**, named by `JDL_ADAPTER` (an importable module path).
Each implementation ships its own adapter; the adapter maps this fixed
interface onto that implementation's own API, whatever its names are. An
adapter is glue: it computes nothing itself.

Every function below is a module-level function of the adapter. Store paths
are directories the harness creates empty. "Universe file" means the TOML
grammar the kit documents; `None` means the implementation's packaged one.

```python
make_collector(provider: str, fixture_dir: str, api_key: str = "test-key-not-real") -> object
    # provider in {"eodhd", "binance"}. A collector whose HTTP layer REPLAYS the
    # recorded-fixture files found under fixture_dir (file shape: see the kit's
    # contracts), with no rate limiting in effect, and which raises on a request
    # no fixture answers. Never reaches the network.

load_universe(path: str | None) -> object
select_legs(universe, assets=None, providers=None) -> list[dict]
    # The ordered leg dicts (keys: the kit's contract). Raises the
    # implementation's own error on an unknown filter value or an empty selection.

run_sync(universe, store_path: str, *, assets=None, providers=None, dry_run=False,
         tail=10, force_actions=False, now=None, collectors=None, out=None) -> tuple[list, bool]
    # `now`: a timezone-aware UTC datetime standing in for the real clock, or None.
    # `collectors`: {provider: collector} from make_collector; a provider absent
    # from the dict is constructed the implementation's own way (the harness
    # always passes every provider a scenario needs). `out`: a callable taking
    # one string per log line, or None to discard. Returns the per-leg results
    # and the run's ok flag, as the command's exit code would read them.

sync_summary(results, ok) -> dict
    # Exactly the document `<exe> sync --summary-json FILE` writes.

status_json(universe, store_path: str, *, assets=None, providers=None, now=None,
            window=10, jump_threshold=0.40, staleness_k=2, resolution_window=500,
            resolution_k=0.20, flat_k=0.25, gap_k=5, spread_threshold=0.005,
            spread_alerts=False) -> tuple[dict, int]
    # Exactly the document `<exe> status --json` prints, and the exit code the
    # command would return. Knob names and defaults are the command's own.

export_frame(store_path: str, exchange: str, symbol: str) -> pandas.DataFrame
    # Exactly the frame `<exe> export` writes, as a DataFrame (before CSV).

stored_frame(store_path: str, exchange: str, symbol: str) -> pandas.DataFrame
    # The full stored series as the store returns it, every column included.

actions_state(store_path: str, symbol: str) -> dict
    # {"splits": [...], "dividends": [...], "last_updated": str | None} as stored;
    # each split and dividend as a plain dict of the stored fields.

import_csv(store_path: str, csv_path: str, exchange: str, symbol: str,
           asset_type: str, currency: str = "USD") -> int
    # What `<exe> import-csv` does; returns the row count it reports.
```

Rules for the adapter the subject's side ships: it may use the subject's
internal API freely. Rules for a recreation's adapter: the same, against the
recreation. The harness never imports anything but the adapter.
