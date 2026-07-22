"""Golden-score regression guard (Phase 10f).

Scores are a public contract: any change that shifts a corpus diagram's level
or composite — a new rule, a reweighted dimension, a parser fix — must be a
conscious decision, not a side effect. This test regenerates the corpus
deterministically and compares every unit's score against the committed
snapshot.

After a *deliberate* scoring change, re-freeze with:

    python tools/calibrate.py --freeze tests/golden_scores.json

Plain assert functions so the zero-dependency runner exercises this too.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import calibrate  # noqa: E402
import gen_corpus  # noqa: E402

_GOLDEN_PATH = Path(__file__).resolve().parent / "golden_scores.json"
_REFREEZE = "run: python tools/calibrate.py --freeze tests/golden_scores.json"


def test_corpus_scores_match_the_golden_snapshot():
    golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "corpus"
        gen_corpus.generate(dest)
        current = calibrate.snapshot(dest)

    assert set(current) == set(golden), {
        "new_units": sorted(set(current) - set(golden)),
        "missing_units": sorted(set(golden) - set(current)),
        "hint": _REFREEZE,
    }
    drifted = []
    for unit, want in golden.items():
        got = current[unit]
        if got["level"] != want["level"] or abs(got["composite"] - want["composite"]) > 0.01:
            drifted.append(f"{unit}: {want} -> {got}")
    assert not drifted, "scores drifted (deliberate? " + _REFREEZE + "):\n" + "\n".join(drifted)


def test_golden_snapshot_is_sane():
    golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert len(golden) >= 40
    levels = {v["level"] for v in golden.values()}
    assert levels >= {1, 3, 4}, f"golden spans too few levels: {sorted(levels)}"
    assert all(1 <= v["level"] <= 5 and 0 <= v["composite"] <= 100 for v in golden.values())
