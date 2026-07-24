# Setup and CI integration

*Audience: DevOps / platform engineers wiring pumllint into a pipeline, and
anyone running it locally for the first time.*

## Requirements

- Python ≥ 3.11. No runtime dependencies (PyYAML only if you use a **YAML**
  config file; TOML and JSON configs need nothing).
- Optional companion: the `plantuml` CLI, if you want the syntax gate
  (`--check-syntax`) in addition to semantic linting.

## Install and first run

```bash
pip install pumllint                    # or: pipx / uv tool install pumllint

pumllint diagrams/                      # lint a directory recursively
pumllint --list-rules                   # what can it check?
pumllint score diagrams/                # maturity report (read-only)
```

To install from source instead (e.g. to try an unreleased commit):
`pip install git+https://github.com/fdurieux/pumllint@v0.21.0`.
`python -m pumllint` is equivalent to the `pumllint` script everywhere.

`.puml`, `.plantuml`, `.iuml` and `.wsd` files are picked up.

**Exit codes** (identical for local runs and CI): `0` clean, `1` findings at
or above `--fail-on` (default `major`) — or, for `score`, a failed gate — and
`2` usage error.

## Configuration

Place `pumllint.yaml` (or `.toml` / `.json`) in the working directory — it is
auto-detected — or pass it with `-c`. Rules are keyed by ID or kebab-case
name; `false` disables, a mapping supplies options and/or a `severity`
override:

```yaml
rules:
  unnamed-diagram: false
  max-participants: { max: 7 }
  # Convention rules are dormant until you supply YOUR convention:
  owner-tag:        { pattern: "(?i)owner\\s*:" }
  requirement-link: { pattern: "REQ-\\d+|ADR-\\d+" }
```

The CLI `--profile` flag overrides the config's `profile:` key. All scoring
knobs (weights, thresholds, caps) live under a `scoring:` key — see
[SCORING.md](../SCORING.md); the defaults are calibrated, change them
deliberately.

## The recommended pipeline shape

Three steps, cheapest first:

1. **Syntax** — `plantuml -checkonly` (pure syntax; pumllint deliberately
   delegates this).
2. **Lint** — `pumllint` with `--fail-on major`: blocks broken/misleading
   diagrams.
3. **Score gate** — `pumllint score` with a **baseline ratchet** plus a
   **minimum-level floor**.

### GitHub Actions (composite action)

The repo ships an action; pin the ref, inputs mirror the CLI:

```yaml
- uses: actions/checkout@v4

- name: Lint PlantUML diagrams
  uses: fdurieux/pumllint@v0.21.0
  with:
    paths: docs/diagrams

- name: Maturity ratchet + floor
  uses: fdurieux/pumllint@v0.21.0
  with:
    command: score
    paths: docs/diagrams
    baseline: maturity.json
    min-level: "2"

- name: Maturity report (artifact for reviewers)
  uses: fdurieux/pumllint@v0.21.0
  with:
    command: score
    paths: docs/diagrams
    format: html
    output: maturity-report.html
- uses: actions/upload-artifact@v4
  with: { name: maturity-report, path: maturity-report.html }
```

Available inputs: `command` (`lint`|`score`|`fix`), `paths`, `config`,
`profile`, `format`, `output`, `fail-on` (lint), `min-level` / `baseline` /
`update-baseline` (score), and `extra-args` for anything else — e.g.
`command: fix` with `extra-args: --dry-run` as a "fixes pending?" check.

### Baseline / ratchet workflow (brownfield)

A fixed `--min-level` on an existing model set would demand a big-bang
cleanup. Instead:

```bash
pumllint score diagrams/ --baseline maturity.json   # 1st run RECORDS levels
git add maturity.json                               # commit the baseline
```

From then on the same command **ratchets**: CI fails only when a diagram
drops below its own recorded level (`regression: file::Diagram: Level 2
(baseline 3)` on stderr, exit 1). Diagrams new since the baseline always pass
the ratchet — combine with `--min-level` to hold new work to a floor. When a
team deliberately accepts a lower level, refresh with `--update-baseline`
(treat that flag like `--amend`: a reviewed, conscious act — the baseline
diff shows exactly what was conceded).

### Pre-commit hooks

```yaml
repos:
  - repo: https://github.com/fdurieux/pumllint
    rev: v0.21.0
    hooks:
      - id: pumllint                  # lint staged diagrams
      - id: pumllint-score
        args: [--min-level, "3"]      # maturity gate per commit
```

Hook environments are isolated: if your repo uses a `pumllint.yaml` config,
add `additional_dependencies: [PyYAML]` to the hook.

### SonarQube (no plugin needed)

```yaml
- run: |
    python -m pumllint docs/diagrams --fail-on major \
      -f sonar -o pumllint-sonar.json
- uses: SonarSource/sonarqube-scan-action@v4
  env: { SONAR_TOKEN: "${{ secrets.SONAR_TOKEN }}" }
  with:
    args: >
      -Dsonar.externalIssuesReportPaths=pumllint-sonar.json
```

The `sonar` format is the Generic Issue Import Format (10.3+ schema with
clean-code impacts); findings land in dashboards, quality gates and PR
decoration.

### Maturity badge

```bash
pumllint score diagrams/ -f badge -o badge.json
```

Publish `badge.json` anywhere raw-fetchable and embed:

```markdown
![maturity](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<org>/<repo>/main/badge.json)
```

## Building tooling on the output

`-f json` (for both `lint` and `score`) is a **public contract**, pinned by
JSON Schemas shipped in the package:

```bash
python -m pumllint schema lint    # shape of `pumllint -f json`
python -m pumllint schema score   # shape of `pumllint score -f json`
```

Point any draft-2020-12 validator at these when you script against the
output; pumllint's own test suite guarantees every report it emits validates
against them, so the shape cannot drift silently between versions. (The
`badge` and `sonar` shapes are shields.io's and SonarQube's contracts, not
pumllint's.)

## Auditing suppressions

Authors can silence findings with `' pumllint: disable=…` comments
(see [findings guide](findings-and-scores.md#suppressions)). Every maturity
report already discloses how much is being silenced — an affected diagram
shows `100/100 (3 suppressed)` and the JSON report carries the count as
`suppressedCount` — so a rising count is visible on every run, not just
during audits. For a full audit, run CI once with `--no-suppressions` —
everything is reported regardless of comments, so you can see what is being
suppressed and decide whether that's fine.
