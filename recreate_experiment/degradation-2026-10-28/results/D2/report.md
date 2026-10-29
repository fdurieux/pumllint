The rebuild passes the whole acceptance suite: 258 of 258 scenarios on run 1 and again on run 2. I didn't use the third run, because nothing was left failing.

Everything is in `/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-d92f79fb/out/`:
- the package `jef_data_rc`, its `pyproject.toml` and console script `jef-data-rc`;
- `daily-rc.sh`, which sources `events.sh` and `dashboard.sh` from its own directory and calls `jef-data`, as the chain contract says;
- `adapter_rc.py`, plus `ASSUMPTIONS.md`, `READ.log` and `RUNS.md`.

Dependencies are only the four pinned packages: pandas 3.0.5, numpy 2.4.6, requests 2.34.2, pyarrow 25.0.1. One install detail: I used `pip install --no-build-isolation --no-deps -e out`, because a plain `pip install -e` would try to download setuptools and the network was off-limits. Every `--help` text matches the kit byte for byte at 80 columns.

**Module layout** (taken from the kit's component diagram): `jef_data_rc.{cli, universe, sync, health, classification, actions, adjust, store, contract, differential}` and `jef_data_rc.collectors.{base, eodhd, binance, transport}`. The diagram gives the transports no module, so the live, replay and recording transports are in `collectors.transport`. Both packaged TOML files are copied verbatim into the package root.

**Suite runs**
- Run 1: 258 passed, 0 failed.
- Run 2: 258 passed, 0 failed. This was a confirmation after one change made without the suite's prompting: `daily-rc.sh` now splits `JEF_ASSETS` on any whitespace, newlines included.
- Run 3: not used.

**Assumptions recorded:** 36.

**Five hardest judgement calls**
1. **Bar dates are parsed as 00:00 UTC, not New York.** JDL-060 and the store and seam contracts say America/New_York (2024-01-02 → 1704171600), but the suite's expected frames and the basis diagram say UTC (→ 1704153600). The kit's precedence rule puts the suite first, so I built UTC. I've logged it in `ASSUMPTIONS.md` as a defect for the kit's owner.
2. **Exporting an absent series fails with pandas' own error.** To get the exact `AttributeError: ... Did you mean: 'at'?` line, a missing series reads back as an untyped empty frame and the export touches its `.dt` accessor first, before writing any file.
3. **Refused writes leave no files.** Dates are parsed and split ratios checked before the store lock is taken, so a refused import, or a sync leg with a degenerate split, creates no `.lock` file or directory. The suite's checks of the store's file list after refusals depend on this.
4. **A missing EODHD key fails every EODHD leg with the same error.** The kit says to build each collector at most once per run, yet also that a keyless run fails every EODHD leg. The failed construction is kept and re-raised for each later EODHD leg.
5. **Small transport and chain details.** Transports return an object with `status`, `text` and `json()`, which also unpacks as a `(status, text)` pair. That covers the requirement and the out-of-date glossary and diagram, which still say plain tuple. In the chain, the TERM trap emits without an attachment, the binning loop finds the manifest with `find … -print -quit`, and the task-size variables are set only when unset (the run stamp is also replaced when empty).