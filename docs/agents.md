# Using pumllint from a coding agent

*Audience: AI coding agents that receive PlantUML diagrams as
specification input — and the engineers who configure them (AGENTS.md,
CLAUDE.md, Kiro steering files, custom harnesses). Everything below uses
shipped, schema-pinned interfaces; there is no agent-specific mode in the
tool. A paste-ready instruction block for your agent configuration is at
the end.*

## Why a diagram gate belongs in your loop

The measured result behind this page ([EVIDENCE.md](../EVIDENCE.md)):
diagrams below maturity Level 2 cost roughly 21 percentage points of
*executed* correctness in code generated from them — about one intended
behavior in three failing when the code runs, versus one in ten above —
across three generator models from two vendors. And the effect is
**scaffold-resistant**: better prompting lifted moderately untidy
diagrams to near-pristine results but never rescued below-cliff ones,
because no prompt can restore decision rules the diagram does not
contain. The only repair that works is repairing the diagram — which is
a loop an agent can run mechanically, before writing any code:

**score → read the gap report → repair what you may → re-score →
implement.**

The gate is an evidence-backed **risk filter**: its demonstrated value
is keeping low-maturity diagrams out of generation. It is not a
guarantee of faithful output (see the honesty section at the end).

## The loop

pumllint is a zero-dependency CLI (`pip install pumllint`, Python
≥ 3.11); every step below is a subprocess call with stable exit codes
and JSON output pinned by shipped schemas (`pumllint schema lint`,
`pumllint schema score`).

One rule before any flags: **if the repository has a pumllint config**
(`pumllint.toml` / `.yaml` / `.json`, auto-detected), run within it and
do not override severities, rule options or profiles ad hoc — those are
the project's decisions, not yours.

### 1. Score before you implement

```sh
pumllint score diagrams/ --profile codegen -f json -o score.json
pumllint score diagrams/ --min-level 2      # exit 1 below Level 2
```

Use `--profile codegen` whenever the diagrams feed code generation: the
SEQ101–SEQ109 pack checks exactly whether a sequence diagram can be
implemented *without inventing missing details*, and Level 5 cannot be
reached without it. Exit codes are CI-grade: `0` pass, `1` gate failed
or findings at/above threshold, `2` usage error.

### 2. Read the machine-readable gap report

`score -f json` returns `{diagrams: [...], modelSet: {...}}`. Each
diagram's `maturity` carries `level`, `levelName`, `score`, per-dimension
scores, and — the part built for you — `gapReport`: an ordered list of
exactly what blocks the next level, each entry with the threshold that
failed (`current` vs `required`) and the concrete `findings` behind it
(`ruleId`, `severity`, `message`, file and line). `pumllint -f json`
(lint mode) returns the flat findings list with the same fields. The
gap report is a to-do list, not a grade — work it top-down.

### 3. Repair — two kinds of finding, two different rules

| Kind | Examples | What you do |
|---|---|---|
| **Mechanical** — the correct content is already determined | missing title (GEN001), unnamed diagram (GEN002), undeclared participant (SEQ001/SEQ101) | `pumllint fix diagrams/` — deterministic, idempotent, never invents |
| **Content-bearing** — the diagram is missing a decision | vague guard (SEQ105), prose message label (SEQ103), missing failure path (SEQ107), elision marker `...`/`TBD` (SEQ106), missing multiplicity (CLS002) | **Ask.** List the findings with file:line, propose candidate resolutions, and get the missing decisions from the diagram's author or your user |

Structural findings in between (unbalanced activations, unterminated
blocks, missing return arrows) are yours to fix only where the diagram
itself already determines the answer; where naming or intent is needed
(what does the call return?), treat them as content-bearing.

The dividing line is the same covenant the auto-fixer follows: *the
linter tells you what, but will not guess which* — and neither should
you. A guard you invent inside the diagram is worse than one invented in
code, because it now looks specified. Silent fabrication is precisely
the failure mode the measured cliff quantifies (below-cliff diagrams
roughly double the generator's invented business logic).

### 4. Never suppress your way through the gate

Inline `' pumllint: disable=…` comments exist so *humans* can mark
reviewed, genuinely-intended exceptions. Do not add them to make a gate
pass. The tool discloses suppression: every affected diagram and the
model set carry a `suppressedCount`, reports annotate it
(`100/100 (3 suppressed)`), and CI can audit with `--no-suppressions`.
A suppression you add to dodge a finding will be visible — and defeats
the input filter you are part of.

### 5. Re-score, then implement — and stay inside the diagram

Re-run step 1. Implement only once the gate passes, and implement what
the repaired diagram specifies. Where the diagram remains silent after
step 3, leave the gap visible (a `NotImplementedError`, a TODO naming
the missing decision, a note in your summary) rather than filling it —
per the evidence, filled-in gaps read as specified behavior to every
reviewer downstream.

Level thresholds worth knowing: **Level 2** is the evidence-backed
floor (the cliff sits below it); **Level 5** means *method-convention
complete* — the diagram-side preconditions for faithful generation are
met. It is deliberately not called "generation-ready": a sequence
diagram underdetermines an implementation even at Level 5.

## When you author diagrams

If your instructions have you *drawing* PlantUML (steering files
telling agents to document designs as diagrams are common), run the same
loop on your own output: author, then
`pumllint score <file> --profile codegen`, then repair until the gate
passes — asking your user for any content-bearing decision you had to
leave open. `pumllint --list-rules` enumerates every check. A diagram
you hand over below the gate is a diagram some other agent will later
implement wrongly.

## Drop-in block for your agent configuration

Paste into AGENTS.md, CLAUDE.md, a Kiro steering file, or your harness
prompt; adjust paths:

```text
When PlantUML diagrams are the specification for code you generate:

1. Gate the inputs first:
     pumllint score <diagrams> --profile codegen -f json -o score.json
   Read each diagram's maturity.gapReport. Do not implement from any
   diagram below Level 2.
2. Apply the deterministic repairs: pumllint fix <diagrams>.
3. For findings that need content the diagram does not contain (vague
   guards, prose message labels, missing failure paths, "..."/"TBD"
   markers, missing multiplicities): list them with file:line, propose
   candidates, and ask for the missing decisions. Never resolve them
   silently — not in the diagram, not in the code.
4. Never add pumllint suppression comments to pass a gate.
5. Re-run the score. Implement only what the repaired diagram
   specifies; where it stays silent, leave the gap visible instead of
   filling it.
```

## What is measured, and what is not

Measured ([EVIDENCE.md](../EVIDENCE.md)): maturity scores correlate
with generation fidelity, and the below-Level-2 cliff — ~21 pp of
executed correctness, invented logic roughly doubling — is
oracle-robust, vendor-robust and prompt-robust. That is the case for
gating your inputs.

Not measured: that an agent following this recipe end-to-end produces
better code than one that does not. The recipe operationalizes a
measured *input-side* effect; the interventional claim (repair per the
gap report → outcomes improve) is the mechanism the evidence points at,
stated here as exactly that — a mechanism, not a measured result.

Related reading: [understanding findings and
scores](findings-and-scores.md) (what each finding means),
[setup & CI integration](setup-and-ci.md) (gates, ratchet, hooks in
pipelines), [SCORING.md](../SCORING.md) (the maturity model itself).
