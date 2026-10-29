#!/bin/bash
. "$(dirname "$0")/env.sh"
M=$L/mut/$1
BASE=$L/mut/null; [[ -d "$M/chain" ]] && BASE=$L/mut/nullc
python "$H/compare.py" "$BASE/run" "$M/run" --out "$M/compare.json" > /dev/null 2>&1
python "$H/compare.py" "$L/ref_run1" "$M/run" --out "$M/compare_ref.json" > /dev/null 2>&1
python - "$M" <<'PY'
import json, sys
M = sys.argv[1]
c = json.load(open(f"{M}/compare.json"))
k2 = {a['artefact'] for a in json.load(open('/home/user/pumllint/recreate_experiment/results/K2/compare.json'))['artefacts'] if a['verdict'] == 'identical'}
obs = sorted(a['artefact'] for a in c['artefacts'] if a['verdict'] != 'identical')
outside = [a for a in obs if a not in k2]
json.dump({"observing": obs, "outside_k2_identical": outside}, open(f"{M}/observing.json", "w"), indent=1)
print(f"observing {len(obs)}; outside K2-identical {len(outside)}")
for a in obs: print("  ", a, "" if a in k2 else "(outside)")
PY
