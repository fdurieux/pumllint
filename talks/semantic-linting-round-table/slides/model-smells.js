const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', MUTED = '4A5A4E';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

s.addText('② The contribution · not always an error, always a reason to guess',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Code smells, model smells',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// The analogy: two cards joined by ≈
const AY = 1.72, AW = 5.85, AH = 1.3, HB = 0.42, AX = [0.5, 7.0];
const card = (x, head, headFill, bodyFill, line, runs) => {
  s.addShape(S.RECTANGLE, { x, y: AY, w: AW, h: AH, fill: { color: bodyFill }, line: { color: line, width: 1 } });
  s.addShape(S.RECTANGLE, { x, y: AY, w: AW, h: HB, fill: { color: headFill }, line: { color: headFill } });
  s.addText(head, { x: x + 0.18, y: AY, w: AW - 0.36, h: HB, fontSize: 16, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(runs, { x: x + 0.18, y: AY + HB + 0.04, w: AW - 0.36, h: AH - HB - 0.08, fontSize: 14, valign: 'middle', margin: 0 });
};
card(AX[0], 'Code smell · SonarQube', GREY, GREY_BG, GREY, [
  { text: 'Something in the code that makes it harder to understand, change or trust; not always a bug.',
    options: { color: '4A4A4A', breakLine: true } },
  { text: 'e.g. too complex · unreachable branch · unclosed resource',
    options: { color: GREY, italic: true } },
]);
card(AX[1], 'Model smell · pumllint', HEAD, ROW, ROW_LINE, [
  { text: 'Something in the diagram that makes it harder to interpret, implement or trust: ',
    options: { color: INK } },
  { text: 'a reason for the next reader to guess.', options: { color: INK, bold: true } },
]);
const dx = (AX[0] + AW + AX[1]) / 2, dd = 0.5;
s.addShape(S.OVAL, { x: dx - dd / 2, y: AY + AH / 2 - dd / 2, w: dd, h: dd, fill: { color: LIME }, line: { color: WHITE, width: 2 } });
s.addText('≈', { x: dx - dd / 2, y: AY + AH / 2 - dd / 2, w: dd, h: dd, fontSize: 24, bold: true, color: HEAD,
  align: 'center', valign: 'middle', margin: 0 });

// One real model smell per dimension, mixing diagram types
const rows = [
  ['Logical correctness', 'sequence', 'A participant sends messages but was never declared', 'SEQ001', 'critical'],
  ['Completeness', 'business process', 'The flow never reaches an end', 'ACT002', 'major'],
  ['Ambiguity', 'state chart', 'A transition with no label: what triggers it?', 'STA003', 'minor'],
  ['Consistency', 'across the set', 'One participant is a service here, a database there', 'XD001', 'major'],
  ['Traceability', 'any', 'No link to the requirement or decision it implements *', 'GEN007', 'minor'],
  ['Readability', 'any', 'Too many elements on one canvas (over 60)', 'GEN009', 'minor'],
];
const hdr = ['Dimension', 'Diagram', 'Model smell', 'Rule', 'Severity'].map(t =>
  ({ text: t, options: { bold: true, color: WHITE, fill: { color: HEAD } } }));
const body = rows.map((r, i) => {
  const fill = { color: i % 2 ? ROW2 : ROW };
  const hard = r[4] !== 'minor';
  return [
    { text: r[0], options: { bold: true, fill } },
    { text: r[1], options: { fill, color: MUTED } },
    { text: r[2], options: { fill } },
    { text: r[3], options: { fill, fontFace: 'Consolas', fontSize: 14 } },
    { text: r[4], options: { bold: true, align: 'center', fill: { color: hard ? HEAD : fill.color }, color: hard ? WHITE : INK } },
  ];
});
const TY = AY + AH + 0.22;
s.addTable([hdr, ...body], { x: 0.5, y: TY, w: 12.35, colW: [2.3, 1.95, 5.5, 1.1, 1.5], rowH: 0.42,
  fontSize: 15, color: INK, valign: 'middle', margin: 0.08, border: { type: 'solid', pt: 1, color: 'F7F8F5' } });
s.addText('* checked once your requirement-tag format is configured', { x: 0.5, y: TY + 7 * 0.42 + 0.08,
  w: 12.35, h: 0.28, fontSize: 13, italic: true, color: MUTED, margin: 0 });


pres.writeFile({ fileName: 'model-smells.pptx' }).then(f => console.log('wrote', f));
