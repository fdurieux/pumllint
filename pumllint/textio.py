"""Text file reading with encoding failures that name the file.

Every text input pumllint reads — diagrams, config, baselines, requirement
inventories — goes through :func:`read_text_file`. Two reasons it is not a
bare ``read_text(encoding="utf-8")``:

* Windows editors and PowerShell write UTF-16. PowerShell 5.1's ``>`` and
  ``Out-File`` default to UTF-16 LE with a BOM, so a ``.puml`` a Windows user
  generated from a script is not UTF-8 at all. A BOM is unambiguous, so
  honouring it costs nothing and rescues those files.
* When decoding genuinely fails, the message has to say *which* file and
  *which kind* of file. ``error: 'utf-8' codec can't decode byte 0xff`` names
  neither, which is indistinguishable from "pumllint does not understand my
  diagram".

Guessing is deliberately not on the list: falling back to the locale encoding
would silently mis-decode a cp1252 file into wrong participant names and then
lint it green. An error the user can act on beats a wrong answer.

A leaf module on purpose — config and baseline reading must not grow an
import edge into the parser package.
"""

from __future__ import annotations

import codecs
from pathlib import Path

_BOMS = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF32_LE, "utf-32"),  # before UTF-16 LE: its BOM is a prefix
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


def read_text_file(path: str | Path, *, kind: str = "file") -> str:
    """Decode *path* as text, honouring a BOM, else strict UTF-8.

    ``kind`` names the subsystem in the error message ("diagram", "config
    file", ...) so a bad config never reads like a bad diagram.
    """
    p = Path(path)
    data = p.read_bytes()
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError as e:
                raise _decode_error(p, kind, e, encoding) from None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise _decode_error(p, kind, e, "utf-8") from None


def _decode_error(p: Path, kind: str, e: UnicodeDecodeError, encoding: str) -> ValueError:
    return ValueError(
        f"{p}: {kind} is not valid {encoding.upper()} ({e.reason} at byte {e.start}) "
        f"— re-save it as UTF-8. PowerShell 5.1's '>' and Out-File write UTF-16 "
        f"and Set-Content writes the ANSI code page; pumllint reads UTF-8, or "
        f"UTF-16/UTF-32 when the file carries a byte-order mark"
    )
