# Review: the Legible systemic impact model v0.2, tested against the recreation experiment

*Dated record, 2026-10-28. Reviewer: a Claude Code session on the
maintainer's ask; one context, no subagent. Target: the handoff bundle
`legible-agent-review-handoff.zip` (sha256 `ff499f88…45f3`; its 20 files
verify against `target/SHA256SUMS`), model v0.2: 46 nodes, 70 signed
edges, 8 loops, 18 inventory rows. Baselines: site
`fdurieux/fdurieux.github.io` at `9ba9b09` (HEAD on the review date, and
byte-identical to the bundle's snapshot), pumllint at `d315c64`, J-F at
`635f989` (its data lane unchanged since the experiment's `8f6d6b0`).*

## Scope, and what this review is not

The handoff asks for a review against R01–R10. This review is narrower
and deliberately so: it tests the model's **cascade** — R06, R07 and R08,
and the edges, loops and claims under them — against one body of
evidence the model never saw. That evidence is this repository's
recreation experiment on J-F's daily asset load: the
code → kit → code round trip (`docs/recreate-experiment.md`), wave 2, the
fourth rebuild, the coverage register and the OpenWiki comparison. The
model's S3 pin is pumllint `9d728c8`, where `EVIDENCE.md` does not
mention the experiment, so every observation here is out of sample for
the model.

The experiment touches the **artefact → product** leg only. It ships
nothing and has no users, no deployments and no incidents. Quality in
use (`harm`, `exposure`) and all five DORA metrics are therefore **not
reached**. Nothing below supports or contradicts E14–E26 or E64–E66.
R01 is checked against the site at the pinned commit. R02–R05, R09 and
R10 are outside the test and are not reviewed.

Every number below was re-read from a primary file, not the prose
record:
- `results/{K,KminusUML,K2}/compare.json` (non-identical artefacts 22,
  22 and 11 of 157, recomputed);
- `results/K/diffs/` and `results/K2/diffs/` (the `export` refusal);
- `results/review/REVIEW.md` and `VERIFICATION.md` (25 and 12
  contradicted claims after the overturn);
- `results/coverage/UNREALISED.md`;
- `WAVE2_PREREGISTRATION.md` Results;
- `openwiki-2026-10-27/PREREGISTRATION.md` Results M1 and M2;
- J-F issues #305 and #309 (both open);
- J-F `src/jef/data/store.py`, executed under the pinned pandas 3.0.5.

## Verdict

**Fit for its stated purpose after specified corrections, for the
cascade.**

What the experiment corroborates:
- The model's hedges hold: propagation is conditional; downstream
  faults also arise independently; there is no universal multiplier;
  matching specs and tests prove nothing without an independent oracle
  (H4's challenge).
- Shared-premise concealment (C06) has a measured instance.

The cascade itself has three structural gaps, each tied to a measured
observation:
1. It flows in one direction only. Defects measurably travelled the
   other way: from code, through specs derived from code, into a
   rebuild.
2. It cannot represent attenuation by **which artefact is load-bearing**.
   Twelve diagram defects reached nothing, because contracts and
   scenarios carried the behaviour.
3. "Green" enters only through score-driven repair (R4). A green gate
   over drift is the more common case, and was measured: 25 contradicted
   claims under Level 5 100/100.

## Findings, by priority

### F1 — major — R06, R07, R08 · cascade (PDF p. 3; JSON `cascade`, E50–E55): the cascade has no reverse path, from code to derived artefacts

**Issue.** Every cascade edge runs from upstream intent to
implementation (`updef → deriveddef → codedef`). The only
non-upstream origin is a sentence in `cascade.limits` ("Some downstream
faults are introduced independently"). No node or edge carries it.

**Evidence, measured twice in one program.**

*`timestamp` units.*
- J-F's store derives `timestamp` as
  `stamped.astype("int64") // 10**6`. That arithmetic assumes
  nanosecond resolution.
- Under the pinned pandas 3.0.5, `pd.to_datetime` on ISO strings yields
  `datetime64[us, UTC]`. Executed here, the stored value is
  `1583107200` for 2020-03-02: seconds.
- Four artefacts state milliseconds: the schema comment, the helper's
  docstring (`_utc_midnight_ms`), J-F `docs/DATA_CONTRACT.md` §3 ("Unix
  ms") and OpenWiki's generated wiki (M2 row 060, graded NONE).
- The kit, derived from the logic, pins seconds as a requirement.
- The post-hoc reviewer agent believed the comment, and execution
  overturned its verdict (`results/review/VERIFICATION.md`).

One root defect therefore reached two derived artefacts, in opposite
directions: the kit copied the code, and the wiki copied the comment.
A third artefact, the reviewer's verdict, was stopped only by an
independent channel (execution). The origin is a **dependency change
downstream of the intent**. By the normative contract, the intent (ms)
is the correct side. J-F #304 has the owner's call.

*`export` on an absent series.*
- The original exits 1 with a raw pandas `AttributeError`.
- The round-1 kit was silent on this path. Arms K and K−UML both refused
  cleanly with `StoreError` (`results/K/diffs/s21_cli_refusals/cli_export_empty.json`).
- The closing round, derived from the code, wrote the crash into the
  spec as JDL-159; wave 2 added JDL-163 for `differential`.
- K2 then reproduced the traceback line for line
  (`results/K2/diffs/…/cli_export_empty.json`: `.dt.strftime` on the
  unguarded frame). The harness scored this as *closing* a divergence.
- J-F #305, which calls the same behaviour a defect, is open.

**Why it matters.** Reverse-engineered specs, generated wikis and
code-derived tests are now common derivation routes. On these routes
the cascade runs `codedef → deriveddef → (rebuild) codedef`, and a
code-calibrated oracle turns inheritance into a passing grade. The model
as drawn would attribute both defects to "upstream intent", which is
the wrong place.

**Correction.**
- Add a reverse edge `codedef → deriveddef` (+; mechanism "derivation
  treats implemented behaviour as intent"; condition "the derived
  artefact is calibrated to the implementation, not to independent
  intent").
- Add a source node for platform and dependency change feeding
  `codedef`.
- Draw both on p. 3.

**Verify.** Trace both instances above, node by node, on the revised
figure.

### F2 — major — R07 · C06, E52–E53, `detection`: concealment measured; detection came from a channel the model does not name

**Issue.** C06 ("shared wrong premises can make tests and code agree")
is labelled H overall.

**Evidence.**
- After the closing round, the kit's own suite (197/197, later 257/257
  on the original and on K2) agrees with the original, and so does K2,
  on a behaviour the owner's tracker calls a defect.
- The only thing that disagreed was an **independent derivation**. Two
  rebuilders, given a silent spec, chose the clean refusal, and both
  recorded it as an assumption (M11 = 0.5).
- `detection` and E57 offer "independent examples and reality checks".
  Diverse independent implementation (N-version disagreement) is a
  third channel, and the one that fired here.

**Correction.**
- Upgrade C06 to "M, bounded (one instance; premise originating in
  code)".
- Add *diverse independent derivation* as an input to `detection`,
  with the condition "divergences are triaged, not scored away".

### F3 — major — R06, R07 · `deriveddef`, E51, E03, A01: attenuation by redundancy and load-bearing role is not representable

**Issue.** `deriveddef` lumps "models, contracts, data definitions or
decisions". E51 (`deriveddef → codedef`) is conditioned only on scope.

**Evidence.**
- The kit's eight diagrams carry 12 claims the code contradicts
  (`results/review/REVIEW.md`, after the overturn).
- Three rebuilds from that kit matched the original on every
  behavioural metric: M1–M6 and M8 at 100 %, zero gate inversions.
- The ablation agrees: K−UML equals K on every behavioural metric.
- The diagrams moved structure only: M9, 5 of 14 against 1 of 14 of
  the original's test modules importing.
- The defects did not propagate because executable contracts and
  scenarios with exact strings dominated the rebuild.

The model's E03 rests on sequence-only codegen (S3), where the diagram
was the sole channel. In a multi-artefact handoff the same diagram
channel measured no behavioural effect.

**Correction.**
- Split `deriveddef` by role: behaviour-carrying artefacts (contracts,
  decision tables, executable examples) versus structural or
  explanatory ones (models, prose).
- Alternatively, add a moderator "load-bearing share / redundancy" on
  E51.
- Narrow E03's M label to "when the model is the consumer's only
  behavioural input".

The site's "Why this, and why now" paragraph makes the same unqualified
claim. That is a site finding, not a model defect: the measurement is
real, but its transfer to multi-artefact handoffs is now contradicted
by an ablation.

### F4 — major — R07, R08 · R4, E27–E28, `drift`, B2, A01: a green gate over drift is measured, independent of repair

**Issue.** `green` has one causal input: E27, from `repair`. Drift
reaches nothing but `knowledge` (E37) and `discrepancy` (E33).

**Evidence.**
- J-F's maintained data-lane set lints clean, scores Level 5 100/100
  and traces fully, yet carries **25 claims its code contradicts**
  (J-F #309). No repair loop was involved.
- The drift accrued as the code moved and the gate scored the set
  against itself (J-F trap T-0800).
- B2 is visible with its delay: discrepancies were confirmed and filed
  2026-10-23 (#304–#309), and all six are open on 2026-10-28.
- Five days is too short to read as B2 failing. It is the E34
  condition ("owners have capacity and incentives") waiting.
- No product defect is traceable to the 25: the code was never derived
  from them. That is consistent with F3's attenuation.

**Correction.**
- Add `drift → confidence` (+, "a passing structural gate over a
  drifted artefact"), so R4's false-assurance mechanism no longer needs
  repair to start.
- Raise A01's limit "diagram-code drift is not checked" from H to M,
  bounded: one maintained set, 25 contradicted claims.
- Name the drift check the experiment actually ran as a B2 instance: an
  agent reading the model against the code, adjudicated, spot-checked by
  execution (1 of 4 spot-checks overturned).

### F5 — moderate — R07 · `unknown`, E31, E32, `updef`: omission is the dominant defect class, and invention is not uniformly harmful

**Evidence.**
- Both round-1 spec-defect classes were omissions: the CLI surface and
  one refusal path.
- OpenWiki's wiki: claim precision 0.992 strict (127/128), coverage of
  the 163 requirements 0.245 strict and 0.926 lenient. No refusal
  requirement is FULL (0 of 21); 58 of 111 PARTIALs lack an exact
  message or output string.
- Accurate-but-incomplete is the shape a precision check cannot see.
- Rebuilders turn omissions into recorded assumptions: 65, 50 and 30
  for K, K−UML and K2; 117 and 94 for W-R1 and W-R2. The `unknown`
  stock is therefore countable.
- The one omission whose invention we can grade (`export`) produced
  *better* Q2 behaviour than the original, and was scored as a
  divergence.

**Correction.**
- E32's sign holds against *valid intent*, not against a reference
  implementation. Make `fidelity`'s measurement say which.
- Give `unknown` an operational indicator: assumption-register entries
  per artefact set.
- Add a completeness check (coverage of a requirement inventory) as a
  detection input distinct from precision.

### F6 — moderate — R02 · A08, A09, H3: two gate-specific limits now have measurements

**DMN (A08).** The round-1 kit's 13 decision tables show 0 gaps, 0
overlaps and 1 untyped output: the (`export`, absent) row had no
outcome. Gap analysis alone would have passed the very defect that cost
a closing round; output typing caught it (`WAVE2_PREREGISTRATION.md`).
The model's A08 limit ("do not infer gap/overlap verification from a
lint pass") is right but understates the problem: even a passing gap
analysis is insufficient.

**Trace (A09, H3).** `trace` reported 158/158 requirements verified
while 33 statements the kit specifies were never executed by any
scenario: the lock timeout, the leftover-file sweep, the 100-page
refusal and others (`UNREALISED.md` class B). Requirement-granular
"verified" hides clause-level gaps. This is H3's challenge measured:
link coverage is not a leading indicator.

**Correction.** Cite both as M, bounded, in A08 and A09, naming the
mechanism (output typing; clause-level coverage).

### F7 — moderate — R07, R08 · `detection`, practices P1–P8: measured interruption points the model does not list

- **Oracle calibration by mutation.**
  - The kit's suite was calibrated to 100 % on the original before any
    rebuild.
  - Planted mutant m1 failed 2 scenarios; m2 failed 11.
  - This tests the tests, the precondition for `detection` being
    effective rather than shared-premise.
  - Absent from P1–P8.
- **A bounded correction loop with measured convergence.** Spec
  defects per iteration ran 2 → 0 in one code-only revision. Non-
  identical artefacts fell 22 → 11, all 11 by construction. This is a
  measured B-loop, unlike B1–B3, which are H.
- **P2 measured.** The fourth rebuild refused to manufacture the two
  shell scripts the inputs named but never shipped, and reported 246
  rather than 257 on the unmodified suite. An unrunnable check was not
  passed silently.

**Correction.**
- Add oracle calibration as a practice feeding `detection`.
- Cite the closing round as M evidence for an early-correction loop.

### F8 — minor — R01 · inventory: states match; two notes

All 18 site rows map one-to-one onto A01–A18 with matching states
(covered/planned/open), and the site at HEAD is the pinned commit.

Two notes, neither a model error:
- **Drift classification.** The site's PlantUML row lists "Diagram-
  versus-code drift (planned)" under *what is missing*, while ROADMAP.md
  classes it *open*. The model discloses this. The experiment makes it
  the single best-evidenced gap in the inventory (F4).
- **Missing inventory rows.** The site has no row for vocabulary
  (glossary) or for property-based invariants. On this subject, 42 of
  60 recurring kit terms had no definition before wave 2. Under
  systemic element 1 ("frame and reframe"), the boundary note could say
  the inventory omits these.

### F9 — informational — R03 · DORA and quality in use not reached

The experiment produces no deployment, failure or recovery event, so
E14–E26 and E64–E66 stay H. The closing round's cost (one revision, one
rebuild) is rework, but not deployment rework (DRR); it should not be
cited as DORA evidence.

## Evidence map

One row per experiment observation, against the model element it bears
on. *Supports*: the observation is an instance of the element. *Qualifies*:
the element holds only under a condition the model does not state.
*Gap*: the model has no element for it. *Not reached*: the experiment
cannot speak to it.

| Observation (source) | Model element | Reading |
|---|---|---|
| Kit → rebuilds cell-identical on all behavioural metrics (compare.json K, K−UML, K2) | E51 `deriveddef → codedef` | supports (faithful implementation of represented intent) |
| K−UML = K on behaviour; diagrams move layout only (M9 5/14 vs 1/14) | E03, E51, A01 mechanism | qualifies: F3 |
| 12 kit diagram defects, no behavioural trace in any rebuild | `limits`: propagation conditional | supports; gap in structure: F3 |
| J-F Level 5 100/100 set with 25 contradicted claims | R4, E28, `drift`, A01 limit | supports A01 limit; gap: F4 |
| Timestamp: pandas pin → seconds; comment, docstring, contract, wiki say ms; kit says s | cascade direction, `codedef` sources | gap: F1 |
| JDL-159/163 written from code; K2 reproduces the crash; suite 257/257 | C06, E52–E53, H4 challenge | supports (measured instance): F1, F2 |
| K, K−UML refuse cleanly where the spec is silent; both flag it | `detection`, `unknown`, E32 | gap (diverse derivation), qualifies E32: F2, F5 |
| Spec-defect classes are omissions; OpenWiki precision 0.992 vs strict coverage 0.245 | `updef` (missing), C05 | supports "missing" as a defect type; gap (completeness check): F5 |
| DMN 0 gaps / 0 overlaps / 1 untyped output | A08 limit | supports, sharper: F6 |
| trace 158/158 verified; 33 specified statements unexecuted | A09 limit, H3 | supports: F6 |
| Mutant calibration m1 2, m2 11 | `detection`, P1–P8 | gap: F7 |
| Closing round 2 → 0 spec defects, 22 → 11 artefacts | `early`, E48, E58 | supports (bounded M for an early-correction loop): F7 |
| Fourth rebuild: 246 of 257 unmodified, externals refused | P2 | supports: F7 |
| Reviewer verdict overturned by execution | E57, `validation` | supports (execution as independent evidence) |
| J-F #304–#309 open 5 days after filing | B2, E34 | consistent; too short to read: F4 |
| No deployments, users, incidents | E14–E26, E64–E66, all DORA | not reached: F9 |

## Requirement coverage, for this test only

| Req | Covered here | Reading |
|---|---|---|
| R01 | yes | 18/18 rows and states match the site at `9ba9b09`; F8 |
| R02 | partly | A08 and A09 limits measured (F6); quality elements not reviewed |
| R03 | no | not reached (F9) |
| R04 | no | systemic-design elements not reviewed |
| R05 | partly | the artefact → product link is tested; the other links are not reached |
| R06 | yes | supported, with a missing reverse path (F1) and a missing role distinction (F3) |
| R07 | yes | amplification is not observed in this program; attenuation and concealment are (F2–F5) |
| R08 | yes | figure p. 3 cannot show F1, F3 or F4 as drawn |
| R09, R10 | no | not reviewed |

## Open questions

1. **Is the reference the intent?** F1 and F5 both turn on it. The
   experiment's oracle is the original program; J-F's owner has not yet
   ruled on #304 or #305. Until then, "fidelity" in this evidence means
   agreement with the original, and the model should say which it
   measures.
2. **Does attenuation by redundancy survive a kit whose executable layer
   is itself wrong?** F3 shows defective diagrams harmless *because*
   scenarios were correct. The common-mode case — the same defect in the
   requirement, contract and scenario together — is the model's C06
   prediction. It is untested except by the one instance F1 found, where
   the premise came from code. This is what a degradation test settles
   (README, "Next").
3. **Would amplification appear on a subject with dependants?** The data
   lane's outputs feed J-F's binning and R lanes. The experiment stopped
   at the seam frame, which the original's loader accepted bit for bit
   (M8). Spread (`reach`, `affected`) was never exercised.

## Bounds

- One reviewer context. The same session read the experiment's record
  and wrote this review; it did not write the model.
- One program, single runs per arm, as the experiment states.
- The evidence map is a reading, not a re-run. Only the store's
  timestamp arithmetic was executed afresh here.
- The handoff's PDF was read as text; the cascade PNG was not
  inspected beyond the PDF's p. 3.
