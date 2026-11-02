const path = require('path');
const pptxgen = require('pptxgenjs');
const { C, header } = require('./style.js');
const { OUT, S: slideNo } = require('../config.js');
const CHECKS = require(path.join(OUT, 'checks.json')); // written by export_checks.py from pumllint itself
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, '② The contribution · the checks behind the level, drawn as a wheel', 'What the score is made of');

// One colour per dimension, with a tint for its ring of checks
const COL = {
  'DIM-SEM': ['3E6B48', 'C9DCCB'], 'DIM-CMP': ['42687D', 'C9D9E3'], 'DIM-AMB': ['B07A2E', 'EED9B6'],
  'DIM-CON': ['7E5470', 'E0CBD9'], 'DIM-TRC': ['6E7B4B', 'DCE2C6'], 'DIM-RDB': ['5B6770', 'D4DADF'],
};
const rad = d => d * Math.PI / 180;
const CX = 3.75, CY = 4.2;
const P = (deg, r) => [CX + r * Math.cos(rad(deg)), CY + r * Math.sin(rad(deg))];
// a ring segment: angles clockwise from 3 o'clock, as PowerPoint draws a block arc
const ring = (a0, a1, R, r, o) => s.addShape(S.BLOCK_ARC, Object.assign({
  x: CX - R, y: CY - R, w: 2 * R, h: 2 * R, angleRange: [a0 % 360, a1 % 360], arcThicknessRatio: (R - r) / R }, o));
const R0 = 0.96, R1 = 1.98, R2i = 2.04, R2 = 2.3;

// Six dimensions, clockwise from 12 o'clock; each spans its share of the score
let a = 270;
CHECKS.dimensions.forEach(d => {
  const [col, tint] = COL[d.id], span = 360 * d.weight, a1 = a + span;
  ring(a, a1, R1, R0, { fill: { color: col }, line: { color: C.WHITE, width: 2.5 } });
  const [px, py] = P(a + span / 2, (R0 + R1) / 2);
  s.addText(`${Math.round(d.weight * 100)}%`, { x: px - 0.45, y: py - 0.2, w: 0.9, h: 0.4, fontSize: span < 30 ? 13 : 19,
    bold: true, color: C.WHITE, align: 'center', valign: 'middle', margin: 0 });
  // the outer ring: one wedge per check in that dimension
  const n = d.rules.length, step = span / n;
  d.rules.forEach((_, k) => ring(a + k * step, a + (k + 1) * step, R2, R2i,
    { fill: { color: k % 2 ? tint : col }, line: { color: C.WHITE, width: 0.75 } }));
  // the label outside the wheel
  const mid = a + span / 2, [lx, ly] = P(mid, R2 + 0.22), right = Math.cos(rad(mid)) >= -0.05;
  s.addText([{ text: d.label, options: { bold: true, color: col, breakLine: true } },
    { text: `${n} checks`, options: { color: C.MUTED, fontSize: 12.5 } }],
    { x: right ? lx : lx - 1.95, y: ly - 0.27, w: 1.95, h: 0.54, fontSize: 14, align: right ? 'left' : 'right', valign: 'middle', margin: 0 });
  a = a1;
});

// The hub: syntax is a gate, not a share of the score
s.addShape(S.OVAL, { x: CX - R0 + 0.06, y: CY - R0 + 0.06, w: 2 * R0 - 0.12, h: 2 * R0 - 0.12, fill: { color: C.HEAD }, line: { color: C.HEAD } });
s.addText([{ text: 'Syntax', options: { bold: true, color: C.LIME, fontSize: 16, breakLine: true } },
  { text: 'a gate, not a weight', options: { color: C.WHITE, fontSize: 12 } }],
  { x: CX - 0.85, y: CY - 0.4, w: 1.7, h: 0.8, align: 'center', valign: 'middle', margin: 0 });

// Right: how to read it
const codegen = CHECKS.dimensions.reduce((t, d) => t + d.rules.filter(r => r.profiles.length).length, 0);
const dormant = CHECKS.dimensions.reduce((t, d) => t + d.rules.filter(r => r.dormant).length, 0);
const sw = CHECKS.severity_weights;
const RX = 7.85, RW = 5.0;
const items = [
  ['The size of a segment is its weight in the score. ', 'Completeness and ambiguity count most, because those are the gaps the next reader fills with a guess.'],
  ['Each finding counts against its dimension by severity: ', `blocker ${sw.blocker}, critical ${sw.critical}, major ${sw.major}, minor ${sw.minor}, info ${sw.info}.`],
  ['The outer ring has one wedge per check: ', `${CHECKS.total} in all. ${codegen} run only with the code-generation profile; ${dormant} stay off until a team sets its own convention.`],
  ['Syntax sits in the middle as a gate: ', 'a diagram that does not render is Level 1, whatever the rest says.'],
];
items.forEach(([b, t], i) => {
  const y = 1.75 + i * 1.05;
  s.addShape(S.RECTANGLE, { x: RX, y, w: 0.09, h: 0.88, fill: { color: C.LIME }, line: { color: C.LIME } });
  s.addText([{ text: b, options: { bold: true } }, { text: t }],
    { x: RX + 0.25, y, w: RW - 0.25, h: 0.88, fontSize: 14, color: C.INK, valign: 'middle', margin: 0 });
});
s.addText(`Every check, with what it looks for: slides ${slideNo(24)} to ${slideNo(27)} (appendix). Read from pumllint ${CHECKS.version}'s rule catalogue when this deck was built.`,
  { x: RX, y: 6.05, w: RW, h: 0.55, fontSize: 12, italic: true, color: C.MUTED, valign: 'top', margin: 0 });

pres.writeFile({ fileName: 'score-wheel.pptx' }).then(f => console.log('wrote', f));
