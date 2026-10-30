"""The systemic-model view: the Legible v0.3 reduced knowledge view with a
scenario's path laid over it, as SVG.

The drawing is the deck generator's
(``recreate_experiment/knowledge-transfer/deck/tools/gen_cascade_slide.py``):
its lanes, node positions, edge list, anchor geometry and colours are
imported, not copied, so the two renderings cannot drift apart. The
model JSON is the vendored copy in ``kg_experiment/demo/model/`` (see its
``SOURCE.md``); it supplies each edge's polarity and evidence class, as
in the slide. What this module adds is the overlay: the node where the
scenario's defect enters, the edges it travelled, and the node where it
was stopped or made visible, in one colour for the governed arm and one
for the baseline. Standard library only.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
DECK_TOOLS = REPO / "recreate_experiment" / "knowledge-transfer" / "deck" / "tools"
MODEL = HERE.parent / "model" / "model.json"

sys.path.insert(0, str(DECK_TOOLS))
import gen_cascade_slide as slide  # noqa: E402  (the layout tables; nothing runs on import)

RED, RED_PALE = "#B3261E", "#F9E3E1"
TEAL, TEAL_PALE = "#087E83", "#DDF1F0"

_model_cache: dict | None = None


def model() -> dict:
    global _model_cache
    if _model_cache is None:
        _model_cache = json.loads(MODEL.read_text(encoding="utf-8"))
    return _model_cache


def _edge_between(a: str, b: str) -> tuple[str, str, str] | None:
    for eid, x, y in slide.edges:
        if x == a and y == b:
            return eid, x, y
    return None


def render(spec: dict, arm: str, *, title: str | None = None) -> str:
    """``spec`` is one entry of views.SYSTEMIC; ``arm`` is 'G' or 'B'."""
    M = model()
    E = {e["id"]: e for e in M["edges"]}
    W, H, BW, BH = slide.W, slide.H, slide.BW, slide.BH
    colour, pale = (TEAL, TEAL_PALE) if arm == "G" else (RED, RED_PALE)
    armspec = spec.get(arm, {})
    path = armspec.get("path") or []
    stop = armspec.get("stop")
    entry = spec.get("entry")
    on_path = {(path[i], path[i + 1]) for i in range(len(path) - 1)}
    label = html.escape(title or "the reduced knowledge view with the scenario's path")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -36 {W} {H + 36}" role="img" '
           f'aria-label="{label}" class="cascade cascade-{arm}">',
           '<defs>'
           '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#44524B"/></marker>'
           '<marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#C27A1F"/></marker>'
           f'<marker id="ahp-{arm}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{colour}"/></marker>'
           '</defs>']
    for x0, t in slide.lanes:
        out.append(f'<rect x="{x0}" y="0" width="400" height="{H}" rx="12" fill="{slide.PALE}" opacity="0.55"/>')
        out.append(f'<text x="{x0 + 16}" y="-10" font-size="22" font-weight="600" fill="{slide.GREEN}" '
                   f'style="text-transform:uppercase;letter-spacing:1px" font-family="IBM Plex Sans, Arial, sans-serif">{html.escape(t)}</text>')
    # the model's edges, exactly as the slide draws them
    for eid, a, b in slide.edges:
        e = E[eid]
        pa, pb = slide.edge_endpoints(eid, a, b)
        measured = e["evidence"].startswith("M")
        neg = e["polarity"] == "-"
        col = slide.AMBER if neg else "#44524B"
        dash = "" if measured else ' stroke-dasharray="9,7"'
        out.append(f'<line x1="{pa[0]:.0f}" y1="{pa[1]:.0f}" x2="{pb[0]:.0f}" y2="{pb[1]:.0f}" stroke="{col}" '
                   f'stroke-width="2.5" marker-end="url(#{"ahm" if neg else "ah"})"{dash} opacity="{0.35 if (entry or path) else 1}"><title>{html.escape(eid)}: {html.escape(e.get("label", "") or "")} [{html.escape(e["evidence"])}]</title></line>')
    # the path the defect travelled, over the model's own edges
    for a, b in on_path:
        hit = _edge_between(a, b)
        if hit is None:
            continue
        pa, pb = slide.edge_endpoints(hit[0], a, b)
        out.append(f'<line x1="{pa[0]:.0f}" y1="{pa[1]:.0f}" x2="{pb[0]:.0f}" y2="{pb[1]:.0f}" stroke="{colour}" '
                   f'stroke-width="7" stroke-linecap="round" marker-end="url(#ahp-{arm})" opacity="0.9"/>')
    # the edge it would have taken next, had the oracle not caught it
    if armspec.get("would") and stop == "detection" and path:
        hit = _edge_between(path[-1], armspec["would"])
        if hit:
            pa, pb = slide.edge_endpoints(hit[0], path[-1], armspec["would"])
            out.append(f'<line x1="{pa[0]:.0f}" y1="{pa[1]:.0f}" x2="{pb[0]:.0f}" y2="{pb[1]:.0f}" stroke="{colour}" '
                       f'stroke-width="5" stroke-dasharray="4,10" stroke-linecap="round" opacity="0.7"/>')
    # the nodes
    for nid, (x, y, l1, l2, lever) in slide.nodes.items():
        base_fill = "#FDFDFB" if nid in ("tacit", "validation", "detection", "depchange", "dora", "diverse") else slide.AMBERPALE
        stroke, width, fill = (slide.GREEN if lever else slide.LINE), 2, base_fill
        tag = None
        if nid == entry:
            stroke, width, fill = colour, 5, pale
            tag = "defect enters here"
        if nid in path and nid != entry:
            stroke, width, fill = colour, 4, pale
        if nid == stop:
            stroke, width, fill = colour, 5, pale
            tag = ("made visible here" if armspec.get("visible") else
                   "resolved by an invented decision" if armspec.get("invented") else
                   "stopped here")
            if nid == entry:
                tag = "defect enters here, and is stopped here"
        out.append(f'<g><rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
                   f'<text x="{x + 12}" y="{y + 30}" font-size="22" font-weight="600" fill="{slide.INK}" font-family="IBM Plex Sans, Arial, sans-serif">{html.escape(l1)}</text>'
                   f'<text x="{x + 12}" y="{y + 56}" font-size="20" fill="{slide.GREEN if lever else slide.MUTED}" font-family="IBM Plex Sans, Arial, sans-serif">{html.escape(l2)}</text></g>')
        if tag:
            tw = 12 * len(tag) + 20
            out.append(f'<g><rect x="{x}" y="{y - 30}" width="{tw}" height="26" rx="13" fill="{colour}"/>'
                       f'<text x="{x + 10}" y="{y - 11}" font-size="18" font-weight="600" fill="#fff" font-family="IBM Plex Sans, Arial, sans-serif">{html.escape(tag)}</text></g>')
    if not entry and not path:
        out.append(f'<text x="{W / 2:.0f}" y="{H - 14}" text-anchor="middle" font-size="22" fill="{slide.MUTED}" font-family="IBM Plex Sans, Arial, sans-serif">no defect planted — nothing to place</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":  # a quick look: python cascade.py S2 B > out.svg
    sys.path.insert(0, str(HERE))
    import views
    sc = sys.argv[1] if len(sys.argv) > 1 else "S2"
    arm = sys.argv[2] if len(sys.argv) > 2 else "B"
    print(render(views.SYSTEMIC[sc], arm, title=f"{sc} {arm}"))
