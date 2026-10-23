# pumllint gate results

pumllint 0.34.0, run from kit/ on 2026-10-23T10:59:18Z.

## 1. Lint: `pumllint uml --fail-on info -c pumllint.toml`

```
✔ No issues found.
exit code: 0
```

## 2. Score: `pumllint score uml --min-level 5 -c pumllint.toml`

```
uml/basis_and_adjustment.puml [basis_and_adjustment]: Level 5 (Method-complete) — 100/100

uml/component.puml [component]: Level 5 (Method-complete) — 100/100

uml/daily_chain.puml [daily_chain]: Level 5 (Method-complete) — 100/100

uml/data_model.puml [data_model]: Level 5 (Method-complete) — 100/100

uml/series_state.puml [series_state]: Level 5 (Method-complete) — 100/100

uml/status_run.puml [status_run]: Level 5 (Method-complete) — 100/100

uml/sync_leg.puml [sync_leg]: Level 5 (Method-complete) — 100/100

uml/sync_run.puml [sync_run]: Level 5 (Method-complete) — 100/100

Model set: Level 5 (Method-complete) — 100/100 weighted across 8 diagram(s)

Syntax gate: not run — DIM-SYN unchecked; Level verdicts assume valid syntax (enable with --check-syntax or scoring.syntax_gate).
exit code: 0
```

## 3. Trace: `pumllint trace uml --requirements requirements.json --features features --fail-on-uncovered --fail-on-unverified -c pumllint.toml`

```
✔ Requirement coverage: 158/158 covered across 8 diagram(s)
✔ Verification: 158/158 modelled requirement(s) referenced by a feature file across 11 feature file(s), 95 scenario(s)

(158 per-requirement lines, each '✔'; first three:)
JDL-001  ← uml/component.puml [component]:72, uml/sync_run.puml [sync_run]:54  ✔ features/sync.feature [The sync ritual - selection, windows, ordering, containment and reporting] (The packaged universe expands into nine ordered legs:7),
JDL-002  ← uml/data_model.puml [data_model]:230  ✔ features/universe.feature [The declarative universe - grammar, normalisation and refusals] (Defaults, dates and the class map normalise into one shape:30)
JDL-003  ← uml/data_model.puml [data_model]:230  ✔ features/universe.feature [The declarative universe - grammar, normalisation and refusals] (Defaults, dates and the class map normalise into one shape:30)
exit code: 0
```

Unverified/uncovered lines in the full trace output: 158 requirement lines, 0 without a tick.

## Closing round (revision 2026-10-23), run 2026-10-23T11:52:34Z

Lint (`pumllint uml --fail-on info -c pumllint.toml`), exit 0:
```
✔ No issues found.
```
Score (`pumllint score uml --min-level 5 -c pumllint.toml`), exit 0:
```
uml/basis_and_adjustment.puml [basis_and_adjustment]: Level 5 (Method-complete) — 100/100
uml/component.puml [component]: Level 5 (Method-complete) — 100/100
uml/daily_chain.puml [daily_chain]: Level 5 (Method-complete) — 100/100
uml/data_model.puml [data_model]: Level 5 (Method-complete) — 100/100
uml/series_state.puml [series_state]: Level 5 (Method-complete) — 100/100
uml/status_run.puml [status_run]: Level 5 (Method-complete) — 100/100
uml/sync_leg.puml [sync_leg]: Level 5 (Method-complete) — 100/100
uml/sync_run.puml [sync_run]: Level 5 (Method-complete) — 100/100
Model set: Level 5 (Method-complete) — 100/100 weighted across 8 diagram(s)
Syntax gate: not run — DIM-SYN unchecked; Level verdicts assume valid syntax (enable with --check-syntax or scoring.syntax_gate).
```
Trace (`pumllint trace uml --requirements requirements.json --features features --fail-on-uncovered --fail-on-unverified -c pumllint.toml`), exit 0:
```
✔ Requirement coverage: 162/162 covered across 8 diagram(s)
✔ Verification: 162/162 modelled requirement(s) referenced by a feature file across 11 feature file(s), 98 scenario(s)

JDL-159  ← uml/component.puml [component]:67  ✔ features/cli.feature [The command-line surface and its argument errors] (Exporting a series the store does not hold ends in pandas' own AttributeError:42)
JDL-160  ← uml/component.puml [component]:67  ✔ features/cli.feature [The command-line surface and its argument errors] (Parser errors print the failing parser's usage and one error line:54, Every --help prints its verbatim text and exits 0:70)
JDL-161  ← uml/component.puml [component]:67  ✔ features/cli.feature [The command-line surface and its argument errors] (Parser errors print the failing parser's usage and one error line:54)
JDL-162  ← uml/component.puml [component]:67  ✔ features/cli.feature [The command-line surface and its argument errors] (Every --help prints its verbatim text and exits 0:70)
```
