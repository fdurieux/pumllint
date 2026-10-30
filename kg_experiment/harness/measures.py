"""M3 keyword sets (frozen in the pre-registration §8), M5 reference
resolution, and the suite runner for M4."""

from __future__ import annotations

import base64
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from kitio import REPO

FLAG_WORDS = {
    "S1": [],
    "S2": ["outage", "unavailable", "od-1", "not yet specified", "req-06"],
    "S3": ["forties", "sixties", "boundary", "threshold", "ambigu", "exact value"],
    "S4": ["contradict", "conflict", "disagree", "inconsisten"],
    "S5": ["inferred", "unverified", "auto-generated", "assistant", "not reviewed"],
    "S6": ["invalidat", "re-verif", "stale", "341", "316", "suspect"],
    "S7": ["unverified", "proposed", "not verified", "blocked", "approval"],
}
# S4 and S5 need the outage named as well (pre-registration §8)
CO_WORDS = {"S4": ["outage", "unavailable"], "S5": ["outage", "unavailable"]}

TARGETS = {
    "S1": None, "S7": None,
    "S2": ["screening_down_hold"], "S4": ["screening_down_hold"], "S5": ["screening_down_hold"],
    "S3": ["accept_boundary_41", "review_boundary_42", "refuse_boundary_67"],
    "S6": ["price_exact_heavy", "price_exact_both"],
}

S6_OVERLAYS = {
    "price_exact_heavy": {"require_re": r"3211", "forbid_re": r"3186"},
    "price_exact_both": {"require_re": r"8682\.2", "forbid_re": r"8652\.4|8622\.2"},
}


def flagged(scenario: str, parsed: dict | None) -> dict:
    if not parsed:
        return {"flagged": False, "hits": [], "text_len": 0}
    text = " ".join([*(parsed.get("questions") or []),
                     *(a.get("text", "") for a in (parsed.get("assumptions") or []) if isinstance(a, dict))]).lower()
    hits = [w for w in FLAG_WORDS[scenario] if w in text]
    co = CO_WORDS.get(scenario)
    ok = bool(hits) and (not co or any(w in text for w in co))
    return {"flagged": ok, "hits": hits, "co_hit": (any(w in text for w in co) if co else None), "text_len": len(text)}


def resolvable_refs(arm: str, parsed: dict | None, bundle_ids: set[str], kit: dict[str, str]) -> dict:
    if not parsed:
        return {"total": 0, "resolved": 0, "share": None}
    refs = [x.get("ref", "") for k in ("claims", "assumptions") for x in (parsed.get(k) or []) if isinstance(x, dict)]
    total = len(refs)
    ok = 0
    for ref in refs:
        ref = (ref or "").strip()
        if arm == "G":
            if ref in bundle_ids or ref.split("@")[0] in {b.split("@")[0] for b in bundle_ids}:
                ok += 1
        else:
            m = re.match(r"([\w./-]+):(\d+)", ref)
            if m and m.group(1) in kit and 1 <= int(m.group(2)) <= kit[m.group(1)].count("\n") + 1:
                ok += 1
    return {"total": total, "resolved": ok, "share": (ok / total) if total else None}


# ------------------------------------------------------------ the suite

def _smoke():
    spec = importlib.util.spec_from_file_location("smoke_test", REPO / "stack_experiment" / "smoke_test.py")
    mod = importlib.util.module_from_spec(spec)
    sys.argv = [str(REPO / "stack_experiment" / "smoke_test.py")]
    spec.loader.exec_module(mod)
    return mod


def run_suite(code: str | None, scenario: str) -> dict:
    """pass/total over the 11 scenarios, with S6's recomputed overlays."""
    if not code:
        return {"ran": False, "passed": 0, "total": 11, "per_scenario": {}}
    smoke = _smoke()
    suite = smoke.suite_mod
    overlays = dict(suite.OVERLAYS)
    if scenario == "S6":
        overlays.update(S6_OVERLAYS)
    with tempfile.TemporaryDirectory() as td:
        art = Path(td) / "artifact.py"
        art.write_text(code, encoding="utf-8")
        per = {}
        for name in suite.SUITE["scenarios"]:
            res = smoke.run_child(art, smoke.build_spec(name))
            ov = overlays.get(name)
            if ov and res.get("passed"):
                detail = (res.get("detail") or "").lower()
                if ov.get("require_re") and not re.search(ov["require_re"], detail):
                    res.update(passed=False, stage="wrong_outcome", detail="overlay-require: " + detail)
                elif ov.get("forbid_re") and re.search(ov["forbid_re"], detail):
                    res.update(passed=False, stage="wrong_outcome", detail="overlay-forbid: " + detail)
            per[name] = {"passed": bool(res.get("passed")), "stage": res.get("stage"), "detail": (res.get("detail") or "")[:200]}
    return {"ran": True, "passed": sum(1 for v in per.values() if v["passed"]), "total": len(per), "per_scenario": per}


def outage_status(suite_result: dict) -> str | None:
    """What the code returned on screening_down_hold, read from the runner detail."""
    d = suite_result.get("per_scenario", {}).get("screening_down_hold", {}).get("detail", "")
    m = re.search(r"'status': '([^']+)'", d) or re.search(r'"status": "([^"]+)"', d)
    return m.group(1) if m else (d[:80] or None)
