"""edit.py KIT SPEC.json : apply exact replacements to a kit copy; each must match exactly `count` times."""
import json, sys, pathlib
kit = pathlib.Path(sys.argv[1]); spec = json.load(open(sys.argv[2]))
for e in spec:
    p = kit / e["file"]; s = p.read_text(encoding="utf-8")
    n = s.count(e["old"]); want = e.get("count", 1)
    assert n == want, f'{e["file"]}: {n} matches, want {want}: {e["old"][:80]!r}'
    p.write_text(s.replace(e["old"], e["new"]), encoding="utf-8")
    print(f'{e["file"]}: {n} replaced')
