# The evidence, explained from scratch

*Audience: anyone — no software, statistics or AI background assumed.
This page walks through what the [v0.22.0 "evidence release"](https://github.com/fdurieux/pumllint/releases/tag/v0.22.0)
and the [v0.23.0 "agent release"](https://github.com/fdurieux/pumllint/releases/tag/v0.23.0)
actually established, starting from zero and defining every term as it
appears. The rigorous record with all the numbers is
[EVIDENCE.md](../EVIDENCE.md); the business case built on it is
[The case for pumllint](case-for-pumllint.md).*

## The setting, in one paragraph

Software teams draw diagrams of how their systems work — "when a customer
pays, the order service asks the payment gateway to charge the card; if
the card is declined, do this instead." Those diagrams are increasingly
written as plain text (using a tool called **PlantUML**) and, more
importantly, increasingly *read by AI*: you hand the diagram to an AI
coding assistant and it writes the program the diagram describes.
**pumllint** is a quality checker for those diagrams — like a spelling
and grammar checker, but for diagrams — and it grades every diagram on a
maturity scale from Level 1 (*sketchy*) to Level 5 (*method-complete*).
The product's central claim is: **the better the diagram, the better the
AI-written code — and below Level 2, code quality falls off a cliff.**
Release 0.22.0 changed nothing about how the tool works. It is an
*evidence release*: it ships the experiments run to test that central
claim much more rigorously, the results (including one prediction that
failed), and the updated documentation.

---

## Part 1 — The vocabulary

### The basics

**Linter.** An automatic checker that reads a file and flags problems,
the way a grammar checker reads prose. pumllint is a linter for diagram
files.

**Maturity score.** pumllint reads a diagram and produces a score from 0
to 100 (called the *composite*), which maps to Levels 1–5. A vague
diagram ("charge the customer somehow", a decision branch labelled
"sometimes") scores low; a precise one (every step named, every failure
path drawn) scores high.

**The cliff.** The experiments repeatedly show that AI-generated code
quality doesn't decline gently as diagrams get worse — it holds up
reasonably well, then *collapses* once the diagram score drops below
roughly 40/100 (Level 1 territory). Like a hiking path that's fine until
the edge, then a drop. This cliff is the product's most important
finding, because it justifies a simple rule: don't let below-Level-2
diagrams anywhere near AI code generation.

### The experiment words

**Generator.** The AI model that reads a diagram and writes code from
it. Three were used: two from Anthropic (Claude Opus — large, and Claude
Haiku — small) and one from Google (Gemini 3.1 Pro).

**Judge.** A *different* AI model that reads the diagram and the
generated code, and gives an opinion: "this code faithfully implements
about 72% of what the diagram says." An opinion — that word matters
later.

**Wave.** One batch of measurements: take ~28 diagrams of deliberately
mixed quality, generate code from each one three times, measure the
results. Eight waves have now been run (the last two are Part 4's
repair experiment).

**Pre-registration.** Before running an experiment, you write down — and
permanently record — exactly what you predict and exactly what number
counts as pass or fail. *Then* you run it. This is how honest science
avoids fooling itself: you can't move the goalposts after seeing the
results, and a failed prediction can't be quietly buried. (If this
sounds like how a bank validates a risk model — commit to the test
before you see the data — that's exactly the spirit.)

**Correlation (the "r" number).** A number between 0 and 1 describing
how much two measurements move together. r = 1 means lockstep; r = 0
means no relationship at all — knowing one tells you nothing about the
other; around 0.5–0.7 is a solidly strong relationship. Keep an eye on
this — the whole story turns on a few r values.

**Percentage points (pp).** The plain difference between two
percentages. If good diagrams yield code that passes 85% of its tests
and bad ones 64%, the gap is 21 percentage points.

### Five terms from the release notes

**Pins.** A software project's own documentation says things like
"install version 0.21.1" in many places — the install guide, the
examples, the setup snippets. Each of those hard-written version numbers
is a "pin." At release time, every pin must be updated to the new
version, everywhere, or users copy-paste outdated instructions. It's
like moving house: your address is printed on more documents than you
remember, and all of them need changing. pumllint has an automated check
that *fails the build* if any pin is forgotten — this release bumped 11
pins across 4 files, and the check confirmed none were missed.

**Execution oracle.** In testing, an "oracle" is whatever decides pass
or fail. Until this release, the oracle was the AI judge — an *opinion*.
The execution oracle replaces opinion with observation: a set of
behavioural tests was hand-written for each diagram scenario ("if the
payment is declined, the order must be rejected and a compensation step
must happen"), locked in before any result was seen, and then the
AI-generated code was **actually run** against them in a sealed sandbox.
Think of judging a cake by tasting it instead of asking an expert how it
looks. Code either does the right thing when executed, or it doesn't —
no AI, of any brand, is involved in that verdict.

**Scaffold resistance.** "Scaffolding" is giving the AI extra help —
stricter instructions, a required structure, a fill-in-this-template
contract. One wave tested whether better prompting could compensate for
worse diagrams. Result: scaffolding rescued *moderately* untidy diagrams
(they jumped to near-perfect scores) but did **nothing** for below-cliff
diagrams. The cliff is *scaffold-resistant*. The intuition: a template
helps a student whose notes are messy but complete; it cannot help a
student whose notes are missing the actual facts. No prompt can restore
a business rule the diagram simply never contained.

**Cross-vendor robustness.** All earlier evidence used Anthropic
(Claude) models on both sides of the experiment. A fair skeptic could
say: "maybe this cliff is a quirk of one company's AI." Cross-vendor
robustness means the result also holds with a different company's
model — like getting the same result from a second, independent
laboratory. That was the whole point of the final wave, run with
Google's Gemini.

**Reliability ≠ validity.** Two measurement concepts that sound alike
and are dangerously different. **Reliability** = measurements agree with
each other (two graders give similar marks). **Validity** = measurements
agree with *reality* (the marks reflect true quality). The trap: two
bathroom scales that both read 5 kg too heavy agree perfectly — flawless
reliability, zero validity. Keep this in mind for verdict three.

---

## Part 2 — What release 0.22.0 actually did

Nothing in the tool's behaviour changed — a diagram gets the identical
score in 0.22.0 as in 0.21.1, and an automated "golden score" check
guarantees it. What shipped was the evidence and its record: the
hand-written test suites and the sandbox runner, the results of six
measurement waves written into [EVIDENCE.md](../EVIDENCE.md) (including
the failed prediction, verbatim), an updated
[roadmap](../ROADMAP.md), and plain-language updates to the
management-facing documents. The release ritual itself: bump the 11
version pins, regenerate the live example report (only its embedded
version number changed — proof nothing else moved), run both test
suites (769 tests, all green), tag the release (which automatically
publishes it to PyPI — the public "app store" for Python software),
verify a fresh installation works end-to-end, and publish the release
notes. Total cost of the entire day's experiments, incidentally: about
**$24** in AI usage fees.

---

## Part 3 — The three verdicts

Before running the Gemini wave, three predictions were pre-registered,
named XV1–XV3, each with an exact pass bar. Here is what each said, what
happened, and what it means.

### Verdict 1 — XV2 confirmed: the cliff is real, everywhere (the headline)

**Predicted:** if *Google's* Gemini writes the code and it is graded by
*actually running it* (the execution oracle — no AI opinion anywhere in
the scoring), the cliff should appear: at least a 10-percentage-point
gap in test pass-rate between bad diagrams and good ones.

**Happened:** the gap was **20.9 percentage points** — and under the
Claude generators it had been 21.9. Nearly identical. Concretely: code
generated from below-cliff diagrams failed roughly **one intended
behaviour in three** when run; code from decent diagrams failed roughly
one in ten.

**Why it matters:** the cliff has now been demonstrated with three
different generator AIs from two different companies, measured by the
one method that cannot be accused of AI bias — running the code. The
cliff is a property of the *diagrams*, not of any particular AI. That
makes pumllint's core recommendation ("automatically block
below-Level-2 diagrams from AI code generation") about as well-founded
as a claim like this can be.

### Verdict 2 — XV1 failed, and the failure is the most instructive part

**Predicted:** the AI judge (Claude Sonnet) should *also* see the cliff
when reading Gemini's code — at least an 8-point gap in its fidelity
opinions.

**Happened:** the judge saw almost nothing — a flat 3.2-point gap.
Worse: comparing the judge's opinions with what the code actually did
when run gave **r = 0.002. Zero.** The judge's opinion of Gemini's code
carried no information about whether that code worked.

Two explanations were possible. The charitable one — Gemini is so good
the cliff genuinely vanished — is *ruled out*, because the execution
oracle showed the cliff at full size in that same code. What remains:
**the judge can't accurately assess code written in another company's
style.** Its grading rubric was, in effect, calibrated to the coding
idiom it knows, and it lost touch with reality on unfamiliar-looking
code.

**Why it matters:** first, honestly reporting a failed prediction is
precisely what pre-registration is for — the failure is on the record,
in the release notes, undiluted, and that candour is what makes the
confirmed results trustworthy. Second, the failure taught something the
successes couldn't: AI judges' opinions of code degrade — all the way
to worthless — as the code's style gets less familiar. Nothing in the
product's claims was resting on this judge (the execution oracle
carries them), but anyone else relying on AI-judged code quality should
want to know this.

### Verdict 3 — XV3 confirmed: the judges agree with each other… which is the problem

**Predicted:** if Gemini *re-grades* the code that Claude's judge had
already graded, the two judges should broadly agree on *ranking*
(r ≥ 0.5).

**Happened:** they agreed comfortably — r = 0.682 — though Gemini graded
about 19 points more generously across the board, like a lenient teacher
and a strict teacher who agree on who the best students are while giving
different absolute marks.

**The uncomfortable synthesis:** put verdicts 2 and 3 side by side. The
judges agree with **each other** at about 0.7. Either judge agrees with
**what the code actually does** at about 0.25 — and on cross-vendor
code, at 0.0. The judges are *reliable* (consistent with each other) but
not *valid* (not consistent with reality). Remember the two broken
bathroom scales: a firm handshake between two graders is not evidence
that either is right.

**Why it matters — well beyond this project:** a lot of the AI industry
currently checks AI output by asking another AI ("LLM-as-judge"), and
"our judges agree with each other" is routinely offered as proof of
quality. This measured result says: that proof establishes nothing.
**When behaviour can be executed, execute it; agreement between opinions
is not a substitute.** That finding now sits in
[the SDLC assessment](value-in-the-sdlc.md)'s methodological exports as
something you can reuse when evaluating *any* AI tooling — which may be
worth more than the tool itself.

---

## Part 4 — Release 0.23.0: can an AI *repair* a bad diagram?

The 0.22.0 evidence ended on a hard fact: below the cliff, better
prompting cannot compensate — no instruction can restore a business
rule the diagram never contained. But pumllint doesn't just grade a
diagram; it produces a **gap report** — a to-do list of exactly what is
missing, item by item. So the obvious next question: if an AI assistant
*follows that to-do list and repairs the diagram first*, does the code
get better? Release 0.23.0 ships that experiment — run twice, once for
each of the two ways a missing decision can be filled in.

**The two arms.** (An "arm" is one variant of an experiment, run so the
variants can be compared.) Both arms took the sixteen worst diagrams
from the earlier waves, gave the same AI assistant the diagram plus
pumllint's to-do list, and let it repair. Then the same code-writing AI
as before implemented the repaired diagrams, and the code was graded by
*actually running it* against the same locked behavioural tests. The
only difference between the arms:

- **Arm one — repair by guessing.** Nobody to ask. Where a business
  decision was missing (which condition? what happens on failure?), the
  repairer chose the most plausible answer itself.
- **Arm two — repair by asking.** The repairer could put questions to
  the diagram's *author* — played, in the lab, by a separate AI that
  had been given the original intended design, under strict rules:
  answer only what is asked, in at most 40 words, never show the design
  itself. Every question and answer was recorded, and audited
  afterwards for accidental give-aways.

### Verdict — guessing made things worse; asking recovered almost everything

**Arm one (guessing), predicted:** repairs should help at least a
little, even below the cliff. **Happened: the opposite.** Repaired
below-cliff diagrams produced code that failed *more* behavioural tests
than code from the unrepaired originals — 58% passing versus 64%. The
starkest case: a nearly-good diagram whose one real flaw was a single
vague decision label. The repairer replaced it with a confident,
plausible — and wrong — rule, and that diagram's pass rate fell from
93% to 40%. The explanation is uncomfortable and important: the
code-writing AI treats whatever the diagram says as the truth. A wrong
rule written into a diagram *looks exactly like a right one*, and it
overrides the sensible guess the code-writer would otherwise have made.
(Purely *structural* damage — an undeclared component, a malformed
block — was repaired reliably in this same arm, several diagrams
jumping to 100%. Structure can be repaired from the to-do list;
*content* cannot be safely guessed.)

**Arm two (asking), predicted and happened:** with the author
answering, the same below-cliff diagrams produced code passing **86%**
of intended behaviours — versus 64% untouched and 58% under guessing.
The moderately-flawed diagrams did even better: statistically
indistinguishable from perfect ones (96% vs 95%). Since the two arms
differed *only* in where missing decisions came from, the comparison
isolates one ingredient: **asking instead of guessing was worth about
27 percentage points of working behaviour.** That is the release's
headline number.

### The gate's honest limit — now measured, not just stated

One more result, and it is deliberately uncomfortable: **every repaired
diagram passed pumllint's quality gate — including the ones repaired
with wrong guesses.** That is not a newly discovered flaw; it is the
tool's known boundary, now demonstrated by measurement. The checker
verifies that a diagram *states* its decisions; it cannot verify the
decisions are *true*. Automated checking filters out missing and vague
content — catching what silently ruins AI-generated code — but only the
author, or actually running the result, can vouch for the content
itself. This is exactly why the product's claim language has always
said "method-convention complete", never "guaranteed correct".

### The honesty notes

- Predictions failed here too, on the record: the repairs did not reach
  the top maturity level as predicted (three deeply-damaged diagrams
  stalled one level lower — while their *code* nonetheless worked; the
  score errs conservative by design). And even with an author on call,
  the repairer still guessed small details 45 times instead of asking —
  "ask first" instructions cut guessing in half, not to zero.
- A new failure mode appeared: one author answer about retry behaviour
  became code that retries *forever* — it hung until the sealed sandbox
  killed it. Moral: repair changes what a reviewer must look at; it
  does not remove the reviewer.
- The "author" was an AI stand-in reading the true design, not a
  human — and the audit flagged 2 of its 255 answers for containing
  diagram notation they shouldn't have. Both facts are disclosed in the
  record rather than smoothed over.
- Cost of both arms together: about **$12** in AI usage fees.

For teams pointing AI assistants at diagrams, the practical rule this
measures is short: *let the AI repair structure from the gap report;
make it ask a human about content.* The step-by-step version lives in
[Using pumllint from a coding agent](agents.md).

---

## Part 5 — The impact, in four lines

1. **For users of pumllint:** the "block bad diagrams from AI work" gate
   now rests on real executed behaviour, across three AIs and two
   vendors — the strongest evidence available, with the boundaries of
   that evidence stated as carefully as the claims.
2. **For teams using AI on diagrams:** repair-by-guessing measurably
   backfires; repair-by-asking recovers the cliff — a ~27-point
   difference from one habit: the AI asks instead of inventing.
3. **For the project's credibility:** predictions were locked before
   results, several failed, and the failures are published as
   prominently as the successes.
4. **For everyone else:** AI graders agreeing with each other is
   *reliability*; only matching reality is *validity* — and this program
   measured a case where the first was high and the second was zero.
