"""Build the kit's DMN tables (kit/contracts/dmn/*.dmn) and the round-1
command x store-state table (harness/dmn_round1/) from compact specs.

Lab tooling, revision 2026-10-23 (wave 2). Every row cites the kit
requirement it encodes; the round-1 table cites the round-1 kit (pumllint
1451c05) only. Run: python harness/dmn_build.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dmn_write import table, write  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "kit" / "contracts" / "dmn"
R1 = ROOT / "harness" / "dmn_round1"

PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
TYPES = ["stock", "etf", "crypto"]

# ---- 1. basis resolution (adjustment.md s1-2, JDL-086, JDL-100) ------------
basis = table(
    "price_basis_resolution",
    [("provider", "string", PROVIDERS), ("declared_asset_type", "string", TYPES)],
    [("price_basis", "string", ["raw", "split_adjusted"]),
     ("split_events_applied", "boolean", None),
     ("actions_eligible", "boolean", None)],
    [(['"eodhd"', '"stock"'], ['"raw"', "true", "true"], "adjustment.md s1 row 1; JDL-086"),
     (['"eodhd"', '"etf"'], ['"raw"', "true", "true"], "adjustment.md s1 row 2 (bond_etf -> etf); JDL-086"),
     (['"eodhd"', '"crypto"'], ['"split_adjusted"', "false", "false"], "adjustment.md s1 row 3; JDL-086 (declared class, not suffix)"),
     (['"binance"', "-"], ['"split_adjusted"', "false", "false"], "adjustment.md s1 row 4; JDL-100"),
     (['"yahoo-csv"', "-"], ['"split_adjusted"', "false", "false"], "adjustment.md s1 row 5; JDL-070")],
    description="Which basis a stored series gets and whether stored split events are applied, from the leg's provider and DECLARED asset_type (never the symbol suffix).")
volume = table(
    "volume_raw_source",
    [("price_basis", "string", ["raw", "split_adjusted"]), ("provider", "string", PROVIDERS)],
    [("stored_volume_raw", "string", ["served_volume_divided_by_F", "served_volume"])],
    [(['"raw"', '"eodhd"'], ['"served_volume_divided_by_F"'], "adjustment.md s2 row 1: EODHD serves split-adjusted volume, raw-ized by the cumulative factor; JDL-056"),
     (['"raw"', 'not("eodhd")'], ['"served_volume"'], "adjustment.md s2 row 2 (no raw-basis collector other than EODHD exists today; the row is the contract, not a reachable path); JDL-056"),
     (['"split_adjusted"', "-"], ['"served_volume"'], "adjustment.md s2 row 3: the collector's basis is not consulted; JDL-055")],
    description="What is written to volume_raw.")

# ---- 2. command x store-state -> outcome (cli.md, refusals.md, store.md s6) ----
COMMANDS = ["sync-collector-leg", "sync-yahoo-csv-leg", "load", "adjust", "import-csv", "export", "differential-a", "differential-b", "status"]
STATES = ["absent", "filled"]
OUT_KINDS = ["proceed", "refuse-wrapped", "refuse-traceback", "alert"]
# The ATTR literal is the exact last traceback line measured on the original.
ATTR = "AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?"

def cmd_rows(revised):
    rows = [
        (['"sync-collector-leg"', '"absent"'], ['"proceed"', '"first fill: fetch from the universe start (or open) and write every served row; no revisions"'], "JDL-093, store.md s6 reconcile (empty series)"),
        (['"sync-collector-leg"', '"filled"'], ['"proceed"', '"tail refresh: fetch from the oldest of the newest tail sessions and reconcile"'], "JDL-093, JDL-065"),
        (['"sync-yahoo-csv-leg"', "-"], ['"proceed"', '"overwrite the series with the whole file"'], "JDL-099, JDL-070"),
        (['"load"', '"absent"'], ['"proceed"', '"first fill from --from (or open); append; re-adjust when raw and bars ingested"'], "cli.md load step 4-5, JDL-141"),
        (['"load"', '"filled"'], ['"proceed"', '"incremental from the day after the latest stored session; append; re-adjust when raw"'], "cli.md load step 4-5, JDL-141"),
        (['"adjust"', '"absent"'], ['"refuse-traceback"', '"StoreError: nothing stored for {exchange}/{symbol}"'], "refusals.md X-02, JDL-069"),
        (['"adjust"', '"filled"'], ['"proceed"', '"re-derive main OHLCV from *_raw with the stored splits (split_adjusted series refuse: X-03, a different input)"'], "JDL-069; X-03 is on price_basis, not store state"),
        (['"import-csv"', "-"], ['"proceed"', '"overwrite the series with the CSV rows"'], "JDL-070"),
        (['"export"', '"filled"'], ['"proceed"', '"write the seam frame to F and print the validation report"'], "cli.md export, JDL-138"),
        (['"status"', '"absent"'], ['"alert"', '"never filled - no stored rows (jef-data sync first)"'], "JDL-114"),
        (['"status"', '"filled"'], ['"proceed"', '"run the source checks in JDL-110 order"'], "JDL-110"),
    ]
    if revised:
        rows += [
            (['"export"', '"absent"'], ['"refuse-traceback"', f'"{ATTR}"'], "refusals.md X-09 (closing round), JDL-159"),
            (['"differential-a"', '"absent"'], ['"refuse-traceback"', f'"{ATTR}"'], "wave 2: measured on the original 2026-10-23 (A series absent, --b-csv given): exit 1, stdout empty"),
            (['"differential-b"', '"absent"'], ['"refuse-traceback"', f'"{ATTR}"'], "wave 2: measured on the original 2026-10-23 (A stored, --b-symbol names an absent series): exit 1, stdout empty"),
            (['"differential-a"', '"filled"'], ['"proceed"', '"A = seam frame of a-exchange/S"'], "cli.md differential, JDL-140, JDL-082"),
            (['"differential-b"', '"filled"'], ['"proceed"', '"B = seam frame of b-exchange/S2 (or the CSV when --b-csv)"'], "cli.md differential, JDL-140, JDL-082"),
        ]
    else:
        rows += [
            (['"export"', '"absent"'], ['"refuse-traceback"', "traceback, no file written"], "round-1 refusals.md X-04: the outcome category is given, the message is not"),
            (['"differential-a"', "-"], ['"proceed"', '"A = seam frame of a-exchange/S"'], "round-1 cli.md differential: silent on an absent series"),
            (['"differential-b"', "-"], ['"proceed"', '"B = seam frame of b-exchange/S2 (or the CSV when --b-csv)"'], "round-1 cli.md differential: silent on an absent series"),
        ]
    return rows

def cmd_table(revised):
    return table(
        "command_by_store_state",
        [("command", "string", COMMANDS), ("store_state", "string", STATES)],
        [("outcome", "string", OUT_KINDS), ("message_or_action", "string", None)],
        cmd_rows(revised),
        description=("What each store-touching command does when the addressed series is absent or filled. "
                     + ("Revision 2026-10-23 (wave 2): the two differential rows carry outcomes measured on the original." if revised
                        else "Round-1 kit (pumllint 1451c05) as written: built for the W2-E3 measurement only.")))

# ---- 3. sync window (JDL-093, JDL-094, JDL-095) ----------------------------
fetch_start = table(
    "fetch_start",
    [("series_has_rows", "boolean", None), ("universe_start_declared", "boolean", None)],
    [("fetch_start", "string", ["universe_start", "open", "oldest_of_newest_tail_sessions"])],
    [(["false", "true"], ['"universe_start"'], "JDL-093 first fill with start"),
     (["false", "false"], ['"open"'], "JDL-093 first fill, full history"),
     (["true", "-"], ['"oldest_of_newest_tail_sessions"'], "JDL-093: the universe start is never read again once the series has rows")])
fetch_end = table(
    "fetch_end",
    [("declared_crypto", "boolean", None), ("universe_end_declared", "boolean", None)],
    [("fetch_end", "string", ["universe_end", "today_minus_1", "min_universe_end_today_minus_1", "open"])],
    [(["true", "true"], ['"min_universe_end_today_minus_1"'], "JDL-094: ISO-string minimum"),
     (["true", "false"], ['"today_minus_1"'], "JDL-094 end-guard, any provider"),
     (["false", "true"], ['"universe_end"'], "JDL-094: end caps every fetch"),
     (["false", "false"], ['"open"'], "JDL-094")])
request = table(
    "bar_request",
    [("series_has_rows", "boolean", None), ("start_after_end", "boolean", None)],
    [("request", "string", ["send", "skip_green_inverted"])],
    [(["true", "true"], ['"skip_green_inverted"'], "JDL-095: zero bars, leg green, detail names the declaration"),
     (["true", "false"], ['"send"'], "JDL-093"),
     (["false", "-"], ['"send"'], "JDL-095: an empty series with start > end still sends its request")])

# ---- 4. actions gate (JDL-086, JDL-091) ------------------------------------
gate = table(
    "actions_gate",
    [("actions_eligible", "boolean", None), ("force_actions", "boolean", None),
     ("splits_stamp", "string", ["none", "before_today", "today"])],
    [("action", "string", ["refresh", "skip_fresh", "none"]), ("detail_part", "string", None)],
    [(["false", "-", "-"], ['"none"', '""'], "JDL-086: not eligible, no actions part in the detail"),
     (["true", "true", "-"], ['"refresh"', '"{s} split(s), {d} dividend(s); "'], "JDL-091 force"),
     (["true", "false", '"none"'], ['"refresh"', '"{s} split(s), {d} dividend(s); "'], "JDL-091 no stamp"),
     (["true", "false", '"before_today"'], ['"refresh"', '"{s} split(s), {d} dividend(s); "'], "JDL-091 stale stamp"),
     (["true", "false", '"today"'], ['"skip_fresh"', '"actions fresh; "'], "JDL-091")],
    description="today = the run clock's UTC date (JDL-088); the stamp is the splits file's, written by the real wall clock (JDL-043).")

# ---- 5. status verdicts (JDL-114..JDL-132) ---------------------------------
staleness = table(
    "staleness_check",
    [("series_has_rows", "boolean", None), ("expected_sessions_missed", "integer", ">= 0")],
    [("finding", "string", ["ALERT_never_filled", "ALERT_stale", "none"]), ("ends_report", "boolean", None)],
    [(["false", "-"], ['"ALERT_never_filled"', "true"], "JDL-114"),
     (["true", "< 2"], ['"none"', "false"], "JDL-116 below --staleness (default 2 encoded)"),
     (["true", ">= 2"], ['"ALERT_stale"', "false"], "JDL-116: missed_sessions reported regardless")],
    description="--staleness is encoded at its default (2); the threshold is an input of the program, a constant of this table.")
actions_fresh = table(
    "actions_freshness_check",
    [("actions_eligible", "boolean", None), ("splits_stamp", "string", ["none", "present"]),
     ("refresh_sessions_missed", "integer", ">= 0")],
    [("finding", "string", ["ALERT_never_synced", "ALERT_stale", "none"])],
    [(["false", "-", "-"], ['"none"'], "JDL-125 applies to actions-eligible legs only"),
     (["true", '"none"', "-"], ['"ALERT_never_synced"'], "JDL-125"),
     (["true", '"present"', "< 2"], ['"none"'], "JDL-125: fixed threshold 2, not an option"),
     (["true", '"present"', ">= 2"], ['"ALERT_stale"'], "JDL-125")])
phantom = table(
    "phantom_jump_check",
    [("previous_close_nonzero", "boolean", None), ("abs_move_exceeds_threshold", "boolean", None),
     ("split_on_same_date", "boolean", None)],
    [("finding", "string", ["ALERT_phantom_jump", "none"])],
    [(["false", "-", "-"], ['"none"'], "JDL-124: rows with a zero previous close are skipped"),
     (["true", "false", "-"], ['"none"'], "JDL-124: strict > --jump-threshold"),
     (["true", "true", "true"], ['"none"'], "JDL-124: a same-day stored split explains the move (splits read for eligible legs only)"),
     (["true", "true", "false"], ['"ALERT_phantom_jump"'], "JDL-124")])
spread = table(
    "cross_venue_spread_check",
    [("measurable", "string", ["empty_side", "no_common_session", "zero_mid", "measured"]),
     ("spread_exceeds_threshold", "boolean", None), ("spread_alerts_flag", "boolean", None)],
    [("note", "string", ["not_measured", "close_spread"]), ("finding", "string", ["none", "WARNING", "ALERT"])],
    [(['not("measured")', "-", "-"], ['"not_measured"', '"none"'], "JDL-127: exactly one note, spread null"),
     (['"measured"', "false", "-"], ['"close_spread"', '"none"'], "JDL-129: the note is always added"),
     (['"measured"', "true", "false"], ['"close_spread"', '"WARNING"'], "JDL-129 default"),
     (['"measured"', "true", "true"], ['"close_spread"', '"ALERT"'], "JDL-129 --spread-alerts")])
verdict = table(
    "status_exit_and_flag",
    [("alerts_total", "integer", ">= 0"), ("warnings_in_report", "integer", ">= 0")],
    [("exit_code", "number", None), ("row_flag", "string", ["ALERT", "WARN", "ok"])],
    [([">= 1", "-"], ["1", '"ALERT"'], "JDL-131/JDL-132 (flag is per report; exit is per run - the table reads alerts_total as the report's alerts for the flag)"),
     (["0", ">= 1"], ["0", '"WARN"'], "JDL-132"),
     (["0", "0"], ["0", '"ok"'], "JDL-132")],
    description="Counts are non-negative integers (typeRef integer, inputValues >= 0): the checker samples integer points of the constrained partition only.")

# ---- 6. refusal routing (refusals.md headings, cli.md General rules) ----------
routing = table(
    "refusal_routing",
    [("raised_in", "string", ["universe_load", "selection", "leg_body", "load_declaration", "command_body", "argument_parse"])],
    [("handling", "string", ["wrapped", "leg_failed", "traceback", "usage"]),
     ("exit_code", "number", None), ("stderr_form", "string", None)],
    [(['"universe_load"'], ['"wrapped"', "1", '"{command}: {message}"'], "refusals.md Universe: wrapped by sync, status, universe; JDL-134, JDL-144, JDL-145"),
     (['"selection"'], ['"wrapped"', "1", '"{command}: {message}"'], "refusals.md Selection; JDL-085, JDL-134"),
     (['"leg_body"'], ['"leg_failed"', "1", '"FAILED  {asset} {exchange}/{symbol} [{provider}]: {ErrorClass}: {message} (stdout); other legs run"'], "refusals.md Leg failures, JDL-101"),
     (['"load_declaration"'], ['"wrapped"', "1", '"load: {message}"'], "refusals.md D-01..D-03; JDL-142"),
     (['"command_body"'], ['"traceback"', "1", '"Python traceback, last line {module}.{ErrorClass}: {message}"'], "refusals.md Other commands X-02..X-07, X-09; JDL-069, JDL-159, JDL-163"),
     (['"argument_parse"'], ['"usage"', "2", '"usage: ... then {prog}: error: {message}"'], "refusals.md X-08, cli.md Parser errors; JDL-133, JDL-161")])

KIT.mkdir(parents=True, exist_ok=True)
R1.mkdir(parents=True, exist_ok=True)
write(KIT / "basis.dmn", [basis, volume], "basis")
write(KIT / "command_store_state.dmn", [cmd_table(True)], "command_store_state")
write(KIT / "sync_window.dmn", [fetch_start, fetch_end, request], "sync_window")
write(KIT / "actions_gate.dmn", [gate], "actions_gate")
write(KIT / "status_verdicts.dmn", [staleness, actions_fresh, phantom, spread, verdict], "status_verdicts")
write(KIT / "refusal_routing.dmn", [routing], "refusal_routing")
write(R1 / "command_store_state.dmn", [cmd_table(False)], "command_store_state_round1")
print("written", sorted(p.name for p in KIT.glob("*.dmn")), "+ round1")
