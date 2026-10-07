# Round table: semantic linting of PlantUML diagrams

A 45-minute round table for teams that write PlantUML diagrams, or build on
them: business processes, sequence diagrams, state charts. It works through
three questions with the room:

1. **Do we recognise the problem?** A diagram can render and still leave the
   next reader guessing.
2. **What does a semantic linter add?** Findings with a severity, a maturity
   level per diagram, and an optional gate before a diagram is handed on.
3. **Is it worth a proof of concept (PoC)?** The session ends with a go /
   no-go vote and, on a go, the four things to agree before leaving.

**The published copy** (slides as PDF and PowerPoint, speaker notes, team
hand-out) is at
<https://fdurieux.github.io/pumllint/talks/semantic-linting-round-table/>.
This folder is the source it is built from.

## What is in the deck

| Slides | Part | What it covers |
|--------|------|----------------|
| 1–2 | Opening | The promise of the session, and its three questions |
| 3–7 | ① The problem | What "semantic correctness" means; two examples; why every reader downstream fills the gaps; how gaps are found today |
| 8–12 | ② The contribution | From linter to model analysis; model smells; detect, measure, govern; the measured effect on AI-generated code; the parallel with SonarQube |
| 13–15 | ③ The value | The same value stream before and after; how the checks fit the workflow |
| 16 | Closing | A short recap and the PoC vote |
| 17–20 | Hand-outs (hidden) | A go / no-go form for teams that were not in the room, and three slides on getting started with pumllint |

The speaker notes open with a timed run sheet: 26 minutes of presenting,
18 of discussion, a minute of buffer.

## The two examples

The examples on slides 4 and 5 are real diagrams, in `diagrams/`, and the
findings on the slides are what pumllint reports on them with its default
settings (`diagrams/lint.toml` keeps the repository's own conventions out):

| Diagrams | What pumllint reports |
|----------|-----------------------|
| `credit-flow/credit-application.puml` (a business process) and `credit-flow/credit-decision.puml` (the sequence diagram derived from it) | ACT003 twice (the decision's branches are not labelled), ACT002 (the process never ends; major, so the build fails), SEQ007 (an `alt` block with no condition: the designer's guess) |
| `order-service/checkout.puml` and `order-service/refund.puml` | XD002 on both files (OrderService is a `<<service>>` in one and a `<<gateway>>` in the other). Both files also have no title, so GEN001 fires too; the slide leaves it out to stay on the point |

`tests/test_talk_round_table.py` runs pumllint on these files and fails if
the findings drift away from what the slides and notes say, so a rule change
that would make the talk wrong is caught by the test suite, not by an
audience.

## Building it

You need [Node.js](https://nodejs.org/) and Python 3. For the PDFs you also
need LibreOffice and poppler-utils; for the speaker notes, a Chromium-based
browser; for the overview image, ImageMagick.

```bash
cd talks/semantic-linting-round-table
npm install
sh build.sh
```

In plain English: `npm install` fetches the one library the slide scripts
use (PptxGenJS, which writes PowerPoint files). `sh build.sh` then builds
the deck slide by slide into `out/semantic-linting-round-table.pptx`, adds
the speaker notes, the two click-to-reveal strips and the Morph transition,
and hides the four hand-out slides. If LibreOffice is installed it also
exports the PDFs: the full deck, the team hand-out (slides 17–20) and the
speaker notes with the run sheet. Anything it could not build, it says so
and skips.

### Your own version

The committed deck is neutral. To build one with your details, set them in
the environment instead of editing the slides:

```bash
INTRO_SLIDES=4 PRESENTER_NAME="A. Presenter" PRESENTER_EMAIL=a.presenter@example.com \
  REPLY_BY=31/10/2026 sh build.sh
```

`INTRO_SLIDES` is the number of your own slides in front of this deck (a
cover, an agenda, …): every slide number quoted in the speaker notes, the
run sheet and on slide 14 moves with it. The other three fill the return
strip on the team hand-out.

### Updating the published copy

```bash
sh build.sh --publish
```

This builds the neutral version and copies it to
`docs/talks/semantic-linting-round-table/`, which GitHub Pages serves; it
goes live when the change is merged to `main`. It refuses to run while any
of the four personal settings above is set, because the published copy is
public.

## Presenting it

- Slides 4 and 5 ask the room a question first; the findings strip appears
  on the next click.
- Slide 13 is a copy of slide 7. Click straight through it: PowerPoint then
  morphs the "before" value stream into the "after" one on slide 14 (other
  viewers show a fade).
- Slides 17–20 are hidden in the slide show. Send them as one PDF to teams
  that were not in the room.

## Files

| Path | What it is |
|------|------------|
| `slides/*.js` | One script per slide (`appendix.js` builds slides 18–20, `before.js` also the recap on slide 13) |
| `notes.js` | The speaker notes and the timing of every slide |
| `merge-deck.js` | Runs the slide scripts in order into one deck and attaches the notes |
| `make-handout.js` | The speaker-notes pages and the run sheet |
| `post/*.py` | Small edits PptxGenJS cannot make: notes paragraphs, animations, Morph, hidden slides |
| `config.js` | The personal settings above, and the pumllint version the appendix pins (read from `pyproject.toml`) |
| `site/index.html` | The landing page of the published copy |
| `diagrams/` | The example diagrams on slides 4 and 5 |
