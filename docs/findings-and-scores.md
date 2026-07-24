# Understanding findings and scores

*Audience: two groups who meet in the middle — architects/reviewers who
**receive** the reports, and modellers whose diagrams **get checked**. The
first half explains how to read what pumllint says; the second half explains
how to act on it.*

## Part 1 — Reading the reports

### Findings

Every finding is one rule firing at one location:

```text
order.puml:18  SEQ102 major  participant declaration has no role type
```

Severities and what they oblige you to do:

| Severity | Meaning | Typical CI effect |
|----------|---------|-------------------|
| `blocker` | Diagram is semantically broken or misleading | Fails the build; caps maturity at Level 2 |
| `major` | Violates a mandatory modelling standard | Fails the build at the default `--fail-on major` |
| `minor` | Violates a recommended convention | Reported, doesn't fail lint |
| `info` | Advisory; improves maintainability | Reported only |

These map 1:1 to SonarQube severities, so the same finding reads the same in
a Sonar dashboard.

Every rule has a stable ID (`SEQ003`, `CLS004`, …) and a rationale — the full
catalog with reasoning and acceptance examples is [RULES.md](../RULES.md);
the one-line summary table is in the [README](../README.md#rules).

### Maturity levels

`pumllint score` grades each diagram 1–5. What the levels *mean* in practice:

| Level | Name | Read it as |
|-------|------|-----------|
| 1 | Sketchy | A drawing. Don't build, review, or generate from it. Below Level 2 the measured code-generation cliff applies: fidelity drops ~⅓, invented logic doubles. |
| 2 | Structured | Syntactically sound and minimally coherent. A starting point. |
| 3 | Disciplined | No blockers; house conventions largely followed. Reviewable. |
| 4 | Precise | Complete and unambiguous where it matters (typed participants, guards, labels). Implementable by a human without guessing. |
| 5 | Generation-ready | *Method-convention complete*: every dimension strong, no majors, and the codegen rule pack actually ran. The diagram-side preconditions for faithful generation — not a guarantee of it. |

Behind the composite score are seven dimensions (completeness, ambiguity,
consistency, traceability, readability, semantic correctness, plus the
external syntax gate). Two things worth knowing as a reader:

- **Caps prevent gaming.** A single blocker caps a diagram at Level 2 no
  matter how high its composite; a single very weak dimension caps it at
  Level 3; a near-empty diagram cannot score at all. A high level therefore
  can't be bought by padding.
- **The model set is scored by its worst diagram.** One Sketchy diagram makes
  the whole set Level 1 — deliberately, because consumers of a model set
  can't know in advance which diagram they'll rely on.

### The gap report — the most useful part

Every score report is prescriptive: under each diagram, the exact findings
standing between it and the next level:

```text
order.puml [Order]: Level 3 (Disciplined) — 68/100
  To reach Level 4 (Precise):
    • DIM-CMP is 61, needs >= 70 — fix:
        SEQ102 major  order.puml:18  participant declaration has no role type
```

Read it as a backlog, not a verdict: fix the listed findings, re-run, level
goes up. There is no hidden judgment beyond the listed items.

### Trends, badge, HTML

- When CI ratchets against a baseline, reports carry trend annotations:
  `(Level 3 → 4 since last baseline)`, `(new since baseline)` — per diagram
  and for the model set.
- The repository badge shows the current model-set level (red = 1 …
  brightgreen = 5).
- The **HTML report** (`score -f html`, usually a CI artifact) is built for
  people who never run CLIs: model-set verdict first, then per-diagram cards
  sorted **worst-first**, each with dimension bars, its gap report, and
  trends. It is self-contained and deterministic — safe to attach to a
  review, diff between runs, or drop in a wiki.

## Part 2 — Acting on findings (for diagram authors)

### The working loop

```bash
pumllint score mydiagrams/          # where do I stand, and what blocks the next level?
pumllint fix mydiagrams/            # auto-fix the mechanical findings
# …fix the remaining gap-report items by hand…
pumllint score mydiagrams/          # confirm the level moved
```

`pumllint fix` handles only deterministic, semantics-preserving repairs —
naming an unnamed diagram from its file stem, inserting a humanized title,
declaring implicitly-created participants. Anything requiring *judgment*
(labels, guards, multiplicities) stays yours: the linter tells you **what**
is missing, it will not guess **which** value is right.

### What the rule families are trying to tell you

- **SEQ001–011 (sequence)** — mostly integrity: undeclared participants are
  *typo detectors* (PlantUML silently invents a lifeline for `Custmer`),
  unbalanced activations and unterminated blocks are flows that never
  finish. Labels and size limits keep the diagram reviewable.
- **ACT/CLS/STA/UC packs** — the same idea per diagram type: unreachable
  states, inheritance cycles, orphan actors, unlabelled decisions — things
  PlantUML renders happily but that make the model wrong or undecidable.
- **GEN (governance)** — identity and traceability: titles, names,
  ownership/requirement tags. Note that `owner-tag`, `requirement-link`,
  verb-first naming and similar convention rules are **dormant until your
  project configures its convention** — if they fire, the pattern they check
  is your organisation's, not the tool's.
- **XD (cross-diagram)** — active only when several diagrams are linted
  together: the same entity must keep one name, one kind, one stereotype
  across the whole model set. If XD004 flags `orderService` vs
  `OrderService`, the finding is about the *set*, not the line it happens to
  point at — align on one identity.
- **SEQ101–109 (codegen profile)** — opt-in, stricter meaning of "done":
  could a code generator implement this without inventing anything? Prose
  messages (`fetch the order details`) instead of signatures
  (`findOrderById(orderId)`), vague guards (`sometimes`), elision markers
  (`...`, `TBD`), missing returns and missing failure paths all count. These
  only run under `--profile codegen` — and Level 5 is only claimable when
  they do.

### Suppressions

When a finding is genuinely wrong for a specific spot, silence it **in the
source**, reviewably — not by disabling the rule project-wide:

```plantuml
' pumllint: disable=SEQ006, unlabelled-message   ← next line only
Batch -> Batch : self-trigger

' pumllint: disable-file=GEN003                  ← whole file
```

Rules can be referenced by ID or name. Be sparing: CI can audit all
suppressions at any time (`--no-suppressions` reports everything regardless),
and a suppression in a diff is a natural review conversation.

Suppressions are also visible in the score reports themselves: a diagram
whose findings were silenced shows the count next to its score — `100/100
(3 suppressed)` — in the text and HTML reports, and the JSON report records
it as `suppressedCount`. A perfect score earned by suppressing findings
never looks the same as one earned by fixing them.

### If you think a rule is wrong

Sometimes it is — for your context. The escalation ladder: suppress the one
occurrence (visible, reviewable) → tune the rule's options in
`pumllint.yaml` (most thresholds, patterns and whitelists are configurable) →
disable the rule (`rule-name: false`) → propose a change to the rule itself
(see [Writing rules](writing-rules.md); every rule's rationale and acceptance
criteria live in RULES.md, so the argument has a concrete anchor).
