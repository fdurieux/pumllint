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

The optional verification side (``--features``) adds the column the Arc G
spec reserved: Gherkin feature files are scanned with the same pattern —
file name first, then text, so a ``@REQ-101`` tag, a step that names the
ID and a ``REQ-101.feature`` file all count — and each inventory row
records which feature files reference it. The new direction is
*modelled but untested*: a requirement some diagram realizes that no
feature file references.

Sites are attributed to scenarios by a keyword-level reader, not a
Gherkin parser: the file is read line by line for the fixed English
keywords (``Feature:``, ``Rule:``, ``Background:``, ``Scenario:``,
``Scenario Outline:``, ``Example:``, ``Examples:``) and tag lines, and
Gherkin's own tag-inheritance rules are applied — a tag on the Feature
belongs to every scenario in the file, a tag on a Rule to every scenario
under it, a tag line directly above a scenario to that scenario, tags
above ``Examples:`` to the enclosing outline. Text inside a scenario
(steps, tables, doc strings, comments) is that scenario's; text in the
feature header, a Rule description or the Background is the file's, with
no scenario. No grammar, no AST, no dependency; a ``# language:`` other
than English degrades to file-level attribution.
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

# Suffixes scanned when --features points at a directory. Deliberately not
# part of SCAN_SUFFIXES: the inventory is the universe of what must be
# modelled, and a test must never define it.
FEATURE_SUFFIXES = (".feature",)

_FEATURE_HEADING = re.compile(r"^\s*Feature:\s*(.*\S)\s*$", re.MULTILINE)

# The Gherkin keywords the attribution reader recognises (English, the
# default dialect). Scenario-opening keywords name a scenario; the others
# open a container or a block whose text belongs to the file.
_SCENARIO_KEYWORDS = ("Scenario Outline:", "Scenario Template:", "Scenario:", "Example:")
_EXAMPLES_KEYWORDS = ("Examples:", "Scenarios:")
_LANGUAGE_HEADER = re.compile(r"^\s*#\s*language\s*:\s*([\w-]+)")
_DOCSTRING_FENCES = ('"""', "```")


@dataclass(frozen=True)
class DiagramRef:
    """One diagram-side site: which diagram, and (for references) where."""

    file: str
    name: str | None
    line: int
    diagram_type: str = "unknown"


@dataclass(frozen=True)
class FeatureRef:
    """One feature-file reference site: which file, its ``Feature:`` heading
    (None when the file has none), the line of the first text carrying the
    ID — 0 when the ID is carried by the file name — and the scenario the
    reference is attributed to (None = the file itself: its name, the
    feature header, a Rule description or the Background), with the line
    of that scenario's heading (0 when there is none)."""

    file: str
    name: str | None
    line: int
    scenario: str | None = None
    scenario_line: int = 0


@dataclass(frozen=True)
class ScenarioRef:
    """One attribution inside a feature file: the line of the reference and
    the scenario it belongs to (None = the file itself)."""

    line: int
    scenario: str | None = None
    scenario_line: int = 0


@dataclass
class FeatureFile:
    """One scanned feature file: its heading, how many scenarios it declares
    and every ID it references — per ID, one :class:`ScenarioRef` per
    scenario (first line wins), in file order."""

    file: str
    name: str | None
    references: dict[str, tuple[ScenarioRef, ...]] = field(default_factory=dict)
    scenario_count: int = 0


@dataclass(frozen=True)
class RequirementRow:
    """One inventory ID, the diagrams that reference it (may be none) and,
    when the verification side ran, the feature files that reference it."""

    id: str
    covered_by: tuple[DiagramRef, ...] = ()
    verified_by: tuple[FeatureRef, ...] = ()

    @property
    def covered(self) -> bool:
        return bool(self.covered_by)

    @property
    def verified(self) -> bool:
        return bool(self.verified_by)


@dataclass(frozen=True)
class UnknownReference:
    """A diagram-cited ID the inventory does not contain."""

    id: str
    cited_by: tuple[DiagramRef, ...] = ()


@dataclass(frozen=True)
class UnknownFeatureReference:
    """A feature-cited ID the inventory does not contain — the same typo
    detector, applied to the test side. Kept apart from
    :class:`UnknownReference` so that list keeps meaning "a diagram said
    it": its sites are diagrams, these are feature files."""

    id: str
    cited_by: tuple[FeatureRef, ...] = ()


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
    # The verification side. ``feature_count`` is None when it did not run
    # (no --features), and the reporters then emit exactly the v1 shape.
    feature_count: int | None = None
    unknown_feature_references: list[UnknownFeatureReference] = field(
        default_factory=list
    )
    unlinked_features: list[FeatureRef] = field(default_factory=list)
    scenario_count: int = 0

    @property
    def uncovered(self) -> list[RequirementRow]:
        return [r for r in self.requirements if not r.covered]

    @property
    def verification_ran(self) -> bool:
        return self.feature_count is not None

    @property
    def verified(self) -> list[RequirementRow]:
        """Modelled *and* tested: covered rows some feature file references.

        The verification side measures the model, so an unmodelled
        requirement a feature happens to cite is neither here nor in
        :attr:`unverified` — it is already the ``uncovered`` direction, and
        one gap must not trip two gates.
        """
        return [r for r in self.requirements if r.covered and r.verified]

    @property
    def unverified(self) -> list[RequirementRow]:
        """Modelled but untested: covered rows no feature file references.

        Empty when the side did not run — a check that never happened
        reports nothing, the same reason the JSON omits its keys.
        """
        if not self.verification_ran:
            return []
        return [r for r in self.requirements if r.covered and not r.verified]


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


def load_inventory(
    path: str | Path, *, on_warning: "callable | None" = None
) -> list[str]:
    """Requirement IDs from an explicit list file, order preserved, deduped.

    ``.json`` / ``.yaml`` / ``.yml``: an array whose items are ID strings or
    objects with an ``id`` key, or an object whose ``requirements`` key
    holds such an array (richer snapshot columns ride along untouched).
    Anything else is read as text: one ID per line; blank lines, full-line
    ``#`` comments and inline ``<whitespace>#`` comments are ignored (a
    ``#`` with no whitespace before it stays part of the ID). An ID that
    still contains whitespace after stripping is kept verbatim and
    reported through *on_warning* — it can never match a sane reference
    pattern, so silence would present it as merely uncovered.
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
    return _ids_from_text(text, p, on_warning)


def _ids_from_text(text: str, path: Path, on_warning=None) -> list[str]:
    """IDs from the plain-text inventory form, one per line.

    A ``#`` preceded by whitespace starts an inline comment; a ``#``
    embedded in the ID (``REQ#5``) is kept. Whitespace inside a stripped
    ID is unmatchable by construction, so it is surfaced via
    *on_warning* rather than silently reported as uncovered later.
    """
    ids = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = re.split(r"\s#", s, maxsplit=1)[0].strip()
        if not s:
            continue
        if on_warning is not None and re.search(r"\s", s):
            on_warning(
                f"{path}:{lineno}: requirement ID {s!r} contains whitespace "
                "and can never match a reference pattern"
            )
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

    **Both the file's name and its text are matched.** Identifier schemes
    that carry the ID in the filename (``ADR-0007-use-plantuml.md``,
    ``REQ-123.md``) are as common as ones that write it in the body, and
    scanning the body alone finds nothing at all for them — an empty
    inventory, which the matrix can only report as every reference being
    unknown. The name is scanned before the text, so a file's own ID
    precedes any it merely cites.

    Note that this cannot reconcile *different* spellings of one ID: a
    tree of ``0001-use-plantuml.md`` files holds ``0001``, not
    ``ADR-0001``, so a pattern written for the prose form still matches
    nothing there. That is an inventory the pattern genuinely does not
    describe, and the caller is expected to say so rather than let it pass
    as silence.
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
        ids.extend(m.group(0) for m in pattern.finditer(f.name))
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


# -- feature files (the verification side) -----------------------------------


def feature_references(
    text: str, file_name: str, pattern: re.Pattern[str]
) -> dict[str, tuple[ScenarioRef, ...]]:
    """IDs a feature file references → the scenarios each is attributed to.

    The file's **name** is matched first (line 0, the file's own), then
    each line of text in order — the same two haystacks and the same
    whole-match rule as :func:`scan_inventory`, so a ``REQ-123.feature``
    file, a ``@REQ-123`` tag and a step that names the ID are all found
    by one mechanism. Attribution follows Gherkin's tag rules (module
    docstring) via :func:`attribute_lines`; per ID and scenario the first
    carrying line wins, and the tuple is in file order.
    """
    refs: dict[str, dict[str | None, ScenarioRef]] = {}

    def _add(rid: str, ref: ScenarioRef) -> None:
        refs.setdefault(rid, {}).setdefault(ref.scenario, ref)

    for m in pattern.finditer(file_name):
        _add(m.group(0), ScenarioRef(0))
    lines = text.splitlines()
    owners = attribute_lines(lines)
    for lineno, line in enumerate(lines, start=1):
        ids = [m.group(0) for m in pattern.finditer(line)]
        if not ids:
            continue
        for scenario, scenario_line in owners[lineno - 1]:
            for rid in ids:
                _add(rid, ScenarioRef(lineno, scenario, scenario_line))
    return {rid: tuple(by_scn.values()) for rid, by_scn in refs.items()}


def _keyword(line: str, keywords: tuple[str, ...]) -> str | None:
    return next((k for k in keywords if line.startswith(k)), None)


def attribute_lines(lines: list[str]) -> list[list[tuple[str | None, int]]]:
    """For each line, the scenarios a reference on it belongs to.

    One entry per line: a list of ``(scenario, heading_line)`` pairs —
    ``(None, 0)`` for the file itself. A line belongs to several scenarios
    only through inheritance: a tag line above ``Feature:`` or ``Rule:``
    is attributed to every scenario under that container, resolved once
    the whole file has been read. Doc-string fences suppress keyword
    recognition inside them. A ``# language:`` header naming a dialect
    other than English disables recognition altogether, and every line is
    the file's.
    """
    file_owner: list[tuple[str | None, int]] = [(None, 0)]
    owners: list[list[tuple[str | None, int]]] = [list(file_owner) for _ in lines]
    if lines:
        m = _LANGUAGE_HEADER.match(lines[0])
        if m and not m.group(1).lower().startswith("en"):
            return owners

    pending: list[int] = []  # tag lines since the last keyword
    feature_tags: list[int] = []  # tag lines above Feature: (whole file)
    rule_tags: list[int] = []  # tag lines above the current Rule:
    current: tuple[str, int] | None = None  # the open scenario
    scenarios: list[tuple[tuple[str, int], list[int], list[int]]] = []
    in_docstring: str | None = None

    for i, raw in enumerate(lines):
        line = raw.strip()
        if in_docstring:
            if line.startswith(in_docstring):
                in_docstring = None
            if current:
                owners[i] = [current]
            continue
        if line.startswith(_DOCSTRING_FENCES):
            in_docstring = line[:3]
            if current:
                owners[i] = [current]
            continue
        if line.startswith("@"):
            pending.append(i)
            continue
        if line.startswith("Feature:"):
            feature_tags, pending, current = pending, [], None
            continue
        if line.startswith("Rule:"):
            rule_tags, pending, current = pending, [], None
            continue
        if line.startswith("Background:"):
            pending, current = [], None  # its tags (invalid Gherkin) stay the file's
            continue
        kw = _keyword(line, _SCENARIO_KEYWORDS)
        if kw:
            current = (line[len(kw):].strip() or "(unnamed)", i + 1)
            scenarios.append((current, feature_tags, rule_tags))
            for t in pending:
                owners[t] = [current]
            pending = []
            owners[i] = [current]
            continue
        if _keyword(line, _EXAMPLES_KEYWORDS):
            # Examples tags apply to the pickles the enclosing outline
            # derives — to the outline itself, here.
            for t in pending:
                owners[t] = [current] if current else list(file_owner)
            pending = []
        if current:
            owners[i] = [current]
        # else: feature header, description, Background or Rule text — the file's.

    # Inheritance, resolved at the end: a Feature tag line belongs to every
    # scenario, a Rule tag line to the scenarios declared under that Rule.
    inherited: dict[int, list[tuple[str | None, int]]] = {}
    for scn, ftags, rtags in scenarios:
        for t in ftags + rtags:
            inherited.setdefault(t, []).append(scn)
    for t, scns in inherited.items():
        owners[t] = scns
    return owners


def scenario_count(text: str) -> int:
    """How many scenarios the file declares — distinct headings in
    :func:`attribute_lines`, so an outline counts once whatever its
    ``Examples`` expand to, and a non-English dialect counts none."""
    seen: set[tuple[str | None, int]] = set()
    for owner in attribute_lines(text.splitlines()):
        seen.update(o for o in owner if o[0] is not None)
    return len(seen)


def feature_name(text: str) -> str | None:
    """The first ``Feature:`` heading's title, or None — the feature-file
    counterpart of a diagram's ``@startuml`` name."""
    m = _FEATURE_HEADING.search(text)
    return m.group(1) if m else None


def scan_features(path: str | Path, pattern: re.Pattern[str]) -> list[FeatureFile]:
    """Every feature file under ``path`` with the IDs it references.

    A directory is walked for ``*.feature`` files in sorted order; an
    explicit file is scanned regardless of suffix — both exactly as
    :func:`scan_inventory` does. Paths are reported with forward slashes.
    """
    p = Path(path)
    if p.is_dir():
        files = sorted(f for f in p.rglob("*") if f.suffix.lower() in FEATURE_SUFFIXES)
    elif p.exists():
        files = [p]
    else:
        raise FileNotFoundError(p)
    out: list[FeatureFile] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        out.append(
            FeatureFile(
                f.as_posix(),
                feature_name(text),
                feature_references(text, f.name, pattern),
                scenario_count(text),
            )
        )
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
    features: Iterable[FeatureFile] | None = None,
) -> TraceResult:
    """Fold per-diagram references and the inventory into the coverage matrix.

    ``features`` (from :func:`scan_features`) adds the verification side;
    None — the default, and the v1 call — leaves every verification field
    at its "did not run" value.
    """
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

    verified_by: dict[str, list[FeatureRef]] = {i: [] for i in inventory}
    unknown_feature: dict[str, list[FeatureRef]] = {}
    unlinked_features: list[FeatureRef] = []
    feature_count: int | None = None
    scenarios = 0
    if features is not None:
        features = list(features)
        feature_count = len(features)
        for f in features:
            scenarios += f.scenario_count
            if not f.references:
                unlinked_features.append(FeatureRef(f.file, f.name, 0))
                continue
            for rid, attributions in f.references.items():
                bucket = verified_by[rid] if rid in known else unknown_feature.setdefault(rid, [])
                for a in attributions:
                    bucket.append(FeatureRef(f.file, f.name, a.line, a.scenario, a.scenario_line))

    return TraceResult(
        requirements=[
            RequirementRow(i, tuple(covered_by[i]), tuple(verified_by[i])) for i in inventory
        ],
        unknown_references=[
            UnknownReference(rid, tuple(sites)) for rid, sites in unknown.items()
        ],
        unlinked_diagrams=unlinked,
        diagram_count=len(diagrams),
        feature_count=feature_count,
        unknown_feature_references=[
            UnknownFeatureReference(rid, tuple(sites))
            for rid, sites in unknown_feature.items()
        ],
        unlinked_features=unlinked_features,
        scenario_count=scenarios,
    )
