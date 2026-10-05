# The 360° rule map

*Audience: architects, reviewers and modellers who want to know what the
maturity level is made of. This guide lists every check behind
`pumllint score`, sorted by the part of the score it feeds, with a simple
and a harder example for each. No prior knowledge of PlantUML or linters
is assumed. [Understanding findings and scores](findings-and-scores.md)
explains how to read the reports themselves.*

## How the level is built

**Rules are the tests.** pumllint reads a PlantUML diagram and runs a set of
*rules* over it. Each rule looks for one specific problem. When it finds one,
it reports a *finding* with a severity, from `info` (advice) up to `blocker`
(the diagram is broken or misleading).

**Every rule belongs to exactly one dimension.** A *dimension* is one angle on
quality, such as completeness or ambiguity. `pumllint score` turns each
dimension's findings into a score from 0 to 100. It weighs each finding by
its severity and by the size of the diagram, so a large diagram isn't
punished just for being large. The six dimension scores are then combined
into one score with these weights:

| Dimension | Weight | Rules | The question it asks |
|-----------|-------:|------:|----------------------|
| [Semantic correctness](#semantic-correctness-dim-sem) | 20% | 9 | Is the diagram logically sound? |
| [Completeness](#completeness-dim-cmp) | 30% | 13 | Is everything that should be there actually there? |
| [Ambiguity](#ambiguity-dim-amb) | 25% | 8 | Could two readers take it two different ways? |
| [Consistency](#consistency-dim-con) | 15% | 11 | Does it follow one convention, here and across the model set? |
| [Traceability](#traceability-dim-trc) | 5% | 5 | Can you find it, cite it, and tell who owns it? |
| [Readability](#readability-dim-rdb) | 5% | 6 | Is it small enough for a person to take in? |
| Syntactic validity | gate | — | Does PlantUML itself accept the file? |

**Syntactic validity is a gate, not a rule.** With `pumllint score
--check-syntax`, each file is first run through PlantUML's own checker
(`plantuml -checkonly`). If PlantUML rejects the file, the diagram is
Level 1 and nothing else is scored. Without the flag the gate is skipped.

The combined score and a few hard conditions give the level:

| Level | Name | What it takes |
|------:|------|---------------|
| 1 | Sketchy | Combined score below 40, PlantUML rejects the file, or the diagram is empty. |
| 2 | Structured | Combined score 40 or more. **Any `blocker` finding keeps a diagram here**, however high the score. |
| 3 | Disciplined | Combined score 60 or more and no blockers. Any single dimension below 40 keeps a diagram at this level or lower. |
| 4 | Precise | Combined score 75 or more, no blockers, and both Completeness and Ambiguity at 70 or more. |
| 5 | Method-complete | Combined score 90 or more, every dimension at 80 or more, and no finding at `major` or worse. Only claimable when the codegen profile ran. |

A set of diagrams takes the level of its weakest diagram. The exact formula
is in [SCORING.md](../SCORING.md).

## Two switches change which rules run

- **The codegen profile.** Nine stricter sequence-diagram rules (SEQ101 to
  SEQ109) ask one question: could a code generator implement this diagram
  without inventing anything? They run only with `--profile codegen`.
  Several of them restate a base rule more strictly.
- **Dormant rules.** Some conventions differ from one organisation to the
  next: owner tags, requirement IDs, which verbs may start an activity name.
  These rules stay silent until `pumllint.toml` spells out your convention.
  When they fire, they are checking your organisation's rule, not the tool's.

## Rules by dimension and diagram type

The XD rules and GEN010 compare diagrams with each other. The XD rules run
when several diagrams are checked together; GEN010 runs when one file holds
several diagrams.

| Dimension | sequence | activity | class | state | use case | all types |
|-----------|---|---|---|---|---|---|
| Semantic correctness | SEQ001 SEQ003 SEQ004 SEQ009 SEQ108 | ACT004 | CLS004 | STA001 | UC003 | — |
| Completeness | SEQ002 SEQ007 SEQ010 SEQ101 SEQ102 SEQ104 SEQ107 | ACT001 ACT002 ACT003 | CLS002 | STA002 | UC001 | — |
| Ambiguity | SEQ005 SEQ006 SEQ103 SEQ105 SEQ106 SEQ109 | — | CLS003 | STA003 | — | — |
| Consistency | GEN004 XD001 XD002 XD003 | ACT005 ACT006 | CLS001 | — | UC002 | GEN003 XD004 XD005 |
| Traceability | — | — | — | — | — | GEN001 GEN002 GEN006 GEN007 GEN010 |
| Readability | GEN005 SEQ008 SEQ011 | — | CLS005 | — | GEN005 | GEN008 GEN009 |

## How to read the examples

Every rule below has two examples. The **simple** one shows the problem in
its plainest form. The **more complex** one shows a subtler case, or a case
people expect to be flagged that the rule deliberately lets through. Each
example is marked *flagged* (the rule reports it) or *passes* (it does not).

To keep them short, the examples leave out the lines that open and close a
diagram (`@startuml name`, `title …` and `@enduml`) unless the rule is about
those lines. Where an example needs a setting, the setting is shown as the
`pumllint.toml` snippet that switches it on. Cross-diagram examples show each
diagram file separately.

Every example on this page is run through pumllint by the test suite
(`tests/test_rule_map.py`). If a rule changes and an example stops behaving
as described, the tests fail until this page is updated.

## Semantic correctness (DIM-SEM)

**Weight 20% · 9 rules.** *Is the diagram logically sound?*

Catches diagrams that PlantUML draws without complaint but that are broken underneath: a block that never closes, a class that inherits from itself, a state machine with no starting point. These are the most serious findings. One blocker caps the whole diagram at Level 2.

### SEQ001 undeclared-participant

**Severity:** `critical` · **Diagram type:** sequence

Every lifeline must be declared before it is used. Otherwise a typo silently creates a new, wrong lifeline.

**Simple example — flagged**

```plantuml
participant Customer
participant Shop
participant Payment
Customer -> Shop : placeOrder
Shop -> Paymnet : charge
```

The typo `Paymnet` becomes a fourth lifeline. PlantUML draws it without a warning.

**More complex example — flagged**

```plantuml
participant Customer
Customer -> Shop : placeOrder
participant Shop
```

`Shop` is declared, but only after its first use. PlantUML has already created the lifeline by then, so this counts as undeclared too. The finding names both lines.

### SEQ003 unbalanced-activation

**Severity:** `major` · **Diagram type:** sequence

Each `activate` (the bar showing a participant is busy) must be matched by a `deactivate` or a return.

**Simple example — flagged**

```plantuml
participant Shop
participant Stock
Shop -> Stock : reserve
activate Stock
Stock --> Shop : reserved
```

`Stock` is switched on and never switched off, so its bar runs to the bottom of the page.

**More complex example — flagged**

```plantuml
participant Shop
participant Stock
participant Db
Shop -> Stock ++ : reserve
Stock -> Db ++ : lock
Db --> Stock -- : locked
Stock --> Shop : reserved
```

Uses the `++`/`--` shorthand. `Db` is closed, but `Stock`'s bar is not. The fix is `Stock --> Shop -- : reserved`.

### SEQ004 unterminated-block

**Severity:** `critical` · **Diagram type:** sequence

Every `alt`, `opt`, `loop`, `par`, `group` or `box` must be closed with `end`. An open block changes the meaning of everything after it.

**Simple example — flagged**

```plantuml
participant Shop
participant Bank
alt card accepted
  Shop -> Bank : capture
```

The `alt` is never closed.

**More complex example — flagged**

```plantuml
participant Shop
participant Stock
loop each order line
  alt in stock
    Shop -> Stock : reserve
  else out of stock
    Shop -> Stock : backorder
  end
```

Nested blocks: the single `end` closes the inner `alt`, and the outer `loop` is left open.

### SEQ009 unpaired-return

**Severity:** `minor` · **Diagram type:** sequence

A dashed return arrow (`-->`) must answer an earlier call that went the other way.

**Simple example — flagged**

```plantuml
participant Shop
participant Stock
Stock --> Shop : reserved
```

A reply with no request before it.

**More complex example — flagged**

```plantuml
participant Shop
participant Stock
Shop -> Stock : reserve
Shop --> Stock : reserved
```

A call is there, but the dashed arrow points the same way as the call. The return should go `Stock --> Shop`.

### SEQ108 codegen-activation-lifecycle

**Severity:** `major` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

The strict version of SEQ003 for code generation: on each lifeline, activations must open and close like a well-formed stack.

**Simple example — flagged**

```plantuml
participant Api
participant Repo
Api -> Repo : load(id)
deactivate Repo
Repo --> Api : order
```

Closes an activation that was never opened.

**More complex example — flagged**

```plantuml
participant Api
participant Repo
Api -> Repo : load(id)
activate Repo
Repo -> Repo : validate(order)
activate Repo
deactivate Repo
Repo --> Api : order
```

`Repo` opens two nested activations and closes only one. A generator cannot tell where the outer call's scope ends.

### ACT004 unterminated-construct

**Severity:** `critical` · **Diagram type:** activity

Every `if`, `while`, `repeat`, `fork`, `switch` or `partition` in an activity diagram must be closed.

**Simple example — flagged**

```plantuml
start
if (paid?) then (yes)
  :Ship order;
else (no)
  :Cancel order;
stop
```

The `if` has no `endif`.

**More complex example — flagged**

```plantuml
start
partition Fulfilment {
  :Pick items;
  :Pack parcel;
:Ship parcel;
stop
```

The `partition` brace is never closed. PlantUML tolerates this one and renders a diagram that silently differs from the intent.

### CLS004 inheritance-cycle

**Severity:** `major` · **Diagram type:** class

A class may not (directly or indirectly) inherit from itself. PlantUML draws it, but no programming language can build it.

**Simple example — flagged**

```plantuml
class Animal
class Dog
Animal <|-- Dog
Dog <|-- Animal
```

Two classes, each the parent of the other.

**More complex example — flagged**

```plantuml
interface Shape
class Polygon
class Square
Shape <|-- Polygon
Polygon <|-- Square
Square <|.. Shape
```

A three-step loop that mixes inheritance (`<|--`) and realization (`<|..`). The finding prints the whole path.

### STA001 single-initial-state

**Severity:** `blocker` · **Diagram type:** state

A state machine needs exactly one top-level starting transition (`[*] -->`): not zero, not two.

**Simple example — flagged**

```plantuml
state Draft
state Submitted
Draft --> Submitted : submit
```

No `[*] -->`, so nobody knows where the machine starts.

**More complex example — flagged**

```plantuml
[*] --> Draft
[*] --> Imported
Draft --> Submitted : submit
Imported --> Submitted : validate
state Submitted {
  [*] --> Queued
}
```

Two top-level starts (`Draft` and `Imported`). The `[*]` inside the composite `Submitted` is that composite's own entry point and does not count.

### UC003 include-extend-direction

**Severity:** `minor` · **Diagram type:** use case

`<<include>>` points from the main use case to the included one. `<<extend>>` points from the extension to the main one. Neither may involve an actor.

**Simple example — flagged**

```plantuml
actor Customer
usecase (Log in)
Customer ..> (Log in) : <<include>>
```

An actor on an include arrow. Includes relate use cases only.

**More complex example — flagged**

```plantuml
:Customer:
usecase (Check out)
usecase (Log in)
:Customer: --> (Check out)
(Log in) ..> (Check out) : <<include>>
```

Reversed. `Check out` is the main case (the customer reaches it), so it must include `Log in`, not the other way round.

## Completeness (DIM-CMP)

**Weight 30% · 13 rules.** *Is everything that should be there actually there?*

Looks for missing pieces: a process with no start or end, an association without its numbers (one-to-many?), a call that never gets an answer, an error path nobody drew. This dimension carries the most weight, because gaps are exactly what a reader or a code generator has to guess.

### SEQ002 unused-participant

**Severity:** `minor` · **Diagram type:** sequence

A declared participant must take part in at least one message or activation.

**Simple example — flagged**

```plantuml
participant Shop
participant Stock
participant Audit
Shop -> Stock : reserve
```

`Audit` is drawn but never used. Usually a leftover from an earlier version.

**More complex example — flagged**

```plantuml
participant Shop
database OrderDB
Shop -> OrderDb : save
```

A case slip: the message goes to `OrderDb`, so the declared `OrderDB` is unused and SEQ001 also flags `OrderDb` as undeclared. Two findings, one cause.

### SEQ007 unlabelled-block-condition

**Severity:** `minor` · **Diagram type:** sequence

An `alt`, `opt`, `loop`, `break` or `critical` block must say under which condition it runs.

**Simple example — flagged**

```plantuml
participant Shop
participant Bank
alt
  Shop -> Bank : capture
end
```

“Alternatively”, but on what condition?

**More complex example — flagged**

```plantuml
participant Shop
participant Bank
group Payment
  opt
    Shop -> Bank : refund
  end
end
```

Only the `opt` is flagged. A `group` or `box` may legitimately have no condition.

### SEQ010 explicit-participant-order

**Severity:** `info` · **Diagram type:** sequence · **Dormant** until `require_explicit_order` is set

Lifelines should be declared up front so the left-to-right order is fixed, not implied by whichever message comes first.

**Simple example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
explicit-participant-order = { require_explicit_order = true }
```

```plantuml
participant Shop
Shop -> Stock : reserve
```

`Stock` gets its position from the first message. Moving that message reshuffles the diagram.

**More complex example — passes**

With this in `pumllint.toml`:

```toml
[rules]
explicit-participant-order = { require_explicit_order = true }
```

```plantuml
participant Shop
participant Stock
Shop -> Stock : reserve
Stock -> Shop : confirm
```

Passes: both lifelines declared, so the layout is pinned. In practice SEQ001 already covers this. SEQ010 exists for teams that relax SEQ001 but still want the order fixed.

### SEQ101 codegen-implicit-participant

**Severity:** `blocker` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

For code generation every participant must be declared explicitly, so its identity is unambiguous.

**Simple example — flagged**

```plantuml
participant Client
Client -> Api : getOrder(id)
```

`Api` is created by first use.

**More complex example — flagged**

```plantuml
Client -> Api : getOrder(id)
Api --> Client : order
```

A quick sketch with no declarations at all. The base rule SEQ001 stays quiet on such sketches on purpose; under the codegen profile both lifelines are blockers.

### SEQ102 codegen-untyped-participant

**Severity:** `major` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

Each declared participant must say what it is: a typed keyword (`actor`, `database`, `queue`, …) or a `<<stereotype>>`.

**Simple example — flagged**

```plantuml
participant Billing
actor Customer
Customer -> Billing : pay(order)
```

A bare `participant` tells a generator nothing. `participant Billing <<service>>` or `database Billing` would pass. `actor` is already typed.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
codegen-untyped-participant = { allowed_stereotypes = ["service", "external", "gateway"] }
```

```plantuml
participant Billing <<thing>>
participant Ledger <<service>>
Billing -> Ledger : post(entry)
```

With a closed vocabulary configured (`allowed_stereotypes`), a stereotype outside the list is flagged too: `<<thing>>` fails and `<<service>>` passes.

### SEQ104 codegen-missing-return

**Severity:** `major` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

Every synchronous call (`->`) must get an explicit reply arrow. Fire-and-forget calls are marked async (`->>`).

**Simple example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : load(id)
```

What does `load` return? The diagram doesn't say.

**More complex example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
participant Db <<service>>
Api -> Repo : load(id)
Repo -> Db : selectLines(id)
Repo --> Api : order
```

The outer call is answered, but the nested `selectLines` call never gets its rows back.

### SEQ107 codegen-missing-failure-path

**Severity:** `major` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

Calls to a `database`, `queue` or `<<external>>` participant can fail, so they must sit inside a block that also shows the failure (error, timeout, missing, …).

**Simple example — flagged**

```plantuml
participant Api <<service>>
database OrderDb
Api -> OrderDb : save(order)
OrderDb --> Api : orderId
```

Happy path only: what happens when the database is down?

**More complex example — flagged**

```plantuml
participant Api <<service>>
participant Psp <<external>>
alt approved
  Api -> Psp : charge(card, amount)
  Psp --> Api : receipt
else declined
  Api -> Api : markUnpaid(order)
end
```

There is an `alt`, but neither branch reads as a failure: “declined” is not in the failure vocabulary. `else timeout` or `else error` would pass. The vocabulary is configurable.

### ACT001 missing-start

**Severity:** `major` · **Diagram type:** activity

An activity diagram with actions needs a `start` node, so the reader knows where the process begins.

**Simple example — flagged**

```plantuml
:Receive order;
:Ship order;
stop
```

Ends cleanly but never says where it begins.

**More complex example — flagged**

```plantuml
|Sales|
:Receive order;
|Warehouse|
:Pick items;
:Ship order;
stop
```

With swimlanes it is easy to miss: the first lane starts straight with an action.

### ACT002 missing-stop

**Severity:** `major` · **Diagram type:** activity

An activity flow must reach a `stop` or `end`. A process that never finishes is almost always an omission.

**Simple example — flagged**

```plantuml
start
:Receive order;
:Ship order;
```

No terminal node.

**More complex example — passes**

```plantuml
start
:Receive order;
if (fraud suspected?) then (yes)
  :Block account;
  kill
else (no)
  :Ship order;
  detach
endif
```

Passes: `kill` and `detach` also count as endings.

### ACT003 unlabelled-decision-branch

**Severity:** `minor` · **Diagram type:** activity

Each branch of a decision, and both outcomes of a loop, must carry a label (“yes”/“no” or a condition).

**Simple example — flagged**

```plantuml
start
if (in stock?) then
  :Ship order;
else
  :Back-order;
endif
stop
```

Which branch is “in stock”? Both branches are unlabelled.

**More complex example — flagged**

```plantuml
start
repeat
  :Call payment provider;
repeat while (failed?)
:Confirm order;
stop
```

A loop is a decision too: without `is (yes) not (no)` the reader cannot tell which way goes round and which way exits.

### CLS002 association-multiplicity

**Severity:** `major` · **Diagram type:** class

Associations, aggregations and compositions must state the numbers at both ends (e.g. `"1"` and `"*"`). Inheritance and dependency arrows are exempt.

**Simple example — flagged**

```plantuml
class Customer
class Order
Customer -- Order : places
```

One customer, many orders? Or the other way round? The most important design decision is missing.

**More complex example — flagged**

```plantuml
class Order
class OrderLine
class Customer
Customer "1" -- Order : places
Order *-- OrderLine : contains
```

Two traps: a multiplicity on one end only, and a composition (`*--`) that needs numbers too.

### STA002 unreachable-state

**Severity:** `major` · **Diagram type:** state

Every state other than the start must have at least one transition leading into it.

**Simple example — flagged**

```plantuml
[*] --> Draft
Draft --> Submitted : submit
Archived --> [*]
```

`Archived` can never be entered. Usually left over from a refactoring.

**More complex example — flagged**

```plantuml
[*] --> Draft
Draft --> Submitted : submit
Archived --> Archived : touch
Archived --> [*]
```

A state that only points at itself is still unreachable. Self-transitions don't count as a way in.

### UC001 orphan-actor-or-usecase

**Severity:** `major` · **Diagram type:** use case

Every actor and use case must be connected to something.

**Simple example — flagged**

```plantuml
actor Customer
actor Auditor
usecase (Place order)
Customer --> (Place order)
```

`Auditor` is connected to nothing.

**More complex example — passes**

```plantuml
actor Customer
usecase (Place order)
usecase (Verify address)
Customer --> (Place order)
(Place order) ..> (Verify address) : <<include>>
```

Passes: `Verify address` has no actor of its own, but any link counts, and it is included by a connected use case.

## Ambiguity (DIM-AMB)

**Weight 25% · 8 rules.** *Could two readers take it two different ways?*

Flags things that are present but vague: arrows with no label, conditions like “sometimes”, placeholders like “TBD” or “…”, replies that just say “ok”. Together with Completeness it decides whether a diagram reaches Level 4 (Precise).

### SEQ005 unlabelled-message

**Severity:** `minor` · **Diagram type:** sequence

Every message arrow must say what is being sent. Dashed return arrows may stay unlabelled by default.

**Simple example — flagged**

```plantuml
participant Shop
participant Stock
Shop -> Stock
```

Something is sent, but what?

**More complex example — flagged**

```plantuml
participant Shop
participant Stock
Shop -> Stock : reserve
Stock --> Shop
Shop ->> Stock
```

The unlabelled dashed return is tolerated. The unlabelled async (`->>`) message is flagged.

### SEQ006 no-self-message

**Severity:** `minor` · **Diagram type:** sequence

An arrow from a participant to itself usually models internal computation, which belongs in an activity diagram or a note.

**Simple example — flagged**

```plantuml
participant Shop
participant Stock
Shop -> Shop : validate basket
Shop -> Stock : reserve
```

Internal logic drawn as a message.

**More complex example — passes**

```plantuml
participant Scheduler
participant Shop
' pumllint: disable=SEQ006
Scheduler -> Scheduler : tick
Scheduler -> Shop : runNightlyBatch
```

Passes: where the self-call is genuinely part of the interaction, silence it on that line. The suppression is visible in review and counted in the score report.

### SEQ103 codegen-prose-message

**Severity:** `blocker` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

For code generation, call messages must look like signatures, `name(args)`, not prose.

**Simple example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : fetch the order details
Repo --> Api : order
```

Prose. `findOrderById(orderId)` would pass.

**More complex example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : findOrders(the latest open orders)
Repo --> Api : orders
```

Signature-shaped on the outside, prose on the inside: the argument contains function words (`the`) and is more than two words long.

### SEQ105 codegen-vague-guard

**Severity:** `blocker` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

Conditions on `alt`/`opt`/`loop` must be present and must not be a known vague phrase (“sometimes”, “if needed”, “otherwise”, …).

**Simple example — flagged**

```plantuml
participant Api <<service>>
participant Cache <<service>>
opt sometimes
  Api -> Cache : evict(key)
end
```

“Sometimes” cannot be evaluated.

**More complex example — flagged**

```plantuml
participant Api <<service>>
participant Cache <<service>>
alt hit
  Api -> Cache : get(key)
  Cache --> Api : value
else otherwise
  Api -> Api : recompute(key)
end
```

The first branch is fine; the `else` branch's “otherwise” is vague. Write the actual condition, e.g. `else miss`.

### SEQ106 codegen-elision-marker

**Severity:** `blocker` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

No placeholders (`…`, `TBD`, `TODO`, `etc`, `???`) in messages, conditions or notes.

**Simple example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : save(...)
Repo --> Api : id
```

The arguments were left out.

**More complex example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : save(order)
note right : retry policy TBD
Repo --> Api : id
```

The messages are fine, but a note admits the design is unfinished. A generator would have to invent the retry policy.

### SEQ109 codegen-uninformative-reply

**Severity:** `minor` · **Diagram type:** sequence · **Runs only with** `--profile codegen`

Replies must use a dashed arrow and name what comes back, not just “ok”, “done”, “success”, “response” or “result”.

**Simple example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : save(order)
Repo --> Api : ok
```

“ok” names no value. `orderId` would pass.

**More complex example — flagged**

```plantuml
participant Api <<service>>
participant Repo <<service>>
Api -> Repo : save(order)
Repo --> Api
```

A dashed reply with no label at all. The base rule SEQ005 tolerates this; the codegen profile does not.

### CLS003 unlabelled-association

**Severity:** `minor` · **Diagram type:** class

A plain association should say how the two classes relate (“places”, “owns”).

**Simple example — flagged**

```plantuml
class Customer
class Order
Customer "1" -- "*" Order
```

Related, but how?

**More complex example — flagged**

```plantuml
class Order
class OrderLine
class Customer
Order "1" *-- "1..*" OrderLine
Customer "1" --> "*" Order
```

Only the directed plain association is flagged. A composition (`*--`) already says “is made of” through its arrow.

### STA003 unlabelled-transition

**Severity:** `minor` · **Diagram type:** state

A transition between states should name what triggers it, using the convention `event [guard] / action`.

**Simple example — flagged**

```plantuml
[*] --> Draft
Draft --> Submitted
Submitted --> [*]
```

What moves a draft to submitted? Transitions from `[*]` and to `[*]` are exempt.

**More complex example — flagged**

```plantuml
[*] --> Draft
Draft --> Submitted : submit [form valid] / notifyReviewer
Submitted --> Draft
Submitted --> Approved : approve
Approved --> [*]
```

The full form is used once, but the way back to `Draft` is unlabelled: a rejection, a withdrawal, a timeout?

## Consistency (DIM-CON)

**Weight 15% · 11 rules.** *Does it follow one convention, here and across the model set?*

Checks naming conventions and house style, and, when several diagrams are checked together, that one thing keeps one name, one kind and one stereotype everywhere. Several of these rules stay switched off until your project tells pumllint what its convention is.

### GEN003 inline-skinparam

**Severity:** `minor` · **Diagram type:** all types

Styling (`skinparam`) belongs in a shared theme file pulled in with `!include`, not in each diagram.

**Simple example — flagged**

```plantuml
skinparam backgroundColor #EEEEEE
participant Shop
participant Stock
Shop -> Stock : reserve
```

Local styling drifts from the house style.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
inline-skinparam = { allowed = ["monochrome"] }
```

```plantuml
skinparam monochrome true
skinparam sequence {
  ArrowColor DeepSkyBlue
}
participant Shop
participant Stock
Shop -> Stock : reserve
```

With `allowed = ["monochrome"]` configured, the first line is tolerated; the styling block is still flagged.

### GEN004 participant-naming

**Severity:** `minor` · **Diagram type:** sequence

Declared participant names must follow the naming convention (default: `PascalCase`, dots allowed).

**Simple example — flagged**

```plantuml
participant order_service
participant Stock
order_service -> Stock : reserve
```

snake_case where the convention is PascalCase.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
participant-naming = { per_kind = { database = "^[A-Z][A-Za-z]*Db$", queue = "^[A-Z][A-Za-z]*Q$" } }
```

```plantuml
participant Shop
database Orders
queue OrderEventsQ
Shop -> Orders : save
Shop -> OrderEventsQ : publish
```

Per-kind conventions: with databases required to end in `Db`, `Orders` is flagged while the queue follows its own rule.

### ACT005 swimlane-naming

**Severity:** `minor` · **Diagram type:** activity

Swimlane names (who is responsible) must follow one convention (default: capitalised words).

**Simple example — flagged**

```plantuml
|billing dept.|
start
:Send invoice;
stop
```

Lower case and punctuation. “billing dept.”, “Billing” and “BILLING” end up as three owners.

**More complex example — flagged**

```plantuml
|Sales|
start
:Take order;
|Order-Fulfilment|
:Ship order;
stop
```

A hyphen is outside the default pattern. Change the pattern if your organisation's unit names use one.

### ACT006 verb-first-activity

**Severity:** `minor` · **Diagram type:** activity · **Dormant** until `verbs` or `verb_pattern` is set

Activities are named verb + object (“Validate order”), the classic process-modelling convention. Dormant until you list your verbs or a pattern.

**Simple example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
verb-first-activity = { verbs = ["validate", "ship", "send", "check"] }
```

```plantuml
start
:Order validation;
:Ship order;
stop
```

A noun phrase where a verb is expected.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
verb-first-activity = { verbs = ["validate", "ship", "send", "check"] }
```

```plantuml
start
:Validate order;
:Re-check stock;
stop
```

`Re-check` is not in the verb list. Either add it, or configure a `verb_pattern` such as `^Re-`, which lets a name pass by shape.

### CLS001 class-naming

**Severity:** `minor` · **Diagram type:** class

Class names follow `PascalCase`, member names start lower-case, unless your project configures otherwise. Enum values are exempt.

**Simple example — flagged**

```plantuml
class order_line
```

A class named in snake_case.

**More complex example — flagged**

```plantuml
class Order {
  +id : String
  +TotalPrice() : Money
}
enum Status {
  OPEN
  CLOSED
}
```

The member `TotalPrice()` is flagged; the upper-case enum values are not.

### UC002 usecase-actor-naming

**Severity:** `minor` · **Diagram type:** use case · **Dormant** until `verbs` or `verb_pattern` is set

Use cases are named verb + object (“Place order”). Dormant until you list your verbs or a pattern.

**Simple example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
usecase-actor-naming = { verbs = ["place", "cancel", "track"] }
```

```plantuml
actor Customer
usecase (Order placement)
Customer --> (Order placement)
```

A noun phrase.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
usecase-actor-naming = { verbs = ["place", "cancel", "track"] }
```

```plantuml
actor Customer
usecase (Order tracking) as Track
Customer --> Track
```

The alias `Track` looks fine, but the rule judges the label readers see, “Order tracking”.

### XD001 conflicting-participant-kind

**Severity:** `major` · **Diagram type:** sequence

Across diagrams, the same participant must be declared as the same kind (participant, database, queue, …).

**Simple example — flagged**

*Diagram A:*

```plantuml
participant Shop
database Orders
Shop -> Orders : save
```

*Diagram B:*

```plantuml
participant Shop
participant Orders
Shop -> Orders : save
```

One thing, two roles. Every site is reported; neither side is picked as “right”.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
conflicting-participant-kind = { authoritative = { Orders = "database" } }
```

*Diagram A:*

```plantuml
participant Shop
database Orders
Shop -> Orders : save
```

*Diagram B:*

```plantuml
participant Shop
database Orders
Shop -> Orders : load
```

*Diagram C:*

```plantuml
participant Shop
queue Orders
Shop -> Orders : publish
```

With `authoritative = { Orders = "database" }` configured, only the site that disagrees with the pin (the `queue`) is reported.

### XD002 conflicting-participant-stereotype

**Severity:** `minor` · **Diagram type:** sequence

Across diagrams, the same participant must carry the same `<<stereotype>>`. A missing stereotype is not a conflict.

**Simple example — flagged**

*Diagram A:*

```plantuml
participant Shop
participant Payments <<service>>
Shop -> Payments : pay
```

*Diagram B:*

```plantuml
participant Shop
participant Payments <<external>>
Shop -> Payments : pay
```

`Payments` is a service here and external there.

**More complex example — flagged**

*Diagram A:*

```plantuml
participant Shop
participant Payments <<service>>
Shop -> Payments : pay
```

*Diagram B:*

```plantuml
participant Shop
participant Payments
Shop -> Payments : pay
```

*Diagram C:*

```plantuml
participant Shop
participant Payments <<external>>
Shop -> Payments : pay
```

Why it matters: SEQ107 demands a failure path only for `<<external>>` participants, so the conflict decides whether the error branch is required at all.

### XD003 participant-name-case-collision

**Severity:** `minor` · **Diagram type:** sequence

Across sequence diagrams, names that differ only by upper/lower case are almost certainly the same thing spelled two ways.

**Simple example — flagged**

*Diagram A:*

```plantuml
participant Shop
participant OrderSvc
Shop -> OrderSvc : place
```

*Diagram B:*

```plantuml
participant Shop
participant Ordersvc
Shop -> Ordersvc : cancel
```

`OrderSvc` and `Ordersvc` become two lifelines.

**More complex example — flagged**

*Diagram A:*

```plantuml
participant Shop
participant OrderSvc
Shop -> OrderSvc : place
```

*Diagram B:*

```plantuml
participant Shop
Shop -> ORDERSVC : cancel
```

The drift enters through an arrow, not a declaration (the second diagram never declares `ORDERSVC`). Implicit lifelines count here.

### XD004 cross-type-name-collision

**Severity:** `minor` · **Diagram type:** all types

The same check across diagram types: a class `OrderService` and a lifeline `orderService` are the same entity drifting apart.

**Simple example — flagged**

*Diagram A:*

```plantuml
class OrderService
class Order
OrderService "1" -- "*" Order : manages
```

*Diagram B:*

```plantuml
participant Shop
participant orderService
Shop -> orderService : place
```

Class diagram and sequence diagram disagree on spelling.

**More complex example — flagged**

*Diagram A:*

```plantuml
class OrderService
class Order
OrderService "1" -- "*" Order : manages
```

*Diagram B:*

```plantuml
participant Shop
participant orderService
Shop -> orderService : place
```

*Diagram C:*

```plantuml
participant Shop
participant Orderservice
Shop -> Orderservice : cancel
```

One class site and two sequence sites. Every spelling is reported with its count, whatever order the files are checked in. XD003 also flags the two sequence spellings.

### XD005 cross-type-stereotype-conflict

**Severity:** `minor` · **Diagram type:** all types

The same entity must carry the same stereotype across diagram types.

**Simple example — flagged**

*Diagram A:*

```plantuml
class OrderService <<service>>
class Order
OrderService "1" -- "*" Order : manages
```

*Diagram B:*

```plantuml
participant Shop
participant OrderService <<gateway>>
Shop -> OrderService : place
```

`<<service>>` in the class model, `<<gateway>>` in the sequence: one entity, two contracts.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
cross-type-stereotype-conflict = { authoritative = { OrderService = "service" } }
```

*Diagram A:*

```plantuml
class OrderService <<service>>
class Order
OrderService "1" -- "*" Order : manages
```

*Diagram B:*

```plantuml
participant Shop
participant OrderService <<gateway>>
Shop -> OrderService : place
```

With `authoritative = { OrderService = "service" }` configured, only the non-conforming sequence site is reported.

## Traceability (DIM-TRC)

**Weight 5% · 5 rules.** *Can you find it, cite it, and tell who owns it?*

Governance basics: a title, a stable diagram name, an owner, a link to the requirement or decision it implements. Owner and requirement checks are dormant until you configure your own tag format.

### GEN001 missing-title

**Severity:** `minor` · **Diagram type:** all types

Every diagram needs a `title`, the name people use for it in reviews and reports.

**Simple example — flagged**

```plantuml
@startuml checkout
participant Shop
participant Bank
Shop -> Bank : capture
@enduml
```

No title line.

**More complex example — flagged**

```plantuml
@startuml checkout
title Checkout
participant Shop
participant Bank
Shop -> Bank : capture
@enduml

@startuml refund
participant Shop
participant Bank
Shop -> Bank : refund
@enduml
```

Two diagrams in one file are judged separately: the first has a title, the second does not.

### GEN002 unnamed-diagram

**Severity:** `info` · **Diagram type:** all types

`@startuml` should carry a name (`@startuml checkout`). The name fixes the exported image's file name.

**Simple example — flagged**

```plantuml
@startuml
title Checkout
participant Shop
participant Bank
Shop -> Bank : capture
@enduml
```

Unnamed: the image is named by position and changes when diagrams are added or reordered.

**More complex example — passes**

```plantuml
@startuml checkout-flow
title Checkout
participant Shop
participant Bank
Shop -> Bank : capture
@enduml
```

Passes. `pumllint fix` can add a name automatically from the file name.

### GEN006 owner-tag

**Severity:** `minor` · **Diagram type:** all types · **Dormant** until `pattern` is set

The diagram must name its owner (a team or person) in its title, header, footer, caption or a note. Dormant until you configure your tag format.

**Simple example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
owner-tag = { pattern = "owner: @[a-z-]+" }
```

```plantuml
@startuml checkout
title Checkout
participant Shop
participant Bank
Shop -> Bank : capture
@enduml
```

No owner anywhere. Here the convention is `owner: @team`.

**More complex example — passes**

With this in `pumllint.toml`:

```toml
[rules]
owner-tag = { pattern = "owner: @[a-z-]+" }
```

```plantuml
@startuml checkout
title Checkout
footer owner: @payments-team
participant Shop
participant Bank
Shop -> Bank : capture
@enduml
```

Passes: the tag can live in a footer (or header, caption, note).

### GEN007 requirement-link

**Severity:** `minor` · **Diagram type:** all types · **Dormant** until `pattern` is set

The diagram must reference the requirement or decision it implements (`REQ-123`, `ADR-0007`, a ticket key). Dormant until you configure your reference format.

**Simple example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
requirement-link = { pattern = "(REQ|ADR)-\\d+" }
```

```plantuml
@startuml checkout
title Checkout
participant Shop
participant Bank
Shop -> Bank : capture
@enduml
```

Nothing ties the diagram to a requirement.

**More complex example — passes**

With this in `pumllint.toml`:

```toml
[rules]
requirement-link = { pattern = "(REQ|ADR)-\\d+" }
```

```plantuml
@startuml checkout
title Checkout (REQ-142)
participant Shop
participant Bank
Shop -> Bank : capture
note right : see ADR-0007 for the capture timing
@enduml
```

Passes: the reference can sit in the title or a note.

### GEN010 duplicate-diagram-name

**Severity:** `minor` · **Diagram type:** all types

Two diagrams in the same file may not share a name. PlantUML would write both to the same image file, and the second silently overwrites the first.

**Simple example — flagged**

```plantuml
@startuml order
title Place order
participant Shop
participant Bank
Shop -> Bank : capture
@enduml

@startuml order
title Cancel order
participant Shop
participant Bank
Shop -> Bank : refund
@enduml
```

Both are `order`, so only one `order.png` survives.

**More complex example — flagged**

```plantuml
@startuml order
title Place order
participant Shop
participant Bank
Shop -> Bank : capture
@enduml

@startuml
title Cancel order
participant Shop
participant Bank
Shop -> Bank : refund
@enduml

@startuml order
title Refund order
participant Shop
participant Bank
Shop -> Bank : refund
@enduml
```

Both `order` sites are reported. The tool cannot know which one should keep the name, so it never renames for you. The unnamed middle diagram is GEN002's concern.

## Readability (DIM-RDB)

**Weight 5% · 6 rules.** *Is it small enough for a person to take in?*

Size limits: too many lifelines, messages, members, notes or nesting levels on one canvas. The limits are deliberately generous; they fire on diagrams that are clearly doing too much.

### GEN005 max-participants

**Severity:** `minor` · **Diagram type:** sequence, use case

Not too many lifelines on one canvas: by default 9 for sequence diagrams, 15 actors-plus-use-cases for use-case diagrams.

**Simple example — flagged**

```plantuml
participant P1
participant P2
participant P3
participant P4
participant P5
participant P6
participant P7
participant P8
participant P9
participant P10
P1 -> P2 : call2
P1 -> P3 : call3
P1 -> P4 : call4
P1 -> P5 : call5
P1 -> P6 : call6
P1 -> P7 : call7
P1 -> P8 : call8
P1 -> P9 : call9
P1 -> P10 : call10
```

Ten lifelines, one over the default of 9. Split the scenario by phase.

**More complex example — flagged**

<details><summary>Full diagram (28 lines)</summary>

```plantuml
actor A1
actor A2
actor A3
actor A4
usecase (Goal 1) as G1
usecase (Goal 2) as G2
usecase (Goal 3) as G3
usecase (Goal 4) as G4
usecase (Goal 5) as G5
usecase (Goal 6) as G6
usecase (Goal 7) as G7
usecase (Goal 8) as G8
usecase (Goal 9) as G9
usecase (Goal 10) as G10
usecase (Goal 11) as G11
usecase (Goal 12) as G12
A2 --> G1
A3 --> G2
A4 --> G3
A1 --> G4
A2 --> G5
A3 --> G6
A4 --> G7
A1 --> G8
A2 --> G9
A3 --> G10
A4 --> G11
A1 --> G12
```

</details>

A use-case diagram counts actors *plus* use cases: 4 + 12 = 16, over 15.

### GEN008 note-density

**Severity:** `minor` · **Diagram type:** all types

Notes should annotate the model, not replace it. Fires at 4+ notes when there is more than one note per two elements.

**Simple example — flagged**

```plantuml
participant Shop
participant Bank
Shop -> Bank : capture
note left : first we check the basket
note right : then the bank reserves funds
note over Shop : if it fails we retry
note over Bank : and after three tries we give up
```

Four notes on a three-element diagram: the retry logic is told in prose instead of modelled.

**More complex example — flagged**

With this in `pumllint.toml`:

```toml
[rules]
note-density = { max_chars_per_element = 30 }
```

```plantuml
participant Shop
participant Bank
participant Stock
Shop -> Stock : reserve
Shop -> Bank : capture
Bank --> Shop : receipt
note over Shop : The capture happens only after the reservation has been confirmed by the warehouse system, and if the warehouse does not answer within thirty seconds the shop releases the basket, notifies the customer and records the attempt for the nightly reconciliation run.
```

One note, but it carries the model. With the opt-in length test `max_chars_per_element = 30` configured, total note length is capped per element.

### GEN009 max-elements

**Severity:** `minor` · **Diagram type:** all types

A type-neutral size cap: at most 60 modelled elements (lifelines, messages, classes, relations, states, …) per diagram.

**Simple example — flagged**

<details><summary>Full diagram (61 lines)</summary>

```plantuml
class C1
class C2
class C3
class C4
class C5
class C6
class C7
class C8
class C9
class C10
class C11
class C12
class C13
class C14
class C15
class C16
class C17
class C18
class C19
class C20
class C21
class C22
class C23
class C24
class C25
class C26
class C27
class C28
class C29
class C30
class C31
class C32
class C33
class C34
class C35
class C36
class C37
class C38
class C39
class C40
C1 "1" -- "*" C2 : next
C2 "1" -- "*" C3 : next
C3 "1" -- "*" C4 : next
C4 "1" -- "*" C5 : next
C5 "1" -- "*" C6 : next
C6 "1" -- "*" C7 : next
C7 "1" -- "*" C8 : next
C8 "1" -- "*" C9 : next
C9 "1" -- "*" C10 : next
C10 "1" -- "*" C11 : next
C11 "1" -- "*" C12 : next
C12 "1" -- "*" C13 : next
C13 "1" -- "*" C14 : next
C14 "1" -- "*" C15 : next
C15 "1" -- "*" C16 : next
C16 "1" -- "*" C17 : next
C17 "1" -- "*" C18 : next
C18 "1" -- "*" C19 : next
C19 "1" -- "*" C20 : next
C20 "1" -- "*" C21 : next
C21 "1" -- "*" C22 : next
```

</details>

40 classes and 21 associations: 61 elements. Split by subdomain or package.

**More complex example — flagged**

<details><summary>Full diagram (62 lines)</summary>

```plantuml
state S1
state S2
state S3
state S4
state S5
state S6
state S7
state S8
state S9
state S10
state S11
state S12
state S13
state S14
state S15
state S16
state S17
state S18
state S19
state S20
state S21
state S22
state S23
state S24
state S25
state S26
state S27
state S28
state S29
state S30
state S31
[*] --> S1
S1 --> S2 : e1
S2 --> S3 : e2
S3 --> S4 : e3
S4 --> S5 : e4
S5 --> S6 : e5
S6 --> S7 : e6
S7 --> S8 : e7
S8 --> S9 : e8
S9 --> S10 : e9
S10 --> S11 : e10
S11 --> S12 : e11
S12 --> S13 : e12
S13 --> S14 : e13
S14 --> S15 : e14
S15 --> S16 : e15
S16 --> S17 : e16
S17 --> S18 : e17
S18 --> S19 : e18
S19 --> S20 : e19
S20 --> S21 : e20
S21 --> S22 : e21
S22 --> S23 : e22
S23 --> S24 : e23
S24 --> S25 : e24
S25 --> S26 : e25
S26 --> S27 : e26
S27 --> S28 : e27
S28 --> S29 : e28
S29 --> S30 : e29
S30 --> S31 : e30
```

</details>

The same cap applies to a long state machine: 31 states and 31 transitions. On ordinary sequence diagrams, SEQ011's message cap fires first.

### SEQ008 fragment-nesting-depth

**Severity:** `minor` · **Diagram type:** sequence

Blocks nested more than 3 deep (an `alt` inside a `loop` inside a `par` …) should move to a sub-diagram.

**Simple example — flagged**

```plantuml
participant Shop
participant Bank
loop each order
  alt card
    opt 3-D Secure
      loop retries < 3
        Shop -> Bank : authenticate
      end
    end
  end
end
```

Depth 4, one past the default of 3.

**More complex example — flagged**

```plantuml
participant Shop
participant Bank
par
  loop each order
    alt card
      critical capture
        Shop -> Bank : capture
      end
    end
  end
end
```

`par` and `critical` count as levels too. The depth is the same whatever the block kind.

### SEQ011 max-messages

**Severity:** `minor` · **Diagram type:** sequence

At most 30 messages per sequence diagram. The finding sits on the first message past the limit.

**Simple example — flagged**

<details><summary>Full diagram (33 lines)</summary>

```plantuml
participant Shop
participant Bank
Shop -> Bank : step1
Shop -> Bank : step2
Shop -> Bank : step3
Shop -> Bank : step4
Shop -> Bank : step5
Shop -> Bank : step6
Shop -> Bank : step7
Shop -> Bank : step8
Shop -> Bank : step9
Shop -> Bank : step10
Shop -> Bank : step11
Shop -> Bank : step12
Shop -> Bank : step13
Shop -> Bank : step14
Shop -> Bank : step15
Shop -> Bank : step16
Shop -> Bank : step17
Shop -> Bank : step18
Shop -> Bank : step19
Shop -> Bank : step20
Shop -> Bank : step21
Shop -> Bank : step22
Shop -> Bank : step23
Shop -> Bank : step24
Shop -> Bank : step25
Shop -> Bank : step26
Shop -> Bank : step27
Shop -> Bank : step28
Shop -> Bank : step29
Shop -> Bank : step30
Shop -> Bank : step31
```

</details>

31 messages.

**More complex example — passes**

With this in `pumllint.toml`:

```toml
[rules]
max-messages = { max = 40 }
```

<details><summary>Full diagram (33 lines)</summary>

```plantuml
participant Shop
participant Bank
Shop -> Bank : step1
Shop -> Bank : step2
Shop -> Bank : step3
Shop -> Bank : step4
Shop -> Bank : step5
Shop -> Bank : step6
Shop -> Bank : step7
Shop -> Bank : step8
Shop -> Bank : step9
Shop -> Bank : step10
Shop -> Bank : step11
Shop -> Bank : step12
Shop -> Bank : step13
Shop -> Bank : step14
Shop -> Bank : step15
Shop -> Bank : step16
Shop -> Bank : step17
Shop -> Bank : step18
Shop -> Bank : step19
Shop -> Bank : step20
Shop -> Bank : step21
Shop -> Bank : step22
Shop -> Bank : step23
Shop -> Bank : step24
Shop -> Bank : step25
Shop -> Bank : step26
Shop -> Bank : step27
Shop -> Bank : step28
Shop -> Bank : step29
Shop -> Bank : step30
Shop -> Bank : step31
```

</details>

With `max = 40` configured, the same diagram passes. Every size cap is a setting.

### CLS005 max-members-per-class

**Severity:** `minor` · **Diagram type:** class

At most 15 attributes and operations per class. A bigger box is a “god class” in the model as it would be in code.

**Simple example — flagged**

```plantuml
class Customer {
  +field1 : String
  +field2 : String
  +field3 : String
  +field4 : String
  +field5 : String
  +field6 : String
  +field7 : String
  +field8 : String
  +field9 : String
  +field10 : String
  +field11 : String
  +field12 : String
  +field13 : String
  +field14 : String
  +field15 : String
  +field16 : String
}
```

16 members.

**More complex example — flagged**

```plantuml
class Order {
  +attr1 : String
  +attr2 : String
  +attr3 : String
  +attr4 : String
  +attr5 : String
  +attr6 : String
  +attr7 : String
  +attr8 : String
  +op1()
  +op2()
  +op3()
  +op4()
  +op5()
  +op6()
  +op7()
  +op8()
}
```

Attributes and operations count together: 8 + 8 = 16.
