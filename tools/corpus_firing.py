"""Corpus firing report — where does each rule fire, and how often?

The Arc F safeguard made runnable: beyond pass/fail golden scores, run
the rule set over the calibration corpus (per-unit profiles from
corpus/manifest.json, engines built exactly like the golden pipeline)
and the wild tier, and emit a per-rule firing histogram as a human
review artifact. A rule that is golden-neutral *by design* — profile- or
convention-gated — is invisible to the golden test; this report is what
catches "semantically wrong but golden-neutral" before it ships, the
analysis that forced GEN006/GEN007's dormancy decision.

Typical uses:
  python tools/corpus_firing.py                      # full histogram
  python tools/corpus_firing.py --rules SEQ110       # new-rule review
  python tools/corpus_firing.py --config obligations.toml --rules SEQ110

Calibration units lint their FIRST diagram under their manifest profile
(golden-pipeline parity); wild files lint every diagram they contain
under --profile (default: none). Per-unit isolation throughout, so
cross-diagram (XD) firing is not represented — matching the calibration
pipeline. Standard library only, deterministic output, no timestamps.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pumllint import Engine  # noqa: E402
from pumllint.config import load_config  # noqa: E402
from pumllint.parser.sequence import parse_source  # noqa: E402


def _engine(profile, config, cache):
    if profile not in cache:
        cfg = dict(config) if config else {}
        if profile:
            cfg["profile"] = profile
        cache[profile] = Engine(cfg)
    return cache[profile]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="pumllint corpus firing report")
    ap.add_argument("--corpus", default=str(REPO_ROOT / "corpus"),
                    help="corpus root (default: corpus/)")
    ap.add_argument("--config", help="config file for convention-gated packs "
                                     "(e.g. an [obligations] table)")
    ap.add_argument("--profile", help="profile for the wild tier "
                                      "(calibration units use the manifest)")
    ap.add_argument("--rules", help="comma-separated rule ids to focus on; "
                                    "zero-firing ids are reported explicitly")
    ap.add_argument("--samples", type=int, default=3,
                    help="sample findings per focused rule (default 3)")
    ap.add_argument("--no-wild", action="store_true",
                    help="skip the wild tier")
    args = ap.parse_args(argv)

    corpus = Path(args.corpus)
    manifest_path = corpus / "manifest.json"
    if not manifest_path.exists():
        sys.exit("error: corpus/manifest.json not found — the corpus is "
                 "gitignored; regenerate with: python tools/gen_corpus.py")

    config = load_config(args.config) if args.config else None
    engines: dict = {}
    focus = ([r.strip().upper() for r in args.rules.split(",") if r.strip()]
             if args.rules else None)

    # rule id -> aggregation
    agg: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "files": set(), "severity": "",
                 "tiers": defaultdict(int), "samples": []})

    def record(violations, tier, label):
        for v in violations:
            r = agg[v.rule_id]
            r["count"] += 1
            r["files"].add(label)
            r["severity"] = getattr(v.severity, "value", str(v.severity))
            r["tiers"][tier] += 1
            r["samples"].append((label, v.line, v.message))

    units = json.loads(manifest_path.read_text(encoding="utf-8"))["units"]
    profiles = defaultdict(int)
    for u in units:
        profiles[u.get("profile") or "none"] += 1
        path = corpus / u["file"]
        diagrams = parse_source(
            path.read_text(encoding="utf-8", errors="replace"), str(path))
        if not diagrams:
            continue
        eng = _engine(u.get("profile"), config, engines)
        record(eng.lint_diagram(diagrams[0]), u["tier"], u["file"])

    wild_files: list[Path] = []
    if not args.no_wild:
        wild_files = sorted((corpus / "wild").glob("*.puml"))
        for path in wild_files:
            diagrams = parse_source(
                path.read_text(encoding="utf-8", errors="replace"), str(path))
            eng = _engine(args.profile, config, engines)
            for d in diagrams:
                record(eng.lint_diagram(d), "wild", f"wild/{path.name}")

    # ------------------------------------------------------------- report
    prof = " ".join(f"{k}:{n}" for k, n in sorted(profiles.items()))
    print(f"corpus firing report — calibration: {len(units)} units ({prof});"
          f" wild: {len(wild_files)} files,"
          f" profile={args.profile or 'none'}")
    print(f"engine: {'config=' + args.config if args.config else 'config-free (golden-pipeline parity)'}\n")

    rows = sorted(agg.items(), key=lambda kv: (-kv[1]["count"], kv[0]))
    if focus:
        rows = [(rid, r) for rid, r in rows if rid in focus]
    print(f"{'rule':<8} {'severity':<9} {'findings':>8} {'units':>6}  tiers")
    for rid, r in rows:
        tiers = " ".join(f"{t}:{n}" for t, n in sorted(r["tiers"].items()))
        print(f"{rid:<8} {r['severity']:<9} {r['count']:>8} "
              f"{len(r['files']):>6}  {tiers}")
    if not rows:
        print("(no findings)")

    if focus:
        silent = [rid for rid in focus if rid not in agg]
        if silent:
            print(f"\nfocused rules with ZERO findings: {', '.join(silent)}"
                  "\n(for a new rule this is the review signal: dormant as"
                  " intended, or semantically wrong but golden-neutral?)")
        for rid in focus:
            if rid in agg and args.samples > 0:
                print(f"\nsamples ({rid}):")
                for label, line, msg in sorted(agg[rid]["samples"])[:args.samples]:
                    print(f"  {label}:{line}  {msg[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
