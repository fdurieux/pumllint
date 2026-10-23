"""A minimal JSON Schema (draft 2020-12 subset) checker for the kit's schemas."""
import json
import re
import sys

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def check(node, schema, root, where="$"):
    if "$ref" in schema:
        ref = schema["$ref"].lstrip("#/").split("/")
        target = root
        for part in ref:
            target = target[part]
        return check(node, target, root, where)
    errs = []
    if "const" in schema and node != schema["const"]:
        errs.append(f"{where}: const {schema['const']!r} != {node!r}")
    if "enum" in schema and node not in schema["enum"]:
        errs.append(f"{where}: {node!r} not in enum")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        ok = False
        for t in types:
            if t == "integer":
                ok |= isinstance(node, int) and not isinstance(node, bool)
            elif t == "number":
                ok |= isinstance(node, (int, float)) and not isinstance(node, bool)
            else:
                ok |= isinstance(node, TYPES[t]) and not (t != "boolean" and isinstance(node, bool) and TYPES[t] is not bool)
        if not ok:
            errs.append(f"{where}: type {types} != {type(node).__name__}")
            return errs
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errs.append(f"{where}: below minimum")
        if "maximum" in schema and node > schema["maximum"]:
            errs.append(f"{where}: above maximum")
    if isinstance(node, str) and "pattern" in schema and not re.search(schema["pattern"], node):
        errs.append(f"{where}: pattern")
    if isinstance(node, dict):
        for key in schema.get("required", []):
            if key not in node:
                errs.append(f"{where}: missing {key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    errs.append(f"{where}: additional {key}")
        for key, value in node.items():
            if key in props:
                errs += check(value, props[key], root, f"{where}.{key}")
    if isinstance(node, list) and "items" in schema:
        for i, value in enumerate(node):
            errs += check(value, schema["items"], root, f"{where}[{i}]")
    return errs


if __name__ == "__main__":
    schema = json.load(open(sys.argv[1]))
    for doc_path in sys.argv[2:]:
        errs = check(json.load(open(doc_path)), schema, schema)
        print(doc_path, "OK" if not errs else errs)
