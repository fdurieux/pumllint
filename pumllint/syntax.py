"""DIM-SYN gate: external syntactic validation via ``plantuml -checkonly``.

Kept out of :mod:`pumllint.scoring` so the scorer stays pure; this module is
the only place that spawns a process. The gate is opt-in (``scoring:
syntax_gate: true`` or ``--check-syntax``) because it needs a PlantUML/Java
installation the linter itself does not require.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence


def _unquote(token: str) -> str:
    """Drop one matched pair of surrounding quotes."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def _split_command(command: str, *, windows: bool = os.name == "nt") -> list[str]:
    """Split a string command into argv the way the platform reads it.

    POSIX splitting treats a backslash as an escape character, so
    ``java -jar C:\\tools\\plantuml.jar`` — the normal Windows PlantUML
    setup — would arrive as ``C:toolsplantuml.jar`` and the gate would fail
    naming a path the user never typed. Windows splits without escaping,
    which keeps the separators but leaves quotes on the tokens.
    """
    if not windows:
        return shlex.split(command)
    return [_unquote(token) for token in shlex.split(command, posix=False)]


def _resolve_program(program: str) -> str:
    """The executable *program* names, or an error that says it is missing.

    ``subprocess`` resolves a bare name through ``CreateProcess`` on Windows,
    which appends ``.exe`` and never consults ``PATHEXT`` — so a
    ``plantuml.bat`` wrapper on PATH, the usual Windows install, is invisible
    and the gate fails on a machine where ``plantuml`` runs fine from the same
    prompt. ``shutil.which`` does apply PATHEXT, and hands back a full path
    ``CreateProcess`` can launch.
    """
    found = shutil.which(program)
    if found is None:
        raise FileNotFoundError(
            f"syntax gate: command {program!r} was not found on PATH — set "
            f"scoring.syntax_command to the full path of the executable, or "
            f"to an argv list such as [java, -jar, plantuml.jar]"
        )
    return found


def _default_runner(timeout: float) -> Callable[[list[str]], int]:
    resolved: dict[str, str] = {}

    def run(cmd: list[str]) -> int:
        program = resolved.get(cmd[0])
        if program is None:
            program = resolved[cmd[0]] = _resolve_program(cmd[0])
        argv = [program, *cmd[1:]]
        try:
            return subprocess.run(
                argv, capture_output=True, timeout=timeout, check=False
            ).returncode
        except subprocess.TimeoutExpired:
            # Surface as a config error (the CLI maps ValueError to exit 2)
            # rather than a traceback.
            raise ValueError(
                f"syntax gate timed out after {timeout:g}s running: {' '.join(argv)}"
            ) from None

    return run


def check_files(
    files: Iterable[str | Path],
    command: str | Sequence[str] = "plantuml",
    timeout: float = 60.0,
    runner: Optional[Callable[[list[str]], int]] = None,
) -> dict[str, bool]:
    """Run ``<command> -checkonly <file>`` per file; True = syntax passes.

    Files are checked one at a time so each diagram file gets its own verdict.
    ``runner`` is injectable for tests (takes the argv list, returns the exit
    code). The real runner resolves the executable with ``shutil.which`` so a
    ``plantuml.bat`` wrapper on PATH is found on Windows; a missing binary
    raises ``FileNotFoundError`` — the CLI surfaces it as a config error
    rather than silently skipping the gate the user asked for.
    """
    # A string command is shell-split so `syntax_command: java -jar plantuml.jar`
    # works the way it reads; pass a list to control argv exactly.
    cmd = _split_command(command) if isinstance(command, str) else list(command)
    if not cmd:
        raise ValueError("syntax gate: scoring.syntax_command is empty")
    run = runner or _default_runner(timeout)
    # Keyed the way diagrams are tagged (forward slashes), so the score
    # gate still finds its verdict on Windows.
    return {
        Path(f).as_posix(): run(cmd + ["-checkonly", str(f)]) == 0 for f in files
    }
