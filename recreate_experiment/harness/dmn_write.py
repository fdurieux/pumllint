"""Write DMN 1.3 decision tables from compact Python specs (lab tooling)."""
import xml.etree.ElementTree as ET
from xml.dom import minidom

NS = "https://www.omg.org/spec/DMN/20191111/MODEL/"


def table(name, inputs, outputs, rules, hit="UNIQUE", description=""):
    """inputs: [(label, typeRef, [allowed]|"<numeric constraint>"|None)]; outputs: [(label, typeRef, [allowed]|None)];
    rules: [([inputEntry...], [outputEntry...], annotation)]"""
    return {"name": name, "inputs": inputs, "outputs": outputs, "rules": rules, "hit": hit, "description": description}


def write(path, tables, ns_id):
    ET.register_namespace("", NS)
    defs = ET.Element(f"{{{NS}}}definitions", {"id": ns_id, "name": ns_id, "namespace": f"urn:recreate-experiment:{ns_id}"})
    for t in tables:
        dec = ET.SubElement(defs, f"{{{NS}}}decision", {"id": t["name"], "name": t["name"]})
        if t["description"]:
            ET.SubElement(dec, f"{{{NS}}}description").text = t["description"]
        dt = ET.SubElement(dec, f"{{{NS}}}decisionTable", {"id": t["name"] + "_dt", "hitPolicy": t["hit"]})
        for i, (label, typ, allowed) in enumerate(t["inputs"]):
            inp = ET.SubElement(dt, f"{{{NS}}}input", {"id": f"{t['name']}_i{i}", "label": label})
            ie = ET.SubElement(inp, f"{{{NS}}}inputExpression", {"id": f"{t['name']}_ie{i}", "typeRef": typ})
            ET.SubElement(ie, f"{{{NS}}}text").text = label
            if allowed:
                iv = ET.SubElement(inp, f"{{{NS}}}inputValues", {"id": f"{t['name']}_iv{i}"})
                ET.SubElement(iv, f"{{{NS}}}text").text = allowed if isinstance(allowed, str) else ", ".join(f'"{a}"' for a in allowed)
        for i, (label, typ, allowed) in enumerate(t["outputs"]):
            out = ET.SubElement(dt, f"{{{NS}}}output", {"id": f"{t['name']}_o{i}", "label": label, "name": label, "typeRef": typ})
            if allowed:
                ov = ET.SubElement(out, f"{{{NS}}}outputValues", {"id": f"{t['name']}_ov{i}"})
                ET.SubElement(ov, f"{{{NS}}}text").text = ", ".join(f'"{a}"' for a in allowed)
        for ri, (ins, outs, note) in enumerate(t["rules"], 1):
            r = ET.SubElement(dt, f"{{{NS}}}rule", {"id": f"{t['name']}_r{ri}"})
            if note:
                ET.SubElement(r, f"{{{NS}}}description").text = note
            for k, e in enumerate(ins):
                ie = ET.SubElement(r, f"{{{NS}}}inputEntry", {"id": f"{t['name']}_r{ri}_i{k}"})
                ET.SubElement(ie, f"{{{NS}}}text").text = e
            for k, e in enumerate(outs):
                oe = ET.SubElement(r, f"{{{NS}}}outputEntry", {"id": f"{t['name']}_r{ri}_o{k}"})
                ET.SubElement(oe, f"{{{NS}}}text").text = e
    xml = minidom.parseString(ET.tostring(defs)).toprettyxml(indent="  ")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
