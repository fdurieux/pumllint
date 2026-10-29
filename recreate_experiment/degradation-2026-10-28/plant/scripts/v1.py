"""V1: each degraded kit differs from the pristine kit only in its arm's permitted layers."""
import filecmp, os, sys
from pathlib import Path
L = Path(sys.argv[1]); REF = L / "kit_ref"
NEVER = ["README.md", "features/README.md", "pumllint.toml", "tools/", "contracts/externals/", "contracts/HARNESS_INTERFACE.md"]
def layer(p):
    if p.startswith("features/"): return "L1"
    if p == "requirements.json": return "L2"
    if p.startswith("contracts/dmn/") or p == "contracts/glossary.md": return "L4"
    if p.startswith("contracts/") or p == "CHANGES.md": return "L3"
    if p.startswith("uml/"): return "L5"
    return "other"
ALLOWED = {"D1": {"L5"}, "D2": {"L2", "L3", "L4"}, "D3": {"L1", "L2", "L3", "L4", "L5"}, "D4": {"L1"}, "D5": {"L1", "L2", "L3", "L4", "L5"}}
def files(root):
    out = set()
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".pytest_cache")]
        for f in fn:
            if f.endswith(".pyc"): continue
            out.add(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    return out
ok = True
ref = files(REF)
for arm, allowed in ALLOWED.items():
    kit = L / "plant" / "kits" / arm; got = files(kit)
    changed = sorted(p for p in (ref | got) - {"MANIFEST.sha256"}
                     if p not in ref or p not in got or not filecmp.cmp(REF / p, kit / p, shallow=False))
    layers = {}
    for p in changed: layers.setdefault(layer(p), []).append(p)
    bad = [p for p in changed if layer(p) not in allowed or any(p == n or p.startswith(n) for n in NEVER)]
    ok &= not bad
    print(arm, {k: len(v) for k, v in sorted(layers.items())}, "added:", sorted(got - ref), "removed:", sorted(ref - got), "VIOLATIONS:" if bad else "ok", bad or "")
print("V1", "pass" if ok else "FAIL")
