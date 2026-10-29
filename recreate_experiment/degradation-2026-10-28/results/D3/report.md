The rebuild is finished and passes the kit's acceptance suite: 258 of 258 scenarios on the first run and again on the second. The third run wasn't needed. The kit's checksum manifest still verifies after the runs.

**Module layout** (the package mirrors the module names in the kit's component diagram, jef.data's modules under `jef_data_rc/`):
- `cli.py`: the module docstring is the parser description; `prog` is `jef-data`.
- `universe.py`, `sync.py`, `health.py` (status), `classification.py`, `actions.py` (corporate actions and split events), `adjust.py`, `store.py` (Parquet store plus the export frame), `contract.py` (validation), `differential.py`.
- `collectors/base.py` holds the transports, replay and recording, the rate limiter and the retry logic; `collectors/eodhd.py` and `collectors/binance.py` hold the two providers.
- `__main__.py` makes the package runnable as a module. `universe.toml` and `classifications.toml` ship byte-identical as package data.
- `pyproject.toml` declares the console script `jef-data-rc` and exactly the four pins (pandas 3.0.5, numpy 2.4.6, requests 2.34.2, pyarrow 25.0.1).
- I installed with `pip install --no-build-isolation --no-deps --no-index -e`, because a plain `pip install -e` would try to download setuptools.

**Suite results**
- Run 1: 258/258.
- Run 2: 258/258, after silencing harmless numpy 0/0 warnings and accepting date-time text as a Binance start/end.
- Run 3: not used.

Every `--help` block matches `contracts/cli_help.md` byte for byte. I also ran the `load` and `sync-actions` commands, which the suite can't reach, through a replayed transport: they produce the same stored frame as the sync does.

**Assumptions: 44 entries** in `ASSUMPTIONS.md`. Two are disagreements inside the kit that should go back to its owner as defects:
- JDL-132's `{missed_sessions or -}` would print `-` for a measured 0, but the scenario expects `0 missed`. I followed the scenario.
- The glossary and the component diagram still give the transport as returning a `(status, text)` tuple, where the revised contract says it returns an object. I built the object.

**Five hardest judgement calls**
1. **Price rounding:** "float32 division" means casting both the raw price and the split factor to float32 before dividing. I checked this against every row of the expected frames; the other reading misses 40 of 476 price cells.
2. **Timestamp quirk:** the stored timestamp is the parsed datetime's integer value divided by 10^6, on whatever unit pandas infers. That gives seconds for date strings, as the original does, rather than "fixing" it to milliseconds.
3. **Missing-series export:** an absent series reads back as a zero-row frame of object-typed columns. That way exporting or differencing it fails inside pandas with the exact `AttributeError ... Did you mean: 'at'?` line, unwrapped.
4. **No stray files on refusal:** I parse dates and check split ratios before taking the store lock. A refused import or a failed leg therefore leaves no `.lock` file or directory, which the scenario expecting an empty store requires.
5. **Command names:** `prog` stays `jef-data` even though the executable is `jef-data-rc`. The chain also calls `jef-data`, as its contract and stubs require, so a real deployment would need a `jef-data` alias.

`READ.log` lists all 208 kit files (each once); I read nothing outside the kit and `out/`. All deliverables are in `/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-716abf2f/out/`:
- `jef_data_rc/`
- `pyproject.toml`
- `daily-rc.sh`
- `adapter_rc.py`
- `ASSUMPTIONS.md`
- `READ.log`
- `RUNS.md`
- `events.sh`, `dashboard.sh` (the given externals, unchanged)