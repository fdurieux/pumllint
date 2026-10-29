#!/bin/bash
# renorm.sh ID : normalise the mutant root path in an existing run, then recompute the observing set
. "$(dirname "$0")/env.sh"
M=$L/mut/$1
python - "$M" <<'PY'
import sys
from pathlib import Path
M = Path(sys.argv[1])
for p in (M / "run").rglob("*"):
    if p.is_file():
        t = p.read_text()
        if str(M) in t:
            p.write_text(t.replace(str(M), "<mut>"))
PY
