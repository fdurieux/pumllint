# The BPMN ecosystem, re-examined — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `1089a99` (v0.30.0).
Twenty-second in the series. The BPMN **ecosystem** was evaluated fourth
(2026-08-27, `eee24ac`, v0.29.0); that note is not re-opened. This one
executes the measurement it explicitly deferred, and re-checks the two
follow-ups it recorded as needing re-checking.*

**Verdict up front: the settlement is unchanged — no BPMN support of any
kind, on the same four grounds. The contribution is measurement, and it
produces three corrections to the fourth note, one of them to its central
claim about the product boundary.**

**Why this could run now.** The fourth note's §8.4 said, of the
convergence argument that is the whole reason it was written:

> This note does not compare `bpmnlint`'s findings against pumllint's on
> equivalent processes — the convergence in §3 is read from rule names,
> documented rationales and this project's own catalog, not from paired
> runs. A paired run would be the honest way to claim the mapping is
> exact, and it would need a Node toolchain and a corpus of matched
> BPMN/PlantUML pairs that does not exist.

This session has Node v22.22.2 and reachable npm. The corpus does not
exist, so it was written: the same order process, expressed twice, in two
variants. **`bpmnlint` has now been executed.** The mapping is no longer
a reading.

**What the paired run returns. (1) Two of the three headline
correspondences hold exactly; the third does not.** `conditional-flows`
is **not** ACT003 — it is silent on a gateway with no conditions at all,
and fires only once conditions have been *started*. It checks
consistency; ACT003 checks completeness. **(2) The rule count was wrong,
and the error cost the note its single best correspondence.** 11.13.0
carries 27 rules, not "~25"; `global.js`, filed as infrastructure, is a
shipped rule in both presets — and it is the one rule in the catalogue
that maps to three pumllint principles at once. **(3) The ambiguity
dimension exists, and predates the note by six weeks.** §3's product
boundary rested on "`bpmnlint` has none because a BPMN task label is
documentation for humans". That is true of `bpmnlint` core and **false of
the BPMN ecosystem since 2026-07-15**, when
`bpmnlint-plugin-camunda-compat` 2.56.0 shipped three rules whose stated
rationale is that *an LLM reads the text and an underspecified label
degrades what it does*.

**The third correction is the interesting one, and it does not weaken the
settlement — it is the strongest external validation this project has on
file.** The fourth note's structural ground was that BPMN has *no
generation step to gate*: a `.bpmn` file **is** the implementation, so
there is nothing between description and execution for a linter to stand
in. That was right about deterministic engines. It stopped being the
whole picture the moment a *model* began reading the model: in an agentic
ad-hoc sub-process, an LLM reads a tool's element documentation to decide
which tool to call. A consumption step appeared — and the ecosystem's
dominant plugin immediately grew exactly the dimension pumllint has and
`bpmnlint` core lacks. **Convergence on the specific dimension the fourth
note used as the product boundary is worth more than the architectural
convergence it was written to record.**

*Bounds. Every pumllint claim was executed at `1089a99` with default
config, on files outside the repository (GEN006/GEN007 verified dormant).
`bpmnlint` 11.13.0 and `bpmnlint-plugin-camunda-compat` 2.59.2 were
installed from the npm registry and **executed**; rule sources quoted
below are from the installed packages. Per this session's repository
scope **no GitHub repository was read** — so where a slip is reported in
§7, it is reported as observed behaviour at a pinned version, and this
note cannot say whether it is known upstream. The BPMN corpus is
hand-written by me and small (one process, four variants); it exercises
the rules named and no others. The PlantUML BPMN situation is now
verified against plantuml.com's own language-specification index rather
than characterized from search-result titles. No BPMN **engine** was run:
claims about deploy-time validation remain read, not measured.*

## 0. What is being re-examined, and what is not

The fourth note settled the question and recorded three follow-ups. Two
carried explicit re-check instructions:

- **Recorded candidate 2** — "the convergence record itself (§3) … worth
  re-checking if `bpmnlint`'s rule set changes materially."
- **Recorded candidate 1** — the ACT-pack positioning note, "gated on a
  correctness precondition: the DIM-AMB coverage residual … must be
  addressed before this is said in public."
- **Re-litigation trigger 1** — "PlantUML gaining a BPMN diagram type
  with actual BPMN semantics."

All three are checked below, along with §8.4's deferred paired run. The
decision, the four grounds and the never-builds are not re-opened; §9
records what moved underneath them.

## 1. The paired run

### 1.1 The corpus

One order process — receive, decide, fulfil or reject — written four
ways. On the BPMN side: a **defective** variant with no start event, no
end event and an exclusive gateway whose two outflows carry no
conditions; a **partial** variant identical but for one condition
attached to one outflow; a **clean** variant with start and end events, a
condition on one branch and a `default` on the other. On the PlantUML
side: the matched defective and clean activity diagrams.

`bpmnlint` was run under `bpmnlint:recommended`, and again under a
config with the two layout rules in that preset (`no-bpmndi`,
`no-overlapping-elements`) disabled, so that the semantic finding sets
can be compared without diagram-interchange noise. pumllint was run with
default config.

### 1.2 Defective — semantic rules only

```
$ npx bpmnlint -c .bpmnlintrc-semantic pairs/order_defective.bpmn
  OrderProcess  error  Process is missing end event    end-event-required
  Fulfil        error  Element is an implicit end      no-implicit-end
  Reject        error  Element is an implicit end      no-implicit-end
  Receive       error  Element is an implicit start    no-implicit-start
  OrderProcess  error  Process is missing start event  start-event-required

✖ 5 problems (5 errors, 0 warnings)                                   (exit 1)
```

```
$ python3 -m pumllint pairs/order_defective_named.puml
order_defective_named.puml:3: [ACT001/major] Activity flow has no 'start' node — entry point is implicit
order_defective_named.puml:4: [ACT003/minor] Decision '(Order valid?)' has an unlabelled 'then' branch — write "then (yes)"
order_defective_named.puml:6: [ACT003/minor] Unlabelled 'else' branch — write "else (no)"
order_defective_named.puml:7: [ACT002/major] Activity flow never terminates with 'stop' or 'end' (unterminated flow)

✖ 4 issue(s): 2 major, 2 minor                                        (exit 1)
```

The pumllint side reproduces the fourth note's published output exactly,
at a different version (v0.29.0 → v0.30.0) — ACT001, ACT003 twice,
ACT002, two major and two minor. §3's measured half has not drifted.

### 1.3 Clean — both silent, both exit 0

```
$ npx bpmnlint -c .bpmnlintrc-semantic pairs/order_clean.bpmn      (exit 0)
$ python3 -m pumllint pairs/order_clean_named.puml
✔ No issues found.                                                    (exit 0)
$ python3 -m pumllint score pairs/order_clean_named.puml
order_clean_named.puml [order-process]: Level 4 (Precise) — 100/100
```

Both tools agree on exit-code semantics: `1` on findings, `0` on clean.
Under the full `recommended` preset the clean BPMN still reports **13
problems, every one of them `no-bpmndi`** — the file has no diagram
interchange. That is §3's divergence row, measured: `bpmnlint` has layout
rules because the artefact carries geometry, and they are loud enough to
dominate a semantically perfect file.

### 1.4 What the mapping table got right

Of the twelve rows in the fourth note's §3 table, the paired run
exercises five. Four survive:

| §3 row | Status after the paired run |
|---|---|
| `start-event-required` ↔ **ACT001** | **Holds.** Both fire, both process-level, both on the same defect. |
| `end-event-required` ↔ **ACT002** | **Holds.** Same. |
| `label-required` ↔ **SEQ005 / STA003 / CLS003** | **Holds.** Fired on the unnamed start and end events of the §3 probe (`S`, `E` — "Element is missing label/name"). |
| `no-implicit-start` / `no-implicit-end` ↔ **SEQ001 / SEQ010 / SEQ101** | **Holds, and is finer than recorded.** `bpmnlint` fires *both* families on the defective file — process-level (`start-event-required`) and element-level (`no-implicit-start`) are separate rules on the same file. pumllint's ACT001/ACT002 are process-level only; the element-level analogue lives in the SEQ pack, on a different diagram type. |
| `conditional-flows` ↔ **ACT003 / SEQ007** | **Fails.** §2. |

The `no-implicit-*` row deserves the emphasis the fourth note gave it,
and slightly more: the two tools do not merely share the principle, they
share the judgement that *implicit entry* and *no declared entry point*
are worth reporting separately.

## 2. Correction 1 — `conditional-flows` is not ACT003

The fourth note's abstract says:

> Its `start-event-required`, `end-event-required` and `conditional-flows`
> are ACT001, ACT002 and ACT003.

Measured, the third is wrong. On the defective BPMN — an exclusive
gateway with two outflows, neither carrying a condition, neither marked
default — `conditional-flows` **does not fire**. It fires only on the
partial variant:

```
$ npx bpmnlint -c .bpmnlintrc-semantic pairs/order_partial.bpmn
  Flow_3  error  Sequence flow is missing condition  conditional-flows
```

The rule source says why:

```js
function isConditionalForking(node) {
  const defaultFlow = node['default'];
  const outgoing = node.outgoing || [];
  return defaultFlow || outgoing.find(hasCondition);
}
```

The check is guarded on the node **already being** conditional-forking —
having a default flow, or at least one outflow that already carries a
condition. Only then are the remaining outflows required to carry one.

**`conditional-flows` enforces consistency; ACT003 enforces
completeness.** "If you have started attaching conditions, finish the
job" is a different obligation from "every branch must say what selects
it". A BPMN gateway with zero conditions is clean under
`bpmnlint:recommended`; the matched PlantUML decision with zero branch
labels is two ACT003 findings.

The honest restatement is a *subsumption*, not an equivalence:
**everything `conditional-flows` catches, ACT003 would also catch; the
converse is false.** That is a real result and it points the same way as
the fourth note's thesis — it is simply a stronger claim for pumllint
than the one published, and the published one was not supported.

Why the divergence is principled, not an oversight on either side: in
BPMN the condition is *executable* — the engine evaluates it to route a
token, so a gateway with no conditions anywhere is a legitimate
under-specified draft that the engine will reject at deploy time if it
matters. In PlantUML the branch label is the *only* record of what
selects the branch; nothing downstream will ever complain. **The tool
with a runtime behind it can afford to wait. The tool with nothing behind
it cannot.** That asymmetry is worth more than the correspondence it
replaces.

## 3. Correction 2 — the rule count, and the rule the note deleted from its own evidence

The fourth note reported:

> Its published package carries 27 rule files, two of which (`global.js`,
> `helper.js`) are infrastructure — so on the order of 25 rules against
> this project's 51.

`bpmnlint` 11.13.0 was published **2026-08-19**, eight days before that
note — so this is the same version, and the figure is checkable rather
than a version drift:

```
$ ls node_modules/bpmnlint/rules/ | wc -l
28
$ node -e "console.log(Object.keys(require('bpmnlint/config/all.js').rules).length)"
27
```

**28 files, 27 rules, one helper.** `helper.js` is infrastructure —
`annotateRule` and typedefs. `global.js` is not: `global` appears in
`config/all.js` and in `config/recommended.js` at `warn`, and it is a
shipped, firing rule.

The miscount would be trivia except for what `global` does. Its docblock, with the bullet list inlined:

> Currently recognized global elements are `bpmn:Error`,
> `bpmn:Escalation`, `bpmn:Message`, `bpmn:Signal`. For each of these
> elements proper usage implies: element must have a name; element is
> referenced by at least one element; there exists only a single element
> per type with a given name.

Executed against a probe with one unnamed message and two messages
sharing a name:

```
  Msg_1  warning  Element is unused            global
  Msg_2  warning  Element is unused            global
  Msg_2  warning  Element name is not unique   global
  Msg_3  warning  Element is unused            global
  Msg_3  warning  Element name is not unique   global
```

**One rule, three of pumllint's principles**: *must have a name* is the
`label-required` / SEQ005 / STA003 / CLS003 family; *referenced by at
least one element* is `no-disconnected` / UC001 orphan / SEQ002
unused-participant; *unique per type per name* is the XD family's
identity-and-duplication concern. No other rule among the five this note
exercised spans three; the remaining twenty-two were not audited for
breadth. The fourth note filed its richest single correspondence under
"infrastructure" and dropped it from a table built to argue that the two
catalogues converge. The correction strengthens the argument it was
making.

Against candidate 2's re-check instruction — *has the rule set changed
materially?* — **no.** Same version, same 27 rules. The delta is entirely
in the reading.

## 4. Correction 3 — the ambiguity dimension exists

This is the one that matters.

The fourth note's §3 closes with the product boundary:

> pumllint has an ambiguity dimension because its artefact is
> prose-bearing and feeds a generator; `bpmnlint` has none because a BPMN
> task label is documentation for humans while the execution semantics
> live in the attributes.

True of `bpmnlint` core. False of the BPMN ecosystem, and false at the
time of writing.

`bpmnlint-plugin-camunda-compat` — the dominant plugin, at 2.59.2
(2026-08-13) — ships **60 rule files** under `rules/camunda-cloud/` (79 `.js` files under
`rules/` in total, counting helpers, nested connector rules and a single
`camunda-platform` rule). Three of the 60 are these:

```
rules/camunda-cloud/agent-tool-documentation.js
rules/camunda-cloud/agent-tool-output-key.js
rules/camunda-cloud/agent-fromai-contract.js
```

Their own docblocks, quoted from the installed package:

> **`agent-tool-documentation`** — *The AI agent reads a tool's element
> documentation to decide which tool to call; without it the LLM falls
> back to the element name, which is underspecified. This rule warns when
> a tool entry activity … inside an agentic ad-hoc sub-process has no
> documentation text.*

> **`agent-tool-output-key`** — *… on the entry activity when the flow
> writes none at all, since there's no single offending element to point
> to (the agent gets no completion signal and may retry or hallucinate an
> outcome).*

> **`agent-fromai-contract`** — *Validates the parts of `fromAi()` calls
> that have no legitimate reading: the call silently resolves to nothing
> at runtime, with no error, and there is no plausible intent behind the
> violation.*

Read those against this project's charter. The first is DIM-AMB's
argument verbatim — a label that a model will read must not be
underspecified. The third is the codegen profile's `blocker` argument
verbatim — a defect whose failure mode is *silent* at runtime is worth
stopping the build for, which is exactly why SEQ103/SEQ105/SEQ106 are
blockers rather than warnings.

**Dated.** The rules are absent from 2.55.0 (2026-06-25) and present in
2.56.0 (**2026-07-15**):

```
2.50.0 -> agent-* rule files: 0      2.55.0 -> agent-* rule files: 0
2.52.0 -> agent-* rule files: 0      2.56.0 -> agent-* rule files: 3
2.54.0 -> agent-* rule files: 0      2.59.0 -> agent-* rule files: 3
```

So this is **not** the ecosystem moving under a correct note. It is a
note written on 2026-08-27 asserting the absence of something that had
been shipping for six weeks. The fourth note's own bounds admitted the
reach — "`bpmnlint`'s rule inventory was read from its published package
on unpkg, not from source" — and reading core's inventory could never
have found this, because it is not in core. **The boundary claim was
scoped to a package and stated about an ecosystem.**

### 4.1 What it does to the structural ground

Ground (3) was the strongest of the four:

> C4, ArchiMate and UML diagrams describe something a human or an agent
> then implements; a BPMN file **is** the implementation — deployed to
> Zeebe or Flowable and validated by the engine at deploy time. The
> thesis `docs/agents.md` rests on — gate the spec before the agent
> generates from it — has nothing to gate here.

That reasoning holds for the parts of a BPMN file a deterministic engine
executes. It does not hold for the parts **a model reads**. In an agentic
ad-hoc sub-process, the tool documentation is not executed by Zeebe — it
is handed to an LLM, which decides from it. For that text, the file *is*
a description feeding a generator, and the failure mode is the one
`docs/agents.md` describes: a vague label produces a plausible wrong
choice, silently.

**A consumption step appeared in BPMN, and within weeks the ecosystem's
linter grew an ambiguity dimension to gate it.** The fourth note used the
absence of that dimension as the product boundary. Its presence is
better evidence for the same product than its absence was.

### 4.2 What it does *not* do to the decision

Nothing. It **reinforces** ground (2). The gap was already closed by a
27-rule notation linter; it is now closed by that plus a 60-rule vendor
pack, written by the people who own the runtime, embedded in the modeler,
covering FEEL expression shapes and `toolCall` variable channels that no
external tool could adjudicate without reimplementing Zeebe's
tool-schema resolution. `agent-fromai-contract`'s docblock cites the
engine's own `FromAiTaggedParameterExtractor` and the test that pins its
behaviour. **Convergence is evidence the design is right; it is not an
invitation to enter the market it converged in.** That was already record
N3 ("a competitor's adoption is not your pull") and it applies with more
force now, not less.

## 5. Re-verified at HEAD

### 5.1 The honest boundary holds — with a better message

```
$ python3 -m pumllint order.bpmn
warning: 1 file(s) contained no @startuml block and were not checked: order.bpmn — pumllint lints @startuml…@enduml sources; @startmindmap / @startjson / @startsalt / @startgantt blocks are not linted
✔ No issues found.                                                    (exit 0)
```

The contract is intact and the exit code has not moved. The message has
gained a clause since `eee24ac` naming the sibling block types. `.bpmn`
is still outside `PUML_EXTENSIONS`; no coverage is implied that does not
exist.

### 5.2 The type-fallback instance still reproduces

A BPMN-ish sketch drawn with `rectangle` declarations and plain `-->`
arrows, at HEAD:

```
  diagramType='sequence'  level=4 (Precise)  score=90.97  elementCount=9
```

No recognized type marker, undecorated arrows, endpoints materialize as
implicit lifelines, cap C6 escaped, Level 4 on a file with no sequence
diagram in it. The **mechanism** is unchanged at v0.30.0. The sample is a
reconstruction — the fourth note did not publish its source — so the
figures are not comparable to its `score=91.0 elements=5`, and no
inference should be drawn from the difference.

BPMN remains **instance 4** in the corrected enumeration (Linked.Archi 1,
C4 2, ArchiMate 3, BPMN 4, UML 5, D2 6, Structurizr 7, Ilograph 8,
Graphviz 9). No new candidate; the ArchiMate note's candidate 1 covers
it.

### 5.3 No grader — now measured rather than read

```
✖ 12 problems (12 errors, 0 warnings)
```

Findings, severities, a count. No level, no dimension weighting, no gap
report, no ratchet, no aggregate of any kind — confirmed by execution
across four files and two configurations, and confirmed for the
60-rule vendor pack too, which inherits `bpmnlint`'s reporter and adds
nothing above it. Under the corrected criterion settled in the TOGAF turn
— *nothing grades a **description*** — BPMN is not a counterexample:
`bpmnlint` does not grade anything at all.

### 5.4 Candidate 1's precondition is still open — and now demonstrated

The ACT pack is unchanged at HEAD: **ACT001–ACT006, six rules**, on
DIM-CMP (three), DIM-SEM (one) and DIM-CON (two). **None on DIM-AMB.**
Every DIM-AMB rule in the catalogue is scoped to `class`, `sequence` or
`state`:

```
CLS003  unlabelled-association    DIM-AMB (class)
SEQ005  unlabelled-message        DIM-AMB (sequence)
SEQ006  no-self-message           DIM-AMB (sequence)
SEQ103  codegen-prose-message     DIM-AMB (sequence)  {profile: codegen}
SEQ105  codegen-vague-guard       DIM-AMB (sequence)  {profile: codegen}
SEQ106  codegen-elision-marker    DIM-AMB (sequence)  {profile: codegen}
SEQ109  codegen-uninformative-reply DIM-AMB (sequence) {profile: codegen}
STA003  unlabelled-transition     DIM-AMB (state)
```

The fourth note asserted the consequence from the catalogue. It is
directly measurable. A deliberately vague activity diagram — `:handle
it;` used twice, `:do the thing;`, guard `(ok?)`:

```
type=activity  level=4  score=100.0
DIM-AMB: {'score': 100.0, 'penalty': 0, 'weight': 0.25}
```

**A quarter of the composite, awarded in full, for a dimension with no
applicable rule.** Candidate 1 stays gated, and §4 makes the gate look
worse: the BPMN ecosystem now has agent-ambiguity rules for processes
while pumllint's own process diagrams have no ambiguity rule at all.

### 5.5 Trigger 1 has not fired — and is now verified

The fourth note flagged its own weakest external claim: the PlantUML BPMN
situation was "characterized from forum and issue *titles* surfaced by
search rather than from their contents". Fetched from plantuml.com's
language-specification index (2026-08-29), the documented diagram types
are: sequence, use case, class, activity, component, state, object,
deployment, timing, regex, network (nwdiag), wireframe (salt), **archimate**,
gantt, mindmap, WBS, EBNF, JSON, YAML, chart, entity-relationship, files,
information-engineering.

**ArchiMate is a documented PlantUML diagram type. BPMN is not.** Ground
(1) is now verified against the primary source rather than characterized,
and F2 stays closed for want of anything to parse.

## 6. The plugin surface, quantified

The fourth note asserted a "plugin system" and a `bpmnlint-plugin-{NAME}`
convention. Counted on the registry: **8 published `bpmnlint-plugin-*`
packages.**

| Package | Version | Character |
|---|---|---|
| `bpmnlint-plugin-camunda-compat` | 2.59.2 | vendor deploy-compat; 60 `camunda-cloud` rules |
| `bpmnlint-plugin-processmaker` | 1.5.0 | vendor |
| `bpmnlint-plugin-process-engine` | 1.8.0 | engine-specific |
| `bpmnlint-plugin-camunda` | 0.6.1 | superseded vendor pack |
| `bpmnlint-plugin-example` | 0.5.1 | the documentation example |
| `bpmnlint-plugin-spark`, `-shinyinfo`, `-fuyao-bpmnlint` | 1.x / 0.1.x | small / single-purpose |

Two readings, and they pull against each other.

**The niche is occupied twice over.** 27 notation rules plus a 60-rule
vendor pack — larger than `bpmnlint` core, and larger than this project's
51 — is a stronger version of ground (2) than the fourth note had.

**But the community plugin surface is thin.** After nearly five years
(first release 2021-12-08) and 134 versions of the leading plugin, the
open extension ecosystem is one example package and a handful of
vendor/engine packs. That is a sober data point for *this* project's
extensibility story: `@register` + `catalog.toml` is the right
architecture, and the comparable ecosystem shows what such an interface
actually attracts — **the platform vendor, and almost nobody else.** Not
a reason to remove it; a reason not to count on third-party packs as a
growth mechanism.

## 7. An observation on `bpmnlint`'s `global` rule

Reported as observed behaviour at 11.13.0, not as a bug report: this
session's scope permits no GitHub access, so whether it is known upstream
was not checked, and no issue was or will be filed from here.

`global`'s docblock says "element must have a name". The predicate:

```js
function hasName(event) {
  return (
    event.name?.trim() !== ''
  );
}
```

When `name` is absent, `event.name?.trim()` short-circuits to
`undefined`, and `undefined !== ''` is **true** — so a `bpmn:Message`
with no `name` attribute at all passes the check. Only an explicitly
empty `name=""` fails it. Measured both ways:

```
absent  -> hasName: true      empty  -> hasName: false
spaces  -> hasName: false     real   -> hasName: true
```

Two runs of the same probe, differing only in `Msg_1`'s `name`
attribute — first with the attribute absent, then with `name=""`:

```
$ npx bpmnlint -c .bpmnlintrc-semantic pairs/global_probe.bpmn     # <bpmn:message id="Msg_1" />
  Msg_1  warning  Element is unused         global

$ npx bpmnlint -c .bpmnlintrc-semantic pairs/global_emptyname.bpmn # <bpmn:message id="Msg_1" name="" />
  Msg_1  warning  Element is missing name   global
  Msg_1  warning  Element is unused         global
```

The message with no name at all draws no missing-name finding; the one
that names itself the empty string does.

Worth recording here for one reason only: **it is the same defect
shape as this project's own type-fallback class** — a check that is
correct on the values it was written against and silently permissive on
the value nobody tested, with the permissive branch being the common one
in the wild. Two linters, two languages, the same failure mode. §5.2's
instance is not evidence of unusual carelessness in this codebase.

## 8. Boundaries, overlap, sense, nonsense, fit — the deltas

**Boundaries.** Unchanged in structure; one is narrower than recorded.
*Executed vs implemented* (boundary 1) is now **executed, implemented, and
— in agentic sub-processes — read by a model**. The third part is the
only part where this project's thesis has any purchase, and it is the
part Camunda has covered. *XML vs text-with-layout*, *occupied vs
unoccupied* and *discovered vs not* are unchanged; the second is
stronger.

**Overlap.** Larger than recorded, and differently shaped. Four of five
exercised rows hold; `global` adds a three-way correspondence the fourth
note dropped; `conditional-flows` is a subsumption, not an equivalence;
and DIM-AMB — recorded as the thing `bpmnlint` conspicuously lacked — has
an ecosystem counterpart with a rationale that reads like this project's
charter.

**Sense.** S1 ("`bpmnlint` is the best available evidence that this
project's rule catalogue is well-designed") is **stronger**: the
convergence is now measured on paired runs, not read from names, and it
extends to the dimension that was supposed to distinguish them. The
others are unchanged.

**Nonsense — one new move to refuse, and it is tempting.** *"The BPMN
ecosystem grew an ambiguity dimension, which is our dimension; therefore
there is now a gap for us."* **No.** It grew that dimension because a
consumption step appeared in its own artefact, and the vendor that owns
the runtime filled it within weeks, with rules that reach into FEEL AST
shapes and engine variable channels. What the finding licenses is a
sentence about *design validation*. It licenses nothing about market
entry, and the reasoning that would take it there is the same
convention-manufacturing the never-build list already refuses.

**Fit.** No verdict moves.

| Fit | Verdict | Change |
|---|---|---|
| **F1** BPMN rule pack over `.bpmn` | **No** — never-build | Reinforced (§4.2, §6). |
| **F2** BPMN-over-PlantUML pack | **No** — nothing to parse | Ground now verified (§5.5). |
| **F3** BPMN XML as codegen carrier arm | Recorded, hypothesis | Unchanged; W3 untouched by anything here. |
| **F4** Cross-spec verifier | Adopter programme | Unchanged. |
| **F5** ACT pack as "BPMN-lite" positioning | Recorded, gated | **Gate unchanged and now measured** (§5.4). |

## 9. SWOT delta

Only the rows that move.

**Strengths.** *"Independent architectural validation from a shipping
tool"* → **validation now measured on paired runs, and extended to
DIM-AMB.** The strongest design evidence on file is stronger than
recorded, and rests on execution rather than on reading rule names.

**Weaknesses.** The DIM-AMB residual moves from *asserted* to
**demonstrated** (§5.4) — a vague activity diagram scores 100/100 with a
0.25-weight dimension awarded in full. It is the same residual, better
evidenced, and §4 makes it look worse by comparison.

**Threats.** The fourth note recorded the containment pattern as a
projection — *"if the industry direction is processes orchestrating
agents rather than specs feeding generators…"*. **It is no longer a
projection.** `agent-tool-documentation`, `agent-tool-output-key` and
`agent-fromai-contract` are processes orchestrating agents, shipped,
versioned and linted since 2026-07-15. The capability-horizon watch item
(2026-08-01) has an arrival date now.

The counter-reading, which is the more important half: the same rules
show that when processes orchestrate agents, **the orchestration document
itself needs ambiguity gating** — and that is this project's thesis, not
a threat to it. What changes is where the thesis applies, not whether it
holds.

## 10. Decision, recorded candidates, triggers

**Decision: unchanged. No BPMN support of any kind, no carrier arm. The
fourth note's four grounds, never-builds and fit verdicts all stand;
ground (3) is narrower than written and ground (1) is now verified.**

**Never build** — unchanged, and nothing here reopens any of them:

- A BPMN rule pack, over `.bpmn` or over PlantUML (N1, F1, F2).
- A BPMN XML carrier arm without a pre-registered wave under charter §10
  (N2).
- **New:** an agent-tooling rule pack aimed at BPMN's agentic constructs.
  §4 is validation, not an opening; the runtime knowledge required is the
  vendor's, and §4.2 is the whole argument.

**Recorded, not queued:**

1. **Candidate 1 (ACT-pack positioning) — unchanged, gate now
   measured.** §5.4 replaces the catalogue-based assertion with a
   figure. Still gated, still no constituency, still needs "activity
   diagrams, not BPMN" in the same breath.
2. **Candidate 2 (the convergence record) — updated, not retired.** The
   record is now paired-run evidence rather than a name mapping, with
   §2's row removed, §3's row added and §4 appended. Its re-check
   instruction should read *"re-check if `bpmnlint` **or its plugin
   ecosystem** changes materially"* — this note is the case for widening
   it, since the material change was in a plugin and reading core would
   never have found it.
3. **Candidate 3 (type-fallback instance 4) — unchanged.** §5.2.

**Re-litigate on:**

- PlantUML gaining a BPMN diagram type with actual BPMN semantics —
  **not fired**, verified 2026-08-29 (§5.5).
- A measured wave establishing that a machine interchange format
  outperforms a diagram carrier — **not fired**; nothing here touches W3.
- An adopter running PlantUML activity diagrams as their process
  documentation of record — **not fired**; still the F5 constituency.
- **New:** the DIM-AMB residual being closed for activity diagrams, which
  would ungate candidate 1 without any further BPMN argument. §5.4 is the
  measurement to re-run.

## Related reading

- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  fourth note, which this one measures rather than re-opens. Its §3
  mapping table is corrected in §2 and §3 here; its §3 boundary claim is
  corrected in §4.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the type-fallback defect class and its standing candidate 1, which
  §5.2 declines to duplicate.
- [The UML ecosystem, evaluated](uml-ecosystem-evaluation.md) — its §3 is
  the mirror image of the fourth note's convergence argument.
- [The Mermaid ecosystem, evaluated](mermaid-ecosystem-evaluation.md) —
  the second convergence instance, and the occupied-niche reading §6
  extends.
- [The measured minimum sufficient stack](minimum-sufficient-stack.md) —
  W3's carrier figures, untouched here.
