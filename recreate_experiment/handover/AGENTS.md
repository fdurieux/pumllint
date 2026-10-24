# Brief for an AI coding agent

You are building a program from its specification. Everything you need is
in the kit at `../kit/` and in this folder; nothing else describes the
program in a way the acceptance suite checks. Read `../kit/README.md`,
then this folder's `README.md`, `ARCHITECTURE.md` and `KNOWN-QUIRKS.md`,
then every file under `../kit/` in full, before writing code. This brief
is the one that three independent agents built the program from, each
matching the reference implementation cell for cell; it is kept close to
that wording.

## Build, under your output directory

- A Python package `jef` (version 0.6.0) providing the console script
  `jef-data` with exactly the command-line surface `../kit/contracts/cli.md`
  and `cli_help.md` describe: every subcommand, flag, default, message and
  exit code. Python ≥ 3.11, exactly the dependency pins in
  `../kit/contracts/pins.md`, no other runtime dependency; a `pyproject.toml`
  so `pip install -e .` installs it; `universe.toml` and
  `classifications.toml` shipped as package data.
- `deploy/daily.sh`: the chain script of `../kit/contracts/chain.md`. It
  sources `events.sh` and `dashboard.sh` from its own directory; those two
  are given externals you do not write (the suite places stubs beside your
  script).
- `jdl_adapter.py`: the harness adapter, implementing every function of
  `../kit/contracts/HARNESS_INTERFACE.md` against your package. Glue only.
- `ASSUMPTIONS.md`: every point where the kit was silent, ambiguous or
  contradictory, what you chose and why; one entry each, written as you go,
  never resolved silently. This file is a deliverable.

## Working rules

- Read only the kit and your output directory. Do not search for other
  copies, documentation or tests of this program, and do not use the
  network: a gap in the kit is an assumption to record, not a thing to look
  up.
- Run the acceptance suite against your build as often as you like, fixing
  what it shows between runs: from `../kit/`,
  `JDL_UNDER_TEST=jef-data JDL_CHAIN=<your deploy/daily.sh> JDL_ADAPTER=jdl_adapter python -m pytest -q features/steps`
  with your output directory on `PYTHONPATH` and your package installed in
  the active environment (`../kit/features/README.md` has the details).
  Done is 257 passed, 0 failed, 0 skipped.
- Exactness over elegance: where the kit gives a message string, reproduce
  it byte for byte; where it gives arithmetic, implement that arithmetic,
  not an equivalent you prefer. The build is judged on numbers, verdicts,
  messages and exit codes, not on design.
- The behaviours in `KNOWN-QUIRKS.md` are the contract. Do not repair them.
- Keep code comments to what the code does; do not cite the kit's documents
  in them.
- Use `DECISIONS.md` as the checklist for every branch you write: each row
  is one case the suite exercises.

## Report back with

The module layout you chose, the final suite result, the count of entries
in `ASSUMPTIONS.md`, and the five hardest judgement calls in one line each.
Do not paste file contents.
