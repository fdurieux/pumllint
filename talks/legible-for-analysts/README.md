# Legible for analysts: a 45-minute session with a live demo

A version of the [round table](../semantic-linting-round-table/README.md)
for functional analysts and process engineers. It opens on
[Legible](https://fdurieux.github.io/), the programme pumllint belongs to,
maps the problems and the tooling across the delivery pipeline, and ends with
the [credit-application demo sandbox](../../sandbox/credit-application/README.md)
run live.

**The published copy** (slides as PDF and PowerPoint, speaker notes, team
hand-out) is at
<https://fdurieux.github.io/pumllint/talks/legible-for-analysts/>.

## What is in the deck

| Slides | Part | What it covers |
|--------|------|----------------|
| 1–2 | Opening | Legible: everything before code, checked before it is handed on; the session's three questions |
| 3–7 | ① The problem | **Problems to solve across the delivery pipeline**; what "makes sense" means; the credit-flow and OrderService examples; why every reader downstream fills the gaps |
| 8–12 | ② The contribution | **Tooling across the delivery pipeline**, with pumllint's place and the open gaps; from linter to model analysis; model smells; detect, measure, govern; the measured effect on AI-generated code |
| 13–16 | ③ In practice | **The demo set**; **why each diagram passes or fails**; **the live demo**; how the checks fit the workflow |
| 17–18 | Closing | The PoC vote; where to read more, with QR codes |
| 19–22 | Hand-outs (hidden) | The go / no-go form and the three getting-started slides |

The speaker notes open with a run sheet: 44 minutes, 9 of them discussion,
and a minute of buffer. The live demo (slide 15) takes 9 minutes. The
sandbox's `WALKTHROUGH.md` is its script.

## Where the content comes from

The new slides quote what is already written rather than inventing it:

- **Problems × pipeline:** the four aspects and their problems follow the map on
  [fdurieux.github.io](https://fdurieux.github.io/) and
  [`docs/case-for-pumllint.md`](../../docs/case-for-pumllint.md) ("The
  problem"). The one measured figure is from [`EVIDENCE.md`](../../EVIDENCE.md).
- **Tooling × pipeline:** the gates per artefact come from the "fellow gates"
  table in [`docs/positioning-quadrant.md`](../../docs/positioning-quadrant.md)
  §6 and the open gaps from Legible's artefact table.
- **Demo and "why" slides:** these read
  [`demo-findings.json`](demo-findings.json).
  `tests/test_sandbox_credit_application.py` checks that file against a live
  pumllint run on the sandbox's diagrams, so the slides cannot drift from the
  tool.

## Building it

The same tools as the round table: Node.js and Python 3, plus LibreOffice,
poppler-utils, a Chromium-based browser and ImageMagick for the PDFs. Fifteen
of the 22 slides are the round table's own scripts, used in place, so only
this folder needs `npm install`:

```bash
cd talks/legible-for-analysts
npm install
sh build.sh             # builds into out/
sh build.sh --publish   # also refreshes docs/talks/legible-for-analysts/ (GitHub Pages)
```

In plain English: `npm install` fetches PptxGenJS, the library that writes
PowerPoint files. `sh build.sh` assembles the 22 slides, adds the speaker
notes, makes the findings on slides 5 and 6 appear on a click, and hides the
four hand-out slides. With LibreOffice installed it also exports the PDFs.
`--publish` copies the neutral build to the folder GitHub Pages serves. It
refuses to run while any of the personal settings below is set.

Your own version takes the same settings as the round table: `INTRO_SLIDES`,
`PRESENTER_NAME`, `PRESENTER_EMAIL` and `REPLY_BY`.

The three QR codes in `assets/` were generated once with
[segno](https://pypi.org/project/segno/), for the Legible site, the repository
and the sandbox. Regenerate them only if those addresses change.

## Files

| Path | What it is |
|------|------------|
| `slides/*.js` | This talk's own slides; `style.js` holds their shared look |
| `notes.js` | The speaker notes and timings; reused slides reuse the round table's notes |
| `merge-deck.js` | Assembles the deck from this talk's slides and the round table's |
| `demo-findings.json` | What pumllint reports on the sandbox's diagrams, read by slides 13 and 14 |
| `make-handout.js`, `post/*.py`, `config.js` | As in the round table |
| `site/index.html` | The landing page of the published copy |
