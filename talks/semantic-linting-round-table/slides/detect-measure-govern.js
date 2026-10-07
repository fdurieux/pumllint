const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', INK = '1E2B22',
      LIME_HI = 'E3F3C2', WHITE = 'FFFFFF', MUTED = '4A5A4E', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('② The contribution · every finding has a severity; every diagram gets a level',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Detect, measure, govern',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// Stacked like the deck's original slide: a step tag on the left, its content on the right
const TX = 0.5, TW = 1.4, CX = 2.0, CW = 10.85, RH = 0.31, GAP = 0.14;
const tag = (y, h, n, t, sub) => {
  s.addShape(S.RECTANGLE, { x: TX, y, w: TW, h, fill: { color: TITLE }, line: { color: TITLE } });
  s.addText([
    { text: n, options: { fontSize: 22, bold: true, breakLine: true } },
    { text: t, options: { fontSize: 15, bold: true, charSpacing: 2, breakLine: !!sub } },
    ...(sub ? [{ text: sub, options: { fontSize: 12 } }] : []),
  ], { x: TX, y, w: TW, h, color: WHITE, align: 'center', valign: 'middle', margin: 0 });
};
const H = t => ({ text: t, options: { bold: true, color: WHITE, fill: { color: HEAD } } });
const opts = (y, colW) => ({ x: CX, y, w: CW, colW, rowH: RH, fontSize: 13, color: INK, valign: 'middle',
  margin: 0.04, border: { type: 'solid', pt: 1, color: BG } });

// 1 Detect: severities
const Y1 = 1.72;
tag(Y1, 6 * RH, '1', 'DETECT', 'findings');
const sev = [
  ['Blocker', 'Unusable as a specification', 'Fails the build · max Level 2'],
  ['Critical', 'Broken structure', 'Fails the build · blocks Level 5'],
  ['Major', 'Breaks a mandatory standard', 'Fails the build · blocks Level 5'],
  ['Minor', 'Breaks a recommended convention', 'Reported · lowers the score'],
  ['Info', 'Advisory', 'Reported · lowers the score slightly'],
];
s.addTable([[H('Severity'), H('Meaning'), H('Effect')], ...sev.map((r, i) => {
  const fill = { color: i % 2 ? ROW2 : ROW }, hard = i < 3;
  return [
    { text: r[0], options: { bold: true, fill: { color: hard ? HEAD : fill.color }, color: hard ? WHITE : INK } },
    { text: r[1], options: { fill } },
    { text: r[2], options: { fill, bold: hard } },
  ];
})], opts(Y1, [1.6, 4.3, 4.95]));

// 2 Measure: maturity levels
const Y2 = Y1 + 6 * RH + GAP;
tag(Y2, 6 * RH, '2', 'MEASURE', 'maturity');
const lv = [
  ['5', 'Method-complete', 'Every dimension strong, no majors: preconditions for AI code generation met (codegen profile only)'],
  ['4', 'Precise', 'Complete and unambiguous: ready for hand-off'],
  ['3', 'Disciplined', 'No blockers: ready for review, not yet for hand-off'],
  ['2', 'Structured', 'Coherent enough to work on, although it may still contain blockers'],
  ['1', 'Sketchy', "Don't build on it"],
];
s.addTable([[H('Level'), H('Name'), H('Read it as')], ...lv.map((r, i) => {
  const fill = { color: r[0] === '4' ? LIME_HI : (i % 2 ? ROW2 : ROW) };
  return [
    { text: r[0], options: { bold: true, align: 'center', fill } },
    { text: r[1], options: { bold: true, fill } },
    { text: r[2], options: { fill } },
  ];
})], opts(Y2, [0.75, 1.9, 8.2]));

// 3 Govern: the gate
const Y3 = Y2 + 6 * RH + GAP, GH = 0.66;
s.addShape(S.RECTANGLE, { x: TX, y: Y3, w: TW, h: GH, fill: { color: TITLE }, line: { color: TITLE } });
s.addText([{ text: '3  ', options: { fontSize: 22, bold: true } }, { text: 'GOVERN', options: { fontSize: 15, bold: true, charSpacing: 2 } }],
  { x: TX, y: Y3, w: TW, h: GH, color: WHITE, align: 'center', valign: 'middle', margin: 0 });
s.addShape(S.RECTANGLE, { x: CX, y: Y3, w: CW, h: GH, fill: { color: ROW }, line: { color: ROW } });
s.addText([
  { text: 'The team sets the bar, ', options: { bold: true } },
  { text: 'e.g. Level 2 everywhere, Level 4 before hand-off: a diagram below it does not move on.', options: { breakLine: true } },
  { text: 'Business processes: ', options: { bold: true } },
  { text: 'gate on findings, not on the level; no ambiguity rule covers activity diagrams yet.' },
], { x: CX + 0.12, y: Y3, w: CW - 0.24, h: GH, fontSize: 14, color: INK, valign: 'middle', margin: 0 });


pres.writeFile({ fileName: 'detect-measure-govern.pptx' }).then(f => console.log('wrote', f));
