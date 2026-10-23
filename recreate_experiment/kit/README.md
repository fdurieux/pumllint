# Specification kit: `jef.data` / `jef-data` and its daily chain

Rebuild the program from this kit so that every stored number, every verdict
and every exit code matches. Reading order:

1. `requirements.json` — 162 atomic requirements (`JDL-001` …), kinds
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

`events.sh` and `dashboard.sh`, which the chain sources, are given
externals: copy them unchanged beside your `daily.sh`.
