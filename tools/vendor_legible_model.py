"""Re-vendor the Legible systemic impact model under the kg demo from a checkout of the site.

    python tools/vendor_legible_model.py ../fdurieux.github.io            # at the checkout's commit
    python tools/vendor_legible_model.py ../fdurieux.github.io --dry-run  # say what would change

The model's identity is the ``"version"`` field inside ``model/model.json``, which the site
generates from ``model/model-data.py`` and the demo page quotes; the site repository carries
no tags today, so a tag is recorded when the commit has one and not required. The checkout
must be clean. The tool copies ``model/model.json`` byte for byte to
``kg_experiment/demo/model/`` and writes ``SOURCE.md`` from git's answers and the file's own
version: ``tests/test_kg_demo.py`` holds the copy to the note's digest and re-renders the
deck slide from it, which is the check that the drawing still holds.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vendor_register import MARK as _REGISTER_MARK, _sha, current_copy, describe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "kg_experiment" / "demo" / "model"
FILE = "model/model.json"
MARK = _REGISTER_MARK.replace("vendor_register", "vendor_legible_model")


def earlier_copies(note: str) -> list[tuple[str, str, str]]:
    """Earlier copies the note records: its own table rows, or the hand-written first note's
    version row and commit row read as one copy."""
    rows = re.findall(r"^\| `([^`|]*)` \| `([0-9a-f]{7,40})` \| (\d{4}-\d{2}-\d{2}) \|$", note, re.M)
    return [(v, c[:7], d) for v, c, d in rows]


def current(note: str) -> tuple[str, str, str]:
    """(version, commit, copied) of the note's current copy, from either note format."""
    ver = re.search(r"^\| version \| ([0-9][^,| ]*)", note, re.M)
    _, commit, copied = current_copy(note)
    return (ver.group(1) if ver else "", commit, copied)


def source_note(info: dict, version: str, dated: str, digest: str, copied: str, earlier: list[tuple[str, str, str]]) -> str:
    tag_cell = f" | tag | `{info['tag']}` |\n" if info["tag"] else ""
    lines = [
        f"# Vendored copy of the Legible systemic impact model, v{version}", "",
        "| | |", "|---|---|",
        f"| source repository | `{info['repo'] or 'fdurieux/fdurieux.github.io'}` |",
        f"| file | `{FILE}` (generated there from `model/model-data.py`; never edited by hand) |",
        f"| version | {version}, dated {dated} (`\"version\": \"{version}\"` in the file) |",
        f"| commit | `{info['commit']}` — \"{info['subject']}\", {info['date']} |",
    ]
    if tag_cell:
        lines.append(tag_cell.strip())
    lines += [
        f"| sha256 of `model.json` | `{digest}` |",
        f"| copied | {copied}, byte for byte, {MARK} from a clean checkout at that commit |",
        "",
        "The demo's systemic-model view draws the model's reduced knowledge view",
        "(five knowledge nodes, nine edges, four practices P9–P12) with the",
        "layout of `recreate_experiment/knowledge-transfer/deck/tools/gen_cascade_slide.py`,",
        "which reads this JSON for the edges' polarity and evidence class. The",
        "copy is not fetched at build time: the image carries it. To refresh it,",
        "check the source repository out at the commit you want and run",
        "`python tools/vendor_legible_model.py <checkout>`, which rewrites this file;",
        "`tests/test_kg_demo.py` holds the copy to the digest above and re-renders",
        "the deck slide from it.",
    ]
    if earlier:
        lines += ["", "## Earlier copies", "", "| version | commit | copied |", "|---|---|---|"]
        lines += [f"| `{v}` | `{c}` | {d} |" for v, c, d in earlier]
    return "\n".join(lines) + "\n"


def vendor(checkout: Path, dest: Path = DEST, *, copied: str | None = None, dry_run: bool = False, out=print) -> dict:
    info = describe(checkout, allow_untagged=True, paths=(FILE,))
    src = checkout / FILE
    model = json.loads(src.read_text(encoding="utf-8"))
    version = str(model.get("version", ""))
    if not version:
        raise SystemExit(f"{src} carries no \"version\" field")
    dated = str(model.get("date") or model.get("dated") or info["date"])
    digest = _sha(src)
    old_note = (dest / "SOURCE.md").read_text(encoding="utf-8") if (dest / "SOURCE.md").exists() else ""
    old_digest = _sha(dest / "model.json") if (dest / "model.json").exists() else ""
    changed = old_digest != digest
    copied = copied or dt.date.today().isoformat()
    earlier = earlier_copies(old_note)
    cur = current(old_note)
    if cur[1] and cur[1] != info["commit"][:7] and cur[1] not in {c for _, c, _ in earlier}:
        earlier.insert(0, cur)
    note = source_note(info, version, dated, digest, copied, earlier)
    out(f"{info['repo'] or checkout} at {info['tag'] or 'no tag'} ({info['commit'][:7]}, {info['date']}): model v{version}, "
        f"{len(model.get('nodes', []))} nodes, {len(model.get('edges', []))} edges; model.json {'changed' if changed else 'unchanged'}")
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest / "model.json")
        (dest / "SOURCE.md").write_text(note, encoding="utf-8", newline="\n")
        out(f"wrote {dest / 'SOURCE.md'}")
    return {**info, "version": version, "dated": dated, "digest": digest, "changed": changed, "note": note}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("checkout", type=Path, help="a clean checkout of fdurieux/fdurieux.github.io at the commit to vendor")
    ap.add_argument("--dest", type=Path, default=DEST, help=f"where the copy lives (default {DEST.relative_to(ROOT).as_posix()})")
    ap.add_argument("--date", help="the 'copied' date to record (default today)")
    ap.add_argument("--dry-run", action="store_true", help="report what would change and write nothing")
    a = ap.parse_args(argv)
    vendor(a.checkout.resolve(), a.dest.resolve(), copied=a.date, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
