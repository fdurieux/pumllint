"""Write or verify the kit's file manifest (stdlib only).

    python tools/manifest.py            # rewrite MANIFEST.sha256 from the kit's files
    python tools/manifest.py --check    # verify every file; exit 1 on any difference

The manifest lists every file under the kit directory except itself, one
line per file in `sha256sum` format (`<hex>  <path>`, paths relative to the
kit root with forward slashes, sorted), so POSIX `sha256sum -c
MANIFEST.sha256` verifies it too. Hashes are of the exact bytes: a checkout
that rewrote line endings, or a transport that appended a newline, fails
the check, which is the point. Caches (`__pycache__`, `.pytest_cache`) are
ignored.
"""
import hashlib
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
MANIFEST = KIT / "MANIFEST.sha256"
IGNORE = {"__pycache__", ".pytest_cache"}


def entries():
    out = []
    for p in sorted(KIT.rglob("*")):
        if not p.is_file() or p == MANIFEST or IGNORE & set(p.parts) or p.suffix == ".pyc":
            continue
        out.append((hashlib.sha256(p.read_bytes()).hexdigest(), p.relative_to(KIT).as_posix()))
    return sorted(out, key=lambda e: e[1])


def main(argv):
    current = entries()
    text = "".join(f"{h}  {path}\n" for h, path in current)
    if "--check" not in argv:
        MANIFEST.write_text(text, encoding="utf-8")
        print(f"wrote {MANIFEST.name}: {len(current)} files")
        return 0
    if not MANIFEST.exists():
        print("no manifest"); return 1
    recorded = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        h, _, path = line.partition("  ")
        recorded[path] = h
    now = dict((path, h) for h, path in current)
    missing = sorted(set(recorded) - set(now))
    extra = sorted(set(now) - set(recorded))
    changed = sorted(p for p in recorded if p in now and now[p] != recorded[p])
    for label, items in (("missing", missing), ("not in manifest", extra), ("changed", changed)):
        for p in items:
            print(f"{label}: {p}")
    ok = not (missing or extra or changed)
    print(f"{'OK' if ok else 'FAIL'}: {len(recorded)} files in manifest, {len(now)} present")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
