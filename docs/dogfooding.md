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
reporter → exit code. A construct-by-construct description of the
diagram source — every PlantUML element, the rule it satisfies, and the
code it maps to — is in
[the annotated walkthrough](pumllint-lint-flow-explained.md).

The diagram was authored in house style (named diagram, title, declared
PascalCase participants, labelled messages and blocks, balanced
activations) but *not* contorted to dodge every rule: two
`Engine -> Engine` self-messages were kept, because that is how an engineer
naturally draws internal steps. They are the honest test surface. The
checked-in file resolves them the way SEQ006's own rationale sanctions —
inline `' pumllint: disable=SEQ006` comments marking them as genuinely
intended — so the suppression mechanism the diagram *documents* is also the
mechanism that *cleans* it.

All results below are from the tool as built from this repository (first run
on **0.18.1**; the score rows were re-run after the suppressed-count
annotation and the codegen rows after the SEQ103 tightening — both changes
this run motivated, see "What to watch" — and the counts re-verified on
0.28.0 after `2eca8ae` removed one self-message: three suppressions became
two) with the repository's own config
(`pumllint.toml`), run from the repository root.

## The runs

| Command | Result |
|---------|--------|
| `pumllint docs/pumllint-lint-flow.puml` | ✔ No issues found, exit 0 |
| `pumllint --no-suppressions docs/pumllint-lint-flow.puml` | 2 × SEQ006 (self-message, minor), exit 0 |
| `pumllint score docs/pumllint-lint-flow.puml` | Level 4 (Precise) — 100/100 (2 suppressed); Level 5 refused without the codegen profile |
| `pumllint score --no-suppressions docs/pumllint-lint-flow.puml` | Level 4 (Precise) — 98.4/100 |
| `pumllint --profile codegen docs/pumllint-lint-flow.puml` | 12 findings (5 blocker, 7 major), exit 1 |
| `pumllint --profile codegen --no-suppressions …` | 14 findings (the 2 SEQ006 return — a rule-scoped suppression holds across profiles) |
| `pumllint score --profile codegen docs/pumllint-lint-flow.puml` | Level 2 (Structured) — 62.9/100 (2 suppressed); the 5 SEQ103 blockers cap the level — the generation contract correctly refuses a diagram drawn for human readers |
| `pumllint fix --dry-run docs/pumllint-lint-flow.puml` | "Nothing to fix", exit 0 |

## Re-running the checks

The table above is the historical record; the three commands below
re-verify the current state at any time — after edits to the diagram,
the rules, or the config. Run from the repository root (`python3 -m
pumllint …` works where the `pumllint` console script is not on the
path):

```sh
pumllint docs/pumllint-lint-flow.puml
# expected: ✔ No issues found — exit 0

pumllint score docs/pumllint-lint-flow.puml
# expected: Level 4 (Precise) — 100/100 (2 suppressed);
#           Level 5 refused without the codegen profile
#           (plus the trailing "Syntax gate: not run" disclosure —
#           these runs skip the external gate)

pumllint --no-suppressions docs/pumllint-lint-flow.puml
# expected: exactly 2 × SEQ006 (minor) — the Engine self-messages
#           documented above, and nothing else
```

Any other output means something changed — a new finding, a shifted
score, or a suppression hiding more than the two documented
exceptions. Treat it like a golden-test failure: investigate before
shipping.

## What held up

- **Finding precision.** On the default profile, the only findings were the
  two self-messages deliberately left in — correct rule, correct
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
  `--no-suppressions` resurfaces both for audit.
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
  run's finding became the change)*. Adding the disable comments moved
  the score from 98 to 100 with nothing in the output saying so, so a team
  could have inflated its level by suppress-spamming. Score reports now
  disclose the exclusion on every run: the affected diagram reads
  `100/100 (2 suppressed)`, the model-set line carries the total, and the
  JSON report records `suppressedCount` per diagram and for the set.
  `--no-suppressions` remains the full audit.
- **Dormant governance rules stay dormant at home** *(since closed — the
  fourth finding to become a change)*. GEN006/GEN007 (owner tag,
  requirement link) were unconfigured in the repository's own
  `pumllint.toml`, so its own architecture diagram carried no ownership
  metadata. The config now declares the conventions — an `owner:` tag and
  references to the repo's spec documents (`README.md`, `RULES.md`, …) —
  and this diagram carries both in its `footer`. The bundled examples
  deliberately do not: they model a fictional domain and feed the frozen
  calibration corpus, so the published pilot report now honestly shows
  the TRC gap on them (aggregate 88 → 87.2/100; no level changed anywhere,
  measured before enabling).
- **DIM-SYN was not exercised** *(since closed in CI — the third finding
  to become a change)*. The local run environment had no `plantuml`
  binary, so `score --check-syntax` was skipped and syntax was vouched
  for only by pumllint's own parser — evidence of well-formedness, not a
  render. The `syntax-gate` CI job now runs the real gate (a pinned
  PlantUML jar) over every shipped diagram on every push, pinning both
  directions: the whole shipped set must pass `-checkonly`, and a
  synthetic grammar-broken probe must fail it *and* be forced to Level 1
  by the C2 cap. The job's first run measured something worth knowing:
  PlantUML accepts even the deliberately-bad examples — it tolerates
  unclosed `alt`/`while` — so SEQ004/ACT004 are *stricter than the
  grammar*, and grammar checking alone would miss exactly the breakage
  the maturity model exists to catch.

## The syntax gate, measured

The DIM-SYN closure (the `syntax-gate` CI job) turned out to be a
measurement instrument in its own right. The job pins both directions —
every shipped diagram must pass `plantuml -checkonly` (pinned jar), and a
deliberately broken probe must fail it *and* be forced to Level 1 by the
C2 cap — and its first runs overturned two predictions:

- **PlantUML accepts all fifteen shipped diagrams, including the three
  bad examples with unclosed `alt`/`while`.** The original design used
  those files as the failure-direction probes; the grammar turned out to
  tolerate unterminated blocks entirely.
- **The leniency runs deeper than that.** A dangling `Alice ->` also
  passes `-checkonly`. Of the probed breakages, only a structural parser
  error (`class {`) and a preprocessor error (`!undefined_function()`)
  were rejected. The job pins `class {` as its probe — verified end to
  end on the runner: `syntaxOk=false`, level forced to 1 — and logs the
  candidate matrix on every run so a future, still more lenient PlantUML
  is easy to re-pin.

The takeaway inverts the caveat the job was built to close. The worry was
that pumllint's parser vouches for syntax without a render; the
measurement shows the sharper fact: **SEQ004/ACT004 are stricter than
PlantUML's own grammar** on exactly the constructs the maturity model
cares about. Grammar checking alone would bless every deliberately broken
example in this repository. The two layers guard different things —
`-checkonly` catches what will not render, the linter catches what will
not *mean* — and the maturity model needs the second even where the first
is silent.

## Verdict

Sense, decisively — on a sample of one. The default profile flagged
exactly the deliberate style deviations and nothing else; severity, gating
and the suppression round-trip behaved like a tool meant for CI; and the
weak spots found were scoping choices (a signature heuristic since
tightened, craft-not-truth) rather than false positives. The findings
above doubled as a to-do list, not a disclaimer: two shipped as product
changes, a third closed as a CI gate whose first runs produced findings of
their own (previous section), and the fourth closed by declaring the
governance conventions in the repository's own config.
