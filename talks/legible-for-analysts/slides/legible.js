const path = require('path');
const pptxgen = require('pptxgenjs');
const { C, header, label } = require('./style.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, 'Opening · the programme this tool belongs to', 'Legible: checked before it is handed on', 9.9);

// The programme's one-sentence purpose, quoted from its site
s.addText([
  { text: '“Everything that comes before code, from requirements and processes to models, decisions and contracts, ' },
  { text: 'made query-able for humans and AI, and checked before it is handed to a developer or a dev-agent.', options: { bold: true } },
  { text: '”' },
], { x: 0.55, y: 1.62, w: 9.9, h: 0.9, fontSize: 17, italic: true, color: C.INK, valign: 'top', margin: 0 });

// The two halves
const halves = [
  ['Legible', 'query-able by humans and AI', [
    'one identity per entity, in every artefact that names it',
    'stable identifiers other artefacts can reference',
    'machine-readable forms beside the human ones',
    'traceable both ways: requirement → model → test'],
  ],
  ['Checked', 'gated before hand-off', [
    'a deterministic check on every change, at the desk and in the pipeline',
    'findings with a severity; a threshold fails the build',
    'a baseline, so an existing estate adopts it without a clean-up',
    'a graded score that shows progress'],
  ],
];
const HY = 2.62, HW = 4.85, HH = 2.95;
halves.forEach(([name, sub, items], i) => {
  const x = 0.5 + i * (HW + 0.2);
  s.addShape(S.RECTANGLE, { x, y: HY, w: HW, h: HH, fill: { color: i ? C.ROW : 'FFFFFF' }, line: { color: C.ROW_LINE, width: 1 } });
  s.addShape(S.RECTANGLE, { x, y: HY, w: HW, h: 0.55, fill: { color: C.HEAD }, line: { color: C.HEAD } });
  s.addText([{ text: name, options: { bold: true, color: C.LIME } }, { text: '   ' + sub, options: { color: C.WHITE } }],
    { x: x + 0.18, y: HY, w: HW - 0.3, h: 0.55, fontSize: 17, valign: 'middle', margin: 0 });
  s.addText(items.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < items.length - 1 } })),
    { x: x + 0.15, y: HY + 0.65, w: HW - 0.3, h: HH - 0.75, fontSize: 15, color: C.INK, valign: 'top', margin: 0, paraSpaceAfter: 6 });
});

// Where this talk's tool sits
s.addShape(S.RECTANGLE, { x: 0.5, y: 5.72, w: 9.9, h: 0.85, fill: { color: C.HEAD }, line: { color: C.HEAD } });
s.addShape(S.RECTANGLE, { x: 0.5, y: 5.72, w: 0.1, h: 0.85, fill: { color: C.LIME }, line: { color: C.LIME } });
s.addText([
  { text: 'pumllint', options: { bold: true, color: C.LIME } },
  { text: ' is the programme’s reference gate: it checks PlantUML diagrams, and business processes converted from ARIS by ', options: { color: C.WHITE } },
  { text: 'aris2puml', options: { bold: true, color: C.LIME } },
  { text: '. The rest of this session is about that gate.', options: { color: C.WHITE } },
], { x: 0.8, y: 5.72, w: 9.4, h: 0.85, fontSize: 15, valign: 'middle', margin: 0 });

// The programme's map, one scan away
const QS = 2.15, QX = 12.85 - QS, QY = 1.62;
s.addShape(S.RECTANGLE, { x: QX, y: QY, w: QS, h: QS, fill: { color: C.WHITE }, line: { color: C.ROW_LINE, width: 1 } });
s.addImage({ path: path.join(__dirname, '..', 'assets', 'qr-legible.png'), x: QX + 0.05, y: QY + 0.05, w: QS - 0.1, h: QS - 0.1,
  hyperlink: { url: 'https://fdurieux.github.io/' } });
s.addText([{ text: 'fdurieux.github.io', options: { bold: true, color: C.TITLE, hyperlink: { url: 'https://fdurieux.github.io/' } } }],
  { x: QX - 0.3, y: QY + QS + 0.08, w: QS + 0.3, h: 0.35, fontSize: 15, align: 'center', margin: 0 });
s.addText('The map: every artefact before code, the tool or practice that gates it, and the gaps still open.',
  { x: QX - 0.3, y: QY + QS + 0.45, w: QS + 0.3, h: 1.5, fontSize: 13, color: C.MUTED, align: 'center', valign: 'top', margin: 0 });

pres.writeFile({ fileName: 'legible.pptx' }).then(f => console.log('wrote', f));
