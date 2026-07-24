"""Auto-remediation for mechanical findings (``pumllint fix``).

Only findings whose fix is deterministic and semantics-preserving are
touched — nothing is ever invented:

- **GEN002** (unnamed diagram) — name the ``@startuml`` from the file stem
  (kebab-cased; later diagrams in the same file get an ordinal suffix).
- **GEN001** (missing title) — insert ``title <Humanized>`` after
  ``@startuml``, derived from the diagram name (or the name GEN002's fix
  just assigned).
- **SEQ001 / SEQ101** (undeclared participants) — insert ``participant X``
  declarations in first-use order, anchored after the last existing
  declaration (or the title, or ``@startuml``).

Fixes are computed from the engine's *violations*, not from the raw model:
a suppressed finding or a disabled rule is never "fixed", and the fixer
inherits every judgment call the linter makes about what deserves flagging.
The visible consequence: SEQ001 defaults to ``only_if_any_declared`` (an
ad-hoc sketch that declares nothing is deliberately not punished), so such a
sketch also gets no declaration fixes — by design, not omission. Applying
the fixes removes exactly the triggering findings, so a second run is a
no-op.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .engine import Engine, collect_files
from .model import Diagram, Violation
from .parser import parse_source

FIXABLE_RULES = ("GEN001", "GEN002", "SEQ001", "SEQ101")


@dataclass(frozen=True)
class Fix:
    """One line edit: replace line ``line`` or insert directly after it."""

    rule_id: str
    line: int  # 1-based line number in the original file
    kind: str  # "replace" | "insert_after"
    content: str  # new line content, without the newline
    description: str


@dataclass
class FileFixResult:
    """Outcome of fixing one file."""

    path: Path
    original: str
    fixed: str
    fixes: list[Fix] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.fixes)


def _derived_name(stem: str, ordinal: int) -> str:
    name = re.sub(r"[^\w.-]+", "-", stem).replace("_", "-").strip("-")
    return name if ordinal == 1 else f"{name}-{ordinal}"


def _humanize(name: str) -> str:
    words = re.sub(r"[-_]+", " ", name).strip()
    return (words[:1].upper() + words[1:]) if words else name


def _owning(diagrams: Sequence[Diagram], line: int) -> Diagram | None:
    owner = None
    for d in diagrams:
        end = d.end_line if d.end_line is not None else float("inf")
        if d.start_line <= line <= end and (owner is None or d.start_line > owner.start_line):
            owner = d
    return owner


def _quote(name: str) -> str:
    return name if re.fullmatch(r"[\w.]+", name) else f'"{name}"'


def compute_fixes(
    text: str, diagrams: Sequence[Diagram], violations: Iterable[Violation], stem: str
) -> list[Fix]:
    """Line edits that remove the fixable findings from *text*."""
    fixes: list[Fix] = []
    ordinals = {id(d): i for i, d in enumerate(diagrams, start=1)}
    # Diagram name after this run: existing, or the one GEN002's fix assigns.
    names = {id(d): d.name for d in diagrams}

    for v in violations:
        if v.rule_id != "GEN002":
            continue
        d = next((dg for dg in diagrams if dg.start_line == v.line), None)
        if d is None:
            continue
        name = _derived_name(stem, ordinals[id(d)])
        names[id(d)] = name
        fixes.append(
            Fix(
                rule_id="GEN002",
                line=d.start_line,
                kind="replace",
                content=f"@startuml {name}",
                description=f"named diagram '{name}'",
            )
        )

    for v in violations:
        if v.rule_id != "GEN001":
            continue
        d = next((dg for dg in diagrams if dg.start_line == v.line), None)
        if d is None:
            continue
        title = _humanize(names[id(d)] or _derived_name(stem, ordinals[id(d)]))
        fixes.append(
            Fix(
                rule_id="GEN001",
                line=d.start_line,
                kind="insert_after",
                content=f"title {title}",
                description=f"added title '{title}'",
            )
        )

    undeclared_lines = {
        v.line for v in violations if v.rule_id in ("SEQ001", "SEQ101")
    }
    handled: set[tuple[int, str]] = set()
    for line in sorted(undeclared_lines):
        d = _owning(diagrams, line)
        if d is None:
            continue
        # Anchor: after the last declared participant, else the title, else
        # the @startuml line (post-GEN001 insertion order keeps title first).
        anchor = d.start_line
        if d.title is not None:
            anchor = max(anchor, d.title.line)
        declared = [p.line for p in d.participants.values() if p.declared]
        if declared:
            anchor = max(anchor, max(declared))
        for p in sorted(
            (p for p in d.participants.values() if not p.declared and p.line == line),
            key=lambda p: p.name,
        ):
            key = (id(d), p.name)
            if key in handled:
                continue
            handled.add(key)
            fixes.append(
                Fix(
                    rule_id="SEQ001",
                    line=anchor,
                    kind="insert_after",
                    content=f"participant {_quote(p.name)}",
                    description=f"declared participant '{p.name}'",
                )
            )
    return fixes


def apply_fixes(text: str, fixes: Sequence[Fix]) -> str:
    """Apply the edits, preserving the file's newline style."""
    if not fixes:
        return text
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    trailing_nl = text.endswith(("\n", "\r"))
    replace = {f.line: f for f in fixes if f.kind == "replace"}
    inserts: dict[int, list[Fix]] = {}
    for f in fixes:
        if f.kind == "insert_after":
            inserts.setdefault(f.line, []).append(f)
    out: list[str] = []
    for i, raw in enumerate(lines, start=1):
        out.append(replace[i].content if i in replace else raw)
        out.extend(f.content for f in inserts.get(i, ()))
    return nl.join(out) + (nl if trailing_nl else "")


def fix_paths(paths: Iterable[str | Path], config: dict | None = None) -> list[FileFixResult]:
    """Compute (but do not write) fixes for every diagram file under *paths*."""
    engine = Engine(config or {})
    results: list[FileFixResult] = []
    for path in collect_files(paths):
        text = path.read_text(encoding="utf-8")
        diagrams = parse_source(text, file_path=str(path))
        violations = engine.lint_diagrams(diagrams)
        fixes = compute_fixes(text, diagrams, violations, stem=path.stem)
        results.append(
            FileFixResult(
                path=path,
                original=text,
                fixed=apply_fixes(text, fixes),
                fixes=fixes,
            )
        )
    return results
