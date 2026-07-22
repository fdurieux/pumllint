"""Sensitivity/calibration harness for the maturity scorer (Phase 10b).

Scores the whole corpus (tools/gen_corpus.py) plus the example pairs under a
set of candidate scoring configurations and reports four metrics:

- **monotonicity** — a mutated diagram must never outscore its parent
  (composite or level). Violations are the kill criterion for a candidate.
- **expected levels** — synthetic boundary probes must land on their labeled
  level (default profile).
- **pair discrimination** — each good/bad example pair must order correctly
  (good above bad) with a composite gap worth the name.
- **volatility** — the largest composite/level drop caused by one added
  finding, bucketed by parent element count (small-diagram twitchiness).
- **boundary proximity** — units whose composite sits within +/-3 points of a
  level threshold (fragile verdicts).

Run:  python tools/calibrate.py [corpus_dir]   (generates the corpus if absent)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # make `pumllint` importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling tool modules

import _scorelib  # noqa: E402
from pumllint import ScoringConfig  # noqa: E402

EXAMPLES_DIR = REPO_ROOT / "examples"

# Good/bad example pairs: (good stem, bad stem, profile to score under)
PAIRS = [
    ("credit_intake_good", "credit_intake_bad", None),
    ("loan_decision_activity_good", "loan_decision_activity_bad", None),
    ("order_payment_codegen_good", "order_payment_codegen_bad", "codegen"),
]

# Candidate scoring configurations (passed to score(config=...)).
PARAM_SETS: dict[str, dict] = {
    "default": {},
    "K25": {"k": 25},
    "K75": {"k": 75},
    "K100": {"k": 100},
    # Pre-Phase-10 weights (TRC/RDB at 0.10 each), kept as a comparison line.
    "legacy-thin-weights": {
        "dimension_weights": {
            "DIM-SEM": 0.20, "DIM-CMP": 0.25, "DIM-CON": 0.15,
            "DIM-TRC": 0.10, "DIM-RDB": 0.10, "DIM-AMB": 0.20,
        }
    },
    "critical6": {"severity_weights": {"critical": 6}},
}

# Level thresholds come from the product's own defaults — never re-encoded.
_DEFAULTS = ScoringConfig()
_LEVEL_THRESHOLDS = (
    _DEFAULTS.l2_composite, _DEFAULTS.l3_composite,
    _DEFAULTS.l4_composite, _DEFAULTS.l5_composite,
)
_BUCKETS = ((1, 4, "1-4"), (5, 9, "5-9"), (10, 19, "10-19"), (20, 10**9, "20+"))


def _bucket(element_count: int) -> str:
    for lo, hi, name in _BUCKETS:
        if lo <= element_count <= hi:
            return name
    return "0"


class Scorer:
    """Scores diagram files under a fixed scoring config.

    Parsing/linting is delegated to (and cached by) tools/_scorelib.py, which
    the experiment harness shares; only the per-scoring-config results are
    cached here.
    """

    def __init__(self, scoring_cfg: dict):
        self.scoring_cfg = scoring_cfg
        self._cache: dict[tuple[str, str | None], tuple[int, float, int]] = {}

    def score_file(self, path: Path, profile: str | None) -> tuple[int, float, int]:
        """(level, composite, element_count) for the first diagram in *path*."""
        key = (str(path), profile)
        if key not in self._cache:
            result = _scorelib.score_first_diagram(path, profile, self.scoring_cfg)
            self._cache[key] = (result.level, result.composite, result.element_count)
        return self._cache[key]


def _resolve(ref: str, corpus_dir: Path) -> Path:
    if ref.startswith("examples/"):
        return REPO_ROOT / ref
    return corpus_dir / ref


def evaluate(corpus_dir: Path, scoring_cfg: dict) -> dict:
    """All metrics for one candidate configuration."""
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    scorer = Scorer(scoring_cfg)

    mono_violations: list[str] = []
    expected_misses: list[str] = []
    volatility: dict[str, dict[str, float]] = {}
    near_boundary = 0
    scored_units = 0

    for unit in manifest["units"]:
        path = _resolve(unit["file"], corpus_dir)
        profile = unit.get("profile")
        level, composite, elements = scorer.score_file(path, profile)
        scored_units += 1

        if any(abs(composite - t) <= 3.0 for t in _LEVEL_THRESHOLDS):
            near_boundary += 1

        if unit["tier"] == "synthetic":
            expected = unit["expected_level"]
            if level != expected:
                expected_misses.append(
                    f"{unit['file']}: level {level}, expected {expected}"
                )
            continue

        # Mutation: compare against parent (monotonicity + volatility edge).
        p_level, p_composite, p_elements = scorer.score_file(
            _resolve(unit["parent"], corpus_dir), profile
        )
        if composite > p_composite + 1e-9 or level > p_level:
            mono_violations.append(
                f"{unit['file']} (L{level}/{composite:.1f}) outscores parent "
                f"{unit['parent']} (L{p_level}/{p_composite:.1f})"
            )
        bucket = volatility.setdefault(
            _bucket(p_elements), {"max_dc": 0.0, "max_dl": 0}
        )
        bucket["max_dc"] = max(bucket["max_dc"], p_composite - composite)
        bucket["max_dl"] = max(bucket["max_dl"], p_level - level)

    # Wild tier (optional): no ground truth — checks the scorer survives
    # real-world input and reports the level distribution.
    wild = {"count": 0, "failures": [], "levels": {}}
    for path in sorted((corpus_dir / "wild").glob("*.puml")):
        wild["count"] += 1
        try:
            level, composite, _ = scorer.score_file(path, None)
        except Exception as e:  # noqa: BLE001 — robustness metric by design
            wild["failures"].append(f"{path.name}: {type(e).__name__}: {e}")
            continue
        wild["levels"][level] = wild["levels"].get(level, 0) + 1
        if any(abs(composite - t) <= 3.0 for t in _LEVEL_THRESHOLDS):
            near_boundary += 1

    pairs = []
    for good, bad, profile in PAIRS:
        g_level, g_comp, _ = scorer.score_file(EXAMPLES_DIR / f"{good}.puml", profile)
        b_level, b_comp, _ = scorer.score_file(EXAMPLES_DIR / f"{bad}.puml", profile)
        pairs.append({
            "pair": good.replace("_good", ""),
            "good": (g_level, round(g_comp, 1)),
            "bad": (b_level, round(b_comp, 1)),
            "ordered": g_level > b_level and g_comp > b_comp,
            "composite_gap": round(g_comp - b_comp, 1),
        })

    return {
        "units": scored_units,
        "monotonicity_violations": mono_violations,
        "expected_level_misses": expected_misses,
        "pairs": pairs,
        "volatility": volatility,
        "near_boundary": near_boundary,
        "wild": wild,
    }


def run_sweep(corpus_dir: Path, param_sets: dict[str, dict] | None = None) -> dict[str, dict]:
    return {
        name: evaluate(corpus_dir, cfg)
        for name, cfg in (param_sets or PARAM_SETS).items()
    }


def render_report(results: dict[str, dict]) -> str:
    lines = [
        f"{'param set':<22} {'mono':>5} {'expect':>7} {'pairs':>6} "
        f"{'near-b':>7}  volatility (max dComposite/dLevel by parent size)",
    ]
    for name, r in results.items():
        vol = " ".join(
            f"{b}:{v['max_dc']:.0f}/{v['max_dl']}"
            for b, v in sorted(r["volatility"].items())
        )
        pairs_ok = sum(1 for p in r["pairs"] if p["ordered"])
        lines.append(
            f"{name:<22} {len(r['monotonicity_violations']):>5} "
            f"{len(r['expected_level_misses']):>7} {pairs_ok:>4}/{len(r['pairs'])} "
            f"{r['near_boundary']:>7}  {vol}"
        )
    first = next(iter(results.values()), None)
    if first and first["wild"]["count"]:
        w = first["wild"]
        dist = " ".join(f"L{k}:{v}" for k, v in sorted(w["levels"].items()))
        lines.append(
            f"wild tier: {w['count']} diagrams, {len(w['failures'])} failures, "
            f"levels {dist}  (distribution under 'default')"
        )
        for f in w["failures"]:
            lines.append(f"  WILD FAIL: {f}")
    for name, r in results.items():
        for v in r["monotonicity_violations"]:
            lines.append(f"  [{name}] MONO: {v}")
        for m in r["expected_level_misses"]:
            lines.append(f"  [{name}] EXPECT: {m}")
        for p in r["pairs"]:
            if not p["ordered"]:
                lines.append(f"  [{name}] PAIR: {p['pair']} not ordered: {p}")
    return "\n".join(lines)


def snapshot(corpus_dir: Path, scoring_cfg: dict | None = None) -> dict[str, dict]:
    """Golden snapshot: {unit file -> level/composite} under one config.

    Covers the deterministic tiers (mutations + synthetic) only — the wild
    tier is not regenerable and stays out of the golden contract.
    """
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    scorer = Scorer(scoring_cfg or {})
    out: dict[str, dict] = {}
    for unit in manifest["units"]:
        level, composite, elements = scorer.score_file(
            _resolve(unit["file"], corpus_dir), unit.get("profile")
        )
        out[unit["file"]] = {
            "level": level, "composite": round(composite, 2), "elements": elements,
        }
    return out


def _regenerate(corpus_dir: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gen_corpus

    gen_corpus.generate(corpus_dir)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Maturity-scoring calibration harness")
    ap.add_argument("corpus_dir", nargs="?", type=Path, default=REPO_ROOT / "corpus")
    ap.add_argument(
        "--freeze", metavar="DEST", type=Path,
        help="regenerate the corpus, snapshot golden scores, and write them to DEST",
    )
    args = ap.parse_args(argv)
    corpus_dir = args.corpus_dir

    if args.freeze:
        # Always regenerate before freezing: a stale on-disk corpus must never
        # become the golden contract.
        _regenerate(corpus_dir)
        snap = snapshot(corpus_dir)
        args.freeze.write_text(
            json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Froze {len(snap)} golden scores to {args.freeze}")
        return 0

    if not (corpus_dir / "manifest.json").exists():
        _regenerate(corpus_dir)
        print(f"(generated corpus at {corpus_dir})")
    results = run_sweep(corpus_dir)
    print(render_report(results))
    bad = any(
        r["monotonicity_violations"] or r["expected_level_misses"]
        for r in results.values()
    )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
