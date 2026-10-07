const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22', LIME = '9BD12E',
      WHITE = 'FFFFFF', MUTED = '4A5A4E', RED = 'B03A2E', RED_BG = 'F3DEDB', GREY_BG = 'ECECEA', GREY = '7A7A7A', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('② The contribution · the level predicts what happens downstream',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Does the level matter? Measured: yes',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// The two numbers
const TY = 1.8, TH = 2.35, TW = 5.6;
const tile = (x, fill, line, col, big, lvl, what) => {
  s.addShape(S.RECTANGLE, { x, y: TY, w: TW, h: TH, fill: { color: fill }, line: { color: line, width: 1.5 } });
  s.addText(lvl, { x: x + 0.25, y: TY + 0.15, w: TW - 0.5, h: 0.4, fontSize: 16, bold: true, color: col, margin: 0 });
  s.addText(big, { x: x + 0.25, y: TY + 0.5, w: TW - 0.5, h: 1.15, fontSize: 72, bold: true, color: col, valign: 'middle', margin: 0 });
  s.addText(what, { x: x + 0.25, y: TY + 1.65, w: TW - 0.5, h: 0.55, fontSize: 16, color: INK, valign: 'middle', margin: 0 });
};
tile(0.5, RED_BG, RED, RED, '~1 in 3', 'Sequence diagrams at Level 1', 'intended behaviours failed when the generated code ran');
tile(7.25, ROW, TITLE, TITLE, '~1 in 10', 'Sequence diagrams at Level 2 and up', 'intended behaviours failed when the generated code ran');
s.addShape(S.OVAL, { x: 6.38, y: TY + TH / 2 - 0.3, w: 0.6, h: 0.6, fill: { color: LIME }, line: { color: WHITE, width: 2 } });
s.addText('vs', { x: 6.38, y: TY + TH / 2 - 0.3, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: HEAD, align: 'center', valign: 'middle', margin: 0 });

// How it was measured
const HY = TY + TH + 0.25, HH = 1.3;
s.addShape(S.RECTANGLE, { x: 0.5, y: HY, w: 12.35, h: HH, fill: { color: WHITE }, line: { color: ROW_LINE, width: 1 } });
s.addShape(S.RECTANGLE, { x: 0.5, y: HY, w: 0.09, h: HH, fill: { color: LIME }, line: { color: LIME } });
const pts = [
  ['Not an opinion: ', 'AI tools generated the code, and it was run against acceptance tests written beforehand.'],
  ['Robust: ', 'held across three generators from two vendors and three prompt styles.'],
  ['No prompt fixes it: ', 'better prompting helped untidy diagrams, never the Level 1 ones; it cannot add guards and failure paths the diagram never had.'],
];
s.addText(pts.flatMap(([b, t], i) => [{ text: b, options: { bold: true } }, { text: t, options: { breakLine: i < pts.length - 1 } }]),
  { x: 0.8, y: HY + 0.05, w: 11.9, h: HH - 0.1, fontSize: 15, color: INK, valign: 'middle', margin: 0, paraSpaceAfter: 3 });

// Scope, stated plainly
s.addText([
  { text: 'Scope: ', options: { bold: true, color: INK } },
  { text: 'sequence diagrams and AI-generated code only. ' },
  { text: 'Expected, not measured: ', options: { bold: true, color: INK } },
  { text: 'less rework and a shorter lead time; a PoC is how we would find out.' },
], { x: 0.5, y: HY + HH + 0.12, w: 12.35, h: 0.4, fontSize: 14, color: MUTED, valign: 'middle', margin: 0 });

// Source in the pumllint repository
const REPO = 'https://github.com/fdurieux/pumllint/blob/main/';
s.addText([
  { text: 'Source: ', options: { bold: true, color: INK } },
  { text: 'github.com/fdurieux/pumllint · ' },
  { text: 'EVIDENCE.md', options: { hyperlink: { url: REPO + 'EVIDENCE.md' }, color: TITLE, underline: true } },
  { text: ', "What the product may claim" · in plain English: ' },
  { text: 'docs/evidence-explained.md', options: { hyperlink: { url: REPO + 'docs/evidence-explained.md' }, color: TITLE, underline: true } },
  { text: ', "Verdict 1"' },
], { x: 0.5, y: HY + HH + 0.52, w: 12.35, h: 0.34, fontSize: 13, color: MUTED, valign: 'middle', margin: 0 });
console.log('bottom', (HY + HH + 0.52 + 0.34).toFixed(2));

pres.writeFile({ fileName: 'evidence.pptx' }).then(f => console.log('wrote', f));
