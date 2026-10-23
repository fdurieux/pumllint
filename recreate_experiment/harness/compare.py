"""Compare two run_impl.py output trees (reference first) and compute the
pre-registered metrics. Usage: compare.py REF RC --out report.json"""
import argparse
import io
import json
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("ref")
ap.add_argument("rc")
ap.add_argument("--out", required=True)
args = ap.parse_args()
REF, RC = Path(args.ref), Path(args.rc)

VOLATILE_KEYS = {"last_updated"}


def strip(obj):
    if isinstance(obj, dict):
        return {k: strip(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [strip(v) for v in obj]
    return obj


def load_json(p):
    return strip(json.loads(p.read_text()))


def frame_diff(a_text, b_text):
    a = pd.read_csv(io.StringIO(a_text), dtype=str, keep_default_na=False)
    b = pd.read_csv(io.StringIO(b_text), dtype=str, keep_default_na=False)
    info = {"rows": [len(a), len(b)], "columns_equal": list(a.columns) == list(b.columns)}
    if set(a.columns) != set(b.columns):
        info["column_set_differs"] = sorted(set(a.columns) ^ set(b.columns))
    common = [c for c in a.columns if c in b.columns]
    n = min(len(a), len(b))
    cells = 0
    percol = {}
    for c in common:
        d = int((a[c].values[:n] != b[c].values[:n]).sum())
        if d:
            percol[c] = d
        cells += d
    cells += abs(len(a) - len(b)) * len(common)
    info["cells_differ"] = cells
    info["per_column"] = percol
    return info


rows = []
metrics = {"M1_export_identical": [0, 0], "M2_gate_inversions_rc_green_ref_red": 0,
           "M3_gate_inversions_rc_red_ref_green": 0, "M4_status_identical": [0, 0],
           "M4_status_same_verdicts": 0, "M5_summary_identical": [0, 0],
           "M6_stored_identical": [0, 0], "M6_actions_identical": [0, 0],
           "M7_cli_exit_identical": [0, 0], "M7_cli_text_identical": [0, 0],
           "M7_chain_exit_identical": [0, 0], "M7_chain_calls_identical": [0, 0],
           "other_identical": [0, 0], "missing_in_rc": 0, "scenario_errors_rc": [],
           # post-hoc (2026-10-23, after Arm K's first comparison; not pre-registered):
           # the same CLI outcome = same exit code and same final stderr line (a
           # traceback's file paths and line numbers differ by construction);
           # equivalent chain calls = same commands and arguments once an inline
           # `python3 -c` script is reduced to its presence.
           "M7post_cli_same_outcome": [0, 0], "M7post_chain_calls_equivalent": [0, 0]}


def last_line(text):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def reduce_calls(calls):
    out = []
    for c in calls or []:
        parts = c.split(" ", 2)
        if len(parts) >= 2 and parts[0] == "python3" and parts[1] == "-c":
            out.append("python3 -c <script>")
        else:
            out.append(c)
    return out

for ref_file in sorted(REF.rglob("*")):
    if not ref_file.is_file() or ref_file.name == "MANIFEST.sha256.json":
        continue
    rel = ref_file.relative_to(REF).as_posix()
    rc_file = RC / rel
    row = {"artefact": rel}
    if not rc_file.exists():
        row["verdict"] = "missing"
        metrics["missing_in_rc"] += 1
        err = RC / rel.split("/")[0] / "error.json"
        if err.exists():
            e = json.loads(err.read_text())
            row["rc_error"] = f"{e['type']}: {e['message']}"
        rows.append(row)
        continue
    name = ref_file.name
    if name.endswith(".frame.csv"):
        a, b = ref_file.read_text(), rc_file.read_text()
        same = a == b
        key = "M1_export_identical" if name.startswith("export_") else "M6_stored_identical"
        metrics[key][1] += 1
        metrics[key][0] += same
        row["verdict"] = "identical" if same else "differs"
        if not same:
            row["diff"] = frame_diff(a, b)
    elif name.endswith(".json"):
        a, b = load_json(ref_file), load_json(rc_file)
        same = a == b
        row["verdict"] = "identical" if same else "differs"
        if name.startswith("status"):
            metrics["M4_status_identical"][1] += 1
            metrics["M4_status_identical"][0] += same
            ea, eb = a.get("exit"), b.get("exit")
            if ea == 1 and eb == 0:
                metrics["M2_gate_inversions_rc_green_ref_red"] += 1
                row["gate"] = "INVERSION rc green / ref red"
            elif ea == 0 and eb == 1:
                metrics["M3_gate_inversions_rc_red_ref_green"] += 1
                row["gate"] = "inversion rc red / ref green"
            if not same:
                def verdicts(d):
                    out = []
                    for r in d.get("document", {}).get("reports", []) + d.get("document", {}).get("pairs", []):
                        out.append((r.get("alerts"), r.get("warnings"), r.get("notes")))
                    return out
                if verdicts(a) == verdicts(b):
                    metrics["M4_status_same_verdicts"] += 1
                    row["verdict"] = "differs (same verdicts, values/wording differ)"
        elif name.startswith("sync_summary"):
            metrics["M5_summary_identical"][1] += 1
            metrics["M5_summary_identical"][0] += same
        elif name.startswith("actions_"):
            metrics["M6_actions_identical"][1] += 1
            metrics["M6_actions_identical"][0] += same
        elif name.startswith("cli_"):
            metrics["M7_cli_exit_identical"][1] += 1
            metrics["M7_cli_exit_identical"][0] += (a.get("exit") == b.get("exit"))
            metrics["M7_cli_text_identical"][1] += 1
            metrics["M7_cli_text_identical"][0] += same
            if a.get("exit") != b.get("exit"):
                row["exit"] = [a.get("exit"), b.get("exit")]
            metrics["M7post_cli_same_outcome"][1] += 1
            same_out = a.get("exit") == b.get("exit") and last_line(a.get("stderr")) == last_line(b.get("stderr")) and (a.get("stdout") == b.get("stdout") or name.startswith("cli_help"))
            metrics["M7post_cli_same_outcome"][0] += same_out
            if not same and same_out:
                row["verdict"] = "differs (same exit and final message; help/usage prose or traceback paths differ)"
        elif name.startswith("chain_"):
            metrics["M7_chain_exit_identical"][1] += 1
            metrics["M7_chain_exit_identical"][0] += (a.get("exit") == b.get("exit"))
            metrics["M7_chain_calls_identical"][1] += 1
            metrics["M7_chain_calls_identical"][0] += (a.get("calls") == b.get("calls"))
            metrics["M7post_chain_calls_equivalent"][1] += 1
            eq = reduce_calls(a.get("calls")) == reduce_calls(b.get("calls"))
            metrics["M7post_chain_calls_equivalent"][0] += eq
            if not same and eq and a.get("exit") == b.get("exit"):
                row["verdict"] = "differs (equivalent calls; inline python text or script path differs)"
        else:
            metrics["other_identical"][1] += 1
            metrics["other_identical"][0] += same
    else:
        same = ref_file.read_bytes() == rc_file.read_bytes()
        metrics["other_identical"][1] += 1
        metrics["other_identical"][0] += same
        row["verdict"] = "identical" if same else "differs"
    rows.append(row)

for err in sorted(RC.glob("*/error.json")):
    e = json.loads(err.read_text())
    metrics["scenario_errors_rc"].append(f"{err.parent.name}: {e['type']}: {e['message']}")

report = {"metrics": metrics, "artefacts": rows}
Path(args.out).write_text(json.dumps(report, indent=1))
print(json.dumps(metrics, indent=1))
diffs = [r for r in rows if r.get("verdict") != "identical"]
print(f"{len(rows)} artefacts compared, {len(diffs)} not identical")
for r in diffs[:60]:
    print(" -", r["artefact"], r.get("verdict"), r.get("gate", ""), r.get("rc_error", ""))
