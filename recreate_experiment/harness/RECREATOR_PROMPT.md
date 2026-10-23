# The recreator's brief (verbatim, recorded for provenance)

Sent to a fresh `general-purpose` agent, model Opus 5, effort xhigh, once per
arm. `{KIT}` is the arm's kit copy, `{VENV}` its Python environment,
`{OUT}` its output directory. Nothing else is in the prompt.

---

You are rebuilding a program from its specification. You have never seen the
program and you will not: everything you know about it is in the kit at
`{KIT}`. Read `{KIT}/README.md` first if it exists, then everything else, in
full, before writing code. The kit holds: `requirements.json` (atomic
requirements with ids), `contracts/` (data shapes, arithmetic, store layout,
CLI, refusals, the chain, dependency pins, and `HARNESS_INTERFACE.md`),
`features/` (Gherkin scenarios with their step definitions and fixtures — the
acceptance suite you may run), and, when present, `uml/` (PlantUML diagrams).

Build, under `{OUT}/`:
- a Python package `jef_data_rc` providing the console script `jef-data-rc`
  with exactly the command-line surface the contracts describe (every
  subcommand, flag, default, message and exit code), on Python ≥ 3.11, with
  exactly the dependency pins the kit states and no other runtime dependency;
  a `pyproject.toml` so `pip install -e {OUT}` installs it (the console script
  name is `jef-data-rc`; the package name is `jef_data_rc`; choose the module
  layout the kit's architecture describes where it describes one);
- `daily-rc.sh`: the chain script, which sources `events.sh` and
  `dashboard.sh` from its own directory as the chain contract says (those two
  are given externals you do not write; the harness places them beside your
  script), and invokes the data command by the name the contract says;
- `adapter_rc.py`: the harness adapter, implementing every function of
  `contracts/HARNESS_INTERFACE.md` against your package;
- `ASSUMPTIONS.md`: every point where the kit was silent, ambiguous or
  contradictory, what you chose and why — one entry each, as you go, never
  resolved silently; this file is a measured output;
- `READ.log`: the path of every file you read, one per line, appended as you
  go; also a measured output.

Working rules:
- Environment: `. {VENV}/bin/activate`. Install your package there
  (`pip install -e {OUT}`), nothing else beyond what the pins allow.
- Read only under `{KIT}` and `{OUT}`. Do not search the file system, do not
  look for other copies, documentation or tests of this program anywhere, do
  not use the network. If something is missing from the kit, that is an
  assumption to record, not a thing to look up.
- You may run the kit's acceptance suite against your build at most THREE
  times (`JDL_UNDER_TEST=jef-data-rc JDL_CHAIN={OUT}/daily-rc.sh
  JDL_ADAPTER=adapter_rc`, with `{OUT}` on `PYTHONPATH`; the suite's README
  says how). Record each run's pass count in `{OUT}/RUNS.md`. Fix what the
  suite shows between runs. After the third run, stop iterating whatever the
  result.
- Exactness over elegance: the rebuild is judged on whether its numbers,
  verdicts, messages and exit codes equal the original's, cell for cell.
  Where the kit gives a message string, reproduce it byte for byte. Where it
  gives arithmetic, implement that arithmetic, not an equivalent you prefer.
- Keep code comments to what the code does; do not cite the kit's documents
  in them.

Report back with: the module layout you chose, the three suite results, the
count of assumptions, the five hardest judgement calls in one line each. Do
not paste file contents.
