# The TLA+ / Alloy ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-30, written against `f4b8026` (v0.30.0).
Thirty-first in the series. TLA+ and Alloy are **already settled in this
repository** — the 2026-08-02 model-verification evaluation triaged them
as proposed alternatives and the ROADMAP records the verdict. Nothing
here re-opens that. This note asks the question that one did not: it
examined **sequence** diagrams and three named ambitions; the artefact
class where formal methods actually overlap this tool is the **state
diagram**, and that surface has never been measured.*

**Verdict up front: no adoption, unchanged — and the contribution is a
precisely located frontier plus one candidate the record has never
considered.**

**The bound first, because it governs everything.** TLA+ and Alloy were
**not run**. `tla2tools` is absent from Maven Central, `org.lamport`
returns nothing, and neither PyPI nor npm carries either tool; their
distributions come from GitHub releases, which this session's scope keeps
me from — the same wall that stopped OPA one note ago. **Every claim
below about what a model checker would compute is read, not executed, and
nothing in the verdict rests on one.** What *is* executed is the pumllint
side, which is where this note's substance lives.

**What was measured.** pumllint already computes a graph property on
state machines — STA002, `unreachable-state`. Three cases:

| Case | pumllint | Correct? |
|---|---|---|
| `Orphan` with **in-degree 0** | **STA002 fires** | ✔ |
| **Disconnected island** — `Stale ⇄ Archived`, neither reachable from `[*]` | **silent, exit 0** | the states *are* dead |
| **Sink** — `Wedged` entered, never left, never `[*]` | **silent, exit 0** | judgement (§4.2) |

**And the second row is not a gap.** STA002's docstring says *"In-degree
only: a cycle disconnected from `[*]` is not reported (there is no
reachability traversal)"*, and RULES.md says the same in its own words.
**The limitation is deliberate and documented twice.** I built the island
case expecting a name-versus-behaviour mismatch of the SEQ105 kind and
found instead a line the project drew on purpose — which makes the
interesting question *where the line sits*, not whether it was noticed.

**The contribution is a distinction the record does not yet draw.** The
2026-08-02 note rejected deadlock-freedom as **a category error** —
*"PlantUML defines no concurrency semantics, so the check would verify
its own invention"*. That is right, and it is about **sequence**
diagrams. A **state machine's transition graph is exactly what the
notation declares**: `[*] --> Idle`, `Idle --> Running`. Asking whether a
state is reachable from `[*]`, or whether a path to `[*]` exists, invents
**no semantics at all** — it is a traversal of declared edges, and
STA001 already guarantees exactly one initial transition to start from.
**The category error and its look-alike need separating, or the correct
rejection of one will be read as covering the other.**

## 0. What is already settled, restated so nothing is re-derived

`docs/model-verification-evaluation.md` (2026-08-02) triaged an
externally proposed move "beyond linting into verifying the models
themselves", naming TLA+ and Alloy as the honest alternatives. The
adopted verdict, quoted from the ROADMAP:

- ***Matching returns*** is shipped linting (SEQ003/009/104/108); the
  semantic remainder is the specced, decidable SEQ202.
- ***Deadlock-freedom* is a category error** — "PlantUML defines no
  concurrency semantics, so the check would verify its own invention: the
  no-oracle shape the obligation/flow settlement already rejects. Honest
  verification is cross-artifact (trace, XD, the recorded seq↔contract
  item) plus the Arc D measurement — never intra-diagram proofs over
  imposed semantics."
- ***Rule-set consistency***: joint satisfiability "is witnessed
  constructively by the corpus's clean probes under golden enforcement,
  **with no parallel Alloy formalization to drift**."
- ***Well-formedness as a type*** is the anti-goal.

**All four stand. None is reopened here.** What none of them touches is
the state-diagram pack, because the proposal that prompted that note was
about sequence interactions.

## 1. The ecosystem, and why this section is short

TLA+ is a specification language with a model checker (TLC) and a proof
system; Alloy is a relational modelling language with a SAT-backed
analyzer that finds counterexamples within a bounded scope. Both make
**reachability their first primitive**: you write a state relation and
ask what states the system can get into, then assert invariants and
temporal properties over that.

That is the entirety of what this note needs from them, and it is
uncontroversial. **Neither tool was executed** (see the bound above), so
this section makes no claim about their behaviour, performance,
ergonomics or current versions. Any note that tried to say more from
here would be doing what the BPMN re-examination corrected.

**The overlap worth examining is therefore not "should pumllint be a
model checker" — that is settled — but "pumllint already computes one
graph property; where exactly does it stop, and is that the right
stop?"**

## 2. The frontier, measured

All three diagrams are well-formed state machines with a title and a
single `[*] -->` initial transition, so STA001 and STA003 are satisfied
and STA002 is the only rule in play.

### 2.1 In-degree zero — caught

```
[*] --> Idle
Idle --> Running : start
Running --> [*] : done
Orphan --> Idle : never fires
```
```
indegree.puml:6: [STA002/major] State 'Orphan' has no incoming transition
```

### 2.2 Disconnected island — silent, and deliberately so

```
[*] --> Idle
Idle --> Running : start
Running --> [*] : done
Stale --> Archived : sweep
Archived --> Stale : revive
```
```
✔ No issues found.                                                (exit 0)
```

`Stale` and `Archived` each have in-degree 1, so the local test passes.
**Neither is reachable from `[*]`.** Both are dead model content in
exactly the sense STA002's rationale describes — *"typically a leftover
from refactoring"* — and both are missed.

The implementation is four lines and says why:

```python
targeted = {t.target for t in diagram.transitions if t.source != t.target}
for s in diagram.states.values():
    if s.name not in targeted:
        yield self.violation(...)
```

with the docstring: *"In-degree only: a cycle disconnected from `[*]` is
not reported (there is no reachability traversal)."* **RULES.md states
it a second time.** This is a documented boundary, not an oversight, and
§3 is about whether it is in the right place — not about whether anyone
noticed.

### 2.3 Sink — silent, and unexamined anywhere in the record

```
[*] --> Idle
Idle --> Running : start
Running --> Wedged : fail
```
```
✔ No issues found.                                                (exit 0)
```

`Wedged` can be entered and never left; no path from it reaches `[*]`.
Unlike §2.2, **this case appears nowhere** — not in RULES.md, not in the
ROADMAP, not in any rule's rationale. There are exactly three STA rules,
all implemented, and none is about termination.

**That is not a gap either** — nothing ever claimed to catch it — but it
is a candidate the record has never weighed, which is different from one
it weighed and declined.

## 3. Is the line in the right place?

The cost argument for staying local is weaker than it looks. Transitive
reachability here is a breadth-first walk over `diagram.transitions` from
the target of the `[*]` transition — a few lines, stdlib only, linear in
the graph, and **STA001 already guarantees exactly one place to start**.
It invents no semantics: the edges are the ones the author wrote.

Three honest arguments for the line as drawn, none decisive on its own:

**It changes the shape of a finding.** STA002 reports *a state*. An
island is a property of *the model*, and the natural report is "these
three states are unreachable", which is a different report shape and a
different severity conversation.

**Work-in-progress diagrams legitimately have islands.** A state machine
being drafted, or one split across `!include` files, will show
disconnected fragments that are not defects. In-degree zero is a much
safer signal for a rule that fires by default at `major`.

**It is the honest edge of "lint the source".** The strongest version of
the 2026-08-02 reasoning is not about concurrency specifically — it is
that a linter reports what the source *says*, and each step of inference
away from that is a step toward verifying an imposed model. A traversal
is a small step, but it is a step.

**Against all three**: the rule is *named* `unreachable-state`, its
rationale is *"dead model content"*, and §2.2's island is dead model
content that the rule's own name promises to find. The documentation
resolves the contradiction by disclosure rather than by behaviour, which
is honest but is not the same as the property being unwanted.

**This note does not settle it.** It records the question with the
measurement attached, which is what was missing.

## 4. The distinction worth carrying forward

### 4.1 The category error, precisely scoped

"Prove these interactions deadlock-free" fails because **PlantUML's
sequence diagrams have no concurrency semantics** — no scheduler, no
channel model, no fairness. Any deadlock verdict would be over semantics
the checker itself supplied. That reasoning is exact and it is scoped to
its premise.

### 4.2 The look-alike, which is not the same thing

"Does this state machine have a path to `[*]`?" **needs no supplied
semantics.** The transition graph is declared verbatim; `[*]` is declared
verbatim; STA001 already treats the initial marker as authoritative. The
question is graph traversal, not model checking, and it is decidable from
the source in linear time.

**But whether a sink is a *defect* is a separate judgement, and the
answer is not obviously yes.** An absorbing terminal state — a `Failed`
or `Cancelled` state deliberately drawn without a transition to `[*]` —
is a legitimate modelling choice. A rule here would need either an
opt-in, or a project convention that termination is always spelled
`--> [*]`. STA001's insistence on exactly one initial marker suggests
this project does treat `[*]` as canonical, but *requiring every path to
reach it* is a stronger claim than anything currently shipped.

**So: decidable, yes; desirable, unestablished.** Keeping those two apart
is the point of this section, because "deadlock-freedom is a category
error" is a settled sentence that could easily be quoted to close a
question it does not actually reach.

## 5. Boundaries

1. **Declared graph vs supplied semantics.** §4. The real line, and it
   falls in a different place for state diagrams than for sequence
   diagrams.
2. **Local predicate vs traversal.** §2.2. Where the implementation
   currently stops, on purpose and in writing.
3. **Decidable vs desirable.** §4.2.
4. **Artefact class.** A `.tla` or `.als` file is a specification in its
   own language with its own tooling; nothing in this series suggests
   reaching for it, and the 2026-08-02 note settled the direction.

## 6. Sense and nonsense

**S1. The project had already drawn this line and written it down twice**
(§2.2). Finding documentation where I expected a defect is the correct
outcome and worth recording as such.

**S2. The category error and its look-alike are genuinely different**
(§4), and separating them protects a good settled sentence from being
over-applied.

**S3. The sink case is unexamined rather than declined** (§2.3) — a
smaller claim than "gap", and the accurate one.

**N1. "Deadlock-freedom is a category error, therefore no graph analysis
on state machines."** The quotation is right and the inference is not.
§4 exists for this.

**N2. "STA002 is broken / misnamed."** It is documented, twice, in the
terms it actually implements. Reporting it as a defect would be the
Gherkin note's lesson inverted — mistaking a stated convention for an
error.

**N3. "Add a reachability rule because it is cheap."** Cheapness is not
demand. §3 lists three real arguments for the current line and does not
resolve them; a build on this evidence would be premature.

## 7. Fit — graded

| Fit | Verdict |
|---|---|
| **F1** — read or lint `.tla` / `.als` | **No.** Boundary 4; direction settled 2026-08-02. |
| **F2** — deadlock / liveness proofs over sequence diagrams | **No — category error.** Settled; not reopened. |
| **F3** — transitive reachability on state diagrams (upgrade STA002, or a sibling rule) | **Recorded, not queued.** §3's question, now with a measurement. The documented in-degree limitation is the thing to revisit, and the report-shape and WIP-diagram arguments are the ones to answer first. |
| **F4** — a path-to-termination rule (the §2.3 sink) | **Recorded, not queued, and weaker than F3.** Decidable (§4.2); desirability unestablished; would need opt-in or a stated convention. **New to the record.** |

**Neither F3 nor F4 is proposed as a build.** Both are recorded so that
the next person to ask "why doesn't it catch this?" finds the measurement
and the arguments rather than re-deriving them.

## 8. SWOT

**Strengths**

- The frontier is documented where it falls (§2.2) — disclosure rather
  than silence, which is the same discipline as the `.bpmn` "nothing was
  checked" warning.
- The 2026-08-02 settlement is sound and survives contact; §4 sharpens
  its scope rather than weakening it.

**Weaknesses**

- **`unreachable-state` reports in-degree**, and the gap between the name
  and the behaviour is closed by documentation rather than by the rule.
  Defensible, disclosed, and still a thing a reader can be surprised by.
- The sink case (§2.3) has never been weighed.

**Opportunities**

- None external. TLA+ and Alloy are not a market this project enters;
  §7's items are internal.

**Threats**

- **Over-quotation of "category error"** (N1) — the single most likely
  misuse of the existing record, and the reason §4 is written.

## 9. Decision, recorded candidates, triggers

**Decision: unchanged. No `.tla`/`.als` support, no proofs over imposed
semantics, and the 2026-08-02 verdict stands in full. Two internal
candidates recorded, neither queued.**

**Never build:**

- Reading or linting `.tla` / `.als` (F1).
- Deadlock or liveness proofs over sequence diagrams (F2) — the category
  error, settled.
- Any check whose verdict depends on semantics PlantUML does not define.

**Recorded, not queued:**

1. **F3 — transitive reachability on state diagrams.** §2.2 and §3. The
   in-degree limitation is documented; this records the *measurement*
   and the three arguments for the current line, so the question is
   answerable rather than re-derivable.
2. **F4 — path-to-termination (the sink).** §2.3, §4.2. Decidable
   without invented semantics; desirability unestablished; new to the
   record.
3. **The category-error scoping (§4)** — cite the 2026-08-02 sentence
   with its premise attached, exactly as the decision-table result is
   cited with its suite scoping and the no-grader observation with its
   counter-reading.

**Re-litigate on:**

- An adopter reporting a disconnected island or a wedged state that
  pumllint passed — which would supply the demand F3 and F4 both lack.
- TLA+ or Alloy becoming runnable through a package registry, if the
  ecosystem half is ever wanted at the standard the rest of the series
  holds.
- Nothing else. The 2026-08-02 triggers are unchanged.

## Related reading

- [Model verification beyond linting](model-verification-evaluation.md) —
  the settled evaluation this note does not reopen; §4 scopes its
  "category error" finding rather than qualifying it.
- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md) — where
  "the properties that matter are decidable, and belong to a solver" was
  recorded; §4.2 is the case where the property is decidable *and* stays
  on this side of the line.
- [The policy-as-code ecosystem, evaluated](policy-as-code-ecosystem-evaluation.md)
  — the previous note, and the previous instance of an engine that could
  not be run here.
