# Pilot charter — pumllint on real diagrams (template)

*A fill-in-the-blanks charter for a first internal pilot: run the
diagram quality checker on one team's real diagrams, measure what
happens, and decide on evidence. Plain language throughout; technical
terms are defined where they first appear. Companion pieces:
[pilot-starter-config.toml](pilot-starter-config.toml) (the
configuration template) and `tools/pilot_census.py` (the read-only
corpus scan to run before anything gates). The measured evidence this
pilot builds on — and its limits — is summarised in
[the case for pumllint](case-for-pumllint.md) and
[the evidence, explained](evidence-explained.md).*

## Purpose — and the honest framing

pumllint's evidence comes from controlled experiments on scenario
diagrams: strong statistical links between diagram quality and the
correctness of AI-generated code, a measured "cliff" below Level 2, and
a measured rule about repair (structure can be fixed automatically;
missing *decisions* must come from the diagram's author). **What has
never been measured is this organisation's own diagrams.** This pilot
is that measurement. Charter it to produce a number either way — not to
confirm a foregone conclusion. That framing is also what makes the
result defensible to any internal validation or governance function.

## Roles

| Role | Who | Responsibility |
|---|---|---|
| Sponsor | *[name]* | Owns the "why now" message; receives the phase reports |
| Pilot lead | *[name]* | Runs the phases, keeps the log, owns the go/no-go data |
| Architect on call | *[name]* | Answers content questions (the measured must-have) |
| Finding-triage owner | *[name]* | Dispositions every recurring finding in calibration week |
| Pilot team | *[team]* | A **volunteer** team with real diagram pain or AI-generation ambitions — never a conscripted one |

## Scope and duration

*[N]* repositories from the pilot team, all PlantUML files; *[4–6]*
weeks; nothing blocks anyone's delivery until phase 3, and only
regressions block even then.

## Phases

**Phase 0 — census and conventions (week 1).** Run the read-only
dialect census: `python tools/pilot_census.py <paths> -o census.json`.
It reports how much of the house diagram dialect the tool understands
(files yielding nothing, big-file/few-elements suspects, C4-macro and
`!include` usage), the would-be finding histogram, and runtime at your
scale. In parallel, a 30-minute conventions workshop fills the three
organisation patterns in the starter config (ownership tag, requirement
ID, naming). **Exit criterion:** census reviewed; any dialect gap
(e.g. component diagrams, includes) logged as a known limit — not
discovered mid-pilot.

**Phase 1 — advisory (week 2).** `pumllint score <paths> -f html -o
report.html` in CI, report circulated to the team and sponsor. No
gate. Calibration triage runs per the config template's decision order;
the triage owner dispositions every recurring finding (fix / tune /
suppress / disable-with-reason).

**Phase 2 — ratchet (week 3).** `pumllint score <paths> --baseline
maturity.json` — today's levels become the committed baseline; CI fails
only when a diagram gets *worse*. No cleanup demanded.

**Phase 3 — floor (when the team agrees).** Add `--min-level 2`: the
evidence-backed cliff becomes the floor for the whole set.

**Phase 4 — optional, AI-generation scope.** For diagrams that actually
feed AI code generation: enable `profile = "codegen"` on those paths
and hold them to Level 5. Expect heavy findings on human-oriented
diagrams — that is the check working. Agents in the loop follow
[the agent recipe](agents.md): repair structure automatically, **ask
the author** for content (the measured ~27-point rule).

## When the full codegen machinery applies (the phase-4 scope test)

Not every diagram set or task warrants the codegen profile, acceptance
criteria and generation run records. The machinery exists to move work
across two measured gaps: the below-Level-2 cliff (16–25 percentage
points of executed correctness) and the ask-vs-invent gap (≈27
points). Apply the full treatment only where all three hold:

- **The output is kept.** The diagrams feed AI generation whose result
  ships or is maintained — not throwaway exploration.
- **The work recurs.** The set will be regenerated or revised, so
  gates and run records pay off after the first pass.
- **Wrong output is expensive.** Errors are costly to detect or rework
  (reviewer scarcity, audit obligations, downstream dependents).

Everything else gets plain prompting plus normal human review, with no
ceremony — record nothing, gate nothing. One reminder from the
evidence applies either way: the gate is an input filter, never a
content certifier — passing it means the diagram is machine-checkably
ready to consume, not that its content is right.

## The change checklist (ADKAR)

- **Awareness** — sponsor sends the "why now" in their own words, tied
  to a real local pain (review toil, an ambiguity incident, the AI
  push). The tool's docs argue the general case; only the sponsor can
  argue the local one. *[link to sponsor memo]*
- **Desire** — per-role what's-in-it-for-me: authors get a to-do list,
  not a grade; reviewers get typo/consistency catches before review;
  leads get the badge and trends. The ratchet is the anti-fear message:
  **existing diagrams are never retroactively failed.**
- **Knowledge** — one hands-on hour with the team: run the linter, read
  a gap report, do one `pumllint fix`, one inline suppression, one
  config tune. Per-role docs are already split — point each person at
  their page ([docs index](README.md)).
- **Ability** — the measured constraint: content decisions (guards,
  failure paths) need the *author*, not a guess — hence the architect
  on call, and hygiene-first gating. Mechanical findings are one
  command (`pumllint fix`).
- **Reinforcement** — a fortnightly 15-minute review of the HTML report
  with the sponsor; the badge on the repo front page; suppression-count
  watched (rising suppressions = the gate is being routed around — a
  conversation, not a punishment).

## Measures and decision gates (agree these BEFORE phase 1)

KPIs (the fuller measurement plan is in
[pumllint in the SDLC](value-in-the-sdlc.md)):

1. Census coverage: % of files yielding a scoreable diagram; suspects.
2. False-positive rate after calibration week (dispositions logged).
3. Level distribution at baseline, and its trend.
4. Regressions caught by the ratchet (each one is the gate earning its
   keep).
5. Suppression count and audit outcome.
6. Team temperature: would they keep it? (ask, verbatim, at the end)

Pre-agreed decision at week *[6]*: **expand** (a second team) if
coverage ≥ *[80%]*, post-calibration false-positive rate ≤ *[e.g. 1 per
20 findings]*, and the team votes keep; **continue with fixes** if a
dialect gap dominates (that gap becomes a concrete feature request —
see below); **stop** if the team routes around the gate even after
calibration — and record why, because that lesson is worth more than a
zombie mandate.

## Operational facts (for security/procurement review)

Single self-contained program, Python ≥ 3.11 standard library only — no
third-party components to audit. **No network access, ever**: nothing
leaves the machine; reports are deterministic offline files.
GPL-3.0-or-later licence (copyleft duties attach on redistribution,
not internal use); installable from the internal artifact proxy as
one wheel.
CI-agnostic: any runner that can execute a CLI and read an exit code
works (the published GitHub Action is a convenience, not a dependency).

## What this pilot may legitimately pull (and what it won't)

The tool's roadmap is demand-driven. Census findings map to known,
deliberately-unbuilt items: heavy C4/component usage → the
component/deployment parser pack; `!include`-based corpora → include
resolution; a non-GitHub CI → a runner recipe; an older SonarQube →
legacy import format. A pilot observation is exactly the "concrete
user pull" those items wait for — file it as such. What the pilot will
*not* change: scoring calibration and claim language (frozen, public
contract), and no AI opinion ever becomes a gate.
