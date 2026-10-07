const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
// Palette sampled from the deck photos
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD',
      INK = '1E2B22', LIME = '9BD12E', WHITE = 'FFFFFF';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

// Subtitle (small, above) + title — preview only; the deck's own placeholders take these
s.addText('Is semantic linting of diagrams worth a PoC?',
  { x: 0.55, y: 0.35, w: 12, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Three questions for this round table',
  { x: 0.55, y: 0.75, w: 12, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

const cards = [
  { n: '1', verb: 'AGREE', label: 'The problem', q: 'Do we recognise it?',
    chips: ['semantic correctness', 'common pain points', 'analysts & process engineers', 'developers & AI tools'],
    out: 'a shared problem' },
  { n: '2', verb: 'UNDERSTAND', label: 'The contribution', q: 'What does a semantic linter add?',
    chips: ['linting rules', 'conventions', 'quality checks', 'engineering workflows'],
    out: 'a shared understanding' },
  { n: '3', verb: 'DECIDE', label: 'The value', q: 'Is it worth trying?',
    chips: ['documentation quality', 'collaboration', 'automation', 'delivery lifecycle'],
    out: 'a go / no-go for a PoC' },
];
const X0 = 0.45, W = 3.2, GAP = 0.45, Y = 2.2, HH = 0.75, H = 4.35;
const cx = i => X0 + i * (W + GAP);

cards.forEach((c, i) => {
  const x = cx(i);
  // Verb kicker above the card
  s.addText(c.verb, { x, y: Y - 0.45, w: W, h: 0.35, fontSize: 14, bold: true,
    color: TITLE, charSpacing: 3, margin: 0 });
  // Card body
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: H, fill: { color: ROW },
    line: { color: ROW_LINE, width: 0.75 } });
  // Header band with numbered lime disc
  s.addShape(S.RECTANGLE, { x, y: Y, w: W, h: HH, fill: { color: HEAD }, line: { color: HEAD } });
  s.addShape(S.OVAL, { x: x + 0.15, y: Y + 0.14, w: 0.47, h: 0.47, fill: { color: LIME },
    line: { color: LIME } });
  s.addText(c.n, { x: x + 0.15, y: Y + 0.14, w: 0.47, h: 0.47, fontSize: 20, bold: true,
    color: HEAD, align: 'center', valign: 'middle', margin: 0 });
  s.addText(c.label, { x: x + 0.75, y: Y, w: W - 0.85, h: HH, fontSize: 20, bold: true,
    color: WHITE, valign: 'middle', margin: 0 });
  // Question
  s.addText(c.q, { x: x + 0.2, y: Y + HH + 0.1, w: W - 0.4, h: 0.85, fontSize: 20, bold: true,
    color: INK, valign: 'middle', margin: 0 });
  // Keyword chips (from the programme description)
  c.chips.forEach((k, j) => {
    const y = Y + HH + 1.05 + j * 0.47;
    s.addShape(S.ROUNDED_RECTANGLE, { x: x + 0.2, y, w: W - 0.4, h: 0.4, rectRadius: 0.2,
      fill: { color: WHITE }, line: { color: ROW_LINE, width: 1 } });
    s.addText(k, { x: x + 0.2, y, w: W - 0.4, h: 0.4, fontSize: 14, color: INK,
      align: 'center', valign: 'middle', margin: 0 });
  });
  // Outcome strip
  s.addShape(S.RECTANGLE, { x, y: Y + H - 0.55, w: W, h: 0.55, fill: { color: TITLE },
    line: { color: TITLE } });
  s.addText([{ text: '→ ', options: { bold: true } }, { text: c.out, options: { italic: true } }],
    { x: x + 0.2, y: Y + H - 0.55, w: W - 0.4, h: 0.55, fontSize: 16, color: WHITE,
      valign: 'middle', margin: 0 });
  // Chevron to the next card / to the PoC bubble
  s.addShape(S.CHEVRON, { x: x + W + 0.1, y: Y + H / 2 - 0.3, w: 0.25, h: 0.6,
    fill: { color: TITLE }, line: { color: TITLE } });
});

// PoC decision bubble, lime as the deck's question box
const bx = cx(3), bw = 1.55;
s.addShape(S.OVAL, { x: bx, y: Y + H / 2 - bw / 2, w: bw, h: bw, fill: { color: LIME },
  line: { color: LIME } });
s.addText([
  { text: 'PoC?', options: { fontSize: 28, bold: true, breakLine: true } },
  { text: 'go / no-go', options: { fontSize: 14 } },
], { x: bx, y: Y + H / 2 - bw / 2, w: bw, h: bw, color: HEAD, align: 'center',
  valign: 'middle', margin: 0 });

pres.writeFile({ fileName: 'three-questions.pptx' }).then(f => console.log('wrote', f));
