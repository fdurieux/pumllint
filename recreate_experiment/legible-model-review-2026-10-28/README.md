# The Legible systemic model, tested against the recreation experiment (2026-10-28)

A review of an external causal model — *Legible: systemic impact model*
v0.2, a 17-page model of how the tools and practices on
<https://fdurieux.github.io/> affect software quality and DORA metrics —
against the evidence this directory's experiment produced on J-F's daily
asset load. The model's evidence pin (pumllint `9d728c8`) predates the
experiment's entry in `EVIDENCE.md`, so the test is out of sample. Read
`REVIEW.md`; its findings F1–F9 are the record.

| path | what |
|---|---|
| `REVIEW.md` | scope, verdict, findings F1–F9 with sources, evidence map, R01–R10 coverage for this test, open questions, bounds |
| `target/SHA256SUMS` | the handoff bundle's own manifest (20 files, all verified); the bundle zip's sha256 is `ff499f885792e20e06d3bbca9fc1754381eade56b74312ac9cac5ddee91e45f3` |

The bundle itself is not committed: it is the maintainer's upload, and its
model JSON carries a link into a personal chat-library account. The
manifest pins what was reviewed.

## In one paragraph

The model's hedges survive contact with the experiment: propagation was
conditional, faults arose downstream independently, and matching
specifications and tests proved nothing without an independent oracle.
Its cascade, though, flows one way only, and the experiment measured two
defects flowing the other way — from code, through specs and docs derived
from code, into a rebuild that the harness then scored as converging (F1,
F2). It cannot represent the attenuation the diagram ablation measured,
where twelve diagram defects reached nothing because contracts and
scenarios carried the behaviour (F3). And its "green but wrong" loop
starts only from score-driven repair, while the measured case was a green
gate over drift: 25 contradicted claims under Level 5 100/100 (F4). The
experiment never reaches users or deployments, so every DORA path stays
a hypothesis.

## Next: degrading the kit (proposed, not pre-registered)

The review is observational. The open question it leaves (REVIEW.md,
question 2) is interventional, and the experiment's machinery answers it
cheaply: plant known defects in the kit, rebuild from the degraded kit,
grade against the frozen reference. Proposed arms, one defect site each,
three planted defects per arm (one wrong value, one missing rule, one
stale or ambiguous wording) in disjoint behaviours:

| arm | where the defects go | the model predicts |
|---|---|---|
| C | nowhere (undegraded kit, today's model) | the K2 baseline; removes the model confound |
| D1 | diagrams only | attenuated (F3) |
| D2 | requirements and contracts; scenarios intact | detected by the kit's own suite during the rebuild |
| D3 | requirements, contracts, DMN and scenarios, consistently | propagates and is concealed: suite green, reference red (C06) |
| D4 | scenarios only | measures which layer a rebuilder believes when they disagree |
| D5 | omissions across every layer | invention, recorded as assumptions (F5) |

Per arm, before any rebuild: which gates see the degradation — `pumllint`
lint, score and `trace`, `dmn_check.py`, `glossary_check.py`, and the
calibration run of the kit's suite on the original. After the rebuild:
M1–M7 against the reference, and for each planted defect whether it
propagated, was attenuated, or was flagged as an assumption. The planter
is a separate context from every rebuilder; the defect list stays hidden
until grading; the pre-registration is frozen by PR before anything is
planted.
