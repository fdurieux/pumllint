# The policy-as-code ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `14fce84` (v0.30.0).
Thirtieth in the series. Policy-as-code was named as a candidate two
notes ago and deferred when its canonical engine turned out not to be
runnable here; this note runs the part that is, and says plainly what it
did not run.*

**Verdict up front: no adoption — the artefact is infrastructure
configuration and the niche does not overlap. But this note produces two
findings that are about *this project*, and the first of them corrects
the note immediately before it.**

**THE CORRECTION. The Semgrep note (twenty-ninth) concluded that "the
boundary is state, not vocabulary", and that a declarative rule layer for
pumllint "is viable for the lexical tier and nothing above it". Measured
here, that is too strong.** A checkov custom policy — **pure YAML, no
code** — expressed a cross-entity relationship and discriminated
correctly:

```yaml
definition:
  cond_type: connection
  resource_types: [aws_instance]
  connected_resource_types: [aws_security_group]
  operator: exists
```

```
PASSED for resource: aws_instance.connected     # references a security group
FAILED for resource: aws_instance.orphan        # references none
```

**That is SEQ001's exact shape** — *this entity is used but never
connected to the thing that declares it* — and Semgrep could not do it
(2 findings where 1 was correct). Control: remove the reference from
`connected` and all three resources fail, so the check is reading the
**reference graph**, not names.

**The accurate boundary is narrower than "state".** A *pattern-matching*
rules-as-data format (Spectral's JSONPath-plus-function, Semgrep's
patterns over text) cannot carry cross-entity state. A *graph-query*
rules-as-data format, evaluated against a **parsed model with identity
resolution**, can. The discriminator is not data-versus-code; it is
**what the rule is evaluated against** — text positions, or a resolved
graph. pumllint already has the resolved graph (`diagram.participants`,
`diagram.blocks`, the batch), so the Spectral note's F2 is **less narrow
than one note ago**: a graph-query-shaped declarative format could reach
rules the Semgrep note assigned to code.

**The second finding: the ratchet, converged — and the divergence is the
grading gap in a second mechanism.** checkov ships `--create-baseline` /
`--baseline`, measured working exactly like pumllint's: record the
current state, accept it, fail only on regression.

| | records | accepts | new violation |
|---|---|---|---|
| `checkov --create-baseline` → `--baseline` | `.checkov.baseline` | **exit 0** | **exit 1, only the new one** |
| `pumllint score --baseline` | per-diagram levels | exit 0 | exit 1 on regression |

**But they ratchet different things: checkov ratchets a *finding set*,
pumllint ratchets a *level*.** checkov cannot ratchet a level because it
does not compute one — its summary is `Passed checks: 20, Failed checks:
3, Skipped checks: 0`. So the grading gap this series has recorded across
six ecosystems reappears here not as a missing report but as a **missing
axis for an existing mechanism**. Same idea, and the aggregate is the
thing only one of them can ratchet.

*Bounds, and the first one is load-bearing. **OPA, Rego and Conftest —
policy-as-code's canonical stack — were NOT run.** The engine is a Go
binary; `openpolicyagent.org/downloads/...` resolves (checked) to a
GitHub release asset, and this session's scope keeps me away from that,
as it did when this ecosystem was first deferred. **Nothing in this note
is a behavioural claim about Rego**, and the correction in §4 rests on
checkov alone. **checkov 3.3.16 was installed from PyPI and executed**;
every count, exit code and finding below is a run. The corpus is one
Dockerfile and one Terraform file, hand-written. Policy count is table
rows from `checkov --list`. Per session scope no GitHub repository was
read.*

## 0. Why this ran, and what it is not

Policy-as-code was ranked as a remaining candidate at the end of the
twenty-ninth note and set aside in the same breath: the canonical engine
could not be obtained through a package registry, and writing the note
from documentation would repeat the error the BPMN re-examination
corrected. That reasoning still holds for Rego.

It does not hold for the ecosystem as a whole. **checkov is
policy-as-code, not a stand-in for it**: policies as data, a CI gate,
severity-based fail rules, a baseline, and custom policy authoring. It is
pip-installable, so the parts of the question that need execution can
have it.

This note is therefore narrower than its title in one specific way, and
§1 says exactly where.

## 1. The ecosystem

| Layer | Example | State here |
|---|---|---|
| **Engine + policy language** | OPA / Rego, Conftest | **Not run.** Go binary; download resolves to a GitHub release asset. Read-only knowledge, and no claims made. |
| **IaC policy scanner** | **checkov 3.3.16** | **Executed.** ~**7,973** shipped policies across Terraform, CloudFormation, Kubernetes, Docker, ARM, Bicep and more |
| **Custom policy authoring** | checkov YAML + Python | **Executed** (§4) |
| **Gate mechanics** | `--soft-fail-on`, `--hard-fail-on`, `--check`, `--skip-check`, `--baseline` | **Executed** (§2, §3) |

**7,973 policies against this project's 51** is the largest catalogue in
the series by an order of magnitude, and the comparison is not meaningful
as a count: checkov's policies are one-per-cloud-resource-property across
many providers and frameworks, where pumllint's are one-per-defect-class
over one notation. The number is worth recording only to make that point.

## 2. Policy-as-code as a gate — measured

```
$ checkov -d iac --framework dockerfile --compact
Check: CKV_DOCKER_7: "Ensure the base image uses a non latest version tag"
	FAILED for resource: /Dockerfile.FROM
	File: /Dockerfile:1-1
	Guide: https://docs.prismacloud.io/...
...
Passed checks: 20, Failed checks: 3, Skipped checks: 0            (exit 1)
```

Three things worth naming.

**It reports passes as well as failures.** Every previous checker in this
series — `bpmnlint`, Spectral, `dmnlint`, `gherkin-lint`, Semgrep,
pumllint — reports only findings. checkov shows the whole check surface,
20 passed alongside 3 failed. That is a different theory of what a report
is *for*: evidence of coverage, not just a defect list. Worth recording
because it is the first genuine alternative to the findings-only shape
the series has treated as universal.

**The gate is severity-shaped and finely configurable.**
`--soft-fail-on`, `--hard-fail-on`, `--check`, `--skip-check` — a richer
gate surface than `--fail-on`, aimed at the same job.

**No grading.** `Passed checks: N, Failed checks: N, Skipped checks: N`.
Counts, no level, no aggregate. **Sixth ecosystem, and the first where a
denominator was available and still not used** — checkov knows how many
checks passed, which is exactly the input a score would need, and
computes no score from it.

## 3. The ratchet — converged, and divergent in the interesting way

Measured, in three steps:

```
$ checkov -d iac --framework dockerfile --create-baseline     # 3 failures recorded
$ checkov -d iac --baseline iac/.checkov.baseline             (exit 0)   # accepted

# add a new violation (ADD with a remote URL)
$ checkov -d iac --baseline iac/.checkov.baseline
Passed checks: 0, Failed checks: 1, Skipped checks: 0         (exit 1)
	FAILED for resource: /Dockerfile.ADD
```

**Record, accept, fail only on regression.** That is pumllint's ratchet,
independently arrived at, in a different artefact class — a **second
unsolicited convergence** after `bpmnlint`'s rule catalogue, and on a
mechanism rather than a rule.

**And the divergence is the more interesting half.** pumllint's
`--baseline` ratchets **per-diagram levels**; checkov's ratchets a
**finding set**. checkov could not ratchet a level if it wanted to,
because it computes none.

So the no-grader observation, which has until now been about a *missing
report*, shows up here as a **missing axis on a mechanism both projects
have**. Two tools independently decide that "don't get worse" is the
right gate for an existing codebase; only one of them has an aggregate to
say "worse" about. That is a sharper statement of what the maturity model
buys than the count of ecosystems lacking one — and it is still
two-sided, per the Spectral note's recorded caution: an aggregate nobody
else builds may be a differentiator or may be a thing nobody wanted.

## 4. The correction to the Semgrep note

### 4.1 What that note concluded

> **The boundary is state, not vocabulary.** … pumllint's rules run
> against a **parsed model**, so rungs 2–4 are ordinary code. A rule that
> is a *pattern* has, by construction, only the match.
>
> **A declarative rule layer for pumllint is viable for the lexical tier
> and nothing above it.**

The first sentence is right. **The second does not follow from it**, and
this note is the counter-example.

### 4.2 The measurement

A custom checkov policy, authored as YAML with no code, over a Terraform
file with one instance that references a security group and one that does
not:

```yaml
metadata:
  id: "CKV2_CUSTOM_1"
  name: "Instance must be connected to a security group"
definition:
  cond_type: connection
  resource_types: [aws_instance]
  connected_resource_types: [aws_security_group]
  operator: exists
```

```
Passed checks: 2, Failed checks: 1
	PASSED for resource: aws_instance.connected
	PASSED for resource: aws_security_group.web
	FAILED for resource: aws_instance.orphan                       (exit 1)
```

**Control** — remove the reference from `connected` too, and all three
fail. The policy is reading the resolved reference graph, not names.

Set beside this project's ground truth for the same shape:

```
two.puml:5: [SEQ001/critical] Participant 'S' is used but never declared
```

**Both are "entity X must be connected to entity Y in the parsed
model."** One is data; one is code.

### 4.3 The corrected boundary

The discriminator is not data-versus-code, and it is not state in the
abstract. It is **what the rule is evaluated against**:

| Format | Evaluated against | Cross-entity state |
|---|---|---|
| Spectral (JSONPath + 13 functions) | a document tree, per node | **No** |
| Semgrep patterns (generic mode) | text positions | **No** |
| **checkov graph checks (YAML)** | **a resolved resource graph** | **Yes** |
| pumllint rules (Python) | a parsed diagram model + batch | Yes |

Spectral and Semgrep fail the same rung for the same reason — they match
against *positions in text or a tree*, with no identity resolution to
query. checkov's YAML is evaluated against a graph checkov built first,
in which `aws_security_group.web.id` has already been resolved to an
edge. **Given a resolved graph, a declarative format can ask relational
questions of it.**

### 4.4 What this does to F2

The Spectral note's declarative-rule-layer candidate was narrowed one
note ago to "lexical tier only". **That narrowing was wrong, and the
honest position is between the two:**

- The **lexical tier** (SEQ105/106/109/103 lexicons, GEN008 *[misfiled:
  structural — see the Semgrep note's 2026-09-03 correction]*) — expressible
  in any of these formats.
- The **relational tier** (SEQ001/SEQ101 declaration-versus-use, orphan
  and unused-participant checks, plausibly parts of XD) — expressible in
  a **graph-query** format over pumllint's existing parsed model, on this
  evidence.
- **Not established either way**: ordering and structural rules (ACT001/2
  terminals, activation balance, fragment nesting), which are questions
  about *sequence* rather than *connection*, and which checkov's
  `cond_type` vocabulary gives no reason to think a connection-query
  covers.

**F2 is therefore bigger than one note ago and still not sized.** The
measurement it needs is unchanged and still does not exist — a per-rule
classification of the catalogue — but it now needs **three** buckets
rather than two, and this note deliberately does not guess the split.

**None of this makes F2 a better idea, only a better-understood one.**
Demand is still absent; the Spectral note's costs (a second authoring
path to document and support) are untouched.

## 5. Boundaries

1. **Artefact class.** checkov's subject is infrastructure
   configuration — Terraform, Kubernetes, Dockerfiles. Nothing in 7,973
   policies addresses a diagram, and nothing in pumllint's 51 addresses a
   cloud resource. **No functional overlap at all**; the overlap is
   entirely architectural.
2. **Evaluated-against.** §4.3. The boundary that actually governs which
   rules a declarative format can express.
3. **Findings-only vs coverage reporting.** §2. A genuine design fork,
   not a defect on either side.
4. **What can be ratcheted.** §3.

## 6. Sense and nonsense

**S1. The ratchet is a second unsolicited convergence** (§3), and on a
mechanism rather than a rule — a different kind of evidence from
`bpmnlint`'s catalogue.

**S2. The series corrected itself again, one note later** (§4). That is
now the fourth time: the viewpoint generalization, the BPMN ambiguity
dimension, the ADR filename claim, and this. The method's value is
visibly in the *sequence* of notes, not in any one of them.

**S3. Reporting passes is a real alternative** (§2), and this is the
first note to meet it.

**N1. "Adopt a graph-query rule format."** §4.4 explains what it could
reach; it does not argue anyone wants it. The demand bar is unchanged and
unmet, and building an authoring format on the strength of a
counter-example would be the same error the Semgrep note made in the
opposite direction.

**N2. "Lint IaC" / "add policy-as-code checks."** Boundary 1. The niche
is occupied by a 7,973-policy tool and the artefact is not this
project's.

**N3. "Report passes too, like checkov."** A design fork worth knowing
about, not a gap. pumllint's `score` already answers "how good is this?"
with an aggregate; a pass list would be a third answer to a question two
mechanisms already cover.

## 7. Fit — graded

| Fit | Verdict |
|---|---|
| **F1** — an IaC/policy rule pack | **No.** N2, boundary 1. |
| **F2** — a declarative rule-authoring layer | **Re-scoped, still recorded, still demand-gated.** §4.4: bigger than the Semgrep note said, smaller than unbounded, and now needing a three-bucket classification to size. |
| **F3** — report passed checks alongside findings | **No.** N3 — a design fork, and `score` already covers the question. |
| **F4** — anything Rego-shaped | **Not evaluated.** The engine was not run; no verdict is offered. |

## 8. SWOT

**Strengths**

- The ratchet is independently converged-on by a mature tool in another
  artefact class (§3).
- pumllint's parsed model is **already the substrate a graph-query rule
  format would need** (§4.3) — the capability exists; only the authoring
  surface would be new.

**Weaknesses**

- **The series published a boundary claim that was too strong and needed
  correcting one note later** (§4.1). The Semgrep evidence was sound; the
  generalization from it was not. This is the same failure shape as the
  withdrawn viewpoint generalization, and it recurred despite that entry
  existing — worth recording as a habit to watch, not just an incident.
- F2 remains unsized after two notes that both touched it.

**Opportunities**

- None external. §4.4 is an internal clarification, not a market.

**Threats**

- **Over-reading §4.** "A YAML format can express SEQ001" is true and
  narrow. It says nothing about ordering rules, nothing about demand, and
  nothing about whether a second authoring path is worth its
  documentation cost.

## 9. Decision, recorded candidates, triggers

**Decision: no adoption, no IaC pack, no Rego verdict. Two internal
records, one of which corrects the previous note.**

**Never build:**

- An IaC or policy-as-code rule pack (F1, N2).
- A declarative rule layer built because a counter-example showed it is
  *possible* rather than because someone asked (N1).

**Recorded, not queued:**

1. **The correction to the Semgrep note (§4)** — the boundary is *what
   the rule is evaluated against*, not data-versus-code and not state in
   the abstract. The Semgrep entry should be read with this attached.
2. **F2 re-scoped to three tiers** (§4.4) — lexical (expressible),
   relational (expressible over a resolved graph, on this evidence),
   ordering/structural (not established). The sizing measurement is
   unchanged and still absent.
3. **The ratchet convergence, and its divergence** (§3) — the no-grader
   observation restated as a missing *axis* rather than a missing report,
   and still two-sided.
4. **Reporting passes as a design fork** (§2), recorded so it is not
   re-derived as a gap.

**Re-litigate on:**

- OPA/Rego/Conftest becoming runnable without a repository fetch — the
  half of this ecosystem this note did not touch.
- An adopter asking to author project-local rules — F2's constituency,
  unchanged across three notes now.
- Evidence that a graph-query format can or cannot express the ordering
  tier (§4.4's open bucket), which is what would finally size F2.

## Related reading

- [Semgrep and rules-as-data, evaluated](semgrep-rules-as-data-evaluation.md)
  — the note this one corrects; its ladder and its "state, not
  vocabulary" finding are sound, its generalization to "lexical tier and
  nothing above it" is not.
- [The Spectral / OpenAPI ecosystem, evaluated](spectral-openapi-ecosystem-evaluation.md)
  — where F2 was first recorded, and where the two-sided grading caution
  §3 reuses was set.
- [The Structurizr DSL viewpoints ecosystem, evaluated](structurizr-viewpoints-evaluation.md)
  — the first withdrawn generalization, and the reason §8 records this as
  a recurring habit rather than an incident.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  first unsolicited convergence; §3 is the second, on a mechanism.
