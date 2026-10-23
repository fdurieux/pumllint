# Changes to the kit

## Revision 2026-10-23 (closing round)

Three additive revisions; no existing requirement's id or text changed, no
existing scenario changed.

| addition | where |
|---|---|
| JDL-159 (refusal): `export` of a series the store does not hold ends in pandas' unwrapped `AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?`, exit 1, no file | requirements.json; refusals.md row X-09; cli.md `export` note; scenario "Exporting a series the store does not hold ends in pandas' own AttributeError" (cli.feature) |
| JDL-160 (cli): the exact argparse declaration - prog, description, subparsers dest `command` without metavar, subcommand order and help strings, every option's dest, metavar, action, type, default, choices and help | requirements.json; cli.md section "Parser surface" |
| JDL-161 (cli): the exact usage + `{prog}: error: {message}` form of parse errors, exit 2, unrecognised arguments reported by the top-level parser | requirements.json; cli.md "Parser errors"; refusals.md row X-10; scenario outline "Parser errors print the failing parser's usage and one error line" (cli.feature) |
| JDL-162 (cli): `--help` of the top level and of every subcommand prints the verbatim text, exits 0 | requirements.json; new contracts/cli_help.md; scenario outline "Every --help prints its verbatim text and exits 0" (cli.feature) |
| pins note on argparse/pandas/CPython output and the 80-column terminal | pins.md |
| diagram realisation of the four new requirements | uml/component.puml (note on the cli component and footer) |
