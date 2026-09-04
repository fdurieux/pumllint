"""Governance rules applying to any diagram type."""

from __future__ import annotations

from typing import Iterable, Sequence

from ...model import Diagram, Violation, prose_directives
from .. import CrossDiagramRule, Rule, compile_option_pattern, register


@register
class MissingTitle(Rule):
    id = "GEN001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if diagram.title is None:
            yield self.violation(diagram, diagram.start_line, "Diagram has no title")


@register
class UnnamedDiagram(Rule):
    id = "GEN002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if not diagram.name:
            yield self.violation(
                diagram,
                diagram.start_line,
                "@startuml has no name (use '@startuml my-diagram-name' for stable export filenames)",
            )


@register
class DuplicateDiagramName(CrossDiagramRule):
    """Two or more diagrams in one file share a ``@startuml`` name.

    PlantUML writes a named diagram to ``<name>.png``; its automatic ``_001``
    sequence number applies only to *unnamed* blocks, so a repeated name in
    one file makes the later render silently overwrite the earlier one —
    exit 0, "2 files generated", one image on disk. GEN002's advice ("name
    diagrams for stable export filenames") holds only while the names are
    distinct; this is the check that condition needs. Reported at every
    site, since the tool cannot know which diagram should keep the name.

    The pack's one cross-diagram rule, and a within-file one: the batch is
    grouped by ``(file, name)``, so a run over the file meets the engine's
    two-diagram gate by itself. Two *files* sharing a name collide only when
    rendered into one output directory, which is not knowable here — out of
    scope by design.
    """

    id = "GEN010"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        groups: dict[tuple[str, str], list[Diagram]] = {}
        for d in diagrams:
            if d.name:
                groups.setdefault((d.file_path, d.name), []).append(d)
        for (_, name), members in groups.items():
            if len(members) < 2:
                continue
            lines = ", ".join(str(m.start_line) for m in sorted(members, key=lambda m: m.start_line))
            for m in members:
                yield self.violation(
                    m,
                    m.start_line,
                    f"Diagram name '{name}' is used {len(members)} times in this file "
                    f"(lines {lines}) — PlantUML writes every one of them to the same "
                    "output file; one name, one diagram",
                )


@register
class InlineSkinparam(Rule):
    """Central theming beats per-diagram styling drift.

    Option ``allowed`` — list of skinparam prefixes tolerated inline.
    """

    id = "GEN003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        allowed = tuple(s.lower() for s in self.options.get("allowed", []))
        for d in diagram.skinparams:
            if allowed and d.value.lower().startswith(allowed):
                continue
            yield self.violation(
                diagram,
                d.line,
                f"Inline 'skinparam {d.value}' — move styling to the shared theme include",
            )


@register
class ParticipantNaming(Rule):
    """Declared participant names must match a configurable pattern.

    Options: ``pattern`` (regex, default PascalCase-with-dots),
    ``per_kind`` (dict of kind -> regex overriding the default).
    """

    id = "GEN004"

    DEFAULT_PATTERN = r"^[A-Z][A-Za-z0-9]*(\.[A-Z][A-Za-z0-9]*)*$"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        default = self.pattern_option("pattern", self.DEFAULT_PATTERN)
        per_kind = {
            kind: compile_option_pattern(self.id, f"per_kind.{kind}", pat)
            for kind, pat in (self.options.get("per_kind") or {}).items()
        }
        for p in diagram.participants.values():
            if not p.declared:
                continue
            pattern = per_kind.get(p.kind, default)
            if not pattern.match(p.name):
                yield self.violation(
                    diagram,
                    p.line,
                    f"{p.kind.capitalize()} name '{p.name}' does not match pattern {pattern.pattern!r}",
                )


@register
class MaxParticipants(Rule):
    """Too many elements on one canvas = diagram doing too much.

    The budget is per diagram type, because the elements are not comparable: a
    sequence budget counts *lifelines*, a use-case budget counts actors *plus*
    goals, so a textbook three-actor/seven-goal diagram would trip the sequence
    number. Options: ``max`` (applies to every type) and ``per_type`` (dict of
    diagram type -> limit, the narrower override). ``per_type`` is keyed by
    diagram type; GEN004's ``per_kind`` is keyed by participant kind.
    """

    id = "GEN005"

    DEFAULT_MAX = 9

    DEFAULT_MAX_BY_TYPE = {"usecase": 15}

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        per_type = self.options.get("per_type") or {}
        if diagram.diagram_type in per_type:
            limit = int(per_type[diagram.diagram_type])
        elif "max" in self.options:
            # An explicit project-wide max stays authoritative for every type.
            limit = int(self.options["max"])
        else:
            limit = self.DEFAULT_MAX_BY_TYPE.get(diagram.diagram_type, self.DEFAULT_MAX)
        if diagram.diagram_type == "usecase":
            # Link endpoints materialize as declared=False participants;
            # only the declared actors and use cases count against the budget.
            count = sum(1 for p in diagram.participants.values() if p.declared)
            advice = "consider splitting per actor goal or into packages"
        else:
            count = len(diagram.participants)
            advice = (
                "consider splitting per phase or using 'ref over' "
                "(not parsed: lint the extracted file too)"
            )
        if count > limit:
            yield self.violation(
                diagram,
                diagram.start_line,
                f"Diagram has {count} participants (max {limit}) — {advice}",
            )


# The carrier set for owner/requirement tags is shared with `pumllint trace`
# (one definition in pumllint.model, so rule and matrix agree by construction).
_prose_directives = prose_directives


@register
class OwnerTag(Rule):
    """Diagrams must declare ownership (team, maintainer) somewhere findable.

    There is no universal ownership convention, so the rule is dormant until
    the project configures one: option ``pattern`` (regex, e.g.
    ``(?i)owner\\s*:``) is matched against the title, header, footer, caption
    and note texts.
    """

    id = "GEN006"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if self.dormant:
            return
        pattern = compile_option_pattern(self.id, "pattern", self.options["pattern"])
        if any(pattern.search(d.value) for d in _prose_directives(diagram)):
            return
        yield self.violation(
            diagram,
            diagram.start_line,
            f"No ownership tag matching {pattern.pattern!r} in title/header/footer/caption/notes",
        )


@register
class RequirementLink(Rule):
    """Diagrams must reference the requirement/ADR they realize.

    Reference schemes are project-specific (``REQ-123``, ``ADR-0007``,
    ticket keys, URLs), so the rule is dormant until option ``pattern``
    (regex, e.g. ``REQ-\\d+|ADR-\\d+``) supplies the project's scheme; it is
    matched against the diagram name plus title/header/footer/caption/notes.
    """

    id = "GEN007"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if self.dormant:
            return
        pattern = compile_option_pattern(self.id, "pattern", self.options["pattern"])
        haystacks = [d.value for d in _prose_directives(diagram)]
        if diagram.name:
            haystacks.append(diagram.name)
        if any(pattern.search(h) for h in haystacks):
            return
        yield self.violation(
            diagram,
            diagram.start_line,
            f"No requirement/ADR reference matching {pattern.pattern!r} in name/title/header/footer/caption/notes",
        )


@register
class NoteDensity(Rule):
    """Structure drowning in prose: too many notes for the diagram's size.

    Notes annotate; they should not carry the model. Options: ``min_notes``
    (default 4 — smaller counts never fire) and ``max_ratio`` (default 0.5
    notes per element).
    """

    id = "GEN008"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        notes = [d for d in diagram.directives if d.kind == "note"]
        if not notes:
            return
        min_notes = int(self.options.get("min_notes", 4))
        max_ratio = float(self.options.get("max_ratio", 0.5))
        elements = max(1, diagram.element_count)
        if len(notes) >= min_notes and len(notes) > max_ratio * elements:
            yield self.violation(
                diagram,
                notes[0].line,
                f"{len(notes)} notes on {elements} element(s) — model the structure "
                "instead of narrating it in notes",
            )
            return
        # Opt-in length test: a couple of notes can still carry the model in
        # prose. No default — configuring it is a deliberate scoring decision.
        max_chars = self.options.get("max_chars_per_element")
        if max_chars is None:
            return
        chars = sum(len(d.value) for d in notes)
        if chars > float(max_chars) * elements:
            yield self.violation(
                diagram,
                notes[0].line,
                f"{chars} characters of notes on {elements} element(s) "
                f"(max {max_chars} per element) — model the structure instead "
                "of narrating it in notes",
            )


@register
class MaxElements(Rule):
    """Diagram grown past readable size, whatever its type.

    Option: ``max`` (default 60 semantic elements — the same count the
    maturity scorer uses as its density denominator).
    """

    id = "GEN009"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        limit = int(self.options.get("max", 60))
        count = diagram.element_count
        if count > limit:
            yield self.violation(
                diagram,
                diagram.start_line,
                f"Diagram has {count} elements (max {limit}) — split it along "
                "phases, subsystems or scenarios",
            )


@register
class OrphanUseCaseActor(Rule):
    """Actor or use case participating in no relationship.

    Membership, not reachability: any link counts (a use case connected only
    to another use case is linked), and a diagram with no links at all is
    not examined.
    """

    id = "UC001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if not diagram.usecase_links:
            return
        linked: set[str] = set()
        for link in diagram.usecase_links:
            linked.add(link.source)
            linked.add(link.target)
        for p in diagram.participants.values():
            if p.declared and p.name not in linked:
                yield self.violation(
                    diagram,
                    p.line,
                    f"{p.kind.capitalize()} '{p.name}' is not linked to anything",
                )


@register
class IncludeExtendDirection(Rule):
    """``<<include>>``/``<<extend>>`` arrows point the right way.

    ``<<include>>`` points from base to included case; ``<<extend>>`` from
    extension to base. Both relate use cases only — an actor endpoint is
    always wrong. Direction is judged against actor connectivity (the base
    case is the one an actor reaches through a plain association) and only
    when that evidence is unambiguous: exactly one endpoint actor-connected.
    """

    id = "UC003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        stereo = [
            link for link in diagram.usecase_links
            if link.stereotype in ("include", "extend")
        ]
        if not stereo:
            return
        actors = {
            p.name for p in diagram.participants.values() if p.kind == "actor"
        }
        connected: set[str] = set()  # use cases an actor reaches via plain links
        for link in diagram.usecase_links:
            if link.stereotype in ("include", "extend"):
                continue
            if link.source in actors and link.target not in actors:
                connected.add(link.target)
            elif link.target in actors and link.source not in actors:
                connected.add(link.source)
        for link in stereo:
            st = link.stereotype
            actor_end = next(
                (n for n in (link.source, link.target) if n in actors), None
            )
            if actor_end:
                yield self.violation(
                    diagram,
                    link.line,
                    f"<<{st}>> must relate two use cases — '{actor_end}' is an actor",
                )
                continue
            src_conn = link.source in connected
            if src_conn == (link.target in connected):
                continue  # neither or both actor-connected: no verdict
            if st == "include" and not src_conn:
                yield self.violation(
                    diagram,
                    link.line,
                    f"<<include>> points from base to included case — "
                    f"'{link.target}' is the actor-facing base, so the arrow appears reversed",
                )
            elif st == "extend" and src_conn:
                yield self.violation(
                    diagram,
                    link.line,
                    f"<<extend>> points from extension to base — "
                    f"'{link.source}' is the actor-facing base, so the arrow appears reversed",
                )


@register
class UseCaseActorNaming(Rule):
    """Use cases as verb–object phrases ("Place order").

    Actor naming is not checked. Option ``verbs`` supplies the accepted leading
    verbs for use-case names; with no whitelist the rule is dormant (there is no
    language-agnostic verb oracle).
    """

    id = "UC002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if self.dormant:
            return
        verbs = {v.lower() for v in self.options["verbs"]}
        for p in diagram.participants.values():
            if p.kind != "usecase" or not p.declared:
                continue
            label = p.display_name or p.name
            if not label:
                continue
            parts = label.split()
            if not parts:
                continue  # whitespace-only name: UC001/GEN004 territory, not a verb question
            if parts[0].lower() not in verbs:
                yield self.violation(
                    diagram,
                    p.line,
                    f"Use case '{label}' is not verb-first — name it "
                    '"verb + object" (e.g. "Place order")',
                )
