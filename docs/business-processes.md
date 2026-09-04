# Linting business processes: ARIS/EPC processes as PlantUML activity diagrams

*A how-to for process owners and BPM analysts whose processes live in ARIS
and who want the same kind of conventions gate on them that developers
get on code. Every file quoted here is committed under
[`docs/process-demo/`](process-demo/), every command runs from the
repository root, and the transcripts are drift-guarded by
`tests/test_process_demo.py` — if the tool's output ever stops matching
this page, the suite fails.*

## 1. What this is, and what it is not

pumllint lints **PlantUML activity diagrams, not BPMN** and not EPCs. It
reads PlantUML text only: it has no reader for ARIS exports (AML), for
BPMN 2.0 XML, or for any other process interchange format, and the roadmap
records a deliberate decision not to build one (ROADMAP.md, *BPMN
ecosystem*, 2026-08-27). What it does have is an activity pack whose
conventions come from the same place ARIS's do:

| Rule | Checks | ARIS/EPC counterpart |
|------|--------|----------------------|
| ACT001 / ACT002 | a `start` node; every flow reaches `stop`/`end` | start and end events |
| ACT003 | every `if`/`else` branch carries a label | XOR outcomes are named events |
| ACT004 | every `if`/`fork`/`switch`/`repeat`/`while`/`partition` is closed | every split has its join |
| ACT005 | swimlane names follow a pattern | organisational units |
| ACT006 | activities are phrased verb + object | the function naming convention |
| GEN006 / GEN007 | an owner tag and a process/requirement reference | model attributes |

So the practical route is: express the process as a PlantUML activity
diagram with one swimlane per org unit, and run pumllint on it. This page
gives the mapping, a copy-ready configuration, a worked run, and the
limits.

If you have **BPMN** in hand rather than EPCs, use
[`bpmnlint`](https://github.com/bpmn-io/bpmnlint) on the BPMN 2.0 export
directly — it is the same kind of tool for that notation, and
[docs/bpmn-ecosystem-reexamined.md](bpmn-ecosystem-reexamined.md) records
a paired run showing which of its rules correspond to which of pumllint's.
If you need the **ARIS models of record** checked, ARIS's own semantic
checks are the tool; nothing here replaces them.

## 2. Mapping an EPC onto a PlantUML activity diagram

The diagram is a *view* of the EPC, not a round-trippable copy. The
mapping keeps what the linter can check and drops what it cannot.

| EPC element | PlantUML | Checked by |
|-------------|----------|------------|
| Function | `:Verb object;` — one line | ACT006 (naming), ACT004 |
| Org unit / role / position attached to a function | `\|Org unit\|` swimlane before the function; repeat the line whenever the lane changes | ACT005, XD004 (case collisions across diagrams) |
| Start event | `start` then `-> Event text;` | ACT001 |
| End event | `-> Event text;` then `stop` | ACT002 |
| XOR split with two outcomes | `if (Function outcome?) then (Event A) … else (Event B) … endif` — the outgoing events **are** the branch labels | ACT003 |
| XOR split with more outcomes | `switch (…)` / `case (Event A)` … `endswitch` | ACT003 |
| AND split and join | `fork` / `fork again` / `end fork` | ACT004 |
| OR split and join | no faithful equivalent; emit a `fork` with a `' epc: OR` comment and remodel — see §7 | — |
| Loop back to an earlier function | `repeat` … `repeat while (Event)` | ACT004 |
| Process interface (link to another process) | `:Process name;` preceded by `' aris: interface PROC-nnnn` | ACT006 |
| Information objects, documents, IT systems | dropped; optionally `note right` — sparingly, GEN008 counts notes | GEN008 |
| Model name, process ID, owner | `@startuml <slug>`, `title …`, `footer owner: … — ARIS process PROC-nnnn` | GEN001, GEN002, GEN006, GEN007 |

Three consequences of the parser worth knowing before you draw:

- **One line per function.** The parser keeps only the first line of a
  multi-line `:action;` label. Fold long function names onto one line.
- **Events on arrows are invisible to rules.** `-> Event text;` is
  rendered by PlantUML but not parsed by pumllint, so nothing checks
  event names. The XOR outcomes are the exception: as branch labels they
  are checked for presence (ACT003), not for wording.
- **Use the structured constructs only.** `if`/`switch`/`fork`/`repeat`
  are recognised; `split`, arrow-to-label jumps and the legacy `(*)`
  syntax are not, and a diagram built from them may be typed as something
  other than an activity diagram and lose the ACT rules entirely.

For **BPMN modelled in ARIS**, the same table applies with tasks in place
of functions, lanes in place of org units, exclusive gateways as
`if`/`switch`, parallel gateways as `fork`, and start/end events as
`start`/`stop`. Pools become one diagram per pool; message flows between
pools and intermediate events have no activity-diagram equivalent.

## 3. Configure the gate

[`docs/process-demo/conventions.toml`](process-demo/conventions.toml) is
the copy-ready configuration. Drop it beside your diagrams as
`pumllint.toml` (auto-detected) or pass it with `-c`:

```toml
[rules]
swimlane-naming = { pattern = '^[A-Z][a-z]+( [A-Z&][a-z]*)*$' }
verb-first-activity = { severity = "major", verbs = [
  "Receive", "Validate", "Check", "Approve", "Reject", "Notify", "Handle",
  "Pick", "Ship", "Create", "Send", "Record", "Post", "Archive",
] }
unlabelled-decision-branch = { require_else_label = true }
owner-tag        = { pattern = '(?i)owner\s*:' }
requirement-link = { pattern = 'PROC-\d{4}' }
```

Option by option:

- **`swimlane-naming.pattern`** — org units in Title Case, `&` allowed as
  a word (`Credit Control`, `Warehouse & Logistics`). The shipped default
  (`^[A-Z][A-Za-z ]+$`) is looser: it would accept `FIN` and reject the
  ampersand. The rule matches from the start of the name, so anchor with
  `$` if the whole name must conform.
- **`verb-first-activity.verbs`** — the accepted leading verbs. The list
  *replaces* the shipped default (which is empty; the rule is dormant
  until `verbs` or `verb_pattern` is set), so list every verb your process
  vocabulary allows. A shape-based convention (`^(Un|Re)?[A-Z][a-z]+ `)
  goes in `verb_pattern`; a name passes on either gate. Escalated to
  `major` so that a noun-phrase function fails the build under the
  default `--fail-on major`.
- **`unlabelled-decision-branch.require_else_label`** — every XOR outcome
  is an event and must be named, including the `else` leg.
- **`owner-tag.pattern`** / **`requirement-link.pattern`** — both rules
  are dormant until a pattern exists. They search the title, header,
  footer, caption and notes — not comment lines — so put the tags in a
  `footer`, as the demo does.

## 4. Worked run

Two diagrams of the same order-to-cash process are committed under
`docs/process-demo/`. `order_to_cash_draft.puml` is a first draft:

```
@startuml order-to-cash-draft
title Order to cash — first draft

|Sales|
start
:Order intake;
:Order validation;
if (Valid?) then (yes)
  |credit control|
  :Credit check;
  |Warehouse & Logistics|
  :Pick goods;
  :Ship goods;
  |FIN|
  :Create invoice;
  :Send invoice;
  :Record payment;
else
  |Sales|
  :Reject order;
endif
@enduml
```

PlantUML renders it without complaint. The gate does not:

```
$ pumllint docs/process-demo/order_to_cash_draft.puml -c docs/process-demo/conventions.toml
docs/process-demo/order_to_cash_draft.puml:1: [GEN006/minor] No ownership tag matching '(?i)owner\\s*:' in title/header/footer/caption/notes
docs/process-demo/order_to_cash_draft.puml:1: [GEN007/minor] No requirement/ADR reference matching 'PROC-\\d{4}' in name/title/header/footer/caption/notes
docs/process-demo/order_to_cash_draft.puml:10: [ACT006/major] Activity 'Order intake' is not verb-first — name it "verb + object" (e.g. "Validate order")
docs/process-demo/order_to_cash_draft.puml:11: [ACT006/major] Activity 'Order validation' is not verb-first — name it "verb + object" (e.g. "Validate order")
docs/process-demo/order_to_cash_draft.puml:13: [ACT005/minor] Swimlane 'credit control' does not match pattern '^[A-Z][a-z]+( [A-Z&][a-z]*)*$'
docs/process-demo/order_to_cash_draft.puml:14: [ACT006/major] Activity 'Credit check' is not verb-first — name it "verb + object" (e.g. "Validate order")
docs/process-demo/order_to_cash_draft.puml:18: [ACT005/minor] Swimlane 'FIN' does not match pattern '^[A-Z][a-z]+( [A-Z&][a-z]*)*$'
docs/process-demo/order_to_cash_draft.puml:22: [ACT003/minor] Unlabelled 'else' branch — write "else (no)"
docs/process-demo/order_to_cash_draft.puml:24: [ACT002/major] Activity flow never terminates with 'stop' or 'end' (unterminated flow)

✖ 9 issue(s): 4 major, 5 minor
```

Exit code 1: four findings at `major` or worse. Every one of the nine is
a convention an ARIS modeller would recognise — three functions named as
nouns, two lanes off the naming convention, an XOR outcome without its
event, a flow with no end event, and a model with no owner or process ID.

`order_to_cash.puml` is the same process after applying the mapping in
§2 — verb-first functions, Title Case lanes, both XOR outcomes named,
both end events present, the process interface marked, and the governance
tags in the footer:

```
$ pumllint docs/process-demo/order_to_cash.puml -c docs/process-demo/conventions.toml
✔ No issues found.
```

Exit code 0. Render it and it reads as the EPC did: four lanes, the
labelled XOR after *Validate order*, the AND fork between picking and
invoicing, the events on the arrows.

## 5. What the maturity score means here — and what it does not

`pumllint score` works on process diagrams and the ratchet/badge workflow
in [setup-and-ci.md](setup-and-ci.md) applies unchanged. Read the number
with one caveat: **the composite score is not evidence that a process
diagram is unambiguous.** No ambiguity rule applies to activity diagrams —
the DIM-AMB dimension, weighted 0.25, scores 100 for every activity
diagram regardless of content (ROADMAP.md, *DIM-AMB coverage residual*).
The draft above scores Level 4 at 84.9/100 with nine findings open; a
process consisting of `:Do stuff;` would score higher still.

So for processes, gate on the linter, not the level:

```
pumllint processes/ -c conventions.toml --fail-on major
```

and use `score` for what it is good at here — the ratchet against a
baseline and the badge — not as a floor.

## 6. CI wiring

The composite action and the pre-commit hooks in
[setup-and-ci.md](setup-and-ci.md) need only the config path:

```yaml
- name: Process conventions gate
  uses: fdurieux/pumllint@v0.31.0
  with:
    paths: processes
    config: processes/conventions.toml
    fail-on: major
```

```yaml
repos:
  - repo: https://github.com/fdurieux/pumllint
    rev: v0.31.0
    hooks:
      - id: pumllint
        args: [-c, processes/conventions.toml]
```

Lint the whole `processes/` directory in one run rather than file by file:
the cross-diagram rules (XD004 in particular) then catch the same org unit
spelled `Credit Control` in one process and `Credit control` in another.

## 7. Getting diagrams out of ARIS

Redrawing by hand is fine for a pilot and unsustainable for a repository
of processes. The companion converter
[`aris2puml`](https://github.com/fdurieux/aris2puml) (in preparation)
mechanises the mapping in §2:

- **Input** is a small JSON document — process, lanes, nodes (function,
  event, xor, and, or, interface) and edges — written by an ARIS report
  script whose template ships with the converter. The JSON is
  notation-neutral, so the same emitter serves a BPMN 2.0 XML front-end
  later.
- **Output** is one `.puml` per process, following §2 line for line, so
  a converted process lints clean under the configuration in §3 when the
  EPC follows the conventions and reports the same findings as §4 when it
  does not.
- **Refused**, with the connector named: an EPC whose connectors do not
  reduce to nested single-entry, single-exit blocks (a jump into the
  middle of a branch, a join with no matching split). Structure the EPC
  first; the converter will not invent structure that is not there.
- **Warned**: OR connectors, which have no activity-diagram equivalent
  and are emitted as `fork` with an `' epc: OR` marker.

## 8. Known limits

- **No EPC semantics.** Nothing checks that events and functions
  alternate, that a process starts and ends with an event, or that
  connectors are paired by type. Those are ARIS semantic checks.
- **OR connectors** are unrepresentable; the mapping approximates them
  with `fork` and says so.
- **Unstructured EPCs** (arbitrary jumps) cannot be expressed as an
  activity diagram without restructuring.
- **Event wording is unchecked** except on XOR branch labels, where only
  presence is checked.
- **Data flow** — information objects, documents, systems — is dropped.
- **The score's ambiguity dimension is vacuous** for activity diagrams
  (§5). This is a recorded residual, not a feature.

These are the roadmap's re-litigation triggers for the activity pack: an
adopter running PlantUML activity diagrams as process documentation of
record, and asking for flow rules beyond ACT001–006, is exactly the case
that would reopen them. If that is you, open an issue with the diagrams.
