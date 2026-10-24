# Specification kit: `jef.data` / `jef-data` and its daily chain

Rebuild the program from this kit so that every stored number, every verdict
and every exit code matches. Reading order:

1. `requirements.json` — 163 atomic requirements (`JDL-001` …), kinds
   contract, arithmetic, ritual, verdict, refusal, cli, chain; each numeric
   constant lives in exactly one requirement.
2. `contracts/` — one file per contract:
   `universe.toml.md` (+ the packaged `universe.toml`), `classifications.toml.md`
   (+ the packaged `classifications.toml`), `collectors.md`, `fixtures.md`,
   `adjustment.md`, `store.md`, `seam_frame.md`, `leg.md`, `cli.md`,
   `refusals.md`, `chain.md`, `pins.md`, the two JSON Schemas with examples,
   `cli_help.md` (every `--help` output verbatim; revision 2026-10-23, closing
   round) and `HARNESS_INTERFACE.md` (the adapter your rebuild must ship).
5. `CHANGES.md` — revisions made after the first issue of the kit.
3. `uml/` — eight PlantUML diagrams; each footer names the requirements it
   realises. Gates (run from this directory):
   `pumllint uml --fail-on info -c pumllint.toml`,
   `pumllint score uml --min-level 5 -c pumllint.toml`,
   `pumllint trace uml --requirements requirements.json --features features --fail-on-uncovered --fail-on-unverified -c pumllint.toml`.
4. `features/` — the executable scenarios (see `features/README.md`).

## Precedence when two of the kit's documents disagree (revision 2026-10-24)

The kit is written so that its documents agree. If they do not, this is
the order; build the higher one and report the disagreement (in your
`ASSUMPTIONS.md`, and to the kit's owner as a defect to fix):

1. **The acceptance suite** — the expectations in `features/*.feature` and
   `features/fixtures/expected/`, which were recorded from the original
   program and verified on it. What a scenario expects is what the program
   does.
2. **`requirements.json`** — the normative statements. A requirement wins
   over any prose that elaborates it.
3. **`contracts/*.md`, the JSON Schemas and the packaged TOML files** — the
   elaboration: exact strings, arithmetic, layouts, grammars.
4. **`contracts/dmn/` and `contracts/glossary.md`** — derived from 2 and 3;
   a table or a definition never overrides the text it summarises.
5. **`uml/`** — structure, names, sequencing and layout; a diagram never
   decides a message string, a number or an exit code.

Generated views outside the kit (`../handover/REQUIREMENTS.md`,
`DECISIONS.md`, `TRACE.md`) are below all five: they are built from the
kit and carry nothing of their own.

## Verifying the copy you hold

`MANIFEST.sha256` lists every file of the kit with its SHA-256; `python
tools/manifest.py --check` (or `sha256sum -c MANIFEST.sha256` on POSIX)
verifies the copy byte for byte. A checkout that rewrote line endings, or
a transfer that appended a newline, fails the check: the recorded fixtures
are compared byte for byte by the suite, so a kit that fails the check
cannot pass it. `python tools/manifest.py` rewrites the manifest after a
revision.

`events.sh` and `dashboard.sh`, which the chain sources, are given
externals, shipped verbatim in `contracts/externals/` (revision 2026-10-24):
copy them unchanged beside your `daily.sh`; the chain scenarios copy them
from there. The packaged `universe.toml` names two Yahoo CSV snapshots
(`experiments/AAPL.csv`, `experiments/BTC-USD_feb2024.csv`) that are not in
the kit: they are deployment inputs the program's own package does not
carry either, so a full `sync` of the packaged universe needs them present
at the paths declared, while every scenario and `--dry-run` works without.
