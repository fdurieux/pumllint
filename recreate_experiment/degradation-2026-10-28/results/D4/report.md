The rebuild passed the kit's acceptance suite in full on the first run: 256 of 256 scenarios. I read all 206 kit files before writing any code.

**Suite results** (recorded in `RUNS.md`):
- **Run 1:** 256 collected, 256 passed, 0 failed. Nothing needed fixing.
- **Run 2:** 256 collected, 256 passed, 0 failed. The code was unchanged; this was a confirmation run on the final tree, mainly to check that the timing-dependent TERM scenario in the chain tests is stable.
- **Run 3:** not used, because nothing was left to fix.

After both runs the kit still matches `MANIFEST.sha256` byte for byte. I ran pytest with `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1` so it wrote nothing into the kit.

**Module layout:** it follows the component diagram (`uml/component.puml`). Everything is in `/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-f4d38de7/out/`:
- `jef_data_rc/`: `cli`, `universe`, `sync`, `health`, `classification`, `actions`, `adjust`, `store`, `contract`, `differential`.
- `jef_data_rc/collectors/`: `base`, `eodhd`, `binance`, plus `transport` (live, replaying and recording transports, and the response object).
- The packaged `universe.toml` and `classifications.toml` are byte-identical copies of the kit's.
- `pyproject.toml` pins exactly pandas 3.0.5, numpy 2.4.6, requests 2.34.2 and pyarrow 25.0.1, with the console script `jef-data-rc`. The parser's program name stays `jef-data`, so usage lines and messages read as the original's. All 11 `--help` blocks match the kit verbatim.
- `daily-rc.sh` sources `events.sh` and `dashboard.sh` from its own directory and calls `jef-data`. `adapter_rc.py` implements every harness function. `ASSUMPTIONS.md`, `READ.log` and `RUNS.md` are there too.

**Install:** this environment has no network, so I installed with `pip install --no-build-isolation -e out` rather than the plain `pip install -e out` the task gives.

**Assumptions:** 44 entries in `ASSUMPTIONS.md`, A-01 to A-44. Two of them are kit defects worth reporting to the kit owner:
- The suite expects a CSV leg's detail to read `{rows} row(s) loaded`, but requirement JDL-099 and the summary example say `imported`.
- The glossary still describes the transport as returning a `(status, text)` pair, which the 2026-10-24 revision changed elsewhere to a response object.

**Five hardest judgement calls:**
1. **CSV leg wording:** I printed `row(s) loaded` because the suite outranks the requirements and contracts under the kit's precedence rule.
2. **Traceback module paths:** the last line reads `jef_data_rc.store.StoreError: ...` instead of the original's `jef.data....`. I kept the real module names rather than faking them; the text after the class name is identical.
3. **When files get created:** dates, CSV columns and split ratios are checked before the store lock is taken, so a refused import leaves no files (the suite requires this). A reconcile given zero bars never touches the store. `adjust` on an absent series does take the lock first, creating the series folder and `.lock` file before failing; no scenario checks that.
4. **Exactness tied to the pinned pandas:** stored timestamps reproduce pandas 3's microsecond parse divided by 10^6, which gives seconds. A series the store does not hold reads back as an untyped empty table, so `export` and `differential` on it fail with pandas' own `AttributeError ... Did you mean: 'at'?` line.
5. **Status table, `{missed_sessions or -}`:** I read this as "a dash only when the field is absent", so a measured 0 prints `0 missed`, as the suite shows. This is among several untested readings recorded alongside it, such as `sync-actions` writing its files under the normalised symbol.