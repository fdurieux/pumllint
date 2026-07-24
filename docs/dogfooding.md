# Dogfooding: pumllint on its own lint flow

The repository already publishes the tool's own maturity report over the
bundled `examples/` (the pilot's Phase-0 artefact). This page extends the
self-application one step further: pumllint's architecture documentation is
itself a PlantUML sequence diagram, and pumllint lints it.

The artefact is [`pumllint-lint-flow.puml`](pumllint-lint-flow.puml): the
default lint command drawn from `cli.py` (`_run_lint`) and `engine.py` —
CLI → config auto-detection → engine construction (rule discovery from
`catalog.toml`, profile gating, severity escalation) → file collection →
parsing → per-diagram rules → suppression filter → cross-diagram rules →
reporter → exit code.

The diagram was authored in house style (named diagram, title, declared
PascalCase participants, labelled messages and blocks, balanced
activations) but *not* contorted to dodge every rule: three
`Engine -> Engine` self-messages were kept, because that is how an engineer
naturally draws internal steps. They are the honest test surface. The
checked-in file resolves them the way SEQ006's own rationale sanctions —
inline `' pumllint: disable=SEQ006` comments marking them as genuinely
intended — so the suppression mechanism the diagram *documents* is also the
mechanism that *cleans* it.

All results below are from pumllint **0.18.1** with the repository's own
`pumllint.yaml`, run from the repository root.

## The runs

| Command | Result |
|---------|--------|
| `pumllint docs/pumllint-lint-flow.puml` | ✔ No issues found, exit 0 |
| `pumllint --no-suppressions docs/pumllint-lint-flow.puml` | 3 × SEQ006 (self-message, minor), exit 0 |
| `pumllint score docs/pumllint-lint-flow.puml` | Level 4 (Precise) — 100/100; Level 5 refused without the codegen profile |
| `pumllint score --no-suppressions docs/pumllint-lint-flow.puml` | Level 4 (Precise) — 98/100 |
| `pumllint --profile codegen docs/pumllint-lint-flow.puml` | 11 findings (4 blocker, 7 major), exit 1 |
| `pumllint --profile codegen --no-suppressions …` | 14 findings (the 3 SEQ006 return — a rule-scoped suppression holds across profiles) |
| `pumllint fix --dry-run docs/pumllint-lint-flow.puml` | "Nothing to fix", exit 0 |

## What held up

- **Finding precision.** On the default profile, the only findings were the
  three self-messages deliberately left in — correct rule, correct
  severity, exact line numbers. Nothing else was flagged across ~24
  messages, three block kinds, a multiline label, a title containing
  `<paths>`, and a note whose text names `pumllint.yaml`. Zero false
  positives *on this one diagram*; that is an anecdote, not a precision
  claim.
- **Severity calibration.** The findings are minor, the default gate is
  `--fail-on major`, so a good-faith documentation diagram gets feedback
  without a broken build.
- **The escape hatch works as specified.** Inline
  `' pumllint: disable=SEQ006` silences exactly the annotated lines;
  `--no-suppressions` resurfaces all three for audit.
- **The codegen profile discriminates.** SEQ102 flagged all seven bare
  `participant` declarations but not `actor Developer` — the typed keyword
  carries the mapping signal the rule asks for. The prose-message blockers
  are the right verdict against the codegen contract; the defaults keep
  that contract opt-in, which is the right place for it.
- **The Level-5 gate is a contract, not a point total.** Even at a
  composite 100/100 the diagram stays Level 4, because Level 5 requires
  the codegen profile — and the report names the exact command to opt in.
- **The fixer does not invent.** With titles, names and declarations
  already present, `fix` reports nothing to do rather than "improving"
  labels or guards.

## What to watch

- **SEQ103 checks shape, not content.**
  `check_all(diagrams) for cross-diagram rules` is a blocker (trailing
  prose), yet `load_config(explicit path or auto-detect)` passes — prose
  *inside* the parentheses reads as a signature. Directionally right,
  trivially gameable: wrapping prose in parentheses "compiles".
- **Craft is not truth.** A 100/100 diagram with the calls drawn in the
  wrong order would still score 100/100. No rule can check a diagram
  against the code it describes; this is why the maturity levels claim
  "Precise", not "correct", and why that claim language should not drift.
- **Suppressed findings leave no trace in reports.** Adding three disable
  comments moved the score from 98 to 100 with nothing in the output
  saying so. `--no-suppressions` exists for audits, but a
  "N suppressed" annotation in the reports would make a clean run
  self-disclosing. (Improvement candidate at the time of writing.)
- **Dormant governance rules stay dormant at home.** GEN006/GEN007
  (owner tag, requirement link) are unconfigured in the repository's own
  `pumllint.yaml`, so its own architecture diagram carries no ownership
  metadata.
- **DIM-SYN was not exercised.** The run environment had no `plantuml`
  binary, so `score --check-syntax` was skipped; syntax is vouched for by
  pumllint's own parser, which is evidence of well-formedness, not a
  render.

## Verdict

Sense, decisively — on a sample of one. The default profile flagged
exactly the deliberate style deviations and nothing else; severity, gating
and the suppression round-trip behaved like a tool meant for CI; and the
weak spots found are scoping choices (a shape-only signature heuristic,
craft-not-truth) rather than false positives. The findings above double as
a to-watch list, not a disclaimer.
