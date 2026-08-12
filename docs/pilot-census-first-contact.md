# First contact — the pilot census on a public wild corpus

*Dated evidence note, 2026-08-11. The read-only dialect census
(`tools/pilot_census.py`) ran end-to-end for the first time on a corpus
this repository did not author: 159 real third-party PlantUML files
from five public GitHub repositories. This is the ROADMAP's recorded
next action ("not code but measurement") executed on the nearest corpus
a cloud session can lawfully reach — it is **not** the pilot
organisation's corpus, so the pilot charter's phase 0 on the real
internal corpus, and every demand gate, stay open exactly as recorded.
Record: `pilot_results/first_contact/census.json` (aggregates,
corpus-relative paths) and `sources.json` (per-file provenance: repo,
path, pinned commit, license, URL). The harvested diagrams are not
redistributed here — mixed third-party licenses; metadata only, the
same posture as the untracked `corpus/wild` tier. No product behavior
changes; nothing is queued; scoring calibration and claim language are
untouched (frozen public contract).*

## Why this ran

README's 1.0 gate is "evidence that the score contract survives contact
with a foreign corpus", and the recorded next action (2026-07-30) is to
run the census before anything gates. The organisation-internal corpus
the pilot charter targets cannot reach this environment (and should
not: the census is designed to travel to the corpus, not the corpus to
the census — standalone-copyable, no network). What a session *can*
measure is first contact with real, foreign-authored material: how much
of the wild PlantUML dialect the parser understands, whether the
maturity contract stays honest on what it cannot see, and what would
fire on day one.

## The corpus

Anonymous read-only shallow clones at pinned commits; diagram trees
included, sprite/icon libraries and macro/theme definition files
excluded and counted (they are `.puml` by extension but library code by
content):

| Source (files) | What it is | Scope rule |
|---|---|---|
| hyperledger/aries-rfcs (39) | Protocol RFCs of a real project — working sequence diagrams | all diagram files |
| plantuml-stdlib/C4-PlantUML (71) | C4 sample + visual-regression diagrams | `samples/` + `percy/`; 32 theme/macro files excluded |
| awslabs/aws-icons-for-plantuml (37) | Vendor architecture-diagram examples | `examples/`; 861 sprite/library files excluded |
| plantuml-stdlib/Azure-PlantUML (8) | Vendor samples | `samples/`; 294 sprite/library files excluded |
| dcasati/kubernetes-PlantUML (4) | Kubernetes C4 samples | `samples/`; 44 sprite files excluded |

159 files, 174 diagrams (one file carries 16). Two candidate sources
contributed zero: `ddd-by-examples/library` and `edgexfoundry/edgex-docs`
keep only exported images in-repo — itself a wild-corpus datum (diagram
*sources* are rarer in public repos than rendered diagrams).

## What the census reported

Headline: **every file yielded at least one scoreable diagram** (no
hard parse failures), in 0.6 s total — runtime is a non-issue at corpus
scale. Recognition is the story:

- **Types:** unknown 103, sequence 61, state 5, class 2, usecase 2,
  activity 1. 59% of diagrams are dialect-invisible — almost entirely
  the C4-macro material.
- **Dialect markers:** 118/159 files use `!include`, 102/159 use
  preprocessor directives, 73/159 call C4 macros. Zero non-UML forms.
- **Coverage suspects:** 89 of 159 files (big file, few recognized
  elements) — the C4-macro corpus again.
- **Maturity:** Level 4: 31, Level 3: 35, Level 2: 8, Level 1: 100.
  No diagram anywhere reached Level 5 — wild diagrams do not carry the
  method conventions, as designed.
- **Findings:** 1,329. Top firing: GEN003 (inline skinparam, 191),
  GEN006/GEN007 (ownership tag / requirement ID, once per diagram —
  the conventions are unconfigured, which is what the charter's
  conventions workshop exists to fix), GEN001 (missing title, 119
  files), SEQ006, SEQ001.

Per source, the split is clean — the parser's home turf versus the
dialect wall:

| Source | n | L4 | L3 | L2 | L1 | median composite |
|---|---|---|---|---|---|---|
| aries-rfcs (sequence RFCs) | 39 | 21 | 15 | 2 | 1 | 85 |
| aws-icons examples | 37 | 7 | 16 | 3 | 11 | 80 |
| Azure samples | 8 | 3 | 3 | 0 | 2 | 88 |
| kubernetes samples | 4 | 0 | 1 | 3 | 0 | 80 |
| C4-PlantUML samples/percy | 86 | 0 | 0 | 0 | 86 | 95 |

## Two probes behind the numbers

**The zero-element cap carries coverage honesty — and the composite
does not.** A well-formed C4 container sample passes the syntax gate,
parses to **0 recognized elements**, and scores composite **95** —
every dimension vacuously clean because the parser saw nothing to
penalize — while the level is held at **1** by cap C4
(`element_count == 0` → "nothing modelled, nothing to assess",
`pumllint/scoring.py`). On foreign dialects the *level* is the honest
signal and the composite is vacuity; a corpus-median composite of 95
alongside 100 Level-1 diagrams is that in one line. This measures, at
corpus scale, what the C4-pack fit evaluation recorded on a sample
(Level 1 on well-formed C4) and bounds the prose-pipeline evaluation's
projection-completeness claim on foreign corpora: on this corpus the
bound is 41% of diagrams projected, 59% invisible.

**SEQ001's 65 critical findings are true to spec, not parser noise.**
Sampled on aries-rfcs (21 findings in 5 of its 39 files): participants
like `ca` and `PERSON` used without declaration — the wild style leans
on PlantUML's silent lifeline auto-creation, which is exactly the
ambiguity the rule exists to flag for codegen. Whether an organisation
tunes or keeps it is a calibration-week disposition, not a defect.

## What this establishes — and what it does not

Established: the census instrument works end-to-end on foreign material
at scale; the score contract's honesty mechanism on unparsed dialects
is the level cap, not the composite; and on public wild material the
dialect signals the demand-gated items wait for are loud — C4 macros in
46% of files (→ the C4/component parser pack), `!include` in 74% (→
include resolution).

Not established: **demand.** The gates wait for an adopter's census,
and a public corpus proves prevalence, not pull — the C4 pack and
include resolution stay demand-gated as recorded. Not established
either: anything about the pilot organisation's diagrams (phase 0 on
the real internal corpus remains the pilot's own first step, run where
the diagrams live), or any calibration change (advisory numbers;
nothing here moves scores, rules, or claim language). The corpus skews
toward sample galleries — aries-rfcs is the only source that is a real
team's working diagrams; a second wild sweep weighted toward working
project corpora is the natural extension if one is ever needed.
