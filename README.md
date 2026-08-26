# pumllint

[![PyPI](https://img.shields.io/pypi/v/pumllint)](https://pypi.org/project/pumllint/)
[![License: GPL-3.0-or-later](https://img.shields.io/github/license/fdurieux/pumllint)](LICENSE)

A **semantic linter for PlantUML diagrams**. PlantUML validates syntax but is,
by its own admission, a drawing tool rather than a modeling tool: it happily
renders inconsistent diagrams. `pumllint` fills that gap with modeling-hygiene
and governance rules, and exports findings to **SonarQube** without needing a
SonarQube plugin.

Zero runtime dependencies (PyYAML only if you use a YAML config). Python ≥ 3.11.

## Quick start

```bash
pip install pumllint                         # or: pipx / uv tool install pumllint

pumllint diagrams/                           # lint a directory recursively
pumllint --list-rules                        # what can it check?
pumllint diagrams/ -f sonar -o pumllint-sonar.json
pumllint --profile codegen diagrams/         # + codegen-readiness rules
pumllint score diagrams/ --min-level 3       # maturity gate (see below)
pumllint fix diagrams/                       # auto-fix mechanical findings
pumllint trace diagrams/ --requirements reqs.txt   # requirement-coverage matrix
```

(`python -m pumllint` is equivalent wherever the console script is not on PATH.)

Exit codes: `0` clean, `1` findings at/above `--fail-on` (default `major`), `2` usage error — drop it straight into CI.

### Windows and PowerShell

PowerShell and `cmd.exe` do not expand wildcards for native programs, so
pumllint expands them itself — `pumllint *.puml` and `pumllint "diagrams/**/*.puml"`
both work (quote patterns containing `**` so PowerShell leaves them alone). A
pattern that matches nothing is an error, never a silent pass.

Save diagrams as UTF-8. PowerShell 5.1's `>` and `Out-File` write UTF-16 and
`Set-Content` writes the ANSI code page; pumllint reads UTF-8, and UTF-16/UTF-32
when the file carries a byte-order mark, but rejects ANSI-encoded files by name.
In PowerShell 7: `... | Out-File -Encoding utf8NoBOM diagram.puml`.

When output is redirected or piped, Windows drops stdout to the console code
page, which cannot render `✔`/`✖`. pumllint substitutes `OK`/`FAIL` rather than
failing; set `$env:PYTHONUTF8 = "1"` to keep the glyphs.

The opt-in syntax gate takes Windows paths as written —
`syntax_command = 'java -jar C:\tools\plantuml.jar'` is split without POSIX
escaping, so the backslashes survive — and finds a `plantuml.bat` or `.cmd`
wrapper on PATH, which `subprocess` alone would not.

## Project status and stability

**Beta, and deliberately still `0.x`.** The tool is feature-complete for its
declared scope, fully tested (a stdlib-only suite, an executable Gherkin spec,
a pinned-PlantUML syntax gate) and used in its own CI. It has now met
third-party diagrams twice — a read-only dialect census over 159 files from
five public repositories
([record](docs/pilot-census-first-contact.md), 2026-08-11) and a semantic audit
against a 24-diagram corpus that returned four real defects, all fixed in
v0.29.0 ([record](docs/foreign-corpus-audit.md)) — but neither is a *standing*
fixture: no foreign corpus is yet under continuous regression here, and that
adoption is gated (see [ROADMAP.md](ROADMAP.md), Arc D). The remaining roadmap
items are demand-driven, not missing pieces.

*Stable — these are contracts, and breaking one is a deliberate, announced act:*

- CLI commands, flags and exit codes
- Rule IDs and kebab-case names, and their config keys/options
- The `-f json` report shapes for `lint` and `score`, pinned by the shipped
  JSON Schemas (see [Report schemas](#report-schemas))

*May still move within `0.x`:*

- **Score values for a given diagram.** New rules and calibration work can
  shift a diagram's level. Every shift is a diff-verified re-freeze of the
  golden corpus, called out in the release notes — the golden test makes
  silent drift impossible — but it *can* happen on a minor bump. If a build
  gates on an absolute level, pin an exact version (`pumllint==X.Y.Z`); if you
  want to track relative movement instead, use
  [baseline / ratchet mode](#baseline--ratchet-mode), which is designed for it.
- **`diagramType` values**, an open set that grows as parsers are added.

**What `1.0` waits on:** not more features — evidence that the score contract
survives contact with a foreign corpus. Run
[`tools/pilot_census.py`](tools/pilot_census.py) against a real corpus first
(read-only dialect census); that, plus a pilot, is the gate.

## Documentation by audience

This README is the reference. [docs/](docs/README.md) has role-specific guides:
[why adopt it](docs/case-for-pumllint.md) (management case, with the measured
evidence), [where the value lands in the SDLC](docs/value-in-the-sdlc.md)
(a value-stream assessment across the SAFe Continuous Delivery Pipeline),
[setup & CI integration](docs/setup-and-ci.md) (pipelines, ratchet,
Sonar, badge), [understanding findings & scores](docs/findings-and-scores.md)
(for report readers and diagram authors),
[writing rules](docs/writing-rules.md) (a step-by-step programming guide with
an end-to-end example, including how the executable Gherkin spec works), and
[using pumllint from a coding agent](docs/agents.md) (the score → repair →
re-score loop for AI agents implementing from diagrams).

## Maturity scoring

`pumllint score` aggregates rule findings into a **360° maturity level** per
diagram — from 1 (*Sketchy*) to 5 (*Method-complete*) — plus a prescriptive
gap report listing exactly which findings block the next level:

```text
order.puml [Order]: Level 3 (Disciplined) — 68/100
  To reach Level 4 (Precise):
    • DIM-CMP is 61, needs >= 70 — fix:
        SEQ102 major  order.puml:18  participant declaration has no role type

Model set: Level 3 (Disciplined) — 68/100 weighted across 1 diagram(s)
```

When no syntax check ran (no `--check-syntax`, no `scoring.syntax_gate`),
the text report says so — `Syntax gate: not run — DIM-SYN unchecked …` —
because the Level verdict otherwise silently assumes valid syntax.

Every report ends with a **model-set summary**: the worst per-diagram level
(the set is only as trustworthy as its weakest diagram) plus an
element-weighted composite across all scored diagrams. `--min-level` gates on
exactly that model-set level — it fails as soon as any diagram is below N.

```bash
python -m pumllint score diagrams/ --min-level 4     # CI gate: exit 1 below Level 4
python -m pumllint score diagrams/ --profile codegen # Level 5 requires this profile
python -m pumllint score diagrams/ --check-syntax    # also run plantuml -checkonly
```

### Baseline / ratchet mode

On a brownfield model set, a fixed `--min-level` gate would demand a big-bang
cleanup. Ratchet instead: record today's per-diagram levels once, then fail CI
only when a diagram drops **below its own baseline**.

```bash
python -m pumllint score diagrams/ --baseline maturity.json   # 1st run records,
                                                              # later runs ratchet
python -m pumllint score diagrams/ --baseline maturity.json --update-baseline
                                                              # accept the status quo
```

Commit `maturity.json`. Diagrams new since the baseline always pass the
ratchet (combine with `--min-level` to hold new work to a floor); regressions
are listed on stderr as `regression: <file>::<diagram>: Level 2 (baseline 3)`
and exit 1.

Ratchet-compare runs also annotate the report with **trends** — per diagram
and for the model set:

```text
order.puml [Order]: Level 4 (Precise) — 82/100  (Level 3 → 4 since last baseline)
checkout.puml: Level 3 (Disciplined) — 71/100  (new since baseline)
```

The json format carries the same machine-readably: each diagram (and
`modelSet`) gains `"baseline": {"level": 3, "delta": 1}` (`null` when not
ratcheting or new).

### Maturity badge

`-f badge` renders the model-set level as
[shields.io endpoint JSON](https://shields.io/badges/endpoint-badge):

```bash
python -m pumllint score diagrams/ -f badge -o badge.json
```

Publish `badge.json` anywhere raw-fetchable (the repo itself, gh-pages, a CI
artifact) and embed:

```markdown
![maturity](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<org>/<repo>/main/badge.json)
```

Colors follow the level: red (1) → orange (2) → yellow (3) → yellowgreen (4)
→ brightgreen (5).

### HTML report

`-f html` renders the score run as a single self-contained page for
architect-facing reviews — the model-set verdict first, then per-diagram
cards sorted worst-first, each with its level, per-dimension score bars, the
prescriptive gap report, and baseline trends when ratcheting:

```bash
python -m pumllint score diagrams/ -f html -o maturity-report.html
```

No scripts, no external requests, no timestamps: the file renders offline
and is byte-identical across runs over the same model set — publish it as a
CI artifact, attach it to a review, or drop it in a wiki. In GitHub Actions:

```yaml
- name: Maturity report
  uses: fdurieux/pumllint@v0.29.0
  with:
    command: score
    paths: docs/diagrams
    format: html
    output: maturity-report.html
- uses: actions/upload-artifact@v4
  with: { name: maturity-report, path: maturity-report.html }
```

A published example of this report — the bundled [examples/](examples/)
scored by the tool itself — lives at
<https://fdurieux.github.io/pumllint/example-maturity-report.html>
(`docs/example-maturity-report.html`, drift-guarded by
`tests/test_pilot_example.py`).

Why gate on it: in a measured experiment (75 generation runs, independent
LLM judge — see [EVIDENCE.md](EVIDENCE.md)), maturity scores correlated with
the fidelity of code generated from the diagrams (r ≈ 0.49), and diagrams
below Level 2 degraded generation sharply — fidelity dropped by roughly a
third and invented business logic doubled. The gate keeps those diagrams out.
Level 5 means *method-convention complete*: the diagram-side preconditions for
faithful generation, bound to the `codegen` profile so it cannot be claimed
without those rules running.

Scoring model, dimensions, thresholds, and calibration notes: [SCORING.md](SCORING.md).
All knobs are configurable under the `scoring` key (see `pumllint.toml`),
including two opt-in flags: `c7_requires_applicable_rules` (Level 5 needs a
profile rule that applies to the diagram's type) and `deduplicate_findings`
(a base finding restated by its codegen twin on the same line counts once).

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
| GEN005 | max-participants | minor | More elements than the type's budget — lifelines in a sequence diagram (default 9), declared actors plus use cases in a use-case diagram (default 15). `max` sets one budget for every type; `per_type` overrides it per diagram type. |
| GEN006 | owner-tag | minor | No ownership tag in title/header/footer/caption/notes. Needs a `pattern`; dormant otherwise. |
| GEN007 | requirement-link | minor | No requirement/ADR reference in name/title/notes. Needs a `pattern`; dormant otherwise. |
| GEN008 | note-density | minor | Structure narrated in notes instead of modelled (≥ `min_notes`, > `max_ratio` notes/element). |
| GEN009 | max-elements | minor | More semantic elements than `max` (default 60), any diagram type. |
| UC001 | orphan-actor-or-usecase | major | Use-case diagrams: actor or use case linked to nothing. |
| UC002 | usecase-actor-naming | minor | Use case not phrased verb-first (verb–object). Needs a `verbs` whitelist; dormant otherwise. |
| UC003 | include-extend-direction | minor | `<<include>>`/`<<extend>>` arrow pointing the wrong way (judged via actor connectivity), or involving an actor. |
| SEQ006 | no-self-message | minor | Self-message; internal logic belongs in a note or `ref over`. Option `allowed` whitelists participants. |
| SEQ007 | unlabelled-block-condition | minor | `alt`/`opt`/`loop`/`break`/`critical` without a condition label. |
| SEQ008 | fragment-nesting-depth | minor | Combined fragments nested past `max_nesting_depth` (default 3) — extract a sub-diagram. |
| SEQ009 | unpaired-return | minor | Dashed return arrow (`-->`) that pairs with no preceding call. |
| SEQ010 | explicit-participant-order | info | Participant introduced by first use. Opt-in via `require_explicit_order`. |
| SEQ011 | max-messages | minor | More messages than `max` (default 30) — split per phase or `ref over`. |
| ACT001 | missing-start | major | Activity diagram with actions but no `start` node. |
| ACT002 | missing-stop | major | Activity flow never reaches `stop`/`end` (unterminated flow). |
| ACT003 | unlabelled-decision-branch | minor | `if (...) then` / `else` without a `(yes)`/`(no)` branch label. |
| ACT004 | unterminated-construct | critical | `if`/`while`/`repeat`/`fork`/`switch`/`partition` never closed. |
| ACT005 | swimlane-naming | minor | Swimlane (`|Lane|`) name violating a configurable `pattern`. |
| ACT006 | verb-first-activity | minor | Activity not phrased verb-first. Needs a `verbs` whitelist; dormant otherwise. |
| CLS001 | class-naming | minor | Class/member names violating configurable patterns (default PascalCase classes, camelCase members; enum members exempt). |
| CLS002 | association-multiplicity | major | Association/aggregation/composition without a quoted multiplicity on both ends. |
| CLS003 | unlabelled-association | minor | Plain association with no role/verb label (`: places`). |
| CLS004 | inheritance-cycle | major | Cycle in the generalization/realization hierarchy — invalid UML that PlantUML happily renders. |
| CLS005 | max-members-per-class | minor | God-class smell: more members than `max` (default 15). |
| STA001 | single-initial-state | blocker | State machine without exactly one top-level `[*] -->` (composite-body initials don't count). |
| STA002 | unreachable-state | major | State with no incoming transition (self-loops don't count) — dead model content. |
| STA003 | unlabelled-transition | minor | Transition without an `event [guard] / action` label; `[*]` transitions exempt. |

### Cross-diagram consistency pack (XD)

Active only when more than one diagram is linted, these build an entity
symbol table across the whole batch — the same entity must keep one identity
everywhere. XD001–003 compare sequence-diagram participants (kind,
stereotype, spelling); XD004–005 span diagram *types*: a class
`OrderService <<service>>` and a sequence lifeline `orderService <<gateway>>`
are one entity drifting apart, and the linter says so.

| ID | Name | Default | What it catches |
|----|------|---------|-----------------|
| XD001 | conflicting-participant-kind | major | Same participant declared `participant` here, `database` there — every conflicted site is flagged with the full variant set; the per-entity `authoritative` option pins the intended value (also on XD002/XD005). |
| XD002 | conflicting-participant-stereotype | minor | Same participant with disagreeing stereotypes across sequence diagrams. |
| XD003 | participant-name-case-collision | minor | Participant spellings differing only by case across sequence diagrams. |
| XD004 | cross-type-name-collision | minor | Entity spellings differing only by case across diagram *types* (participants, classifiers, swimlanes). |
| XD005 | cross-type-stereotype-conflict | minor | Entity stereotyped differently in the class model than in the interaction models. |

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
| SEQ103 | codegen-prose-message | blocker | Call labels that aren't operation signatures: `fetch the order details` instead of `findOrderById(orderId)` — including prose hiding inside the parentheses (`handle(the payment stuff)`); `name: Type` params and quoted literals stay legal. |
| SEQ104 | codegen-missing-return | major | Synchronous call (`->`) with no reply arrow or `return` — return type left undefined. Async `->>` is exempt. |
| SEQ105 | codegen-vague-guard | blocker | `alt`/`opt`/`loop` with an empty or vague guard (`sometimes`, `if needed`, …). `else` must carry a guard, or literal `[else]` in a two-branch alt. |
| SEQ106 | codegen-elision-marker | blocker | `...`, `TBD`, `TODO`, `etc`, `???`, `and so on` in labels, guards or notes — deliberately omitted behaviour the generator would fill with fiction. |
| SEQ107 | codegen-missing-failure-path | major | Call to an `<<external>>`/`database`/`queue` participant with no failure branch (alt error branch, `break`, or `group error`). |
| SEQ108 | codegen-activation-lifecycle | major | `activate`/`deactivate` not pairing as a well-formed per-lifeline stack — call nesting ambiguous. |
| SEQ109 | codegen-uninformative-reply | minor | Return drawn with a solid arrow, or a reply labelled `ok`/`done`/`result` instead of naming the returned value — breaks data-dependency inference. |

The lexicons and shape options are configurable per rule (`vague_terms`,
`tokens`, `failure_keywords`, `non_informative`; SEQ103 also takes `pattern`,
`arg_stop_words` and `max_arg_words`; SEQ106 also takes `kinds` — which of
`message`, `guard`, `note` to scan, default all three).

Every lexicon takes two levers. Setting the key itself (`failure_keywords = [...]`)
**replaces** the shipped list, which is how you narrow one; setting
`extra_<key>` (`extra_failure_keywords = [...]`) **adds** to whatever is in
force, so opting into one more term does not cost you the defaults you did not
restate.

SEQ107 recognises a failure branch three ways, so the rule constrains modelling
rather than phrasing: the `failure_keywords` lexicon (`error`, `failure`,
`timeout`, `exception`, plus the absence family `absent`, `missing`, `empty`,
`unavailable`), a negated guard (`not`, `!=`, a leading `!`), or absence
phrasing (`none`/`null`/`nil`, or `no <noun>` as in `[order has no stored
rows]`). Setting `failure_keywords` replaces the lexicon; the negation and
absence forms always apply. A branch must still carry at least one message or
return — a declared-but-empty failure branch models nothing.

## Auto-fix

`pumllint fix` applies the mechanical fixes — the ones that are
deterministic and semantics-preserving, where nothing has to be invented:

| Finding | Fix |
|---------|-----|
| GEN002 unnamed-diagram | `@startuml <name>` derived from the file stem (ordinal suffix for multiple diagrams per file) |
| GEN001 missing-title | `title <Humanized>` inserted after `@startuml` |
| SEQ001/SEQ101 undeclared-participant | `participant X` declarations in first-use order, anchored after the existing declarations |

```bash
python -m pumllint fix diagrams/            # apply fixes in place
python -m pumllint fix diagrams/ --dry-run  # show the diff; exit 1 if fixes
                                            # are pending (CI check mode)
```

Fixes are driven by the linter's actual findings, so suppressed findings and
disabled rules are never "fixed", and the run is idempotent. The fixer also
inherits the linter's judgment calls: SEQ001 deliberately stays quiet in
files that declare no participants at all (ad-hoc sketches aren't punished),
so such files get no declaration fixes either — set
`SEQ001: {only_if_any_declared: false}` if you want sketches fixed too.
Everything else (labels, guards, multiplicities) stays a human decision —
the linter tells you *what*, but will not guess *which*. In GitHub Actions,
use `command: fix` with `extra-args: --dry-run` as a "fixes pending?" CI
check.

## Requirement traceability

`pumllint trace` builds the coverage matrix between a requirements
inventory and the diagrams that reference it — all three directions:
which requirement IDs are realized by which diagrams, which IDs no
diagram references, which diagrams reference nothing. It also flags
**unknown references** (an ID cited by a diagram but absent from the
inventory — a typo, or a stale inventory):

```text
Requirement coverage: 2/3 covered — 1 uncovered, 1 unknown reference(s), 1 unlinked diagram(s) — across 4 diagram(s)

REQ-101  ← orders/order_flow.puml [OrderFlow]:2, orders/refund.puml:3
REQ-103  ✖ uncovered

Unknown references (not in the inventory — a typo, or the inventory is stale):
  REQ-113  ← payments/charge.puml [Charge]:4

Unlinked diagrams (no requirement reference):
  sketches/idea.puml (sequence)
```

References are read from exactly the carriers the GEN007
(requirement-link) rule checks — the diagram name plus
title/header/footer/caption/notes — so the rule and the matrix can
never disagree; one configured convention serves both. The ID regex
comes from `--pattern`, falling back to the configured
`rules.requirement-link.pattern`.

The inventory comes from either or both of:

```bash
pumllint trace diagrams/ --requirements reqs.txt        # explicit ID list
pumllint trace diagrams/ --requirements-scan docs/specs # scan docs with the pattern
```

The list file is plain text — one ID per line; blank lines, full-line
`#` comments and inline ` # …` comments are ignored (a `#` with no
whitespace before it stays part of the ID, so `REQ#5` survives). An ID
containing whitespace draws a stderr warning — it can never match a
reference pattern — without changing the exit code.
Or JSON/YAML: an array of IDs — strings or objects carrying an `id`, so a
synchronized snapshot exported from a requirements/process repository
works unchanged (extra columns are ignored today; the JSON report's
`id` values are the stable join keys for a wider traceability matrix
later). `--requirements-scan` walks `*.md/*.txt/*.adoc/*.rst` and
extracts IDs by regex — so the two inventory sources parse differently:
a doc line yields the matched ID alone, while the same line moved into
a dedicated list file is taken verbatim as one ID.

CI gates are opt-in, one per direction — without them the command is
report-only (exit 0):

```bash
pumllint trace diagrams/ --requirements reqs.txt \
  --fail-on-uncovered --fail-on-unlinked --fail-on-unknown-ref
```

`-f json` emits a machine-readable matrix pinned by a shipped schema
(`pumllint schema trace`). In GitHub Actions, use `command: trace` with
the inventory flags in `extra-args`.

## Report schemas

The machine-readable reports are a public contract, pinned by JSON Schemas
(draft 2020-12) shipped inside the package:

```bash
python -m pumllint schema lint    # the shape of `pumllint -f json`
python -m pumllint schema score   # the shape of `pumllint score -f json`
python -m pumllint schema trace   # the shape of `pumllint trace -f json`
```

Point any standard validator at them when building tooling on top of the
output. pumllint's own test suite validates every report shape it can emit
against these schemas — like the golden scores, the shape cannot drift
silently. The badge and sonar formats are deliberately not covered: those
shapes are shields.io's and SonarQube's contracts, not pumllint's.

In GitHub Actions, use `command: schema` with `report: lint | score | trace`
(paths and format inputs are ignored; `output:` writes the schema to a file).

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
  # Traceability rules are dormant until you supply your project's convention:
  owner-tag:
    pattern: "(?i)owner\\s*:"
  requirement-link:
    pattern: "REQ-\\d+|ADR-\\d+"
```

Treat the config file with code-level trust, like a Makefile or a
pre-commit config: `scoring.syntax_command` names a command pumllint will
execute for the opt-in syntax gate, so do not run pumllint with an
auto-detected config inside a checkout you do not trust (see
[SECURITY.md](SECURITY.md)).

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

Suppressed findings never vanish silently from maturity scores: `pumllint
score` annotates every affected diagram — `100/100 (3 suppressed)` — and the
JSON report carries a `suppressedCount` per diagram and for the model set,
so a suppressed-clean diagram is always distinguishable from a clean one.

## Architecture

```
pumllint/
├── model.py          # Diagram / Participant / Message / Violation dataclasses
│                     #   + call/reply pairing & activation-stack helpers
├── parser/           # line-oriented parser → semantic Diagram model
│   ├── sequence.py   #   sequence + use-case + suppression comments
│   ├── activity.py   #   new-style activity syntax (start/if/while/fork/…)
│   ├── class_.py     #   class diagrams (classifiers, members, relations)
│   └── state.py      #   state machines ([*], transitions, composites)
├── rules/            # rule packs; auto-discovered via @register decorator
│   ├── catalog.toml  #   declarative rule metadata (name/desc/severity/scope)
│   ├── sequence/     #   SEQ*  (participants.py, flows.py, codegen.py)
│   ├── activity/     #   ACT*  (structure.py)
│   ├── class_/       #   CLS*  (structure.py)
│   ├── state/        #   STA*  (structure.py)
│   └── common/       #   GEN*, UC*  (governance.py)
├── reporters/        # text / json / sonar / badge / html; auto-registered
│                     #   via @reporter
├── schemas/          # JSON Schemas — the `-f json` output contract
├── schema.py         #   loader + minimal validator (drift-guarded in tests)
├── engine.py         # config merge → rule instantiation → run
├── trace.py          # requirement↔diagram coverage matrix (`trace`)
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
  how activity support (ACT001–004) was added in 0.2.0, class support
  (CLS001–005) in 0.9.0 and state support (STA001–003) in 0.10.0; component
  diagrams would follow the same pattern with `applies_to = ("component",)`.

## CI integration (GitHub Actions)

The repo ships a composite action — it installs pumllint from the exact ref
you pin and runs it:

```yaml
- uses: actions/checkout@v4
- name: Lint PlantUML diagrams
  uses: fdurieux/pumllint@v0.29.0
  with:
    paths: docs/diagrams
- name: Maturity ratchet + floor
  uses: fdurieux/pumllint@v0.29.0
  with:
    command: score
    paths: docs/diagrams
    baseline: maturity.json
    min-level: "2"
```

Inputs mirror the CLI: `command` (`lint`|`score`), `paths`, `config`,
`profile`, `format`, `output`, `fail-on` (lint), `min-level` / `baseline` /
`update-baseline` (score), and `extra-args` for anything else.

Or call the CLI directly — e.g. to feed SonarQube:

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

## Pre-commit hooks

```yaml
repos:
  - repo: https://github.com/fdurieux/pumllint
    rev: v0.29.0
    hooks:
      - id: pumllint                 # lint staged diagrams
      - id: pumllint-score
        args: [--min-level, "3"]     # maturity gate per commit
```

Both hooks receive the staged PlantUML files (`.puml`, `.plantuml`, `.iuml`,
`.wsd`). `pumllint-score` only gates when given `--min-level N` and/or
`--baseline FILE` via `args`; without them it just prints the report. Hook
environments are isolated — if your repo uses a `pumllint.yaml` config, add
`additional_dependencies: [PyYAML]` to the hook (toml/json configs need
nothing extra).

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

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). The tool is *run*, not
linked: executing pumllint over your diagrams in CI, as a pre-commit
hook, or from the CLI imposes no license obligations on your diagrams,
your codebase, or the reports it produces — those are yours.

**Licensing commitment (2026-07-29).** This project will stay under
GPL-3.0-or-later or, at most, move between OSI-approved open-source
licenses. It will never be relicensed to a source-available or
proprietary license, and neither this tool nor any service or MCP
wrapper published from this repository will adopt AGPL. Decision record
and rationale: [ROADMAP.md](ROADMAP.md) § Settled questions and the
[pipeline fit evaluation](docs/prose-pipeline-evaluation.md).
