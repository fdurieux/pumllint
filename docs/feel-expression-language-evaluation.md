# The FEEL expression language ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `76dfc24` (v0.30.0).
Twenty-fourth in the series, and a **narrowing return** on the note
before it: DMN was settled twenty-third, and its F3 (DMN/FEEL as a
codegen carrier) was left recorded-and-fenced. This note asks what that
one did not — about **FEEL itself**, which is the only part of the DMN
ecosystem that touches this project at a specific, named place.*

**Verdict up front: no — and for once the answer is not "the artefact is
out of scope". FEEL and pumllint genuinely overlap at exactly one rule,
SEQ105. Measured against a real FEEL parser, adopting FEEL there would
make that rule *worse at its own job*.**

**The measurement. SEQ105 (`codegen-vague-guard`, class
`MachineEvaluableGuards`) exists to stop `alt`/`opt`/`loop` guards being
hedge words instead of conditions. Its default lexicon is five phrases:
`otherwise`, `sometimes`, `if needed`, `maybe`, `as required`. Fed to
`feelin` 7.0.1 — bpmn.io's FEEL parser, the one inside the Camunda
modeler — **four of those five parse cleanly as valid FEEL**. Only `if
needed` fails, and only because `if` is a reserved keyword: an accident
of grammar, not a judgement about vagueness. Replacing a five-word
lexicon with a real parser would lose 4 of the 5 findings the rule is
for.**

**And it runs both ways. Across an eleven-guard corpus with both sides
executed, the two standards agree on 5 and disagree on 6 — SEQ105
stricter on 4, FEEL stricter on 2. They are orthogonal, not ordered.
Neither subsumes the other, and the case that matters most —
`the customer is probably eligible` — passes *both*.**

**A second finding, unlooked-for: "validate it with FEEL" is not even
well-defined.** `feelin` parses `the customer is probably eligible` as a
single multi-word `VariableName` (five `Identifier` nodes). Camunda's own
FEEL documentation says a variable name *"may not contain whitespaces
(e.g. `order number` is not allowed)"* and requires backticks to escape
them. **The parser in the modeler and the engine that runs the result
disagree about whether an English sentence is a valid name.** Adopting
"FEEL" would mean choosing one.

*Bounds. pumllint claims executed at `76dfc24` with the `codegen` profile
on files outside the repository (no GEN006/GEN007 findings appeared).
**`feelin` 7.0.1 was installed from npm and executed** — every "parses"
and "PARSE-ERROR" below is a run, judged by whether the returned Lezer
tree contains an error node. **Camunda's FEEL engine was NOT run**: its
variable-name restriction is read from Camunda's documentation
(2026-08-29), so §4's implementation disagreement is measured on one side
and read on the other. **I did not read the DMN specification's FEEL
grammar text**, so this note does not say which implementation is
spec-conformant — only that they differ. Per session scope no GitHub
repository was read.*

## 0. Why this ran, and what it is not

The DMN note (twenty-third) settled the ecosystem and left FEEL
deliberately untouched, appearing only inside F3's carrier item and in
ground (2)'s observation that DMN is *"a graphical notation and an
expression language"*. Everything that note measured was about the
notation half.

The expression half deserves its own look for one reason: **it is the
only part of any ecosystem in this series that has a named counterpart
inside pumllint's own catalogue.** SEQ105's class is literally called
`MachineEvaluableGuards`, and "machine-evaluable expression" is what FEEL
is for. Twenty-three notes have asked "is this artefact in scope?". This
one asks a narrower and more useful question: **there is a real overlap
here — should we take it?**

The decision, grounds and never-builds of the DMN note are not re-opened.
§10 records what this adds.

## 1. The ecosystem

### 1.1 What FEEL is, and where it has spread

FEEL — "Friendly Enough Expression Language" — is defined normatively
inside the DMN specification rather than as a standard of its own. It is
the language of decision-table input entries, output entries and boxed
expressions.

**It has since escaped DMN.** Camunda 8 uses FEEL as its expression
language across BPMN as well: sequence-flow conditions, variable
mappings, connector properties, and — as the BPMN re-examination measured
two notes ago — the `fromAi()` calls that bind an agent's tool
parameters. `bpmnlint-plugin-camunda-compat` carries a `utils/feel.js`,
and its `agent-fromai-contract` rule parses **FEEL AST nodes** to
validate a contract statically.

That matters for scoping: FEEL is no longer "the DMN table language". It
is the expression layer of an entire process platform, which is why it
has a maintained standalone parser and DMN's linter does not.

### 1.2 The tool layer

| Layer | Example | State |
|---|---|---|
| **Parser / interpreter** | **`feelin`** 7.0.1 | **99 published versions**, 2019-12-27 → 2026-05-29. Actively maintained. |
| **Engine** | Camunda's FEEL engine (Scala) | Runs FEEL in Zeebe; documents its own name restrictions (§4) |
| **Static analysis over FEEL** | `bpmnlint-plugin-camunda-compat` (`agent-fromai-contract`, `utils/feel.js`) | Parses FEEL to AST inside a BPMN linter |
| **Editor integration** | Camunda Modeler | Live FEEL feedback while editing |

**The version numbers repeat the DMN note's pattern exactly.** `dmnlint`
— the *linter* — has four published versions and two rules. `feelin` —
the *parser* — has ninety-nine. In this ecosystem the investment goes to
the thing that understands the language, and the linting that exists is
built on top of it by someone else.

## 2. The single point of contact

pumllint has one rule whose subject matter is an expression rather than a
diagram element:

```python
@register
class MachineEvaluableGuards(_CodegenRule):
    id = "SEQ105"

    DEFAULT_VAGUE = ("otherwise", "sometimes", "if needed", "maybe", "as required")
    KINDS = ("alt", "opt", "loop")

    def check(self, diagram: Diagram):
        vague = self.lexicon("vague_terms", self.DEFAULT_VAGUE)
        kinds = tuple(self.options.get("kinds", self.KINDS))
        for b in diagram.blocks:
            if b.kind not in kinds:
                continue
            guard = _guard_text(b.label)
            if not guard:
                yield self.violation(..., f"'{b.kind}' fragment has no guard condition")
            elif guard.lower() in vague:
                yield self.violation(..., f"Guard '{guard}' is a known vague phrase "
                                          "('vague_terms' option); write a boolean expression instead")
```

Read precisely, **SEQ105 performs two tests**: is the guard non-empty,
and is it — as a whole string, case-insensitively — a member of a
configurable five-word lexicon. It does **not** check that what remains
is a boolean expression, despite the message saying "write a boolean
expression instead" and the class being named `MachineEvaluableGuards`.

That is a gap between name and behaviour, and it is the honest kind: a
zero-dependency linter cannot evaluate an arbitrary expression language,
and the lexicon is a deliberate, configurable, cheap proxy. **The
interesting question is whether a real expression language would close
it.** FEEL is the obvious candidate, and it is testable.

## 3. Overlap — measured, both sides executed

Eleven guards, each placed in an `alt` fragment of an otherwise-clean
sequence diagram and linted under the `codegen` profile; each also fed to
`feelin`'s `parseExpression`, counted as parsing only if the returned
tree contains no error node.

| Guard | SEQ105 (codegen) | `feelin` 7.0.1 | Agreement |
|---|---|---|---|
| `total > 100` | silent | parses | ✔ agree — sound |
| `balance >= 0 and tier = "gold"` | silent | parses | ✔ agree — sound |
| `the customer is probably eligible` | silent | **parses** | ✔ agree — **both wrong** |
| `user seems fine` | silent | **parses** | ✔ agree — **both wrong** |
| `otherwise` | **blocker** | **parses** | ✘ SEQ105 stricter |
| `maybe` | **blocker** | **parses** | ✘ SEQ105 stricter |
| `as required` | **blocker** | **parses** | ✘ SEQ105 stricter |
| `sometimes` | **blocker** | **parses** | ✘ SEQ105 stricter |
| `if needed` | **blocker** | PARSE-ERROR | ✔ agree — *different reasons* |
| `total >` | silent | **PARSE-ERROR** | ✘ FEEL stricter |
| `>` | silent | **PARSE-ERROR** | ✘ FEEL stricter |

**Agree on 5, disagree on 6: SEQ105 stricter on 4, FEEL stricter on 2.**

Three readings, in increasing order of importance.

**A FEEL parser would lose four of SEQ105's five findings.** The lexicon
exists to catch exactly `otherwise`, `sometimes`, `if needed`, `maybe`,
`as required`. Four of them are well-formed FEEL. The one that fails does
so because `if` opens an if-expression — the grammar objecting to a
keyword, not the language objecting to a hedge. **Swapping the lexicon
for the parser would be a straight downgrade at the rule's stated
purpose.**

**FEEL catches two things SEQ105 misses, and they are real.** `total >`
and `>` are genuinely malformed and slip through the lexicon test
untouched. This is the honest half of the case *for* a parser, and §8
weighs it.

**Neither catches the case that matters most.** `the customer is probably
eligible` passes SEQ105 (not in the lexicon) and parses as FEEL. It is
also precisely the kind of guard the codegen profile exists to stop —
prose wearing a condition's clothes, which a generator will silently
invent an implementation for. **Two independent standards, and the target
walks through both.** That is the finding worth carrying forward: the
lexicon is not a weak approximation of FEEL-parseability, because
FEEL-parseability is not the property anyone wanted.

## 4. Why an English sentence is valid FEEL — and which FEEL

`feelin` parses the phrase as one name:

```
$ node -e "parseExpression('the customer is probably eligible')"
Expression > VariableName > Identifier > Identifier > Identifier > Identifier > Identifier
```

Five identifiers under a single `VariableName`. And it resolves as one:

```
evaluate('the customer is probably eligible', {'the customer is probably eligible': true})
  -> { value: true, warnings: [] }

evaluate('user seems fine', {})
  -> { value: null,
       warnings: [ { type: 'NO_VARIABLE_FOUND',
                     message: "Variable 'user seems fine' not found" } ] }
```

**Two consequences, and the second is the surprising one.**

**(a) The evaluator can flag the phrase, but only with a context.** An
unbound name produces `NO_VARIABLE_FOUND`. That is a genuinely useful
signal — and it requires the variable environment, which is exactly what
a linter reading a `.puml` file does not have and cannot acquire. **The
ecosystem separates context-free syntax (permissive) from
context-dependent resolution (informative), and pumllint has access only
to the first half.** Any "validate guards with FEEL" proposal inherits
the permissive half and none of the useful one.

**(b) The implementations disagree about the phrase.** `feelin` — the
parser inside the modeler — treats it as a multi-word name. Camunda's own
FEEL documentation says a variable name

> may not contain *whitespaces* (e.g. `order number` is not allowed; you
> can use `orderNumber` instead)

and directs authors to backticks (`` `first name` ``) for names with
spaces. So the parser used while editing accepts a construct the
documented engine rules reject.

**This note does not adjudicate that.** I did not run Camunda's engine
and did not read the DMN spec's grammar text, so which one is
spec-conformant is out of scope here. What matters for the decision is
narrower and certain: **"we would validate the guard with FEEL" does not
name a single behaviour.** It names a family, whose members disagree on
the exact input class this rule cares about.

## 5. Boundaries

1. **Lexicon vs grammar.** §3. The two standards are orthogonal. This is
   the one boundary in the series that is *not* about artefact scope —
   both tools look at the same string and disagree about it.
2. **Syntax vs resolution.** §4(a). FEEL's useful check needs a variable
   environment; a source linter has none.
3. **One language, several implementations.** §4(b). "FEEL" is not a
   single acceptor.
4. **Zero dependencies.** Adopting `feelin` means a Node runtime inside a
   Python tool; reimplementing FEEL means carrying a grammar for a
   language this project does not otherwise touch. Not the decisive
   ground — §3 already decides it — but it is real, and it is the
   project's oldest constraint.

## 6. Sense — three true things

**S1. The overlap is real, and specific.** Most prior refusals in this
series turned on the artefact being out of scope — a different file
class, a different notation, a producer rather than a subject. FEEL and
SEQ105 are about *the same string*. Refusing on measurement rather than
on scope is a better refusal, and it took a paired run to earn it.

**S2. SEQ105's honesty gap is smaller than it looks.** The class name
overpromises against the implementation. But the implementation is
*better at the actual job* than the obvious upgrade — so the fix, if any,
is to the **name and the message**, not to the mechanism.

**S3. `feelin`'s two genuine catches are worth remembering.** `total >`
and `>` are malformed and SEQ105 says nothing. That is a real residual,
recorded in §10, and it does not need FEEL to address.

## 7. Nonsense — three moves to refuse

**N1. "Use a real expression parser instead of a word list."** The
intuitive upgrade, and §3 measures it as a downgrade: 4 of 5 findings
lost. This is the note's whole point, and it generalises — *a stricter
formalism is not automatically a better check when the property you want
is not the formalism's property.*

**N2. "Require guards to be valid FEEL."** This would manufacture a
convention: PlantUML guards are free text, no PlantUML tooling reads them
as FEEL, and no adopter writes them that way. It is the
convention-manufacturing anti-goal in a new costume, and §4(b) adds that
the convention would not even be single-valued.

**N3. "Ship a FEEL subset validator."** A subset chosen by this project
is a new language, with this project's name on its edge cases, checked
against nothing. Worse than either option it splits.

## 8. Fit — graded

### F1 — replace SEQ105's lexicon with a FEEL parser. **No. Measured.**

§3. Four of five findings lost, a runtime dependency gained, and §4(b)'s
ambiguity inherited. The strongest "no" in the series that rests on a
measurement rather than a boundary.

### F2 — add FEEL parsing *alongside* the lexicon, to catch `total >`. **No, but this is the closest call in the note.**

The two catches in §3 are real. But they are **malformed-fragment**
defects, not expression-semantics defects, and nothing about them
requires FEEL: they are "the guard ends in an operator" / "the guard is
punctuation only". If that residual is ever worth closing, it is worth
closing with a few characters of pattern-matching in the existing rule,
with no dependency, no grammar, and no commitment to whose FEEL is
authoritative. **Recorded as a residual in §10, explicitly not as a FEEL
candidate.**

### F3 — FEEL as a codegen carrier arm. **Unchanged: recorded, hypothesis, fenced.**

The DMN note's F3 and its N1 apply verbatim; nothing here touches W1B's
pre-registration or W3's carrier result.

### F4 — rename SEQ105 / soften its message. **Recorded, not queued.**

`MachineEvaluableGuards` and "write a boolean expression instead" both
claim more than the two membership tests deliver. §6's S2. This is claim
language, cheap, and it touches a rule ID's *behaviour* not at all — but
rule IDs and kebab-case names are a contract, so the ID and
`codegen-vague-guard` stay; only the class name and message text are in
scope, and only if someone is already editing the file.

### Fit against declared constraints

| Constraint | Reading |
|---|---|
| **Deterministic product path, no LLM** | Untouched — nothing queued. |
| **Zero dependencies** | F1 and F2-as-FEEL both violate it; §5.4. Not the decisive ground, but it is not close. |
| **Golden score contract** | No fit here changes a score. F4 changes message text only, which the golden artefacts would notice — so it is a re-freeze if ever done. |
| **Demand-driven / Arc E bar** | F1/F2 **fail on merit, not demand**. F4 is a tidy-up, not a feature. |
| **Rule IDs and names are contracts** | Constrains F4 to the class name and message. |

## 9. SWOT

Scope: *pumllint's position relative to FEEL*.

**Strengths (internal, favourable)**

- The cheap mechanism beats the sophisticated one at its own job, and now
  there is a measurement saying so rather than an intuition (§3).
- The lexicon is **configurable** (`vague_terms` / `extra_vague_terms`),
  so a project that hedges in its own vocabulary can extend it — an
  affordance a grammar does not have.

**Weaknesses (internal, unfavourable)**

- **`MachineEvaluableGuards` overpromises** (§6 S2, F4).
- **A malformed guard passes** (`total >`, `>`) — a small real residual
  (§8 F2).
- **Neither standard catches prose-shaped guards** (§3's third reading).
  `the customer is probably eligible` is a `codegen` blocker in spirit
  and silent in fact. This is the same shape as the DIM-AMB residual
  recorded twice for activity diagrams, now visible on the sequence side
  too.

**Opportunities (external, favourable)**

- None that are FEEL's. The residuals in §8 F2 and F4 are internal and
  need nothing from this ecosystem.

**Threats (external, unfavourable)**

- **The plausible upgrade.** "Why not just use a real parser?" is a
  reasonable question that a reviewer, an adopter or a future note will
  ask, and the intuitive answer is wrong. §3 exists so the answer is on
  file with numbers.

## 10. Decision, recorded candidates, triggers

**Decision: no FEEL adoption of any kind. SEQ105 keeps its lexicon. The
DMN note's records stand unchanged.**

**Never build:**

- A FEEL parser or FEEL subset validator inside pumllint, or a dependency
  on one (F1, N1, N3, and the zero-dependency constraint).
- A rule requiring guards, labels or arguments to be valid FEEL (N2) —
  convention-manufacturing, and §4(b) means the convention is not
  single-valued.

**Recorded, not queued:**

1. **The malformed-guard residual (§8 F2)** — `total >` and `>` pass
   SEQ105. If ever closed, close it with pattern-matching inside the
   existing rule: **not** with FEEL, and not as a new rule ID.
2. **SEQ105's claim language (§8 F4)** — the class name and message
   overpromise against two membership tests. Message text is a golden
   re-freeze; the rule ID and kebab-case name are contracts and do not
   move.
3. **The prose-guard hole (§9)** — `the customer is probably eligible`
   passes both standards. Recorded as the sequence-side sibling of the
   activity-diagram DIM-AMB residual, and **explicitly without a proposed
   mechanism**: the measurement here says what does *not* work, and
   inventing a hedge-detector on the strength of that would be the same
   error in the other direction.

**Re-litigate on:**

- SEQ105's lexicon being extended far enough that maintaining it becomes
  the cost a grammar would avoid — which §3 says is a long way off, since
  the grammar does not do this job at all.
- PlantUML gaining a typed guard construct that a tool other than this
  one already parses — which would make the convention someone else's,
  and is the only condition that reopens N2.
- The DMN note's triggers, unchanged.

## Related reading

- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md) — the
  previous note; its F3 and its pre-registration fence are unchanged
  here, and its ground (2) is where the expression half was set aside for
  this one.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md) — where
  `agent-fromai-contract`'s FEEL AST parsing was found, and the
  paired-run method this note reuses.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  original convergence argument. §3 here is the **second** paired run to
  come back negative — after `dmnlint`'s silence one note earlier — and
  the first where the adjacent tool is not merely absent but actively
  worse at the shared job.
