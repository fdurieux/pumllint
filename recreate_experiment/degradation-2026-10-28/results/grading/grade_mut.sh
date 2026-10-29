#!/bin/bash
# grade_mut.sh ID : today's run of mutant ID into $L/grade/mut/ID, its root path normalised to <mut> as in the walk
. "$(dirname "$0")/env.sh"
M=$L/mut/$1; O=$L/grade/mut/$1; mkdir -p "$O"
CHAIN=$JF/deploy/daily.sh; [[ -f "$M/chain/daily.sh" ]] && CHAIN=$M/chain/daily.sh
PYTHONPATH="$M/src:$H" python "$H/run_impl.py" --adapter adapters.original --exe "$M/bin/jef-data" \
  --chain "$CHAIN" --inputs "$L/inputs" --out "$O/run" > "$O/run.log" 2>&1
python - "$M" "$O" <<'PY'
import sys
from pathlib import Path
M, O = sys.argv[1], Path(sys.argv[2])
for p in (O / "run").rglob("*"):
    if p.is_file():
        t = p.read_text()
        if M in t:
            p.write_text(t.replace(M, "<mut>"))
PY
echo "$1 done"
