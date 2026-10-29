"""Format an expected-frame document exactly like the kit's fixtures/expected/*.json files."""
import json, math, sys

def fmt_value(v):
    if isinstance(v, float) and math.isnan(v):
        return "NaN"
    return json.dumps(v, ensure_ascii=False)

def dumps(doc):
    lines = ['{"columns": ' + json.dumps(doc["columns"], ensure_ascii=False) + ",",
             ' "dtypes": ' + json.dumps(doc["dtypes"], ensure_ascii=False) + ",",
             ' "data": [']
    rows = doc["data"]
    for i, row in enumerate(rows):
        lines.append("  [" + ", ".join(fmt_value(v) for v in row) + "]" + ("," if i < len(rows) - 1 else ""))
    lines.append(" ]}")
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        text = open(p, encoding="utf-8").read()
        if dumps(json.loads(text)) != text:
            bad += 1; print("DIFF", p)
    print("checked", len(sys.argv) - 1, "bad", bad)
