# The Spectral / OpenAPI ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-29, written against `89c1f36` (v0.30.0).
Twenty-fifth in the series, and the one with the least distance to
travel: Spectral is not a neighbouring ecosystem this project might
expand into — it is **the tool this project's positioning case cites as
its own precedent**.*

**Verdict up front: no expansion, and the analogy holds. But the reason
to write this down is that the analogy is load-bearing and had never been
executed. `case-for-pumllint.md` says Spectral is "a rule-based checker
of exactly this kind"; the positioning quadrant excludes it as a *peer*
in a neighbouring artefact class. Both claims were made from description.
This note runs it.**

**What running it returns. (1) The analogy survives contact, and more
precisely than it was stated** — configuration, presets, severities, a
fail-gate flag, an extension surface and a terminal summary line all map
one-to-one, and Spectral's summary is the same shape as `bpmnlint`'s and
this project's. **(2) The grading gap is confirmed on the closest
possible peer, and it is starker than anywhere else in the series:
Spectral has exactly one subcommand, `lint`.** No score, no level, no
aggregate, no second verb. **(3) There is one genuine architectural
difference, and it is a trade-off rather than a gap: Spectral's rules are
*data*, pumllint's are *code*.** A Spectral rule is a JSONPath plus one
of **thirteen** built-in functions. That makes rules writable by
non-programmers and bounded by construction — and it also means the
semantic rules this project's catalogue is built around could not be
expressed in it.

**And one discipline note, stated up front so the record stays
straight.** Spectral ships **twelve** output formats including SARIF;
pumllint ships three for `lint` and five for `score`. **SARIF's absence
is already on record as "absent, demand-gated like every other format
request"** (`sdd-manifest-evaluation.md`). This note does not rediscover
it as a gap. What it adds is evidence about where the demand bar sits —
the closest peer ships it — and nothing more.

*Bounds. pumllint claims executed at `89c1f36` (v0.30.0). **Spectral
6.16.3 was installed from npm and executed** — every finding, exit code
and summary line below is a run, including a custom ruleset written for
this note. Rule counts are read from the shipped rulesets by loading them
in Node, not from documentation. **I did not survey OpenAPI's wider
ecosystem** (Redocly, Vacuum, oas-tools, the OpenAPI Initiative's own
validators): this note is about Spectral, because Spectral is the
specific tool the positioning case names. Per session scope no GitHub
repository was read. The W1b OpenAPI figures are quoted from this
repository's frozen records, not re-run.*

## 0. Why this ran

Two places in this repository rest on Spectral, and neither was written
from a run.

**The positioning case** (`case-for-pumllint.md`):

> **The pattern itself is proven elsewhere.** For API contract files, a
> rule-based checker of exactly this kind — a tool called Spectral — is
> established enterprise practice: teams block changes on it in their
> pipelines. pumllint applies that same proven pattern to design
> diagrams, a slot that was simply unoccupied.

**The positioning quadrant**, which *excludes* Spectral from its
scoring while keeping it as the reference point:

> Spectral (the proven pattern for *API* contracts that the case document
> cites, but its artefact is an OpenAPI description, not a diagram — it
> reappears in Part 2 where it belongs)

with the row: `CE | API contracts | Spectral | peer — the proven pattern
for a neighbouring artefact`.

That is a claim about *architecture* ("exactly this kind", "that same
proven pattern") supporting the project's core positioning. The BPMN
re-examination two notes ago established what happens when this series
reasons from a tool's description instead of its behaviour: three
published claims were wrong, one of them central. **Spectral is a more
load-bearing analogy than `bpmnlint` ever was.** It was worth an hour.

Nothing here is queued. §10 records what moved.

## 1. The ecosystem

`@stoplight/spectral-cli` **6.16.3**, **Apache-2.0**, 47 published
versions from 2021-06-18 to **2026-08-03** — three weeks before this
note. Actively maintained, permissively licensed. (The Graphviz note's
decisive ground was a licence; here the licence is not an obstacle, so
the grounds have to be real ones.)

**Three built-in rulesets, 133 rules:**

| Ruleset | Rules |
|---|---|
| `spectral:oas` (OpenAPI 2/3) | **56** |
| `spectral:asyncapi` | **55** |
| `spectral:arazzo` | **22** |

Against pumllint's 51 across five diagram types. **Installation pulls 203
entries into `node_modules`**; pumllint ships zero dependencies. Neither
number is a criticism — they are different runtimes with different norms
— but the contrast is the concrete form of a constraint this project
treats as a contract.

## 2. The analogy, verified

Run against the same table the BPMN note used for `bpmnlint`, so the
three tools can be read together:

| Concern | Spectral 6.16.3 | pumllint 0.30.0 | Holds? |
|---|---|---|---|
| Rule configuration | `.spectral.yaml`, `extends` + `rules` | `pumllint.toml`, profiles + per-rule options | ✔ |
| Named presets | `spectral:oas`, `:asyncapi`, `:arazzo` | default profile, `codegen` profile | ✔ |
| Severities | `error` / `warn` / `info` / `hint` | `info` / `minor` / `major` / `critical` / `blocker` | ✔ |
| Fail gate | `-F/--fail-severity` (default `error`) | `--fail-on` | ✔ |
| Extensibility | `-r` custom ruleset; `given`/`then`; custom JS functions | `@register` + `catalog.toml` | ✔ *shape*, ✘ *medium* (§4) |
| Terminal summary | `✖ 7 problems (1 error, 6 warnings, 0 infos, 0 hints)` | `✖ 6 issue(s): 2 major, 4 minor` | ✔ |
| Exit codes | 1 on findings at/above fail severity, 0 clean | 0 / 1 / 2 | ✔ |
| Machine output | **12 formats** incl. `sarif`, `github-actions`, `junit`, `code-climate`, `gitlab` | `json`, `sonar`, `text` (+ `badge`, `html` on `score`) | ✔ shape, **Spectral broader** |
| **Aggregate verdict** | **none — one subcommand** | levels, dimensions, gap report, ratchet, badge | **✘ — §5** |

Executed, so this is not a reading of documentation:

```
$ npx spectral lint api.yaml
 1:1  warning  oas3-api-servers       OpenAPI "servers" must be present and non-empty array.
 2:6  warning  info-contact           Info object must have "contact" object.
 2:6  warning  info-description       Info "description" must be present and non-empty string.
 7:9  warning  operation-description  Operation "description" must be present and non-empty string.
 7:9  warning  operation-operationId  Operation must have "operationId".
 7:9  warning  operation-tags         Operation must have non-empty "tags" array.
 7:9    error  path-params            Operation must define parameter "{id}" as expected by path "/orders/{id}".

✖ 7 problems (1 error, 6 warnings, 0 infos, 0 hints)                  (exit 1)
```

```
$ npx spectral lint -r custom.yaml clean.yaml
No results with a severity of 'error' found!                          (exit 0)
```

**The analogy holds on every row it was ever asked to carry.** The case
document's "exactly this kind" is, if anything, an understatement: the
correspondence is closer than the one the BPMN note found so remarkable,
and unlike that one it was *claimed* in advance rather than discovered.

Worth noting for its own sake: `path-params` is a genuine **model
consistency** rule — the path template declares `{id}` and the operation
defines no matching parameter — and it is the one `error` among six
warnings. That is the same class of check as pumllint's semantic rules,
and it is the class Spectral rates highest. Two tools, two artefacts,
independently agreeing that *internal inconsistency outranks missing
description*.

## 3. Where the analogy is more precise than it was stated

The case document says Spectral is "established enterprise practice:
teams block changes on it in their pipelines". Running it shows *how*
that is achieved, and every mechanism has a pumllint counterpart:

- **A default fail severity of `error`**, with warnings not breaking the
  build. pumllint's `--fail-on` is the same lever, and its five-level
  severity scale gives finer control over the same idea.
- **`--display-only-failures`**, so a pipeline can print only what it
  will fail on. pumllint has no exact equivalent; `--fail-on` changes the
  gate, not the display.
- **Formatters aimed at specific CI surfaces** (`github-actions`,
  `gitlab`, `teamcity`, `junit`, `code-climate`, `sarif`). This is the
  operational half of "teams block changes on it", and it is where the
  peer is broadest.

**None of this is new information about what pumllint should build** —
see the discipline note above and §8 — but it does make the positioning
claim more defensible than it was, because it is now sourced.

## 4. The one real architectural difference: rules as data, rules as code

A Spectral rule is declarative. Written for this note and executed:

```yaml
rules:
  operation-must-name-a-verb:
    description: operationId should start with a verb
    given: $.paths[*][get,post,put,delete].operationId
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^(get|list|create|update|delete)[A-Z]"
```

```
 6:20  error  operation-must-name-a-verb  operationId should start with a verb
✖ 1 problem (1 error, 0 warnings, 0 infos, 0 hints)
```

A JSONPath (`given`), a function, and its options. **The complete
function library is thirteen entries:**

```
alphabetical, casing, defined, enumeration, falsy, length, or, pattern,
schema, truthy, undefined, unreferencedReusableObject, xor
```

That bound is the whole story, and it cuts both ways.

**In Spectral's favour.** A rule is data: reviewable in a pull request by
someone who does not write JavaScript, safely shareable, impossible to
make Turing-complete by accident, and portable to any host that
implements the same functions. An API guild can own its own ruleset
without owning a codebase. pumllint has no equivalent path — a new rule
is Python, `@register`, and a `catalog.toml` entry, which is a
contributor-shaped task, not a guild-shaped one.

**In pumllint's favour, and decisively for this catalogue.** Ask what
those thirteen functions can express about a sequence diagram. *Presence*
(`defined`, `truthy`), *shape* (`pattern`, `casing`, `length`,
`enumeration`, `schema`), *ordering* (`alphabetical`), *exclusivity*
(`xor`, `or`), *reference usage* (`unreferencedReusableObject`). Now ask
them for:

- **SEQ semantics** — every synchronous call has a matching reply;
  activation stacks balance; a fragment closes.
- **XD identity** — the same participant named two ways across a batch of
  files.
- **DIM-TRC / GEN007** — requirement IDs read from exactly one carrier
  set across five diagram types.

**None of these is a path plus a predicate over a node.** They are
computations over a parsed model with cross-node and cross-file state.
Spectral supports custom JavaScript functions for exactly this reason —
but at that point the rule is code again, in a second language, with a
runtime this project does not have.

**So the divergence is explained by the artefact, not by taste** — the
same conclusion the BPMN note reached about layout rules, arrived at from
the opposite direction. An OpenAPI document is a *tree*, and a tree
yields to path-plus-predicate. A sequence diagram is a *trace*, and a
trace does not.

## 5. Grading, on the closest peer there is

```
$ npx spectral --help
spectral <command>

Commands:
  spectral lint [documents..]  lint JSON/YAML documents from files or URLs
```

**One subcommand.**

Every previous no-grader observation in this series was about a tool in
some other notation, with the standing objection that the ecosystems are
not comparable. That objection does not survive here. Spectral is the
tool this project's own case document names as its precedent; it is
mature, maintained, permissively licensed, enterprise-adopted, and
architecturally near-identical across configuration, presets,
severities, gating, extension surface and reporting. **And it has no
second verb.** No level, no dimensions, no gap report, no ratchet, no
badge — not "no aggregate we could find", but no place in the CLI where
one could live.

That is the strongest form the grading observation has taken. It is also
the least comfortable, and the note should say why: **an unoccupied slot
next to a mature peer is evidence in two directions.** It can mean the
maturity model is the differentiator, which is the reading this project
has taken since the beginning and which the DMN note's "analysers took
the work" pattern does not contradict. It can also mean that teams who
block builds on rule findings have never wanted a number, and that the
market's silence is an answer rather than an opening. **This note cannot
distinguish those** — nothing measured here bears on demand — and it is
recorded as a two-sided reading rather than a strengthened claim.

## 6. Boundaries

1. **Tree vs trace.** §4. The one boundary that explains all the others:
   OpenAPI is a document tree, a diagram is a trace over a parsed model.
2. **Data-rules vs code-rules.** The consequence of boundary 1, and a
   real trade-off in both directions.
3. **Artefact class.** An OpenAPI description is not a diagram. This is
   the quadrant's existing exclusion and it is unchanged.
4. **Runtime and dependencies.** 203 transitive packages vs zero. Not a
   criticism of either; a statement of two different contracts.
5. **Peer, not competitor.** Nothing in Spectral's 133 rules addresses a
   diagram, and nothing in pumllint's 51 addresses an API description.
   The overlap is architectural, not functional.

*One point where the artefacts do meet, already on record.* OpenAPI is
not only a neighbouring artefact class here — it is a **measured
component of this project's own carrier experiment**. W1b found that
*"the OpenAPI schema mirror held the validation bounds at exactly 0.0
loss when the tables left"*, while removing it (with the other non-table
components) improved pooled results. So the repository's position on
OpenAPI is already evidence-backed and more nuanced than "different
artefact class": it carries something specific and narrow. That is the
substrate F3's cross-check would stand on, and it is unchanged by
anything measured here.

## 7. Sense and nonsense

**S1. The founding analogy is sound, and now sourced.** §2. Every row it
was asked to carry holds under execution.

**S2. The divergence is principled.** §4. Spectral's declarative model is
right for a tree and could not express this catalogue's semantic rules;
that is the artefact talking, not a judgement about either design.

**S3. The strongest no-grader data point in the series, honestly
two-sided.** §5.

**N1. "Spectral has twelve formatters, so pumllint should add SARIF."**
Refused as *reasoning*, whatever the eventual answer: SARIF is already
recorded as absent and demand-gated, and a peer shipping a thing is not
demand. The peer's breadth is evidence about the bar, not a request.

**N2. "Adopt a declarative rule format."** §4 is not a recommendation.
The thirteen functions are sufficient for a tree and insufficient for
this catalogue, so a declarative layer here would either be a second,
weaker way to write rules or a re-architecture in service of an
authoring audience that has not appeared. §8's F2 grades it honestly and
leaves it recorded.

**N3. "Lint OpenAPI too."** The niche is occupied by a mature, adopted,
permissively licensed tool that is better at it, and the artefact is
outside this project's identity — the same refusal the quadrant already
records, now with a run behind it.

## 8. Fit — graded

### F1 — lint OpenAPI/AsyncAPI. **No.** N3.

### F2 — a declarative rule-authoring layer. **Recorded, not queued — and this is the note's only genuinely open idea.**

The merit is real: rules as reviewable data, authored by an API-guild
equivalent without a Python contribution. The costs are also real: a
second authoring path to document and support; expressiveness that stops
short of the semantic rules that distinguish this catalogue (§4); and no
observed demand. **Gated on demand, like every Arc E item** — an adopter
asking to write project-local rules without contributing Python is the
condition, and it has not happened.

### F3 — sequence ↔ contract cross-check (message signatures against OpenAPI/AsyncAPI operations). **Unchanged: recorded, trigger-gated.**

Already on record (2026-07-29) as "the XD identity discipline extended
across artifact classes". Nothing here moves it, and it is worth noting
that this is the one place the two tools' *artefacts* would meet.

### F4 — SARIF or CI-specific formatters. **Unchanged: absent, demand-gated.**

Already recorded in the SDD-manifest evaluation. §2's row is evidence
about the bar, not a new candidate. N1.

### Fit against declared constraints

| Constraint | Reading |
|---|---|
| **Zero dependencies** | F2 is the only fit that would pressure it, and it does not require a dependency — only a design decision. |
| **Rule IDs and names are contracts** | F2 would have to preserve them, which is a real design constraint on any declarative layer. |
| **Report shapes are contracts** | F4 adds formats rather than changing them; not a blocker, and not the reason it is gated. |
| **Demand-driven / Arc E bar** | F2 and F4 are both squarely demand-gated. F1 and F3 are unchanged. |

## 9. SWOT

**Strengths (internal, favourable)**

- The positioning case's central analogy **survives execution** (§2), and
  is now sourced rather than described.
- The catalogue's semantic rules are outside what the peer's rule model
  can express (§4) — a concrete statement of what this project's
  code-rules buy.
- Grading remains unoccupied at the closest peer in the field (§5).

**Weaknesses (internal, unfavourable)**

- **No non-programmer authoring path** (§4). Spectral has one; this is
  the clearest capability the peer has and this project does not, and it
  is a design choice rather than an oversight.
- Machine-output breadth is narrower than the peer's (§2) — already
  recorded, already gated, restated here only so the comparison is
  complete.

**Opportunities (external, favourable)**

- F2, gated. Nothing else.

**Threats (external, unfavourable)**

- **The two-sided reading of §5.** If the market's silence on grading is
  an answer rather than an opening, the differentiator is weaker than the
  case document assumes. Nothing measured here decides it, and the honest
  move is to keep the observation two-sided every time it is cited.
- **Analogy drift.** "Spectral for diagrams" is a good one-line
  positioning and a bad specification: §4 and §6 are the places it stops
  being true, and a reader who takes the line literally will expect a
  declarative ruleset and twelve formatters.

## 10. Decision, recorded candidates, triggers

**Decision: no change. Spectral remains a peer and a precedent, not a
competitor and not a template. The positioning case's claim stands and is
now backed by a run rather than a description.**

**Never build:**

- An OpenAPI or AsyncAPI rule pack (F1, N3) — occupied, better served,
  and outside this project's artefact identity.
- A declarative rule layer built to imitate Spectral rather than to serve
  an asked-for need (N2) — the distinction is the demand, and F2 records
  the honest version.

**Recorded, not queued:**

1. **A declarative rule-authoring layer (F2)** — the only open idea here.
   Demand-gated: an adopter wanting project-local rules without a Python
   contribution. Must preserve rule IDs and kebab-case names, and must
   not become a second, weaker way to write what the catalogue already
   expresses in code.
2. **The two-sided grading reading (§5)** — cite the no-grader
   observation with its counter-reading attached, in the same way the
   decision-table result is cited with its suite-composition scoping.
   Recorded so the strongest data point does not get quoted as the
   simplest one.
3. **The `path-params` correspondence (§2)** — two independent tools
   rating *internal inconsistency* above *missing description*. A small
   addition to the convergence record the BPMN note opened.

**Re-litigate on:**

- An adopter asking to author rules without contributing Python — the F2
  constituency.
- Evidence bearing on §5's two-sided reading in either direction: a peer
  in any artefact class shipping a maturity aggregate, or an adopter
  explicitly declining one. Both are currently absent.
- The sequence ↔ contract cross-check trigger, unchanged (F3).

## Related reading

- [The case for pumllint](case-for-pumllint.md) — where the Spectral
  analogy is stated; §2 here is its verification.
- [The positioning quadrant](positioning-quadrant.md) — where Spectral is
  excluded as a peer in a neighbouring artefact class; §6's boundary 3 is
  that exclusion, unchanged.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md) — the
  paired-run method, and the reason a described analogy was worth
  executing.
- [The DMN ecosystem, evaluated](dmn-ecosystem-evaluation.md) — its
  "analysers took the work" pattern, which §5 checks against.
- [The SDD manifest, evaluated](sdd-manifest-evaluation.md) — where SARIF
  is recorded as absent and demand-gated.
