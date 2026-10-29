#!/bin/bash
# mkmut.sh ID : a fresh copy of the subject's src as mutant ID, with a jef-data wrapper
. "$(dirname "$0")/env.sh"
M=$L/mut/$1; rm -rf "$M"; mkdir -p "$M/bin"
cp -a "$JF/src" "$M/src"; find "$M/src" -name __pycache__ -prune -exec rm -rf {} +
cat > "$M/bin/jef-data" <<PY
#!/home/user/.jf-venv/bin/python
import sys
sys.path.insert(0, "$M/src")
from jef.data.cli import main
sys.exit(main())
PY
chmod +x "$M/bin/jef-data"; echo "$M"
