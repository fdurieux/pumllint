# Cross-diagram identity, worked: the `!include` disclosure and the `distinct` option

*A runnable companion to the [cross-diagram relationships
evaluation](cross-diagram-relationships-evaluation.md), demonstrating the two
mechanisms that evaluation's G3 and G4 findings produced (shipped 2026-08-28).
Every file quoted here is committed under [`docs/xd-demo/`](xd-demo/), every
command runs from the repository root, and the transcripts are drift-guarded
by `tests/test_xd_demo.py` — if the tool's output ever stops matching this
page, the suite fails.*

The XD pack builds an entity symbol table across every diagram in a lint
batch: one entity, one identity — one kind, one stereotype, one spelling
(RULES.md, *XD — Cross-diagram consistency rules*). This page demonstrates
its two boundary mechanisms: the **disclosure** for declarations the tool
cannot see, and the **`distinct` option** for entities that only look like
one thing.

## 1. The disclosure: declarations hidden behind `!include`

A common modular habit — shared lifeline declarations in an include
fragment, used by every interaction diagram in the flow:

```
docs/xd-demo/
├── _participants.iuml     ← participant OrderService <<service>> …
├── checkout.puml          ← !include _participants.iuml
└── refund.puml            ← !include _participants.iuml
```

pumllint never expands the preprocessor, so those diagrams parse with only
*implicit* participants — and the XD identity checks, plus every
declared-entity rule, go quiet on them. Since v0.29.0 the CLI says so:

```
$ pumllint docs/xd-demo/checkout.puml docs/xd-demo/refund.puml -c docs/xd-demo/lint.toml
warning: 2 diagram(s) contain '!include' but declare nothing: docs/xd-demo/checkout.puml, docs/xd-demo/refund.puml — pumllint does not expand preprocessor directives, so declarations inside included files are invisible to cross-diagram (XD) identity checks and declared-entity rules
✔ No issues found.
```

Three contract properties, all visible in that run:

- **The warning is stderr, the report is stdout.** `✔ No issues found.` is
  still the whole report — the disclosure never becomes a finding, so
  machine-read reports (`-f json`, the pinned schemas) are unchanged.
- **The exit code is untouched** (0 here). A disclosure, not a gate.
- **The score is untouched.** The same warning precedes `pumllint score`,
  and the verdict is what the visible content earns:

```
$ pumllint score docs/xd-demo/checkout.puml docs/xd-demo/refund.puml -c docs/xd-demo/lint.toml
warning: 2 diagram(s) contain '!include' but declare nothing: …
docs/xd-demo/checkout.puml [checkout]: Level 4 (Precise) — 100/100
docs/xd-demo/refund.puml [refund]: Level 4 (Precise) — 100/100
```

The reader now *knows* that Level 4 was reached on half-read files. That is
the entire point: the evaluation measured that moving declarations behind an
`!include` used to raise a conflicted pair's score from 72.5 to 87.5 with no
trace — an evasion the gate silently rewarded
([the note, G3](cross-diagram-relationships-evaluation.md#33-g3-include-makes-the-xd-pack-blind--and-raises-the-score)).

An include used *beside* inline declarations — a theme, which GEN003 itself
recommends centralising — does not warn: the disclosure fires only when a
diagram names entities and declares none of them.

### The contrast: the same drift, visible

What the pack does the moment it can see declarations. Replace each
`!include` with the declarations written inline, and drift one of them —
`refund.puml` declaring the gateway as a `database <<store>>`:

```diff
 @startuml refund
-!include _participants.iuml
+participant OrderService <<service>>
+database PaymentGateway <<store>>
```

```
checkout.puml:6: [XD001/major] Participant 'PaymentGateway' is declared 'participant' here and the set disagrees ('database' ×1, 'participant' ×1) — one entity, one kind
checkout.puml:6: [XD002/minor] Participant 'PaymentGateway' is stereotyped <<external>> here and the set disagrees (<<external>> ×1, <<store>> ×1) — one entity, one stereotype
refund.puml:5: [XD001/major] Participant 'PaymentGateway' is declared 'database' here and the set disagrees ('database' ×1, 'participant' ×1) — one entity, one kind
refund.puml:5: [XD002/minor] Participant 'PaymentGateway' is stereotyped <<store>> here and the set disagrees (<<external>> ×1, <<store>> ×1) — one entity, one stereotype

✖ 4 issue(s): 2 major, 2 minor
```

Every conflicted site reported, every variant counted, no side elected —
behind the `!include`, this exact drift would be invisible. The warning is
the tool admitting it.

## 2. The `distinct` option: deliberately different entities

Two bounded contexts, one word, two genuinely different things:

```
docs/xd-demo/sales.puml           class Order <<aggregate>>   { +lines; +total() }      → Customer
docs/xd-demo/manufacturing.puml   class Order <<work-order>>  { +machine; +schedule() } → Machine
```

Under the XD premise — same spelling, same entity — XD005 fires
symmetrically at both sites, telling both contexts they are wrong about
their own model:

```
$ pumllint docs/xd-demo/sales.puml docs/xd-demo/manufacturing.puml -c docs/xd-demo/lint.toml
docs/xd-demo/manufacturing.puml:4: [XD005/minor] Class 'Order' is stereotyped <<work-order>> here and the set disagrees across diagram types (<<aggregate>> ×1, <<work-order>> ×1) — one entity, one stereotype
docs/xd-demo/sales.puml:4: [XD005/minor] Class 'Order' is stereotyped <<aggregate>> here and the set disagrees across diagram types (<<aggregate>> ×1, <<work-order>> ×1) — one entity, one stereotype

✖ 2 issue(s): 2 minor
```

The `authoritative` option cannot express this — it pins *one* intended
value per name, so using it here would declare one of the two contexts
wrong. `distinct` is its negative form: the name is not one entity, so no
cross-diagram comparison applies.

```toml
[rules.XD005]
distinct = ["Order"]   # sales Order and manufacturing Order are different things
```

```
$ pumllint docs/xd-demo/sales.puml docs/xd-demo/manufacturing.puml -c docs/xd-demo/distinct.toml
✔ No issues found.
```

`distinct` is per-entity, not a mute button: every other name in the batch
keeps the full XD treatment, and a real drift on an undeclared entity still
fires — the acceptance scenarios in RULES.md (*a distinct entity is never
compared*, one per XD rule) pin exactly that boundary. It is accepted by all
five XD rules; XD003/XD004 match it case-insensitively, mirroring their
case-insensitive joins.

## Where this came from

- [Cross-diagram relationships in pumllint, evaluated](cross-diagram-relationships-evaluation.md)
  — the dated note that measured both gaps (G3: the score-raising include
  evasion; G4: the bounded-context false positive) and graded the options.
- RULES.md, *XD — Cross-diagram consistency rules* — the executable
  specification for the pack, `authoritative`, and `distinct`.
- `tests/test_xd_demo.py` — the drift guard: runs the commands above against
  the committed files and asserts this page's quoted output.
