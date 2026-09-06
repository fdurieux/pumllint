"""The prose gate: every ``--flag`` the adopter-facing docs mention exists.

A plain-English walkthrough has no golden behind it, so this is what keeps
it from lying after an option is renamed: each documented flag must be an
option of one of the CLI's parsers. Flags of a companion tool that a guide
documents on purpose are listed in FOREIGN, with their owner, so a typo
cannot hide behind the exemption.

Plain assert functions, stdlib only, for tests/run_tests.py.
"""

import re
from pathlib import Path

from pumllint import cli

ROOT = Path(__file__).resolve().parents[1]
DOCS = ("README.md", "docs/business-processes.md")
FOREIGN = {"--manifest": "aris2puml"}  # business-processes.md §7 documents the converter's flag
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")


def _cli_options() -> set[str]:
    flags: set[str] = set()
    for name, build in vars(cli).items():
        if name.startswith("build_") and name.endswith("parser") and callable(build):
            flags |= {o for o in build()._option_string_actions if o.startswith("--")}
    return flags


def test_every_documented_flag_is_a_cli_option_or_a_declared_foreign_one():
    ours = _cli_options()
    assert "--fail-on" in ours and "--fail-on-unknown-ref" in ours  # the probe works
    assert not ours & set(FOREIGN), "a foreign flag now collides with one of ours"
    for doc in DOCS:
        text = (ROOT / doc).read_text(encoding="utf-8")
        for flag in sorted({m.group() for m in FLAG.finditer(text)}):
            assert flag in ours or flag in FOREIGN, f"{doc} mentions {flag}, which the CLI does not accept"


def test_every_declared_foreign_flag_is_still_mentioned():
    """An exemption nothing uses any more is a stale allowlist entry."""
    text = "".join((ROOT / d).read_text(encoding="utf-8") for d in DOCS)
    for flag in FOREIGN:
        assert flag in text, f"{flag} is exempted but no longer documented — drop it from FOREIGN"
