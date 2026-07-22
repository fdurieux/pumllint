"""Harvest real-world .puml files from public GitHub repos (Phase 10a, wild tier).

Uses the `gh` CLI (GitHub code search) to find public PlantUML sequence
diagrams, downloads up to --limit of them into corpus/wild/, and records
provenance (repo, path, URL, license) in corpus/wild/sources.json so every
harvested file is attributable.

Network- and auth-dependent by design; NOT exercised by the test suite.
Requires an authenticated `gh` (run `gh auth login` first).

Run:  python tools/harvest_corpus.py [--limit N] [dest]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _gh(*args: str) -> str:
    try:
        proc = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=60, check=False
        )
    except subprocess.TimeoutExpired:
        # Normalize to the error type the harvest loop already skips on, so
        # one slow download doesn't abort the whole run.
        raise RuntimeError(f"gh {' '.join(args[:2])}... timed out") from None
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}... failed: {proc.stderr.strip()}")
    return proc.stdout


def harvest(dest: Path, limit: int = 15) -> list[dict]:
    wild_dir = dest / "wild"
    wild_dir.mkdir(parents=True, exist_ok=True)

    raw = _gh(
        "search", "code", "@startuml", "--extension", "puml",
        "--limit", str(limit * 2),  # over-fetch; some hits won't download
        "--json", "repository,path,url",
    )
    hits = json.loads(raw)

    sources: list[dict] = []
    licenses: dict[str, str] = {}
    for hit in hits:
        if len(sources) >= limit:
            break
        repo = hit["repository"]["nameWithOwner"]
        path = hit["path"]
        try:
            content = _gh(
                "api", f"repos/{repo}/contents/{path}",
                "-H", "Accept: application/vnd.github.raw+json",
            )
        except RuntimeError as e:
            print(f"  skip {repo}/{path}: {e}", file=sys.stderr)
            continue
        if "@startuml" not in content:
            continue
        if repo not in licenses:
            try:
                spdx = _gh("api", f"repos/{repo}", "--jq", ".license.spdx_id").strip()
            except RuntimeError:
                spdx = "UNKNOWN"
            licenses[repo] = spdx or "UNKNOWN"

        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{repo}__{Path(path).name}")
        (wild_dir / safe).write_text(content, encoding="utf-8")
        sources.append({
            "file": f"wild/{safe}",
            "repo": repo,
            "path": path,
            "url": hit["url"],
            "license": licenses[repo],
        })
        print(f"  harvested {repo}/{path} [{licenses[repo]}]")

    (wild_dir / "sources.json").write_text(
        json.dumps(sources, indent=2) + "\n", encoding="utf-8"
    )
    return sources


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Harvest public .puml files via gh code search")
    ap.add_argument("dest", nargs="?", type=Path, default=REPO_ROOT / "corpus")
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args(argv)
    dest, limit = args.dest, args.limit

    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=30, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print(
            "error: the `gh` CLI is missing or unauthenticated — run `gh auth login` "
            "first (the wild harvest needs GitHub code search).",
            file=sys.stderr,
        )
        return 2

    sources = harvest(dest, limit=limit)
    print(f"Harvested {len(sources)} wild diagrams to {dest / 'wild'} "
          f"(provenance in sources.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
