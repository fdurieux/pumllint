# groma.md's diagram visualisation and pumllint, evaluated

*Dated evaluation, 2026-10-22, written against `cad7d13` (v0.34.0). The
question as posed: evaluate the relevance, for pumllint, of the
visualisation of diagrams as done in groma. It narrows the same-day
[groma.md evaluation](groma-md-evaluation.md), whose bounds say the web
viewer was "characterized from documentation, not run". This note runs
it.*

**Verdict up front: no capability to adopt, nothing queued, and no
quadrant criterion moves. groma's map is its renderer, not a view of a
diagram: groma has no diagram language, so the picture is the only
output it has. pumllint's artefact is the `.puml`, and PlantUML already
draws it. Of groma's eight visual devices, one carries an idea pumllint
could use: show the reader which element a finding is about. Measured
against PlantUML's own SVG, that idea reaches 10 of 66 findings on the
bundled examples, and none on activity diagrams. Its feasible shape is
aris2puml's `--diagnose` precedent (emit `.puml`, let PlantUML draw), not
a viewer. Recorded, not queued.**

*Bounds: groma.md 0.7.2 (npm `latest`) ran `groma export` twice over a
scratch copy of groma's own repository at `4f7ffac`, the same commit the
first note read. The static site was opened in the pre-installed
Chromium through Playwright 1.56.1: iso view, 2D view, and an actor
selected with its flows listed. Lighting a flow did not respond to a
scripted click, so the lit route, the ghosts, the time machine and the
task pins are taken from groma's viewer docs. The live `groma web`
server, the TUI and the PR Action were not run; they share the core
sheet the export ships. PlantUML 1.2026.6 (sha256 checked against `tests.yml`'s pin) rendered
the 14 files in `examples/` to SVG with `-Playout=smetana`, because the
container has no Graphviz. Whether `dot` layout adds source lines to
class, state and use-case links was not tested. Findings are `pumllint
examples/ -f json` at `cad7d13` with the repository's own config.*

## 1. What groma draws, observed

The export of groma's own model (1 system, 5 containers, 115
components, 6 flows) is a read-only web application:

| | groma export | pumllint `score -f html` |
|---|--:|--:|
| Files | 7 | 1 |
| Size | 11 MB (6.0 MB `index.html`, 3.2 MB `snapshot.js`, 1.0 MB `render.js`, three 1200×630 PNG covers) | 22.6 KB (`docs/example-maturity-report.html`) |
| Scripts | a bundled JS application | 0 `<script>` elements |
| Byte-stable across runs | **no**: a `generation` stamp and the layout `timings` in milliseconds differ. Masking both, the two exports are identical | yes, by contract (`tests/test_pilot_example.py`) |

What the page shows:

- **One computed world.** Core composes a "sheet" (islands, slabs,
  buildings, zones, routes) and the viewer "may not move a footprint or
  reroute a relationship". Layout is deterministic: every coordinate
  matched across the two exports.
- **Three projections of the same sheet**: an isometric blueprint, a 2D
  plan and a layers view, plus a hierarchy tree (actors, structure,
  externals) and a detail pane per element (description, relationship
  table, flows through it, children).
- **Flows lit over structure.** Selecting an actor lists its flows
  (observed); a selected flow lights its routes on the standing map
  (docs). A flow is never its own picture.
- **Ghosts** for drafted elements, distinct from observed ones.
- **A time machine.** The export fixes one revision or a `--from`/
  `--revision` comparison; the Action posts the link on PRs.
- **Social covers**, rendered in-process (resvg WebAssembly, bundled
  fonts), and Backlog task pins on elements in the live server.
- **Component buildings** whose height and shape follow the observed
  code.

The manifesto's heading, "Store architecture, not diagrams", is the key
to all of it. The viewer is not one way to look at a diagram among
several. It is the only rendering of a model that has no diagram file.

## 2. Each device, against pumllint

| groma device | pumllint's nearest surface | Relevance |
|---|---|---|
| Computed layout, viewer cannot move it | PlantUML's layout, via `dot` or Smetana | None. The picture belongs to the renderer, and pumllint "has never needed to know which engine drew the picture" (the Graphviz record, 2026-08-28). |
| One world, many projections | The model set: N diagrams joined by XD's symbol table | Inverse. groma's single model makes cross-view identity a given. pumllint's input is N authored files, and checking that identity is XD001–005. A map would draw what XD checks. It would not fire XD's open gated items (G2 display-name identity, `ref over`). |
| Flows lit over structure | A sequence diagram beside a class or component diagram, joined by XD | As above: pumllint checks the join, groma draws it. A groma flow is linear (no branches or loops), the thinnest sequence the first note scored. |
| Ghosts, draft against observed | none | groma's plan↔code side. Diagram↔code conformance stays "watch, don't build" (2026-07-26); the first note's §6.2 holds. |
| Time machine, before/after on PRs | `--baseline`, trend deltas, the Action's `format: html` upload | Different object. groma diffs the model, while pumllint diffs scores and findings. The HTML report's 0.15.0 design record ("no JS", "deliberately no charts/history", deterministic) stands, and an 11 MB non-byte-stable application is the shape it refused. |
| Social covers | `-f badge` (shields endpoint JSON) | None. The badge record already declined SVG output. |
| Task pins, building height | none | Out of scope: work tracking and code metrics. |
| Selection: "what is this about?" | the line and column on every finding; the LSP | **The one transferable idea** (§3). |

## 3. The transferable idea, measured: findings on the picture

groma lets a reader click an element and see everything about it.
pumllint's equivalent would show the reader the drawn element a finding
is about, which the HTML report cannot: it lists findings as text
beside a picture it does not have. The audience is the one the report
was built for, the architect who never runs a CLI. The LSP already
serves the modeller, who has the source and an editor preview side by
side.

**Route A, overlaying PlantUML's SVG.** PlantUML 1.2026.6 writes
`data-source-line` (0-based) on sequence messages and participants and on
class, state and use-case entities. Class, state and use-case links
carry `data-entity-1`/`data-entity-2` and no line. Activity diagrams
carry nothing beyond `data-diagram-type`. Joining each finding's line
to an SVG element over the 14 examples:

| Family | Findings | On a drawn element | No drawn element | Diagram-level (line 1) |
|---|--:|--:|--:|--:|
| GEN | 41 | 0 | 1 (inline `skinparam`) | 40 |
| SEQ | 10 | 5 | 5 (unterminated blocks, open activations) | 0 |
| CLS | 4 | 1 | 3 (a member, an unlabelled association) | 0 |
| STA | 3 | 2 | 1 (an unlabelled transition) | 0 |
| UC | 2 | 2 | 0 | 0 |
| ACT | 6 | 0 | 6 | 0 |
| **All** | **66** | **10** | **16** | **40** |

Three facts limit the route:

- **Most findings are about the diagram, not an element.** 40 of 66 sit
  on line 1: title, name, ownership, references. The picture has nothing
  more specific to point at.
- **Activity diagrams carry no hooks at all.** That is the type
  aris2puml emits and the business-process guide recommends.
- **The joins that remain would be name joins.** Links, members and
  blocks are reachable only through `data-qualified-name` against names
  in a finding's message prose. A finding has no structured element
  field (`Violation` has rule, message, file, line, column). Adding one
  would be an additive report-shape change (owner decision §6.5 of the
  prioritisation note, answered yes 2026-09-07), but no consumer asks
  for it.

The route would also need the jar at report time. `--check-syntax`
already runs it as an optional external, "run, not linked", so the
dependency itself is not the obstacle. The reach is.

**Route B, emitting `.puml` and letting PlantUML draw it.** This is
aris2puml's `--diagnose`: the refused EPC is written as a `.puml`, with
the named nodes in red and the reason as a note. No renderer is built,
and the join is native, because the finding's line *is* the source
line. For pumllint, it would mean an annotated copy of each diagram:
offending declarations and arrows coloured (PlantUML has per-element
and per-arrow colour syntax), each finding attached as a note. It would
reuse the fixer's line-edit machinery, as the LSP's code actions did.
It should reach every finding a line can carry, activity included,
because it never needs the renderer to say what it drew. Diagram-level
findings become a legend. *Not built and not tested beyond the SVG
measurement above; the shape is recorded so that a trigger finds it.*

*Recorded, not queued. Trigger: an architect or reviewer, the HTML
report's audience, asking to see findings on the picture rather than
beside it. If it fires, Route B goes first, and Route A only if Route B
cannot reach a finding that the SVG can.*

## 4. Does visualisation change the first note's readings?

- **Substitution (§6.3) is confirmed, not widened.** The map is what an
  adopter running groma looks at instead of a hand-written C4-PlantUML
  file. It has no behavioural picture beyond linear flows, so it does
  not substitute for the five types pumllint parses, for XD, or for the
  maturity layer.
- **Producer through a converter (§6.1): unchanged.** The export ships
  the world and its sheet as JSON inside `snapshot.js`, so a converter
  could read the export rather than the OKF Markdown. That changes the
  converter's input, not its shape or its trigger, and the Markdown
  stays the record the generated-artefact principle points findings at.
- **Quadrant: unchanged.** No criterion scores visualisation. E3 counts
  CI, pre-commit, editors and dashboards, and a viewer of another tool's
  model is none of them. groma stays off the chart under the inclusion
  rule.
- **Open problems: none fire.** The 17 open checkboxes keep their gates.

## 5. Decision

- **Adopt:** nothing. **Build:** nothing. No checkbox is added.
- **Recorded, not queued:** findings on the picture, Route B first, on
  the trigger in §3.
- ***Never build*, in this question's vocabulary:**
  - a diagram renderer, layout engine or interactive map inside
    pumllint. "Not a diagram generator or renderer" (the case for
    pumllint) holds, as it held against the Ilograph export;
  - scripts in the HTML report, or a report that is not byte-stable;
  - a viewer for another tool's model.
- **Annotated in place:** the first note's bounds sentence, pointing
  here.
- **Re-litigate on:** the §3 trigger; PlantUML adding source lines to
  activity elements, which would raise Route A's reach; or groma
  shipping a PlantUML export (unchanged from the first note).

## 6. Reproducing

`$S` is a scratch directory; nothing runs on the working tree.

```bash
cd "$S" && npm init -y >/dev/null && npm i groma.md@0.7.2
git clone -q https://github.com/MrLesk/groma.md gm && git -C gm checkout -q 4f7ffac
(cd gm && "$S/node_modules/.bin/groma" export "$S/site")    # twice, to site2, for the diff
for f in index.html snapshot.js; do
  for d in site site2; do
    sed -E 's/"generation":[0-9]+/"generation":0/; s/"[a-zA-Z]+Milliseconds":[0-9.e+-]+/"ms":0/g' \
      "$d/$f" > "$d.$f.n"
  done
  cmp site.$f.n site2.$f.n && echo "$f identical modulo stamp and timings"
done

# findings on the picture
cp /path/to/pumllint/examples/*.puml svg/ && cd svg
java -jar plantuml-1.2026.6.jar -Playout=smetana -tsvg *.puml
pumllint ../examples/ -f json > findings.json   # from the repository root
```

Each finding is joined to its diagram's SVG (named by `@startuml <name>`,
or by the file stem) on `data-source-line == line - 1`. A finding on line
1 counts as diagram-level.

## Related reading

- [groma.md and pumllint — a live C4 map from code, evaluated](groma-md-evaluation.md):
  the three readings this note checks against the viewer.
- [The Ilograph export package, evaluated](export-ilograph-package-evaluation.md):
  the earlier "any export or render capability" refusal.
- [The Graphviz DOT ecosystem, evaluated](graphviz-dot-ecosystem-evaluation.md):
  the layout engine beneath PlantUML.
- [Understanding findings and scores](findings-and-scores.md): what the
  HTML report shows today.
- aris2puml's README §"Where it refused: `--diagnose`": Route B's
  precedent.
