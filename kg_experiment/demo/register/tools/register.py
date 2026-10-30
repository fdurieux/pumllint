"""Shared loading for the register's tools. Standard library only (Python 3.11+ for tomllib)."""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAXONOMIES = ("capabilities", "products", "journeys", "processes", "applications", "information", "organisation")
RELATIONSHIPS = ("requires", "concerns", "is_supported_by", "realizes", "delivers", "supports", "crud", "manages", "owns", "maps_to")


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_register(root: Path = ROOT) -> dict:
    """Everything the checks read: metamodel, glossary, nodes by id, relationship files, exceptions."""
    reg = {
        "root": root,
        "types": load_toml(root / "metamodel" / "types.toml"),
        "lifecycle": load_toml(root / "metamodel" / "lifecycle.toml"),
        "sources": load_toml(root / "metamodel" / "sources.toml"),
        "glossary": load_toml(root / "glossary" / "glossary.toml"),
        "nodes": {},          # id -> node dict, with "_taxonomy" and "_path"
        "relationships": {},  # type name -> {"type": {...}, "links": [...], "_path": Path}
        "exceptions": [],
    }
    for tax in TAXONOMIES:
        d = root / tax
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.toml")):
            n = load_toml(p)
            n["_taxonomy"], n["_path"] = tax, p
            reg["nodes"][n.get("id", p.stem)] = n
    for name in RELATIONSHIPS:
        p = root / "relationships" / f"{name}.toml"
        if p.exists():
            t = load_toml(p)
            reg["relationships"][name] = {"type": t.get("type", {}), "links": t.get("link", []), "_path": p}
    for p in sorted((root / "exceptions").glob("*.toml")):
        e = load_toml(p)
        e["_path"] = p
        reg["exceptions"].append(e)
    return reg


def kind_taxonomy(reg: dict) -> dict:
    """kind -> taxonomy, from types.toml."""
    out = {}
    for tax, spec in reg["types"]["taxonomy"].items():
        for k in spec["kinds"]:
            out[k] = tax
    return out
