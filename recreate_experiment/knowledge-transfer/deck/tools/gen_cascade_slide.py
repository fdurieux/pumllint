import json, html, sys
# usage: gen_cascade_slide.py <model.json> <cascade.html>
# The layout tables below (lanes, nodes, edges, anchor geometry, colours) are
# copied in knowgov's demo/model/cascade_layout.py (since 2026-11-01; before
# that kg_experiment/demo/app/cascade.py imported them), which draws the same
# reduced view with a scenario's path laid over it; a change here is one there.
W, H = 1664, 620
BW, BH = 384, 72
INK, MUTED, GREEN, AMBER, LINE, PALE, AMBERPALE = '#1B2A24', '#6B776F', '#2E7D5B', '#C27A1F', '#DCE2DD', '#E6ECE7', '#FBF1E4'
lanes = [(0, 'People and intent'), (416, 'Derived artefacts'), (832, 'Product'), (1248, 'Use and delivery')]
Y0 = 40
nodes = {  # id: (x, y, line1, line2, lever?)
 'tacit':       (16, Y0+0,   'What only people know', 'Lever 1: elicit it', True),
 'updef':       (16, Y0+130, 'Upstream intent defects', 'wrong, missing, stale', False),
 'unknown':     (16, Y0+260, 'Unresolved decisions', 'counted as assumptions', False),
 'validation':  (16, Y0+440, 'Independent validation', 'Lever 2: owner validates', True),
 'deriveddef':  (432, Y0+70,  'Behaviour-carrying layer', 'contracts, tables, tests', False),
 'explderived': (432, Y0+190, 'Explanatory artefacts', 'models, prose: attenuated', False),
 'testdef':     (432, Y0+310, 'Tests share the premise', 'calibrated on the code', False),
 'drift':       (432, Y0+440, 'Artefact drift', 'Lever 3: externalise it', True),
 'depchange':   (848, Y0-10,  'Dependency change', 'no test pins it', False),
 'codedef':     (848, Y0+100, 'Implementation defects', 'what the code does', False),
 'escape':      (848, Y0+220, 'Escaped product defects', 'reach production', False),
 'detection':   (848, Y0+340, 'Independent detection', 'Lever 4: calibrated oracle', True),
 'confidence':  (848, Y0+470, 'Unwarranted confidence', 'a green gate over drift', False),
 'harm':        (1264, Y0+220, 'Adverse outcomes in use', 'users and operators', False),
 'dora':        (1264, Y0+340, 'Delivery performance', 'DORA metrics: hypothesis', False),
 'diverse':     (1264, Y0+470, 'More detection inputs', 'diverse rebuilds, coverage', False),
}
edges = [('E71','tacit','updef'),('E72','tacit','unknown'),('E50','updef','deriveddef'),('E75','updef','explderived'),('E52','updef','testdef'),
 ('E51','deriveddef','codedef'),('E73','codedef','deriveddef'),('E76','explderived','codedef'),('E74','depchange','codedef'),('E55','codedef','escape'),
 ('E64','escape','harm'),('E53','testdef','detection'),('E54','detection','escape'),('E56','validation','updef'),('E30','validation','unknown'),
 ('E57','validation','detection'),('E77','drift','confidence'),('E29','confidence','validation'),('E78','diverse','detection'),('E17','escape','dora')]
def centre(n): x,y=nodes[n][:2]; return x+BW/2, y+BH/2
def anchor(n, to):
    cx,cy=centre(n); tx,ty=to; dx,dy=tx-cx,ty-cy
    sx=(BW/2)/abs(dx) if dx else 1e9; sy=(BH/2)/abs(dy) if dy else 1e9; s=min(sx,sy)
    return cx+dx*s, cy+dy*s
def edge_endpoints(eid, a, b):
    """Both ends of an edge, with the E51/E73 pair offset so the reverse edge stays visible."""
    pa=anchor(a,centre(b)); pb=anchor(b,centre(a))
    if eid=='E73':  # offset the reverse edge from E51 so both are visible
        pa=(pa[0],pa[1]+14); pb=(pb[0],pb[1]+14)
    if eid=='E51':
        pa=(pa[0],pa[1]-14); pb=(pb[0],pb[1]-14)
    return pa, pb
def render(model_path):
    M = json.load(open(model_path, encoding='utf-8'))
    E = {e['id']: e for e in M['edges']}
    svg=[f'<svg aria-label="The reduced cascade of the systemic impact model with the four capture levers" viewBox="0 0 {W} {H}" style="position:absolute;left:0px;top:0px;width:{W}px;height:{H}px">',
     '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#44524B"/></marker>'
     '<marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#C27A1F"/></marker></defs>']
    for i,(x0,_) in enumerate(lanes):
        svg.append(f'<rect x="{x0}" y="0" width="400" height="{H}" rx="12" fill="{PALE}" opacity="0.55"/>')
    for eid,a,b in edges:
        e=E[eid]; pa, pb = edge_endpoints(eid, a, b)
        m = e['evidence'].startswith('M')
        neg = e['polarity']=='-'
        col = AMBER if neg else '#44524B'
        dash = '' if m else ' stroke-dasharray="9,7"'
        svg.append(f'<line x1="{pa[0]:.0f}" y1="{pa[1]:.0f}" x2="{pb[0]:.0f}" y2="{pb[1]:.0f}" stroke="{col}" stroke-width="2.5" marker-end="url(#{"ahm" if neg else "ah"})"{dash}/>')
    svg.append('</svg>')
    parts=[]
    for x0,t in lanes:
        parts.append(f'<p style="position:absolute;left:{x0+16}px;top:0px;width:380px;font-size:24px;font-weight:600;color:{GREEN};text-transform:uppercase;letter-spacing:1px">{t}</p>')
    for nid,(x,y,l1,l2,lever) in nodes.items():
        fill = '#FDFDFB' if nid in ('tacit','validation','detection','depchange','dora','diverse') else AMBERPALE
        c2 = GREEN if lever else MUTED
        parts.append(f'<div style="position:absolute;left:{x}px;top:{y}px;width:{BW}px;height:{BH}px;background:{fill};border:2px solid {GREEN if lever else LINE};border-radius:10px;padding:6px 10px;display:flex;flex-direction:column;justify-content:center;gap:2px">'
                     f'<p style="font-size:24px;line-height:1.15;font-weight:600;color:{INK};white-space:nowrap">{html.escape(l1)}</p>'
                     f'<p style="font-size:24px;line-height:1.15;color:{c2};white-space:nowrap">{html.escape(l2)}</p></div>')
    legend=(f'<p style="position:absolute;left:1264px;top:{Y0+10}px;width:384px;font-size:24px;line-height:1.3;color:{MUTED}">Solid line: measured, bounded. Dashed: hypothesis. Amber: the arrow reduces its target. Levers are the capture practices P9 to P12.</p>')
    section=f'''<section id="cascade" data-transition="fade" style="background:#F6F7F3;color:#1B2A24;font-family:'IBM Plex Sans', Arial, sans-serif;padding:128px 128px 160px;display:flex;flex-direction:column;gap:28px">
<h2 style="font-family:'Source Serif 4', Georgia, serif;font-size:64px;font-weight:600;line-height:1.1">Where knowledge capture acts on quality</h2>
<div style="position:relative;width:{W}px;height:{H}px">
{chr(10).join(svg)}
{chr(10).join(parts)}
{legend}
</div>
<div style="position:absolute;left:128px;right:128px;bottom:64px;display:flex;justify-content:space-between">
<p style="font-size:24px;color:#6B776F">Source: the systemic impact model v0.3, the reduced knowledge view (fdurieux.github.io, model/knowledge-view.svg)</p>
<p style="font-size:24px;color:#6B776F">7</p>
</div>
<aside>The reduced view of the systemic impact model, version 0.3, drawn from its JSON. Read it left to right. Knowledge held only by people feeds unresolved upstream intent and the assumptions a builder has to make. Those flow into the derived artefacts, through the layer the builder trusts most, into the code, and out into use. The code also writes back into the artefacts derived from it, and a dependency change can alter behaviour with no intent behind it. Four levers sit where the capture practices act: elicit what only people know, have the owner validate every claim, externalise into the normative home with a register that drift can be measured against, and keep an oracle calibrated independently of the code. Solid lines carry a bounded measurement from the recreation experiment, the review and the degradation test. Dashed lines are hypotheses, including every people-side edge and the path to delivery metrics. The model, its changelog and the generator script are in the Legible site repository under model/, version 0.3, merged 29 October 2026.</aside>
</section>
'''
    return section, {'pinned': len(parts)+2, 'svg_bytes': len('\n'.join(svg)),
                     'longest_label_px': max(len(v[2]) for v in nodes.values())*0.6*24*1.1}
if __name__ == '__main__':
    section, stats = render(sys.argv[1])
    open(sys.argv[2],'w',encoding='utf-8').write(section)
    print('pinned children in host:', stats['pinned'], '| svg bytes:', stats['svg_bytes'], '| longest label px est:', stats['longest_label_px'])
