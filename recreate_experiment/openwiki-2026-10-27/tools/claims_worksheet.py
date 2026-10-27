"""Claims worksheet: every OpenWiki Grounded Claim, flattened, plus a seeded sample.

OpenWiki keeps one JSON sidecar per page under ``openwiki/.claims/``, each
with a ``claims`` array of ``{id, statement, evidence: [{resource, version}]}``
(OpenWiki 0.7.x, ``openwiki/concepts/grounded-claims.md`` in its own repo).
This tool reads a generated wiki, writes ``claims.all.json`` (every claim with
its page and evidence resources, versions dropped), ``claims.sample.json``
(a seeded sample of SAMPLE_SIZE claims, or all when fewer) and a Markdown
worksheet with one row per sampled claim and an empty verdict column for the
grader. It makes no judgement: the verdicts are human work, recorded in the
worksheet and summarised by ``claims_tally.py``.

    python claims_worksheet.py <wiki-dir> <out-dir> [--seed 20261027] [--size 150]

Stdlib only. Run with ``python -I`` on an untrusted wiki.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SEED = 20261027
SAMPLE_SIZE = 150
VERDICTS = ("TRUE", "FALSE", "PARTIAL", "UNVERIFIABLE")


def load_claims(wiki: Path) -> list[dict]:
    root = wiki / ".claims"
    if not root.is_dir():
        sys.exit(f"no claims sidecars under {root}")
    out: list[dict] = []
    for sidecar in sorted(root.rglob("*.json")):
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            sys.exit(f"{sidecar}: {exc}")
        page = sidecar.relative_to(root).with_suffix(".md").as_posix()
        for claim in data.get("claims", []):
            resources = [e.get("resource", "") for e in claim.get("evidence", [])]
            out.append({
                "id": claim.get("id", ""),
                "page": page,
                "statement": claim.get("statement", ""),
                "evidence": resources,
            })
    return out


def sample(claims: list[dict], seed: int, size: int) -> list[dict]:
    if len(claims) <= size:
        return list(claims)
    rng = random.Random(seed)
    picked = sorted(rng.sample(range(len(claims)), size))
    return [claims[i] for i in picked]


def worksheet(rows: list[dict]) -> str:
    lines = [
        "# Claims worksheet",
        "",
        "One row per sampled claim. Fill `verdict` with one of "
        + ", ".join(VERDICTS)
        + " and `note` with the symbol read; never edit `statement`.",
        "",
        "| n | id | page | statement | evidence | verdict | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for n, c in enumerate(rows, 1):
        statement = c["statement"].replace("|", "\\|").replace("\n", " ")
        evidence = "<br>".join(e.replace("|", "\\|") for e in c["evidence"])
        lines.append(f"| {n} | `{c['id']}` | `{c['page']}` | {statement} | {evidence} |  |  |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("wiki", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--size", type=int, default=SAMPLE_SIZE)
    args = ap.parse_args()
    claims = load_claims(args.wiki)
    picked = sample(claims, args.seed, args.size)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "claims.all.json").write_text(
        json.dumps(claims, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "claims.sample.json").write_text(
        json.dumps(picked, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "claims.worksheet.md").write_text(worksheet(picked), encoding="utf-8")
    pages = {c["page"] for c in claims}
    with_evidence = sum(1 for c in claims if c["evidence"])
    print(f"claims {len(claims)} on {len(pages)} pages; "
          f"{with_evidence} with evidence; sampled {len(picked)} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
