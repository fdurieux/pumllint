"""Build the clean-room subject tree OpenWiki documents, from a J-F checkout.

    python make_clean_room.py <jf-repo> <commit> <out-dir>

The tree is the one the kit's reverse engineer saw (PREREGISTRATION.md,
Phase 0): ``src/jef/data/`` and ``deploy/daily.sh`` from J-F at the given
commit, the two scripts daily.sh sources (``deploy/events.sh``,
``deploy/dashboard.sh``) copied verbatim and marked as given externals in
``deploy/EXTERNALS.md``, and a reduced ``pyproject.toml`` carrying only the
name, the Python floor, the exact runtime pins and the ``jef-data`` console
script. No ``docs/``, ``tests/``, README, ROADMAP, CLAUDE.md or other
package. The tree is then made a git repository with one commit, because
OpenWiki resolves evidence from a git top level and needs a HEAD.

Prints the sha256 over the sorted list of (path, sha256) pairs of every
file in the tree, which is the subject hash the pre-registration records.
Reads the J-F checkout with ``git archive`` so the working tree's branch
does not matter. Stdlib only.
"""
from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

KEEP_PREFIXES = ("src/jef/data/", "deploy/daily.sh")
EXTERNALS = ("deploy/events.sh", "deploy/dashboard.sh")
EXTERNALS_NOTE = """# Given externals

`events.sh` and `dashboard.sh` are sourced by `daily.sh` and are **not part
of the subject**: they are given, verbatim, so the chain can be read. They
belong to the venue's telemetry and publishing legs, which are out of scope.
"""


def archive(repo: Path, commit: str) -> tarfile.TarFile:
    data = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit],
                          check=True, capture_output=True).stdout
    return tarfile.open(fileobj=io.BytesIO(data))


def reduced_pyproject(full: str) -> str:
    doc = tomllib.loads(full)
    proj = doc["project"]
    deps = "\n".join(f'    "{d}",' for d in proj["dependencies"])
    scripts = proj.get("scripts", {})
    script = scripts.get("jef-data")
    if not script:
        sys.exit("pyproject has no jef-data console script")
    return (
        "[build-system]\n"
        'requires = ["setuptools>=68"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[project]\n"
        f'name = "{proj["name"]}"\n'
        f'version = "{proj["version"]}"\n'
        f'requires-python = "{proj["requires-python"]}"\n'
        f"dependencies = [\n{deps}\n]\n\n"
        "[project.scripts]\n"
        f'jef-data = "{script}"\n\n'
        "[tool.setuptools.packages.find]\n"
        'where = ["src"]\n'
        'include = ["jef.data*"]\n'
    )


def main() -> int:
    repo, commit, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)
    pyproject = None
    with archive(repo, commit) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name
            if name == "pyproject.toml":
                pyproject = tar.extractfile(member).read().decode("utf-8")
                continue
            if name.startswith(KEEP_PREFIXES) or name in EXTERNALS:
                target = out / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
                target.chmod(member.mode & 0o777 | 0o200)
    if pyproject is None:
        sys.exit("no pyproject.toml at that commit")
    (out / "pyproject.toml").write_text(reduced_pyproject(pyproject), encoding="utf-8")
    (out / "deploy" / "EXTERNALS.md").write_text(EXTERNALS_NOTE, encoding="utf-8")

    rows = []
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        rows.append(f"{path.relative_to(out).as_posix()} {hashlib.sha256(path.read_bytes()).hexdigest()}")
    tree_hash = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    (out / ".subject.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")

    env = {"GIT_AUTHOR_NAME": "clean-room", "GIT_AUTHOR_EMAIL": "clean-room@invalid",
           "GIT_COMMITTER_NAME": "clean-room", "GIT_COMMITTER_EMAIL": "clean-room@invalid",
           "GIT_CONFIG_GLOBAL": "/dev/null", "HOME": str(out)}
    for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                ["git", "commit", "-q", "-m", f"clean-room subject from J-F {commit}"]):
        subprocess.run(cmd, cwd=out, check=True, env=env)
    print(f"files {len(rows)}; subject tree sha256 {tree_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
