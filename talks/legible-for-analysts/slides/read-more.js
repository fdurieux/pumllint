const path = require('path');
const pptxgen = require('pptxgenjs');
const { C, header, label } = require('./style.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
const REPO = 'https://github.com/fdurieux/pumllint';
const BLOB = REPO + '/blob/main/';
const TREE = REPO + '/tree/main/';
const PAGES = 'https://fdurieux.github.io/';
header(s, 'Closing · where to read more', 'pumllint on GitHub', 9.9);

// The repository, large, with its QR code
const BY = 1.68, BH = 1.0, BW = 10.0;
s.addShape(S.RECTANGLE, { x: 0.5, y: BY, w: BW, h: BH, fill: { color: C.HEAD }, line: { color: C.HEAD } });
s.addShape(S.RECTANGLE, { x: 0.5, y: BY, w: 0.12, h: BH, fill: { color: C.LIME }, line: { color: C.LIME } });
s.addText([{ text: 'github.com/fdurieux/pumllint', options: { hyperlink: { url: REPO }, color: C.LIME, bold: true } }],
  { x: 0.85, y: BY + 0.08, w: BW - 0.5, h: 0.55, fontSize: 32, valign: 'middle', margin: 0 });
s.addText('Open source (GPL-3.0) · pip install pumllint · Python 3.11 or later, no dependencies',
  { x: 0.85, y: BY + 0.6, w: BW - 0.5, h: 0.32, fontSize: 15, color: C.WHITE, valign: 'middle', margin: 0 });
const QS = 2.2, QX = 12.85 - QS, QY = BY + BH - QS;
s.addShape(S.RECTANGLE, { x: QX, y: QY, w: QS, h: QS, fill: { color: C.WHITE }, line: { color: C.ROW_LINE, width: 1 } });
s.addImage({ path: path.join(__dirname, '..', 'assets', 'qr-github.png'), x: QX + 0.05, y: QY + 0.05, w: QS - 0.1, h: QS - 0.1, hyperlink: { url: REPO } });

// Key documents, three columns by what the reader wants
const groups = [
  ['START HERE', [
    ['Legible', 'the programme: every artefact before code, its gate, its gaps', PAGES],
    ['README', 'what pumllint does, install, quick start', REPO + '#readme'],
    ['Guides by audience', 'which document to read for your role', BLOB + 'docs/README.md'],
    ['The demo sandbox', 'this session’s credit application, to run yourself', TREE + 'sandbox/credit-application'],
  ]],
  ['WHY IT MATTERS', [
    ['The case for pumllint', 'the management case: cost and payoff', BLOB + 'docs/case-for-pumllint.md'],
    ['pumllint in the SDLC', 'where the value lands, claim by claim', BLOB + 'docs/value-in-the-sdlc.md'],
    ['The evidence, explained', 'the measured result, from scratch', BLOB + 'docs/evidence-explained.md'],
    ['Where tooling pays', 'the delivery-tooling landscape', BLOB + 'docs/sdlc-tooling-landscape.md'],
  ]],
  ['USING IT', [
    ['Findings and scores', 'reading findings and maturity levels', BLOB + 'docs/findings-and-scores.md'],
    ['The 360° rule map', 'every check, by dimension, with examples', BLOB + 'docs/rule-map.md'],
    ['Linting business processes', 'ARIS processes as activity diagrams', BLOB + 'docs/business-processes.md'],
    ['Setup and CI', 'editor, pipeline, ratchet, SonarQube', BLOB + 'docs/setup-and-ci.md'],
  ]],
];
const TOP = BY + BH + 0.28, CW = (12.35 - 2 * 0.3) / 3, RH = 0.74;
groups.forEach(([title, rows], c) => {
  const x = 0.5 + c * (CW + 0.3);
  label(s, title, x, TOP, CW);
  rows.forEach(([name, what, url], r) => {
    const y = TOP + 0.38 + r * RH;
    s.addShape(S.LINE, { x, y: y + RH - 0.04, w: CW, h: 0, line: { color: C.ROW_LINE, width: 0.75 } });
    s.addText([{ text: name, options: { bold: true, color: C.TITLE, hyperlink: { url }, breakLine: true } }, { text: what, options: { color: C.MUTED, fontSize: 13 } }],
      { x, y, w: CW, h: RH - 0.06, fontSize: 15, valign: 'middle', margin: 0 });
  });
});
console.log('bottom', (TOP + 0.38 + 4 * RH).toFixed(2));

pres.writeFile({ fileName: 'read-more.pptx' }).then(f => console.log('wrote', f));
