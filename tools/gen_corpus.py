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


# -- class-diagram operators (shop_classes_good) ----------------------------

def op_drop_multiplicities(text):  # CLS002
    return _sub(r'^(\w+) "[^"]+" -- "[^"]+" (\w+)', r"\1 -- \2", text)


def op_unlabel_association(text):  # CLS003
    return _sub(r'^(\w+ "[^"]+" -- "[^"]+" \w+) : .+$', r"\1", text)


def op_snake_case_class(text):  # CLS001 (renames every occurrence: no new entity)
    if "Product" not in text:
        return None
    return text.replace("Product", "product_catalog")


def op_pascal_member(text):  # CLS001
    if "+placeOrder" not in text:
        return None
    return text.replace("+placeOrder", "+PlaceOrder", 1)


def op_god_class(text):  # CLS005 (members are not elements -> ladder-safe)
    if "+email: String\n" not in text:
        return None
    filler = "".join(f"  +field{i:02d}: String\n" for i in range(1, 15))
    return text.replace("  +email: String\n", "  +email: String\n" + filler, 1)


def op_inheritance_cycle(text):  # CLS004; adds a relation -> singles only
    if "Order ..|> Payable" not in text or "@enduml" not in text:
        return None
    return text.replace("@enduml", "Order <|-- Payable\n@enduml", 1)


# -- state-diagram operators (door_lock_state_good) -------------------------

def op_unlabel_transition(text):  # STA003
    return _sub(r"^(Alarmed --> Locked) : .+$", r"\1", text)


def op_unreachable_state(text):  # STA002 (removes a transition)
    return _sub(r"^Locked --> Alarmed : .+\n", "", text)


def op_drop_initial(text):  # STA001 blocker (removes the initial transition)
    return _sub(r"^\[\*\] --> Locked\n", "", text)


def op_duplicate_initial(text):  # STA001; adds a transition -> singles only
    if "[*] --> Locked" not in text or "@enduml" not in text:
        return None
    return text.replace("@enduml", "[*] --> Unlocked\n@enduml", 1)


# -- use-case operators (webshop_usecase_good) ------------------------------

def op_reverse_extend(text):  # UC003 (same entities, same link count)
    if "(Apply coupon) ..> (Place order) : <<extend>>" not in text:
        return None
    return text.replace(
        "(Apply coupon) ..> (Place order) : <<extend>>",
        "(Place order) ..> (Apply coupon) : <<extend>>",
        1,
    )


def op_orphan_usecase(text):  # UC001 (removes a link)
    return _sub(r"^\(Place order\) \.\.> \(Validate cart\) : <<include>>\n", "", text)


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
    (
        "insurance_claim_good.puml",
        "codegen",
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("vague_guard", op_vague_guard),
            ("undeclare_participant", op_undeclare_participant),
            ("unlabel_message", op_unlabel_message),
            ("unbalance_activation", op_unbalance_activation),
            ("unterminate_block", op_unterminate_block),
        ],
        [("self_message", op_self_message)],
    ),
    (
        "shop_classes_good.puml",
        None,
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("drop_multiplicities", op_drop_multiplicities),
            ("unlabel_association", op_unlabel_association),
            ("snake_case_class", op_snake_case_class),
            ("pascal_member", op_pascal_member),
            ("god_class", op_god_class),
        ],
        [("inheritance_cycle", op_inheritance_cycle)],
    ),
    (
        "door_lock_state_good.puml",
        None,
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("unlabel_transition", op_unlabel_transition),
            ("unreachable_state", op_unreachable_state),
            ("drop_initial", op_drop_initial),
        ],
        [("duplicate_initial", op_duplicate_initial)],
    ),
    (
        "webshop_usecase_good.puml",
        None,
        [
            ("drop_title", op_drop_title),
            ("drop_name", op_drop_name),
            ("reverse_extend", op_reverse_extend),
            ("orphan_usecase", op_orphan_usecase),
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
    # Per-type clean probes (v0.14.0): the non-sequence parsers must carry a
    # clean diagram to Level 4 exactly like the sequence path does.
    (
        "class_clean", 4,
        "@startuml class-clean\ntitle Class clean\nclass Customer\nclass Order\n"
        'Customer "1" -- "0..*" Order : places\n@enduml\n',
    ),
    (
        "state_clean", 4,
        "@startuml state-clean\ntitle State clean\n[*] --> Idle\n"
        "Idle --> Busy : work\nBusy --> Idle : done\nBusy --> [*]\n@enduml\n",
    ),
    (
        "usecase_clean", 4,
        "@startuml usecase-clean\ntitle Usecase clean\n:Shopper: as Shopper\n"
        "usecase (Browse catalog)\nusecase (Place order)\n"
        "Shopper --> (Browse catalog) : starts\n"
        "Shopper --> (Place order) : completes\n@enduml\n",
    ),
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

    # Prune stale files from previous generator versions so the on-disk corpus
    # always matches the manifest exactly.
    valid = {u["file"] for u in units}
    for sub in ("mutations", "synthetic"):
        for stray in (dest / sub).glob("*.puml"):
            if f"{sub}/{stray.name}" not in valid:
                stray.unlink()

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
