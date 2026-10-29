#!/bin/bash
# grade_ref.sh : today's reference run (the original, as the frozen manifest was made) into $L/grade/ref
. "$(dirname "$0")/env.sh"
G=$L/grade
PYTHONPATH="$H" python "$H/run_impl.py" --adapter adapters.original --exe jef-data \
  --chain "$JF/deploy/daily.sh" --inputs "$L/inputs" --out "$G/ref" > "$G/ref.log" 2>&1
python - "$G/ref" <<'PY'
import hashlib, json, sys
from pathlib import Path
ref = Path(sys.argv[1]); man = json.load(open("/home/user/pumllint/recreate_experiment/harness/REFERENCE.MANIFEST.sha256.json"))
got = {p.relative_to(ref).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in ref.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256.json"}
same = sorted(k for k in man if got.get(k) == man[k]); diff = sorted(k for k in man if got.get(k) != man[k])
print(f"reference re-run: {len(got)} artefacts; {len(same)} of {len(man)} match the frozen manifest; differ: {diff}")
PY
