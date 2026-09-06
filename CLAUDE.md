# Working on pumllint

## Tests

```bash
python tests/run_tests.py     # zero-dependency runner (stdlib only) — the promise the project makes
python -m pytest              # full suite: the above plus the executable RULES.md spec (pytest-bdd)
```

Both must pass. `tests/run_tests.py` imports every `tests/test_*.py` and calls
each module-level `test_*` function, so tests are plain assert functions with
no fixtures and no third-party imports.

After changing RULES.md, regenerate the Gherkin features or CI fails:
`python tools/extract_features.py`.

After a deliberate scoring or reporter change, regenerate the published pilot
artefacts — `tests/test_pilot_example.py` compares them byte for byte:

```bash
python -m pumllint score examples/ -f html  -o docs/example-maturity-report.html
python -m pumllint score examples/ -f badge -o docs/example-badge.json
```

## Pull requests

Standing authorisation from the maintainer: **open a PR, wait for CI to pass,
then merge it — no need to ask.** Wait for the whole matrix, including the
`windows` job, which is the only one that exercises PowerShell's argument
handling and the Windows console codec. Do not merge on a red or pending run.

Merged branches were not deleted automatically until the 2026-09-06
hygiene pass (twelve stale branches, deleted by the owner that day), and
a hosted session cannot delete them: the git proxy answers a
branch-deleting push (`git push origin :refs/heads/<branch>`) with
`HTTP 403` and then prints `Everything up-to-date`, so read the whole
output, never the last line; no MCP tool deletes a ref, and a direct API
write to the repository settings is denied by the session's permission
gate (reading `delete_branch_on_merge` works). The setting is the
owner's — `gh repo edit` with its delete-branch-on-merge option, or
Settings → General → "Automatically delete head branches" — and a merged
PR's branch vanishing is the sign it is on. Verify a ref with
`git ls-remote origin 'refs/heads/*'`; deleting one is the owner's, via
`gh api -X DELETE repos/fdurieux/pumllint/git/refs/heads/<branch>` or the
Branches page. `main`'s history was restarted on 2026-08-29 (two roots,
`a92c24f` and `1089a99`): a branch from the old line (root `71f70a6`)
shares no ancestor with `main`, reads as hundreds of commits "ahead", and
is superseded once its PRs are merged — compare trees, not commit counts,
before calling such a branch unmerged.

## Audiences and register

Every document here is written for one of two readers, and the register
follows the reader, not the topic:

- **Adopter-facing** — `README.md`, `docs/business-processes.md` and the
  other guides under `docs/`: assume no prior knowledge of PlantUML,
  linters or the modelling tool the reader comes from. Name a concept
  before using it, say what a flag does and what the reader gets back,
  and keep a plain-English walkthrough beside any command sequence a
  guide recommends (the model is aris2puml's README §"The two commands,
  in plain English").
- **Maintainer-facing** — `RULES.md` (the executable spec), `ROADMAP.md`,
  `EVIDENCE.md`, `SCORING.md`, this file, commit messages, PR bodies and
  chat replies: assume all of it. Terse, dense, symbols cited by name.

"Explain in plain English" is therefore the adopter register, not a
verbosity setting: apply it when the reader is an adopter, or when asked.
A prose walkthrough has no golden behind it, so `tests/test_docs_flags.py`
is its gate: every `--<name>` option that `README.md` or `docs/business-processes.md`
mentions must be an option of one of the CLI's parsers, the one foreign
flag (`--manifest`, aris2puml's) being listed there on purpose. Rename or
drop an option and the suite is red until the prose moves with it.

## Things that are contracts, not details

- **Exit codes** `0` / `1` / `2`. The composite action (`action.yml`) and both
  pre-commit hooks depend on them. A new "nothing was checked" condition warns
  on stderr; it does not change the exit code.
- **Report shapes** for `-f json` (lint, score, trace), pinned by the shipped
  JSON Schemas in `pumllint/schemas/`.
- **Rule IDs and kebab-case names**, and their config keys.
- **Reported file paths use forward slashes** on every platform, so a report
  produced on Windows is byte-identical to one produced on POSIX. Compare
  against `Path.as_posix()`, never `str(path)`.
- **All CLI output goes through `_out`/`_err`** in `pumllint/cli.py`, which
  downgrade characters the destination stream cannot encode. A bare `print()`
  reintroduces the Windows crash those helpers exist to prevent.
