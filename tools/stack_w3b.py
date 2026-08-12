"""W3b carrier x prompt-frame factorial: how much of W3's carrier
ordering is intrinsic, and how much was carried by the frozen prompt's
PlantUML-typed frame?

Protocol, pre-registered expectations and interpretation matrix:
stack_experiment/W3B_PREREGISTRATION.md (verified revision; --wave
refuses to start until that file is frozen and owner go recorded —
--confirm-frozen asserts both).

Driver placement (disclosed in the pre-registration's Driver bullet):
this module IMPORTS the frozen drivers — tools/stack_ablation.py (W1:
prompt template, models, spend guard MAX_CALLS=250 / ceiling $30,
generation shim, execution path, judge) and tools/stack_variants.py
(W2-W4: the frozen W3 carrier bundles with kit-style labels) — both
untouched on disk; their pinned shas still describe what W1/W3 ran.
New here: the 14-cell job plan (5 carriers x stored/neutral frames +
4 carrier-native frames; PlantUML native == stored), the three frame
strings as module constants, the frame substitution (EXACTLY ONE
phrase in the generation-prompt template — never applied to bundle
content), the W3B results root (the $30 ceiling accounts this wave
alone), the W3b analysis block (per-cell pooled/per-generator/
flow-set rates, alignment deltas, per-frame orderings, compile
counts, judged medians, every E1-E6/G1-G3 input), and the pre-freeze
equivalence obligations as an executable mode (--prefreeze-checks,
$0, no API).

The judge prompt is NOT varied: one fixed judge frame across all 14
cells (its PlantUML typing is a disclosed limitation, as in W3); the
frame treatment is generation-side only.

Run:
  python tools/stack_w3b.py --dry-run           # plan + 14 cell
                                                # inventories + the three
                                                # frame strings, $0
  python tools/stack_w3b.py --smoke             # reference impl through
                                                # the frozen scoring path, $0
  python tools/stack_w3b.py --prefreeze-checks  # obligations (1)(2)(3), $0
  python tools/stack_w3b.py --wave --confirm-frozen   # scored wave (84 runs)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stack_ablation as sa  # noqa: E402 — the frozen W1 driver, by import
import stack_variants as sv  # noqa: E402 — the frozen W2-W4 driver, by import

REPO_ROOT = sa.REPO_ROOT
SE = REPO_ROOT / "stack_experiment"
RESULTS_W3B = SE / "results" / "W3B"
PREREG = "stack_experiment/W3B_PREREGISTRATION.md"

# ------------------------------------------------- frames (the treatment)

# The three frame strings (pre-registration, Design — frozen there and
# here; hashes of this file pinned at freeze).
FRAME_STORED = "a PlantUML UML sequence diagram"
FRAME_NEUTRAL = "a behavior interaction specification"
FRAME_NATIVE = {
    "mermaid": "a Mermaid sequence diagram",
    "yaml": "a structured YAML behavior specification",
    "controlled-english": "a controlled-English behavior specification",
    "code-stub": ("a Python skeleton of the behavior "
                  "(function stubs with docstrings)"),
}

CARRIERS = ["puml", "code-stub", "mermaid", "controlled-english", "yaml"]
ALTERNATIVES = [c for c in CARRIERS if c != "puml"]

# The substitution is well-defined only if the stored phrase occurs
# exactly once in the template and no replacement phrase pre-exists
# there (adversarial finding verified the count; asserted live so any
# drift in the frozen import aborts everything).
assert sa.GEN_PROMPT.count(FRAME_STORED) == 1, \
    "frame phrase not unique in GEN_PROMPT"
for _p in [FRAME_NEUTRAL, *FRAME_NATIVE.values()]:
    assert _p not in sa.GEN_PROMPT, f"frame phrase collides: {_p}"

# 14 cells: 5 carriers x {stored, neutral} + 4 alternatives x native
# (PlantUML native == stored — identical string, so no separate cell).
CELLS: dict[str, tuple[str, str]] = {}
for _c in CARRIERS:
    CELLS[f"{_c}-stored"] = (_c, "stored")
for _c in CARRIERS:
    CELLS[f"{_c}-neutral"] = (_c, "neutral")
for _c in ALTERNATIVES:
    CELLS[f"{_c}-native"] = (_c, "native")
CELL_ORDER = list(CELLS)
RUNS_PER_CELL = 3

# W3's frozen flow-set lens (pre-registration, Design).
FLOWSET = ["quoted_low_risk", "refuse_high_risk", "review_boundary_42",
           "screening_down_hold", "store_down_error"]


def _cell(carrier: str, frame: str) -> str:
    return f"{carrier}-{frame}"


def frame_template(carrier: str, frame: str) -> str:
    """The generation-prompt TEMPLATE for a cell: stack-bundle-v2 with
    exactly one substitution of the behavior-kind phrase. Substitution
    happens on the template BEFORE bundle insertion, so bundle content
    can never be rewritten by the frame treatment."""
    if frame == "stored":
        return sa.GEN_PROMPT
    phrase = FRAME_NEUTRAL if frame == "neutral" else FRAME_NATIVE[carrier]
    return sa.GEN_PROMPT.replace(FRAME_STORED, phrase)


def carrier_bundle_text(carrier: str) -> str:
    """The cell's bundle — the frozen assembly paths themselves:
    W1's A2 for PlantUML, W3's carrier arms (kit-style labels) else."""
    if carrier == "puml":
        return sa.bundle_text("A2")
    return sv.bundle_text("W3", carrier)


def cell_prompt(carrier: str, frame: str) -> str:
    return frame_template(carrier, frame).format(
        spec=carrier_bundle_text(carrier))


def kit_hashes() -> dict:
    files = {f"cargo_quote/{rel}" for rel in sa.ARMS["A2"]}
    for c in ALTERNATIVES:
        files |= {rel for _, rel in sv.ARMS["W3"][c]}
    h = {rel: hashlib.sha256((SE / rel).read_bytes()).hexdigest()
         for rel in sorted(files)}
    h["tools/acceptance/cargo_quote_suite.py"] = hashlib.sha256(
        sa.SUITE_FILE.read_bytes()).hexdigest()
    h["tools/acceptance/runner_child.py"] = hashlib.sha256(
        sa.CHILD.read_bytes()).hexdigest()
    return h


def prior_spend() -> float:
    """This wave's spend only (results/W3B/*) — pre-registration, Budget."""
    total = 0.0
    for rep in RESULTS_W3B.glob("*/report.json"):
        try:
            total += float(json.loads(rep.read_text())["spend_usd"])
        except Exception:  # noqa: BLE001 — unreadable report: ignore
            pass
    return round(total, 4)


# ------------------------------------------------------------- generation

def generate_one(client, short: str, cell: str, run_idx: int,
                 usage: dict, prior: float) -> dict:
    carrier, frame = CELLS[cell]
    model = sa.GEN_MODELS[short]
    prompt = cell_prompt(carrier, frame)
    attempts = []
    code, ok = "", False
    in_tok = out_tok = 0
    for _ in range(2):  # retry once on truncation / non-compiling output
        resp = sa._call(client, model, usage, prior,
                        max_tokens=sa.GEN_MAX_TOKENS, **sa._thinking(model),
                        messages=[{"role": "user", "content": prompt}])
        code = sa._strip_fences(sa._text_of(resp)).strip()
        ok, err = sa._compiles(code)
        in_tok = resp.usage.input_tokens
        out_tok = resp.usage.output_tokens
        attempts.append({"stop_reason": resp.stop_reason,
                         "compiles": ok, "error": err})
        if ok and resp.stop_reason != "max_tokens":
            break
    return {"arm": cell, "carrier": carrier, "frame": frame,
            "generator": short, "model": model, "run": run_idx,
            "code": code, "attempts": attempts, "compiles": ok,
            "input_tokens": in_tok, "output_tokens": out_tok}


def judge_one(client, carrier: str, code: str, usage: dict,
              prior: float) -> dict:
    """One fixed judge frame across all cells: JUDGE_PROMPT is never
    varied; the spec the judge sees is the cell's carrier bundle
    (frame-independent by construction)."""
    prompt = sa.JUDGE_PROMPT.format(spec=carrier_bundle_text(carrier),
                                    code=code)
    last = None
    for _ in range(2):
        resp = sa._call(
            client, sa.JUDGE_MODEL, usage, prior,
            max_tokens=sa.JUDGE_MAX_TOKENS, **sa._thinking(sa.JUDGE_MODEL),
            output_config={"format": {"type": "json_schema",
                                      "schema": sa.JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(sa._text_of(resp))
        except json.JSONDecodeError as e:
            last = e
    raise last


# ---------------------------------------------------------------- analysis

def _flow_rate(block: dict | None):
    """Flow-set rate of a _rates block: mean of the five flow-scenario
    pass rates == flow slots passed / flow slots (every scenario runs
    once per run). W3's convention; reproduced against W3's stored
    numbers in --prefreeze-checks."""
    if not block or block.get("executed") is None:
        return None
    return round(sum(sa._scen_rate(block, s) for s in FLOWSET)
                 / len(FLOWSET), 4)


def _delta(vals: dict, lo: str, hi: str):
    a, b = vals.get(lo), vals.get(hi)
    if a is None or b is None:
        return None
    return round(b - a, 4)


def analyze_w3b(runs: list[dict]) -> dict:
    cells = [c for c in CELL_ORDER if any(r["arm"] == c for r in runs)]
    pooled = {c: sa._rates(runs, c) for c in cells}
    per_gen = {s: {c: sa._rates(runs, c, s) for c in cells}
               for s in sa.GEN_MODELS}
    flow = {c: _flow_rate(pooled[c]) for c in cells}
    flow_gen = {s: {c: _flow_rate(per_gen[s][c]) for c in cells}
                for s in sa.GEN_MODELS}
    exe = {c: pooled[c]["executed"] for c in cells}
    exe_gen = {s: {c: per_gen[s][c]["executed"] for c in cells}
               for s in sa.GEN_MODELS}

    compile_counts = {c: {s: sum(1 for r in runs
                                 if r["arm"] == c and r["generator"] == s
                                 and r["compiles"])
                          for s in sa.GEN_MODELS} for c in cells}

    judged: dict = {}
    for s in sa.GEN_MODELS:
        judged[s] = {}
        for c in cells:
            counts = [len(r["judge"]["invented_business_logic"])
                      for r in runs
                      if r["arm"] == c and r["generator"] == s
                      and r.get("judge")]
            judged[s][c] = {"n": len(counts),
                            "median": median(counts) if counts else None}

    tokens = {}
    for s in sa.GEN_MODELS:
        tokens[s] = {}
        for c in cells:
            ins = [r["input_tokens"] for r in runs
                   if r["arm"] == c and r["generator"] == s]
            tokens[s][c] = round(sum(ins) / len(ins), 1) if ins else None

    # per-carrier alignment deltas (native - stored; neutral - stored)
    align: dict = {}
    for c in ALTERNATIVES:
        st, na, ne = _cell(c, "stored"), _cell(c, "native"), \
            _cell(c, "neutral")
        align[c] = {
            "native_minus_stored": {
                "pooled": _delta(exe, st, na),
                **{s: _delta(exe_gen[s], st, na) for s in sa.GEN_MODELS},
                "flow": _delta(flow, st, na)},
            "neutral_minus_stored": {
                "pooled": _delta(exe, st, ne),
                **{s: _delta(exe_gen[s], st, ne) for s in sa.GEN_MODELS},
                "flow": _delta(flow, st, ne)},
        }
    puml_frame_delta = {  # E4: neutral - stored, signed
        "pooled": _delta(exe, _cell("puml", "stored"),
                         _cell("puml", "neutral")),
        **{s: _delta(exe_gen[s], _cell("puml", "stored"),
                     _cell("puml", "neutral")) for s in sa.GEN_MODELS},
        "flow": _delta(flow, _cell("puml", "stored"),
                       _cell("puml", "neutral"))}

    def _ordering(frame: str, vals: dict) -> list | None:
        cs = [c for c in CARRIERS
              if vals.get(_cell(c, frame)) is not None]
        if not cs:
            return None
        return sorted(cs, key=lambda c: -vals[_cell(c, frame)])

    orderings = {f: {"flow": _ordering(f, flow),
                     "pooled": _ordering(f, exe)}
                 for f in ("stored", "neutral", "native")}

    # E1 / G3 deficits (positive = the alternative is BELOW PlantUML)
    def _deficits(frame: str) -> dict:
        ref = flow.get(_cell("puml", frame if frame != "native"
                             else "stored"))
        out = {}
        for c in ALTERNATIVES:
            v = flow.get(_cell(c, frame))
            out[c] = (round(ref - v, 4)
                      if ref is not None and v is not None else None)
        return out

    e1 = _deficits("neutral")
    g3 = _deficits("stored")

    expectation_inputs = {
        "E1_flow_deficits_vs_puml_neutral": e1,
        "E2a_alignment_pooled": {
            c: align[c]["native_minus_stored"]["pooled"]
            for c in ALTERNATIVES},
        "E2b_yaml_alignment_pooled":
            align.get("yaml", {}).get("native_minus_stored",
                                      {}).get("pooled"),
        "E3_opus_yaml_compiles": {
            f: compile_counts.get(_cell("yaml", f), {}).get("opus")
            for f in ("stored", "neutral", "native")},
        "E4_puml_frame_delta": puml_frame_delta,
        "E5_alignment_by_gen": {
            c: {s: align[c]["native_minus_stored"][s]
                for s in sa.GEN_MODELS} for c in ALTERNATIVES},
        "E6_judged_by_carrier": {
            c: {s: {f: judged[s].get(_cell(c, f))
                    for f in ("stored", "neutral", "native")
                    if _cell(c, f) in CELLS}
                for s in sa.GEN_MODELS} for c in CARRIERS},
        "G1_puml_stored_pooled": exe.get(_cell("puml", "stored")),
        "G2_puml_stored_by_gen": {
            s: exe_gen[s].get(_cell("puml", "stored"))
            for s in sa.GEN_MODELS},
        "G2b_puml_neutral_by_gen": {
            s: exe_gen[s].get(_cell("puml", "neutral"))
            for s in sa.GEN_MODELS},
        "G3_stored_flow_deficits_vs_puml_stored": g3,
        "G3_licensed": {c: (v is not None and v > 0.10)
                        for c, v in g3.items()},
    }

    # Cross-occasion references — run notes ONLY, never expectation
    # arithmetic (pre-registration, Design; adversarial finding 1).
    run_notes: dict = {}
    try:
        w1_an = json.loads((sa.RESULTS_ROOT / "wave_main"
                            / "analysis.json").read_text())
        w3_an = json.loads((sv.RESULTS["W3"] / "wave_main"
                            / "analysis.json").read_text())
        run_notes = {
            "stored_W1_A2_pooled": w1_an["pooled"]["A2"]["executed"],
            "G1_delta_vs_stored_W1_A2": (
                round(exe[_cell("puml", "stored")]
                      - w1_an["pooled"]["A2"]["executed"], 4)
                if exe.get(_cell("puml", "stored")) is not None else None),
            "stored_W3_pooled": {a: w3_an["pooled"][a]["executed"]
                                 for a in w3_an["pooled"]},
            "stored_W3_judged_medians": {
                s: {a: w3_an["judged_inventions"][s][a]["median"]
                    for a in w3_an["judged_inventions"][s]}
                for s in w3_an["judged_inventions"]},
            "stored_W1_A2_judged_medians": {
                s: w1_an["judged_inventions"][s]["A2"]["median"]
                for s in w1_an["judged_inventions"]},
        }
    except Exception as e:  # noqa: BLE001 — notes are optional context
        run_notes = {"unavailable": str(e)[:200]}

    return {"pooled": pooled, "per_generator": per_gen,
            "flow_set": {"pooled": flow, "per_generator": flow_gen},
            "compile_counts": compile_counts,
            "judged_inventions": judged, "mean_input_tokens": tokens,
            "alignment_deltas": align,
            "puml_frame_delta": puml_frame_delta,
            "per_frame_orderings": orderings,
            "expectation_inputs": expectation_inputs,
            "cross_occasion_run_notes": run_notes}


# ------------------------------------------------------------------- wave

def run_wave(prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    usage: dict = {}
    out_dir = RESULTS_W3B / "wave_main"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(cell, short, i + 1) for cell in CELL_ORDER
            for short in sa.GEN_MODELS for i in range(RUNS_PER_CELL)]
    runs: list[dict] = []
    aborted = None
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(generate_one, client, short, cell, idx,
                                usage, prior): (cell, short, idx)
                    for cell, short, idx in jobs}
            for fut in futs:
                runs.append(fut.result())
    except sa.WaveAbort as e:
        aborted = str(e)
    runs.sort(key=lambda r: (CELL_ORDER.index(r["arm"]), r["generator"],
                             r["run"]))

    for r in runs:
        art = out_dir / f"gen_{r['arm']}_{r['generator']}_run{r['run']}.py"
        art.write_text(r["code"], encoding="utf-8")
        r["code_file"] = art.name
        if r["compiles"]:
            r["execution"] = sa.execute_artifact(art)
        else:
            r["execution"] = [
                {"scenario": s, "stage": "import_error", "passed": False,
                 "outcome_class": None, "entry": None,
                 "detail": "does not compile"}
                for s in sa.suite_mod.SUITE["scenarios"]]

    if not aborted:
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futs = {pool.submit(judge_one, client, r["carrier"],
                                    r["code"], usage, prior): r
                        for r in runs if r["compiles"]}
                for fut, r in futs.items():
                    try:
                        r["judge"] = fut.result()
                    except sa.WaveAbort:
                        raise
                    except Exception as e:  # noqa: BLE001 — logged, excluded
                        r["judge"] = None
                        r["judge_error"] = str(e)[:300]
        except sa.WaveAbort as e:
            aborted = str(e)

    report = {
        "phase": "wave_main", "pre_registration": PREREG,
        "generators": sa.GEN_MODELS, "judge_model": sa.JUDGE_MODEL,
        "runs_per_cell": RUNS_PER_CELL,
        "cells": {c: {"carrier": CELLS[c][0], "frame": CELLS[c][1]}
                  for c in CELL_ORDER},
        # the stored template + the frame phrases + pinned kit hashes
        # reconstruct every cell prompt (the W3 report stored no prompt
        # text — that gap is not repeated here); per-cell prompt shas
        # pin what actually ran.
        "gen_prompt_stored_template": sa.GEN_PROMPT,
        "frame_phrases": {"stored": FRAME_STORED,
                          "neutral": FRAME_NEUTRAL,
                          "native": FRAME_NATIVE},
        "cell_prompt_sha256": {
            c: hashlib.sha256(
                cell_prompt(*CELLS[c]).encode()).hexdigest()
            for c in CELL_ORDER},
        "judge_prompt": sa.JUDGE_PROMPT,
        "kit_hashes": kit_hashes(),
        "usage": usage, "spend_usd": sa._spend(usage),
        "prior_spend_usd": prior, "calls_used": sa._CALLS["n"],
        "aborted": aborted,
        "runs": [{k: v for k, v in r.items() if k != "code"}
                 for r in runs],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = analyze_w3b(runs)
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["expectation_inputs"], indent=2))
    if aborted:
        print(f"ABORTED: {aborted}")
    print(f"spend this phase: ${sa._spend(usage)} "
          f"(W3B cumulative ${round(prior + sa._spend(usage), 2)} "
          f"of ${sa.CEILING_USD}) -> {out_dir}/report.json")
    return 2 if aborted else 0


# --------------------------------------------------------- pre-freeze checks

def prefreeze_checks() -> int:
    """Obligations (1)(2)(3) from the pre-registration's Driver bullet,
    plus the smoke/inventory checks from Calibration and the frozen-base
    identity checks. $0, no API."""
    checks: list[dict] = []

    def rec(name: str, ok: bool, detail: str = ""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              + (f" — {detail}" if detail else ""))

    w1_dir = sa.RESULTS_ROOT / "wave_main"
    w1_rep = json.loads((w1_dir / "report.json").read_text())
    w1_an = json.loads((w1_dir / "analysis.json").read_text())
    w3_dir = sv.RESULTS["W3"] / "wave_main"
    w3_rep = json.loads((w3_dir / "report.json").read_text())
    w3_an = json.loads((w3_dir / "analysis.json").read_text())

    # -- Frame mechanics (the treatment is well-defined).
    rec("frame phrase occurs exactly once in GEN_PROMPT template",
        sa.GEN_PROMPT.count(FRAME_STORED) == 1)
    for name, ph in ([("neutral", FRAME_NEUTRAL)]
                     + [(f"native:{c}", p) for c, p in
                        FRAME_NATIVE.items()]):
        rec(f"replacement phrase absent from template ({name})",
            ph not in sa.GEN_PROMPT, ph)
    rec("cell plan: 14 cells = 5x2 + 4x1", len(CELLS) == 14,
        " ".join(CELL_ORDER))
    rec("job plan: 84 scored generations",
        len(CELLS) * 2 * RUNS_PER_CELL == 84)

    # -- Shared frozen base byte-identity vs the stored records.
    rec("GEN_PROMPT byte-identical to W1 stored gen_prompt",
        sa.GEN_PROMPT == w1_rep["gen_prompt"])
    rec("JUDGE_PROMPT byte-identical to W1 stored judge_prompt",
        sa.JUDGE_PROMPT == w1_rep["judge_prompt"])
    for rel in sa.ARMS["A2"]:
        h = hashlib.sha256((sa.KIT / rel).read_bytes()).hexdigest()
        rec(f"kit hash unchanged vs W1 pin: {rel}",
            w1_rep["kit_hashes"].get(rel) == h)
    for tool in ("tools/acceptance/cargo_quote_suite.py",
                 "tools/acceptance/runner_child.py"):
        cur = kit_hashes()[tool]
        rec(f"hash unchanged vs W1 pin: {tool}",
            w1_rep["kit_hashes"].get(tool) == cur, cur[:16])
    for rel, h_stored in sorted(w3_rep["kit_hashes"].items()):
        cur = hashlib.sha256((SE / rel).read_bytes()).hexdigest()
        rec(f"hash unchanged vs W3 pin: {rel}", cur == h_stored)
    w1b_pre = json.loads((SE / "results" / "W1B" / "prefreeze_checks"
                          / "report.json").read_text())
    cur_sa = hashlib.sha256(
        (Path(__file__).parent / "stack_ablation.py").read_bytes()
    ).hexdigest()
    rec("stack_ablation.py byte-identical to W1b-recorded pin",
        cur_sa == w1b_pre["stack_ablation_sha256"], cur_sa[:16])

    # -- Obligation 1: prompt equivalence.
    # (a) puml-stored: literal byte-identity with W1-A2's prompt as run
    #     (W1's report stores the template; kit files verified unchanged
    #     against W1's pinned hashes above).
    expected_puml = w1_rep["gen_prompt"].format(spec=sa.bundle_text("A2"))
    rec("puml-stored prompt byte-identical to W1-A2's "
        "(stored template + pinned kit)",
        cell_prompt("puml", "stored") == expected_puml)
    # (b) four alternatives: W3's report stores no prompt text, so the
    #     obligation is reconstruction-based — independent string surgery
    #     on the A2 bundle (swap the behavior section, kit-style label)
    #     under W3's substitution rule, then the stored template.
    old_behav = (SE / "cargo_quote/behavior/quote_flow.puml").read_text(
        encoding="utf-8")
    old_sec = f"--- FILE: behavior/quote_flow.puml ---\n{old_behav}"
    for c in ALTERNATIVES:
        entries = dict(sv.ARMS["W3"][c])
        label = next(lbl for lbl in entries
                     if lbl.startswith("behavior/")
                     and lbl != "behavior/quote_flow.puml")
        text = (SE / entries[label]).read_text(encoding="utf-8")
        recon = sa.bundle_text("A2").replace(
            old_sec, f"--- FILE: {label} ---\n{text}")
        rec(f"F-stored prompt reconstruction-identical ({c})",
            cell_prompt(c, "stored")
            == w1_rep["gen_prompt"].format(spec=recon),
            "rule: A2 bundle, behavior section swapped for the frozen "
            f"carrier file under its kit-style label '{label}', "
            "stored template")
    # (c) the frozen W3 identity check itself still passes.
    rec("stack_variants verify_prompt_identity('W3') clean",
        sv.verify_prompt_identity("W3") == [])

    # -- Obligation 2: single-phrase diff, every F-neutral/F-native cell.
    for cell, (c, frame) in CELLS.items():
        if frame == "stored":
            continue
        stored_p = cell_prompt(c, "stored")
        var_p = cell_prompt(c, frame)
        new_ph = FRAME_NEUTRAL if frame == "neutral" else FRAME_NATIVE[c]
        n_occ = stored_p.count(FRAME_STORED)
        rec(f"single-phrase diff: {cell}",
            n_occ == 1 and var_p == stored_p.replace(FRAME_STORED, new_ph),
            f"stored phrase occurs {n_occ}x in assembled prompt; "
            f"'{FRAME_STORED}' -> '{new_ph}'")

    # -- Replay: stored W1-A2 + W3 artifacts re-score bit-for-bit
    #    through this driver's (imported, frozen) execution path.
    replayed = mismatches = 0
    for rep, base in ((w1_rep, w1_dir), (w3_rep, w3_dir)):
        for r in rep["runs"]:
            if rep is w1_rep and r["arm"] != "A2":
                continue
            if not r["compiles"]:
                continue
            rows = sa.execute_artifact(base / r["code_file"])
            replayed += 1
            if rows != r["execution"]:
                mismatches += 1
                for new, old in zip(rows, r["execution"]):
                    if new != old:
                        rec(f"replay mismatch {r['code_file']} "
                            f"{new['scenario']}", False,
                            f"stored={old['passed']} "
                            f"replay={new['passed']}")
    rec("replay: stored W1-A2 + W3 artifacts re-scored bit-for-bit",
        replayed == 27 and mismatches == 0,
        f"{replayed} artifacts (6 W1-A2 + 21 W3 compiling), "
        f"{mismatches} mismatching")

    # -- Marginal reproduction: this driver's rate/flow helpers
    #    reproduce the pinned stored numbers from raw stored runs.
    w3_runs = w3_rep["runs"]
    for arm, want_pool, want_flow in (
            ("code-stub", 0.3788, 0.7667), ("mermaid", 0.3485, 0.7333),
            ("controlled-english", 0.2879, 0.6), ("yaml", 0.1364, 0.2667)):
        block = sa._rates(w3_runs, arm)
        rec(f"W3 pooled reproduced: {arm}",
            block["executed"] == want_pool
            and block["executed"] == w3_an["pooled"][arm]["executed"],
            f"{block['executed']} (pin {want_pool})")
        rec(f"W3 flow-set reproduced: {arm}",
            _flow_rate(block) == want_flow,
            f"{_flow_rate(block)} (pin {want_flow})")
    a2 = sa._rates(w1_rep["runs"], "A2")
    rec("W1-A2 pooled reproduced", a2["executed"] == 0.4394,
        f"{a2['executed']} (pin 0.4394)")
    rec("W1-A2 flow-set reproduced", _flow_rate(a2) == 0.9333,
        f"{_flow_rate(a2)} (pin 0.9333)")
    for s, want in (("opus", 0.4545), ("haiku", 0.4242)):
        v = sa._rates(w1_rep["runs"], "A2", s)["executed"]
        rec(f"W1-A2 {s} reproduced", v == want, f"{v} (pin {want})")
    rec("W3 opus-yaml stored compile count 0/3",
        sum(1 for r in w3_runs if r["arm"] == "yaml"
            and r["generator"] == "opus" and r["compiles"]) == 0)

    # -- Obligation 3: expectation-inputs dry-run over a synthetic
    #    complete dataset (stored W1-A2 runs cloned into all 14 cells;
    #    scoring meaning: none — code-path exercise, the X-R1 lesson).
    synth = []
    for cell, (c, frame) in CELLS.items():
        for r in w1_rep["runs"]:
            if r["arm"] != "A2":
                continue
            clone = dict(r)
            clone["arm"] = cell
            clone["carrier"], clone["frame"] = c, frame
            synth.append(clone)
    ei = analyze_w3b(synth)["expectation_inputs"]
    required = ["E1_flow_deficits_vs_puml_neutral",
                "E2a_alignment_pooled", "E2b_yaml_alignment_pooled",
                "E3_opus_yaml_compiles", "E4_puml_frame_delta",
                "E5_alignment_by_gen", "E6_judged_by_carrier",
                "G1_puml_stored_pooled", "G2_puml_stored_by_gen",
                "G2b_puml_neutral_by_gen",
                "G3_stored_flow_deficits_vs_puml_stored", "G3_licensed"]
    missing = [k for k in required
               if k not in ei or ei[k] is None or ei[k] == {}]
    rec("expectation-inputs dry-run emits every E1-E6/G1-G3 input",
        not missing, f"missing: {missing}" if missing else
        f"{len(required)} inputs emitted (synthetic data, no meaning)")

    # -- Calibration checks: smoke + cell inventories.
    ref_rows = sa.execute_artifact(sa.KIT / "reference_impl.py")
    rec("reference impl 11/11 through the frozen scoring path",
        sum(bool(r["passed"]) for r in ref_rows) == 11)
    for cell, (c, frame) in CELLS.items():
        p = cell_prompt(c, frame)
        rec(f"cell inventory {cell}", len(p) > 0,
            f"prompt sha {hashlib.sha256(p.encode()).hexdigest()[:16]} "
            f"chars {len(p)}")

    ok = all(ch["ok"] for ch in checks)
    out_dir = RESULTS_W3B / "prefreeze_checks"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps({
        "phase": "prefreeze_checks", "pre_registration": PREREG,
        "spend_usd": 0.0,
        "driver_sha256_at_check": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
        "stack_ablation_sha256": cur_sa,
        "stack_variants_sha256": hashlib.sha256(
            (Path(__file__).parent / "stack_variants.py")
            .read_bytes()).hexdigest(),
        "frame_phrases": {"stored": FRAME_STORED,
                          "neutral": FRAME_NEUTRAL,
                          "native": FRAME_NATIVE},
        "checks": checks, "all_ok": ok,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"PRE-FREEZE CHECKS {'PASSED' if ok else 'FAILED'} "
          f"({sum(c_['ok'] for c_ in checks)}/{len(checks)}) "
          f"-> {out_dir}/report.json")
    return 0 if ok else 1


# ------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--prefreeze-checks", action="store_true")
    ap.add_argument("--wave", action="store_true")
    ap.add_argument("--confirm-frozen", action="store_true",
                    help="required with --wave: asserts the W3b "
                         "pre-registration is FROZEN in a commit and "
                         "owner go is recorded in its preamble")
    args = ap.parse_args(argv)

    plan = (f"W3b plan: {len(CELLS) * 2 * RUNS_PER_CELL} scored "
            f"generations (+ up to 1 retry each) + as many judgements "
            f"across {len(CELLS)} cells x 2 generators x "
            f"{RUNS_PER_CELL} runs; MAX_CALLS={sa.MAX_CALLS} (live), "
            f"ceiling ${sa.CEILING_USD} scoped to results/W3B")
    if args.dry_run:
        print(plan)
        print("frame strings (the whole treatment — one substitution):")
        print(f"  stored : {FRAME_STORED!r}")
        print(f"  neutral: {FRAME_NEUTRAL!r}")
        for c, p in FRAME_NATIVE.items():
            print(f"  native ({c}): {p!r}")
        for cell, (c, frame) in CELLS.items():
            p = cell_prompt(c, frame)
            print(f"  {cell:28s} runs/gen={RUNS_PER_CELL} "
                  f"chars={len(p)} sha={hashlib.sha256(p.encode()).hexdigest()[:16]}")
        return 0
    if args.smoke:
        return sa.smoke()
    if args.prefreeze_checks:
        return prefreeze_checks()
    if args.wave:
        if not args.confirm_frozen:
            print("refusing: --wave requires --confirm-frozen (the W3b "
                  "pre-registration must be frozen in a commit and owner "
                  "go recorded — W3B_PREREGISTRATION.md preamble)")
            return 2
        if "VERIFIED REVISION" in (REPO_ROOT / PREREG).read_text()[:400]:
            print("refusing: W3B_PREREGISTRATION.md still reads "
                  "'VERIFIED REVISION' — freeze it first")
            return 2
        if not (os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            print("no Anthropic API credentials in the environment")
            return 2
        print(plan)
        return run_wave(prior_spend())
    print(plan + "\nnothing to do: pass one of --dry-run/--smoke/"
          "--prefreeze-checks/--wave")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
