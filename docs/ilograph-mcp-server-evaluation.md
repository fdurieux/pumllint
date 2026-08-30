# The unofficial Ilograph MCP server, evaluated — a linter for a model, not a gate

*Dated evaluation, 2026-08-30, written against `a21d950` (v0.30.0). The
question as posed: investigate the unofficial Ilograph MCP server, then
assess the boundaries, overlap, fit, gap, sense and nonsense of the
different fits against pumllint's roadmap and ecosystem. Thirty-fifth in
the series, and it retires **the last claim in the ninth note that rested
on description alone**.*

**Verdict up front: no overlap worth a line of code, and the yield is the
delivery question, not the tool. Four things measured. (1) The ninth
note's *"validates without grading"* is imprecise — the server emits an
aggregate ordinal verdict field literally named `assessment`, three bands
wide. **It is the closest approach to grading a description found in
fifteen ecosystems, and I am *not* recording the streak as broken**; §4
says exactly why, and gives the reading that says it is. (2) Measured
head-to-head against the vendor's validator on the same six files, it is
**materially worse in four specific ways** — two false negatives, two
false positives. (3) The chronology reframes the ninth note's §1.3: this
server's last commit is **2025-06-16**, and the vendor's validator shipped
**170 days later**. It was not a community tool filling a gap the vendor
refused; it was a community tool filling a gap the vendor **then filled**,
and it has not been touched in **440 days**. (4) The real boundary, and
the only part of this worth the roadmap's attention: **it is a linter
whose consumer is a model, not a gate** — and it has no exit code because
it does not need one.**

*Bounds. The server was **cloned and executed**. Its validator was run
against six files under **two independent dependency sets** — the newest
registry versions (fastmcp 3.4.7 / pydantic 2.13.5) and the exact
`uv.lock` pins (fastmcp 2.7.0 / pydantic 2.9.2 / mcp 1.9.3) — with
**identical results in both**, so no finding here is a version artefact.
The vendor comparison re-uses `validate-ilograph@0.0.1` from
[the Ilograph re-examination](ilograph-ecosystem-reexamined.md). **The MCP
transport itself was not exercised** — no MCP client was attached; the
validator was imported and called directly, which is the same code the
tool handler calls but is not a test of the protocol layer. The **Docker
image was not pulled**, so the published `ghcr.io` artefact is unverified;
everything here is from source at `4af16cb`. The nine non-validation
tools (documentation, examples, icons, spec) were **read, not run** —
they fetch from `ilograph.com` at runtime and were not exercised.
Adoption is not measured.*

## 0. Why this ran, and a correction it forced first

Yesterday's re-examination closed nine of the ninth note's open claims and
left exactly one:

> Per this session's repository scope **no GitHub repository was read**, so
> the unofficial MCP server remains uninspected — the ninth note's claim
> that it *"validates without grading"* is **still unverified**, and is now
> the only claim in that note resting on description alone.

That bound was **session scope, not obtainability** — and session scope is
extensible. The repository is public; the session's git proxy serves
anonymous reads. It was one clone away the whole time, exactly as the
vendor's validator was one `npm install` away.

**Which makes this the fifth consecutive turn in which a bound recorded as
a limitation turned out to be debt.** The pattern is now stable enough to
name: *this series has repeatedly mistaken "I did not do it" for "it could
not be done."* The ninth note has now had **both** of its "not obtainable"
claims retired by someone simply asking.

## 1. The ecosystem — what the thing actually is

`QuincyMillerDev/ilograph-mcp-server`, **MIT** (Copyright (c) 2025 Quincy
Miller), Python 3.11+, FastMCP, 21 source files, `version = "0.1.0"`,
`Development Status :: 3 - Alpha`.

**It is mostly not a validator.** Eleven registered tools; **two** concern
validation:

| Tool | Purpose |
|---|---|
| `validate_diagram_tool` | the validator measured in §3 |
| `get_validation_help` | a static markdown help page |
| `fetch_documentation_tool`, `list_documentation_sections`, `check_documentation_health` | scrape `ilograph.com/docs/` |
| `fetch_spec_tool`, `check_spec_health` | scrape `ilograph.com/docs/spec/` |
| `fetch_example_tool`, `list_examples_tool` | curated example diagrams |
| `search_icons_tool`, `list_icon_providers_tool` | icon catalogue |

Nine of eleven fetch and reshape the vendor's own documentation for a
model to read. **Its centre of gravity is documentation access, not
validation** — which the ninth note's framing ("the only validation
tooling found is an unofficial community-built MCP server") does not
convey.

Two maturity signals worth one line: `[project.urls]` still points at the
scaffolding placeholder `https://github.com/your-org/ilograph-mcp-server`,
and the author email is `dev@example.com`. Neither is a defect; both are
consistent with Alpha.

## 2. The chronology, which reframes the ninth note

| Date | Event |
|---|---|
| **2025-06-16** | this server's last commit |
| **2025-12-03** | the vendor publishes `validate-ilograph` — **170 days later** |
| **2026-08-30** | today; **440 days (~14.5 months)** since that last commit |

The ninth note read the situation as *"a community MCP server for a closed
product whose vendor has published no validator"* — a community stepping
into a vacuum the vendor was leaving open. **The dates say otherwise.**
When this was written the vacuum was real. The vendor then filled it, and
this project did not react, because it had already stopped.

This is the **linter-vitality pattern** (DMN, FEEL, Gherkin: parser alive,
standalone linter stale) with a variant the series had not seen: *the
standalone linter went stale and then upstream shipped the thing it
existed to provide.* Recorded because a reader meeting a stale community
linter should check whether upstream overtook it before concluding the
niche is unoccupied.

## 3. Head to head — the vendor's validator vs this one

Same six files, both tools, both dependency sets. `validate-ilograph` run
at `-l 2` (its most verbose).

| File | Vendor validator | MCP server |
|---|---|---|
| `aws.ilograph` — **the vendor's own shipped 8175-line model** | **8 × Fatal Error** (duplicate sibling names) | **"Valid with suggestions"** — 0 errors, 3 warnings |
| `broken.ilograph` — relation → non-existent resource | `Referenced resource "DoesNotExist" not found in the resource tree` | **"Valid"** — nothing |
| `props.ilograph` — uses `style`, `backgroundColor` | **silent** (both accepted) | **2 warnings** — "Unknown resource property" |
| `dup.ilograph` — duplicate `name` *and* duplicate `id`, all siblings | **both** flagged | **only the `id`** |
| `nest.ilograph` — same `id` under **two different parents** | **silent** (correctly — not siblings) | **error** — "Duplicate resource ID" |
| `clean.ilograph` | silent | "Valid" |

**Four defects, each reproduced under both dependency sets.**

**F-neg 1 — it does not check duplicate `name`, only duplicate `id`.**
This is why it reports zero errors on the vendor's flagship file: all
eight of those duplicates are duplicate `name:` values (verified at
`aws.ilograph:721`, two consecutive `- name: Athena::CapacityReservation`
entries). Ilograph's own rule is *"Duplicate name **or** id … for two or
more sibling resources"*.

**F-neg 2 — it has no dangling-reference check at all.** A perspective
whose relation points at a resource that does not exist is reported
**"Valid"**. The vendor catches it. This is the single most valuable check
a model-plus-perspectives format can have, and it is absent.

**F-pos 1 — it warns on valid properties.** `style` and `backgroundColor`
are legal: the vendor's validator accepts them at `-l 2`, and the vendor's
own flagship file uses them. The server's `known_resource_properties` set
simply omits them, and its unknown-property check is warn-by-default, so
every real Ilograph file using styling collects false warnings.

**F-pos 2 — its duplicate-`id` check is global, not sibling-scoped.** It
rejects the same `id` under two different parents, which the vendor
correctly allows. So it is simultaneously **too lax** (F-neg 1) and **too
strict** (F-pos 2) on the very same rule.

Also absent, against the vendor's ~40 diagnostics: circular imports,
context-tree cycles, reserved identifiers, definition-before-reference
ordering.

**The honest summary: it produces false confidence on real files and false
alarms on valid ones.** The ninth note quoted its README's *"real-time
validation with detailed error analysis and suggestions"* and recorded it
as Ilograph's validation story. Executed, that description does not
survive contact.

## 4. Does it grade? — the careful answer

The ninth note: *"the unofficial MCP server **validates without grading**,
which is the only real observation available."*

It emits this, computed from finding counts alone:

```python
if result.success:
    formatted["assessment"] = "Valid with suggestions" if result.warnings else "Valid"
else:
    formatted["assessment"] = "Invalid - contains errors"
```

An aggregate, ordinal, whole-artefact verdict, in a field named
`assessment`, over **a description** — which is precisely the criterion the
record settled on after TOGAF:

> nothing found in fourteen ecosystems grades **the artefact class pumllint
> grades — a description**.

**The reading that says the streak breaks:** three ordered bands, over a
diagram, derived by aggregating findings. That is the move, and it meets
the criterion as written.

**The reading that says it does not, which I take:** the three bands are
two booleans wearing three labels — *are there errors?* and *are there
warnings?* There is no quality scale independent of pass/fail: nothing
distinguishes a good diagram from a barely-passing one, because every
diagram with zero errors and zero warnings gets the identical top label.
Every linter that prints `2 problems (1 error, 1 warning)` conveys the
same information; this one labels it. If a labelled pass/warn/fail rollup
counts as grading, the criterion is vacuous, because it would catch
essentially every linter ever written — including `bpmnlint`, which the
series counted as a non-grader.

**So the record should say: the streak holds at fifteen, and this is the
closest approach found so far — the first tool in the series to attach a
word to the rollup rather than only a count.** Both readings are recorded
because the distinction is genuinely thin, and a future reader who wants
to count it as broken should be able to see why without re-deriving it.

**What is *not* in doubt: the ninth note's phrasing was wrong.** "Validates
without grading" asserts an absence that is not there. The right sentence
is *"emits a three-band pass/warn/fail label and no quality scale."*

## 5. Boundaries

1. **Artefact.** Ilograph YAML vs PlantUML. Nothing shared.
2. **Check class.** It is a **schema conformance** checker — known
   properties, required fields, type shapes. pumllint is a **semantic**
   checker over a parsed diagram. The one place they touch is identity
   uniqueness, and §3 shows it gets that wrong in both directions.
3. **Consumer — and this is the real one.** Its output goes to *a model*,
   as a tool-call result. pumllint's goes to *a person and a gate*.
4. **Determinism.** The validator itself is deterministic offline Python —
   `get_fetcher` is imported and called **zero** times in the validation
   path. But the product it sits inside carries this README warning:
   *"The outputs and recommendations provided by the MCP server are
   generated dynamically and may vary based on the query and model. Users
   should thoroughly review all outputs."*

## 6. The finding that matters — a linter for a model has no exit code

This is the first tool in thirty-five evaluations whose **primary
interface is an LLM tool call**. Everything else was a CLI, a CI action,
a library or a GUI. So it is the first opportunity to see what a linter
becomes when its consumer is a model, and the answer is concrete:

| | pumllint | this server |
|---|---|---|
| Interface | CLI + composite action + pre-commit | MCP stdio tool call |
| Failure signal | **exit 0 / 1 / 2** — a named contract | none; returns a dict |
| Can gate CI | yes, by construction | **no** — there is nothing to exit |
| Output consumer | a person, a diff, a gate | a model |
| Output shape | findings + level + score + gap report | findings + `assessment` + `suggestion` per finding |
| Determinism | a stated constraint | true of the validator; disclaimed for the product |

**It gave up gating to gain suggestions.** Every finding carries a
`suggestion` field written for a model to act on — that is the design's
whole point, and a CLI has nowhere to put it. And the vendor's validator
made the *same* trade from the other direction: yesterday's measurement
showed it **always exits 0**, even on eight Fatal Errors. Two independent
Ilograph validators, neither able to gate anything.

**pumllint is, on this evidence, the only tool in the Ilograph-adjacent
comparison that can fail a build.** That is not a boast about quality; it
is a statement about which product each one is.

## 7. Overlap, sense, nonsense

| Concern | pumllint | this server | Reading |
|---|---|---|---|
| Schema conformance | not attempted | its whole job | **No overlap** — different layer |
| Identity uniqueness | XD001–005 | duplicate-`id`, wrong in both directions (§3) | Nominal overlap, negative example |
| Dangling references | XD/UC/SEQ orphan rules | **absent** | Unoccupied on their side |
| Ambiguity / prose | DIM-AMB, codegen lexicons | none | Unoccupied |
| Level / score / ratchet | the scoring model | a three-band label (§4) | **Closest approach in the series** |
| Fix guidance | rule docs, gap report | per-finding `suggestion`, model-directed | **Different consumer, same intent** |

**S1. The `suggestion` field is a real design idea and it is not new to
pumllint.** Every finding carries machine-actionable repair text. pumllint
already has this shape in its gap report and rule fix hints; the
difference is only who reads it. Nothing to build, but worth noting the
convergence.

**S2. An abandoned community linter is weak evidence about a niche.** The
ninth note leaned on this server's existence to characterize Ilograph's
validation story. Executed, it is a stale alpha that upstream overtook.
*Existence of a community tool is not evidence of a living niche* — check
its last commit before citing it.

**N1. Building an MCP interface for pumllint because this exists.
Refused — on this evidence.** One stale alpha is not demand. If the
question is ever taken up it should be taken up on pumllint's own demand
signal, and §6 is the design note to read first: the exit-code contract is
the thing that must survive, and an MCP tool call has nowhere to put it.

**N2. Reading the `assessment` field as validation that grading is
wanted. Refused.** It is a pass/warn/fail label, and §4 explains why
treating it as a grade makes the criterion vacuous.

**N3. Any dependency, of any kind.** MIT, so licence-compatible — and
irrelevant: it checks a format pumllint does not read, and gets that
wrong.

## 8. Fit — graded

### F1 — an Ilograph capability of any sort. **No.** Settled ninth on ground (1); nothing here touches it.

### F2 — an MCP interface for pumllint. **Not now, and this is not the evidence for it.** N1. Recorded, not queued, with §6 as its design note.

### F3 — the no-grader streak. **Holds at fifteen, closest approach recorded.** §4. The ninth note's phrasing is corrected.

### F4 — the ninth note's last description-only claim. **Retired.** §0.

| Declared constraint | Where this lands |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails on the artefact. |
| **Deterministic product path, no LLM** | **The live one.** This server's validator is deterministic, but its product disclaims output stability. Any MCP work must keep the determinism on pumllint's side of the boundary. |
| **Exit codes 0/1/2** | **The contract §6 says an MCP interface cannot carry.** Load-bearing if F2 is ever picked up. |
| **Golden score contract** | Untouched — nothing here proposes a scoring change. |
| **Licence posture** (GPL-3.0-or-later) | MIT, compatible. Second MIT component in this ecosystem, after the vendor's validator. |

## 9. Vitality — stated precisely, because my first measurement was wrong

Its own suite: **84 passed** on the `uv.lock` pins.

My first run reported **55 failed, 29 passed** — and that was **my
artefact**, not a finding. I had installed the newest fastmcp (3.4.7)
against a project pinning `>=2.7.0`; the failures were all
`TypeError: object of type 'CallToolResult' has no len()`, an fastmcp 2→3
API change in the *tests'* assertions, while the server itself logged
`Validation successful`. Recorded because reporting it would have been a
false accusation against someone's project, and the same class of error as
the GEN006/GEN007 config contamination caught yesterday.

**The honest finding is narrower and still real:** its declared ranges
(`fastmcp>=2.7.0`, `pydantic>=2.0.0`, both unbounded above) no longer
resolve to a working combination on today's registries. Newest fastmcp
breaks the tests; the locked fastmcp 2.7.0 will not even import against
current pydantic (`cannot specify both default and default_factory`). A
plain `pip install` from `pyproject.toml` today yields a broken install;
only `uv.lock` works. That is what 440 days of no maintenance looks like
in a Python project with open-ended pins.

## 10. SWOT

Scope: *pumllint's position relative to this server*.

**Strengths**

- The exit-code contract is the thing neither Ilograph validator has
  (§6), and it is what makes pumllint a gate rather than an advisor.
- pumllint's identity rules are correct in both directions where this
  server is wrong in both (§3).

**Weaknesses**

- No machine-directed `suggestion` field per finding; pumllint's repair
  guidance lives in docs and the gap report, not in the finding payload.
  Not a defect — a difference in consumer — but the convergence is worth
  knowing if F2 ever moves.

**Opportunities**

- None pursued. §6 is a design note for a question nobody has asked yet.

**Threats**

- None from this project; it is stale and upstream overtook it. The
  standing threat is the record's own habit: **the ninth note characterized
  this server from its README and was wrong about what it does**, which is
  the third time in this series that a claim about a third party survived
  only because nobody ran the thing.

## 11. Decision

**Decision: no fit, no build, nothing queued. Three corrections to the
ninth note and one design note recorded.**

**Never build:** an Ilograph capability (settled ninth); anything premised
on this server being a live signal about the niche (§2, S2).

**Recorded, not queued:**

1. **The ninth note's "validates without grading" is corrected** to
   "emits a three-band pass/warn/fail label and no quality scale". The
   no-grader streak **holds at fifteen**, with this logged as the closest
   approach and both readings preserved (§4).
2. **An MCP interface for pumllint — a design note, not a proposal.** §6.
   The exit-code contract is what would have to survive, and an MCP tool
   call has nowhere to put it. Revisit only on pumllint's own demand
   signal.
3. **"Check the last commit before citing a community tool as evidence of
   a live niche."** §2, S2 — generalized past its occasion.

**Re-litigate on:** demand for an MCP interface arising from pumllint's
own users. Nothing about Ilograph.

## Related reading

- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — the vendor's validator, and the head-to-head baseline used in §3.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md) —
  the ninth note, whose last description-only claim this retires.
- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md) — the
  linter-vitality pattern this note adds a variant to (§2).
- [ROADMAP.md](../ROADMAP.md) — the exit-code contract §6 turns on, and
  the corrected no-grader criterion §4 tests against.
