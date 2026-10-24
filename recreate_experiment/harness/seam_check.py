"""M8: does an implementation's exported seam frame survive the ORIGINAL's
loader bit-exactly against the committed CSV? Usage (in the J-F venv):
    seam_check.py <export_frame.csv from run_impl> <experiments/AAPL.csv>"""
import sys
import pandas as pd
from jef.binning.loading import load_eod_csv

a = load_eod_csv(sys.argv[1], symbol="AAPL")
b = load_eod_csv(sys.argv[2], symbol="AAPL")
try:
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    print("M8 PASS: exported seam frame routes bit-identically through the original loader", len(a), "rows")
except AssertionError as exc:
    print("M8 FAIL:", str(exc)[:600])
    sys.exit(1)
