# The Mermaid ecosystem, re-examined — the linters, executed

*Dated evaluation, 2026-08-30, written against `14ff865` (v0.30.0).
Thirty-second in the series, and the **second re-examination** after the
BPMN one (twenty-second). The Mermaid ecosystem was settled sixth
(2026-08-27, `f806dce`); that note is not re-opened. This one does the
thing it said it had not done.*

**Verdict up front: the settlement is unchanged, and — unlike the BPMN
re-examination — the convergence claim SURVIVES execution. One table row
is corrected, and four things reading could not see are added, one of
which sharpens the convergence rather than weakening it.**

**Why it ran, in the sixth note's own words:**

> **No Mermaid tool was executed** — neither linter was installed or run,
> so the rule mapping in §3 is read from published rule descriptions, not
> from paired runs against equivalent diagrams.

and its recorded candidate 2:

> **The convergence record (§3.1)** … worth re-checking if
> `mermaid-lint`'s rule set grows, **especially if it grows upward into a
> graded verdict**, which is the one change that would end the
> seven-ecosystem streak from the closest possible range.

**This turn discharges that instruction.** The BPMN re-examination
established what happens when this series reasons from a tool's
description instead of its behaviour — three published claims were wrong,
one central. Mermaid is the other note that said, in writing, that it had
not run the tool.

**The answer to candidate 2: the rule set has NOT grown** — same version,
0.53.1, unchanged since 2026-08-13 — **and it has NOT grown into a graded
verdict.** The streak stands, now confirmed by execution rather than by
reading a feature list.

*Bounds. **`@mermaid-lint/cli` 0.53.1 and `@probelabs/maid` 0.0.29 were
installed from npm and EXECUTED**; every finding, exit code and summary
line below is a run. Corpus is six hand-written Mermaid files plus one
Markdown file with a fence. Per session scope **no GitHub repository was
read**, so the sixth note's stated cost — maintenance status, issue
activity, star counts, source-level rule implementations — is still
unpaid, and nothing here speaks to it. `probelabs.com/maid` was not
re-fetched. No claim is made about either tool's adoption.*

## 1. What held — the rule inventory, verified by execution

The sixth note listed `mermaid-lint`'s semantic rules from its
documentation. **All of them fire, with names matching the descriptions.**

| Claimed (read) | Executed | Severity |
|---|---|---|
| legacy `graph` keyword | `prefer-flowchart` | warning |
| flowchart lacking a direction | `require-direction` | warning |
| duplicate edges | `no-duplicate-edges` | warning |
| self-looping edges | `no-self-loop` | warning |
| empty labels | `no-empty-labels` | warning |
| activations without deactivations | `no-activate-without-deactivate` | warning |
| duplicate class methods | `no-duplicate-methods` | warning |
| duplicate node IDs | `duplicate-ids` | **error** |

Eight for eight. **The sixth note read the inventory correctly** — which
is worth saying plainly, because the BPMN precedent predicted otherwise
and the prediction was wrong here.

The table's other rows also hold under execution: `--format json` emits a
structured report (`version`, `files`, `diagrams`, `ok`, `warnings`);
`--fix` exists; **Markdown fences are linted**, with line numbers pointing
into the fence (`md/doc.md:6:1`, `:7:1`).

## 2. What was wrong — the suppression syntax

The sixth note's table records:

| Suppression | `%% mermaid-lint-disable <rule>` |

**Executed, that form is rejected**:

```
$ mermaid-lint mmd/supp.mmd          # '%% mermaid-lint-disable no-self-loop'
mmd/supp.mmd:3:1: warning: no-self-loop: node `A` has an edge to itself …
mmd/supp.mmd:1:1: warning: suppression-malformed: suppression directive needs
    a reason, e.g. `%% mermaid-lint-disable-next-line duplicate-ids: ids collide upstream`
```

**The rule still fired**, and a second warning was added for the
malformed directive. The working form needs `-next-line` *and* a reason:

```
$ mermaid-lint mmd/supp2.mmd
  %% mermaid-lint-disable-next-line no-self-loop: intentional retry edge
checked 1 diagram in 1 file — all valid                                (exit 0)
```

A documentation-derived detail, wrong in practice, and the kind only a run
finds. §5 is why it matters beyond the correction.

## 3. What reading could not see

### 3.1 The severity ordering — and it sharpens the convergence

Of eight semantic rules, **exactly one is `error`: `duplicate-ids`.** It
is the only semantic finding that exits 1; every other warns at exit 0.

The sixth note mapped duplicate node IDs to **the XD identity family** —
correctly, from the rule's name. What it could not see is that
`mermaid-lint` **rates identity above everything else it checks**, as the
one semantic defect worth failing a build over.

**That is a stronger convergence than the note claimed**, and it is now
the third instance of the same shape in this series: `bpmnlint`'s
`no-duplicate-sequence-flows`, Spectral's `path-params` as its lone
`error` among six warnings, and now `duplicate-ids`. **Independent tools,
four artefact classes, all rating identity-and-consistency as the thing
that stops a build.**

### 3.2 `--no-semantic` is a first-class CLI toggle

```
--no-semantic      Disable all semantic rule checks (e.g. duplicate node IDs).
```

The sixth note observed that `mermaid-lint`'s documentation distinguishes
semantic rules from syntax checking, and called that *"word for word,
this project's founding distinction"*. **The distinction is not only
documentation — it is a switch.** A user can turn the semantic layer off
and keep the parser. That is a firmer version of the same observation.

`--strict` ("Exit 1 if any warnings are present") is the `--fail-on`
analogue, absent from the sixth note's table.

### 3.3 The two incumbents disagree about what fails a build

Same file, `graph` with no direction:

```
mermaid-lint:  exit=0        # warning: require-direction
maid:          exit=1        # error [FL-DIR-MISSING]
```

**The niche the sixth note called occupied is occupied by two tools that
do not agree on severity for the same defect.** That does not reopen the
refusal — an occupied niche is occupied either way — but it is a more
accurate picture than "two incumbents hold the niche", and it is the kind
of thing that only shows up when both are run on the same input.

### 3.4 `maid` is considerably more than the note's dashes

The sixth note's table gave `maid` `—` for config, severities and
suppression, from npm metadata alone. Executed, it has `--format
text|json`, `--fix[=all]`, `--dry-run`, `--include`/`--exclude`,
`--no-gitignore`, a `--strict` mode meaning something different from
`mermaid-lint`'s (*"require quoted labels inside shapes"*), a **coded
rule taxonomy** (`FL-DIR-MISSING`), and a `render` subcommand that
produces SVG/PNG.

The dashes were honest — the note said they came from npm metadata — but
they understated the tool.

## 4. The no-grader claim, executed for both

```
$ mermaid-lint --help | grep -iE "score|grade|level|aggregate|rating"
(nothing)

$ mermaid-lint mmd/flow.mmd
checked 1 diagram in 1 file — all valid, 5 warnings

$ maid mmd/dir.mmd --format json
{ "file": "…", "valid": false, "errorCount": 1, "warningCount": 0, "errors": [ … ] }
```

Counts, a per-diagram boolean, and nothing else. **The sixth note's
"none found" for `maid` is now "none, confirmed by execution"**, and
candidate 2's specific worry — that the rule set might grow *upward into
a graded verdict* — has not happened.

## 5. The suppression discipline — where §2's correction leads

`mermaid-lint` **requires a justification at the suppression site** and
warns when one is missing. pumllint does not:

```plantuml
' pumllint: disable=SEQ006, unlabelled-message   ← next line only
```

**But it is not laxer — it answers the same worry somewhere else, and the
somewhere else is the aggregate.** From this project's README:

> Suppressed findings never vanish silently from maturity scores:
> `pumllint score` annotates every affected diagram — `100/100 (3
> suppressed)` — and the JSON report carries a `suppressedCount`… CI can
> audit what is being suppressed by running with `--no-suppressions`.

Two independent answers to *"don't let suppressions hide"*:
`mermaid-lint` demands the reason **where the suppression is written**;
pumllint makes the suppression **visible in the score and auditable in
CI**.

**And this is a use of the aggregate the series has not recorded before.**
Thirty-one notes have treated the maturity model as a grading feature
that no competitor builds, cited two-sided. Here it does a second job:
`100/100 (3 suppressed)` is not a grade, it is a **disclosure channel**
that only exists because there is an aggregate to annotate. A tool with
no score has to put the discipline in the comment syntax instead. Neither
is wrong; they are the same requirement solved at different layers.

## 6. Decision

**Unchanged. No Mermaid support; the sixth note's four grounds, its
never-builds and its three recorded candidates all stand.**

**Recorded, not queued:**

1. **Candidate 2 is discharged for this cycle** (§4) — rule set unchanged
   at 0.53.1, no graded verdict, streak intact. The re-check instruction
   should stay: it is a good trigger and it worked.
2. **The identity-severity pattern (§3.1)** — third instance, now across
   four artefact classes. Worth citing alongside the convergence record;
   it is a sharper claim than "the catalogues overlap".
3. **The suppression-discipline contrast (§5)** — and specifically the
   observation that **the aggregate does double duty as a disclosure
   channel**. New to the record, and it belongs beside the two-sided
   grading caution rather than inside it.
4. **The sixth note's table row for suppression is corrected** (§2)
   inline in that note.

**Nothing here reopens the refusal**, and §3.3 is the one finding that
could be misread as doing so: two incumbents disagreeing about severity
is still two incumbents.

## Related reading

- [The Mermaid ecosystem, evaluated](mermaid-ecosystem-evaluation.md) —
  the sixth note, whose bounds and candidate 2 this one discharges.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md) — the
  first re-examination, and the precedent for running what a note only
  read. Its outcome was three corrections; this one's is one.
- [The Spectral / OpenAPI ecosystem, evaluated](spectral-openapi-ecosystem-evaluation.md)
  — `path-params` as the lone `error`, which §3.1 turns into a pattern.
