# A foreign corpus reads back — the J-F audit

*Dated evidence note, 2026-08-26. A read-only audit ran the tool against
`akantai/J-F`, a third-party PlantUML corpus this repository did not author
(24 diagrams, five types, gated in that project's own CI). It found two
defects in pumllint, both in SEQ107, and both are fixed in the commit this
note accompanies. The corpus was not modified and is not redistributed here —
the same posture as the wild tier and the pilot census. No scoring or claim
language changes: golden scores, the published pilot artefacts and the
dogfooding record are byte-identical across the fix. Three further
recommendations came out of the audit; all three are recorded as gated, none
is queued.*

## Why this matters

README's beta caveat says the tool "has not yet been exercised against a
third-party diagram corpus". The 2026-08-11 pilot census made first contact
with foreign *dialect* — 159 files, parsed, counted, nothing judged. This is
the first time a foreign corpus has been read for **semantics**: a corpus
whose authors adopted the codegen profile, drove it to Level 5 100/100, and
kept using it long enough to develop workarounds.

Workarounds are the interesting part. A rule that a competent author has to
work *around* is a rule that is measuring the wrong thing, and you cannot
find those on diagrams you wrote yourself.

## What was found, and fixed

**F1 — SEQ107 constrained phrasing, not modelling.** A failure branch was
accepted only when its guard carried `error|failure|timeout|exception` or a
negation. The whole truthful *absence* vocabulary failed it. Reproduced here
from a clean checkout: rewriting a guard to a statement that is equally true
and means the same thing, but omits the word `not`, flips the verdict.

| `else` guard | SEQ107 before | after |
|---|---|---|
| `[source not stored - latest_date returned None]` | 0 | 0 |
| `[source has no stored rows - latest_date returned None]` | 1 | 0 |
| `[source is missing]`, `[store is empty]`, `[data unavailable]`, `[value is absent]` | 1 each | 0 each |

The corpus's authors had resolved this by rewriting true guards to contain
`not` — the rule teaching authors a vocabulary rather than checking their
modelling.

**F2 — the `^\s*!` negation form was unreachable.** `_NEGATED` offered three
forms; the third could never match a guard, because the parser keeps guards
verbatim and the brackets put a leading `!` at index 1. `else !fallback`
matched; `else [!order_found]` — the ordinary bracketed idiom — did not.

Both were the same omission: SEQ107 read the raw label where SEQ105 already
read the bracket-stripped content. The fix shares that idiom as
`_guard_text()` and widens the vocabulary to the absence family. The gate is
unchanged in every other direction — a bracketed business-logic guard still
reports, `nonexistent` does not read as `none`, a declared-but-empty branch
still models nothing, and `failure_keywords` still overrides.

One trade-off was taken deliberately: `no <noun>` can denote a happy path —
this repository's own `docs/pumllint-lint-flow.puml` carries
`alt no finding at or above --fail-on`. An alt whose branches are business
logic phrased that way may now be accepted as modelling failure. That is
leniency in the direction the finding asks for, and the lexicon stays
configurable for projects that want it tighter.

## Recorded, not queued

- **XD member and relationship coherence** → Arc C. The audit's third
  recommendation, and the first concrete form the "growing the XD family"
  direction has taken. *Trigger: a second corpus or an adopter showing the
  same defect class.*
- **Adopt a foreign corpus as a regression fixture** → Arc D. What would
  actually retire README's beta caveat. *Trigger: owner go on vendoring —
  it is a licence, attribution and golden-re-freeze decision, not a
  code one.*
- **"State plainly what a green gate certifies"** → already settled, no
  change made. SCORING.md §9 rejects "guaranteed generation-ready",
  README says Level 5 means *method-convention complete*, and the working
  agreements list the claim language as settled. What the audit adds is
  third-party evidence *for* the existing claim, not a reason to restate
  it — see EVIDENCE.md.

## Provenance

The audit and this fix were separate sessions; this table keeps them apart.

| Claim | Provenance |
|---|---|
| F1 phrasing trap; F2 unreachable `!` | **Reproduced here** (2026-08-26) from a clean checkout at `b30510f`, via `Engine({"profile": "codegen"})` |
| The before/after table above | **Measured here**, after the fix |
| Golden scores, pilot artefacts, dogfooding record unmoved | **Measured here** — full suite green, no re-freeze |
| 15 defects surviving a Level 5 100/100 gate | **Audit record** — that project's own audit ledger, read but not re-derived here |
| ~73% false positives on the corpus's own code-aware checks | **Corpus record** — measured by that project, not by either session |
| Negative-control battery (mutations fire cleanly, no false positives) | **Audit record** — measured that session on a scratch copy, not re-run here |
| Corpus is public and licensed | **Audit record** — asserted there, not independently verified here |

The audit session was scoped to the corpus repository and could not push
here, which is why its findings arrived as a report rather than a patch.
