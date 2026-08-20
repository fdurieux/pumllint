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
