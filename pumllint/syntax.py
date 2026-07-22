"""DIM-SYN gate: external syntactic validation via ``plantuml -checkonly``.

Kept out of :mod:`pumllint.scoring` so the scorer stays pure; this module is
the only place that spawns a process. The gate is opt-in (``scoring:
syntax_gate: true`` or ``--check-syntax``) because it needs a PlantUML/Java
installation the linter itself does not require.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence


def _default_runner(timeout: float) -> Callable[[list[str]], int]:
    def run(cmd: list[str]) -> int:
        return subprocess.run(
            cmd, capture_output=True, timeout=timeout, check=False
        ).returncode

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
    code). A missing binary raises ``FileNotFoundError`` — the CLI surfaces it
    as a config error rather than silently skipping the gate the user asked for.
    """
    cmd = [command] if isinstance(command, str) else list(command)
    run = runner or _default_runner(timeout)
    return {str(f): run(cmd + ["-checkonly", str(f)]) == 0 for f in files}
