const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', INK = '1E2B22', LIME = '9BD12E',
      WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', GREY_BG2 = 'E2E2DF', MUTED = '4A5A4E', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('② The contribution · pumllint and SonarQube, compared as linters',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('The same pattern you already trust on code',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// Linter characteristics, side by side
const rows = [
  ['Analyses', 'diagram semantics, one diagram and across the set', 'code: control and data flow, security'],
  ['Detects', 'model smells', 'bugs, vulnerabilities, code smells'],
  ['Rates', 'maturity level 1–5', 'ratings A–E'],
  ['Gates', '--min-level', 'quality gate on new code'],
  ['Existing debt', 'ratchet: no diagram may get worse', 'Clean as You Code'],
  ['Runs in', 'editor (LSP) · command line · CI', 'IDE · CI scanner · server'],
];
const TX = 0.5, TY = 1.75, RH = 0.44;
const hdr = [
  { text: '', options: { fill: { color: BG } } },
  { text: 'pumllint · on diagrams', options: { bold: true, color: WHITE, fill: { color: HEAD } } },
  { text: 'SonarQube · on code', options: { bold: true, color: WHITE, fill: { color: GREY } } },
];
s.addTable([hdr, ...rows.map((r, i) => [
  { text: r[0], options: { bold: true, color: TITLE, fill: { color: BG } } },
  { text: r[1], options: { fill: { color: i % 2 ? ROW2 : ROW }, fontFace: r[0] === 'Gates' ? 'Consolas' : undefined, fontSize: r[0] === 'Gates' ? 14 : 15 } },
  { text: r[2], options: { color: '4A4A4A', fill: { color: i % 2 ? GREY_BG2 : GREY_BG } } },
])], { x: TX, y: TY, w: 8.3, colW: [1.75, 3.45, 3.1], rowH: RH, fontSize: 15, color: INK, valign: 'middle',
  margin: 0.08, border: { type: 'solid', pt: 1, color: BG } });

// Where they meet
const CX = 9.05, CW = 3.8, CH = 3.32;
s.addShape(S.RECTANGLE, { x: CX, y: TY, w: CW, h: CH, fill: { color: ROW }, line: { color: ROW } });
s.addShape(S.RECTANGLE, { x: CX, y: TY, w: CW, h: RH, fill: { color: HEAD }, line: { color: HEAD } });
s.addText('Where they meet', { x: CX + 0.15, y: TY, w: CW - 0.3, h: RH, fontSize: 15, bold: true, color: WHITE, valign: 'middle', margin: 0 });
const fy = TY + RH + 0.5, bw = 1.25, bh = 0.5;
s.addShape(S.RECTANGLE, { x: CX + 0.15, y: fy, w: bw, h: bh, fill: { color: HEAD }, line: { color: HEAD } });
s.addText('pumllint', { x: CX + 0.15, y: fy, w: bw, h: bh, fontSize: 14, bold: true, color: WHITE, align: 'center', valign: 'middle', margin: 0 });
s.addShape(S.RECTANGLE, { x: CX + CW - 0.15 - bw, y: fy, w: bw, h: bh, fill: { color: GREY }, line: { color: GREY } });
s.addText('SonarQube', { x: CX + CW - 0.15 - bw, y: fy, w: bw, h: bh, fontSize: 14, bold: true, color: WHITE, align: 'center', valign: 'middle', margin: 0 });
s.addShape(S.LINE, { x: CX + 0.2 + bw, y: fy + bh / 2, w: CW - 0.5 - 2 * bw + 0.1, h: 0,
  line: { color: INK, width: 1.5, endArrowType: 'triangle' } });
s.addText('-f sonar', { x: CX + 0.15 + bw, y: fy - 0.3, w: CW - 0.3 - 2 * bw, h: 0.28, fontSize: 12, fontFace: 'Consolas',
  color: INK, align: 'center', margin: 0 });
s.addText([
  { text: '✓ ', options: { bold: true, color: TITLE } },
  { text: 'Findings flow in: one dashboard, PR comments', options: { breakLine: true } },
  { text: '✗ ', options: { bold: true, color: 'B03A2E' } },
  { text: 'SonarQube does not analyse diagrams', options: { breakLine: true } },
  { text: '► ', options: { bold: true, color: TITLE } },
  { text: 'The maturity gate stays in pumllint' },
], { x: CX + 0.15, y: fy + bh + 0.15, w: CW - 0.3, h: CH - (fy - TY) - bh - 0.25, fontSize: 14, color: INK,
  valign: 'top', margin: 0, paraSpaceAfter: 6 });

// Round-table question 2, in the deck's lime question-box style
const qy = TY + CH + 0.3;
s.addShape(S.RECTANGLE, { x: TX, y: qy, w: CX + CW - TX, h: 0.9, fill: { color: LIME }, line: { color: LIME } });
s.addText([
  { text: 'Question: ', options: { bold: true } },
  { text: 'Which of these would you trust a tool to decide, and which stays a human review?' },
], { x: TX + 0.25, y: qy, w: CX + CW - TX - 0.5, h: 0.9, fontSize: 21, color: HEAD, valign: 'middle', margin: 0 });


pres.writeFile({ fileName: 'sonarqube.pptx' }).then(f => console.log('wrote', f));
