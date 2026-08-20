"""Requirement traceability: the coverage matrix between a requirements
inventory and the diagrams that realize them (ROADMAP Arc G).

Deterministic aggregation over the parsed model — no rules, no LLM, no
scoring. Requirement IDs are found with the project's reference pattern
(the same convention GEN007 enforces per diagram) in the same prose
carriers GEN007 reads — the diagram name plus title/header/footer/caption/
notes (:func:`pumllint.model.prose_directives`) — so the rule and the
matrix cannot disagree about what counts as a reference.

The inventory (the universe of requirement IDs) comes from either an
explicit list file (text: one ID per line; JSON/YAML: an array of IDs —
strings, or objects carrying an ``id``, so a richer synchronized snapshot
from a canonical requirements repository works unchanged) or from scanning
a docs file/tree with the pattern. The matrix reports both directions plus
the dangling third: requirements no diagram realizes, diagrams referencing
nothing, and references to IDs the inventory does not know (typo
detector — the SEQ001 instinct applied to requirement IDs).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .model import Diagram, prose_directives
from .textio import read_text_file

# Suffixes scanned when --requirements-scan points at a directory.
SCAN_SUFFIXES = (".md", ".txt", ".adoc", ".rst")


@dataclass(frozen=True)
class DiagramRef:
    """One diagram-side site: which diagram, and (for references) where."""

    file: str
    name: str | None
    line: int
    diagram_type: str = "unknown"


@dataclass(frozen=True)
class RequirementRow:
    """One inventory ID and the diagrams that reference it (may be none)."""

    id: str
    covered_by: tuple[DiagramRef, ...] = ()

    @property
    def covered(self) -> bool:
        return bool(self.covered_by)


@dataclass(frozen=True)
class UnknownReference:
    """A diagram-cited ID the inventory does not contain."""

    id: str
    cited_by: tuple[DiagramRef, ...] = ()


@dataclass
class TraceResult:
    """The full matrix. Row order is deterministic: inventory order for
    requirements (an explicit list's order is the author's), first-seen
    order for scanned inventories and unknown references (file walks are
    sorted), input order for diagrams."""

    requirements: list[RequirementRow] = field(default_factory=list)
    unknown_references: list[UnknownReference] = field(default_factory=list)
    unlinked_diagrams: list[DiagramRef] = field(default_factory=list)
    diagram_count: int = 0

    @property
    def uncovered(self) -> list[RequirementRow]:
        return [r for r in self.requirements if not r.covered]


def compile_pattern(raw: str, origin: str) -> re.Pattern[str]:
    """Compile the reference pattern; malformed = config error, not traceback.

    ``origin`` names where the pattern came from (``--pattern`` or the
    config key) so the exit-2 message points at the right knob.
    """
    try:
        return re.compile(raw)
    except (re.error, TypeError) as e:
        raise ValueError(f"{origin} is not a valid regex ({e}): {raw!r}") from e


def pattern_from_config(config: dict) -> str | None:
    """The GEN007 (requirement-link) ``pattern`` from a loaded config, if any.

    Reads the same ``rules:`` keys the engine does (id or kebab-case name);
    a disabled rule or a non-mapping value yields None — trace then needs
    an explicit ``--pattern``.
    """
    rules_cfg = config.get("rules") or {}
    raw = rules_cfg.get("GEN007", rules_cfg.get("requirement-link"))
    if isinstance(raw, dict):
        value = raw.get("pattern")
        return value if isinstance(value, str) else None
    return None


# -- inventory loading ------------------------------------------------------


def load_inventory(path: str | Path) -> list[str]:
    """Requirement IDs from an explicit list file, order preserved, deduped.

    ``.json`` / ``.yaml`` / ``.yml``: an array whose items are ID strings or
    objects with an ``id`` key, or an object whose ``requirements`` key
    holds such an array (richer snapshot columns ride along untouched).
    Anything else is read as text: one ID per line, ``#`` comments and
    blank lines ignored.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    text = read_text_file(p, kind="requirements inventory")
    suffix = p.suffix.lower()
    if suffix == ".json":
        return _ids_from_data(json.loads(text), p)
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # optional dependency; only needed for YAML inventories
        except ImportError:
            raise ValueError(
                f"requirements file {p} is YAML but PyYAML is not installed — "
                f"install with `pip install pumllint[yaml]`, or use a "
                f".json/plain-text inventory"
            ) from None
        return _ids_from_data(yaml.safe_load(text), p)
    ids = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            ids.append(s)
    return _dedupe(ids)


def _ids_from_data(data, path: Path) -> list[str]:
    if isinstance(data, dict):
        data = data.get("requirements")
    if not isinstance(data, list):
        raise ValueError(
            f"requirements file {path}: expected an array of IDs (strings or "
            f"objects with an 'id'), or an object with a 'requirements' array"
        )
    ids: list[str] = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            ids.append(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"].strip())
        else:
            raise ValueError(
                f"requirements file {path}: entry {i} has no usable ID "
                f"(string or object with an 'id' string)"
            )
    return _dedupe(ids)


def scan_inventory(path: str | Path, pattern: re.Pattern[str]) -> list[str]:
    """Requirement IDs found by scanning a docs file or tree with ``pattern``.

    A directory is walked for {`.md`, `.txt`, `.adoc`, `.rst`} files in
    sorted order; an explicit file is scanned regardless of suffix. Matches
    use the whole-match text (group 0), so patterns with groups behave the
    same here as in GEN007. First-seen order, deduped.
    """
    p = Path(path)
    if p.is_dir():
        files = sorted(f for f in p.rglob("*") if f.suffix.lower() in SCAN_SUFFIXES)
    elif p.exists():
        files = [p]
    else:
        raise FileNotFoundError(p)
    ids: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        ids.extend(m.group(0) for m in pattern.finditer(text))
    return _dedupe(ids)


def _dedupe(ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i and i not in seen:
            seen.add(i)
            out.append(i)
    return out


# -- the matrix ---------------------------------------------------------------


def diagram_references(diagram: Diagram, pattern: re.Pattern[str]) -> dict[str, int]:
    """IDs this diagram references → line of the first carrying text.

    Exactly GEN007's haystacks: the prose directives (title/header/footer/
    caption/notes) plus the ``@startuml`` name. Message labels and other
    model content are deliberately not carriers — same as the rule.
    """
    refs: dict[str, int] = {}
    for d in prose_directives(diagram):
        for m in pattern.finditer(d.value):
            refs.setdefault(m.group(0), d.line)
    if diagram.name:
        for m in pattern.finditer(diagram.name):
            refs.setdefault(m.group(0), diagram.start_line)
    return refs


def build_matrix(
    diagrams: Iterable[Diagram],
    inventory: list[str],
    pattern: re.Pattern[str],
) -> TraceResult:
    """Fold per-diagram references and the inventory into the coverage matrix."""
    diagrams = list(diagrams)
    known = set(inventory)
    covered_by: dict[str, list[DiagramRef]] = {i: [] for i in inventory}
    unknown: dict[str, list[DiagramRef]] = {}
    unlinked: list[DiagramRef] = []
    for d in diagrams:
        refs = diagram_references(d, pattern)
        if not refs:
            unlinked.append(
                DiagramRef(d.file_path, d.name, d.start_line, d.diagram_type)
            )
            continue
        for rid, line in refs.items():
            site = DiagramRef(d.file_path, d.name, line, d.diagram_type)
            (covered_by[rid] if rid in known else unknown.setdefault(rid, [])).append(site)
    return TraceResult(
        requirements=[
            RequirementRow(i, tuple(covered_by[i])) for i in inventory
        ],
        unknown_references=[
            UnknownReference(rid, tuple(sites)) for rid, sites in unknown.items()
        ],
        unlinked_diagrams=unlinked,
        diagram_count=len(diagrams),
    )
