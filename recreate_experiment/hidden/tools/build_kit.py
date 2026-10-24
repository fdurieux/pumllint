"""Render hidden/kit_src/** into kit/** resolving {{requirement-key}} -> JDL-NNN."""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "hidden", "kit_src")
KIT = os.path.join(ROOT, "kit")

subprocess.run([sys.executable, os.path.join(HERE, "build_requirements.py")], check=True,
               stdout=subprocess.DEVNULL)
ids = json.load(open(os.path.join(ROOT, "hidden", "idmap.json")))
pattern = re.compile(r"\{\{([a-z0-9-]+)\}\}")
written = []
for dirpath, _dirs, files in os.walk(SRC):
    for name in files:
        if name.endswith(".pyc"):
            continue
        src = os.path.join(dirpath, name)
        rel = os.path.relpath(src, SRC)
        dst = os.path.join(KIT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        text = open(src, encoding="utf-8").read()
        unknown = sorted({m for m in pattern.findall(text) if m not in ids})
        if unknown:
            sys.exit(f"{rel}: unknown requirement keys {unknown}")
        text = pattern.sub(lambda m: ids[m.group(1)], text)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        written.append(rel)
print(f"rendered {len(written)} files")
