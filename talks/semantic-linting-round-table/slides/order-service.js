const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
// Same palette as the other slides
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD',
      INK = '1E2B22', LIME = '9BD12E', LIME_HI = 'D9F2A6', WHITE = 'FFFFFF', LIFE = '8A968C';
const MONO = 'Consolas';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

s.addText('① The problem · each file is valid, together they contradict',
  { x: 0.55, y: 0.35, w: 12, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Both render. Which one is right?',
  { x: 0.55, y: 0.75, w: 12, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

const diagrams = [
  { file: 'checkout.puml', name: 'checkout', st: 'service', m1: 'placeOrder()', m2: 'charge()' },
  { file: 'refund.puml', name: 'refund', st: 'gateway', m1: 'requestRefund()', m2: 'refund()' },
];
const PX = [0.45, 6.88], PW = 6.0, PY = 1.7, PH = 4.05, HB = 0.5;
const line = (x, y, w, h, opts) => s.addShape(S.LINE, { x, y, w, h, line: opts });

diagrams.forEach((d, i) => {
  const x = PX[i];
  // Panel + header band
  s.addShape(S.RECTANGLE, { x, y: PY, w: PW, h: PH, fill: { color: ROW }, line: { color: ROW_LINE, width: 0.75 } });
  s.addShape(S.RECTANGLE, { x, y: PY, w: PW, h: HB, fill: { color: HEAD }, line: { color: HEAD } });
  s.addText(d.file, { x: x + 0.2, y: PY, w: 3.5, h: HB, fontSize: 18, bold: true, color: WHITE,
    fontFace: MONO, valign: 'middle', margin: 0 });
  s.addShape(S.ROUNDED_RECTANGLE, { x: x + PW - 1.6, y: PY + 0.08, w: 1.4, h: 0.34, rectRadius: 0.17,
    fill: { color: LIME }, line: { color: LIME } });
  s.addText('✓ renders', { x: x + PW - 1.6, y: PY + 0.08, w: 1.4, h: 0.34, fontSize: 14, bold: true,
    color: HEAD, align: 'center', valign: 'middle', margin: 0 });

  // PlantUML source
  const cy = PY + HB + 0.12, ch = 1.72;
  s.addShape(S.RECTANGLE, { x: x + 0.2, y: cy, w: PW - 0.4, h: ch, fill: { color: WHITE }, line: { color: ROW_LINE } });
  const L = (t, o = {}) => ({ text: t, options: { breakLine: true, ...o } });
  s.addText([
    L(`@startuml ${d.name}`, { color: '6B756D' }),
    L('actor Customer'),
    { text: 'participant OrderService ', options: {} },
    L(`<<${d.st}>>`, { bold: true, highlight: LIME_HI }),
    L('participant Payments'),
    L(`Customer -> OrderService : ${d.m1}`),
    L(`OrderService -> Payments : ${d.m2}`),
    { text: '@enduml', options: { color: '6B756D' } },
  ], { x: x + 0.32, y: cy, w: PW - 0.6, h: ch, fontFace: MONO, fontSize: 13, color: INK,
    valign: "middle", margin: 0, paraSpaceAfter: 0 });

  // Rendered sequence diagram, native shapes
  const ry = cy + ch + 0.12, rh = PY + PH - 0.15 - ry, rx = x + 0.2, rw = PW - 0.4;
  s.addShape(S.RECTANGLE, { x: rx, y: ry, w: rw, h: rh, fill: { color: WHITE }, line: { color: ROW_LINE } });
  const cols = [rx + 0.9, rx + rw / 2, rx + rw - 0.9];
  const top = ry + 0.1, bw = 1.6, bh = 0.52, lifeTop = top + bh, lifeBot = ry + rh - 0.08;
  // Actor: stick figure + name
  const ax = cols[0];
  s.addShape(S.OVAL, { x: ax - 0.07, y: top, w: 0.14, h: 0.14, fill: { color: WHITE }, line: { color: INK, width: 1.25 } });
  line(ax, top + 0.14, 0, 0.16, { color: INK, width: 1.25 });
  line(ax - 0.12, top + 0.19, 0.24, 0, { color: INK, width: 1.25 });
  s.addShape(S.LINE, { x: ax - 0.1, y: top + 0.3, w: 0.1, h: 0.1, flipH: true, line: { color: INK, width: 1.25 } });
  s.addShape(S.LINE, { x: ax, y: top + 0.3, w: 0.1, h: 0.1, line: { color: INK, width: 1.25 } });
  s.addText('Customer', { x: ax - 0.8, y: top + 0.38, w: 1.6, h: 0.18, fontSize: 12, color: INK,
    align: 'center', valign: 'middle', margin: 0 });
  // Participants
  [[`«${d.st}»`, 'OrderService', true], [null, 'Payments', false]].forEach(([st, nm, hi], k) => {
    const c = cols[k + 1];
    s.addShape(S.RECTANGLE, { x: c - bw / 2, y: top, w: bw, h: bh, fill: { color: 'EEF2EC' }, line: { color: INK, width: 1 } });
    s.addText(st ? [
      { text: st, options: { italic: true, bold: true, fontSize: 12, highlight: LIME_HI, breakLine: true } },
      { text: nm, options: { fontSize: 13, bold: true } },
    ] : [{ text: nm, options: { fontSize: 13, bold: true } }],
    { x: c - bw / 2, y: top, w: bw, h: bh, color: INK, align: 'center', valign: 'middle', margin: 0 });
  });
  // Lifelines
  cols.forEach((c, k) => line(c, k === 0 ? top + 0.58 : lifeTop, 0, lifeBot - (k === 0 ? top + 0.58 : lifeTop),
    { color: LIFE, width: 1, dashType: 'dash' }));
  // Messages
  const msg = (from, to, y, label) => {
    line(cols[from], y, cols[to] - cols[from], 0, { color: INK, width: 1.25, endArrowType: 'triangle' });
    s.addText(label, { x: cols[from] + 0.08, y: y - 0.22, w: cols[to] - cols[from] - 0.1, h: 0.2,
      fontSize: 12, color: INK, fontFace: MONO, margin: 0, valign: 'bottom' });
  };
  msg(0, 1, lifeTop + 0.38, d.m1);
  msg(1, 2, lifeTop + 0.72, d.m2);
});

// "≠" between the two panels, level with the stereotype line
const nx = (PX[0] + PW + PX[1]) / 2, nd = 0.56, ny = PY + HB + 0.12 + 0.62;
s.addShape(S.OVAL, { x: nx - nd / 2, y: ny - nd / 2, w: nd, h: nd, fill: { color: LIME }, line: { color: WHITE, width: 2 } });
s.addText('≠', { x: nx - nd / 2, y: ny - nd / 2, w: nd, h: nd, fontSize: 26, bold: true, color: HEAD,
  align: 'center', valign: 'middle', margin: 0 });

// The reveal: what pumllint says when it lints both files together
const sy = PY + PH + 0.15;
s.addShape(S.RECTANGLE, { x: PX[0], y: sy, w: PX[1] + PW - PX[0], h: 0.78, fill: { color: HEAD }, line: { color: HEAD }, objectName: 'reveal-bg' });
s.addText([
  { text: 'pumllint, linting both files together', options: { bold: true, color: LIME, fontSize: 15, breakLine: true } },
  { text: 'XD002 · consistency · ', options: { bold: true, color: WHITE, fontSize: 16 } },
  { text: 'OrderService is «service» in checkout.puml and «gateway» in refund.puml: one entity, one stereotype',
    options: { color: WHITE, fontSize: 16 } },
], { x: PX[0] + 0.2, y: sy, w: PX[1] + PW - PX[0] - 0.4, h: 0.78, valign: 'middle', margin: 0, objectName: 'reveal-text' });


pres.writeFile({ fileName: 'order-service.pptx' }).then(f => console.log('wrote', f));
