"""Smoke-test the CargoQuote acceptance suite end-to-end, without API spend.

The deterministic half of the house calibration protocol, runnable at
any time:

    python stack_experiment/smoke_test.py

1. Runs the hand-written reference implementation (reference_impl.py)
   through the sandboxed runner (tools/acceptance/runner_child.py,
   unchanged) for all 11 scenarios of
   tools/acceptance/cargo_quote_suite.py, overlays applied — expects
   11/11 pass.
2. Runs three PRIOR-FOLLOWING MUTANTS of the reference — each encoding
   the guess a generator's priors would make against one adversarial
   rule — and asserts each fails EXACTLY its targeted scenario set and
   nothing else. This is the suite's teeth check: the adversarial
   thresholds are only adversarial if the canonical guess measurably
   fails.

Exit 0 iff every expectation holds. Generation-calibration (pristine
generated artifacts) still runs at W1 pre-registration before the
suite freezes — this script does not replace it.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "tools"))

from acceptance import cargo_quote_suite as suite_mod  # noqa: E402

CHILD = REPO / "tools" / "acceptance" / "runner_child.py"
REFERENCE = HERE / "cargo_quote" / "reference_impl.py"
TIMEOUT_S = 15

# Each mutant: (name, [(old, new), ...] source patches, expected-fail set).
# A patch that matches nothing is a hard error — mutants must mutate.
MUTANTS = [
    (
        "prior_error_on_screening_outage",
        [(
            """        except ScreeningUnavailableError:
            price = self.engine.price(weight, distance)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "price": price,
                    "hold": True, "quote_id": quote_id}""",
            """        except ScreeningUnavailableError:
            return {"status": "error: screening_unavailable",
                    "quote_id": quote_id}""",
        )],
        {"screening_down_hold"},
    ),
    (
        "canonical_accept_threshold_70",
        [("ACCEPT_MAX = 41", "ACCEPT_MAX = 70")],
        {"review_boundary_42", "refuse_boundary_67"},
    ),
    (
        "inverted_surcharge_order",
        [(
            """        if weight_kg > HEAVY_LIMIT_KG:
            total += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_MIN_KM:
            total *= LONGHAUL_FACTOR""",
            """        if distance_km >= LONGHAUL_MIN_KM:
            total *= LONGHAUL_FACTOR
        if weight_kg > HEAVY_LIMIT_KG:
            total += HEAVY_SURCHARGE""",
        )],
        {"price_exact_both"},
    ),
]


def build_spec(scenario: str) -> dict:
    fam = suite_mod.SUITE
    sc = fam["scenarios"][scenario]
    return {
        "family": "cargo_quote", "scenario": scenario,
        "lexicons": fam["lexicons"],
        "entry_cls_like": fam["entry_cls_like"],
        "entry_cls_fallback": fam["entry_cls_fallback"],
        "entry_method_like": fam["entry_method_like"],
        "entry_func_like": fam["entry_func_like"],
        "args": fam["args"],
        "stubs": sc.get("stubs", []),
        "expect": sc["expect"],
        "failure_like": sc.get("failure_like", []),
        "must_call": sc.get("must_call", []),
        "must_not_call": sc.get("must_not_call", []),
        "request": sc.get("request", {}),
        "check_calls": True,
    }


def run_child(artifact: Path, spec: dict) -> dict:
    payload = base64.b64encode(json.dumps(spec).encode()).decode()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(CHILD), str(artifact), payload],
            capture_output=True, text=True, timeout=TIMEOUT_S,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return {"stage": "timeout", "passed": False, "detail": "killed"}
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return {"stage": "harness_error", "passed": False,
                "detail": (proc.stderr or "no output")[:300]}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"stage": "harness_error", "passed": False,
                "detail": ("unparseable: " + lines[-1])[:300]}


def apply_overlay(scenario: str, res: dict) -> dict:
    ov = suite_mod.OVERLAYS.get(scenario)
    if not ov or not res.get("passed"):
        return res
    detail = (res.get("detail") or "").lower()
    require, forbid = ov.get("require_re"), ov.get("forbid_re")
    if require and not re.search(require, detail):
        res.update(passed=False, stage="wrong_outcome",
                   detail=f"overlay-require({require}): " + detail)
    elif forbid and re.search(forbid, detail):
        res.update(passed=False, stage="wrong_outcome",
                   detail=f"overlay-forbid({forbid}): " + detail)
    return res


def run_artifact(artifact: Path) -> dict:
    rows = {}
    for scen in suite_mod.SUITE["scenarios"]:
        rows[scen] = apply_overlay(scen, run_child(artifact, build_spec(scen)))
    return rows


def main() -> int:
    failures = 0

    print("== reference implementation ==")
    rows = run_artifact(REFERENCE)
    for scen, res in rows.items():
        mark = "PASS" if res.get("passed") else "FAIL"
        print(f"  {mark}  {scen:24s} [{res.get('stage')}] {res.get('detail', '')[:90]}")
        if not res.get("passed"):
            failures += 1
    print(f"  -> {sum(1 for r in rows.values() if r.get('passed'))}/{len(rows)} passed (expected {len(rows)}/{len(rows)})")

    src = REFERENCE.read_text()
    with tempfile.TemporaryDirectory() as td:
        for name, patches, expected_fail in MUTANTS:
            mutated = src
            for old, new in patches:
                if old not in mutated:
                    print(f"  ERROR mutant {name}: patch target not found")
                    return 1
                mutated = mutated.replace(old, new)
            mpath = Path(td) / f"mutant_{name}.py"
            mpath.write_text(mutated)
            rows = run_artifact(mpath)
            failed = {s for s, r in rows.items() if not r.get("passed")}
            verdict = "OK " if failed == expected_fail else "BAD"
            print(f"== mutant {name} ==")
            print(f"  {verdict} failed={sorted(failed)} expected={sorted(expected_fail)}")
            if failed != expected_fail:
                for s in sorted(failed ^ expected_fail):
                    r = rows[s]
                    print(f"       {s}: [{r.get('stage')}] {r.get('detail', '')[:120]}")
                failures += 1

    print("SMOKE", "FAILED" if failures else "PASSED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
