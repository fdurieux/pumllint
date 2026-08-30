# Semgrep and rules-as-data, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `95c157a` (v0.30.0).
Twenty-ninth in the series, and a **narrowing return** on the
twenty-fifth: the Spectral note found one real architectural difference —
**Spectral's rules are data, pumllint's are code** — and recorded a
declarative rule layer (its F2) as the only genuinely open idea it
produced. This note tests whether that finding was about Spectral or
about something structural.*

**Verdict up front: structural, and now confirmed at a far more
expressive point. A declarative rule layer for pumllint could serve the
lexical tier of the catalogue and nothing above it — which turns the
Spectral note's open candidate into a scoped one.**

**Why Semgrep.** The Spectral note's boundary rested on a **thirteen-item
function library**, which invites the obvious objection: *the limit is
Spectral's small vocabulary, not rules-as-data.* Semgrep is the test
case that answers it. Its rules are YAML — data — but the vocabulary is a
**pattern language with metavariables** rather than a fixed list of
predicates, and its `generic` mode matches arbitrary text, so it can be
pointed straight at `.puml` files. If expressiveness were the limit,
Semgrep should clear it.

**Measured, on a four-rung ladder up this project's own rule classes:**

| Rung | pumllint analogue | Semgrep result | Correct |
|---|---|---|---|
| **1. Lexical** — a token in a message | SEQ106 elision marker | **✔ 1 finding, right line** | 1 |
| **2. File-scope absence** — no `title` anywhere | GEN001 | **✘ 2 findings** — flags the titled file too | 1 |
| **3. Identity correlation** — used on an arrow, never declared | SEQ001 / SEQ101 | **✘ 2 findings** — cannot tell the declared participant from the undeclared one | 1 |
| **4. Cross-file identity** — same entity named two ways across a batch | XD family | **structurally out of scope** — OSS Semgrep is single-file | — |

**Rung 1 works cleanly.** Rungs 2 and 3 fail in the same way and for the
same reason: **a match-local pattern language carries no file-scope
state.** `pattern-not-inside` scopes to a region *enclosing the match*,
not to the file, so there is no way to say *"and no `participant … as $X`
exists anywhere in this file"* with `$X` bound from the arrow. On rung 3
the metavariable did not even bind in the reported result.

**So the Spectral finding generalises, and its explanation was right.** The
boundary is not the size of a function library. It is that pumllint's
rules need **state** — what else this file declared, what other files in
the batch called the same thing — and a rule expressed as a *local
pattern* has none. Tree-vs-trace, restated: a pattern matcher sees
positions; these rules need a model.

*Bounds, and they matter here more than usual. **Semgrep 1.175.0 was
installed and executed**; every count above is a run, taken from the JSON
`results` array. Semgrep redacts matched source lines without an account
(`"requires login"`), so the claims rest on counts, rule ids and line
numbers, which are returned. **The rules are mine.** I could not express
rungs 2–4 using the documented `patterns` / `pattern-not-inside`
operators in generic mode; **Semgrep also ships a `join` mode** for
correlating findings across rules — present in this version — **which I
did not get working and do not claim is incapable.** The structural
reason given above is my explanation of the failures, not a statement
about the tool's limits in principle. **OPA / Conftest / Rego — the
original candidate for this slot — was NOT run**: the engine needs a
binary not obtainable here through a package registry, and nothing in
this note is a claim about it. Corpus is four hand-written `.puml` files.
No GitHub repository was read.*

## 0. Why this ran

The Spectral note (twenty-fifth) closed with this as its only open idea:

> **F2 — a declarative rule-authoring layer. Recorded, not queued — and
> this is the note's only genuinely open idea.** The merit is real: rules
> as reviewable data, authored by an API-guild equivalent without a
> Python contribution. The costs are also real: … expressiveness that
> stops short of the semantic rules that distinguish this catalogue.

That cost was argued from Spectral's thirteen functions. It is a fair
argument and an incomplete one, because thirteen predicates is a small
vocabulary and the conclusion might not survive a larger one. **If a
richer rules-as-data language can express a declaration-versus-use check,
then F2 is a much better candidate than the Spectral note allowed, and
the record should say so.**

Semgrep is the sharpest available test, and unlike OPA it can be run
here.

## 1. The ecosystem, briefly

Semgrep is a rules-as-data static analyser: rules are YAML carrying a
`pattern` in a language-aware syntax with `$METAVARIABLE` binding and
`...` spans, plus boolean combinators (`patterns`, `pattern-either`,
`pattern-not`, `pattern-not-inside`), a severity, and a message. It has
first-class support for many programming languages and a **`generic`
mode** for everything else — which is what makes it applicable to
PlantUML at all.

Compared with Spectral (twenty-fifth note): **same shape, much larger
vocabulary.** Spectral binds a JSONPath and applies one of thirteen
functions. Semgrep binds metavariables inside a structural pattern and
composes with boolean operators. If "rules as data" has a ceiling, this
is a much higher place to find it.

## 2. The ladder, measured

The harness was verified before any silence was read as a result.

### Rung 1 — lexical. Works.

```yaml
- id: elision-marker
  languages: [generic]
  patterns:
    - pattern-regex: '^\s*\S+\s*-+>\s*\S+\s*:.*\.\.\..*$'
```

```
    puml/seq.puml
    ❯❱ elision-marker
            3┆ C -> S: placeOrder(...)
```

One finding, right line. **SEQ106's job, done in data.** This rung is
never in doubt — it is a regex over a line, and pumllint's own
implementation is a lexicon membership test.

### Rung 2 — file-scope absence. Fails.

Two files: one with a `title`, one without. Correct answer: flag one.

```yaml
- id: no-title
  patterns:
    - pattern: '@startuml $N'
    - pattern-not-inside: |
        title ...
```

```
  flagged: hastitle.puml line 1
  flagged: notitle.puml line 1
  total: 2
```

**Both flagged.** `pattern-not-inside` asks whether the *match* sits
inside a region matching `title ...`; `@startuml b` does not, in either
file. The question "does this file contain a title anywhere?" is not one
the operator asks.

pumllint's ground truth on the same two files: GEN001 on `notitle.puml`,
silent on `hastitle.puml`.

### Rung 3 — identity correlation. Fails, and this is the one that matters.

```
@startuml two
participant "Client" as C
participant "Store" as D
C -> D: read(id)
C -> S: placeOrder(order)
@enduml
```

`C` and `D` are declared; `S` is not. pumllint:

```
two.puml:5: [SEQ001/critical] Participant 'S' is used but never declared
            (possible typo — PlantUML silently creates a new lifeline)
```

One finding, the right participant, named. Semgrep, with both halves of
the rule verified to match individually (`$A -> $X` binds; `participant
... as $X` binds):

```yaml
- id: undeclared-participant
  patterns:
    - pattern: $A -> $X
    - pattern-not-inside: participant ... as $X
```

```
  line 4 | ...
  line 5 | ...
  total: 2   (correct answer: 1 — only the S arrow)
```

**Both arrows flagged.** The declared participant and the undeclared one
are indistinguishable to the rule, because the negation cannot range over
the file with `$X` bound. On the single-arrow probe the same rule
returned one finding with **`$X` unbound (`None`)** — it matched the
right line by arithmetic rather than by identifying anything.

### Rung 4 — cross-file identity. Out of scope.

The XD family compares entity identity **across a batch of files**. OSS
Semgrep analyses one file at a time. Not attempted; recorded as a
structural boundary rather than a measured failure.

## 3. What this establishes

**The Spectral note's boundary was correctly explained.** Its §4 said the
divergence is "the artefact talking, not taste" — a tree yields to
path-plus-predicate, a trace does not. Restated with this evidence: **the
boundary is state, not vocabulary.**

- Rung 1 needs nothing but the current line. A rules-as-data engine does
  it well.
- Rung 2 needs *the rest of the file*.
- Rung 3 needs *the rest of the file, indexed by identity*.
- Rung 4 needs *the rest of the batch, indexed by identity*.

pumllint's rules run against a **parsed model** — `diagram.participants`,
`diagram.blocks`, the batch — so rungs 2–4 are ordinary code. A rule that
is a *pattern* has, by construction, only the match.

**And the objection is answered.** "The limit is Spectral's thirteen
functions" does not survive: Semgrep's vocabulary is far larger and the
ladder breaks at the same rung.

## 4. The consequence for the Spectral note's F2 — it becomes scoped

> **Correction, 2026-08-29, one note later.** The claim below —
> *"viable for the lexical tier and nothing above it"* — is **too
> strong**, and the [policy-as-code note](policy-as-code-ecosystem-evaluation.md)
> is the counter-example. A checkov custom policy in **pure YAML**
> expresses a cross-entity relationship (`cond_type: connection`) and
> discriminates a resource that references a security group from one that
> does not — **SEQ001's exact shape**, in data. §3's finding that the
> boundary is *state, not vocabulary* stands; the inference that no
> declarative format can carry state does not. The real discriminator is
> **what the rule is evaluated against**: Spectral and Semgrep match
> against text positions or a document tree with no identity resolution,
> while checkov's YAML is evaluated against a resource **graph it built
> first**. Given a resolved model — which pumllint has — a declarative
> format can ask relational questions of it. F2 is therefore **bigger
> than this section says** and needs three tiers, not two; see that
> note's §4.4.

This is the practical output.

**A declarative rule layer for pumllint is viable for the lexical tier
and nothing above it.** The lexicon rules — SEQ105's vague terms,
SEQ106's elision tokens, SEQ109's non-informative replies, SEQ103's
argument stop-words, GEN008's density budget — are rung-1 shaped and
would express cleanly as data. The rules that distinguish this catalogue
— SEQ001/SEQ101 declaration-versus-use, ACT001/ACT002 flow terminals,
SEQ011 and GEN005 budgets over parsed structure, the whole XD family —
are rungs 2 to 4.

**So F2's honest form is narrower than it looked**: not "authoring rules
without a Python contribution", but "authoring *lexicon and pattern*
rules without a Python contribution". That may still be worth something —
a project's own vague-term vocabulary is exactly the thing a team wants
to own — but it is a smaller promise, and it should be recorded as the
smaller one.

**The measurement F2 now needs, and which does not exist**: how many of
the 51 rules are rung-1 shaped? That is a per-rule classification against
the criterion "decidable from the matched text alone, without consulting
the rest of the file". It is a morning's work over `pumllint/rules/`, it
would size F2 honestly, and **this note deliberately does not guess at
the number.**

## 5. Boundaries

1. **State vs match.** §3. The one boundary, and it now has two
   independent confirmations.
2. **Generic mode is not a PlantUML parser.** Semgrep sees tokens on
   lines; it has no notion of a participant, a fragment or a diagram
   type. A dedicated Semgrep language plugin for PlantUML would be a
   different proposition — and would amount to writing this project's
   parser inside someone else's tool.
3. **Single-file by default.** Rung 4.

## 6. Sense, nonsense, fit

**S1. The Spectral finding generalises**, and the record is stronger for
having been tested rather than repeated (§3).

**S2. F2 survives as a smaller, better-specified idea** (§4), which is
more useful than either killing it or leaving it vague.

**N1. "Use Semgrep as a PlantUML linter."** Rungs 2–4. It would cover the
lexical tier and silently miss everything the catalogue exists for, while
reporting confidently on what it did match — the failure mode §2's rung 3
demonstrates, where a wrong count looks exactly like a right one.

**N2. "Write a Semgrep language plugin for PlantUML."** §5's boundary 2:
that is this project's parser, re-implemented inside another tool's
extension point, to gain an authoring format for the subset of rules that
needed it least.

**N3. "Rules-as-data is a dead end."** Equally wrong, and §2's rung 1 is
why. It is the right shape for the lexical tier, which is a real part of
the catalogue.

### Fit

| Fit | Verdict |
|---|---|
| **F1** — adopt or depend on Semgrep | **No.** N1, and zero-dependency. |
| **F2** — a Semgrep language plugin | **No.** N2. |
| **F3** — the Spectral note's declarative rule layer | **Unchanged in status, narrowed in scope** (§4). Still demand-gated, still no constituency; now honestly described as a lexical-tier facility. |
| **F4** — classify the catalogue by rung | **Recorded as a missing measurement** (§4), not queued. |

## 7. Decision, recorded candidates, triggers

**Decision: no adoption, no dependency, no plugin. The Spectral note's F2
is narrowed rather than closed.**

**Never build:**

- A dependency on Semgrep, or a Semgrep-based checking path (N1, F1).
- A Semgrep language plugin for PlantUML (N2, F2).

**Recorded, not queued:**

1. **F2 narrowed to the lexical tier** (§4). The Spectral note's entry
   should be read with this scoping attached, the same way the
   decision-table result is read with its suite-composition scoping.
2. **The rung classification** (§4) — a per-rule pass over the catalogue
   against "decidable from the matched text alone". The measurement that
   would size F2. Does not exist; deliberately not guessed at here.
3. **The state-not-vocabulary boundary** (§3) — worth citing whenever a
   declarative or externally-authored rule format is proposed, in place
   of re-deriving it from a function-library count.

**Re-litigate on:**

- A working `join`-mode formulation of rung 3 — which is the one thing
  that would weaken §3, and which this note explicitly did not achieve
  rather than proved impossible.
- An adopter asking to author project-local **lexicon** rules — the
  narrowed F2's actual constituency, and a smaller ask than the Spectral
  note's framing implied.
- OPA/Conftest becoming runnable in an evaluation environment, if the
  policy-as-code comparison is ever wanted; nothing here speaks to it.

## Related reading

- [The Spectral / OpenAPI ecosystem, evaluated](spectral-openapi-ecosystem-evaluation.md)
  — the note this one returns to; its §4 is the finding tested here and
  its F2 is what §4 above narrows.
- [The prose-linting ecosystem, evaluated](prose-linting-ecosystem-evaluation.md)
  — the lexical tier's other neighbour, and the note that established
  what pumllint's lexicons are for.
- [The Gherkin / Cucumber ecosystem, evaluated](gherkin-cucumber-ecosystem-evaluation.md)
  — the convention-versus-defect lesson §2's rung 3 is a different face
  of: a confident count that is simply wrong.
