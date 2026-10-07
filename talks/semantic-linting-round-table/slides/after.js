const pptxgen = require('pptxgenjs');
const { S: slideNo } = require('../config.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', LIME_HI = 'E3F3C2', WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', MUTED = '4A5A4E';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

s.addText('③ The value · check each diagram before the next step builds on it',
  { objectName: '!!subtitle', x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Shift left: checked before it is built on',
  { objectName: '!!title', x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// The same value stream as the 'before' slide, same positions (Morph pairs the !! names)
const st = [
  ['Customer journey', 'not linted', true],
  ['Business process', 'activity diagrams'],
  ['Sequence & state', 'charts: solution design'],
  ['Code', 'human & AI'],
  ['Release', 'test · production'],
];
const X0 = 0.5, W = 2.15, G = 0.4, Y = 2.65, HB = 0.45, HBODY = 0.5, SH = HB + HBODY;
const sx = i => X0 + i * (W + G);
st.forEach(([name, sub, off], i) => {
  const x = sx(i);
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: SH, objectName: `!!vs-${i}-box`, fill: { color: off ? GREY_BG : ROW },
    line: { color: off ? GREY : ROW_LINE, width: off ? 1.25 : 0.75, dashType: off ? 'dash' : 'solid' } });
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: HB, objectName: `!!vs-${i}-head`, fill: { color: off ? GREY : HEAD }, line: { color: off ? GREY : HEAD } });
  s.addText(name, { objectName: `!!vs-${i}-name`, x: x + 0.1, y: Y, w: W - 0.2, h: HB, fontSize: 16, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(sub, { objectName: `!!vs-${i}-sub`, x: x + 0.1, y: Y + HB, w: W - 0.2, h: HBODY, fontSize: 14, italic: !!off,
    color: off ? GREY : INK, valign: 'middle', margin: 0 });
  if (i === st.length - 1) return;
  const gx = x + W + G / 2;
  if (i === 1 || i === 2) {
    // A gate at the hand-off: findings for processes, Level 4 for solution design
    const d = 0.46;
    s.addShape(S.DIAMOND, { x: gx - d / 2, y: Y + SH / 2 - d / 2, w: d, h: d, fill: { color: LIME }, line: { color: HEAD, width: 1.25 } });
    s.addText(i === 1 ? 'gate: findings' : 'gate: Level 4', { x: gx - 0.9, y: Y - 0.36, w: 1.8, h: 0.3,
      fontSize: 13, bold: true, color: TITLE, align: 'center', valign: 'middle', margin: 0 });
  } else {
    s.addShape(S.CHEVRON, { x: gx - 0.1, y: Y + SH / 2 - 0.25, w: 0.2, h: 0.5, fill: { color: TITLE }, line: { color: TITLE }, objectName: `!!vs-chev-${i}` });
  }
});

// The quality station under the two diagram steps
const QX = sx(1), QW = sx(2) + W - sx(1), QY = Y + SH + 0.35, QH = 1.42;
[sx(1) + W / 2, sx(2) + W / 2].forEach(cx => s.addShape(S.LINE, { x: cx, y: Y + SH, w: 0, h: QY - Y - SH,
  line: { color: TITLE, width: 2, endArrowType: 'triangle' } }));
s.addShape(S.RECTANGLE, { x: QX, y: QY, w: QW, h: QH, fill: { color: ROW }, line: { color: LIME, width: 2 } });
s.addShape(S.RECTANGLE, { x: QX, y: QY, w: 0.1, h: QH, fill: { color: LIME }, line: { color: LIME } });
s.addText('QUALITY STATION · every diagram', { x: QX + 0.25, y: QY + 0.06, w: QW - 0.4, h: 0.3, fontSize: 13,
  bold: true, color: TITLE, charSpacing: 2, margin: 0 });
s.addText([
  { text: '1  Syntax: ', options: { bold: true } }, { text: 'does it render? (PlantUML)', options: { breakLine: true } },
  { text: '2  Semantics: ', options: { bold: true } }, { text: 'does it make sense? (six dimensions)', options: { breakLine: true } },
  { text: '3  Gate: ', options: { bold: true } }, { text: 'below the bar? Back to the author' },
], { x: QX + 0.25, y: QY + 0.38, w: QW - 0.4, h: QH - 0.45, fontSize: 14, color: INK, valign: 'top', margin: 0, paraSpaceAfter: 2 });
s.addText('found early, by the author, while the fix is still small', { x: sx(3), y: QY, w: sx(4) + W - sx(3), h: QH,
  fontSize: 16, bold: true, italic: true, color: TITLE, valign: 'middle', margin: [0, 0, 0, 0.1] });

// Where it runs · how to start · evidence
const BY = QY + QH + 0.18, BH = 1.06, BWS = [3.3, 3.55, 5.1];
const boxes = [
  ['WHERE IT RUNS', [
    { text: 'editor (LSP) · command line · CI gate · SonarQube dashboard' }]],
  ['WHO CHECKS', [
    { text: 'Every author, ', options: { bold: true } },
    { text: 'in the editor while writing; ', options: {} },
    { text: 'every change, ', options: { bold: true } },
    { text: 'in CI, whoever made it' }]],
  ['EVIDENCE', [
    { text: 'Measured: ', options: { bold: true } },
    { text: `AI code from Level 1 sequence diagrams fails ~1 in 3 intended behaviours, ~1 in 10 from Level 2 up (slide ${slideNo(11)}).`, options: { breakLine: true } },
    { text: 'Expected: ', options: { bold: true } },
    { text: 'less rework, shorter lead time.' }]],
];
boxes.forEach(([h, runs], i) => {
  const x = X0 + BWS.slice(0, i).reduce((a, b) => a + b + 0.2, 0), BW = BWS[i];
  s.addShape(S.RECTANGLE, { x, y: BY, w: BW, h: BH, fill: { color: WHITE }, line: { color: ROW_LINE, width: 1 } });
  s.addText(h, { x: x + 0.15, y: BY + 0.06, w: BW - 0.3, h: 0.3, fontSize: 13, bold: true, color: TITLE, charSpacing: 2, margin: 0 });
  s.addText(runs, { x: x + 0.15, y: BY + 0.36, w: BW - 0.3, h: BH - 0.4, fontSize: 13, color: INK, valign: 'top', margin: 0 });
});


pres.writeFile({ fileName: 'after.pptx' }).then(f => console.log('wrote', f));
