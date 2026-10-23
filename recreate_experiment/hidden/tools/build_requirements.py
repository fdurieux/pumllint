"""Assemble kit/requirements.json and hidden/provenance.json from the parts."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from reqs_part1 import R1
from reqs_part2 import R2
from reqs_part3 import R3
from reqs_part4 import R4

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALL = R1 + R2 + R3 + R4
keys = [r[0] for r in ALL]
assert len(keys) == len(set(keys)), [k for k in keys if keys.count(k) > 1]
ids = {k: f"JDL-{i + 1:03d}" for i, k in enumerate(keys)}


def resolve(text):
    # cross-references written as {{key}} become ids
    for k, v in ids.items():
        text = text.replace("{{" + k + "}}", v)
    return text


reqs, prov = [], {}
for key, kind, statement, basis, rationale, (f, sym, lines) in ALL:
    entry = {"id": ids[key], "kind": kind, "statement": resolve(statement), "basis": basis}
    if rationale:
        entry["rationale"] = rationale
    reqs.append(entry)
    import re as _re
    nums = [int(x) for x in _re.findall(r"\d+", lines)]
    prov[ids[key]] = {"file": f, "symbol": sym, "lines": f"{min(nums)}-{max(nums)}",
                      "ranges": lines, "basis": basis, "key": key}
with open(os.path.join(ROOT, "kit", "requirements.json"), "w") as fh:
    json.dump(reqs, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
with open(os.path.join(ROOT, "hidden", "provenance.json"), "w") as fh:
    json.dump(prov, fh, indent=1)
    fh.write("\n")
with open(os.path.join(ROOT, "hidden", "idmap.json"), "w") as fh:
    json.dump(ids, fh, indent=1)
from collections import Counter
print(len(reqs), Counter(r["kind"] for r in reqs), Counter(r["basis"] for r in reqs))
for k, v in ids.items():
    print(v, k)
