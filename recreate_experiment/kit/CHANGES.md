# Changes to the kit

## Revision 2026-10-23 (closing round)

Four requirement additions, one contract file, one pins note and one diagram note, all additive; no existing requirement's id or text changed, no
existing scenario changed.

| addition | where |
|---|---|
| JDL-159 (refusal): `export` of a series the store does not hold ends in pandas' unwrapped `AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?`, exit 1, no file | requirements.json; refusals.md row X-09; cli.md `export` note; scenario "Exporting a series the store does not hold ends in pandas' own AttributeError" (cli.feature) |
| JDL-160 (cli): the exact argparse declaration - prog, description, subparsers dest `command` without metavar, subcommand order and help strings, every option's dest, metavar, action, type, default, choices and help | requirements.json; cli.md section "Parser surface" |
| JDL-161 (cli): the exact usage + `{prog}: error: {message}` form of parse errors, exit 2, unrecognised arguments reported by the top-level parser | requirements.json; cli.md "Parser errors"; refusals.md row X-10; scenario outline "Parser errors print the failing parser's usage and one error line" (cli.feature) |
| JDL-162 (cli): `--help` of the top level and of every subcommand prints the verbatim text, exits 0 | requirements.json; new contracts/cli_help.md; scenario outline "Every --help prints its verbatim text and exits 0" (cli.feature) |
| pins note on argparse/pandas/CPython output and the 80-column terminal | pins.md |
| diagram realisation of the four new requirements | uml/component.puml (note on the cli component and footer) |

## Revision 2026-10-23 (wave 2)

Additive; no existing requirement's id or text changed, no existing
scenario changed. Recorded here on 2026-10-24: this section was missing
when the fourth rebuild read the kit (its finding F-006).

| addition | where |
|---|---|
| JDL-163 (refusal): `differential` on a stored side the store does not hold ends in the traceback of JDL-159 | requirements.json; refusals.md row X-11 (numbered X-10 until 2026-10-24); cli.md `differential`; uml/component.puml; decisions.feature "The store commands on an absent series" |
| DMN 1.3 decision tables, 13 tables in 6 files | contracts/dmn/ (built by harness/dmn_build.py, checked by harness/dmn_check.py) |
| `decisions.feature`: one `Rule:` block per table, Examples rows keyed to DMN rule ids | features/decisions.feature; fixture features/fixtures/csv/zero_close_jump.csv |
| glossary | contracts/glossary.md (checked by harness/glossary_check.py) |

## Revision 2026-10-24 (after the fourth rebuild)

Corrections from the fourth, independent rebuild's input review
(`recreate_experiment/rebuilds/codex-2026-10-24/INPUT-QUALITY.md`,
findings F-001 … F-010). One requirement's text changed (JDL-023, the
transport's return shape; its id and its scenarios are unchanged); no
scenario's expectation changed; one Examples row added.

| finding | correction |
|---|---|
| F-001 README counted 162 requirements | 163 |
| F-003 `events.sh` and `dashboard.sh` named as given externals and not carried | shipped verbatim in contracts/externals/; chain.md, features/README.md and the handover say where they go |
| F-004 two rows numbered X-10 in refusals.md | the differential row is X-11 |
| F-005 actions_gate.dmn's stamp domain had no later-than-today value | `today` → `today_or_later`; one Examples row (stamp 2024-02-14, run 2024-02-13) |
| F-006 this file: the closing-round heading said three additions; wave 2 absent | counted; the wave-2 section above |
| F-007 the packaged universe names two CSV snapshots the kit does not carry | README names them as deployment inputs |
| F-008 collectors.md gave the transport a bare `(status, text)` tuple while the data model draws `TransportResponse` | the prose and JDL-023 now say the object (the original's shape) |
| F-009 the chain scenarios' call logger split a multi-line argument into several records | the stub escapes newlines in logged arguments; chain.md states the one-line `python3 -c` the original uses |
| F-010 cli.md's JSON escaping example showed `§` unchanged | `\u00a7` (and this row had the same slip until its own manifest commit) |

Two additions the rebuild's method asked for (`EVALUATION-METHOD.md`,
"Consistency and authority", "input manifest"), same revision:

| addition | where |
|---|---|
| a precedence rule for disagreements between the suite, the requirements, the contracts, the decision tables and glossary, and the diagrams | README.md "Precedence"; the handover README, AGENTS.md and DONE.md point at it |
| `MANIFEST.sha256`, every kit file with its SHA-256, and `tools/manifest.py` to write and verify it (`sha256sum -c` works too) | README.md "Verifying the copy you hold"; regenerate after every revision |
