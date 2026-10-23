"""Join the DMN tables to the decisions feature: which rule has an example.

    dmn_coverage.py <kit_dir> [--existing]

Reads kit/contracts/dmn/*.dmn (rule ids <table>_rN with their cited
requirements in the rule description) and kit/features/decisions.feature
(`Rule: <table>` blocks; Examples rows' `row` column, `# dmn-row: rN`
comments). Prints per table the rows with and without an example. With
--existing, also joins the OTHER features' @JDL tags to each rule's cited
requirement ids: a rule none of whose cited requirements is tagged by any
scenario outside decisions.feature was unreachable, even at requirement
granularity, before wave 2 (requirement-level tagging over-approximates
row coverage, so this count is a lower bound).
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"dmn": "https://www.omg.org/spec/DMN/20191111/MODEL/"}


def dmn_rules(dmn_dir):
    out = {}
    for f in sorted(Path(dmn_dir).glob("*.dmn")):
        root = ET.parse(f).getroot()
        for dec in root.findall("dmn:decision", NS):
            name = dec.get("name")
            rules = []
            for r in dec.findall("dmn:decisionTable/dmn:rule", NS):
                d = r.find("dmn:description", NS)
                text = d.text if d is not None else ""
                rules.append((r.get("id").split("_r")[-1], set(re.findall(r"JDL-\d{3}", text)), text))
            out[name] = rules
    return out


def feature_rows(feature):
    """{table: set(rN)} from Rule blocks."""
    cov, table, header = {}, None, None
    for line in Path(feature).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        m = re.match(r"^Rule:\s*(\S+)", s)
        if m:
            table, header = m.group(1), None
            cov.setdefault(table, set())
            continue
        m = re.match(r"^#\s*dmn-row:\s*(r\d+)", s)
        if m and table:
            cov[table].add(m.group(1))
            continue
        if s.startswith("|") and table:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[0] == "row":
                header = cells
                continue
            if header and header[0] == "row" and re.fullmatch(r"r\d+", cells[0]):
                cov[table].add(cells[0])
                continue
        if s.startswith("Scenario") or s.startswith("Examples"):
            header = None
    return cov


def existing_tags(features_dir, skip="decisions.feature"):
    tags = set()
    for f in Path(features_dir).glob("*.feature"):
        if f.name == skip:
            continue
        tags |= set(re.findall(r"@(JDL-\d{3})", f.read_text(encoding="utf-8")))
    return tags


def main(argv):
    kit = Path(argv[1])
    rules = dmn_rules(kit / "contracts" / "dmn")
    cov = feature_rows(kit / "features" / "decisions.feature")
    tags = existing_tags(kit / "features") if "--existing" in argv else None
    total = covered = unreached = 0
    for table, rs in rules.items():
        have = cov.get(table, set())
        missing = [f"r{rid}" for rid, _, _ in rs if f"r{rid}" not in have]
        unknown = sorted(have - {f"r{rid}" for rid, _, _ in rs})
        total += len(rs)
        covered += len(rs) - len(missing)
        line = f"{table}: {len(rs) - len(missing)}/{len(rs)} rows exercised"
        if missing:
            line += f"; no example: {', '.join(missing)}"
        if unknown:
            line += f"; examples naming no rule: {', '.join(unknown)}"
        if tags is not None:
            cold = [f"r{rid}" for rid, req, _ in rs if not (req & tags)]
            unreached += len(cold)
            if cold:
                line += f"; untouched by the other features (no cited id tagged): {', '.join(cold)}"
        print(line)
    print(f"TOTAL {covered}/{total} rows exercised by decisions.feature")
    if tags is not None:
        print(f"TOTAL {unreached}/{total} rows whose cited requirements no other feature tags (lower bound of rows the existing scenarios never exercised)")
    return 0 if covered + 3 >= total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
