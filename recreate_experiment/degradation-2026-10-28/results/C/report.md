The rebuild passes the kit's acceptance suite in full: 258 of 258 scenarios on the first run and again on the second. I left the third run unused, since nothing was left to fix. I read the whole kit before writing code: all 208 kit files are in `READ.log`, and `MANIFEST.sha256` still verifies after the runs, so the kit is unchanged.

**Module layout.** It follows the component diagram's module names under `jef_data_rc/`:
- `cli.py` (argparse `prog="jef-data"`, its docstring is the parser description; console script `jef-data-rc` → `jef_data_rc.cli:main`)
- `universe.py`, `sync.py`, `health.py` (status checks), `classification.py`, `actions.py`, `adjust.py`, `store.py` (Parquet store plus the export projection), `contract.py` (validation), `differential.py`
- `collectors/base.py` (the three transports, fixture keys, rate limiter, retries), `collectors/eodhd.py`, `collectors/binance.py`
- `universe.toml` and `classifications.toml` copied byte-identical as package data
- `__main__.py`, so `python -m jef_data_rc` also works

`pyproject.toml` declares distribution `jef-data-rc` 0.6.0, Python ≥ 3.11, and exactly the four pins as its only runtime dependencies. I installed it with `pip install --no-build-isolation -e`, because normal build isolation would need the network to fetch setuptools. `daily-rc.sh` and `adapter_rc.py` sit beside the given `events.sh` and `dashboard.sh`.

**Suite results** (recorded in `RUNS.md`):
1. 258 passed, 0 failed.
2. 258 passed, 0 failed — a regression check after a small cleanup in `load` so its collector is closed exactly once.
3. Not used.

Before spending suite runs, I also checked parts the suite can't reach with my own probes: all 11 `--help` texts byte for byte, the `load` happy path through replayed fixtures (it reproduces the expected stored frame), retries and token redaction against a closed localhost port, the rate limiter, and every chain scenario against the kit's own stub logic.

**Assumptions:** 39 entries in `ASSUMPTIONS.md` (A-01 to A-39).

**Five hardest judgement calls:**
1. **Command names:** the parser prints `jef-data` (the contract's explicit prog, which every help and error text needs) while the installed command is `jef-data-rc`. The chain still calls `jef-data`, as its contract says, so a deployment must put a `jef-data` on PATH that runs this build (A-01, A-31).
2. **When the series lock is taken:** writes check their incoming rows before locking, so a refused import or sync leaves no file at all, not even `.lock`. The `adjust` command locks first and then reads, as its contract reads, so adjusting an absent series leaves an empty symbol directory with its `.lock` (A-11).
3. **Stored timestamps are Unix seconds:** dates are parsed at microseconds with the format taken from the first bar, then divided by 10^6, as the kit specifies despite the column being documented as milliseconds (JDL-060).
4. **Export of an absent series:** the empty read-back frame has untyped columns, so the export fails with pandas' own `AttributeError ... Did you mean: 'at'?`, as recorded from the original; the same applies to `differential` on an absent side.
5. **Chain metadata parse:** two one-line `python3 -c` programs (digest, then task size), with the size variables set and exported only when the parse succeeds, so a bad metadata body leaves them unset in the child commands (A-19, A-20).

Files are in /tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-ad0f6d4e/out:
- jef_data_rc/
- pyproject.toml
- daily-rc.sh
- adapter_rc.py
- ASSUMPTIONS.md
- READ.log
- RUNS.md