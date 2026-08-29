# The prose-linting ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `cef591e` (v0.30.0).
Twenty-sixth in the series, and the direct follow-on to the twenty-fourth:
the FEEL note recorded a hole — a guard reading `the customer is probably
eligible` passes both SEQ105 and a real FEEL parser — and **deliberately
refused to invent a mechanism for it**. This note asks whether the
ecosystem that specialises in exactly that already has one.*

**Verdict up front: no — and the negative is the finding. The
established prose linters do not catch the vagueness class DIM-AMB
targets, and where the two ecosystems touch at all, they disagree about
what the defect is.**

**Measured. `proselint` 0.16.0 ships 116 registered checks across 76
modules with 24 categories enabled by default — including `hedging` and
`weasel_words`. Its *entire* `hedging` check is three phrases: `"I would
argue that"`, `", so to speak"`, `"to a certain degree"`. Its
`weasel_words` check is one word: `very`. Neither fires on `probably`,
`seems`, `basically` or `arguably`. `write-good` 1.0.8 with every check
enabled flags `the customer is probably eligible` for exactly one reason
— *"'is' is a form of 'to be'"*, an E-Prime doctrine — and misses `user
seems fine` and `it should basically work` entirely.**

**And the disjointness is total. Across eight labels placed in the
syntactic slots their pumllint rules watch, the two prose linters fire on
**none** of pumllint's six DIM-AMB targets, and pumllint fires on none of
theirs.** One label touches both, and it is the most instructive result
in the note: on `validate(...)`, proselint reports
`typography.symbols.ellipsis: '...' is an approximation, use the ellipsis
symbol '…'`. **Taking that advice leaves SEQ106 firing at `blocker`,
verified on both spellings, because pumllint's elision lexicon contains
`"..."` *and* `"…"`.** proselint thinks the glyph is wrong; pumllint
thinks the omission is wrong. Same three characters, two tools, opposite
readings.

**What this establishes.** DIM-AMB is **not** an amateur reimplementation
of prose linting — a reasonable suspicion, since pumllint carries roughly
seventy lexicon entries across five codegen rules and has never named the
neighbouring field. The prose linters check *free-running English* for
**style, usage, clichés and typography**. DIM-AMB checks *a label in a
named syntactic position* for **specificity sufficient to generate code
from**. Different property, different scope, different unit. The FEEL
note's refusal to invent a hedge-detector on the strength of a gap now
has a second, independent reason: **the field that would have supplied
one does not have it either.**

*Bounds. pumllint claims executed at `cef591e` (v0.30.0), `codegen`
profile, neutral cwd. **`write-good` 1.0.8 and `proselint` 0.16.0 were
installed and executed** — proselint's harness was verified against a
known-positive returning 8 findings at exit 1 before any silence below
was recorded as a result. **Vale was NOT run**: it is a Go binary not
available in this environment, so every claim here is about `proselint`
and `write-good` only, and Vale's style packages (Microsoft, Google,
write-good ports) may differ. `textlint` and `markdownlint` were not
examined. English only. Per session scope no GitHub repository was read.*

## 0. Why this ran

The FEEL note (twenty-fourth) closed with this, as recorded candidate 3:

> **The prose-guard hole** — `the customer is probably eligible` passes
> both standards. Recorded as the sequence-side sibling of the
> activity-diagram DIM-AMB residual, and **explicitly without a proposed
> mechanism**: the measurement here says what does *not* work, and
> inventing a hedge-detector on the strength of that would be the same
> error in the other direction.

That is the right discipline and it leaves an obvious next question
unasked. There is an entire tool category devoted to finding hedges,
weasel words and vagueness in English. **Before this project ever
considers building one, it should find out whether the specialists have
solved it.**

A second reason, less comfortable: pumllint already *is* a small
lexicon-based prose linter and has never said so. Five codegen rules
carry word lists:

| Rule | Lexicon | Entries |
|---|---|---|
| SEQ103 `codegen-prose-message` | `arg_stop_words` | **44** |
| SEQ105 `codegen-vague-guard` | `vague_terms` | 5 |
| SEQ106 `codegen-elision-marker` | `tokens` | 7 |
| SEQ107 | `failure` | 9 |
| SEQ109 `codegen-uninformative-reply` | `non_informative` | 5 |

**Seventy entries.** In twenty-five prior notes the prose-linting field
has not been mentioned once. That is a gap in the record regardless of
what the answer turns out to be.

## 1. The ecosystem

| Tool | Version | Shape |
|---|---|---|
| **`proselint`** | 0.16.0 | Python; **76 check modules, 116 registered checks**, 24 categories on by default; sourced to named style authorities (Garner, Pinker, White) |
| **`write-good`** | 1.0.8 | Node, 8 packages; *"Naive linter for English prose"*; toggleable checks — passive, weasel, adverb, tooWordy, cliches, illusion, thereIs, so, eprime |
| **Vale** | *not run* | Go binary; the enterprise entry, with importable style packages. **Unavailable here — see bounds.** |

The category is mature, and unlike DMN's linter layer it is not
vestigial: proselint's 116 checks are a real body of work with cited
sources. **The question is not whether the field is serious. It is
whether it is aimed at this.**

## 2. Overlap — measured, and it is empty

Eight labels, each placed in the syntactic slot its rule watches, each
also passed to both prose linters:

| Label | slot | pumllint | `write-good` | `proselint` |
|---|---|---|---|---|
| `getOrder(the customer id)` | message | **SEQ103** | — | — |
| `validate(...)` | message | **SEQ106** | "validate" is wordy | **`typography.symbols.ellipsis`** |
| `handle TBD` | message | **SEQ106** | — | — |
| `ok` | reply | **SEQ109** | — | — |
| `otherwise` | guard | **SEQ105** | — | — |
| `the customer is probably eligible` | guard | — | — | — |
| `utilize the very unique path` | message | — | 2 findings | 3 findings |
| `At the end of the day, settle` | message | — | — | 2 findings |

**Six pumllint targets, zero prose-linter findings on their defect.** Two
proselint/write-good targets, zero pumllint findings. The single
intersection is `validate(...)`, and it is a collision rather than an
agreement (§3).

`write-good`'s hit on `validate(...)` — *"'validate' is wordy or
unneeded"* — is worth naming as a **false friend**: it fires on the
correct label for the wrong reason, objecting to the verb rather than to
the elided argument list. A pipeline that took it seriously would rename
the operation and leave the defect in place.

## 3. The ellipsis collision

The most useful single result here, because it shows the two tools
looking at the same characters and disagreeing about the property.

```
$ proselint check lbl.txt      # label: validate(...)
typography.symbols.ellipsis: '...' is an approximation, use the ellipsis symbol '…'.
```

Follow that advice, and:

```
$ pumllint --profile codegen e.puml      # label: validate(...)
[SEQ106/blocker] Elision marker '...' in message signals omitted behaviour;
                 model it or the generator will invent it

$ pumllint --profile codegen e.puml      # label: validate(…)
[SEQ106/blocker] Elision marker '…' in message signals omitted behaviour;
                 model it or the generator will invent it
```

**Both verified.** pumllint's `tokens` lexicon is `("...", "…", "TBD",
"TODO", "etc", "???", "and so on")` — it lists both spellings precisely
because the defect is the *omission*, and the glyph is irrelevant to it.
proselint's typography check is about the glyph, and is indifferent to
whether anything was omitted.

**Neither is wrong.** They are checking different properties of the same
token, and the collision is the clearest possible statement of the
boundary: *typographic correctness of prose* and *sufficiency of a
generator's input* are unrelated goals that happen to share a character
sequence.

## 4. Why the specialists miss the hedges

The surprising part is not that prose linters ignore `getOrder(the
customer id)` — that is a signature, not prose. It is that they miss
`probably`, `seems` and `basically`, which look like their home turf.

The reason is that the surface is much smaller than the category name
suggests. proselint's **entire** hedging check:

```python
check = Check(
    check_type=types.Existence(
        items=(
            "I would argue that",
            ", so to speak",
            "to a certain degree",
        )
    ),
    path="hedging",
    message="Hedging. Just say it.",
)
```

Three phrases, sourced to Pinker. And `weasel_words` is a single check
for one word:

```python
check_very = Check(
    check_type=types.ExistenceSimple(
        pattern=Padding.WORDS_IN_TEXT.format(r"very(?! well)")
    ),
    path="weasel_words.very", ...
)
```

**Four items in total across both categories.** Against pumllint's
seventy. The comparison is not "a big mature lexicon versus our small
one" — it is the reverse, in the one area where the fields overlap,
because proselint's mass is elsewhere: clichés, malapropisms, needless
variants, uncomparables, typography, social awareness, archaisms.

`write-good` is likewise aimed sideways. With every check enabled, its
only finding on `the customer is probably eligible` is E-Prime — an
objection to the copula, which is a writing doctrine and not a claim
about specificity — while `user seems fine` and `it should basically
work` pass clean.

**The field is aimed at style, not at specificity.** "Is this sentence
well written?" and "does this label pin down what a generator must
produce?" are different questions, and only the first has a literature.

## 5. Boundaries

1. **Style vs specificity.** §4. The one that explains the rest.
2. **Free text vs a named slot.** proselint sees a string; pumllint knows
   the string is a *guard* or a *reply label* or an *argument list*, and
   nearly all of DIM-AMB's leverage comes from that. A prose linter has
   no slot to condition on.
3. **The glyph vs the omission.** §3.
4. **Runtime.** proselint is Python and *could* in principle be a
   dependency; the zero-dependency constraint makes it a real cost, but
   §2 means the question never arises.

## 6. Sense — three true things

**S1. DIM-AMB is not a reimplementation of prose linting.** §2's empty
intersection is the evidence, and it was worth having, because the
suspicion is reasonable from the outside.

**S2. The FEEL note's refusal is now doubly grounded.** It declined to
invent a hedge-detector on the strength of a gap. The field that
specialises in hedges has four items and misses the case. **Declining to
invent was right, and the reason is now external as well as internal.**

**S3. Position-scoping is the asset.** Boundary 2. pumllint's seventy
entries do more than proselint's four *in this domain* not because the
lists are better but because each is attached to a syntactic slot where a
specific kind of vagueness matters. That is not portable to prose, and it
is why the field could not have solved this.

## 7. Nonsense — three moves to refuse

**N1. "Import proselint's or Vale's vocabularies to extend
`vague_terms`."** The premise is that they have vocabularies worth
importing. §4 measures four relevant items, none of which is a guard
hedge. There is nothing to import.

**N2. "Add a prose-quality dimension / lint the notes as English."**
DIM-RDB already prices notes structurally (GEN008 note-density), and
grading a diagram on whether its note is well-written would be
convention-manufacturing on someone else's turf — with a mature field
that would do it better if anyone wanted it done.

**N3. "Take a prose linter's advice on a diagram label."** §3 and §2's
`write-good` false friend. Both would degrade the artefact: one converts
an elision into a prettier elision, the other renames a correct verb.
**Recorded as the practical warning of this note**, since a team already
running Vale on their docs could plausibly point it at `.puml` files.

## 8. Fit — graded

### F1 — depend on, or vendor, a prose linter. **No.** §2, N1, and zero-dependency.

### F2 — extend `vague_terms` from the field's lexicons. **No — there is nothing to take.** §4, N1.

### F3 — a prose-quality dimension for notes and titles. **No.** N2.

### F4 — close the prose-guard hole with a home-grown hedge lexicon. **Unchanged: recorded, without a mechanism, and now better justified.**

The FEEL note's candidate 3 stands exactly as written. This note adds
that the external option is closed, which **removes an alternative
without creating a mandate**: "nobody else solved it" is not a reason to
solve it, and a hedge lexicon invented here would carry this project's
name on every judgement call about whether `probably` is vague in a
guard. Still no constituency, still no mechanism proposed.

### Fit against declared constraints

| Constraint | Reading |
|---|---|
| **Zero dependencies** | F1 violates it; §2 means the question is moot anyway. |
| **Demand-driven / Arc E bar** | F4 is the only live item and has no constituency. |
| **Claim language is settled** | One addition: DIM-AMB should not be described as "prose linting" — §2 says it is not, and the phrase invites N3. |

## 9. SWOT

**Strengths (internal, favourable)**

- **Position-scoped lexicons** do work in this domain that a general
  prose linter's much larger catalogue does not (§4, S3).
- The elision lexicon's inclusion of *both* ellipsis spellings turns out
  to be exactly right, and §3 is the demonstration.

**Weaknesses (internal, unfavourable)**

- The prose-guard hole is unchanged and now has one fewer escape route
  (§8 F4).
- **Nothing in the project's own documentation situates DIM-AMB against
  this field**, which is why the "is this just prose linting?" question
  had no answer until now. §10 records the claim-language note.

**Opportunities (external, favourable)**

- None. The field is mature, serious, and aimed elsewhere.

**Threats (external, unfavourable)**

- **A team pointing Vale or proselint at `.puml` files** and acting on
  the output (N3). This is a realistic scenario — prose linters are
  commonly wired to run over whole repositories — and both measured
  collisions degrade the artefact.
- **The "just prose linting" dismissal.** §2 is the answer; before this
  note there was not one.

## 10. Decision, recorded candidates, triggers

**Decision: no adoption, no dependency, no prose dimension, and the
FEEL note's open residual stays open and unmechanised.**

**Never build:**

- A dependency on, or vendored copy of, a prose linter (F1).
- A prose-quality dimension over notes, titles or labels (F3, N2).
- A `vague_terms` extension sourced from the field's lexicons (F2, N1) —
  there is nothing there to source.

**Recorded, not queued:**

1. **Claim language: DIM-AMB is not prose linting.** Worth one sentence
   wherever DIM-AMB is described, because the confusion is natural and
   invites N3. §2's disjointness table is the evidence.
2. **The prose-guard hole (FEEL note, candidate 3) — unchanged**, with
   the external option now measured closed. Explicitly **not** a mandate.
3. **The N3 warning** — a prose linter pointed at `.puml` will produce
   advice that degrades the artefact in at least two measured ways.
   Recorded in case an adopter reports it as a conflict.

**Re-litigate on:**

- Vale being available to run, if anyone wants the third data point —
  its style packages are larger than proselint's and were **not**
  measured here. This would sharpen §4 but is unlikely to move §2, since
  the boundary is position-scoping rather than vocabulary size.
- An adopter reporting a conflict between a prose linter and pumllint on
  the same files — the N3 scenario arriving.
- The FEEL note's triggers, unchanged.

## Related reading

- [The FEEL expression language ecosystem, evaluated](feel-expression-language-evaluation.md)
  — the note this one follows from; its candidate 3 is the question here,
  and §8's F4 is the answer.
- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md) — where the
  "the specialists took the work" pattern was first recorded; §4 is the
  case where they did **not**.
- [The Spectral / OpenAPI ecosystem, evaluated](spectral-openapi-ecosystem-evaluation.md)
  — the other tool-shaped peer, and the lexicon-vs-grammar contrast in
  its §4 is the sibling of §4 here.
