# The C4 viewpoints / notation ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-28, written against `9e14f02` (v0.30.0).
Twentieth in the series, and the **second narrowing return** in two
turns: the C4 *ecosystem* was re-examined second (2026-08-27), as the
ArchiMate *notation* was settled third and its viewpoint mechanism
examined nineteenth. This note asks the question that one did not — what
C4 says about **its own levels and its own notation** — and finds that
the answer explains something the earlier note measured without
explaining.*

**Verdict up front: the settlement is unchanged — *fit verified, wait for
census pull*. Nothing here moves the decision, nothing new is proposed,
and no new defect is claimed. What the note contributes is a reason.**

**The C4 note measured that C4's 21-item review checklist is roughly
**40% mechanizable** from `.puml` text, and attributed the remaining 60%
to "the rendered picture". That is true and shallow. The deeper reason is
doctrinal, and it is stated on C4's own notation page:**

> **"The C4 model is notation independent, and doesn't prescribe any
> particular notation."**
>
> **"Any notation used should be as self-describing as possible, but all
> diagrams should have a key/legend to make the notation explicit."**

**C4 declines to specify a notation, so the picture is the only place a
free notation can be judged at all. The mechanizable residue is small
*because of the doctrine*, not incidentally — and the one rule that
survives into the source is the legend, which exists precisely *because*
the notation is free.** §5.1. That reframes the C4 pack's ceiling from an
accident of checklist authorship into a structural property of the model
it would check.

**The measurement is small and exact.** C4's single unambiguously
source-checkable requirement — *every diagram should have a key/legend* —
is invisible to pumllint in **both** of its spellings:

| | with legend | without | difference |
|---|---|---|---|
| PlantUML `legend`…`endlegend` | `sequence`, L4, 100.00 | `sequence`, L4, 100.00 | **none** |
| C4-PlantUML `SHOW_LEGEND()` | `unknown`, L1, 100.00, exit 0 | `unknown`, L1, 100.00, exit 0 | **none** |

**And pumllint already recognises the token.** `parser/sequence.py:91-92`
defines `RE_LEGEND_START` and `RE_LEGEND_END`, and the parser swallows the
block on purpose:

```python
# Legend blocks are display furniture: swallow until 'endlegend' so
# body text can never parse as live messages or participants.
```

So the C4 note's *"`SHOW_LEGEND()` is worth a rule"* would need **no
parser work for the PlantUML spelling** — the tokens are already
tokenised and deliberately discarded. §8.3. That is an implementation
fact the earlier note did not have, and it belongs to the candidate it
already recorded rather than being a new one.

*Bounds. **c4model.com is free and was read directly** — every C4
quotation here is from `c4model.com/diagrams/notation`, which is the
happiest access result in the series after DoDAF and FEAF, and a sharp
contrast with ArchiMate 3.2 and TOGAF one turn earlier. **No C4 tool was
executed**; C4-PlantUML's macro behaviour is inferred from pumllint's
reading of the file, not from rendering it. The three probe files are
mine. All pumllint claims were executed at `9e14f02` (v0.30.0) with
default config from a neutral working directory. Per session scope no
GitHub repository was read.*

## 0. What is already settled, and is not restated here

The C4 note (second in the series, 2026-08-27) re-examined and upheld the
2026-07-27 settlement: **fit verified, wait for census pull.** It is the
only ecosystem in twenty where a pack is fit-verified and waiting on
demand rather than refused — the ArchiMate note drew that contrast
explicitly, calling itself "a principled no rather than a wait-for-pull".

**Already on record, and not presented as new here:**

- **The legend rule as a candidate.** *"`SHOW_LEGEND()` is worth a rule: a
  declared legend is the mechanical proxy"*, and *"the decidable residue
  is one rule — is a legend declared?"*
- **Abstraction mixing**, recorded as a **PlantUML-only defect** — C4's
  own tooling prevents it by construction ("components can't be added to
  a container diagram"), C4-PlantUML does not.
- **The ~40% mechanizable figure** and its C2 correction.
- **The census exclusion guard** — 45% of the corpus is C4-PlantUML's own
  gallery, so the 46% marker reading must be cited with its composition.
- **The codegen amplification**, and the three claim-language
  corrections.

This note adds no measurement to any of those and proposes nothing they
did not already contain.

## 1. The doctrine

### 1.1 C4 is not a notation, and says so

From `c4model.com/diagrams/notation`, verbatim:

> **"The C4 model is notation independent, and doesn't prescribe any
> particular notation."**

and, on what follows from that:

> **"Any notation used should be as self-describing as possible, but all
> diagrams should have a key/legend to make the notation explicit."**
>
> **"Every diagram should have a key/legend explaining the notation being
> used (e.g. shapes, colours, border styles, line types, arrow heads,
> etc)."**
>
> *"Just make sure that any colour coding is consistent (within and
> across diagrams)…"*

C4 describes itself as a set of **hierarchical abstractions** — software
systems, containers, components, code — and its diagrams as **four levels
of zoom**, each showing *"a different amount of detail for a different
audience"*.

### 1.2 The levels are viewpoints in all but name — and carry no conformance

*"A different amount of detail for a different audience"* is ISO 42010's
viewpoint idea in plain words: a view framed for a stakeholder's concern.
C4 does not use the word, and — like ArchiMate one turn earlier — **it
defines no conformance**: nothing on the notation page or in the model's
own description says what makes a diagram non-conformant to its level, or
makes conformance an obligation.

**Two consecutive evaluations, two viewpoint-shaped mechanisms, neither
normative.** ArchiMate has 25 catalogued viewpoints with published element
subsets and still makes conformance no requirement; C4 has four levels
with no subsets at all. The pattern is worth naming once: **the
viewpoint-shaped thing in an ecosystem is reliably guidance, not a
contract** — which is exactly why a third-party linter adjudicating it
would be inventing an obligation.

## 2. Why the doctrine explains the ceiling

The C4 note established that of C4's 21 review-checklist items, roughly
**8 are cleanly mechanizable from `.puml` text**, 3 partially, and the
remaining 10 *"are about the rendered picture"* — colours, shapes, icons,
arrowheads, border styles, element sizes.

That is a correct description and an incomplete explanation. **The
checklist is picture-heavy because C4 refuses to specify a notation.**
When the shapes and colours are the author's free choice, the only things
left to review are (a) whether those choices were made sensibly, which is
a judgement about the rendered image, and (b) whether they were
*declared* — which is the legend.

So the split is not an accident of how Simon Brown happened to write a
checklist. **It is the shape any review guidance for a notation-independent
model must take**, and it puts a ceiling on what any source-level linter
can check about C4 — pumllint or otherwise — that no amount of parser
work moves.

This does not weaken the recorded C4 fit. The pack's value was never the
checklist coverage: the C4 note's own §7 grounds it in **tiers 2 and 3**,
which are "this project's own design and carry no external authorship".
What §2 does is stop the 40% figure being read as a coverage gap that
better engineering could close.

## 3. Overlap

| Concern | pumllint | C4 | Reading |
|---|---|---|---|
| Levels as viewpoints | no concept | four levels of zoom, per audience | Guidance, not contract — §1.2 |
| Notation | reads PlantUML text | **prescribes none** | §2: the ceiling |
| **Legend declared** | **parsed and discarded** (§8.3) | *"all diagrams should have a key/legend"* | **The one source-checkable rule**, already a recorded candidate |
| Abstraction mixing | invisible | prevented upstream by C4's own tooling | PlantUML-only defect, already recorded |
| Colour/shape consistency | none, correctly | *"consistent within and across diagrams"* | About the picture — unreachable |
| Aggregate verdict | levels + composite | none | Twentieth, no grader |

## 4. Boundaries

1. **No notation to conform to** (§1.1) — so there is no notational
   conformance check to build, only a legend-declared check.
2. **No level conformance defined** (§1.2) — same shape as ArchiMate's
   viewpoints one turn earlier.
3. **The ceiling is doctrinal** (§2), not an engineering limit.

## 5. Sense — four true things

### 5.1 The doctrine explains the measurement, which is this note's contribution

§2. The C4 note measured the 40%; this one says why it is 40% and why
that number is not going to improve. **The legend rule is not the small
leftover of a checklist — it is the only thing a notation-independent
model can ask of its source text**, and C4 asks for it emphatically and
for a stated reason.

### 5.2 pumllint already tokenises the thing it cannot check

§8.3. `RE_LEGEND_START` / `RE_LEGEND_END` exist at `parser/sequence.py:91-92`,
and the swallow is deliberate and commented — legends are *"display
furniture"*, discarded so their body text cannot be mistaken for
messages. That is the right call for a parser whose job is to find live
model content.

It also means the recorded legend candidate is cheaper than it looked for
the PlantUML spelling: the block is already located. (The C4-PlantUML
spelling `SHOW_LEGEND()` is a macro line and would need its own
recognition, which is the same macro-reading problem the C4 pack has
always faced.)

### 5.3 The honest Level 1 and the blindness are the same fact

A complete, well-formed C4-PlantUML container diagram — person,
containers, relationships, `SHOW_LEGEND()` — scores **`unknown`, Level 1
(Sketchy), 100.00, 0 elements, "✔ No issues found", exit 0**. Re-confirmed
at v0.30.0; the C4 note recorded this shape and it has not moved.

That is the *honest* outcome the type-fallback class is measured against —
and it is also exactly why the legend is invisible. **pumllint reads no
macro content, so it reads neither the containers nor the legend.** The
result the record celebrates and the gap this note measures are one
behaviour seen from two sides, which is worth stating plainly rather than
recording as two findings.

### 5.4 Access, ninth data point — and the best case

**c4model.com is free, unauthenticated, and was read directly.** After
ArchiMate 3.2 and TOGAF both behind Open Group SSO, and ISO 42010 behind a
paywall, the tally now runs: paid-with-preview (42010), gated-and-unread
(TOGAF), gated-with-readable-predecessor (ArchiMate), free-but-unread
(NAF), trademarked (Zachman), public-domain-and-read (DoDAF, FEAF),
subscription-and-unread (Gartner), **and openly published and read
(C4)**. The pattern holds: **how a body publishes predicts readability;
what it charges does not.**

## 6. Nonsense — five moves to refuse

**N1. Treating §1.1 as a reason to build the pack now. Refused.** The
doctrine explains the ceiling; it is not demand. The settlement's trigger
is an adopter census after the exclusion rule, a concrete user, or a
vendor closing the niche — and none of those is a page on c4model.com.

**N2. A "notation conformance" check. Refused on the doctrine itself.**
C4 prescribes no notation, so there is nothing to conform to. Any such
check would be enforcing *pumllint's* idea of a C4 notation against a
model that explicitly declines to have one.

**N3. A level-conformance check ("this container diagram contains a
component"). Refused, and it is already refused.** The C4 note recorded
abstraction mixing as a PlantUML-only defect inside the waiting pack.
§1.2 adds only that C4 makes no conformance obligation — the same result
the ArchiMate viewpoints note reached, and the same refusal.

**N4. Reading §5.3's Level 1 / 100.00 as a defect. Refused.** It is the
honest result. Cap C4 holds the level down and the report says there is no
modelled content. Quoting the 100.00 without the Level 1 and the zero
element count would misrepresent it in exactly the way the NAF note's N5
forbids for its own pair.

**N5. Presenting the legend measurement as a new finding. Refused.** The
legend rule is a recorded candidate from the C4 note. §8.3 adds an
implementation detail and a measurement of the current behaviour; it does
not add a candidate, and the record must not read as though a twentieth
note found a twentieth gap.

## 7. Fit — graded

### F1 — the C4 pack. **Unchanged: fit verified, waiting.** §0.

Nothing in this note moves it. §2 gives its ceiling a better explanation;
§5.2 makes one of its rules slightly cheaper.

### F2 — the doctrinal explanation of the 40%. **The contribution; nothing to build.** §2, §5.1.

### F3 — a notation or level conformance check. **No.** N2, N3.

### Fit against declared constraints

| Declared constraint | Where this lands |
|---|---|
| **Demand bar** | **Decides N1** — the settlement waits on the trigger, and doctrine is not demand. |
| **Claim language** | Untouched; the C4 note's three corrections stand and none is revisited. |
| **Golden score contract** | Untouched — nothing proposed changes scoring. |

## 8. Gap — measured

### 8.1 No discovery probe

C4 defines no file format; C4-PlantUML's discovery behaviour was measured
in the C4 note. Eighth note in the series with no §8.1 boundary
measurement.

### 8.2 The samples

Three files. A **PlantUML-native** container view with a
`legend`…`endlegend` block (three participants, four messages), and the
same file with the block removed. A **C4-PlantUML macro** container
diagram (`Person`, two `Container`, two `Rel`) with `SHOW_LEGEND()`, and
the same file without it.

### 8.3 The legend is invisible in both spellings

```
with_legend    type=sequence  Level 4  100.00  elements=7
no_legend      type=sequence  Level 4  100.00  elements=7      → identical output

c4_legend      type=unknown   Level 1  100.00  elements=0  ✔ No issues found  (exit 0)
c4_nolegend    type=unknown   Level 1  100.00  elements=0  ✔ No issues found  (exit 0)
                                                            → identical output
```

Both pairs produce byte-identical reports. **C4's one unambiguously
source-checkable requirement is currently unobservable**, whichever way it
is written.

The PlantUML spelling is the interesting half, because the tokens are
*not* unrecognised:

```python
# pumllint/parser/sequence.py:91-92
RE_LEGEND_START = re.compile(r"^legend\b.*$", re.IGNORECASE)
RE_LEGEND_END   = re.compile(r"^end\s*legend\s*$", re.IGNORECASE)

# :249-251
# Legend blocks are display furniture: swallow until 'endlegend' so
# body text can never parse as live messages or participants.
```

**The block is found and thrown away on purpose**, which is correct for a
parser hunting model content — and it means a *"is a legend declared?"*
rule for this spelling is a question the parser is already positioned to
answer.

### 8.4 What was not measured

**No C4 tool was executed** — nothing was rendered, so C4-PlantUML's
`SHOW_LEGEND()` output was not observed, only its invisibility to
pumllint. The 60% of the checklist that concerns the rendered picture was
not re-verified; §2 explains the C4 note's figure rather than re-deriving
it. No new census work was done, and the C4 note's recorded census re-run
(with the notation's own gallery excluded) remains undone.

## 9. SWOT

**Strengths (pumllint, internal)**

- §5.3: the honest Level 1 on macro-only files, re-confirmed at v0.30.0.
- §5.2: the recorded legend candidate is cheaper than it looked for one
  of its two spellings.

**Weaknesses (pumllint, internal)**

- §8.3: the one thing C4 asks of its source text is currently
  unobservable in both spellings.
- §2: and the ceiling above it is doctrinal, so no engineering closes it.

**Opportunities (external)**

- None new. F1 waits on the trigger it has always waited on.

**Threats (external)**

- None specific. The standing threat is the FEAF/Gartner note's, left
  open there.

## 10. Decision, recorded candidates, triggers

**Decision: the C4 settlement stands unchanged — fit verified, wait for
census pull. No new candidate, no new defect, nothing queued. Three
observations recorded, all of which attach to entries that already
exist.**

**Never build:**

- Anything premised on the doctrine being demand (N1) — the trigger is an
  adopter census after the exclusion rule, a concrete user, or a vendor
  closing the niche.
- A notation-conformance check (N2) — **C4 prescribes no notation**, so
  such a check would enforce this project's idea of C4 against a model
  that declines to have one.
- A level-conformance check (N3) — already inside the waiting pack as
  "abstraction mixing"; §1.2 adds only that C4 makes no conformance
  obligation, matching the ArchiMate viewpoints result.

**Recorded, not queued:**

1. **The doctrinal explanation of the 40% ceiling** (§2, §5.1) — the C4
   note's *"the rest are about the rendered picture"* is correct but
   incomplete. **C4 is picture-heavy in its guidance because it refuses to
   specify a notation**, so the source-checkable residue is small
   structurally and no parser work moves it. Attach to the C2 correction
   so the 40% is never read as a gap better engineering could close.
2. **The parser already tokenises legends** (§5.2, §8.3) —
   `RE_LEGEND_START`/`RE_LEGEND_END` at `parser/sequence.py:91-92`, with a
   deliberate swallow at `:249-251`. The recorded legend candidate needs
   no parser work for the PlantUML spelling; the `SHOW_LEGEND()` spelling
   remains the macro-reading problem the pack already has.
3. **~~Viewpoint-shaped mechanisms are guidance, not contracts~~** (§1.2)
   — **WITHDRAWN 2026-08-29 by the
   [Structurizr DSL viewpoints note](structurizr-viewpoints-evaluation.md),
   whose N4 refuses to carry it forward.** It was generalized from n = 2
   and n = 3 refutes it: Structurizr's views take a **typed scope
   argument** and derive their content from the model, so abstraction
   mixing is prevented **by construction** — a row *this note already
   recorded* and cited without noticing it cut against the
   generalization. The **ecosystem-scoped observations remain true**:
   ArchiMate publishes 25 viewpoints with element subsets and makes
   conformance no requirement; C4 has four levels of zoom and defines no
   conformance at all. **What does not follow is the law.** The
   replacement predictor is **derived views vs drawn views** — where
   content is derived, conformance is not unenforced but *vacuous* — and
   it is offered as a predictor to test, not as another generalization
   from three points. The practical rule (do not adjudicate viewpoint
   conformance) is unchanged, with two distinct reasons rather than one.

**Re-litigate on:** the C4 settlement's existing triggers, unchanged — an
adopter's own census after the exclusion rule, a concrete user with
hand-written C4-PlantUML asking for a gate, or a vendor shipping quality
checking for C4-PlantUML specifically. **Not** on anything in this note:
it explains the settlement's ceiling and does not touch its conditions.

## Related reading

- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — the
  settlement this note returns to; §2 explains its 40% figure and §8.3
  costs its legend candidate.
- [The ArchiMate viewpoints ecosystem, evaluated](archimate-viewpoints-ecosystem-evaluation.md)
  — the previous turn and the same shape: a viewpoint mechanism with no
  normative conformance; §1.2 pairs the two.
- [The DoDAF / UAF ecosystem, evaluated](dodaf-uaf-ecosystem-evaluation.md)
  — the other framework that frees the notation explicitly, and the one
  where doing so produced a reachable fit rather than a ceiling.
- [The ISO 42010 / viewpoint ecosystem, evaluated](iso42010-viewpoint-ecosystem-evaluation.md)
  — the viewpoint vocabulary §1.2 borrows.
- [ROADMAP.md](../ROADMAP.md) — the C4 settlement and its trigger.
