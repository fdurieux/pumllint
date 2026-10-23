#!/usr/bin/env bash
# Score one recreation arm: differential run, compare against the frozen
# reference, the seam check (M8) and the replayed original tests (M9).
#   run_arm.sh <ARM> <arm_out_dir> <venv> <results_dir>
set -uo pipefail
ARM=$1; OUT=$2; VENV=$3; RES=$4
S=/tmp/claude-0/-home-user/2ad689ab-3a24-5b0f-9348-2331660d6b34/scratchpad
H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$RES"
. "$VENV/bin/activate"
VIRTUAL_ENV="$VENV" uv pip install -q --offline -e "$OUT" 2>&1 | tail -1
echo "== run_impl ($ARM)"
PYTHONPATH="$OUT" python "$H/run_impl.py" --adapter adapter_rc --exe jef-data-rc \
    --chain "$OUT/daily-rc.sh" --inputs "$S/inputs" --out "$RES/run" 2>&1 | grep -v ": ok" | tail -30
echo "== compare"
python "$H/compare.py" "$S/ref_run1" "$RES/run" --out "$RES/compare.json" | tail -70
echo "== M8"
deactivate; . /home/user/.jf-venv/bin/activate
if [[ -f "$RES/run/s18_import_export/export_yahoo_AAPL.frame.csv" ]]; then
  python "$H/seam_check.py" "$RES/run/s18_import_export/export_yahoo_AAPL.frame.csv" /home/user/J-F/experiments/AAPL.csv | tee "$RES/m8.txt"
else
  echo "M8 FAIL: no exported frame produced" | tee "$RES/m8.txt"
fi
echo "== M9"
mkdir -p "$RES/chain_rc" && cp "$OUT/daily-rc.sh" "$RES/chain_rc/daily.sh" && cp /home/user/J-F/deploy/events.sh /home/user/J-F/deploy/dashboard.sh "$RES/chain_rc/"
python "$H/m9_run_original_tests.py" --jf /home/user/J-F --rc-pkg jef_data_rc --rc-chain "$RES/chain_rc/daily.sh" \
    --python "$VENV/bin/python" --extra-path "$OUT" --out "$RES/m9.json" 2>&1 | tail -8
echo "== kit suite on the arm (M10, our own run)"
deactivate; . "$VENV/bin/activate"
KIT=$S/arms/$ARM/kit
( cd "$KIT" && JDL_UNDER_TEST=jef-data-rc JDL_CHAIN="$OUT/daily-rc.sh" JDL_ADAPTER=adapter_rc PYTHONPATH="$OUT" \
  python -m pytest -q -p no:cacheprovider --basetemp="$RES/pytest-tmp" features/steps 2>&1 | tail -3 | tee "$RES/m10.txt" )
