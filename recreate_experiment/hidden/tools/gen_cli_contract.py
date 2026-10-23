"""Closing round: render the parser surface (into cli.md) and the verbatim
--help outputs (cli_help.md) from what was captured from the SUBJECT in
hidden/scratch/closing (surface.json = parser introspection, help_*.80.txt =
`COLUMNS=80 jef-data [<cmd>] --help`)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CAP = os.path.join(ROOT, "hidden", "scratch", "closing")
SRC = os.path.join(ROOT, "hidden", "kit_src", "contracts")
MARK = "revision 2026-10-23 (closing round)"
ORDER = ["validate", "sync-actions", "load", "adjust", "import-csv", "export",
         "differential", "sync", "status", "universe"]

surface = json.load(open(os.path.join(CAP, "surface.json")))


def code(text):
    if text is None:
        return "—"
    text = str(text)
    fence = "``" if "`" in text else "`"
    pad = " " if fence == "``" else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def shown_metavar(action):
    if action["action"] in ("_StoreTrueAction", "_HelpAction"):
        return "(none)"
    if action["metavar"]:
        return action["metavar"]
    if action["choices"]:
        return "{" + ",".join(action["choices"]) + "}"
    if not action["option_strings"]:
        return action["dest"]
    return action["dest"].upper()


def kind(action):
    return {"_StoreAction": "store", "_StoreTrueAction": "store_true",
            "_AppendAction": "append (repeatable)", "_HelpAction": "help"}.get(
        action["action"], action["action"])


def rendered_help(text):
    return None if text is None else text.replace("%%", "%")


lines = [f"<!-- {MARK}: generated section, do not edit by hand -->",
         "", f"## Parser surface ({MARK})", "",
         "Requirements {{cli-parser-surface}}, {{cli-parser-errors}}, {{cli-help}}. "
         "This section fixes the declaration of the parser so that `--help` "
         "(contracts/cli_help.md) and the usage line of a parser error are "
         "reproducible byte for byte with Python's `argparse` under the pins "
         "(CPython 3.12, default `HelpFormatter`, terminal width 80: "
         "`COLUMNS=80`, or no terminal and `COLUMNS` unset).", "",
         "### Top-level parser", "",
         "| property | value |", "|---|---|",
         "| prog | `jef-data` (set explicitly, so it does not depend on how the program is launched) |",
         "| description | the CLI module's docstring, quoted below; the default formatter reflows it |",
         "| usage / epilog | not set (usage generated; no epilog) |",
         "| formatter | the default `HelpFormatter` |",
         "| `-h, --help` | the default help action |",
         "| subcommands | one subparsers group: dest `command`, required, **no metavar, no title, no help** "
         "(so usage and help list the choices in braces); subcommands added in the order "
         + ", ".join(f"`{n}`" for n in ORDER) + " |",
         "| subcommand parsers | created with a `help` string only: **no description**, no epilog; "
         "their prog is `jef-data <name>` |", "",
         "The description (verbatim, including its line breaks, which the formatter reflows):", "",
         "```text", surface["top"]["description"].rstrip("\n"), "```", "",
         "### Subcommand help strings (shown in the top-level `--help`)", "",
         "| subcommand | help |", "|---|---|"]
for dest, help_ in surface["subparsers"]["choices_help"]:
    lines.append(f"| `{dest}` | {code(help_)} |")
lines += ["", "### Options of each subcommand", "",
          "Metavar as printed: the upper-cased dest unless the table names one; an option with "
          "choices prints its choices in braces. `help` is shown after argparse's `%` "
          "interpolation (a literal `%` is written `%%` in an argparse help string, e.g. the "
          "`0.5%%` of `--spread-threshold`). Options appear in usage and help in table order.", ""]
for name in ORDER:
    sp = surface[name]
    lines += [f"#### `{name}` (prog `{sp['prog']}`)", "",
              "| option | dest | metavar shown | action | type | default | required | choices | help |",
              "|---|---|---|---|---|---|---|---|---|"]
    for a in sp["actions"]:
        opt = ", ".join(a["option_strings"]) if a["option_strings"] else "(positional)"
        default = a["default"]
        if a["action"] == "_HelpAction":
            default = "—"
        lines.append("| " + " | ".join([
            code(opt), code(a["dest"]), code(shown_metavar(a)), kind(a),
            code(a["type"]) if a["type"] else ("—" if a["action"] in ("_StoreTrueAction", "_HelpAction") else "str"),
            code(default) if default not in (None, "—") else ("None" if default is None else "—"),
            "yes" if a["required"] else "no",
            code(",".join(a["choices"])) if a["choices"] else "—",
            code(rendered_help(a["help"])) if a["help"] else "—"]) + " |")
    lines.append("")
lines += ["### Parser errors", "",
          "A parse failure prints, on stderr, `usage: ` followed by the failing parser's "
          "formatted usage (wrapped at the terminal width), then `{prog}: error: {message}`, "
          "and exits 2; stdout stays empty. Arguments no parser recognises are reported by the "
          "top-level parser even after a valid subcommand, so they print the TOP-LEVEL usage "
          "and `jef-data: error: unrecognized arguments: ...`. Examples (80 columns):", "",
          "```text",
          "$ jef-data",
          "usage: jef-data [-h]",
          "                {validate,sync-actions,load,adjust,import-csv,export,differential,sync,status,universe}",
          "                ...",
          "jef-data: error: the following arguments are required: command",
          "",
          "$ jef-data export --symbol X",
          "usage: jef-data export [-h] --symbol SYMBOL [--exchange EXCHANGE] --output",
          "                       OUTPUT [--store STORE]",
          "jef-data export: error: the following arguments are required: --output",
          "```", "",
          f"<!-- end of the {MARK} generated section -->", ""]
section = "\n".join(lines)

cli_path = os.path.join(SRC, "cli.md")
text = open(cli_path, encoding="utf-8").read()
start = text.find(f"<!-- {MARK}: generated section")
if start != -1:
    text = text[:start].rstrip("\n") + "\n"
open(cli_path, "w", encoding="utf-8").write(text.rstrip("\n") + "\n\n" + section)

# cli_help.md
help_lines = [f"# `--help` output, verbatim ({MARK})", "",
              "Requirement {{cli-help}}. Each block is exactly what the subject prints on "
              "stdout for the command in its heading, captured with `COLUMNS=80` (identical to "
              "running with no terminal and `COLUMNS` unset); the command exits 0 and prints "
              "nothing on stderr. Every block ends with a newline that the fence hides. The "
              "help depends on the terminal width (argparse wraps at `COLUMNS` - 2), so the "
              "scenarios run with `COLUMNS=80`. The parser declaration that produces these "
              "texts is cli.md \"Parser surface\".", ""]
for name in ["top"] + ORDER:
    cmd = "jef-data --help" if name == "top" else f"jef-data {name} --help"
    body = open(os.path.join(CAP, f"help_{name}.80.txt"), encoding="utf-8").read()
    assert body.endswith("\n") and "```" not in body
    help_lines += [f"## `{cmd}`", "", "```text", body.rstrip("\n"), "```", ""]
open(os.path.join(SRC, "cli_help.md"), "w", encoding="utf-8").write("\n".join(help_lines))
print("cli.md section and cli_help.md written")
