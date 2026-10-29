# The knowledge-preservation deck, and the document behind it

*Committed 2026-10-29. A deck for an audience outside this repository,
built in a session on the maintainer's ask from four sources: the
maintainer's draft slides, an LLM outline, this repository's record, and a
web research note on the kinds of knowledge. The bank it was drafted for is
named nowhere in these files; the author line is a placeholder.*

| path | what |
|---|---|
| `tacit-tribal-knowledge-deck.md` | The consolidated document: the draft deck and the outline merged (deck wins on conflicts), the repository findings, the seven-kinds research note, the storyline as built, and editorial notes. The record behind the deck. |
| `knowledge-types-research.md` | The research note on grounded, asserted, deductive, inductive, abductive, tacit and tribal knowledge, with sources. Six terms researched from the web on 2026-10-29; grounded knowledge added on the maintainer's ask. |
| `project/deck.json`, `project/slides/*.html` | The deck's files as published on claude.ai (Slides artefact, private), read back from the artefact on 2026-10-29 after the cascade slide was added. One file per slide, in the slide format of that artefact type; `deck.json` is the index. |
| `tools/gen_cascade_slide.py` | Generates `project/slides/cascade.html`, the reduced knowledge view of the Legible systemic impact model, from the model's JSON (`model/model.json` in `fdurieux/fdurieux.github.io`, v0.3). Standard library only. |

## What the deck says

Thirteen content slides and a four-slide appendix. The spine: knowledge
lives at every layer of the lifecycle and a gap cascades downstream; what
exists at each layer can be recovered and measured, and for behaviour the
code is the truth; each layer gives only what it holds, never why, and the
cascade runs both ways; the approach is four stages at every layer with a
human turn in the middle; the measure is counts with a remainder, never a
percentage, and two regeneration tests. The evidence is this repository's:
the recreation experiment, the coverage register, the degradation test, the
departing-expert case (`../DOMINIQUE-CASE.md`), and the systemic model's
out-of-sample review, present through its findings and, on slide 7, through
the model's reduced knowledge view at v0.3.

## Provenance

- The deck: a private Slides artefact on claude.ai, created 2026-10-29.
  These files are what the artefact served at the time of the commit; the
  artefact is the working copy and may move on.
- The model drawn on slide 7: `fdurieux/fdurieux.github.io`, `model/`, v0.3
  (merged 2026-10-29 as that repository's #2; v0.2 as its #1). The slide
  cites the version and the merge, not a tag; tags are the owner's to create.
- The research note's sources are listed in the note. Several reference
  hosts were outside the session's network allow-list, so those entries are
  cited from search extracts rather than the live pages; the note says so.

## Regenerate the cascade slide

```bash
python3 -I recreate_experiment/knowledge-transfer/deck/tools/gen_cascade_slide.py \
  /path/to/fdurieux.github.io/model/model.json \
  recreate_experiment/knowledge-transfer/deck/project/slides/cascade.html
```
