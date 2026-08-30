# The D2 ecosystem, re-examined — the compiler, executed

*Dated evaluation, 2026-08-30, written against `a35b605` (v0.30.0).
Thirty-third in the series and the **third re-examination**, after BPMN
(22nd) and Mermaid (32nd). The D2 ecosystem was settled seventh
(2026-08-27, `5b4a5a0`); that note is not re-opened. This one runs what
its bounds said had not been run.*

**Verdict up front: the refusal stands on grounds (1) and (2), which are
untouched. Ground (3) is CORRECTED — and the correction cuts against the
refusal, so it is worth being careful about exactly how far it goes.**

**Why it ran.** The bounds scan of 2026-08-30 classified the series'
unexecuted claims and picked D2 as the one worth acting on, because its
refusal rests partly on a claim about D2's *own* tooling. The seventh
note's bounds:

> **No D2 tool was executed** — `d2` was not installed, so nothing here
> reports what `d2 validate` actually accepts or rejects; its scope is
> characterized from documentation.

**A correction to the scan, before anything else.** That scan listed D2
as flatly *runnable*, on the strength of `npm view @terrastruct/d2
version` returning `0.1.33`. **That is registry presence, not
runnability.** `@terrastruct/d2` is **D2.js — a WASM wrapper library with
no `bin`**; the real `d2` CLI comes from `d2lang.com/install.sh`, which
fetches GitHub release assets. What the WASM build *does* expose is
`compile()`, which is exactly the accept/reject surface ground (3) turns
on. So D2 is **partly** runnable, and this note reports only that part.

*Bounds. **`@terrastruct/d2` 0.1.33 (D2.js, the WASM build of the D2
compiler) was installed from npm and EXECUTED**; every ACCEPTED/REJECTED
result below is a run. **The `d2` CLI was NOT run** — `d2 fmt`,
`d2 validate` as commands, exit codes and CLI ergonomics are still
uninspected, and nothing here is a claim about them. The compiler is the
same engine the CLI wraps, which is why the accept/reject surface
transfers; the CLI's *behaviour around* it does not. Seven hand-written
D2 inputs. Per session scope **no GitHub repository was read**, so the
seventh note's other stated costs — release cadence, issue activity, the
linter roadmap item's status — remain unpaid.*

## 1. What held

**Multiple errors from one broken program — confirmed.** The seventh note
cited "a parser that emits *multiple* human-readable errors from one
broken program". Given one input with two independent faults:

```
a -> : x
b: {
```
```
[{"errmsg":"index:1:1: connection missing destination"},
 {"errmsg":"index:2:4: maps must be terminated with }"}]
```

Two distinct entries, each with a line:column and a plain-English
message. The claim is accurate.

**The shape vocabulary is closed, and enforced.** `a.shape: not_a_real_shape`
is **rejected** — `unknown shape "not_a_real_shape"`. That is more than
syntax: D2 validates shape names against a fixed set. It does **not**
enumerate the set in the error, so the seventh note's careful hedge —
the shape list is *"bounded, not exact"*, and "one of five packs
transfers" is *a floor* — stands as written and could not be tightened
cheaply.

## 2. What was wrong — ground (3)

The seventh note's third ground, verbatim:

> **(3)** D2 already ships more language tooling than PlantUML does —
> `d2 fmt`, `d2 validate`, and a parser that emits *multiple*
> human-readable errors from one broken program — **so the gap that
> motivates this tool for PlantUML is narrower there before any semantic
> rule exists.**

The premise is right and **the conclusion does not follow.** Measured:

| Input | D2 compiler |
|---|---|
| `a -> b: request` / `b -> a: reply` | ACCEPTED |
| `a -> : request` (missing destination) | **REJECTED** — syntax |
| `a: {` unterminated | **REJECTED** — syntax |
| `a.shape: not_a_real_shape` | **REJECTED** — closed vocabulary |
| `a -> a: retry` (self-loop) | **ACCEPTED** |
| `a -> b: go` twice (duplicate connection) | **ACCEPTED** |
| `a -> b` (unlabelled connection) | **ACCEPTED** |

**D2 rejects malformed programs and unknown keywords. It accepts every
semantic defect tested.** On the equivalent PlantUML, pumllint reports:

```
eq.puml:5: [SEQ006/minor] Self-message on 'a' — consider a note or 'ref over' instead
eq.puml:8: [SEQ005/minor] Message a -> b has no label
```

**So the tooling D2 ships more of is *syntax and vocabulary* tooling. The
semantic gap — the one that motivates this project — is not narrower in
D2. It is the same size.** A D2 author gets better parse errors than a
PlantUML author and exactly as little help with a self-loop, an
unlabelled connection, or a duplicated one.

**Precision, because it matters:** of the three semantic defects D2
accepts, pumllint catches **two**. The duplicate connection is not a
single-file pumllint finding either — the XD family is cross-file — so
that row is a wash and is not evidence of a gap in D2's favour or
against it.

## 3. Which way the correction cuts

Ground (3) was a reason **not** to build. Correcting it **removes** that
reason, so the honest thing is to ask whether the refusal still holds.

**It does, on grounds (1) and (2), which this note does not touch:**

- **(1) D2 is not a UML notation.** Its shape vocabulary is
  presentational, sequence is the one pack with a verified counterpart,
  and four of five have none. Unchanged — and §1 confirms the shape set
  is closed, which if anything firms up the "presentational vocabulary"
  reading.
- **(2) The niche is unoccupied but claimed by upstream.** D2's roadmap
  reads *"Build a configurable linter."* Building it for them is the
  SonarQube-plugin lesson against a maintainer who has said they intend
  to do it. Unchanged, and **this is now the load-bearing ground.**

**What changes is the shape of the argument, not the verdict.** The
seventh note refused D2 partly because the need looked smaller there.
Measured, the need is the same size as PlantUML's; what stops the build
is that **someone else has announced they will meet it**, plus four packs
that do not transfer. That is a narrower and more honest basis, and it is
more fragile: **ground (2) is a statement about someone's intentions**,
and intentions lapse.

## 4. Boundaries

1. **Syntax/vocabulary vs semantics.** §2. D2's compiler is thorough on
   the first and silent on the second, exactly as PlantUML's is.
2. **Compiler vs CLI.** The WASM build answers what is accepted; it says
   nothing about `d2 fmt`, exit codes, or how the CLI reports. Stated in
   the bounds and not worked around.
3. **Notation class.** Ground (1), untouched.

## 5. Sense and nonsense

**S1. The seventh note's factual claims held; its inference did not.**
Multiple errors, closed vocabulary, more tooling — all correct. *"The gap
is narrower"* was the step too far.

**S2. This is the fifth self-correction of the same shape** — sound
measurement or sound premise, over-reaching conclusion — after the
viewpoint generalization, BPMN's ambiguity dimension, the ADR filename
claim and the Semgrep narrowing. **It recurs even when the underlying
facts are right**, which is what makes it worth naming as a habit rather
than a series of accidents.

**S3. The scan's own error is the same shape, one layer up** — "the
package resolves" inferred to "the tool runs". Caught within the hour,
and corrected in the scan entry before it merged.

**N1. "Ground (3) fell, therefore build a D2 pack."** No — §3. Grounds
(1) and (2) carry the refusal, and (2) is now doing most of the work.

**N2. "D2's compiler is weak."** It is not: it is a *compiler*, and it
does compiler things thoroughly. Expecting semantic linting from it is
the category error the seventh note itself avoided when it named the
roadmap item.

## 6. Decision

**Unchanged: no D2 support, no D2 pack. Grounds (1) and (2) stand;
ground (3) is corrected and withdrawn as a reason.**

**Recorded, not queued:**

1. **Ground (3) corrected** (§2), annotated inline in the seventh note in
   this turn.
2. **Ground (2) is now load-bearing, and it is the fragile one** (§3).
   D2 shipping its configurable linter would settle the question in this
   project's favour permanently; D2 *abandoning* that roadmap item would
   remove the second of three grounds and leave only ground (1). **That
   is the trigger to watch, and it is someone else's decision.**
3. **The CLI remains unrun** (bounds) — `d2 fmt`, exit codes, reporting.
   Not worth a third pass unless ground (2) moves.

## Related reading

- [The D2 ecosystem, evaluated](d2-ecosystem-evaluation.md) — the seventh
  note, whose ground (3) this corrects and whose grounds (1) and (2) it
  leaves standing.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md) and
  [The Mermaid ecosystem, re-examined](mermaid-ecosystem-reexamined.md) —
  the first two re-examinations; this is the third, and the first where
  the correction cuts *against* the refusal.
