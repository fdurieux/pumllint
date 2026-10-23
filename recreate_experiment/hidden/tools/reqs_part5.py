# Requirements, part 5: closing round (revision 2026-10-23). Appended after
# every earlier requirement so no existing id moves.
CLI = "src/jef/data/cli.py"

R5 = [
("cli-export-empty", "refusal",
 "If `export` is asked for a series the store does not hold (no year file under its exchange tag and symbol), then the command shall apply the export projection to the zero-row read-back frame without any guard and terminate with an unhandled traceback whose last stderr line is pandas' own `AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?` (the zero-row frame's `datetime` column is not datetimelike), with exit code 1, nothing on stdout and the output file not written - it is not a StoreError refusal.",
 "logic", None, (CLI, "cmd_export; store.load (empty branch); store.to_contract_frame", "202-211")),
("cli-parser-surface", "cli",
 "The command line shall be declared as: a top-level parser with prog `jef-data`, the CLI module docstring as description (quoted in contracts/cli.md), the default help formatter, no epilog and the default `-h, --help`; one subparsers group with dest `command`, required, without metavar, title or help, so usage and help list the subcommand choices in braces; the ten subcommands added in the order validate, sync-actions, load, adjust, import-csv, export, differential, sync, status, universe, each created with its help string and no description; and every option with the option strings, dest, metavar, action, type, default, choices and help string of the contracts/cli.md \"Parser surface\" tables (the metavar is the upper-cased dest except `--summary-json`, whose metavar is `PATH`; choice options print `{crypto,etf,stock}`).",
 "logic", None, (CLI, "main", "378-573")),
("cli-parser-errors", "cli",
 "When the command line cannot be parsed, the program shall print on stderr `usage: ` plus the formatted usage of the parser that failed (wrapped at the terminal width), then the line `{prog}: error: {message}` with prog `jef-data` or `jef-data <subcommand>`, print nothing on stdout and exit 2; arguments no parser recognises are reported by the top-level parser (top-level usage and `jef-data: error: unrecognized arguments: {arguments}`) even after a valid subcommand, and a missing subcommand reads `jef-data: error: the following arguments are required: command`.",
 "logic", None, (CLI, "main (argparse parse_args)", "378-380,572-573")),
("cli-help", "cli",
 "When `--help` or `-h` is given to the top-level parser or to any of the ten subcommands, the program shall print on stdout exactly the corresponding block of contracts/cli_help.md (captured with an 80-column terminal: `COLUMNS=80`, or no terminal and `COLUMNS` unset), print nothing on stderr and exit 0.",
 "logic", None, (CLI, "main (argparse help actions)", "378-573")),
]
