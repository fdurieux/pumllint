#!/bin/bash
# grade_arm.sh ARM DIR : the harness run, compare (M1-M7), M8, the arm's own kit suite (R4), the pristine suite (R5)
L=/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/lab; H=/home/user/pumllint/recreate_experiment/harness
ARM=$1; D=$2; OUT=$D/out; KIT=$D/kit; R=$L/grade/arms/$ARM; mkdir -p "$R"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_CORETYPE=HASWELL NPY_DISABLE_CPU_FEATURES=X86_V4
. "$D/venv/bin/activate"
{ echo "jef-data-rc: $(command -v jef-data-rc)"; python -c "import jef_data_rc, sys; print('package:', jef_data_rc.__file__)"; } > "$R/install.txt" 2>&1
PYTHONPATH="$OUT" python "$H/run_impl.py" --adapter adapter_rc --exe jef-data-rc --chain "$OUT/daily-rc.sh" \
  --inputs "$L/inputs" --out "$R/run" > "$R/run.log" 2>&1
python "$H/compare.py" "$L/grade/ref" "$R/run" --out "$R/compare.json" > "$R/compare.txt" 2>&1
( . /home/user/.jf-venv/bin/activate; if [[ -f "$R/run/s18_import_export/export_yahoo_AAPL.frame.csv" ]]; then
    python "$H/seam_check.py" "$R/run/s18_import_export/export_yahoo_AAPL.frame.csv" /home/user/J-F/experiments/AAPL.csv > "$R/m8.txt" 2>&1
  else echo "M8 FAIL: no exported frame produced" > "$R/m8.txt"; fi )
( cd "$KIT" && JDL_UNDER_TEST=jef-data-rc JDL_CHAIN="$OUT/daily-rc.sh" JDL_ADAPTER=adapter_rc PYTHONPATH="$OUT" \
  python -m pytest -q -p no:cacheprovider -rf --basetemp="$R/pt-own" features/steps > "$R/r4.txt" 2>&1 )
rm -rf "$R/pristine_kit" && cp -a "$L/kit_ref" "$R/pristine_kit" && find "$R/pristine_kit" -name __pycache__ -prune -exec rm -rf {} +
( cd "$R/pristine_kit" && JDL_UNDER_TEST=jef-data-rc JDL_CHAIN="$OUT/daily-rc.sh" JDL_ADAPTER=adapter_rc PYTHONPATH="$OUT" \
  python -m pytest -q -p no:cacheprovider -rf --basetemp="$R/pt-pristine" features/steps > "$R/r5.txt" 2>&1 )
( cd "$KIT" && python tools/manifest.py --check > "$R/kit_manifest.txt" 2>&1 )
echo "$ARM: run $(ls "$R/run" | wc -l) scenarios; R4 $(tail -1 "$R/r4.txt"); R5 $(tail -1 "$R/r5.txt"); $(head -1 "$R/m8.txt" | cut -c1-80)"
