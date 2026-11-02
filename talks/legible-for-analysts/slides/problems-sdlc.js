const pptxgen = require('pptxgenjs');
const { C, header } = require('./style.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, '① The problem · what goes wrong before code, stage by stage', 'Problems to solve, across the delivery pipeline');

// The four aspects of the SAFe Continuous Delivery Pipeline (nomenclature only), with
// the problems Legible's map and this repository's docs name for each. Tags as in the sources.
const cols = [
  ['Continuous Exploration', 'where intent is formed', C.CE, [
    ['A diagram renders but does not make sense: a typo becomes a phantom participant, a branch is guarded by “sometimes”, one service is described two ways.'],
    ['Requirements and stories: their structure is checked, their wording and ambiguity are not.'],
    ['Models and decisions: gated for PlantUML, C4 and OpenAPI; open for ArchiMate, SysML, ARIS processes and ADRs.'],
  ]],
  ['Continuous Integration', 'where the checks run', C.CI, [
    ['Code has had quality gates for twenty years; the information it is built from has had none.'],
    ['A gap found here is found late: someone has already built on it.'],
    ['AI builds from the design at near-zero cost and fills gaps with guesses: from Level 1 sequence diagrams ~1 in 3 intended behaviours fail.', 'measured'],
  ]],
  ['Continuous Deployment', 'mostly no claim', C.CD, [
    ['Deploy, verify, monitor: nothing upstream is checked here, and this session claims nothing for them.'],
    ['Respond: responders inherit the models, if they are current and if they consult them.', 'hypothesis'],
  ]],
  ['Release on Demand', 'governance and learning', C.ROD, [
    ['No evidence that the design documentation is current when an auditor asks.'],
    ['No trend of documentation health to steer on.'],
    ['A process design never compared with what actually happens.', 'planned'],
  ]],
];
const X0 = 0.5, W = (12.35 - 3 * 0.14) / 4, Y0 = 1.62, HH = 0.74, BODY = 3.55;
cols.forEach(([name, sub, color, items], i) => {
  const x = X0 + i * (W + 0.14);
  s.addShape(S.RECTANGLE, { x, y: Y0, w: W, h: HH, fill: { color }, line: { color } });
  s.addText([{ text: name, options: { bold: true, breakLine: true } }, { text: sub, options: { italic: true, fontSize: 13 } }],
    { x: x + 0.14, y: Y0, w: W - 0.24, h: HH, fontSize: 16, color: C.WHITE, valign: 'middle', margin: 0 });
  s.addShape(S.RECTANGLE, { x, y: Y0 + HH, w: W, h: BODY, fill: { color: 'FFFFFF' }, line: { color: C.ROW_LINE, width: 1 } });
  // An evidence tag rides at the end of its own bullet, in brackets
  const runs = items.map(([t, tag], k) => ({ text: tag ? `${t} [${tag}]` : t, options: { bullet: true, breakLine: k < items.length - 1 } }));
  s.addText(runs, { x: x + 0.12, y: Y0 + HH + 0.14, w: W - 0.22, h: BODY - 0.24, fontSize: 13.5, color: C.INK, valign: 'top', margin: 0, paraSpaceAfter: 7 });
});

// Legible's one-line conclusion, under the four columns
const BY = Y0 + HH + BODY + 0.14;
s.addShape(S.RECTANGLE, { x: X0, y: BY, w: 12.35, h: 0.5, fill: { color: C.LIME }, line: { color: C.LIME } });
s.addText([{ text: 'Shift-left is a split, not a point: ', options: { bold: true } },
  { text: 'the artefacts are written in Continuous Exploration; the gates on them run in Continuous Integration.' }],
  { x: X0 + 0.2, y: BY, w: 12.0, h: 0.5, fontSize: 15, color: C.HEAD, valign: 'middle', margin: 0 });
console.log('bottom', (BY + 0.5).toFixed(2));

pres.writeFile({ fileName: 'problems-sdlc.pptx' }).then(f => console.log('wrote', f));
