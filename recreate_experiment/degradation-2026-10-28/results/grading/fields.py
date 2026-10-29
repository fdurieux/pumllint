"""Field by field, for every OTHER artefact r6.json lists: does the rebuild's exit code, stdout and stderr
equal the reference's, the mutant's and the combined mutant's? Where stderr differs from the mutant's,
print the lines only the rebuild has, its arm directory written <rc>. Usage: fields.py <lab>"""
import json, sys
from pathlib import Path
L = Path(sys.argv[1]); G = L / "grade"
ARMS = dict(line.split() for line in (L / "arms.map").read_text().splitlines() if line.strip())
COMBINED = {"D3": "D3-all", "D5": "D5-all"}
def cli(p):
    return json.loads(p.read_text()) if p.exists() else None
for row in json.loads((G / "r6.json").read_text())["artefacts"]:
    if row["verdict"] != "OTHER":
        continue
    a, arm = row["artefact"], row["arm"]
    rc = cli(G / "arms" / arm / "run" / a)
    sides = {"reference": cli(G / "ref" / a), "mutant " + row["mutant"]: cli(G / "mut" / row["mutant"] / "run" / a)}
    if arm in COMBINED:
        sides["combined " + COMBINED[arm]] = cli(G / "mut" / COMBINED[arm] / "run" / a)
    print(f"{arm}-{row['slot']} {a}")
    for name, other in sides.items():
        same = {k: rc.get(k) == other.get(k) for k in ("exit", "stdout", "stderr")}
        print(f"  vs {name}: " + ", ".join(f"{k} {'equal' if v else 'differs'}" for k, v in same.items()))
    mut = sides["mutant " + row["mutant"]]
    extra = [x for x in rc["stderr"].splitlines() if x not in mut["stderr"].splitlines()]
    for x in extra:
        print("  stderr only in the rebuild: " + x.replace(ARMS[arm], "<rc>"))
