const pptxgen = require('pptxgenjs');
const { C, header, label } = require('./style.js');
const DEMO = require('../demo-findings.json');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, '③ In practice · one business case, four linked diagrams, drawn twice', 'The demo: a credit application');

// The set, left to right in the order a reader meets it
const boxes = [
  ['requirements.txt', 'CRD-101 … CRD-105', 'what must be designed'],
  ['credit-application', 'business process', 'who does what, in which order'],
  ['credit-decision', 'sequence diagram', 'the decision, derived from the process'],
  ['credit-scoring', 'sequence diagram', 'one step in detail'],
  ['application-status', 'state chart', 'the application’s life'],
];
const BY = 1.85, BW = 2.2, BH = 1.25, GAP = (12.35 - 5 * BW) / 4;
boxes.forEach(([file, kind, what], i) => {
  const x = 0.5 + i * (BW + GAP);
  s.addShape(S.RECTANGLE, { x, y: BY, w: BW, h: BH, fill: { color: i ? 'FFFFFF' : C.ROW }, line: { color: C.ROW_LINE, width: 1 } });
  s.addShape(S.RECTANGLE, { x, y: BY, w: BW, h: 0.42, fill: { color: C.HEAD }, line: { color: C.HEAD } });
  s.addText(file, { x: x + 0.08, y: BY, w: BW - 0.16, h: 0.42, fontSize: 13, bold: true, fontFace: 'Consolas', color: C.LIME, valign: 'middle', margin: 0 });
  s.addText([{ text: kind, options: { bold: true, breakLine: true } }, { text: what, options: { color: C.MUTED, fontSize: 13 } }],
    { x: x + 0.1, y: BY + 0.46, w: BW - 0.2, h: BH - 0.5, fontSize: 14, color: C.INK, valign: 'middle', margin: 0 });
  if (i) s.addShape(S.LINE, { x: x - GAP + 0.04, y: BY + BH / 2, w: GAP - 0.08, h: 0, line: { color: C.TITLE, width: 2, endArrowType: 'triangle' } });
});
s.addText([
  { text: 'Linked like a real set: ', options: { bold: true, color: C.INK } },
  { text: 'the same names (Customer, CreditOfficer, RiskEngine) and the same requirement IDs in every diagram, so pumllint can check the set as a whole and trace each requirement to the diagrams that draw it.' },
], { x: 0.5, y: BY + BH + 0.15, w: 12.35, h: 0.62, fontSize: 15, color: C.MUTED, valign: 'top', margin: 0 });

// The two versions and their verdicts, from demo-findings.json
const ok = DEMO.compliant, ko = DEMO['non-compliant'];
const n = Object.values(ko.counts).reduce((a, b) => a + b, 0);
const sev = ['blocker', 'critical', 'major', 'minor', 'info'].filter(k => ko.counts[k]).map(k => `${ko.counts[k]} ${k}`).join(', ');
const rows = [
  ['Compliant', C.TITLE, 'FFFFFF', '✔ Gate passes',
    `no findings · every diagram at Level 4 · ${ok.covered} of ${ok.requirements} requirements drawn`],
  ['Non-compliant', C.RED, C.RED_BG, '✖ Gate fails',
    `${n} findings (${sev}) · still Level 4 · ${ko.covered} of ${ko.requirements} requirements drawn, ${ko.unknown.length} unknown ID cited`],
];
const RY = 4.45, RH = 0.9;
rows.forEach(([name, color, fill, verdict, detail], i) => {
  const y = RY + i * (RH + 0.15);
  s.addShape(S.RECTANGLE, { x: 0.5, y, w: 12.35, h: RH, fill: { color: fill }, line: { color, width: 1.5 } });
  s.addShape(S.RECTANGLE, { x: 0.5, y, w: 2.3, h: RH, fill: { color }, line: { color } });
  s.addText(name, { x: 0.65, y, w: 2.1, h: RH, fontSize: 17, bold: true, color: C.WHITE, valign: 'middle', margin: 0 });
  s.addText([{ text: verdict, options: { bold: true, color, breakLine: true } }, { text: detail, options: { color: C.INK } }],
    { x: 3.0, y, w: 9.7, h: RH, fontSize: 15, valign: 'middle', margin: 0 });
});
s.addText('Every one of the eight diagrams renders.', { x: 0.5, y: RY + 2 * RH + 0.25, w: 12.35, h: 0.3, fontSize: 14, italic: true, color: C.MUTED, margin: 0 });

pres.writeFile({ fileName: 'demo-set.pptx' }).then(f => console.log('wrote', f));
