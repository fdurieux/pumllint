"""mutate.py ID FILE OLD NEW : one exact replacement in mutant ID's copy (FILE relative to the mutant root: src/... or chain/daily.sh)."""
import sys
from pathlib import Path
L = Path("/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/lab")
mid, rel, old, new = sys.argv[1:5]
p = L / "mut" / mid / rel
s = p.read_text()
n = s.count(old)
assert n == 1, f"{p}: expected 1 occurrence, found {n}"
p.write_text(s.replace(old, new))
print(f"{mid}: {rel} patched")
