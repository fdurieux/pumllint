"""M9: run the SUBJECT's own in-scope test modules against a recreation, through
an import shim that aliases `jef.data.<module>` to `<rc_pkg>.<module>` where a
module of that name exists. Reported, never gated: a recreation that named its
modules differently fails at import, and that is the measurement.

    m9_run_original_tests.py --jf <J-F checkout> --rc-pkg jef_data_rc \
        --rc-chain <daily-rc.sh> --python <venv python> --out report.json
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--jf", required=True)
ap.add_argument("--rc-pkg", required=True)
ap.add_argument("--rc-chain", required=True)
ap.add_argument("--python", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--extra-path", default="", help="extra PYTHONPATH entries (os.pathsep-joined) where the rc package lives")
args = ap.parse_args()
JF = Path(args.jf)

API_MODULES = ["test_actions_store", "test_adjust", "test_binance_collector",
               "test_classification", "test_contract", "test_differential",
               "test_eodhd_collector", "test_health", "test_rate_limiter",
               "test_store", "test_store_reconcile", "test_store_robustness",
               "test_sync", "test_universe_config"]
# Not applicable through the shim, on the ORIGINAL too (measured 2026-10-23):
# three health tests inspect other source homes (jef.api, deploy/, docs/) for
# knob consistency, test_pilot_universe needs jef.binning, and the chain's
# ledger test needs `python3 -m jef.events`, which no recreation venv has.
DESELECT = ["tests/data/test_health.py::test_every_health_knob_has_one_calibrated_value_in_every_home",
            "tests/data/test_health.py::test_the_resolution_knobs_have_one_set_of_defaults",
            "tests/data/test_health.py::test_no_call_site_overrides_a_calibrated_knob",
            "tests/test_daily_chain.py::test_red_day_still_writes_the_ledger"]
BLACKBOX_MODULES = ["test_daily_chain"]
SUBMODULES = ["actions", "adjust", "classification", "cli", "collectors",
              "collectors.base", "collectors.eodhd", "collectors.binance",
              "contract", "differential", "health", "store", "sync", "universe"]

work = Path(tempfile.mkdtemp(prefix="m9-"))
shim = work / "shim" / "jef"
(shim / "data").mkdir(parents=True)
(shim / "__init__.py").write_text("")
(shim / "data" / "__init__.py").write_text(f'''
"""Import shim: jef.data.<m> -> {args.rc_pkg}.<m> when such a module exists."""
import importlib, sys
_RC = "{args.rc_pkg}"
_rc = importlib.import_module(_RC)
for _name in {SUBMODULES!r}:
    try:
        _mod = importlib.import_module(_RC + "." + _name)
    except Exception:
        continue
    sys.modules["jef.data." + _name] = _mod
    if "." not in _name:
        globals()[_name] = _mod
for _k in dir(_rc):
    if not _k.startswith("_"):
        globals().setdefault(_k, getattr(_rc, _k))
''')
# a subpackage path entry so `import jef.data.collectors.eodhd` resolves via sys.modules
tests = work / "tests"
(tests / "data").mkdir(parents=True)
shutil.copy(JF / "tests" / "conftest.py", tests / "conftest.py")
shutil.copy(JF / "tests" / "data" / "conftest.py", tests / "data" / "conftest.py")
shutil.copytree(JF / "tests" / "data" / "fixtures", tests / "data" / "fixtures")
shutil.copytree(JF / "tests" / "fixtures", tests / "fixtures")
shutil.copytree(JF / "experiments", work / "experiments", ignore=shutil.ignore_patterns("*.txt", "*.R", "*.py"))
(work / "tools").mkdir()
for m in API_MODULES:
    shutil.copy(JF / "tests" / "data" / f"{m}.py", tests / "data" / f"{m}.py")
chain_test = (JF / "tests" / "test_daily_chain.py").read_text()
chain_test = re.sub(r'DAILY = ROOT / "deploy" / "daily.sh"', f'DAILY = "{args.rc_chain}"', chain_test)
(tests / "test_daily_chain.py").write_text(chain_test)
# the root conftest pins the numeric runtime and ROOT; tests/data/conftest derives ROOT from its own path
report = {"work": str(work), "modules": {}}


def run(paths, label):
    xml = work / f"{label}.xml"
    p = subprocess.run([args.python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--continue-on-collection-errors",
                        f"--junitxml={xml}", "-o", "junit_family=xunit2",
                        *[a for d in DESELECT for a in ("--deselect", d)], *paths],
                       cwd=work, capture_output=True, text=True,
                       env={"PYTHONPATH": str(work / "shim") + (":" + args.extra_path if args.extra_path else ""), "PATH": "/usr/bin:/bin:" + str(Path(args.python).parent),
                            "HOME": str(work)})
    import xml.etree.ElementTree as ET
    per = {}
    if xml.exists():
        for case in ET.parse(xml).getroot().iter("testcase"):
            mod = Path(case.get("classname", "").replace(".", "/")).name or case.get("file", "?")
            d = per.setdefault(mod, {"passed": 0, "failed": 0, "error": 0, "skipped": 0})
            if case.find("failure") is not None:
                d["failed"] += 1
            elif case.find("error") is not None:
                d["error"] += 1
            elif case.find("skipped") is not None:
                d["skipped"] += 1
            else:
                d["passed"] += 1
    # collection errors appear as <testcase> under the module with an <error>; also catch the summary line
    tail = "\n".join(p.stdout.splitlines()[-6:])
    return {"per_module": per, "summary_tail": tail, "collection_errors": p.stdout.count("ERROR collecting")}


report["api_level"] = run([f"tests/data/{m}.py" for m in API_MODULES], "api")
report["black_box"] = run(["tests/test_daily_chain.py"], "chain")
for k in ("api_level", "black_box"):
    tot = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for d in report[k]["per_module"].values():
        for kk in tot:
            tot[kk] += d[kk]
    report[k]["total"] = tot
Path(args.out).write_text(json.dumps(report, indent=1))
print(json.dumps({k: report[k]["total"] for k in ("api_level", "black_box")}, indent=1))
print(report["api_level"]["summary_tail"])
print(report["black_box"]["summary_tail"])
