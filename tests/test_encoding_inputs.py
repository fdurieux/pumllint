"""Input decoding: BOM-marked files load, and failures name the file.

PowerShell 5.1's `>` and `Out-File` write UTF-16 LE with a BOM, so diagrams a
Windows user generated from a script are not UTF-8 at all; `Set-Content`
writes the ANSI code page, which pumllint cannot decode and must reject by
name rather than with a bare codec error. Plain assert functions for the
zero-dependency runner.
"""

import codecs
import json
import tempfile
from pathlib import Path

from pumllint.baseline import load_baseline
from pumllint.config import load_config
from pumllint.parser import parse_file
from pumllint.textio import read_text_file

_SRC = "@startuml Order\nAlice -> Bob : hi\n@enduml\n"


def _write(tmp, name, data: bytes) -> Path:
    p = Path(tmp) / name
    p.write_bytes(data)
    return p


def test_utf16_le_with_bom_diagram_parses():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "d.puml", codecs.BOM_UTF16_LE + _SRC.encode("utf-16-le"))
        diagrams = parse_file(p)
        assert len(diagrams) == 1 and diagrams[0].name == "Order"


def test_utf16_be_with_bom_diagram_parses():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "d.puml", codecs.BOM_UTF16_BE + _SRC.encode("utf-16-be"))
        assert len(parse_file(p)) == 1


def test_utf8_with_bom_diagram_parses():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "d.puml", codecs.BOM_UTF8 + _SRC.encode("utf-8"))
        diagrams = parse_file(p)
        assert len(diagrams) == 1 and diagrams[0].name == "Order"


def test_plain_utf8_is_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "d.puml", _SRC.encode("utf-8"))
        assert read_text_file(p, kind="diagram") == _SRC


def test_ansi_diagram_error_names_the_file_and_the_kind():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "d.puml", _SRC.replace("Bob", "Bøb").encode("cp1252"))
        try:
            parse_file(p)
        except ValueError as e:
            assert "d.puml" in str(e), e
            assert "diagram" in str(e), e
            assert "UTF-8" in str(e), e
        else:
            raise AssertionError("an undecodable diagram must raise")


def test_bad_config_error_says_config_not_diagram():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "pumllint.toml", "profile = 'codegén'\n".encode("cp1252"))
        try:
            load_config(p)
        except ValueError as e:
            assert "config file" in str(e), e
        else:
            raise AssertionError("an undecodable config must raise")


def test_bad_baseline_error_says_baseline():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "base.json", '{"nøte": 1}\n'.encode("cp1252"))
        try:
            load_baseline(p)
        except ValueError as e:
            assert "baseline" in str(e), e
        else:
            raise AssertionError("an undecodable baseline must raise")


def test_bom_config_toml_loads():
    # tomllib rejects a BOM; read_text_file strips it first.
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "pumllint.toml", codecs.BOM_UTF8 + b'profile = "codegen"\n')
        assert load_config(p)["profile"] == "codegen"


def test_bom_baseline_json_loads():
    with tempfile.TemporaryDirectory() as tmp:
        payload = {"version": 1, "diagrams": {}}
        p = _write(tmp, "base.json", codecs.BOM_UTF8 + json.dumps(payload).encode())
        assert load_baseline(p) == {}
