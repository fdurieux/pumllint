# Vendored copy of the Legible systemic impact model, v0.3

| | |
|---|---|
| source repository | `fdurieux/fdurieux.github.io` |
| file | `model/model.json` (generated there from `model/model-data.py`; never edited by hand) |
| version | 0.3, dated 2026-10-29 (`"version": "0.3"` in the file) |
| commit | `099a7373e5c7817953709e8a0af45f050fc67a5c` — "Systemic impact model v0.3: review corrections, degradation refinements, knowledge source (#2)", merged 2026-10-29 as that repository's #2 |
| sha256 of `model.json` | `42e6be8aa9a906a0af8a4db926c0ac1358ffaf5a35e5f9f6358f1cb5f911d992` |
| copied | 2026-10-30, byte for byte, by the session that built `kg_experiment/demo/` |

The demo's systemic-model view draws the model's reduced knowledge view
(five knowledge nodes, nine edges, four practices P9–P12) with the
layout of `recreate_experiment/knowledge-transfer/deck/tools/gen_cascade_slide.py`,
which reads this JSON for the edges' polarity and evidence class. The
copy is not fetched at build time: the image carries it. To refresh it,
copy the file from the source repository at the commit you want, update
this table, and regenerate the deck slide to see that the drawing still
holds.
