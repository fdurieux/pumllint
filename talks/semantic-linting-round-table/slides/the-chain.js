const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
// Same palette as slides 2 and 3; red only for the gap trail
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', RED = 'B03A2E';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

s.addText('① The problem · humans and AI tools build on what the diagram says, gaps and ambiguities included',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Semantic quality: why it matters now',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// The chain: four steps, each built on the one before
const steps = [
  { name: 'Customer journey', by: null, note: 'not linted' },
  { name: 'Business process', by: 'process engineers · analysts' },
  { name: 'Sequence & state charts', by: 'analysts · AI tools' },
  { name: 'Code', by: 'developers · AI tools' },
];
const X0 = 0.5, W = 2.75, G = 0.45, Y = 1.8, HB = 0.55, HBODY = 0.85;
const sx = i => X0 + i * (W + G);
steps.forEach((st, i) => {
  const x = sx(i), off = !st.by;
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: HB + HBODY, fill: { color: off ? GREY_BG : ROW },
    line: { color: off ? GREY : ROW_LINE, width: off ? 1.25 : 0.75, dashType: off ? 'dash' : 'solid' } });
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: HB, fill: { color: off ? GREY : HEAD }, line: { color: off ? GREY : HEAD } });
  s.addText(st.name, { x: x + 0.12, y: Y, w: W - 0.24, h: HB, fontSize: 17, bold: true, color: WHITE,
    valign: 'middle', margin: 0 });
  s.addText(off ? [{ text: st.note, options: { italic: true, color: GREY, fontSize: 15 } }] : [
    { text: 'BUILT BY', options: { fontSize: 11, bold: true, color: TITLE, charSpacing: 2, breakLine: true } },
    { text: st.by, options: { fontSize: 15, bold: true, color: INK } },
  ], { x: x + 0.12, y: Y + HB, w: W - 0.24, h: HBODY, valign: 'middle', margin: 0 });
  if (i < steps.length - 1)
    s.addShape(S.CHEVRON, { x: x + W + 0.12, y: Y + (HB + HBODY) / 2 - 0.27, w: 0.22, h: 0.54,
      fill: { color: TITLE }, line: { color: TITLE } });
});

// The gap trail: one gap upstream grows into a guess at every step below
const ty = Y + HB + HBODY + 0.55;
s.addShape(S.LINE, { x: sx(0) + W / 2, y: ty, w: sx(3) - sx(0), h: 0,
  line: { color: RED, width: 2, dashType: 'dash', endArrowType: 'triangle' } });
const trail = ['a gap', 'a guess', 'a guess on a guess', 'a built-in assumption'];
trail.forEach((t, i) => {
  const d = 0.34 + i * 0.08, cx = sx(i) + W / 2;
  s.addShape(S.OVAL, { x: cx - d / 2, y: ty - d / 2, w: d, h: d, fill: { color: i ? RED : WHITE },
    line: { color: RED, width: 2 } });
  s.addText('?', { x: cx - d / 2, y: ty - d / 2, w: d, h: d, fontSize: 14 + i * 2, bold: true,
    color: i ? WHITE : RED, align: 'center', valign: 'middle', margin: 0 });
  s.addText(t, { x: cx - W / 2, y: ty + 0.33, w: W, h: 0.32, fontSize: 15, italic: true, bold: i === 3,
    color: RED, align: 'center', valign: 'middle', margin: 0 });
});

// Why it matters now: the three statements of the original slide
const cards = [
  ['Hallucinations are not exclusive to AI',
   'Every reader fills the gaps: an analyst, process engineer, developer or AI tool turns what is unclear into a guess.'],
  ['Diagrams form a chain',
   'Each level is the foundation for the next, gaps included. One gap upstream becomes a guess at every step below.'],
  ['AI raises the stakes',
   'AI tools read and write diagrams at scale: more volume, the same gaps, and they never ask.'],
];
const CY = 4.65, CW = 4.0, CG = 0.175, CH = 1.75, CHB = 0.5;
cards.forEach(([h, b], i) => {
  const x = X0 + i * (CW + CG);
  s.addShape(S.RECTANGLE, { x, y: CY, w: CW, h: CH, fill: { color: ROW }, line: { color: ROW_LINE, width: 0.75 } });
  s.addShape(S.RECTANGLE, { x, y: CY, w: CW, h: CHB, fill: { color: HEAD }, line: { color: HEAD } });
  s.addShape(S.RECTANGLE, { x, y: CY, w: 0.09, h: CHB, fill: { color: LIME }, line: { color: LIME } });
  s.addText(h, { x: x + 0.22, y: CY, w: CW - 0.3, h: CHB, fontSize: 17, bold: true, color: WHITE,
    valign: 'middle', margin: 0 });
  s.addText(b, { x: x + 0.22, y: CY + CHB + 0.08, w: CW - 0.44, h: CH - CHB - 0.16, fontSize: 16,
    color: INK, valign: 'top', margin: 0 });
});


pres.writeFile({ fileName: 'the-chain.pptx' }).then(f => console.log('wrote', f));
