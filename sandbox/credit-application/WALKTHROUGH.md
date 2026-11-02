# A 15-minute live demo

A script for presenting the sandbox to functional analysts. Start it before
the session (`docker compose up`), open <http://localhost:8000>, and keep a
text editor open on `diagrams/non-compliant/`.

## 1. Every diagram renders (2 minutes)

Scroll through the page without reading the findings. Eight pictures, all of
them drawn without an error.

> *Ask:* "Which of these would you sign off?"

Most people cannot tell the left column from the right at a glance. That is
the point: a diagram that renders is not yet a diagram the next reader can
build on.

## 2. The compliant set (2 minutes)

Look at the top-left box: **Gate passes**. Every diagram is at Level 4, with no
findings. Under *Requirements*, CRD-101 to CRD-105 each name the diagrams that
draw them.

> *Say:* "This is what 'ready for hand-off' looks like: complete, unambiguous,
> owned, and traced to the requirements."

## 3. The non-compliant set, one diagram at a time (5 minutes)

For each pair, read the bold line under the finding first, then point at the
picture:

1. **Business process:** which branch of *Score sufficient?* approves? Nothing
   says so. And the flow never ends.
2. **Sequence:** the `alt` box has no condition, so the designer guessed. A
   fourth lifeline, *Custmer*, appeared from a typo.
3. **Scoring:** the risk engine is a *gateway* here and a *service* in the
   decision diagram. Neither file is wrong on its own; together they contradict
   each other.
4. **State chart:** what makes an application *Approved*? And how does one
   ever become *Withdrawn*?

> *Ask:* "Who downstream would have found this, and when?"

## 4. Fix one live (3 minutes)

In `diagrams/non-compliant/credit-application.puml`:

- change `if (Score sufficient?) then` to `if (Score sufficient?) then (yes)`;
- change `else` to `else (no)` on the line below *Approve credit*;
- add `stop` on a new line after `:Inform customer;`.

Save and reload. The three findings disappear, and the process card has no
findings left. Run `git checkout -- diagrams` afterwards to restore the demo.

## 5. Levels, gates and requirements (3 minutes)

- **Levels and gates.** Every non-compliant diagram still says *Level 4*. The
  level summarises how complete and precise the drawing is; the gate looks at
  severity, and one critical or major finding stops the hand-off. Open
  *Maturity report* for the per-diagram detail.
- **Requirements.** CRD-105, "the customer is informed", is drawn nowhere, and
  CRD-106 is cited but does not exist. That is a stale diagram, or a missing
  requirement.

> *Close:* "Each of these took pumllint a fraction of a second to find. In a
> review they take a careful reader; downstream, they become a guess."
