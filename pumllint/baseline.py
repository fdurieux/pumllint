"""Baseline/ratchet support for the ``score`` command.

A baseline records each diagram's maturity level at a point in time. On later
runs the gate fails only on *regression* — a diagram dropping below its
recorded level — so the score gate is adoptable on a brownfield model set
without a big-bang cleanup: existing debt is tolerated, new debt is not.

Diagrams are keyed by ``<file path>::<diagram name>``, the path spelled
relative to the baseline file's own directory, with forward slashes. So one
file has one key from any working directory and under any argv spelling —
``diagrams/``, ``./diagrams``, an absolute path, ``.`` from inside
``diagrams/`` — and a committed baseline still matches when the whole tree is
checked out somewhere else. The anchor is the file itself: keep it where it
is (moving the file alone changes every key — re-record with
``--update-baseline``). Unnamed diagrams fall back to their per-file ordinal
(``::#0``) so the key survives edits elsewhere in the file. A ``#`` in a
name is doubled in the key (``Dup#1`` → ``::Dup##1``), so a name can never
be read as an ordinal and no two diagrams share a key. Diagrams new
since the baseline pass by definition (they can be gated with
``--min-level``); diagrams removed from the set are ignored by the ratchet.
``--update-baseline`` merges by file (:func:`carry_over`): the run's entries
replace those of every file it scored, entries of files it did not score
stay while the file exists and go once it is gone — so updating from one
file, or from pre-commit's staged list, does not shrink the file, and a
deleted file's entries leave on the next update.

Version 1 files (through 0.30.0) keyed on the recording run's own path
spelling, so the ratchet only matched from the same directory with the same
spelling. They are still read: a file recorded the canonical way — from its
own directory with relative paths — already carries the anchored keys and now
matches under every spelling; any other key matches exactly as it did. The
next write produces version 2.

Reading: :func:`load_baseline` returns the file's entries under the keys it
stores; :func:`resolve_baseline` re-keys them onto a run's
:func:`diagram_keys`, which is what :func:`find_regressions`,
:func:`compute_deltas` and the reporters look up (the two functions do the
translation themselves when handed a loaded file). Writing:
:func:`write_baseline` records a run; handed the loaded file as ``previous``
it updates it in place, by file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Callable, Iterable, Mapping

from .model import Diagram
from .textio import read_text_file
from .scoring import MaturityResult

BASELINE_VERSION = 2  # what write_baseline emits
_READABLE_VERSIONS = (1, 2)  # what load_baseline accepts


@dataclass
class BaselineEntry:
    level: int
    composite: float  # informational; the ratchet compares levels only


@dataclass
class Regression:
    key: str
    baseline_level: int
    current_level: int


@dataclass
class Delta:
    """Level movement of one diagram since the baseline was recorded."""

    baseline_level: int
    current_level: int

    @property
    def delta(self) -> int:
        return self.current_level - self.baseline_level


class BaselineFile(dict):
    """``load_baseline``'s result: the entries, plus how the file keys them.

    ``anchor`` is the directory the keys are relative to — the file's own.
    ``version`` 1 means the keys are the recording run's path spellings,
    which coincide with the anchored form only when that run was made from
    the anchor with relative paths. A ``dict`` subclass, so everything that
    only reads entries (``.get``, ``in``, ``set(...)``, ``== {}``) is
    unaffected.
    """

    def __init__(self, entries=(), *, version: int, anchor: Path):
        super().__init__(entries)
        self.version = version
        self.anchor = anchor


def _keys(diagrams: Iterable[Diagram], path_of: Callable[[Diagram], str]) -> list[str]:
    """``<path>::<name with every # doubled>``, then ``#<n>`` when the name
    is empty or repeats an earlier one in the same file.

    Doubling leaves a name with only even runs of ``#``, so a trailing odd
    run of ``#`` followed by digits can only be the ordinal: distinct
    (path, name, occurrence) triples never share a key. A name without
    ``#`` — every name in every corpus measured — keys exactly as before.
    """
    counters: dict[str, int] = {}
    keys = []
    for d in diagrams:
        base = f"{path_of(d)}::{(d.name or '').replace('#', '##')}"
        n = counters.get(base, 0)
        counters[base] = n + 1
        keys.append(base if d.name and n == 0 else f"{base}#{n}")
    return keys


def diagram_keys(diagrams: Iterable[Diagram]) -> list[str]:
    """Identity per diagram as this run spells it: file path + name, ordinal
    when unnamed.

    Grammar: ``<path>::<name>`` with every ``#`` in the name doubled, and
    ``#<n>`` appended when the name is empty (``::#0``, ``::#1`` — n counts
    the file's unnamed diagrams in document order) or repeats an earlier
    name in the same file (``::Dup``, ``::Dup#1``; no rule flags a
    duplicate name — GEN002 is *unnamed*-diagram). The doubling keeps the
    grammar injective: a diagram literally named ``Dup#1`` keys as
    ``::Dup##1`` and can neither collide with the second ``Dup`` nor be
    mistaken for it; the ordinal is always the trailing odd run of ``#``.

    Stability: a uniquely named diagram's key depends on nothing but its
    file and name; an unnamed or repeated name keys on its rank among the
    file's earlier unnamed or same-named diagrams, so only removing or
    renaming one of *those* shifts it — editing, renaming, adding or
    removing anything else never does. These are the keys the reporters,
    the ratchet and the ``regression:`` line use (a ``#`` in a name shows
    doubled there); the keys a baseline *file* stores are
    :func:`anchored_keys`.
    """
    return _keys(diagrams, lambda d: d.file_path)


def _anchored_path(resolved: Path, root: Path) -> str:
    """*resolved* spelled relative to *root* with forward slashes — the path
    part of a stored key; the resolved absolute path when no relative
    spelling exists (a file on another Windows drive)."""
    try:
        return PurePath(os.path.relpath(resolved, root)).as_posix()
    except ValueError:
        return resolved.as_posix()


def anchored_keys(diagrams: Iterable[Diagram], anchor: str | Path) -> list[str]:
    """The keys a baseline file in directory *anchor* stores.

    The path is resolved and spelled relative to *anchor* with forward
    slashes, so one file has one key from any working directory and under
    any argv spelling, and the key is the same on every platform. A file on
    another Windows drive has no relative spelling; it keys on its resolved
    absolute path instead (portable only as far as that path is).
    """
    root = Path(anchor).resolve()
    return _keys(diagrams, lambda d: _anchored_path(Path(d.file_path).resolve(), root))


def load_baseline(path: str | Path) -> BaselineFile:
    """The file's entries under the keys it stores; see :func:`resolve_baseline`."""
    try:
        raw = json.loads(read_text_file(path, kind="baseline file"))
    except json.JSONDecodeError as e:
        raise ValueError(f"baseline file {path} is not valid JSON: {e}") from e
    if not isinstance(raw, dict) or "diagrams" not in raw:
        raise ValueError(f"baseline file {path} has no 'diagrams' key")
    version = raw.get("version")
    if version not in _READABLE_VERSIONS:
        readable = " and ".join(str(v) for v in _READABLE_VERSIONS)
        raise ValueError(
            f"baseline file {path} has version {version!r}; this pumllint "
            f"reads versions {readable} — regenerate with --update-baseline"
        )
    entries: dict[str, BaselineEntry] = {}
    for key, entry in raw["diagrams"].items():
        entries[key] = BaselineEntry(
            level=int(entry["level"]), composite=float(entry.get("composite", 0.0))
        )
    return BaselineFile(entries, version=version, anchor=Path(path).resolve().parent)


def carry_over(
    previous: Mapping[str, BaselineEntry],
    results: list[tuple[Diagram, MaturityResult]],
    anchor: str | Path,
) -> tuple[dict[str, BaselineEntry], list[str]]:
    """What an update keeps of *previous* beside this run's own entries.

    The rule is per file: the run's entries replace every entry of a file it
    scored (a diagram removed from that file goes with them); entries of
    files it did not score are kept while the file still exists and dropped
    once it is gone. Returns ``(kept, dropped)`` — the kept entries in
    *previous*'s order, and the keys dropped.

    *previous* is keyed as a baseline file in directory *anchor* stores keys
    (:func:`anchored_keys`); a key's path part is what precedes its first
    ``::`` — diagram names may contain ``::``, paths do not (outside a POSIX
    name chosen to defeat this). Whether a file was scored is decided by
    identity, not spelling: an entry for a scored file under another
    spelling — the resolved absolute form a cross-drive Windows run stores,
    a version-1 key recorded as ``sub/../x.puml`` — resolves to that file
    and is superseded, not kept beside the run's entry. A version-1 key
    recorded from another directory names no file relative to *anchor* and
    is dropped, as a rewrite always dropped it.
    """
    root = Path(anchor).resolve()
    scored_parts: set[str] = set()  # anchored path parts: matched without I/O
    scored_files: set[str] = set()  # resolved identities: for other spellings
    for d, _ in results:
        resolved = Path(d.file_path).resolve()
        scored_parts.add(_anchored_path(resolved, root))
        scored_files.add(resolved.as_posix())
    kept: dict[str, BaselineEntry] = {}
    dropped: list[str] = []
    identity: dict[str, str | None] = {}  # path part -> resolved; None when gone
    for key, entry in previous.items():
        part = key.split("::", 1)[0]
        if part in scored_parts:
            continue  # superseded by the run's entries for that file
        if part not in identity:
            try:
                identity[part] = (root / part).resolve(strict=True).as_posix()
            except (OSError, RuntimeError):  # missing; a symlink loop before 3.13
                identity[part] = None
        if identity[part] is None:
            dropped.append(key)
        elif identity[part] not in scored_files:
            kept[key] = entry
    return kept, dropped


def write_baseline(
    path: str | Path,
    results: list[tuple[Diagram, MaturityResult]],
    *,
    previous: Mapping[str, BaselineEntry] | None = None,
) -> tuple[dict[str, BaselineEntry], list[str]]:
    """Record *results* in *path* (version 2 form).

    Without *previous* the file holds exactly this run's entries — a caller
    that scored a subset writes a subset. With *previous* — the file's
    current entries as :func:`load_baseline` returns them — the write is a
    merge by file (:func:`carry_over`): the run's entries replace those of
    every file scored, entries of files not scored are kept while the file
    exists. Entries keep the file's own order, so a partial update refreshes
    an entry where it stands and appends only what is new to the file — the
    diff shows what moved and nothing else. Returns what :func:`carry_over`
    returned; ``({}, [])`` without *previous*.
    """
    anchor = Path(path).resolve().parent
    current = {
        key: BaselineEntry(level=r.level, composite=round(r.composite, 2))
        for key, (_, r) in zip(anchored_keys((d for d, _ in results), anchor), results)
    }
    kept: dict[str, BaselineEntry] = {}
    dropped: list[str] = []
    entries = current
    if previous is not None:
        previous_anchor = getattr(previous, "anchor", anchor)
        if previous_anchor != anchor:
            raise ValueError(
                f"baseline entries are keyed relative to {previous_anchor}, not "
                f"{anchor}: an update writes the file where it was recorded"
            )
        kept, dropped = carry_over(previous, results, anchor)
        entries = {}
        for key in previous:
            if key in kept:
                entries[key] = kept[key]
            elif key in current:
                entries[key] = current[key]
        for key, entry in current.items():
            entries.setdefault(key, entry)
    payload = {
        "version": BASELINE_VERSION,
        "diagrams": {
            key: {"level": e.level, "composite": e.composite}
            for key, e in entries.items()
        },
    }
    # newline="": a baseline is committed and diffed across machines, so it
    # must not gain CRLF just because it was written on Windows.
    Path(path).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline=""
    )
    return kept, dropped


def resolve_baseline(
    baseline: dict[str, BaselineEntry],
    results: list[tuple[Diagram, MaturityResult]],
) -> dict[str, BaselineEntry]:
    """*baseline* re-keyed onto this run's :func:`diagram_keys`.

    A loaded file stores keys relative to its own directory; the run, the
    reporters and the ratchet key on the path as given on argv. This is the
    one translation between the two: for each scored diagram, the file's
    entry under the anchored key — or, for a version-1 file, under the
    as-given key when the anchored one is absent — lands under the run's
    key. Entries for diagrams not in this run are dropped (the ratchet
    ignores removed diagrams anyway). A plain dict has no anchor, is taken
    to be in run form already, and is returned as is — so the function is
    idempotent, and fixtures built from ``diagram_keys`` need no translation.
    """
    anchor = getattr(baseline, "anchor", None)
    if anchor is None:
        return baseline
    diagrams = [d for d, _ in results]
    legacy = getattr(baseline, "version", BASELINE_VERSION) == 1
    out: dict[str, BaselineEntry] = {}
    for run_key, stored in zip(diagram_keys(diagrams), anchored_keys(diagrams, anchor)):
        entry = baseline.get(stored)
        if entry is None and legacy:
            entry = baseline.get(run_key)
        if entry is not None:
            out[run_key] = entry
    return out


def find_regressions(
    baseline: dict[str, BaselineEntry],
    results: list[tuple[Diagram, MaturityResult]],
) -> list[Regression]:
    """Diagrams scoring below their baselined level, in result order."""
    baseline = resolve_baseline(baseline, results)
    out = []
    for key, (_, r) in zip(diagram_keys(d for d, _ in results), results):
        entry = baseline.get(key)
        if entry is not None and r.level < entry.level:
            out.append(Regression(key, entry.level, r.level))
    return out


def compute_deltas(
    baseline: dict[str, BaselineEntry],
    results: list[tuple[Diagram, MaturityResult]],
) -> dict[str, Delta]:
    """Level movement per baselined diagram (trend reporting).

    Diagrams absent from the baseline have no delta — they are new, which the
    reporters call out separately.
    """
    baseline = resolve_baseline(baseline, results)
    out: dict[str, Delta] = {}
    for key, (_, r) in zip(diagram_keys(d for d, _ in results), results):
        entry = baseline.get(key)
        if entry is not None:
            out[key] = Delta(baseline_level=entry.level, current_level=r.level)
    return out
