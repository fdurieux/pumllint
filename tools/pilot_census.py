"""Pilot dialect census — read-only sweep over a real diagram corpus.

Answers the question a pilot must answer BEFORE gating anything: how much
of this organisation's PlantUML dialect does pumllint actually understand,
and what would fire on day one? Produces:

  1. Inventory        — files found, files yielding no scoreable diagram,
                        diagrams by detected type
  2. Coverage suspects — diagrams whose recognized element count is tiny
                        relative to file size (the parser understood little:
                        C4 macros, component/deployment forms, heavy
                        preprocessor use)
  3. Dialect markers  — files using !include, C4 macro calls, preprocessor
                        directives, or non-UML PlantUML forms (@startmindmap…)
  4. Maturity distribution — levels, composite stats, suppressed findings
  5. Rule-firing histogram — findings per rule with files affected
  6. Runtime          — wall time and files/second at corpus scale

Standard library only; drives the installed `pumllint` CLI through its
schema-pinned JSON contract (`pumllint schema lint|score`), so this file
can be copied standalone anywhere `pip install pumllint` works. Read-only:
it never modifies a diagram and never calls the network.

Usage:
  python pilot_census.py <paths...> [--profile codegen] [--config FILE]
                         [-o census.json] [--top 15] [--pumllint CMD]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

EXTENSIONS = (".puml", ".plantuml", ".iuml", ".wsd")

MARKERS = {
    "include directives (!include…)": re.compile(r"^\s*!include", re.M),
    "C4 macro calls (Person/System/Container/Rel…)": re.compile(
        r"\b(?:Person|System|Container|Component|Boundary|Rel|Enterprise_Boundary)"
        r"(?:_\w+)?\s*\(", re.M),
    "preprocessor (!define/!procedure/!function/!if…)": re.compile(
        r"^\s*!(?:define|definelong|procedure|function|if|while|import|"
        r"local|global|assert)", re.M),
    "non-UML PlantUML forms (@startmindmap/gantt/json/salt/wbs…)": re.compile(
        r"^@start(?!uml)\w+", re.M),
    "multiple diagrams per file": re.compile(
        r"(?:@startuml.*?@enduml.*?){2,}", re.S),
}


def _by_file(suspects: list[dict]) -> list[dict]:
    """One row per file — its worst — preserving the incoming ratio order.

    A multi-diagram file otherwise contributes one identical row per diagram,
    which both inflates the headline count and lets a single file monopolise
    the display.
    """
    seen: set = set()
    out = []
    for s in suspects:
        if s["file"] not in seen:
            seen.add(s["file"])
            out.append(s)
    return out


def _spread(hits: list[str], n: int) -> list[str]:
    """*n* examples from as many distinct directories as possible.

    `hits` is path-sorted, so a plain slice returns whichever source sorts
    first — systematically hiding the largest contributor. Take one per
    directory, then fill from what is left; sorted at the end so the result
    is deterministic.
    """
    groups: dict[str, list[str]] = {}
    for h in hits:
        # Parent directory, not the leading segment: paths may be absolute, in
        # which case every leading segment is the same empty string.
        groups.setdefault(h.rsplit("/", 1)[0] if "/" in h else "", []).append(h)
    picked = [g[0] for g in groups.values()][:n]
    if len(picked) < n:
        rest = [h for h in hits if h not in picked]
        picked += rest[: n - len(picked)]
    return sorted(picked)


def discover(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in (Path(x) for x in paths):
        if p.is_dir():
            for ext in EXTENSIONS:
                files.extend(sorted(p.rglob(f"*{ext}")))
        elif p.exists():
            files.append(p)
        else:
            sys.exit(f"error: no such path: {p}")
    return sorted(set(files))


def resolve_cli(explicit: str | None) -> list[str]:
    if explicit:
        return explicit.split()
    if shutil.which("pumllint"):
        return ["pumllint"]
    return [sys.executable, "-m", "pumllint"]


def run_cli(cli, args, paths) -> str:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out = tmp.name
    cmd = [*cli, *args, "-f", "json", "-o", out, *map(str, paths)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 2:
        sys.exit(f"error: pumllint usage error:\n{proc.stderr}")
    text = Path(out).read_text(encoding="utf-8")
    Path(out).unlink(missing_ok=True)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="pumllint pilot dialect census")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--profile", help="e.g. codegen (default: none)")
    ap.add_argument("--config", help="pumllint config file (-c pass-through)")
    ap.add_argument("--pumllint", help="pumllint command (default: auto)")
    ap.add_argument("--top", type=int, default=15,
                    help="how many coverage suspects to list")
    ap.add_argument("-o", "--output", help="also write full census JSON here")
    args = ap.parse_args(argv)

    cli = resolve_cli(args.pumllint)
    common = []
    if args.profile:
        common += ["--profile", args.profile]
    if args.config:
        common += ["-c", args.config]

    files = discover(args.paths)
    if not files:
        sys.exit("error: no diagram files found")
    src = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}
    lines_of = {f: src[f].count("\n") + 1 for f in files}

    t0 = time.time()
    score = json.loads(run_cli(cli, ["score", *common], files))
    findings = json.loads(run_cli(cli, [*common], files))
    elapsed = time.time() - t0

    diagrams = score["diagrams"]
    scored_files = {Path(d["file"]).resolve() for d in diagrams}
    unscored = [f for f in files if f.resolve() not in scored_files]

    # 2 — coverage suspects
    #
    # One row per *diagram*, but `lines` is the whole file's count, so a
    # multi-diagram file contributes one identical row per diagram it holds.
    # The 2026-08-11 wild corpus had a 16-diagram file that produced 16 rows
    # at the same ratio: 104 rows over 89 files, and because rows sort by
    # ratio that single file filled every slot of the default display. The
    # headline counts files (what an operator acts on) and the display shows
    # each file once, keeping its worst row.
    suspects = []
    for d in diagrams:
        f = Path(d["file"])
        n_lines = lines_of.get(f) or lines_of.get(f.resolve(), 0)
        el = d["maturity"]["elementCount"]
        ratio = n_lines / max(1, el)
        if (el <= 2 and n_lines >= 15) or (ratio > 12 and n_lines >= 30):
            suspects.append({"file": d["file"], "diagram": d.get("name"),
                             "lines": n_lines, "elements": el,
                             "type": d.get("diagramType"),
                             "lines_per_element": round(ratio, 1)})
    suspects.sort(key=lambda s: -s["lines_per_element"])
    suspect_files = _by_file(suspects)

    # 3 — dialect markers
    #
    # Examples are spread across distinct top-level directories rather than
    # taken as `hit[:3]`. `files` arrives sorted, so the first three came from
    # whichever repository sorts first: on the 2026-08-11 wild corpus that
    # showed two repositories contributing 5 hits between them while the one
    # contributing 66 of 73 never appeared, because it sorted last. The
    # examples are the only per-file evidence the artefact keeps, so they have
    # to be representative rather than alphabetical.
    marker_hits = {}
    for label, rx in MARKERS.items():
        hit = [f.as_posix() for f in files if rx.search(src[f])]
        marker_hits[label] = {"files": len(hit), "examples": _spread(hit, 3)}

    # 4 — maturity distribution
    levels = Counter(d["maturity"]["level"] for d in diagrams)
    composites = [d["maturity"]["score"] for d in diagrams]
    suppressed = sum(d["maturity"].get("suppressedCount", 0) for d in diagrams)

    # 5 — rule firing
    by_rule: dict[str, dict] = defaultdict(lambda: {"count": 0, "files": set(),
                                                    "severity": ""})
    for v in findings:
        r = by_rule[v["ruleId"]]
        r["count"] += 1
        r["files"].add(v["file"])
        r["severity"] = v["severity"]

    # ------------------------------------------------------------- report
    print(f"pumllint pilot census — {len(files)} files, "
          f"{len(diagrams)} diagrams, profile={args.profile or 'default'}")
    print(f"runtime: {elapsed:.1f}s ({len(files) / max(elapsed, 1e-9):.0f} files/s)\n")

    print("1. INVENTORY")
    for t, n in Counter(d.get("diagramType") for d in diagrams).most_common():
        print(f"   {t or '(untyped)':<12} {n}")
    if unscored:
        print(f"   files yielding NO scoreable diagram: {len(unscored)} "
              f"— dialect-gap signal, inspect these first:")
        for f in unscored[:args.top]:
            print(f"     {f}")
    else:
        print("   every file yielded at least one scoreable diagram")

    print(f"\n2. COVERAGE SUSPECTS (big file, few recognized elements): "
          f"{len(suspect_files)} of {len(files)} files"
          + (f" ({len(suspects)} diagram rows)"
             if len(suspects) != len(suspect_files) else ""))
    for s in suspect_files[:args.top]:
        print(f"   {s['lines_per_element']:>6} l/el  {s['lines']:>4} lines "
              f"{s['elements']:>3} el  [{s['type']}] {s['file']}")

    print("\n3. DIALECT MARKERS (files containing)")
    for label, h in marker_hits.items():
        flag = "  <-- expect gaps/false positives here" if (
            h["files"] and ("C4" in label or "include" in label
                            or "non-UML" in label)) else ""
        print(f"   {h['files']:>4}  {label}{flag}")

    print("\n4. MATURITY DISTRIBUTION (advisory — calibrate before gating)")
    for lv in (5, 4, 3, 2, 1):
        if levels.get(lv):
            print(f"   Level {lv}: {levels[lv]}")
    if composites:
        print(f"   composite: median {statistics.median(composites):.0f}, "
              f"min {min(composites):.0f}, max {max(composites):.0f}; "
              f"model set: Level {score['modelSet']['level']} "
              f"({score['modelSet']['levelName']})")
    print(f"   findings suppressed inline: {suppressed}")

    print(f"\n5. RULE FIRING ({len(findings)} findings)")
    for rid, r in sorted(by_rule.items(), key=lambda kv: -kv[1]["count"]):
        print(f"   {rid:<8} {r['severity']:<8} {r['count']:>5} findings "
              f"in {len(r['files'])} files")
    if not findings:
        print("   none")

    if args.output:
        Path(args.output).write_text(json.dumps({
            "files": len(files), "diagrams": len(diagrams),
            "profile": args.profile, "runtime_s": round(elapsed, 1),
            "types": Counter(d.get("diagramType") for d in diagrams),
            "unscored_files": [f.as_posix() for f in unscored],
            "coverage_suspect_files": len(suspect_files),
            "coverage_suspects": suspects,
            "dialect_markers": marker_hits,
            "levels": levels,
            "model_set": score["modelSet"],
            "suppressed": suppressed,
            "rule_firing": {rid: {"count": r["count"],
                                  "files": len(r["files"]),
                                  "severity": r["severity"]}
                            for rid, r in by_rule.items()},
        }, indent=2, default=list) + "\n", encoding="utf-8")
        print(f"\nfull census -> {args.output}")

    print("\nNext steps: inspect unscored files and top suspects (dialect "
          "gaps);\nreview the firing histogram with your architect "
          "(calibration week);\nthen record the baseline: pumllint score "
          "<paths> --baseline maturity.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
