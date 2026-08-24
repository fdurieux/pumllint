"""Codegen-readiness rules (SEQ101–SEQ109), active under the ``codegen`` profile.

These rules validate whether a sequence diagram is precise and complete enough
for an AI coding agent (or any downstream generator) to implement it without
inventing missing details. They are disabled by default and activate with
``profile: codegen`` (config) or ``--profile codegen`` (CLI).

Rule ids SEQ100–SEQ199 are reserved for this range to avoid collision with the
base catalog (SEQ001–SEQ099).
"""

from __future__ import annotations

import re

from ...model import (
    Diagram,
    pair_calls_and_replies,
    walk_activation_stack,
)
from .. import Rule, register

# Participant kinds that already convey an implementation mapping (SEQ102),
# and kinds that denote persistence/messaging infrastructure (SEQ107).
_TYPED_KINDS = ("actor", "boundary", "control", "entity", "database", "collections", "queue")
_PERSISTENT_KINDS = ("database", "queue")

_SIGNATURE = re.compile(r"[A-Za-z_][\w.]*\s*\(.*\)")


class _CodegenRule(Rule):
    """Shared plumbing for codegen rules.

    Scope and profile gating (sequence-only, ``codegen`` profile) come from each
    rule's ``catalog.toml`` entry, like every other rule.
    """

    def lexicon(self, key: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
        """A configurable lowercase word list, overridable per project."""
        raw = self.options.get(key, defaults)
        return tuple(str(t).lower() for t in raw)


@register
class ExplicitParticipants(_CodegenRule):
    id = "SEQ101"

    def check(self, diagram: Diagram):
        for p in diagram.participants.values():
            if not p.declared:
                yield self.violation(
                    diagram,
                    p.line,
                    f"Participant '{p.name}' is created implicitly on first use; "
                    "declare it (participant/actor/database/...) so its identity is authoritative",
                )


@register
class TypedParticipants(_CodegenRule):
    id = "SEQ102"

    def check(self, diagram: Diagram):
        for p in diagram.participants.values():
            if p.declared and p.kind == "participant" and not p.stereotype:
                yield self.violation(
                    diagram,
                    p.line,
                    f"Participant '{p.name}' has no role type; use a typed keyword "
                    f"({', '.join(_TYPED_KINDS)}) or a <<stereotype>>",
                )


def _prose_argument(label: str, stop_words: tuple[str, ...], max_words: int) -> str | None:
    """Why the parenthesised argument list reads as prose, or None if it is
    signature-shaped.

    Precision-first heuristic: function words and wide multi-word arguments
    are prose signals; ``name: Type`` params collapse to one token and fully
    quoted literals pass as single compilable values. Two-word arguments with
    no function word (``Order order``) deliberately pass.
    """
    inner = label[label.find("(") + 1 : label.rfind(")")]
    for arg in inner.split(","):
        arg = arg.strip()
        if not arg:
            continue
        if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in "\"'":
            continue  # quoted literal — a compilable value, not prose
        tokens = re.sub(r":\s+", ":", arg).split()
        if len(tokens) > max_words:
            return f"'{arg}' reads as {len(tokens)} words"
        for t in tokens:
            if t.strip(".,:;!?\"'()[]").lower() in stop_words:
                return f"function word in '{arg}'"
    return None


@register
class SignatureMessages(_CodegenRule):
    id = "SEQ103"

    # Function words that never name a compilable parameter; overridable via
    # the `arg_stop_words` option, like the other codegen lexicons.
    DEFAULT_ARG_STOP_WORDS = (
        "a", "an", "the", "and", "or", "but", "nor",
        "is", "are", "was", "were", "be", "been",
        "we", "you", "it", "they",
        "if", "then", "else", "when", "while", "that", "this", "which", "whether",
        "not", "no",
        "of", "with", "for", "to", "from", "by", "at", "on", "in", "into",
        "per", "via", "as", "etc", "some", "stuff",
    )

    def check(self, diagram: Diagram):
        pattern = self.pattern_option("pattern", _SIGNATURE.pattern)
        stop_words = self.lexicon("arg_stop_words", self.DEFAULT_ARG_STOP_WORDS)
        max_words = int(self.options.get("max_arg_words", 2))
        for m in diagram.messages:
            if m.is_return_arrow:
                continue  # replies are SEQ109's concern
            label = m.label.strip()
            shown = label or "<unlabelled>"
            if not pattern.fullmatch(label):
                yield self.violation(
                    diagram,
                    m.line,
                    f"Message '{shown}' is not signature-shaped; use "
                    "name(params) (the accepted shape is the 'pattern' option)",
                )
                continue
            reason = _prose_argument(label, stop_words, max_words)
            if reason:
                yield self.violation(
                    diagram,
                    m.line,
                    f"Message '{shown}' hides prose in its arguments "
                    f"({reason}); use identifier parameters "
                    "('arg_stop_words' / 'max_arg_words' options)",
                )


@register
class SyncCallsReturn(_CodegenRule):
    id = "SEQ104"

    def check(self, diagram: Diagram):
        for cr in pair_calls_and_replies(diagram):
            if not cr.answered:
                shown = cr.call.label.strip() or "<unlabelled>"
                yield self.violation(
                    diagram,
                    cr.call.line,
                    f"Synchronous call '{shown}' has no explicit return; "
                    "add a reply arrow (-->) naming the returned value, or mark it async (->>)",
                )


@register
class MachineEvaluableGuards(_CodegenRule):
    id = "SEQ105"

    DEFAULT_VAGUE = ("otherwise", "sometimes", "if needed", "maybe", "as required")
    KINDS = ("alt", "opt", "loop")

    def check(self, diagram: Diagram):
        vague = self.lexicon("vague_terms", self.DEFAULT_VAGUE)
        kinds = tuple(self.options.get("kinds", self.KINDS))
        for b in diagram.blocks:
            if b.kind not in kinds:
                continue
            guard = b.label.strip().strip("[]").strip()
            if not guard:
                yield self.violation(
                    diagram, b.start_line, f"'{b.kind}' fragment has no guard condition"
                )
            elif guard.lower() in vague:
                yield self.violation(
                    diagram,
                    b.start_line,
                    f"Guard '{guard}' is a known vague phrase "
                    "('vague_terms' option); write a boolean expression instead",
                )
            for br in b.else_branches:
                guard = br.label.strip().strip("[]").strip()
                if not guard:
                    yield self.violation(
                        diagram, br.line, "'else' branch has no guard condition"
                    )
                elif guard.lower() == "else":
                    if b.kind != "alt" or len(b.else_branches) != 1:
                        yield self.violation(
                            diagram,
                            br.line,
                            "literal [else] is only allowed as the complement "
                            "of a two-branch alt",
                        )
                elif guard.lower() in vague:
                    yield self.violation(
                        diagram,
                        br.line,
                        f"Guard '{guard}' is a known vague phrase "
                        "('vague_terms' option); write a boolean expression instead",
                    )


@register
class NoElisionMarkers(_CodegenRule):
    id = "SEQ106"

    DEFAULT_TOKENS = ("...", "…", "TBD", "TODO", "etc", "???", "and so on")

    def check(self, diagram: Diagram):
        tokens = self.lexicon("tokens", self.DEFAULT_TOKENS)
        word_tokens = [t for t in tokens if re.fullmatch(r"[\w ]+", t)]
        symbol_tokens = [t for t in tokens if t not in word_tokens]
        word_re = (
            re.compile(r"\b(?:" + "|".join(map(re.escape, word_tokens)) + r")\b", re.IGNORECASE)
            if word_tokens
            else None
        )

        def offending(text: str) -> str | None:
            for t in symbol_tokens:
                if t in text:
                    return t
            if word_re:
                m = word_re.search(text)
                if m:
                    return m.group(0)
            return None

        sources = [(m.line, "message", m.label) for m in diagram.messages]
        for b in diagram.blocks:
            sources.append((b.start_line, "guard", b.label))
            sources.extend((br.line, "guard", br.label) for br in b.else_branches)
        sources.extend(
            (d.line, "note", d.value) for d in diagram.directives if d.kind == "note"
        )
        for line, where, text in sorted(sources):
            tok = offending(text)
            if tok:
                yield self.violation(
                    diagram,
                    line,
                    f"Elision marker '{tok}' in {where} signals omitted behaviour; "
                    "model it or the generator will invent it",
                )


def _branch_spans(block) -> list[tuple[str, int, float]]:
    """(label, lo, hi) per branch of a fragment; content lines satisfy lo < line < hi."""
    end: float = block.end_line if block.end_line is not None else float("inf")
    edges: list[float] = [block.start_line, *(br.line for br in block.else_branches), end]
    labels = [block.label, *(br.label for br in block.else_branches)]
    return [(labels[i], int(edges[i]), edges[i + 1]) for i in range(len(labels))]


@register
class ExternalCallsFailurePath(_CodegenRule):
    id = "SEQ107"

    DEFAULT_FAILURE = ("error", "failure", "timeout", "exception")
    _NEGATED = re.compile(r"(?:\bnot\b|!=|^\s*!)", re.IGNORECASE)

    def check(self, diagram: Diagram):
        failure_kw = self.lexicon("failure_keywords", self.DEFAULT_FAILURE)

        def is_failure_label(label: str) -> bool:
            low = label.lower()
            return any(k in low for k in failure_kw) or bool(self._NEGATED.search(label))

        content_lines = [m.line for m in diagram.messages]
        content_lines += [a.line for a in diagram.activations if a.kind == "return"]

        def has_failure_branch(b) -> bool:
            # A declared-but-empty failure branch models nothing: the branch
            # must carry at least one message (or a return) to count.
            return any(
                is_failure_label(label) and any(lo < ln < hi for ln in content_lines)
                for label, lo, hi in _branch_spans(b)
            )

        fragile = {
            p.name
            for p in diagram.participants.values()
            if p.kind in _PERSISTENT_KINDS
            or (p.stereotype or "").lower() == "external"
        }
        error_groups = [
            b for b in diagram.blocks if b.kind == "group" and is_failure_label(b.label)
        ]
        for m in diagram.messages:
            if m.is_return_arrow or m.effective_target not in fragile:
                continue
            guarded = any(
                b.kind == "alt" and b.contains_line(m.line) and has_failure_branch(b)
                for b in diagram.blocks
            )
            guarded = guarded or any(
                b.kind == "break" and b.contains_line(m.line) for b in diagram.blocks
            )
            guarded = guarded or any(g.contains_line(m.line) for g in error_groups)
            if not guarded:
                shown = m.label.strip() or "<unlabelled>"
                yield self.violation(
                    diagram,
                    m.line,
                    f"Call '{shown}' to '{m.effective_target}' has no enclosing alt "
                    "error branch, break, or group error fragment; add one (failure "
                    "vocabulary: 'failure_keywords' option, or a negated guard)",
                )


@register
class ActivationLifecycle(_CodegenRule):
    id = "SEQ108"

    def check(self, diagram: Diagram):
        orphans, dangling = walk_activation_stack(diagram)
        for a in orphans:
            yield self.violation(
                diagram,
                a.line,
                f"'deactivate {a.participant}' has no open activation to close",
            )
        for participant, line in dangling:
            yield self.violation(
                diagram,
                line,
                f"Activation of '{participant}' is never closed; "
                "the call scope is ambiguous for a generator",
            )


@register
class InformativeReplies(_CodegenRule):
    id = "SEQ109"

    DEFAULT_NON_INFORMATIVE = ("ok", "done", "success", "response", "result")

    def check(self, diagram: Diagram):
        noninf = self.lexicon("non_informative", self.DEFAULT_NON_INFORMATIVE)

        # (b) reply arrows must name the returned value
        for m in diagram.messages:
            if not m.is_return_arrow:
                continue
            label = m.label.strip()
            if not label or label.lower() in noninf:
                shown = label or "<unlabelled>"
                yield self.violation(
                    diagram,
                    m.line,
                    f"Reply '{shown}' is empty or a generic label "
                    "('non_informative' option); name the returned value (e.g. 'order: Order')",
                )

        # (a) returns drawn with a solid arrow toward the caller of an open call
        open_calls: list = []
        for m in sorted(diagram.messages, key=lambda m: m.line):
            src, dst = m.effective_source, m.effective_target
            if m.is_return_arrow:
                open_calls = [
                    c for c in open_calls
                    if not (c.effective_source == dst and c.effective_target == src)
                ]
                continue
            if m.is_async or src is None or dst is None or src == dst:
                continue
            for c in reversed(open_calls):
                if c.effective_source == dst and c.effective_target == src:
                    open_calls.remove(c)
                    yield self.violation(
                        diagram,
                        m.line,
                        f"Return to '{dst}' is drawn with a solid arrow; "
                        "use a reply arrow (-->) so call and return can be paired",
                    )
                    break
            else:
                open_calls.append(m)
