# Mutant calibration

Both mutants are full copies of the subject tree (`hidden/mutants/m1`,
`hidden/mutants/m2`), edited only in `src/jef/data/sync.py`. Each was run with
`PYTHONPATH=<mutant>/src` prepended (verified: `jef.data.sync.__file__`
resolves into the mutant), `PYTHONDONTWRITEBYTECODE=1`, every `__pycache__`
purged first (and none created), nothing installed; the chain used is the
unmutated `hidden/chain_original/daily.sh`. Command: `hidden/run_suite.sh`.

Baseline on the subject: **178 passed, 0 failed** (178 test cases from 95
scenarios incl. outline rows).

## m1 - a raw-basis leg fetches its bars BEFORE the corporate-actions refresh

The bar fetch (`collector.get_eod`, with the inverted-window branch) moved
above the actions block of `_run_leg`; the inverted-window detail text is
re-attached at its original position so green-run details are unchanged.
Splits are still read after the refresh, so stored cells are identical: the
mutant is visible only through failure ordering.

```diff
--- subject/src/jef/data/sync.py	2026-10-23 09:31:24.846059632 +0000
+++ m1/src/jef/data/sync.py	2026-10-23 10:35:23.821403250 +0000
@@ -188,6 +188,21 @@
     start, end, latest = _window(store, leg, tail, today)
     detail = ""
     splits = ()
+    # MUTANT m1: the bar fetch moved before the actions refresh
+    inverted_detail = ""
+    if latest is not None and end is not None and start > end:
+        # The INVERTED window (owner ruling 2026-09-13,
+        # docs/DATA_CONTRACT.md §7 item 10): a series with rows past its
+        # declared `end` has nothing to fetch - the stored tail starts
+        # after the cap - so no request goes out (a provider's answer to
+        # from > to is undefined) and the leg says so loudly, never red:
+        # the page-limit guard's pattern. The fix is the declaration.
+        bars = []
+        inverted_detail = (f"end {end} predates the stored tail (from {start}); "
+                   "nothing fetched - a pinned window with rows past its "
+                   "end, the fix is the declaration; ")
+    else:
+        bars = collector.get_eod(leg["symbol"], start=start, end=end)
     if leg["provider"] == "eodhd":
         # The basis keys on the DECLARED class, never on the symbol
         # suffix. `.CC` is EODHD's crypto namespace and reading it was
@@ -233,19 +248,7 @@
     else:
         basis = "split_adjusted"  # binance klines: pre-adjusted crypto
 
-    if latest is not None and end is not None and start > end:
-        # The INVERTED window (owner ruling 2026-09-13,
-        # docs/DATA_CONTRACT.md §7 item 10): a series with rows past its
-        # declared `end` has nothing to fetch - the stored tail starts
-        # after the cap - so no request goes out (a provider's answer to
-        # from > to is undefined) and the leg says so loudly, never red:
-        # the page-limit guard's pattern. The fix is the declaration.
-        bars = []
-        detail += (f"end {end} predates the stored tail (from {start}); "
-                   "nothing fetched - a pinned window with rows past its "
-                   "end, the fix is the declaration; ")
-    else:
-        bars = collector.get_eod(leg["symbol"], start=start, end=end)
+    detail += inverted_detail
     if (latest is None and leg["start"] is None
             and len(bars) == getattr(collector, "limit", -1)):
         # the no-silent-caps guard (Arc X rung (b), 2026-08-21): a first
```

Result: **2 failed, 176 passed**. Caught by:

| scenario (feature) | why it fails on m1 |
|---|---|
| A 404 on the bars fails the leg after the corporate actions were refreshed (collectors.feature) | the 404 now happens before the refresh, so no actions files exist (`actions state` / `store holds exactly the files` assertions fail) |
| When both the actions and the bars would fail, the actions failure is what the leg reports (collectors.feature) | detail becomes `CollectorError: eod SPLT.US: HTTP 404: ...` instead of `... splits SPLT.US: HTTP 503 after 5 attempts` |

The second scenario was added during calibration (the first run caught m1
with one scenario only); it passes on the subject.

## m2 - the crypto end-guard removed

```diff
--- subject/src/jef/data/sync.py	2026-10-23 09:31:24.846059632 +0000
+++ m2/src/jef/data/sync.py	2026-10-23 10:35:23.821644246 +0000
@@ -144,7 +144,7 @@
     universe's declared class. A `.CC` symbol declared non-crypto is a
     mis-declaration whose fix is the declaration."""
     crypto = leg["asset_type"] == "crypto"
-    guard = (today - timedelta(days=1)).isoformat() if crypto else None
+    guard = None  # MUTANT m2: the crypto end-guard removed
     ends = [e for e in (leg["end"], guard) if e]
     end = min(ends) if ends else None  # ISO strings order chronologically
     recents = store.recent_dates(leg["exchange"], leg["symbol"], tail)
```

Result: **11 failed, 167 passed**. Every crypto leg now requests without
the `to` / `endTime` the fixtures were recorded with (and the dry-run plan
loses its `to {yesterday}`):

* (x1) test_a_bar_endpoint_answering_something_other_than_a_json_list_fails_the_leg
* (x1) test_a_dry_run_plans_every_leg_shape_from_local_state_only
* (x1) test_a_first_fill_without_a_start_that_lands_on_the_page_limit_says_it_is_a_trailing_window
* (x1) test_an_eodhd_crypto_series_is_stored_as_served_endguarded_at_the_previous_utc_day
* (x1) test_binance_klines_become_preadjusted_bars_dated_by_their_utc_open_time
* (x1) test_binance_pages_ascending_from_the_declared_start_until_a_short_page
* (x4) test_the_crossvenue_close_spread_warns_strictly_above_its_threshold_or_alerts_when_promoted
* (x1) test_the_declared_class_never_the_cc_suffix_decides_basis_actions_and_guard
