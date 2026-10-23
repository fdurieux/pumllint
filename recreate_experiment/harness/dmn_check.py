"""Completeness and typing check for DMN 1.3 decision tables (stdlib only).

For every table: enumerate the input space - finite domains (inputValues)
exhaustively, numeric domains by the interval partition the rules' constants
induce plus the boundary points - and report GAPS (no rule matches), OVERLAPS
(several rules match under UNIQUE), and UNTYPED OUTPUT cells (an output with
declared outputValues whose entry is not one of them, or an entry that is not a
quoted literal where every other entry is). FEEL subset: quoted literals and
comma lists, `-`, comparisons (<, <=, >, >=), ranges [a..b] (a..b) etc.,
true/false, `not(...)` over a literal list.

    dmn_check.py FILE_OR_DIR [--json out.json]
"""
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"dmn": "https://www.omg.org/spec/DMN/20191111/MODEL/"}


def q(tag):
    return f"{{{NS['dmn']}}}{tag}"


def literals(text):
    return [t.strip().strip('"') for t in re.findall(r'"[^"]*"', text)]


def parse_entry(text):
    text = (text or "-").strip()
    if text in ("", "-"):
        return ("any",)
    if text in ("true", "false"):
        return ("lit", [text])
    m = re.match(r"^not\s*\((.*)\)$", text)
    if m:
        return ("notlit", literals(m.group(1)))
    if text.startswith('"'):
        return ("lit", literals(text))
    m = re.match(r"^([<>]=?)\s*(-?\d+(?:\.\d+)?)$", text)
    if m:
        return ("cmp", m.group(1), float(m.group(2)))
    m = re.match(r"^([\[\(])\s*(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)\s*([\]\)])$", text)
    if m:
        return ("range", m.group(1) == "[", float(m.group(2)), float(m.group(3)), m.group(4) == "]")
    m = re.match(r"^-?\d+(?:\.\d+)?$", text)
    if m:
        return ("num", float(text))
    return ("raw", text)


def matches(entry, value):
    kind = entry[0]
    if kind == "any":
        return True
    if kind == "lit":
        return str(value) in entry[1]
    if kind == "notlit":
        return str(value) not in entry[1]
    if kind == "cmp":
        op, c = entry[1], entry[2]
        return {"<": value < c, "<=": value <= c, ">": value > c, ">=": value >= c}[op]
    if kind == "range":
        _, lo_in, lo, hi, hi_in = entry
        return (lo <= value if lo_in else lo < value) and (value <= hi if hi_in else value < hi)
    if kind == "num":
        return value == entry[1]
    raise ValueError(f"unsupported FEEL entry {entry[1]!r}")


def domain_points(column_entries, declared_values, type_ref, constraint=None):
    """Representative points of one input's domain.

    `constraint` is a numeric inputValues expression (`>= 0`, `[0..10]`): the
    partition is restricted to the points satisfying it. typeRef `integer`
    samples integer points only (midpoint a+1 when the interval holds one)."""
    if declared_values:
        return list(declared_values), "finite"
    if type_ref == "boolean":
        return ["true", "false"], "finite"
    integer = type_ref == "integer"
    consts = sorted({c for e in column_entries for c in
                     ([e[2]] if e[0] == "cmp" else [e[2], e[3]] if e[0] == "range" else [e[1]] if e[0] == "num" else [])})
    if not consts:
        lits = sorted({v for e in column_entries if e[0] in ("lit", "notlit") for v in e[1]})
        return lits + ["<other>"], "finite-from-rules"
    if constraint is not None:
        consts = sorted(set(consts) | {c for c in ([constraint[2]] if constraint[0] == "cmp" else [constraint[2], constraint[3]] if constraint[0] == "range" else [])})
    pts = [consts[0] - 1]
    for a, b in zip(consts, consts[1:]):
        pts.append(a)
        mid = a + 1 if integer else (a + b) / 2
        if mid < b:
            pts.append(mid)
    pts.append(consts[-1])
    pts.append(consts[-1] + 1)
    if constraint is not None:
        pts = [v for v in pts if matches(constraint, v)]
    return pts, "interval-partition" + ("-integer" if integer else "") + ("-constrained" if constraint is not None else "")


def check_table(dt, name):
    inputs = []
    for inp in dt.findall("dmn:input", NS):
        label = inp.get("label") or inp.find("dmn:inputExpression/dmn:text", NS).text
        type_ref = (inp.find("dmn:inputExpression", NS).get("typeRef") or "").lower()
        iv = inp.find("dmn:inputValues/dmn:text", NS)
        values, constraint = [], None
        if iv is not None:
            if iv.text.strip().startswith('"'):
                values = literals(iv.text)
            else:
                constraint = parse_entry(iv.text)
        inputs.append({"label": label, "type": type_ref, "values": values, "constraint": constraint})
    outputs = []
    for out in dt.findall("dmn:output", NS):
        ov = out.find("dmn:outputValues/dmn:text", NS)
        outputs.append({"label": out.get("label") or out.get("name"), "values": literals(ov.text) if ov is not None else [],
                        "type": (out.get("typeRef") or "").lower()})
    rules = []
    for r in dt.findall("dmn:rule", NS):
        ins = [parse_entry(e.find("dmn:text", NS).text) for e in r.findall("dmn:inputEntry", NS)]
        outs = [(e.find("dmn:text", NS).text or "").strip() for e in r.findall("dmn:outputEntry", NS)]
        rules.append({"id": r.get("id"), "in": ins, "out": outs})
    hit = dt.get("hitPolicy", "UNIQUE")
    # output typing
    untyped = []
    for ri, r in enumerate(rules):
        for oi, cell in enumerate(r["out"]):
            o = outputs[oi]
            is_literal = cell.startswith('"') and cell.endswith('"') or cell in ("true", "false") or re.match(r"^-?\d+(\.\d+)?$", cell)
            if o["values"] and (not is_literal or literals(cell) and literals(cell)[0] not in o["values"]):
                untyped.append({"rule": r["id"], "output": o["label"], "cell": cell, "why": "not one of the declared output values"})
            elif not o["values"] and not is_literal and cell not in ("", "-"):
                untyped.append({"rule": r["id"], "output": o["label"], "cell": cell, "why": "not a literal: a category where other cells carry a value"})
    # input space
    axes, kinds = [], []
    for ci, inp in enumerate(inputs):
        pts, kind = domain_points([r["in"][ci] for r in rules], inp["values"], inp["type"], inp["constraint"])
        axes.append(pts)
        kinds.append(kind)
    gaps, overlaps = [], []
    total = 0
    for combo in itertools.product(*axes):
        total += 1
        hits = [r["id"] for r in rules if all(matches(e, v) for e, v in zip(r["in"], combo))]
        point = {inp["label"]: v for inp, v in zip(inputs, combo)}
        if not hits:
            gaps.append(point)
        elif len(hits) > 1 and hit == "UNIQUE":
            overlaps.append({"point": point, "rules": hits})
    return {"table": name, "hit_policy": hit, "inputs": [i["label"] for i in inputs], "domains": kinds,
            "rules": len(rules), "points": total, "gaps": gaps, "overlaps": overlaps, "untyped_outputs": untyped}


def check_file(path):
    root = ET.parse(path).getroot()
    out = []
    for dec in root.findall("dmn:decision", NS):
        dt = dec.find("dmn:decisionTable", NS)
        if dt is not None:
            out.append(check_table(dt, dec.get("name") or dec.get("id")))
    return out


def main(argv):
    target = Path(argv[1])
    files = sorted(target.glob("*.dmn")) if target.is_dir() else [target]
    report = []
    for f in files:
        for t in check_file(f):
            t["file"] = f.name
            report.append(t)
    for t in report:
        flag = "OK " if not (t["gaps"] or t["overlaps"] or t["untyped_outputs"]) else "!! "
        print(f"{flag}{t['file']} :: {t['table']} [{t['hit_policy']}] rules={t['rules']} points={t['points']} "
              f"gaps={len(t['gaps'])} overlaps={len(t['overlaps'])} untyped={len(t['untyped_outputs'])}")
        for g in t["gaps"][:12]:
            print("     gap     ", g)
        for o in t["overlaps"][:6]:
            print("     overlap ", o)
        for u in t["untyped_outputs"][:6]:
            print("     untyped ", u)
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(report, indent=1))
    return 1 if any(t["gaps"] or t["overlaps"] or t["untyped_outputs"] for t in report) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
