"""Deterministic extraction: kit text -> fragments, entities, assertions.

One extractor per artefact family, each a hand-written mapper for this
kit (the aris2puml shape: parse what is there, invent nothing, and when
a value cannot be read, record the raw text so a rule can flag it).

An assertion is a dict:
  id, entity, predicate, value, text, basis, artefact, fragments (ids)
A fragment: id, artefact, locator, text.  An entity: id, kind, name.

Keys are ``entity|predicate``. Behaviour values are ``k=v;k=v`` strings
over the fields the artefact states; numeric values are strings of the
number; a documented absence is the sentinel ``NONE``.
"""

from __future__ import annotations

import ast
import re
import tomllib
import xml.etree.ElementTree as ET

import yaml

NONE = "NONE"


class Bag:
    def __init__(self, artefact: str):
        self.artefact = artefact
        self.fragments: list[dict] = []
        self.entities: dict[str, dict] = {}
        self.assertions: list[dict] = []
        self._n = {}

    def frag(self, locator: str, text: str) -> str:
        fid = f"F:{self.artefact}:{locator}"
        self.fragments.append({"id": fid, "artefact": self.artefact,
                               "locator": locator, "text": text.strip()})
        return fid

    def ent(self, eid: str, kind: str, name: str | None = None) -> str:
        self.entities.setdefault(eid, {"id": eid, "kind": kind, "name": name or eid})
        return eid

    def assertion(self, entity: str, predicate: str, value, text: str,
                  frags: list[str], basis: str = "extracted") -> dict:
        key = f"{entity}|{predicate}"
        n = self._n.get(key, 0)
        self._n[key] = n + 1
        aid = f"A:{self.artefact}:{key}" + (f"#{n}" if n else "")
        a = {"id": aid, "entity": entity, "predicate": predicate,
             "value": str(value), "text": text.strip(), "basis": basis,
             "artefact": self.artefact, "fragments": list(frags)}
        self.assertions.append(a)
        return a


_SHORT = {
    "kit/requirements.md": "req", "contract/decision_table.md": "dt",
    "contract/spec.md": "spec", "contract/openapi.yaml": "oas",
    "behavior/quote_flow.puml": "seq", "structure/containers.puml": "c4",
    "kit/quote_process.bpmn": "bpmn", "kit/screening_decision.dmn": "dmn",
    "tests_input/acceptance.feature": "gherkin", "kit/links.toml": "links",
}


def short(path: str) -> str:
    return _SHORT[path]


# ---------------------------------------------------------------- helpers

def _num(s: str):
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*", s)
    return m.group(1) if m else None


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """(1-based start line, paragraph text) for blank-line-separated blocks."""
    out, buf, start = [], [], None
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip():
            if start is None:
                start = i
            buf.append(line)
        elif buf:
            out.append((start, "\n".join(buf)))
            buf, start = [], None
    if buf:
        out.append((start, "\n".join(buf)))
    return out


def _numbered_items(text: str) -> list[tuple[int, str, str]]:
    """(1-based line, number, body) for items of the form ``n. body`` that
    continue over indented lines, in order of appearance."""
    out = []
    cur = None
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"(\d+)\. (.*)", line)
        if m:
            if cur:
                out.append(cur)
            cur = [i, m.group(1), m.group(2)]
        elif cur and line.startswith("   ") and line.strip():
            cur[2] += " " + line.strip()
        else:
            if cur:
                out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return [tuple(x) for x in out]


def _behaviour_tokens(*, priced=None, status=None, notified=None, hold=None,
                      screen=None, store=None) -> str:
    parts = []
    for k, v in (("priced", priced), ("status", status), ("notified", notified),
                 ("hold", hold), ("screen", screen), ("store", store)):
        if v is not None:
            parts.append(f"{k}={v}")
    return ";".join(parts)


# ---------------------------------------------------------- requirements

def extract_requirements(path: str, text: str) -> Bag:
    b = Bag(short(path))
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\|\s*(REQ-\d+)\s*\|\s*(.+?)\s*\|\s*$", line)
        if not m:
            continue
        rid, body = m.group(1), m.group(2)
        f = b.frag(f"row/{rid}", line)
        b.ent(rid, "requirement", rid)
        if "NOT YET SPECIFIED" in body:
            b.assertion(rid, "specified", NONE, body, [f], basis="authored")
            b.assertion(rid, "open_decision", "OD-1", body, [f], basis="authored")
        else:
            b.assertion(rid, "text", body, body, [f], basis="authored")
    for i, line in enumerate(text.splitlines(), 1):
        if "not yet authored" in line:
            f = b.frag(f"line/{i}", line)
            b.ent("screening_decision.dmn", "artefact_ref")
            b.assertion("screening_decision.dmn", "authored", NONE, line, [f], basis="authored")
    return b


# ------------------------------------------------------- decision tables

_DTS_STATUS = {"quoted": "quoted", "review_hold": "review_hold",
               "refused_screening": "refused_screening"}


def extract_decision_table(path: str, text: str) -> Bag:
    b = Bag(short(path))
    lines = text.splitlines()
    section = None
    for i, line in enumerate(lines, 1):
        if line.startswith("## DT-V"):
            section = "V"
        elif line.startswith("## DT-S"):
            section = "S"
        elif line.startswith("## DT-P"):
            section = "P"
        if section == "V":
            m = re.match(r"\|\s*V(\d)\s*\|\s*`(\w+)`\s*\|\s*(.+?)\s*\|\s*$", line)
            if m:
                field, rule = m.group(2), m.group(3)
                f = b.frag(f"DT-V/row/V{m.group(1)}", line)
                b.ent(field, "field", field)
                if "present" in rule:
                    b.assertion(field, "present", "yes", rule, [f])
                mm = re.search(r"`(-?[\d.]+)\s*<=\s*\w+\s*<=\s*(-?[\d.]+)`", rule)
                if mm:
                    b.assertion(field, "min", mm.group(1), rule, [f])
                    b.assertion(field, "max", mm.group(2), rule, [f])
        if section == "S":
            m = re.match(r"\|\s*(accept|review|refuse)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*`(\w+)`\s*\|\s*$", line)
            if m:
                row, cond, _dec, priced, notified, status = m.groups()
                ent = f"S-{row}"
                f = b.frag(f"DT-S/row/{row}", line)
                b.ent(ent, "decision_row", f"DT-S {row}")
                c = cond.strip("`")
                lo = re.fullmatch(r"(\d+)\s*<=\s*risk_index\s*<=\s*(\d+)", c)
                le = re.fullmatch(r"risk_index\s*<=\s*(\d+)", c)
                ge = re.fullmatch(r"risk_index\s*>=\s*(\d+)", c)
                if lo:
                    b.assertion(ent, "min", lo.group(1), cond, [f])
                    b.assertion(ent, "max", lo.group(2), cond, [f])
                elif le:
                    b.assertion(ent, "max", le.group(1), cond, [f])
                elif ge:
                    b.assertion(ent, "min", ge.group(1), cond, [f])
                else:
                    # unparsable condition: keep the raw text as the value
                    pred = {"accept": "max", "review": "min", "refuse": "min"}[row]
                    b.assertion(ent, pred, cond, cond, [f])
                    if row == "review":
                        b.assertion(ent, "max", cond, cond, [f])
                b.assertion(ent, "priced", "yes" if priced.strip("* ").lower().startswith("yes") else NONE, priced, [f])
                nt = notified.strip("* ").lower()
                nv = NONE if nt.startswith("no") else ("quote document" if "quote document" in nt else "refusal notice")
                b.assertion(ent, "notified", nv, notified, [f])
                b.assertion(ent, "status", status, status, [f])
    # notes and paragraphs
    for start, para in _paragraphs(text):
        p = " ".join(para.split())
        if p.startswith("An invalid request is rejected"):
            f = b.frag("DT-V/para/invalid", para)
            b.ent("invalid_request", "condition")
            b.assertion("invalid_request", "behaviour",
                        _behaviour_tokens(status="rejected: invalid_request", store="no", screen="no", priced="no", notified="no"),
                        p, [f])
        if p.startswith("Worked example"):
            f = b.frag("DT-P/para/worked-example", para)
            b.ent("P3", "pricing_step", "DT-P P3")
            b.assertion("P3", "order", "after P2", p, [f])
            mm = re.search(r"\*\*`([\d.]+)`\*\*", p)
            if mm:
                b.ent("worked_example", "example")
                b.assertion("worked_example", "price", mm.group(1), p, [f])
    notes_start = text.find("Notes (normative):")
    notes_end = text.find("## DT-P")
    if notes_start > 0:
        block = text[notes_start:notes_end]
        for lineno, n, body in _numbered_items(block):
            para = body
            if "storage failure" in body:
                f = b.frag("DT-S/note/3", para)
                b.ent("QuoteAPI", "service")
                b.assertion("QuoteAPI", "on_store_failure",
                            _behaviour_tokens(status="error: store_unavailable", screen="no", priced="no", notified="no"), body, [f])
            elif "fire-and-forget" in body:
                f = b.frag("DT-S/note/4", para)
                b.ent("QuoteAPI", "service")
                b.assertion("QuoteAPI", "on_notification_failure",
                            "response=unchanged;stored=unchanged", body, [f])
            elif "screening outage" in body:
                f = b.frag("DT-S/note/5", para)
                b.ent("QuoteAPI", "service")
                b.assertion("QuoteAPI", "on_screening_outage",
                            _behaviour_tokens(priced="yes", status="held_unscreened", notified="no", hold="true"), body, [f])
            elif "review hold" in body.lower():
                f = b.frag("DT-S/note/1", para)
                b.assertion("S-review", "final", "no", body, [f])
            elif "refusal" in body.lower():
                f = b.frag("DT-S/note/2", para)
                b.assertion("S-refuse", "notified", "refusal notice", body, [f])
    for i, line in enumerate(lines, 1):
        m = re.match(r"\|\s*(P\d)\s*\|\s*(.+?)\s*\|\s*$", line)
        if not m:
            continue
        step, rule = m.groups()
        f = b.frag(f"DT-P/row/{step}", line)
        b.ent(step, "pricing_step", f"DT-P {step}")
        if step == "P1":
            mm = re.search(r"`base = (.+?)`", rule)
            b.assertion(step, "formula", mm.group(1) if mm else rule, rule, [f])
        elif step == "P2":
            mm = re.search(r"`weight_kg > ([\d.]+)`, add `([\d.]+)`", rule)
            if mm:
                b.assertion(step, "threshold", mm.group(1), rule, [f])
                b.assertion(step, "surcharge", mm.group(2), rule, [f])
            else:
                b.assertion(step, "threshold", rule, rule, [f])
                b.assertion(step, "surcharge", rule, rule, [f])
        elif step == "P3":
            mm = re.search(r"`distance_km >= ([\d.]+)`, multiply the running total by `([\d.]+)`", rule)
            if mm:
                b.assertion(step, "threshold", mm.group(1), rule, [f])
                b.assertion(step, "factor", mm.group(2), rule, [f])
            else:
                b.assertion(step, "threshold", rule, rule, [f])
                b.assertion(step, "factor", rule, rule, [f])
            if "after" in rule:
                b.assertion(step, "order", "after P2", rule, [f])
        elif step == "P4":
            mm = re.search(r"round\(result, (\d)\)", rule)
            b.assertion(step, "rounding", mm.group(1) if mm else rule, rule, [f])
    return b


# ------------------------------------------------------------------ spec

_STEP_CANON = {"Validate": "validate", "Store": "store", "Request the shipper": "screen",
               "Apply": "decide", "Price": "price", "Notify": "notify", "Return": "respond"}


def extract_spec(path: str, text: str) -> Bag:
    b = Bag(short(path))
    order = []
    flow_start = text.find("## Flow order")
    flow_end = text.find("## API contract")
    for lineno, n, body in _numbered_items(text[flow_start:flow_end]):
        canon = next((v for k, v in _STEP_CANON.items() if body.startswith(k)), None)
        if not canon:
            continue
        order.append(canon)
        f = b.frag(f"flow/step/{n}", body)
        if canon == "store" and "If storage fails" in body:
            b.ent("QuoteAPI", "service")
            b.assertion("QuoteAPI", "on_store_failure",
                        _behaviour_tokens(status="error: store_unavailable", screen="no", priced="no", notified="no"), body, [f])
        if canon == "screen" and "If screening is unavailable" in body:
            b.ent("QuoteAPI", "service")
            b.assertion("QuoteAPI", "on_screening_outage",
                        _behaviour_tokens(priced="yes", status="held_unscreened", notified="no", hold="true"), body, [f])
    if order:
        f = b.frag("flow/order", "\n".join(f"{i}. {s}" for i, s in enumerate(order, 1)))
        b.ent("flow", "process_flow", "quotation flow")
        b.assertion("flow", "order", ">".join(order), "flow order steps 1-7", [f])
    # response vocabulary
    m = re.search(r"Response \(JSON object\): `status` is exactly one of\n\n(.*?)\n\nplus (.*?)\n\n", text, re.S)
    if m:
        enum = sorted(re.findall(r'`"([^"]+)"`', m.group(1)))
        f1 = b.frag("api/response/statuses", m.group(1))
        b.ent("response", "api_response")
        b.assertion("response", "statuses", "|".join(enum), m.group(1), [f1])
        plus = " ".join(m.group(2).split())
        f2 = b.frag("api/response/fields", m.group(2))
        if "`quote_id`" in plus:
            b.assertion("response", "quote_id_presence", "whenever a draft was stored", plus, [f2])
        if "`price`" in plus:
            b.assertion("response", "price_presence", "priced rows only", plus, [f2])
        if "`hold: true`" in plus:
            b.assertion("response", "hold_presence", "held_unscreened only", plus, [f2])
    return b


# --------------------------------------------------------------- openapi

def extract_openapi(path: str, text: str) -> Bag:
    b = Bag(short(path))
    doc = yaml.safe_load(text)
    req = doc["components"]["schemas"]["QuoteRequest"]["properties"]
    for field, spec in req.items():
        b.ent(field, "field", field)
        f = b.frag(f"QuoteRequest/{field}", yaml.safe_dump({field: spec}))
        if "minimum" in spec:
            b.assertion(field, "min", spec["minimum"], f"minimum: {spec['minimum']}", [f])
        if "maximum" in spec:
            b.assertion(field, "max", spec["maximum"], f"maximum: {spec['maximum']}", [f])
        if spec.get("minLength", 0) >= 1 and field in doc["components"]["schemas"]["QuoteRequest"]["required"]:
            b.assertion(field, "present", "yes", "required, minLength 1", [f])
    resp = doc["components"]["schemas"]["QuoteResponse"]["properties"]
    enum = sorted(resp["status"]["enum"])
    f = b.frag("QuoteResponse/status", yaml.safe_dump({"status": resp["status"]}))
    b.ent("response", "api_response")
    b.assertion("response", "statuses", "|".join(enum), "status enum", [f])
    if "hold" in resp:
        f = b.frag("QuoteResponse/hold", yaml.safe_dump({"hold": resp["hold"]}))
        b.assertion("response", "hold_presence", "held_unscreened only", resp["hold"].get("description", ""), [f])
    if "price" in resp:
        f = b.frag("QuoteResponse/price", yaml.safe_dump({"price": resp["price"]}))
        b.assertion("response", "price_presence", "priced rows only", resp["price"].get("description", ""), [f])
    return b


# -------------------------------------------------------------- sequence

_STATUS_TOKEN = {"statusQuoted": "quoted", "statusReviewHold": "review_hold",
                 "statusRefusedScreening": "refused_screening",
                 "statusHeldUnscreened": "held_unscreened",
                 "statusErrorScreening": "error: screening_unavailable"}


def extract_sequence(path: str, text: str) -> Bag:
    from pumllint import parser  # the product's parser, as a library
    b = Bag(short(path))
    d = parser.parse_source(text, file_path=path)[0]
    lines = text.splitlines()
    for name in d.participants:
        p = d.participants[name]
        b.ent(name, "participant", name)
        f = b.frag(f"participant/{name}", lines[p.line - 1])
        b.assertion(name, "kind", p.kind, lines[p.line - 1], [f])
    # branches: (label, start, end)
    spans = []
    for blk in d.blocks:
        if blk.kind != "alt":
            continue
        bounds = [(blk.label, blk.start_line)] + [(br.label, br.line) for br in blk.else_branches]
        for j, (label, start) in enumerate(bounds):
            end = bounds[j + 1][1] if j + 1 < len(bounds) else blk.end_line
            spans.append((label, start, end))
    for label, start, end in spans:
        msgs = [m for m in d.messages if start < m.line < end]
        priced = "yes" if any(m.target == "TariffEngine" for m in msgs) else "no"
        status = None
        for m in msgs:
            if m.target == "QuoteStore" and "updateQuote" in m.label:
                for tok, st in _STATUS_TOKEN.items():
                    if tok in m.label:
                        status = st
        notified = NONE
        for m in msgs:
            if m.target == "NotificationService":
                notified = "quote document" if "QuoteDocument" in m.label else "refusal notice"
        key = None
        if "screening failure" in label:
            key = ("QuoteAPI", "on_screening_outage")
            value = _behaviour_tokens(priced=priced, status=status, notified="no" if notified == NONE else notified)
        elif "storeDraft failure" in label:
            key = ("QuoteAPI", "on_store_failure")
            value = _behaviour_tokens(status="error: store_unavailable", screen="no", priced="no", notified="no")
        elif "row accept" in label:
            key = ("S-accept", None)
        elif "row review" in label:
            key = ("S-review", None)
        elif "row refuse" in label:
            key = ("S-refuse", None)
        if not key:
            continue
        f = b.frag(f"alt/{start}-{end}", "\n".join(lines[start - 1:end]))
        b.ent(key[0], "service" if key[0] == "QuoteAPI" else "decision_row")
        if key[1]:
            b.assertion(key[0], key[1], value, label, [f])
        else:
            b.assertion(key[0], "priced", "yes" if priced == "yes" else NONE, label, [f])
            b.assertion(key[0], "notified", notified, label, [f])
            if status:
                b.assertion(key[0], "status", status, label, [f])
            if "<= ACCEPT_MAX" in label:
                b.assertion(key[0], "max", "ACCEPT_MAX", label, [f])
            if "REVIEW_MIN <=" in label:
                b.assertion(key[0], "min", "REVIEW_MIN", label, [f])
                b.assertion(key[0], "max", "REVIEW_MAX", label, [f])
            if ">= REFUSE_MIN" in label:
                b.assertion(key[0], "min", "REFUSE_MIN", label, [f])
    return b


# ------------------------------------------------------------- containers

def extract_containers(path: str, text: str) -> Bag:
    b = Bag(short(path))
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*(Container|ContainerDb|System_Ext|Person)\((\w+), \"([^\"]+)\", \"([^\"]+)\"", line)
        if m:
            kind, alias, label, tech = m.groups()
            b.ent(alias, {"Person": "person", "System_Ext": "external_system"}.get(kind, "container"), label)
            f = b.frag(f"line/{i}", line)
            b.assertion(alias, "technology", tech, line, [f])
        m = re.match(r"\s*Rel\((\w+), (\w+), \"([^\"]+)\"", line)
        if m:
            src, dst, lbl = m.groups()
            f = b.frag(f"line/{i}", line)
            b.ent(src, "container"); b.ent(dst, "container")
            b.assertion(src, f"uses:{dst}", lbl, line, [f])
    return b


# ------------------------------------------------------------------- bpmn

def extract_bpmn(path: str, text: str) -> Bag:
    b = Bag(short(path))
    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
    root = ET.fromstring(text)
    proc = root.find("bpmn:process", ns)
    names = {}
    for el in proc:
        tag = el.tag.split("}")[1]
        if tag in ("task", "exclusiveGateway", "startEvent", "endEvent"):
            names[el.get("id")] = (tag, el.get("name", ""))
            b.ent(f"bpmn:{el.get('id')}", tag, el.get("name", ""))
    flows = [(f.get("id"), f.get("sourceRef"), f.get("targetRef"), f.get("name", ""))
             for f in proc.findall("bpmn:sequenceFlow", ns)]
    out = {}
    for fid, s, t, n in flows:
        out.setdefault(s, []).append((t, n, fid))
    # walk a path from a node, following unnamed flows, collecting names
    def walk(node):
        seen, path_nodes = set(), []
        while node and node not in seen:
            seen.add(node)
            path_nodes.append(node)
            nxt = [t for t, n, _ in out.get(node, []) if not n or n in ("valid", "stored")]
            node = nxt[0] if nxt else None
        return path_nodes
    def tokens_from(path_nodes):
        texts = [names[n][1] for n in path_nodes if n in names]
        priced = "yes" if any(t.startswith("Price") for t in texts) else "no"
        notified = "no"
        for t in texts:
            if t.startswith("Send quote"):
                notified = "quote document"
            if t.startswith("Send refusal"):
                notified = "refusal notice"
        status = None
        for t in texts:
            m = re.search(r"Update stored quote to (.+)", t)
            if m:
                status = m.group(1)
        return priced, status, notified
    for s, targets in out.items():
        for t, n, fid in targets:
            if s != "g_screen":
                continue
            path_nodes = walk(t)
            priced, status, notified = tokens_from(path_nodes)
            f = b.frag(f"path/{fid}", " -> ".join(names[x][1] for x in path_nodes if x in names))
            if n == "screening outage":
                b.ent("QuoteAPI", "service")
                b.assertion("QuoteAPI", "on_screening_outage",
                            _behaviour_tokens(priced=priced, status=status, notified=notified), f"{n}: {f}", [f])
            elif n.endswith(" row"):
                ent = {"accept": "S-accept", "review": "S-review", "refuse": "S-refuse"}[n.split()[0]]
                b.ent(ent, "decision_row")
                b.assertion(ent, "priced", "yes" if priced == "yes" else NONE, n, [f])
                b.assertion(ent, "notified", NONE if notified == "no" else notified, n, [f])
                if status:
                    b.assertion(ent, "status", status, n, [f])
    # main-path order
    order = []
    for node in walk("start"):
        tag, name = names.get(node, ("", ""))
        if tag == "task":
            order.append({"Validate": "validate", "Store": "store", "Request": "screen"}.get(name.split()[0], name))
        if tag == "exclusiveGateway" and "DT-S" in name:
            order.append("decide")
            break
    f = b.frag("path/main", " > ".join(order))
    b.ent("flow", "process_flow")
    b.assertion("flow", "order_prefix", ">".join(order), "main path to the screening decision", [f])
    return b


# -------------------------------------------------------------------- dmn

def extract_dmn(path: str, text: str) -> Bag:
    b = Bag(short(path))
    ns = {"d": "https://www.omg.org/spec/DMN/20191111/MODEL/"}
    root = ET.fromstring(text)
    for rule in root.iter(f"{{{ns['d']}}}rule"):
        rid = rule.get("id")
        cond = rule.find("d:inputEntry/d:text", ns).text
        outs = [o.text.strip('"') for o in rule.findall("d:outputEntry/d:text", ns)]
        row = rid.split("_")[1]
        ent = f"S-{row}"
        b.ent(ent, "decision_row")
        f = b.frag(f"rule/{rid}", ET.tostring(rule, encoding="unicode"))
        m = re.fullmatch(r"<= (\d+)", cond)
        if m:
            b.assertion(ent, "max", m.group(1), cond, [f])
        m = re.fullmatch(r"\[(\d+)\.\.(\d+)\]", cond)
        if m:
            b.assertion(ent, "min", m.group(1), cond, [f])
            b.assertion(ent, "max", m.group(2), cond, [f])
        m = re.fullmatch(r">= (\d+)", cond)
        if m:
            b.assertion(ent, "min", m.group(1), cond, [f])
        b.assertion(ent, "priced", "yes" if outs[1] == "true" else NONE, outs[1], [f])
        b.assertion(ent, "notified", NONE if outs[2] == "none" else outs[2], outs[2], [f])
        b.assertion(ent, "status", outs[3], outs[3], [f])
    return b


# ---------------------------------------------------------------- gherkin

def extract_gherkin(path: str, text: str) -> Bag:
    b = Bag(short(path))
    lines = text.splitlines()
    starts = [(i, re.match(r"\s*Scenario: (G\d) - (.*)", l)) for i, l in enumerate(lines, 1)]
    starts = [(i, m.group(1), m.group(2)) for i, m in starts if m]
    for j, (i, gid, title) in enumerate(starts):
        end = starts[j + 1][0] - 1 if j + 1 < len(starts) else len(lines)
        body = "\n".join(lines[i - 1:end]).rstrip()
        f = b.frag(f"scenario/{gid}", body)
        b.ent(gid, "scenario", title)
        b.assertion(gid, "title", title, title, [f])
        m = re.search(r'the response status is "([^"]+)"', body)
        if m:
            b.assertion(gid, "expects_status", m.group(1), body, [f])
    return b


# ------------------------------------------------------------------ links

def extract_links(path: str, text: str, code_text: str) -> Bag:
    b = Bag(short(path))
    doc = tomllib.loads(text)
    tree = ast.parse(code_text)
    units = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef):
                    units[f"{node.name}.{fn.name}"] = (fn.lineno, fn.end_lineno)
        elif isinstance(node, ast.FunctionDef):
            units[node.name] = (node.lineno, node.end_lineno)
    for i, link in enumerate(doc.get("implements", [])):
        cu = link["code_unit"]
        b.ent(cu, "code_unit", cu)
        b.ent(link["requirement"], "requirement")
        f = b.frag(f"implements/{i}", f'{link["requirement"]} implemented_by {cu} (reference_impl.py lines {units.get(cu)})')
        b.assertion(link["requirement"], "implemented_by", cu, f"{cu} at {units.get(cu)}", [f], basis="authored")
    for i, link in enumerate(doc.get("verifies", [])):
        b.ent(link["scenario"], "scenario")
        b.ent(link["requirement"], "requirement")
        f = b.frag(f"verifies/{i}", f'{link["requirement"]} verified_by {link["scenario"]}')
        b.assertion(link["requirement"], "verified_by", link["scenario"], f, [f], basis="authored")
    return b


EXTRACTORS = {
    "kit/requirements.md": extract_requirements,
    "contract/decision_table.md": extract_decision_table,
    "contract/spec.md": extract_spec,
    "contract/openapi.yaml": extract_openapi,
    "behavior/quote_flow.puml": extract_sequence,
    "structure/containers.puml": extract_containers,
    "kit/quote_process.bpmn": extract_bpmn,
    "kit/screening_decision.dmn": extract_dmn,
    "tests_input/acceptance.feature": extract_gherkin,
}


def extract_all(kit: dict[str, str], code_text: str) -> list[Bag]:
    bags = []
    for path, text in kit.items():
        if path in EXTRACTORS:
            bags.append(EXTRACTORS[path](path, text))
        elif path == "kit/links.toml":
            bags.append(extract_links(path, text, code_text))
    return bags


if __name__ == "__main__":
    import sys
    from kitio import kit_for, CARGO
    code = (CARGO / "reference_impl.py").read_text()
    scenario = sys.argv[1] if len(sys.argv) > 1 else "S1"
    for bag in extract_all(kit_for(scenario), code):
        print(f"== {bag.artefact}: {len(bag.fragments)} fragments, {len(bag.entities)} entities, {len(bag.assertions)} assertions")
        for a in bag.assertions:
            print(f"   {a['id']:48s} = {a['value'][:60]!s}")
