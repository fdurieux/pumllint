"""Recurring terms of the requirements and whether the kit defines them.

    glossary_check.py <kit_dir> [--no-glossary] [--min-uses 3]

The vocabulary under check is VOCAB below (the measurement instrument,
committed with the result). A term "recurs" when it appears, as a whole
word or phrase (case-insensitive, optional plural s), in at least
--min-uses requirement statements of kit/requirements.json. A term is
"defined" when kit/contracts/glossary.md has a table row whose first cell
is the term (`| term |`), or any other contract defines it with a bold
lead (`**term**` opening a line or bullet) or a heading naming it. With
--no-glossary the glossary file is ignored: the "before" measurement.
Exit 0 when every recurring term is defined.
"""
import json
import re
import sys
from pathlib import Path

VOCAB = [
    "leg", "series", "price_basis", "basis", "tail", "window", "end-guard",
    "stamp", "seam frame", "raw columns", "cumulative split factor",
    "revision", "verdict", "alert", "warning", "note", "modeled",
    "enabled", "first fill", "tail refresh", "reconcile", "re-adjust",
    "store coordinate", "universe", "source", "asset", "collector",
    "transport", "fixture", "refusal", "wrapped", "traceback",
    "actions-eligible", "declared asset_type", "split event", "dividend",
    "expected session", "staleness", "phantom", "spread", "pair",
    "resolution", "today", "dry run", "summary document", "plan",
    "chain", "stage", "corporate actions", "year file", "lock",
    "adjustment_factor", "adjusted_close", "volume basis", "page limit",
    "replay", "run clock", "store", "exchange tag", "normalise",
]


def recurring(kit, min_uses):
    reqs = json.load(open(kit / "requirements.json", encoding="utf-8"))
    counts = {}
    for term in VOCAB:
        pat = re.compile(r"(?<![\w-])" + re.escape(term).replace(r"\ ", r"[\s-]") + r"(?:s|es)?(?![\w-])", re.I)
        counts[term] = sum(1 for r in reqs if pat.search(r["statement"]))
    return {t: n for t, n in counts.items() if n >= min_uses}


def defined_terms(kit, use_glossary):
    found = set()
    for f in sorted((kit / "contracts").glob("*.md")):
        if f.name == "glossary.md" and not use_glossary:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            m = re.match(r"^\|\s*`?([^|`]+?)`?\s*\|", s) if f.name == "glossary.md" else None
            if m:
                found.add(m.group(1).strip().lower())
            m = re.match(r"^(?:[-*]\s+)?\*\*`?([^*`]+?)`?\*\*", s)
            if m:
                found.add(m.group(1).strip().lower())
            m = re.match(r"^#{1,4}\s+(.+)$", s)
            if m:
                found.add(m.group(1).strip().lower())
    return found


def is_defined(term, found):
    t = term.lower()
    return any(t == d or t + "s" == d or d.startswith(t + " (") or d.startswith(t + ",") for d in found)


def main(argv):
    kit = Path(argv[1])
    min_uses = int(argv[argv.index("--min-uses") + 1]) if "--min-uses" in argv else 3
    use_glossary = "--no-glossary" not in argv
    rec = recurring(kit, min_uses)
    found = defined_terms(kit, use_glossary)
    undefined = {t: n for t, n in rec.items() if not is_defined(t, found)}
    print(f"{len(rec)} of {len(VOCAB)} vocabulary terms recur in >= {min_uses} requirements"
          f" ({'with' if use_glossary else 'WITHOUT'} glossary.md)")
    for t, n in sorted(rec.items(), key=lambda x: -x[1]):
        print(f"  {'UNDEFINED' if t in undefined else 'defined  '} {n:3d}  {t}")
    print(f"UNDEFINED: {len(undefined)}")
    return 1 if undefined else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
