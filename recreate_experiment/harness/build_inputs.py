"""Build the HIDDEN scenario inputs from the subject's recorded fixtures and the
committed Yahoo CSV: fixture directories (base + derived variants) and universe
files. Never shipped in a kit. Usage: build_inputs.py <jf_checkout> <inputs_dir>"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

JF, OUT = Path(sys.argv[1]), Path(sys.argv[2])
FIX = JF / "tests" / "data" / "fixtures"


def key_of(method, path, params):
    return {"method": method, "path": path,
            "params": {k: str(v) for k, v in sorted(params.items())}}


def filename(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:10]
    return f"{slug}_{digest}.json"


def load(rel):
    return json.loads((FIX / rel).read_text(encoding="utf-8"))


def write(dirname, fixtures):
    d = OUT / "fixtures" / dirname
    d.mkdir(parents=True, exist_ok=True)
    for fx in fixtures:
        (d / filename(fx["request"])).write_text(
            json.dumps(fx, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def derived(base, params=None, mutate=None):
    fx = json.loads(json.dumps(base))
    if params is not None:
        fx["request"] = key_of(fx["request"]["method"], fx["request"]["path"], params)
    if mutate:
        mutate(fx["response"]["json"])
    return fx


if OUT.exists():
    shutil.rmtree(OUT)
(OUT / "fixtures").mkdir(parents=True)

eod_tlt = load("eodhd/api_eod_TLT.US_edd719cfd3.json")
eod_aapl = load("eodhd/api_eod_AAPL.US_66d5d562b5.json")
eod_btc = load("eodhd/api_eod_BTC-USD.CC_6d815a7907.json")
spl_tlt = load("eodhd/api_splits_TLT.US_79cb33ab8f.json")
spl_aapl = load("eodhd/api_splits_AAPL.US_13e2ff1ebd.json")
div_tlt = load("eodhd/api_div_TLT.US_b364779dc7.json")
div_aapl = load("eodhd/api_div_AAPL.US_aa39d6f2e3.json")
kl_btc = load("binance/api_v3_klines_f310efd00e.json")

base_eodhd = [eod_tlt, eod_btc, spl_tlt, div_tlt]
# AAPL's dividends were recorded with a window; the sync ritual asks windowless.
div_aapl_windowless = derived(div_aapl, params={"fmt": "json"})
write("base/eodhd", base_eodhd + [eod_aapl, spl_aapl, div_aapl_windowless])
write("base/binance", [kl_btc])


def revise_tlt(bars):
    bars[-1]["close"] = round(bars[-1]["close"] + 1.0, 4)      # 2020-03-13 close
    bars[-2]["volume"] = int(bars[-2]["volume"]) + 1000         # 2020-03-12 volume
write("tlt_revised/eodhd", [derived(eod_tlt, mutate=revise_tlt), spl_tlt, div_tlt])


def jump_tlt(bars):
    bars[6]["close"] = round(bars[6]["close"] * 2.0, 4)         # 2020-03-10: +100 %
write("tlt_jump/eodhd", [derived(eod_tlt, mutate=jump_tlt), spl_tlt, div_tlt])


def btc_tail(bars):
    del bars[:3]                                                 # keep 01-04, 01-05
    bars[-1]["close"] = round(bars[-1]["close"] * 1.01, 2)
write("btc_tail2/eodhd", [derived(eod_btc, params={"fmt": "json", "from": "2024-01-04",
                                                   "order": "a", "period": "d",
                                                   "to": "2024-01-05"},
                                  mutate=btc_tail)])


def zero_vol(bars):
    bars[1]["volume"] = 0
    bars[2]["volume"] = 0
write("btc_zero_volume/eodhd", [derived(eod_btc, mutate=zero_vol)])

# ---- universes -------------------------------------------------------------
U = OUT / "universes"
U.mkdir()
AAPL_CSV = (JF / "experiments" / "AAPL.csv").as_posix()

TLT = """
[[asset]]
name = "TLT"
asset_class = "bond_etf"
  [[asset.source]]
  provider = "eodhd"
  symbol = "TLT.US"
  start = 2020-03-02
  end = 2020-03-13
"""
BTC2 = """
[[asset]]
name = "BTC"
asset_class = "crypto"
  [[asset.source]]
  provider = "eodhd"
  symbol = "BTC-USD.CC"
  modeled = true
  start = 2024-01-01
  end = 2024-01-05
  [[asset.source]]
  provider = "binance"
  symbol = "BTCUSDT"
  start = 2024-01-01
  end = 2024-01-05
"""
AAPL_CSV_SRC = f"""
[[asset]]
name = "AAPL"
asset_class = "stock"
  [[asset.source]]
  provider = "yahoo-csv"
  path = "{AAPL_CSV}"
  symbol = "AAPL"
"""
universes = {
    "r1": TLT + BTC2 + AAPL_CSV_SRC,
    "tlt": TLT,
    "paused_tlt": TLT.replace('asset_class = "bond_etf"', 'asset_class = "bond_etf"\nenabled = false') + BTC2,
    "aapl_eod": """
[[asset]]
name = "AAPL"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "AAPL.US"
  modeled = true
  start = 2020-08-24
  end = 2020-09-04
""",
    "btc_noend": """
[[asset]]
name = "BTC"
asset_class = "crypto"
  [[asset.source]]
  provider = "eodhd"
  symbol = "BTC-USD.CC"
  modeled = true
  start = 2024-01-01
""",
    "btc_end03": """
[[asset]]
name = "BTC"
asset_class = "crypto"
  [[asset.source]]
  provider = "eodhd"
  symbol = "BTC-USD.CC"
  modeled = true
  start = 2024-01-01
  end = 2024-01-03
""",
    "tlt_misdeclared": TLT.replace('"bond_etf"', '"stock"'),
    # refusal variants (parse-time)
    "bad_modeled_disabled": """
[[asset]]
name = "X"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
  modeled = true
  enabled = false
""",
    "bad_two_modeled": """
[[asset]]
name = "X"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
  modeled = true
  [[asset.source]]
  provider = "binance"
  symbol = "XUSDT"
  modeled = true
""",
    "bad_no_enabled_source": """
[[asset]]
name = "X"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
  enabled = false
""",
    "bad_unknown_key": """
[[asset]]
name = "X"
asset_class = "stock"
colour = "blue"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
""",
    "bad_date": """
[[asset]]
name = "X"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
  start = "not-a-date"
""",
    "bad_provider": """
[[asset]]
name = "X"
asset_class = "stock"
  [[asset.source]]
  provider = "bloomberg"
  symbol = "X"
""",
    "bad_class": """
[[asset]]
name = "X"
asset_class = "tulip"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
""",
    "bad_kind": """
[[asset]]
name = "X"
asset_class = "stock"
kind = "intraday"
  [[asset.source]]
  provider = "eodhd"
  symbol = "X.US"
""",
    "bad_csv_no_path": """
[[asset]]
name = "X"
asset_class = "stock"
  [[asset.source]]
  provider = "yahoo-csv"
  symbol = "X"
""",
    "bad_dup_asset": TLT + TLT,
    "bad_toml": "[[asset]\nname = ",
}
for name, text in universes.items():
    (U / f"{name}.toml").write_text(text.lstrip(), encoding="utf-8")

# a deliberately broken Yahoo CSV for the validate refusal
(OUT / "bad.csv").write_text("Date,Open,High,Low,Close,Volume\n2020-01-02,1,2,0.5,1.5,100\n",
                             encoding="utf-8")
(OUT / "aapl_csv_path.txt").write_text(AAPL_CSV, encoding="utf-8")
manifest = {}
for p in sorted(OUT.rglob("*")):
    if p.is_file():
        manifest[p.relative_to(OUT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
(OUT / "INPUTS.sha256.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print(f"inputs: {len(manifest)} files under {OUT}")
