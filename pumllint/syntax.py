"""DIM-SYN gate: external syntactic validation via ``plantuml -checkonly``.

Kept out of :mod:`pumllint.scoring` so the scorer stays pure; this module is
the only place that spawns a process. The gate is opt-in (``scoring:
syntax_gate: true`` or ``--check-syntax``) because it needs a PlantUML/Java
installation the linter itself does not require.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence


def _default_runner(timeout: float) -> Callable[[list[str]], int]:
    def run(cmd: list[str]) -> int:
        try:
            return subprocess.run(
                cmd, capture_output=True, timeout=timeout, check=False
            ).returncode
        except subprocess.TimeoutExpired:
            # Surface as a config error (the CLI maps ValueError to exit 2)
            # rather than a traceback.
            raise ValueError(
                f"syntax gate timed out after {timeout:g}s running: {' '.join(cmd)}"
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
    code). A missing binary raises ``FileNotFoundError`` — the CLI surfaces it
    as a config error rather than silently skipping the gate the user asked for.
    """
    # A string command is shell-split so `syntax_command: java -jar plantuml.jar`
    # works the way it reads; pass a list to control argv exactly.
    cmd = shlex.split(command) if isinstance(command, str) else list(command)
    run = runner or _default_runner(timeout)
    # Keyed the way diagrams are tagged (forward slashes), so the score
    # gate still finds its verdict on Windows.
    return {
        Path(f).as_posix(): run(cmd + ["-checkonly", str(f)]) == 0 for f in files
    }
