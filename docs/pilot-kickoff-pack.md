# Pilot kickoff pack — first contact with the real corpus

*Dated operational companion, 2026-08-11, to the
[pilot charter template](pilot-charter.md). The charter defines the
full pilot (phases, ADKAR, governance); this pack is what you carry
into the kickoff conversation: the measured case in sponsor-ready
sentences (current through W1b and the wild-corpus census, each with
its record), the 30-minute census runbook, and the short list of
inputs only the organisation can supply. Everything quotable here is
dated and scoped; nothing in this pack changes product behavior or
promises results on a corpus that has not been measured — that
measurement is the pilot's purpose.*

## The case, in four measured sentences (sponsor material)

1. **Below-Level-2 diagrams measurably break AI code generation:**
   16–25 percentage points of executed correctness, across three
   generators and two vendors, resistant to prompt scaffolding — and
   the effect survives an agentic test-and-repair loop (W5: a
   below-cliff artifact was not repaired by k ≤ 2 iteration at all).
   *(EVIDENCE.md; research-charter §6; W5 record.)*
2. **The highest-value artifact to pair with diagrams is a written
   decision table:** W1 measured the contract bundle at +37.9 pp
   executed; W1b decomposed the bundle and found the decision tables
   carry it — +40.9 pp added alone, the only component whose removal
   hurt, with the judged-invention cut localizing to them. Quote with
   its scoping: suite-relative, single-shot and k ≤ 2 agentic, one
   lab system, per-generator wording where required.
   *(W1_PREREGISTRATION.md, W1B_PREREGISTRATION.md § Results.)*
3. **More documentation is not more correctness:** past the knee,
   added detail measured at best nothing and at worst −26 to −32 pp
   on the cheaper generator (W4), and W1b found the same inside the
   contract bundle itself — removing the redundant companion files
   *improved* results on that occasion. One source per decision;
   stale duplicates get silently resolved, never flagged (W2: 0/18
   surfaced). *(W4/W2/W1B records; minimum-sufficient-stack.md.)*
4. **The gate is an input filter, never a content certifier:**
   passing means machine-checkably ready to consume, not right — and
   the measured recovery path for missing decisions is asking the
   author (≈ +27 pp), which no tool replaces.
   *(agents.md honesty section; EVIDENCE.md repair waves.)*

Honest boundary for any governance audience: every number above is
from controlled lab systems built for measurement. **Nothing has been
measured on this organisation's diagrams yet.** The pilot exists to
produce that number either way — charter it as measurement, not as a
foregone conclusion.

## The 30-minute first move: the census (runbook)

Read-only, offline, no gating, no install beyond the tool itself.
Whoever has repo access runs:

```
pip install pumllint          # or the internal artifact proxy
python tools/pilot_census.py <paths to diagram repos> -o census.json
```

(`pilot_census.py` is standalone-copyable — one file, standard
library only, drives the installed CLI; copy it anywhere the wheel
installs.)

It reports six things: file/diagram inventory and anything yielding
no scoreable diagram; coverage suspects (big file, few recognized
elements — the dialect-gap signal); dialect markers (`!include`, C4
macros, preprocessor use); the maturity distribution (advisory — no
gate); the rule-firing histogram (what calibration week will
disposition); and runtime at corpus scale.

Calibration reference from first contact with a public wild corpus
(159 real third-party files, 2026-08-11 —
[record](pilot-census-first-contact.md)): every file yielded a
scoreable diagram; runtime was ~0.6 s for the whole corpus, so scale
is a non-issue; plain sequence-diagram material landed Levels 2–4;
C4-macro material is dialect-invisible today (held at Level 1 by the
zero-element cap — expect this if the corpus is C4-heavy, and log it
as a known limit rather than discovering it mid-pilot; heavy C4 usage
in the census is precisely the demand signal the C4 parser pack
waits for).

**Exit criterion for this step:** census reviewed with the architect;
dialect gaps logged; go/no-go on chartering the pilot proper.

## The only inputs the organisation supplies

| Blank | What's needed |
|---|---|
| Sponsor | Owns the "why now" in their own words, tied to a local pain (review toil, an ambiguity incident, the AI push) |
| Pilot lead | Runs the phases, keeps the log, owns the go/no-go data |
| Architect on call | Answers content questions — the measured must-have (decisions need authors, not guesses) |
| Finding-triage owner | Dispositions every recurring finding in calibration week (fix / tune / suppress / disable-with-reason) |
| Volunteer team | Real diagram pain or AI-generation ambitions — never conscripted |
| Scope | N repositories, all PlantUML files; 4–6 weeks; org conventions (ownership tag, requirement-ID pattern, naming) for the 30-minute workshop |

## Phases and pre-agreed gates (condensed from the charter)

| Phase | What happens | Blocks anyone? |
|---|---|---|
| 0 — census + conventions (wk 1) | Runbook above + conventions workshop fills the starter config | No |
| 1 — advisory (wk 2) | HTML report in CI, circulated; calibration triage of every recurring finding | No |
| 2 — ratchet (wk 3) | Today's levels become the baseline; CI fails only on regression | Only regressions |
| 3 — floor (when the team agrees) | `--min-level 2` — the evidence-backed cliff becomes the floor | Below-cliff only |
| 4 — codegen scope (optional) | Diagrams that feed AI generation: `profile = "codegen"`, held to Method-complete; agents follow the repair-structure / ask-author recipe | That subset only |

Decide **before phase 1** and hold to it at week ~6: **expand** (second
team) if census coverage ≥ ~80%, post-calibration false-positive rate
≤ ~1 per 20 findings, and the team votes keep; **continue with
fixes** if a dialect gap dominates (that gap becomes the concrete
feature request); **stop** if the team routes around the gate even
after calibration — and record why.

## What to mandate for AI-feeding diagrams (phase 4, post-W1b form)

Dated, suite-relative, per-generator scoping as recorded: a task
brief; the structure diagram; **one behavior artifact — a PlantUML
sequence diagram at Level ≥ 2, Method-complete under the codegen
profile for generation inputs** (carrier defensible on outcome
evidence, not just tooling); **decision tables for every idiosyncratic
numeric rule — the measured load-bearing component**; acceptance
examples where the cheaper generators run at scale (their biggest
per-token lever). Keep every decision stated exactly once and stop
writing at the knee — over-specification measurably harms the models
an adopter actually runs at scale. The full measured answer, with
every scoping: [minimum-sufficient-stack.md](minimum-sufficient-stack.md).

## Security & procurement facts (one block)

Single self-contained program, Python ≥ 3.11 standard library only —
no third-party components to audit. No network access, ever; reports
are deterministic offline files. GPL-3.0-or-later licence (copyleft
duties attach on redistribution, not internal use); installable from
the internal artifact proxy as one wheel. CI-agnostic (any runner that
executes a CLI and reads an exit code). Scoring calibration and claim
language are a frozen public contract; no AI opinion ever becomes a
gate.

## What the pilot may pull — and what it won't change

Census findings map to deliberately-unbuilt items and are exactly the
"concrete user pull" those items wait for: heavy C4/component usage →
the component/deployment parser pack; `!include` corpora → include
resolution; a requirement-ID convention from the workshop →
`pumllint trace` adoption (already shipped); a review-aid ask →
the verbalizer arc; an architect iterating config in calibration
week → shadow-config. What it will not change: scoring calibration,
claim language, and the no-AI-gates rule.
