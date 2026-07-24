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

All results below are from the tool as built from this repository (first run
on **0.18.1**; the score rows were re-run after the suppressed-count
annotation and the codegen rows after the SEQ103 tightening — both changes
this run motivated, see "What to watch") with the repository's own config
(`pumllint.toml`), run from the repository root.

## The runs

| Command | Result |
|---------|--------|
| `pumllint docs/pumllint-lint-flow.puml` | ✔ No issues found, exit 0 |
| `pumllint --no-suppressions docs/pumllint-lint-flow.puml` | 3 × SEQ006 (self-message, minor), exit 0 |
| `pumllint score docs/pumllint-lint-flow.puml` | Level 4 (Precise) — 100/100 (3 suppressed); Level 5 refused without the codegen profile |
| `pumllint score --no-suppressions docs/pumllint-lint-flow.puml` | Level 4 (Precise) — 98/100 |
| `pumllint --profile codegen docs/pumllint-lint-flow.puml` | 12 findings (5 blocker, 7 major), exit 1 |
| `pumllint --profile codegen --no-suppressions …` | 15 findings (the 3 SEQ006 return — a rule-scoped suppression holds across profiles) |
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

- **SEQ103 checked shape, not content** *(since tightened — this run's
  second finding to become a change)*. At the time of the run,
  `check_all(diagrams) for cross-diagram rules` was a blocker (trailing
  prose) yet `load_config(explicit path or auto-detect)` passed — prose
  *inside* the parentheses read as a signature, so wrapping prose in
  parentheses "compiled". The rule now inspects the argument list — a
  function-word lexicon plus a two-word width cap, both configurable;
  `name: Type` params and quoted literals stay legal — and that label is
  a blocker (the codegen rows above show the post-tightening counts).
  Deliberately precision-first: a two-word argument with no function
  word (`recursing directories`) still passes.
- **Craft is not truth.** A 100/100 diagram with the calls drawn in the
  wrong order would still score 100/100. No rule can check a diagram
  against the code it describes; this is why the maturity levels claim
  "Precise", not "correct", and why that claim language should not drift.
- **Suppressed findings left no trace in reports** *(since fixed — this
  run's finding became the change)*. Adding three disable comments moved
  the score from 98 to 100 with nothing in the output saying so, so a team
  could have inflated its level by suppress-spamming. Score reports now
  disclose the exclusion on every run: the affected diagram reads
  `100/100 (3 suppressed)`, the model-set line carries the total, and the
  JSON report records `suppressedCount` per diagram and for the set.
  `--no-suppressions` remains the full audit.
- **Dormant governance rules stay dormant at home.** GEN006/GEN007
  (owner tag, requirement link) are unconfigured in the repository's own
  `pumllint.toml`, so its own architecture diagram carries no ownership
  metadata.
- **DIM-SYN was not exercised** *(since closed in CI — the third finding
  to become a change)*. The local run environment had no `plantuml`
  binary, so `score --check-syntax` was skipped and syntax was vouched
  for only by pumllint's own parser — evidence of well-formedness, not a
  render. The `syntax-gate` CI job now runs the real gate (a pinned
  PlantUML jar) over every shipped diagram on every push, pinning both
  directions: the grammar-valid set must pass `-checkonly`, and the
  deliberately broken examples with grammar-level damage must fail it
  *and* be forced to Level 1 by the C2 cap.

## Verdict

Sense, decisively — on a sample of one. The default profile flagged
exactly the deliberate style deviations and nothing else; severity, gating
and the suppression round-trip behaved like a tool meant for CI; and the
weak spots found were scoping choices (a signature heuristic since
tightened, craft-not-truth) rather than false positives. The findings
above doubled as a to-do list, not a disclaimer: two of them shipped as
product changes, and a third closed as a CI gate.
