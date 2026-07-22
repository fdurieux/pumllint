# pumllint

A **semantic linter for PlantUML diagrams**. PlantUML validates syntax but is,
by its own admission, a drawing tool rather than a modeling tool: it happily
renders inconsistent diagrams. `pumllint` fills that gap with modeling-hygiene
and governance rules, and exports findings to **SonarQube** without needing a
SonarQube plugin.

Zero runtime dependencies (PyYAML only if you use a YAML config). Python ≥ 3.11.

## Quick start

```bash
python -m pumllint examples/                 # lint a directory recursively
python -m pumllint --list-rules              # what can it check?
python -m pumllint diagrams/ -f sonar -o pumllint-sonar.json
python -m pumllint --profile codegen diagrams/   # + codegen-readiness rules
```

Exit codes: `0` clean, `1` findings at/above `--fail-on` (default `major`), `2` usage error — drop it straight into CI.

## Rules

| ID | Name | Default | What it catches |
|----|------|---------|-----------------|
| SEQ001 | undeclared-participant | critical | Participant used but never declared. **Typo detector**: PlantUML silently creates a phantom lifeline for `Custmer -> Bank`. |
| SEQ002 | unused-participant | minor | Declared participant that appears in no message. |
| SEQ003 | unbalanced-activation | major | `activate` never closed by `deactivate`/`return` (unterminated flow), or `deactivate` without prior `activate`. Understands `++`/`--` arrow shortcuts and `destroy`. |
| SEQ004 | unterminated-block | critical | `alt`/`opt`/`loop`/`par`/`group`/`box` without `end`. |
| SEQ005 | unlabelled-message | minor | Arrow with no label (dotted returns tolerated by default). |
| GEN001 | missing-title | minor | No `title`. |
| GEN002 | unnamed-diagram | info | `@startuml` without a name. |
| GEN003 | inline-skinparam | minor | Per-diagram styling instead of a central theme include. |
| GEN004 | participant-naming | minor | Names violating a configurable regex (per-kind overrides supported). |
| GEN005 | max-participants | minor | More lifelines than the configured max. |
| UC001 | orphan-actor-or-usecase | major | Use-case diagrams: actor or use case linked to nothing. |
| UC002 | usecase-actor-naming | minor | Use case not phrased verb-first (verb–object). Needs a `verbs` whitelist; dormant otherwise. |
| SEQ006 | no-self-message | minor | Self-message; internal logic belongs in a note or `ref over`. Option `allowed` whitelists participants. |
| SEQ007 | unlabelled-block-condition | minor | `alt`/`opt`/`loop`/`break`/`critical` without a condition label. |
| SEQ008 | fragment-nesting-depth | minor | Combined fragments nested past `max_nesting_depth` (default 3) — extract a sub-diagram. |
| SEQ009 | unpaired-return | minor | Dashed return arrow (`-->`) that pairs with no preceding call. |
| SEQ010 | explicit-participant-order | info | Participant introduced by first use. Opt-in via `require_explicit_order`. |
| ACT001 | missing-start | major | Activity diagram with actions but no `start` node. |
| ACT002 | missing-stop | major | Activity flow never reaches `stop`/`end` (unterminated flow). |
| ACT003 | unlabelled-decision-branch | minor | `if (...) then` / `else` without a `(yes)`/`(no)` branch label. |
| ACT004 | unterminated-construct | critical | `if`/`while`/`repeat`/`fork`/`switch`/`partition` never closed. |
| ACT005 | swimlane-naming | minor | Swimlane (`|Lane|`) name violating a configurable `pattern`. |
| ACT006 | verb-first-activity | minor | Activity not phrased verb-first. Needs a `verbs` whitelist; dormant otherwise. |

### Codegen-readiness pack (profile: `codegen`)

Rules `SEQ101–SEQ109` validate whether a sequence diagram is precise and
complete enough for an AI coding agent (or any downstream generator) to
implement it **without inventing missing details**. They are disabled by
default and activate with `--profile codegen` or `profile: codegen` in the
config. Ids `SEQ100–SEQ199` are reserved for this range.

| ID | Name | Default | What it catches |
|----|------|---------|-----------------|
| SEQ101 | codegen-implicit-participant | blocker | Lifeline created implicitly on first use — the generator must guess what `OrderSvc` is. |
| SEQ102 | codegen-untyped-participant | major | Bare `participant X` with no typed keyword or `<<stereotype>>` — no mapping signal (actor → API boundary, `database` → repository, `<<external>>` → client stub). |
| SEQ103 | codegen-prose-message | blocker | Call labels that aren't operation signatures: `fetch the order details` instead of `findOrderById(orderId)`. |
| SEQ104 | codegen-missing-return | major | Synchronous call (`->`) with no reply arrow or `return` — return type left undefined. Async `->>` is exempt. |
| SEQ105 | codegen-vague-guard | blocker | `alt`/`opt`/`loop` with an empty or vague guard (`sometimes`, `if needed`, …). `else` must carry a guard, or literal `[else]` in a two-branch alt. |
| SEQ106 | codegen-elision-marker | blocker | `...`, `TBD`, `TODO`, `etc`, `???`, `and so on` in labels, guards or notes — deliberately omitted behaviour the generator would fill with fiction. |
| SEQ107 | codegen-missing-failure-path | major | Call to an `<<external>>`/`database`/`queue` participant with no failure branch (alt error branch, `break`, or `group error`). |
| SEQ108 | codegen-activation-lifecycle | major | `activate`/`deactivate` not pairing as a well-formed per-lifeline stack — call nesting ambiguous. |
| SEQ109 | codegen-uninformative-reply | minor | Return drawn with a solid arrow, or a reply labelled `ok`/`done`/`result` instead of naming the returned value — breaks data-dependency inference. |

The vagueness / elision / non-informative lexicons are configurable per rule
(`vague_terms`, `tokens`, `failure_keywords`, `non_informative`).

## Configuration

`pumllint.yaml` (or `.toml` / `.json`) is auto-detected in the working
directory, or passed with `-c`. Rules are keyed by ID or kebab-case name;
`false` disables, a mapping supplies options and/or a `severity` override:

```yaml
rules:
  unnamed-diagram: false
  participant-naming:
    severity: major
    pattern: "^[A-Z][A-Za-z0-9]*$"
    per_kind:
      actor: "^[A-Z][a-z]+$"
  max-participants:
    max: 7
```

## Profiles

A profile switches on profile-gated rule packs and may escalate severities of
existing rules. Select it with `profile:` in the config or `--profile` on the
CLI (the CLI wins):

```yaml
profile: codegen
profiles:
  codegen:
    enable:            # optional: activate gated rules explicitly by id/name
      - SEQ101
      - SEQ102
    escalate:          # optional: severity overrides while the profile is active
      SEQ001: blocker  # e.g. undeclared participant becomes blocking
```

`pumllint --profile codegen src/diagrams/` is enough on its own — rules
registered for a profile activate whenever that profile is selected; the
`enable:` list is only needed to pull in rules gated behind *other* profiles,
and `escalate:` to tighten the base catalog. Escalations win over rule-level
`severity:` settings — a profile is an opt-in quality gate.

## Inline suppressions

Findings can be silenced at the source, `eslint`-style, with PlantUML
comments — reviewable and diff-friendly, unlike config-file exclusions:

```plantuml
' pumllint: disable=SEQ006, unlabelled-message   ← next line only
Batch -> Batch : self-trigger

' pumllint: disable-file=GEN003                  ← whole file
' pumllint: disable                              ← all rules, next line
```

Rules can be referenced by id or kebab-case name. CI can audit what is being
suppressed by running with `--no-suppressions` (or `suppressions: false` in
the config), which reports everything regardless of comments.

## Architecture

```
pumllint/
├── model.py          # Diagram / Participant / Message / Violation dataclasses
│                     #   + call/reply pairing & activation-stack helpers
├── parser/           # line-oriented parser → semantic Diagram model
│   ├── sequence.py   #   sequence + use-case + suppression comments
│   └── activity.py   #   new-style activity syntax (start/if/while/fork/…)
├── rules/            # rule packs; auto-discovered via @register decorator
│   ├── catalog.toml  #   declarative rule metadata (name/desc/severity/scope)
│   ├── sequence/     #   SEQ*  (participants.py, flows.py, codegen.py)
│   ├── activity/     #   ACT*  (structure.py)
│   └── common/       #   GEN*, UC*  (governance.py)
├── reporters/        # text / json / sonar; auto-registered via @reporter
├── engine.py         # config merge → rule instantiation → run
├── config.py         # yaml / toml / json loading
└── cli.py            # argparse CLI, CI-friendly exit codes
```

Design choices for extensibility:

- **Parser and rules are decoupled** through the `Diagram` model. Rules never
  see raw text, so parser improvements benefit every rule.
- The parser recognizes a *governance-relevant subset* and ignores unknown
  lines — deliberately tolerant, because the PlantUML grammar is defined by
  its Java implementation and evolves constantly.
- **Adding a rule = one class + one catalog entry.** A rule class carries only
  its `id` and its `check()` algorithm; the declarative metadata (name,
  description, severity, scope, profiles) lives in `rules/catalog.toml` and is
  stamped onto the class by `@register`. Drop a module anywhere under
  `pumllint/rules/` — `discover()` walks the package, so there is nothing else
  to wire up:

```toml
# pumllint/rules/catalog.toml
[SEQ006]
name = "no-self-message"
description = "Self-messages hide logic that belongs in a note or ref"
severity = "minor"
applies_to = ["sequence"]
profiles = []
```

```python
from pumllint.rules import Rule, register

@register
class NoSelfMessage(Rule):
    id = "SEQ006"

    def check(self, diagram):
        for m in diagram.messages:
            if m.source and m.source == m.target:
                yield self.violation(diagram, m.line, f"Self-message on '{m.source}'")
```

- **Adding an output format = one class** decorated with `@reporter`.
- **Profile-gated rules** set `profiles = ["codegen"]` in their catalog entry;
  the engine keeps them dormant until that profile is selected. Everything else
  (config, suppressions, reporters) works identically for gated rules.
- New diagram types slot in as a parser extension plus a rule pack — exactly
  how activity support (ACT001–004) was added in 0.2.0; class/component
  diagrams would follow the same pattern with `applies_to = ("class",)`.

## CI integration (GitHub Actions)

```yaml
- name: Lint PlantUML diagrams
  run: |
    python -m pumllint docs/diagrams --fail-on major \
      -f sonar -o pumllint-sonar.json
- name: SonarQube scan
  uses: SonarSource/sonarqube-scan-action@v4
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
  with:
    args: >
      -Dsonar.externalIssuesReportPaths=pumllint-sonar.json
```

The `sonar` reporter emits the **Generic Issue Import Format** (the 10.3+
schema with `rules` + `issues` and clean-code impacts). SonarQube ingests it
via `sonar.externalIssuesReportPaths` — findings land in dashboards, quality
gates and PR decoration with **no Java plugin to build or maintain**.

Recommended companion step: run PlantUML's own `-checkonly` first for pure
syntax, then `pumllint` for semantics.

## Tests

Two complementary entry points:

```bash
# 1. Unit + integration tests. Zero-dependency runner — no pytest needed;
#    ideal for offline/CI-minimal environments.
python tests/run_tests.py

# 2. Everything above PLUS the executable RULES.md spec (pytest-bdd).
#    Needs the optional `test` extra.
pip install -e ".[test]"
python -m pytest
```

`run_tests.py` collects only the top-level `tests/test_*.py` (unit tests,
rule checks, the catalog parity guard, and the feature/RULES.md sync guard) and
never imports pytest-bdd. The BDD layer lives under `tests/bdd/` and runs only
under pytest.

**Executable spec (RULES.md ↔ tests).** The `` ```gherkin `` block under each
rule in [RULES.md](RULES.md) is the acceptance spec. `tools/extract_features.py`
generates `tests/bdd/features/<ID>.feature` from those blocks; pytest-bdd binds
them to a small canonical step vocabulary (`tests/bdd/test_features.py`) and runs
them against the real linter. Blocked/planned rules are `@skip`-tagged. A sync
test fails if the committed features drift from RULES.md — after editing a
Gherkin block, regenerate:

```bash
python tools/extract_features.py
```
