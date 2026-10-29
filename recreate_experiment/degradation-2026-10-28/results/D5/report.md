The rebuild passed the kit's acceptance suite on the first run: 256 of 256 scenarios. I logged 33 assumptions in `ASSUMPTIONS.md`. The biggest is one I could not settle from the kit (judgement call 1 below).

**Module layout** (from the component diagram), under `/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-e6e4099d/out/`:
- `jef_data_rc/`: `cli`, `universe`, `sync`, `health` (status), `classification`, `actions`, `adjust`, `store` (also produces the 7-column export frame), `contract` (validate), `differential`, plus `collectors/base.py`, `collectors/eodhd.py` and `collectors/binance.py`. `universe.toml` and `classifications.toml` ship byte-identical as package data.
- The console script is `jef-data-rc`, and `python -m jef_data_rc` also works. The only runtime pins are pandas 3.0.5, numpy 2.4.6, requests 2.34.2 and pyarrow 25.0.1.
- `daily-rc.sh` calls `jef-data` by name and sources `events.sh` and `dashboard.sh` from its own directory. `adapter_rc.py` implements every function of the harness interface.

**Suite results** (recorded in `RUNS.md`):
- Run 1: 256 passed, 0 failed.
- Run 2: 256 passed, 0 failed. Between runs I changed one thing not shown by the suite: the chain now splits `JEF_ASSETS` on any whitespace, newlines included.
- Run 3: not used, since nothing was left to fix.

All 11 `--help` texts match the kit byte for byte. Outside the suite, I also ran `load` and `sync-actions` against a local fake HTTP server through `--base-url`, and checked retries, token redaction and the 100-page Binance cap directly.

**Five hardest judgement calls**
1. **Crypto end-guard: the kit contradicts itself.** The original's verbatim `sync` help says crypto is "end-guarded at the previous UTC day", and other evidence points the same way: a fixture comment, leftover decision-table output values, and one clause of JDL-095 that can only happen with a guard. JDL-094 says the fetch end is the universe `end`, else open. I followed JDL-094 (no guard), because the kit's precedence rule puts requirements above contracts. The suite cannot tell the two apart: every crypto scenario sets its `end` to the day before the run date. If the original really has the guard, hidden comparisons on crypto legs without a declared end will differ. I flagged this as a kit defect.
2. **Stored `timestamp` is Unix seconds.** It is the microsecond count integer-divided by 10^6, reproducing the pinned pandas quirk on purpose; `datetime` is stored at millisecond resolution.
3. **Lock placement.** Incoming rows (date parsing, split-ratio checks, volume adjustment) are built before taking the series lock, so a refused import or a bad split ratio writes no files at all. Re-adjust and reconcile take the lock before reading, so `adjust` on an absent series leaves a `.lock` file behind.
4. **Status table "missed" column.** JDL-132's literal `{missed_sessions or -}` would print `-` for 0, but a scenario shows `0 missed`. I let the suite win: `-` appears only when the field is absent.
5. **Two smaller conventions.** The traceback's last line names this package's module (`jef_data_rc.store.StoreError: ...`) rather than the original's `jef.data...`; only the `ErrorClass: message` suffix matches. Hand-run `sync-actions` writes its files under the symbol as given, while `load` reads splits under the normalised symbol.

The package was installed with `pip install --no-build-isolation -e out`, because a plain `pip install -e` would download setuptools.

Files are in `/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-e6e4099d/out/`:
- `ASSUMPTIONS.md`
- `READ.log` (211 paths: every kit file plus the two externals)
- `RUNS.md`
- `adapter_rc.py`
- `daily-rc.sh`
- `pyproject.toml`
- `jef_data_rc/`
