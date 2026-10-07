const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', MUTED = '4A5A4E';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

s.addText('② The contribution · a semantic static analyser for PlantUML models',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('From linter to static model analysis',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

const chev = (x, y, c = TITLE) => s.addShape(S.CHEVRON, { x, y: y - 0.22, w: 0.18, h: 0.44, fill: { color: c }, line: { color: c } });

// Lane A: a conventional linter reads text
const AY = 1.8, AH = 0.6;
s.addText('A CONVENTIONAL LINTER', { x: 0.5, y: AY, w: 2.6, h: AH, fontSize: 13, bold: true, color: GREY,
  charSpacing: 2, valign: 'middle', margin: 0 });
['Text', 'Pattern rule', 'Warning'].forEach((t, i) => {
  const x = 3.1 + i * 2.0;
  s.addShape(S.RECTANGLE, { x, y: AY, w: 1.6, h: AH, fill: { color: GREY_BG }, line: { color: GREY, width: 1 } });
  s.addText(t, { x, y: AY, w: 1.6, h: AH, fontSize: 15, bold: true, color: '4A4A4A', align: 'center', valign: 'middle', margin: 0 });
  if (i < 2) chev(x + 1.71, AY + AH / 2, GREY);
});
s.addText('e.g. "line too long", "unused variable": it reads the text, not what it means',
  { x: 9.2, y: AY, w: 3.65, h: AH, fontSize: 14, italic: true, color: GREY, valign: 'middle', margin: 0 });

// Lane B: pumllint reasons over a model
const BY = 2.65;
s.addText('PUMLLINT', { x: 0.5, y: BY, w: 3, h: 0.35, fontSize: 13, bold: true, color: TITLE, charSpacing: 2, margin: 0 });
const X0 = 0.5, W = 1.85, G = 0.25, TOP = BY + 0.45, HALF = 0.95, FULL = 2 * HALF + 0.15;
const cx = i => X0 + i * (W + G);
const box = (i, y, h, title, sub, beyond) => {
  const x = cx(i);
  s.addShape(S.RECTANGLE, { x, y, w: W, h, fill: { color: ROW }, line: { color: beyond ? LIME : ROW_LINE, width: beyond ? 2 : 0.75 } });
  if (beyond) s.addShape(S.RECTANGLE, { x, y, w: 0.09, h, fill: { color: LIME }, line: { color: LIME } });
  s.addText([
    { text: title, options: { bold: true, fontSize: 15, color: INK, breakLine: true } },
    { text: sub, options: { fontSize: 13, color: MUTED } },
  ], { x: x + 0.15, y, w: W - 0.25, h, valign: 'middle', margin: 0 });
};
const mid = TOP + FULL / 2, low = TOP + HALF + 0.15, one = TOP + (FULL - 1.15) / 2;
box(0, one, 1.15, 'PlantUML source', 'one diagram or a whole set');
box(1, one, 1.15, 'Semantic model', 'participants, messages, flows, states');
box(2, TOP, HALF, 'One diagram', 'its own logic');
box(2, low, HALF, 'Across the set', 'one entity, one identity', true);
box(3, one, 1.15, 'Rules', 'six dimensions → findings with a severity');
box(4, TOP, HALF, 'Lint result', 'pass or fail, on severity');
box(4, low, HALF, 'Maturity level', '1–5, per diagram and set', true);
box(5, one, 1.15, 'Quality gate', '--min-level: may it move on?', true);
for (let i = 0; i < 5; i++) chev(cx(i) + W + 0.035, mid);

// Detect → measure → govern, under the lane
const LY = TOP + FULL + 0.3;
[['DETECT', 0, 3], ['MEASURE', 4, 4], ['GOVERN', 5, 5]].forEach(([t, a, b]) => {
  const x = cx(a), w = cx(b) + W - cx(a);
  s.addShape(S.LINE, { x, y: LY, w, h: 0, line: { color: TITLE, width: 2.5 } });
  s.addText(t, { x, y: LY + 0.06, w, h: 0.32, fontSize: 14, bold: true, color: TITLE, charSpacing: 3,
    align: 'center', valign: 'middle', margin: 0 });
});

// Legend + the separation the positioning note stresses
const NY = LY + 0.6;
s.addShape(S.RECTANGLE, { x: 0.5, y: NY + 0.08, w: 0.09, h: 0.3, fill: { color: LIME }, line: { color: LIME } });
s.addText([
  { text: 'What a conventional linter does not do.  ', options: { bold: true, color: INK } },
  { text: 'The rules stay the source of truth; the level adds them up, the gate applies your policy.', options: { color: MUTED } },
], { x: 0.72, y: NY, w: 12.1, h: 0.46, fontSize: 15, valign: 'middle', margin: 0 });


pres.writeFile({ fileName: 'linter-to-model-analysis.pptx' }).then(f => console.log('wrote', f));
