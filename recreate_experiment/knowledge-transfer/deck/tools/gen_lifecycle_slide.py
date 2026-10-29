"""Generate the deck's lifecycle slide, project/slides/lifecycle.html.

Usage: python3 -I gen_lifecycle_slide.py <output.html>
Standard library only; no input file. The texts are the deck's own (slide 2's
layers and losses, slide 10's checks).
"""
import sys

GREY, DARK, GREEN, AMBER, MUTED, CARD, EDGE = "#6B776F", "#1B2A24", "#2E7D5B", "#C27A1F", "#44524B", "#FDFDFB", "#DCE2DD"
FONT = "font-family:'IBM Plex Sans', Arial, sans-serif"
W, H = 1664, 548
COLS, CW, GAP = 5, 288, 46          # 5*288 + 4*46 = 1624, 40px kept for the return line
HEAD, RH, RGAP = 92, 120, 44         # header row, card row height, gap between rows
ROW_Y = [HEAD, HEAD + RH + RGAP, HEAD + 2 * (RH + RGAP)]
col_x = [i * (CW + GAP) for i in range(COLS)]
col_c = [x + CW // 2 for x in col_x]

stages = ["Business rules and processes", "Requirements", "Architecture", "Code", "Operations"]

build = [
    ("Process models, decision tables", "lost: the reason for a rule"),
    ("Requirements, scenarios", "lost: the unstated assumption"),
    ("UML models, API and data contracts", "lost: why the boundary is there"),
    ("The code, defects included", "lost: the why behind what it applies"),
    ("Runbooks, the running system", "lost: the ritual nobody wrote down"),
]
recover = [  # in column order; the flow reads right to left
    ("Rules and exceptions, with their enforcement state", "◇ the reason, the exception path"),
    ("Requirements written from behaviour", "◇ the assumption"),
    ("Contracts and models drawn from the code", "◇ why this boundary"),
    ("The system read: what it does", "◇ why this quirk"),
    ("Traces: tickets, incidents, questions asked", "◇ who to call, the ritual"),
]
validate = [
    ("Decision-table gap check, owner sign-off", ""),
    ("Trace coverage, scenarios run", ""),
    ("Diagram-to-code drift checks", ""),
    ("Rebuild from the record alone", ""),
    ("Compared with what runs: counts and a remainder", ""),
]

svg = []
svg.append('<defs>' + ''.join(
    f'<marker id="m-{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    for n, c in (("grey", GREY), ("dark", DARK), ("green", GREEN), ("amber", AMBER))) + '</defs>')
# upstream -> downstream axis above the headers
svg.append(f'<line x1="110" y1="14" x2="{W-150}" y2="14" stroke="{GREY}" stroke-width="2" marker-end="url(#m-grey)"/>')

def row_arrows(row, color, name, reverse=False):
    y = ROW_Y[row] + RH // 2
    for i in range(COLS - 1):
        x1, x2 = col_x[i] + CW + 4, col_x[i + 1] - 4
        if reverse:
            x1, x2 = x2, x1
        svg.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="3" marker-end="url(#m-{name})"/>')

row_arrows(0, DARK, "dark")
row_arrows(1, GREEN, "green", reverse=True)
row_arrows(2, AMBER, "amber")
# connectors: build -> recover at the operations column; recover -> validate at the rules column
x = col_c[4]
svg.append(f'<line x1="{x}" y1="{ROW_Y[0]+RH+4}" x2="{x}" y2="{ROW_Y[1]-6}" stroke="{GREEN}" stroke-width="3" marker-end="url(#m-green)"/>')
x = col_c[0]
svg.append(f'<line x1="{x}" y1="{ROW_Y[1]+RH+4}" x2="{x}" y2="{ROW_Y[2]-6}" stroke="{AMBER}" stroke-width="3" marker-end="url(#m-amber)"/>')
# the comparison: validate's last card back up to the running system, routed outside the cards
x, xr = col_x[4] + CW, W - 8
svg.append(f'<path d="M{x},{ROW_Y[2]+RH//2} L{xr},{ROW_Y[2]+RH//2} L{xr},{ROW_Y[0]+RH//2} L{x+6},{ROW_Y[0]+RH//2}" fill="none" stroke="{AMBER}" stroke-width="3" stroke-dasharray="8,8" marker-end="url(#m-amber)"/>')

def card(color, title, sub, accent):
    sub_html = f'<p style="font-size:18px;line-height:1.25;color:{accent};margin-top:6px">{sub}</p>' if sub else ""
    return (f'<div style="box-sizing:border-box;height:{RH}px;padding:12px 16px;background:{CARD};border:1px solid {EDGE};'
            f'border-left:8px solid {color};border-radius:10px;display:flex;flex-direction:column;justify-content:center">'
            f'<p style="font-size:20px;font-weight:600;line-height:1.2;color:{DARK}">{title}</p>{sub_html}</div>')

grid = []
grid.append(f'<div style="position:absolute;left:0px;top:0px;width:{W}px;display:grid;grid-template-columns:repeat(5, {CW}px);column-gap:{GAP}px;row-gap:{RGAP}px;grid-template-rows:{HEAD-RGAP}px {RH}px {RH}px {RH}px;width:{COLS*CW+(COLS-1)*GAP}px">')
for s in stages:
    grid.append(f'<p style="font-size:20px;font-weight:600;line-height:1.15;color:{DARK};align-self:end;padding-bottom:2px">{s}</p>')
for t, s in build:
    grid.append(card(DARK, t, s, AMBER))
for t, s in recover:
    grid.append(card(GREEN, t, s, GREEN))
for t, s in validate:
    grid.append(card(AMBER, t, s, AMBER))
grid.append('</div>')

out = f'''<section id="lifecycle" data-transition="fade" style="background:#F6F7F3;color:#1B2A24;{FONT};padding:128px 128px 160px;display:flex;flex-direction:column;gap:28px">
<h2 style="font-family:'Source Serif 4', Georgia, serif;font-size:64px;font-weight:600;line-height:1.1">Three passes over the lifecycle</h2>
<div style="position:relative;width:{W}px;height:{H}px">
<svg aria-label="Five lifecycle stages as columns, upstream on the left and downstream on the right, with three rows: the build pass left to right losing knowledge at each handoff, the recover pass right to left adding a person's knowledge at each stage, and the validate pass left to right ending with a rebuild compared against what runs" viewBox="0 0 {W} {H}" style="position:absolute;left:0px;top:0px;width:{W}px;height:{H}px">
{chr(10).join(svg)}
</svg>
<p style="position:absolute;left:0px;top:2px;font-size:18px;color:{GREY}">upstream</p>
<p style="position:absolute;right:0px;top:2px;width:140px;text-align:right;font-size:18px;color:{GREY}">downstream</p>
{chr(10).join(grid)}
</div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0 40px">
<p style="font-size:20px;line-height:1.3;color:{MUTED}"><b style="color:{DARK}">Build, downstream.</b> Each stage writes its artefacts and loses something at the handoff. By the time the loss reaches the code it looks like a decision.</p>
<p style="font-size:20px;line-height:1.3;color:{MUTED}"><b style="color:{GREEN}">Recover, upstream.</b> Start from what runs and work back one stage at a time. At each stage a person adds what the system cannot give (◇).</p>
<p style="font-size:20px;line-height:1.3;color:{MUTED}"><b style="color:{AMBER}">Validate, downstream again.</b> Check each recovered stage, rebuild from the record alone, and compare the rebuild with what runs. The dashed line is that comparison.</p>
</div>
<div style="position:absolute;left:128px;right:128px;bottom:64px;display:flex;justify-content:space-between">
<p style="font-size:24px;color:{GREY}">Preserving tacit and tribal knowledge in banking systems</p>
<p style="font-size:24px;color:{GREY}">13</p>
</div>
<aside>The same five layers as slide 2, now as columns, upstream on the left and downstream on the right. Three passes run over them. The first is the build as it ran, left to right: each stage writes its artefacts and loses something at the handoff, and the losses add up, which is the cascade of slide 7. The second is the reverse engineering of the pilot, right to left: it starts from what runs, the traces and the code, and works back one stage at a time to the rules. At each stage a person adds what the system cannot give, the reason, the assumption, the exception, the name. Those are the diamonds, and they are the sessions of weeks 3 to 6. The third pass is validation, left to right again: each recovered stage is checked with the tools of slide 10, the record is rebuilt from the writing alone, and the rebuild is compared with what runs. The dashed line closes the loop. The comparison gives counts and a remainder, never a percentage, and the rebuild is never used to repair the record. The next slide is the same pilot as a calendar.</aside>
</section>
'''
open(sys.argv[1], "w").write(out)
print("wrote", sys.argv[1])
