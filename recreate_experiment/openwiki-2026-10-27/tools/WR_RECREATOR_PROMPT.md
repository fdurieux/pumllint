# The W-R recreator's brief (verbatim, recorded for provenance)

`../../harness/RECREATOR_PROMPT.md` with the two changes §2 (Arm W-R) of
`../PREREGISTRATION.md` names: the kit paragraph replaced by a wiki
paragraph, and the three permitted acceptance-suite runs removed (the wiki
ships no suite). Every other line is the recorded brief's. Sent to a fresh
`general-purpose` agent, once per wiki. `{WIKI}` is the arm's wiki copy
(`openwiki/`, `AGENTS.md`, and `HARNESS_INTERFACE.md`), `{VENV}` its Python
environment, `{OUT}` its output directory. Nothing else is in the prompt.

---

You are rebuilding a program from its documentation. You have never seen the
program and you will not: everything you know about it is in the wiki at
`{WIKI}`. Read `{WIKI}/AGENTS.md` and `{WIKI}/openwiki/` first, starting from
the wiki's index page, then everything else, in full, before writing code.
The wiki holds Markdown pages describing the program, each with Grounded
Claims (atomic statements citing source lines by path and line range, which
you cannot open), the `.claims/` sidecars that record those claims, and a
page manifest. `{WIKI}/HARNESS_INTERFACE.md` is the interface the comparison
harness drives your build through. There is no acceptance suite.

Build, under `{OUT}/`:
- a Python package `jef_data_rc` providing the console script `jef-data-rc`
  with exactly the command-line surface the wiki describes (every
  subcommand, flag, default, message and exit code), on Python ≥ 3.11, with
  exactly the dependency pins the wiki states and no other runtime dependency;
  a `pyproject.toml` so `pip install -e {OUT}` installs it (the console script
  name is `jef-data-rc`; the package name is `jef_data_rc`; choose the module
  layout the wiki's architecture describes where it describes one);
- `daily-rc.sh`: the chain script, which sources `events.sh` and
  `dashboard.sh` from its own directory as the wiki says (those two
  are given externals you do not write; they are already beside your
  script in `{OUT}`), and invokes the data command by the name the wiki says;
- `adapter_rc.py`: the harness adapter, implementing every function of
  `HARNESS_INTERFACE.md` against your package;
- `ASSUMPTIONS.md`: every point where the wiki was silent, ambiguous or
  contradictory, what you chose and why — one entry each, as you go, never
  resolved silently; this file is a measured output;
- `READ.log`: the path of every file you read, one per line, appended as you
  go; also a measured output.

Working rules:
- Environment: `. {VENV}/bin/activate`. Install your package there
  (`pip install -e {OUT}`), nothing else beyond what the pins allow.
- Read only under `{WIKI}` and `{OUT}`. Do not search the file system, do not
  look for other copies, documentation or tests of this program anywhere, do
  not use the network. If something is missing from the wiki, that is an
  assumption to record, not a thing to look up.
- Exactness over elegance: the rebuild is judged on whether its numbers,
  verdicts, messages and exit codes equal the original's, cell for cell.
  Where the wiki gives a message string, reproduce it byte for byte. Where it
  gives arithmetic, implement that arithmetic, not an equivalent you prefer.
- Keep code comments to what the code does; do not cite the wiki's pages
  in them.

Report back with: the module layout you chose, the count of assumptions, the
five hardest judgement calls in one line each. Do not paste file contents.
