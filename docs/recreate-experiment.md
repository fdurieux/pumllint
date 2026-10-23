# The recreation experiment — code → spec kit → code, graded by the original

*Dated experiment record, 2026-10-23. Pre-registration frozen before any
kit, recreation or comparison run (`recreate_experiment/PREREGISTRATION.md`
at `5c1fa55`; results appended below its frozen text as the phases
completed). Subject: J-F's daily asset load — `src/jef/data/` (≈ 3 500
lines, eleven modules, two packaged TOML files) and the acquisition half
of `deploy/daily.sh` — read at `8f6d6b0` as an oracle and never changed.
Lab machinery, kit, recreations and results: `recreate_experiment/`.
Nothing here ships; nothing enters J-F.*

## The question, and the answer in one paragraph

Can a specification stack reverse-engineered from working code —
requirements as code, contracts, UML, Gherkin — carry enough for an
independent agent to recreate the code, and where exactly does it fall
short? **On this program: yes, to the cell.** A fresh agent given only
the code tree (no documentation, no tests) produced a kit of 158
EARS-form requirements with stable ids, 14 contracts and two JSON
Schemas, 8 PlantUML diagrams at Level 5 under the codegen profile, and
95 Gherkin scenarios that pass 178/178 on the original and catch two
planted mutants. Two further fresh agents, one with the diagrams and one
without, rebuilt the program from that kit alone. Against 157 reference
artefacts frozen from the original over its recorded provider fixtures,
**every exported seam frame, every stored series, every health verdict,
every sync summary and every exit code was identical** in both arms, with
zero gate inversions; the seam frame routes bit-identically through the
original's loader. What diverged was the command-line *surface* nobody
specified — help text, the usage line of a parser error — and one
refusal path the kit was silent on, where both rebuilds refused cleanly
and the original crashes. **Zero code defects; two spec-defect classes;
and the diagrams changed nothing measurable in behaviour** — they fixed
the module layout and API shape, which is exactly what the original's
own API-level tests then measured. *[Closing round and the post-hoc
diagram comparison: pending below.]*

## Why this ran

Every wave of the research program so far (the C4 ladder, W1–W5) ran
the model→code hop forward on toy systems, graded by a hidden suite. This
ran it round trip on a real, operated program with a perfect oracle: the
original. A divergence can therefore be attributed — the kit failed to
carry a fact (spec defect), the kit carried it and the generator missed
it (code defect), a scenario asserts the wrong thing (test defect), or
the original is wrong. The maintainer named the subject and set the
conditions: the kit derived from the code alone (no existing J-F diagram
or document used — the subject already carries a Level 5 model set for
this lane, and J-F's trap T-0800 says a green gate "scores the set
against itself, never against the code"), the original's tests hidden
from the reverse engineer, two recreation arms, a closing round
authorised in advance.

The design adopts the 2026-10-20 note *AI-Assisted Testing in
Spec-Driven Development* verbatim: the spec is the test oracle; atomic
requirements with ids; code and tests from separate contexts;
assumptions listed, never silently resolved; deterministic oracles;
generated artefacts with provenance.

## Design

Four phases, four contexts. **Phase 0 (this session)**: freeze the
pre-registration; build the reverse engineer's clean room — a copy of
the code tree with `docs/`, `tests/`, every README and the ROADMAP
absent, installable on its own; build the comparison harness and freeze
the original's outputs. **Phase 1 (fresh Opus 5 @ xhigh agent)**: derive
the kit from that tree; write a hidden provenance map; calibrate the
scenarios to 100 % on the original; plant two mutants and show the
suite catches them; pass three pumllint gates. **Phase 2 (two fresh
Opus 5 @ xhigh agents)**: rebuild from a copy of the kit, placed outside
every repository, with no repository or package name in the brief;
Arm K with the diagrams, Arm K−UML without; at most three runs of the
kit's own suite; an assumptions file and a read log as measured
outputs. **Phase 3 (this session)**: score both arms through a fixed
adapter interface against the frozen reference; triage every
divergence with the provenance map. The orchestrating session never
wrote kit content: it had read parts of J-F's data contract while
planning, which is why the reverse engineering went to a fresh agent.

**Oracles.** 24 scenario groups, 157 artefacts: first fill of every leg
over the nine recorded fixtures (two equities with real split and
dividend histories, a crypto composite, Binance klines), tail refresh
with revised cells inside and outside the window, a real 4:1 split
through the adjustment pass, the crypto end-guard, a universe `end` cap
and an inverted window, a paused asset, stale and fresh actions, the
cross-venue spread at and over its threshold, a phantom-split jump, a
zero-volume run, the Yahoo CSV import and export (10 400 rows), dry
runs, 22 refusal cases, 24 CLI surface cases, 8 chain cases with every
external command stubbed as the original's own tests stub them. Plus
the original's own in-scope tests replayed against each rebuild through
an import shim (M9, reported not gated) and the seam-invariance proof
through the original's loader (M8). Wall-clock values were normalised
(ISO stamps, the chain's run stamp and stage epochs, the actions
`last_updated` field, paths); two reference runs compare identical.

## The kit (Phase 1)

| Artefact | Count |
|---|---|
| Requirements (`requirements.json`, ids `JDL-001`–`JDL-158`) | 158: contract 48, ritual 27, arithmetic 22, refusal 19, cli 17, chain 13, verdict 12; basis both 112, logic 45, prose 1 |
| Contracts | 14 documents + 2 JSON Schemas with validating examples + the two shipped TOML files + the harness interface |
| Diagrams | 8: component, class, four sequence, one activity, one state |
| Scenarios | 95 in 11 features (178 cases), 148 synthetic fixtures |

Gates, re-run by this session with pumllint 0.34.0: lint clean at
`--fail-on info`; Level 5 (Method-complete) 100/100 on all eight;
`trace` 158/158 realised and 158/158 verified, with `--features` joining
the scenario tags — the requirements-as-code gate. The syntax gate did
not run (no renderer here). Calibration: 178/178 on the original;
mutant m1 (bar fetch moved before the actions refresh, store-invisible
by construction) fails 2 scenarios; mutant m2 (crypto end-guard removed)
fails 11. The subject tree was byte-identical to J-F after the run; the
read log stayed inside the clean room; no line of 50+ characters is
shared between the subject's source and any kit file.

The reverse engineer's hidden notes record where the source's comments
and its logic disagree — the kit states the logic: the store's
`timestamp` column holds Unix seconds under the pinned pandas while its
schema comment says milliseconds; `ingest_yahoo_csv` reports a row count
that includes the duplicate dates it then drops; the health module
documents an `actions_missed_k` knob the CLI never exposes; the injected
clock drives the actions gate's comparison but the stamp it reads is
always the real clock. These are observations about the original,
handed to J-F as findings (§ What goes back), not changes.

## Results (Phases 2–3)

Both recreators stopped after their second suite run at 178/178 (first
runs 175/178, the same chain scenario in both: multi-line inline python
broke the recording stub). Arm K laid out 13 modules as the component
diagram names them; Arm K−UML chose one module per contract, 12
modules. Assumptions: 65 and 50 entries.

| Metric | K | K−UML |
|---|---|---|
| M1 exported seam frames identical | 14/14 | 14/14 |
| M2 / M3 gate inversions | 0 / 0 | 0 / 0 |
| M4 status documents identical | 17/17 | 17/17 |
| M5 sync summaries identical | 14/14 | 14/14 |
| M6 stored series / actions files identical | 13/13, 2/3 | 13/13, 2/3 |
| M7 CLI exit codes / CLI text identical | 52/52, 38/52 | 52/52, 38/52 |
| M7 chain exit codes / call logs identical | 8/8, 1/8 | 8/8, 1/8 |
| M8 seam invariance through the original loader | PASS | PASS |
| M9 original tests, API-level: modules importing, cases passing | 5/14, 18/50 | 1/14, 0/5 |
| M9 original tests, chain (black-box) | 10/10 | 10/10 |
| Artefacts not byte-identical | 22/157 | 22/157 |

The 22 are the same set in both arms:

| Artefacts | Class | Finding |
|---|---|---|
| 9 `--help` outputs, 2 parser-error usage lines | **spec defect (cli)** | the kit carried flags, defaults and messages, not the argparse surface |
| `export` of an absent series | **spec defect (refusal)**, and an original observation | kit silent; the original exits 1 with a raw pandas `AttributeError`; both rebuilds refuse with a clean `StoreError`, and both listed the gap as an assumption |
| 2 unwrapped tracebacks | not a defect | same exception class and message; paths and the module prefix differ by construction |
| 7 chain call logs | not a defect | identical commands, arguments and exit codes; the inline metadata parser is spelled differently |
| 1 actions file | harness defect | the interface's "stored fields" read two ways; dates and ratios identical |

Code defects: 0. Spec-defect classes: 2 (12 artefacts). M9's API-level
failures are signature-level by construction — keyword names, return
shapes, module names the kit left free — and are reported as
pre-registered, not triaged.

**Expectations.** E1 confirmed (M1 100 %, both arms). E2 confirmed
(M2 = 0). E4 confirmed trivially — two spec-defect classes against zero
code defects — with the honest caveat that on 157 artefacts the kit left
almost nothing to diverge on. E5 confirmed: K−UML equals K on every
pre-registered metric; the diagrams' measurable contribution is the
module layout and API shape (M9: 5 against 1 original test modules
importing), not behaviour. E6 at the bar: of the two spec-defect
classes, one was flagged as an assumption in both arms, M11 = 0.5. E7
confirmed. E3 pending (§ Post-hoc).

## Closing round

*[Pending: the three cli/refusal gaps folded into the kit as dated
additions by the reverse-engineering agent; gates and calibration
re-run; a third recreation on the revised full kit; M1–M8 re-measured.]*

## Post-hoc: the kit's diagrams beside J-F's existing eight

*[Pending, taken last by design.]*

## What this does and does not show

- **Shown.** On a 3 500-line data layer with numeric, silent failure
  modes, a code-only reverse-engineered kit carried every behaviour the
  harness could observe: a different model, a different context, no
  access to the original, cell-identical output. The requirements-as-
  code gate (`pumllint trace` over diagrams and scenario tags) and the
  mutant calibration were cheap and decisive: the kit's own suite caught
  both planted defects before any recreation ran.
- **Shown, and uncomfortable for diagrams.** Removing the eight Level 5
  diagrams changed no behaviour. The W1 result — the written decision
  contract is the load-bearing artefact — holds on a real program: the
  arithmetic, the message strings and the scenarios did the carrying;
  the diagrams fixed names and layout.
- **Not shown.** Live-provider behaviour (provisional closes,
  pagination at scale, rate limits, timeouts), the lock timeout and the
  hand-run `load`/`sync-actions` paths are outside what fixtures and
  stubs reach; the kit declares them. One program, one domain, n = 1
  per arm: single runs, quoted as such. The reverse engineer and the
  comparison analyst were different contexts, but the comparison
  analyst and the pre-registration author were the same one.
- **The denominator problem.** Two spec-defect classes out of 158
  requirements says less about reverse-engineered specs in general than
  about this subject: a program whose comments already carry its
  decisions, written under a discipline that pins messages and
  arithmetic. The experiment should be repeated on a program with fewer
  comments before the "to the cell" claim travels.

## What goes back to J-F

Findings, never changes: `jef-data export` on an absent series exits
with a raw traceback; `timestamp` holds seconds where the comment says
milliseconds; the import row count includes dropped duplicates;
`actions_missed_k` is documented but not exposed; the injected clock
does not reach the actions stamp. *[Plus whatever the post-hoc diagram
comparison finds.]* Filed on the maintainer's go.
