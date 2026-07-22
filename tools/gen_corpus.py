"""Generate the calibration corpus (Phase 10a).

Two tiers, all derived deterministically so the corpus is reproducible:

- **mutations/** — systematic single degradations of the known-good examples
  ("singles", one operator each), plus a cumulative **degradation ladder** per
  example. The ladder is ground truth by construction: each rung adds findings
  to the previous rung, so a rung may never outscore its parent (the
  monotonicity property tools/calibrate.py checks).

  Operators that *add* diagram elements (e.g. self_message) are excluded from
  ladders: a new element enlarges the density denominator, which can
  legitimately raise *other* dimensions' scores — they are emitted as singles
  only.

- **synthetic/** — hand-authored boundary probes with expected maturity levels
  (default profile), exercising the integrity caps and level thresholds.

Run:  python tools/gen_corpus.py [dest]     (default dest: ./corpus)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


# ---------------------------------------------------------------------------
# Mutation operators: (name, transform) — transform returns None when the
# operator does not apply to the given text.
# ---------------------------------------------------------------------------

def _sub(pattern: str, repl: str, text: str) -> str | None:
    new, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    return new if n else None


def op_drop_title(text):
    return _sub(r"^title .*\n", "", text)


def op_drop_name(text):
    return _sub(r"^@startuml .+$", "@startuml", text)


def op_undeclare_participant(text):
    return _sub(r"^participant \w+.*\n", "", text)


def op_unlabel_message(text):
    return _sub(r"^(\s*\w+ -> \w+) : .+$", r"\1", text)


def op_unbalance_activation(text):
    return _sub(r"^\s*deactivate \w+\n", "", text)


def op_unterminate_block(text):
    return _sub(r"^end\n", "", text)


def op_self_message(text):  # adds an element -> singles only
    m = re.search(r"^(?:participant|actor) (\w+)", text, flags=re.MULTILINE)
    if not m or "@enduml" not in text:
        return None
    name = m.group(1)
    return text.replace("@enduml", f"{name} -> {name} : recheck data\n@enduml", 1)


def op_vague_guard(text):
    return _sub(r"^(\s*)alt .+$", r"\1alt sometimes", text)


def op_prose_message(text):
    if "findOrderById(orderId)" not in text:
        return None
    return text.replace("findOrderById(orderId)", "handle the order data somehow", 1)


def op_elision_marker(text):
    if ": receipt" not in text:
        return None
    return text.replace(": receipt", ": receipt ...", 1)


def op_drop_start(text):
    return _sub(r"^start\n", "", text)


def op_drop_stop(text):
    return _sub(r"^stop\n", "", text)


def op_noun_activity(text):
    if ":Receive application;" not in text:
        return None
    return text.replace(":Receive application;", ":Application review;", 1)


def op_unlabel_branch(text):
    if "then (yes)" not in text:
        return None
    return text.replace("then (yes)", "then", 1)


def op_unterminate_construct(text):
    return _sub(r"^\s+endif\n", "", text)


# Per-parent operator plans: (example file, profile, ladder ops, single-only ops)
PLANS = [
    (
        "credit_intake_good.puml",
        None,
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("undeclare_participant", op_undeclare_participant),
            ("unlabel_message", op_unlabel_message),
            ("unbalance_activation", op_unbalance_activation),
            ("unterminate_block", op_unterminate_block),
        ],
        [("self_message", op_self_message)],
    ),
    (
        "order_payment_codegen_good.puml",
        "codegen",
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("vague_guard", op_vague_guard),
            ("prose_message", op_prose_message),
            ("elision_marker", op_elision_marker),
            ("undeclare_participant", op_undeclare_participant),
            ("unlabel_message", op_unlabel_message),
            ("unbalance_activation", op_unbalance_activation),
            ("unterminate_block", op_unterminate_block),
        ],
        [("self_message", op_self_message)],
    ),
    (
        "loan_decision_activity_good.puml",
        None,
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("noun_activity", op_noun_activity),
            ("unlabel_branch", op_unlabel_branch),
            ("drop_start", op_drop_start),
            ("drop_stop", op_drop_stop),
            ("unterminate_construct", op_unterminate_construct),
        ],
        [],
    ),
]


# ---------------------------------------------------------------------------
# Synthetic boundary probes (expected levels under the default profile)
# ---------------------------------------------------------------------------

def _large_clean(n_pairs: int = 7) -> str:
    lines = ["@startuml large-clean-flow", "title Large clean flow"]
    lines += [f"participant Svc{i}" for i in range(1, n_pairs + 2)]
    for i in range(1, n_pairs + 1):
        lines.append(f"Svc{i} -> Svc{i + 1} : step{i}()")
        lines.append(f"Svc{i + 1} --> Svc{i} : result{i}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


SYNTHETIC = [
    # (name, expected_level, source)
    ("empty", 1, "@startuml empty-model\ntitle Empty model\n@enduml\n"),
    ("prose", 1, "@startuml\nthis is just prose, not a diagram\n@enduml\n"),
    (
        "tiny_clean", 3,
        "@startuml tiny-flow\ntitle Tiny flow\nparticipant Alice\n"
        "Alice -> Alice : check()\n@enduml\n",
    ),
    (
        "small_clean", 4,
        "@startuml small-flow\ntitle Small flow\nparticipant Alice\nparticipant Bob\n"
        "Alice -> Bob : greet()\nBob --> Alice : ack\n@enduml\n",
    ),
    ("large_clean", 4, _large_clean()),
    ("large_no_title", 4, _large_clean().replace("title Large clean flow\n", "")),
]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate(dest: Path, examples_dir: Path = EXAMPLES_DIR) -> dict:
    """Write the corpus under *dest*; return the manifest dict."""
    mutations_dir = dest / "mutations"
    synthetic_dir = dest / "synthetic"
    mutations_dir.mkdir(parents=True, exist_ok=True)
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    units: list[dict] = []

    for example_name, profile, ladder_ops, single_ops in PLANS:
        stem = example_name.replace(".puml", "")
        base_text = (examples_dir / example_name).read_text(encoding="utf-8")
        parent_ref = f"examples/{example_name}"

        # Singles: each operator applied alone to the pristine parent.
        for op_name, op in ladder_ops + single_ops:
            mutated = op(base_text)
            if mutated is None:
                raise ValueError(f"{op_name} does not apply to {example_name}")
            fname = f"{stem}__S-{op_name}.puml"
            (mutations_dir / fname).write_text(mutated, encoding="utf-8")
            units.append({
                "file": f"mutations/{fname}", "tier": "mutation",
                "parent": parent_ref, "ops": [op_name], "profile": profile,
            })

        # Ladder: cumulative degradation; rung 1 IS the first single.
        text = base_text
        prev_ref = parent_ref
        applied: list[str] = []
        for rung, (op_name, op) in enumerate(ladder_ops, start=1):
            text = op(text)
            if text is None:
                raise ValueError(f"ladder op {op_name} failed on {example_name} rung {rung}")
            applied = applied + [op_name]
            if rung == 1:
                prev_ref = f"mutations/{stem}__S-{op_name}.puml"
                continue  # rung 1 == the first single, already written
            fname = f"{stem}__L{rung}.puml"
            (mutations_dir / fname).write_text(text, encoding="utf-8")
            units.append({
                "file": f"mutations/{fname}", "tier": "mutation",
                "parent": prev_ref, "ops": list(applied), "profile": profile,
            })
            prev_ref = f"mutations/{fname}"

    for name, expected, source in SYNTHETIC:
        fname = f"{name}.puml"
        (synthetic_dir / fname).write_text(source, encoding="utf-8")
        units.append({
            "file": f"synthetic/{fname}", "tier": "synthetic",
            "expected_level": expected, "profile": None,
        })

    manifest = {"version": 1, "units": units}
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str]) -> int:
    dest = Path(argv[1]) if len(argv) > 1 else REPO_ROOT / "corpus"
    manifest = generate(dest)
    tiers = {}
    for u in manifest["units"]:
        tiers[u["tier"]] = tiers.get(u["tier"], 0) + 1
    print(f"Wrote {len(manifest['units'])} corpus units to {dest} ({tiers})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
