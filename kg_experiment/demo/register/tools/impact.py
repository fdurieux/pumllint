"""Walk the typed edges from a node and print each with its state, owner and evidence; stop at a
deprecated or retired node. The IEAM's own question: which journeys and products would be
affected by retiring this module?

    python tools/impact.py --from APP-0002
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from register import ROOT, load_register  # noqa: E402

# how impact travels: (relationship, follow from source to target?) per step
FORWARD = {
    "applications": [("supports", True)],
    "processes": [("delivers", True), ("is_supported_by", False), ("realizes", True)],
    "journeys": [("concerns", True)],
}


def walk(reg: dict, start: str) -> list[dict]:
    seen, out, frontier = {start}, [], [start]
    while frontier:
        nxt = []
        for nid in frontier:
            n = reg["nodes"].get(nid)
            if n is None or n.get("state") in ("deprecated", "retired"):
                continue
            for rel, forward in FORWARD.get(n["_taxonomy"], []):
                for ln in reg["relationships"].get(rel, {}).get("links", []):
                    a, b = (ln["source"], ln.get("target")) if forward else (ln.get("target"), ln["source"])
                    if a != nid or b is None:
                        continue
                    out.append({"from": nid, "rel": rel if forward else f"{rel} (inverse)", "to": b, "state": ln.get("state"), "owner": ln.get("owner"), "evidence": ln.get("evidence", [])})
                    if b not in seen:
                        seen.add(b)
                        nxt.append(b)
        frontier = nxt
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--root", type=Path, default=ROOT)
    a = ap.parse_args(argv)
    reg = load_register(a.root)
    if a.start not in reg["nodes"]:
        print(f"{a.start}: no such node")
        return 2
    edges = walk(reg, a.start)
    for e in edges:
        n = reg["nodes"][e["to"]]
        print(f"{e['from']} -[{e['rel']}, {e['state']}, owner {e['owner']}]-> {e['to']} {n['name']!r} ({n['state']}); evidence: {', '.join(e['evidence']) or 'none'}")
    reached = {e["to"] for e in edges}
    prods = sorted(x for x in reached if x.startswith("PRD-"))
    jrns = sorted(x for x in reached if x.startswith("JRN-"))
    print(f"\n{a.start}: {len(edges)} edges walked; products reached {prods or 'none'}; journey elements reached {jrns or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
