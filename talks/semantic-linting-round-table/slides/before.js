const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
// Same palette as the other slides
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', RED = 'B03A2E', RED_BG = 'F3DEDB';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

// Recap variant (global.RECAP_BEFORE): repeated just before the 'after' slide so Morph can play
const RECAP = global.RECAP_BEFORE === true;
s.addText(RECAP ? '③ The value · where we started' : '① The problem · model quality is a subjective review concern',
  { objectName: '!!subtitle', x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Today: reviewed by eye, found late',
  { objectName: '!!title', x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// The value stream, as on the "after" slide but with no quality station
const st = [
  ['Customer journey', 'not linted', true],
  ['Business process', 'activity diagrams'],
  ['Sequence & state', 'charts: solution design'],
  ['Code', 'human & AI'],
  ['Release', 'test · production'],
];
const X0 = 0.5, W = 2.15, G = 0.4, Y = 2.65, HB = 0.45, HBODY = 0.5;
const sx = i => X0 + i * (W + G);
st.forEach(([name, sub, off], i) => {
  const x = sx(i);
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: HB + HBODY, objectName: `!!vs-${i}-box`, fill: { color: off ? GREY_BG : ROW },
    line: { color: off ? GREY : ROW_LINE, width: off ? 1.25 : 0.75, dashType: off ? 'dash' : 'solid' } });
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: HB, objectName: `!!vs-${i}-head`, fill: { color: off ? GREY : HEAD }, line: { color: off ? GREY : HEAD } });
  s.addText(name, { objectName: `!!vs-${i}-name`, x: x + 0.1, y: Y, w: W - 0.2, h: HB, fontSize: 16, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(sub, { objectName: `!!vs-${i}-sub`, x: x + 0.1, y: Y + HB, w: W - 0.2, h: HBODY, fontSize: 14, italic: !!off,
    color: off ? GREY : INK, valign: 'middle', margin: 0 });
  if (i < st.length - 1)
    s.addShape(S.CHEVRON, { x: x + W + 0.1, y: Y + (HB + HBODY) / 2 - 0.25, w: 0.2, h: 0.5,
      fill: { color: TITLE }, line: { color: TITLE }, ...(i === 0 || i === 3 ? { objectName: `!!vs-chev-${i}` } : {}) });
});

// Gaps surface late: red markers on Code and Release
[3, 4].forEach(i => {
  const d = 0.42, x = sx(i) + W - d / 2 - 0.05, y = Y - d / 2;
  s.addShape(S.OVAL, { x, y, w: d, h: d, fill: { color: RED }, line: { color: WHITE, width: 1.5 } });
  s.addText('?', { x, y, w: d, h: d, fontSize: 18, bold: true, color: WHITE, align: 'center', valign: 'middle', margin: 0 });
});

// Rework loop: from Code back to the business process
const ly = 2.1, cx3 = sx(3) + W / 2 - 0.3, cx1 = sx(1) + W / 2;
const red = { color: RED, width: 2.25, dashType: 'dash' };
s.addShape(S.LINE, { x: cx3, y: ly, w: 0, h: Y - ly, line: red });
s.addShape(S.LINE, { x: cx1, y: ly, w: cx3 - cx1, h: 0, line: red });
s.addShape(S.LINE, { x: cx1, y: ly, w: 0, h: Y - ly - 0.02, line: { ...red, endArrowType: 'triangle' } });
s.addText('rework, after the code is written',
  { x: cx1 + 0.9, y: ly - 0.2, w: cx3 - cx1 - 1.8, h: 0.4, fontSize: 15, bold: true, italic: true,
    color: RED, fill: { color: 'F7F8F5' }, align: 'center', valign: 'middle', margin: 0 });

// Hand-offs today: review by eye
const ry = Y + HB + HBODY + 0.3;
s.addShape(S.RECTANGLE, { x: sx(0), y: ry, w: sx(3) + W - sx(0), h: 0.5, fill: { color: GREY_BG },
  line: { color: GREY, width: 1, dashType: 'dash' } });
s.addText([
  { text: 'Every hand-off today: ', options: { bold: true } },
  { text: 'a review by eye, as good as the reviewer\'s time and attention' },
], { x: sx(0) + 0.15, y: ry, w: sx(3) + W - sx(0) - 0.3, h: 0.5, fontSize: 15, color: '4A4A4A', valign: 'middle', margin: 0 });
s.addText('gaps surface here, late', { x: sx(4), y: ry, w: W, h: 0.5, fontSize: 15, bold: true, italic: true,
  color: RED, align: 'center', valign: 'middle', margin: 0 });

// The cost of a late gap grows with every step built on it
const ay = ry + 0.85;
s.addShape(S.RIGHT_ARROW, { x: sx(0), y: ay, w: sx(4) + W - sx(0), h: 0.6, fill: { color: RED_BG },
  line: { color: RED, width: 1 } });
s.addText('The later a gap is found, the more steps were built on it, and the further back the rework goes',
  { x: sx(0) + 0.2, y: ay, w: sx(4) + W - sx(0) - 0.8, h: 0.6, fontSize: 15, color: RED, bold: true,
    valign: 'middle', margin: 0 });

// Round-table question, in the deck's lime question-box style
const qy = ay + 0.95;
if (!RECAP) {
s.addShape(S.RECTANGLE, { x: sx(0), y: qy, w: sx(4) + W - sx(0), h: 0.85, fill: { color: LIME }, line: { color: LIME } });
s.addText([
  { text: 'Question: ', options: { bold: true } },
  { text: 'How do you find a diagram\'s gaps today, and at which step?' },
], { x: sx(0) + 0.25, y: qy, w: sx(4) + W - sx(0) - 0.5, h: 0.85, fontSize: 22, color: HEAD, valign: 'middle', margin: 0 });
}


pres.writeFile({ fileName: 'before.pptx' }).then(f => console.log('wrote', f));
