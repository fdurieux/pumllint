# The ADR / arc42 ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `6b727fa` (v0.30.0).
Twenty-eighth in the series, and the **second** whose subject is already
inside the project — after Gherkin, one note earlier. ADRs are not a
neighbouring artefact class here: GEN007 is described in the catalogue as
*"Diagram references no requirement/ADR"*, DIM-TRC is *"title, id,
ownership, requirement/ADR links"*, and `ADR-\d+` is the worked example in
the CLI's own help text.*

**Verdict up front: nothing to adopt — and this note found a defect
instead. `pumllint trace --requirements-scan` does not work against
either of the two dominant ADR conventions, and when it fails it blames
the diagram.**

**Measured. Given a diagram whose note correctly cites `ADR-0001` and
`ADR-0002`, and an ADR directory in `adr-tools` layout
(`0001-record-architecture-decisions.md`) or MADR layout
(`0001-use-plantuml.md`), `--requirements-scan` builds an **empty
inventory** and reports:**

```
Requirement coverage: 0/0 covered — 0 uncovered, 2 unknown reference(s)

Unknown references (not in the inventory — a typo, or the inventory is stale):
  ADR-0001  ← order.puml [order-flow]:3
  ADR-0002  ← order.puml [order-flow]:3
```

**The references are correct. The ADRs exist. The diagnostic accuses the
diagram of a typo.** And with the gate on, `--fail-on-unknown-ref` **exits
1** — a build broken by a correctly-annotated diagram and a
correctly-maintained ADR directory.

**The cause is one line of design.** `scan_inventory` walks
`{.md,.txt,.adoc,.rst}` and matches the pattern against **file contents
only**. Both dominant ADR conventions put the identifier in the
**filename** and a plain human title in the body — `# 1. Record
architecture decisions`, `# Use PlantUML for design diagrams`. There is no
`ADR-0001` string anywhere in the file for the pattern to find. A layout
that *does* spell the ID in the body scans correctly (2/2 covered, exit
0), which is what makes this a real limitation rather than a
misconfiguration: **the feature works, on a convention almost nobody
uses.**

**And there is a precedent for the fix, inside this repository.** The
lint path already warns when its input yields nothing —
`warning: no PlantUML files found … — nothing was checked` — a contract
CLAUDE.md records explicitly, warning on stderr without moving the exit
code. `trace` has the same failure mode and no such warning: it errors
when *no* inventory option is given, and is silent when an option is
given and matches nothing. **The empty-inventory case is the same
condition and deserves the same sentence.**

*Bounds. Everything above was executed at `6b727fa` (v0.30.0) against
hand-written ADR directories in the two conventions. **The conventions
themselves are reproduced from their published templates as I understand
them, not fetched in this session** — the `adr-tools`/Nygard shape (`# 1.
Title`, Status/Context/Decision) and the MADR shape (YAML front-matter,
`# Title`, Context and Problem Statement / Decision Outcome). If a
project's ADRs *do* spell `ADR-0001` in the body, the feature works for
them; the claim here is about the two default templates. **No ADR tool
was executed** — `adr-tools`, `Log4brains` and `adr-manager` are named
from general knowledge, not run or version-checked, and no claim is made
about their current maintenance. arc42 is discussed as a documentation
template only. Per session scope no GitHub repository was read.*

## 0. Why this ran, and why it is not an expansion question

The Gherkin note (twenty-seventh) was the first in the series whose
subject was already a dependency. ADRs are the second, and the coupling
is tighter: Gherkin is used by the *test harness*, but ADRs are named in
the **product's own rule catalogue and CLI**.

```
GEN007  requirement-link  Diagram references no requirement/ADR
                          (dormant until a pattern is configured)
DIM-TRC                   title, id, ownership, requirement/ADR links
--pattern                 Requirement-ID regex (e.g. 'REQ-\d+|ADR-\d+')
```

So the expansion question — *should pumllint reach into this ecosystem?*
— is already answered yes, by design, years ago. The only useful question
left is the one the Gherkin note introduced: **does the thing we already
built actually work against the ecosystem as it exists?**

It does not, and §2 is the measurement.

## 1. The ecosystem

**ADRs** are short markdown records of an architectural decision, one per
file, numbered. Two conventions dominate:

| Convention | File | Body opens |
|---|---|---|
| **`adr-tools` / Nygard** | `0001-record-architecture-decisions.md` | `# 1. Record architecture decisions` |
| **MADR** | `0001-use-plantuml.md` | YAML front-matter, then `# Use PlantUML` |

> **Corroborated 2026-08-30 by running a real tool** — the bounds above
> say the conventions were "reproduced from their published templates as
> I understand them, not fetched", and that premise carries the whole
> finding and the shipped fix. npm's `adr-tools` 2.0.4, run for real,
> produces `docs/adr/0001-use.md` whose body opens `# 1. Use` — **ID in
> the filename, plain human title in the body, no `ADR-0001` string
> anywhere.** *Caveat: this is the npm `adr-tools`, a different project
> from Nygard's shell script, which is not distributed through a package
> registry. It corroborates the **convention**, not Nygard's specific
> implementation.*

**The identifier lives in the filename in both.** The body carries a
human title. This is not incidental: the number is the file's sort key
and its permanent handle, and the title is what a reader sees. Tooling
(`adr-tools`, `adr-manager`, `Log4brains`) generates and renumbers files
on that basis.

**arc42** is a different animal — a documentation *template* of twelve
sections, not an identifier scheme, and it has no linter and no
machine-readable form. It is relevant here only as the place ADRs
conventionally live (section 9, "Architecture Decisions"), and nothing in
this note bears on it beyond that.

**There is no ADR linter to compare against.** The vitality pattern the
Gherkin note recorded does not even get a chance to apply: the artefact
is prose in markdown, and its tooling is generators and viewers, not
checkers. That is a fourth shape, and it is unsurprising — there is
nothing in an ADR to check mechanically beyond front-matter.

## 2. Gap — measured, and it is ours

The corpus: one diagram citing two ADRs in a note, and three ADR
directories — the two real conventions and a control that spells the ID
in the body.

```
@startuml order-flow
title Order flow
note right
  Realizes ADR-0001 and ADR-0002.
end note
...
```

### 2.1 The two real conventions both fail

```
$ pumllint trace puml/ --pattern 'ADR-\d+' --requirements-scan adr-tools/
Requirement coverage: 0/0 covered — 0 uncovered, 2 unknown reference(s) — across 1 diagram(s)

Unknown references (not in the inventory — a typo, or the inventory is stale):
  ADR-0001  ← order.puml [order-flow]:3
  ADR-0002  ← order.puml [order-flow]:3
```

MADR: **identical output.** Control (`# ADR-0001: Use PlantUML…`):

```
✔ Requirement coverage: 2/2 covered across 1 diagram(s)                (exit 0)
```

### 2.2 The gate fires on correct input

```
$ pumllint trace puml/ --pattern 'ADR-\d+' --requirements-scan madr/ --fail-on-unknown-ref
exit=1
```

**A build failed. The diagram is right, the ADRs exist, and the tool says
the references are unknown.** This is the worst shape a finding can take
— not a missed defect, but a confidently reported false one.

### 2.3 The cause

```python
def scan_inventory(path, pattern):
    """Requirement IDs found by scanning a docs file or tree with ``pattern``.
    A directory is walked for {`.md`, `.txt`, `.adoc`, `.rst`} files in
    sorted order ... Matches use the whole-match text (group 0) ...
    """
    ...
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        ids.extend(m.group(0) for m in pattern.finditer(text))
```

**Contents only. The filename is never consulted.** For a convention that
keeps its identifier in the filename, the scan is structurally incapable
of finding anything.

### 2.4 The silence is the other half

An inventory that matches nothing is indistinguishable, in the output,
from an inventory that was never going to match. The empty case produces
no warning and **exit 0** (without the gate flag). Compare the lint path:

```
warning: no PlantUML files found in . (looked for .puml, .plantuml, .iuml, .wsd)
         — nothing was checked
```

CLAUDE.md records that as a contract: *"A new 'nothing was checked'
condition warns on stderr; it does not change the exit code."* `trace`
already errors when **no** inventory option is passed (`error: no
inventory given`). It has no equivalent for *an inventory option that
produced zero IDs* — which is the case a user actually hits.

**Two distinct defects, then**: a scan that cannot see the ID where the
ecosystem puts it, and a report that misattributes the consequence.

## 3. Boundaries

1. **Inside, not adjacent.** ADRs are already a first-class concept in
   the catalogue and CLI (§0). No expansion question exists.
2. **Filename as identifier.** §2.3. The boundary this project's
   implementation quietly assumed away.
3. **Prose with no checkable structure.** An ADR body is free text; there
   is no ADR linter because there is little to lint. pumllint should not
   become one.
4. **arc42 is a template, not a schema.** Nothing to integrate.

## 4. Overlap

`trace`'s coverage matrix and the ADR ecosystem meet at exactly one
point: **the identifier**. pumllint does not read ADR content, does not
model decision status, and should not. What it does is answer *which
diagrams realize which decisions* — and that requires only the ID to
resolve on both sides. §2 is the report that it currently resolves on
one.

## 5. Sense — three true things

**S1. The feature's design is right and its input assumption is wrong.**
Matching a configurable pattern against docs is the correct shape; the
error is scanning only contents.

**S2. The internal precedent settles the reporting half.** §2.4. The
project already knows how to say "nothing was compared" — it says it on
the lint path, and CLAUDE.md calls it a contract.

**S3. The series' method found a product defect.** Twenty-seven notes
produced boundary observations and refusals. Running the project's own
documented workflow against the ecosystem as it actually exists produced
a reproducible bug in under an hour. **That is an argument for the
method, and §9 records the uncomfortable corollary.**

## 6. Nonsense — three moves to refuse

**N1. "Parse ADRs."** Read status, supersession chains, decision content.
No — §3's boundary 3. The ID is the whole interface.

**N2. "Ship an ADR linter."** There is no defect class to check that
markdown tooling does not already cover, and it is a second artefact
class. The never-build lists across this series settle it.

**N3. "Just tell users to put the ID in the body."** This is the
documentation-shaped escape and it should be refused as a *primary*
answer: it asks every adopter to deviate from both dominant templates to
suit one tool. It is a reasonable *interim* note in the docs, and §7
records it as such — but the fix is on this side.

## 7. Fit — graded

### F1 — scan filenames as well as contents. **Recorded — and this note's own claim about it was wrong.**

> **Correction, 2026-08-29, applied when the fix was implemented.** This
> section originally said filename scanning "makes the documented workflow
> work against both dominant conventions". **It does not.** `ADR-\d+`
> matches neither the body *nor the filename* of `0001-use-plantuml.md`:
> the ID in the adr-tools and MADR layouts is `0001`, not `ADR-0001`, so
> the reference form and the inventory form are **different strings**, and
> no single regex reconciles them. §2's measurement stands; the proposed
> remedy was overstated, and §2.4's silence turns out to be the more
> important half.

One additional match target in `scan_inventory`: apply the pattern to
`f.name` as well as `f.read_text()`. Small, zero-dependency, no report
*shape* change — and it genuinely fixes the schemes that carry the whole
ID in the filename (`ADR-0007-use-plantuml.md`, `REQ-123.md`), which
today return an empty inventory and therefore report every correct
reference as unknown. That is a real and common layout, so the repair has
independent merit.

**What it does not do** is rescue a bare-number scheme whose diagrams
cite a prefixed form. For those, the honest answers are `--requirements`
with an explicit list, or a pattern matching both spellings — and, above
all, **being told the inventory is empty** rather than being told the
diagram has a typo.

### F2 — warn when the inventory is empty. **Recorded, and it is the cheaper half.**

`warning: inventory is empty — <n> reference(s) were compared against
nothing` on stderr, exit code unmoved, exactly matching the lint path's
existing contract (§2.4). Independent of F1 and useful even if F1 is
never done: it converts a misleading report into an accurate one.

### F3 — soften the "unknown references" wording. **Folded into F2.**

*"a typo, or the inventory is stale"* is a fair diagnosis when the
inventory is non-empty and a bad one when it is empty. F2's warning makes
the distinction without touching this string.

### F4 — an ADR rule pack, or ADR content parsing. **No.** N1, N2.

### Fit against declared constraints

| Constraint | Reading |
|---|---|
| **Zero dependencies** | F1 and F2 both satisfy it — stdlib only. |
| **Report shapes are contracts** | F1 changes report *content*, not shape; F2 adds a stderr line, which the lint path's precedent shows is contract-compatible. |
| **Exit codes are contracts** | F2 explicitly does not move them, per the existing "nothing was checked" rule. |
| **Demand-driven / Arc E bar** | **Neither F1 nor F2 is a feature request** — they are correctness of a shipped, documented feature. The demand bar governs new capability, not repair. |

## 8. SWOT

**Strengths (internal, favourable)**

- The ID-only interface (§4) is the right level of coupling and needs no
  revision.
- The fix for the reporting half already exists in the codebase as a
  pattern (§2.4, S2).

**Weaknesses (internal, unfavourable)**

- **A documented workflow does not work against the ecosystem's two
  dominant conventions** (§2.1), and **fails closed with the gate on**
  (§2.2).
- **The diagnostic misattributes the cause** to the diagram (§2.2).
- No test covers `--requirements-scan` against a realistic ADR tree —
  inferable from the fact that the behaviour ships.

**Opportunities (external, favourable)**

- None external. F1 and F2 are internal repairs.

**Threats (external, unfavourable)**

- **An adopter wiring `--fail-on-unknown-ref` into CI over a real ADR
  directory gets a red build and a message telling them their diagrams
  are wrong.** That is the realistic first-contact experience for the
  exact workflow the CLI's help text advertises with `ADR-\d+`.

## 9. Decision, recorded candidates, triggers

**Decision: no ADR or arc42 support beyond the identifier — unchanged.
Two internal repairs recorded, neither queued here, because both are
maintainer calls about a shipped feature's behaviour.**

**Never build:**

- ADR content parsing — status, supersession, decision text (N1, F4).
- An ADR rule pack or an arc42 conformance check (N2, F4).

**Recorded, not queued:**

1. **F1 — scan filenames as well as contents in `scan_inventory`.** The
   substantive repair. Small and stdlib-only, but it changes existing
   `trace` output and needs tests, docs and a decision about whether the
   JSON distinguishes filename from content matches.
2. **F2 — warn on an empty inventory**, stderr, exit code unmoved,
   matching the lint path's "nothing was checked" contract. Cheaper,
   independent, and useful on its own.
3. **A missing test** — `--requirements-scan` against a realistic ADR
   tree in both conventions. This is what would have caught §2 before
   release, and it is worth having whether or not F1 lands.
4. **An interim docs line** (N3) — that `--requirements-scan` matches
   file *contents*, so ADR schemes keeping the ID in the filename need
   `--requirements` with an explicit list until F1 lands. Honest, and
   explicitly not a substitute for the fix.

**Re-litigate on:** nothing external. **These are repairs to a shipped
feature, not ecosystem questions**, and the trigger for acting on them is
a maintainer's decision rather than an adopter's arrival — which is the
distinction §7's constraint table draws between the demand bar and
correctness.

## Related reading

- [The Gherkin / Cucumber ecosystem, evaluated](gherkin-cucumber-ecosystem-evaluation.md)
  — the first "already inside" note, one earlier; its cold-run finding
  and this note's §2 are the same method applied to different surfaces.
- [The prose-linting ecosystem, evaluated](prose-linting-ecosystem-evaluation.md)
  — where DIM-AMB's lexicons were situated; DIM-TRC gets the same
  treatment here.
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) —
  the note that first exercised GEN006/GEN007's carrier set.
