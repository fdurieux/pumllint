const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22', LIME = '9BD12E',
      LIME_HI = 'D9F2A6', WHITE = 'FFFFFF', LIFE = '8A968C', RED = 'B03A2E', LANE = 'F1F4EF', BG = 'F7F8F5';
const MONO = 'Consolas';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('① The problem · a credit flow: one gap, passed on to the next diagram',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Both render. Which branch approves?',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

const line = (x, y, w, h, o) => s.addShape(S.LINE, { x, y, w, h, flipV: h < 0, ...(h < 0 ? { y: y + h, h: -h } : {}), line: o });
const arrow = { color: INK, width: 1.25, endArrowType: 'triangle' };
const plain = { color: INK, width: 1.25 };
const box = (x, y, w, h, t, o = {}) => {
  s.addShape(S.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: o.fill || 'EEF2EC' }, line: { color: INK, width: 1 } });
  s.addText(t, { x, y, w, h, fontSize: o.fs || 11, color: INK, align: 'center', valign: 'middle', margin: 0.02 });
};
const qmark = (cx, cy, d = 0.26) => {
  s.addShape(S.OVAL, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: RED }, line: { color: WHITE, width: 1 } });
  s.addText('?', { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fontSize: 12, bold: true, color: WHITE, align: 'center', valign: 'middle', margin: 0 });
};
const panel = (x, w, file, note) => {
  s.addShape(S.RECTANGLE, { x, y: 1.7, w, h: 3.9, fill: { color: ROW }, line: { color: ROW_LINE, width: 0.75 } });
  s.addShape(S.RECTANGLE, { x, y: 1.7, w, h: 0.45, fill: { color: HEAD }, line: { color: HEAD } });
  s.addText([{ text: file, options: { fontFace: MONO, bold: true } }, ...(note ? [{ text: '  ' + note, options: { italic: true, color: 'C9D4C3', fontSize: 12 } }] : [])],
    { x: x + 0.15, y: 1.7, w: w - 1.5, h: 0.45, fontSize: w > 5 ? 15 : 13, color: WHITE, valign: 'middle', margin: 0 });
  s.addShape(S.ROUNDED_RECTANGLE, { x: x + w - 1.3, y: 1.77, w: 1.15, h: 0.31, rectRadius: 0.15, fill: { color: LIME }, line: { color: LIME } });
  s.addText('✓ renders', { x: x + w - 1.3, y: 1.77, w: 1.15, h: 0.31, fontSize: 12, bold: true, color: HEAD, align: 'center', valign: 'middle', margin: 0 });
};

// ---- Left: the business process (activity diagram with three swimlanes)
const PX = 0.45, PW = 8.4;
panel(PX, PW, 'credit-application.puml', 'business process');
const RX = PX + 0.15, RW = PW - 0.3, LY = 2.3, LH = 0.8, LW = 0.95;
s.addShape(S.RECTANGLE, { x: RX, y: LY, w: RW, h: 3 * LH, fill: { color: WHITE }, line: { color: ROW_LINE } });
['Customer', 'Credit officer', 'Risk engine'].forEach((t, i) => {
  const y = LY + i * LH;
  s.addShape(S.RECTANGLE, { x: RX, y, w: LW, h: LH, fill: { color: LANE }, line: { color: ROW_LINE, width: 0.75 } });
  s.addText(t, { x: RX + 0.05, y, w: LW - 0.1, h: LH, fontSize: 11, bold: true, color: TITLE, valign: 'middle', margin: 0 });
  if (i) line(RX, y, RW, 0, { color: ROW_LINE, width: 0.75 });
});
const cy = i => LY + i * LH + LH / 2;        // lane centre
// start → submit (customer)
s.addShape(S.OVAL, { x: 1.68, y: cy(0) - 0.08, w: 0.16, h: 0.16, fill: { color: INK }, line: { color: INK } });
line(1.84, cy(0), 0.2, 0, arrow);
box(2.05, cy(0) - 0.24, 1.2, 0.48, 'Submit credit application');
// ↓ check completeness (officer)
line(2.65, cy(0) + 0.24, 0, cy(1) - 0.24 - cy(0) - 0.24, arrow);
box(2.05, cy(1) - 0.24, 1.2, 0.48, 'Check completeness');
// ◇ Complete?
const d1x = 3.55, dd = 0.42;
line(3.25, cy(1), d1x - 3.25, 0, arrow);
s.addShape(S.DIAMOND, { x: d1x, y: cy(1) - dd / 2, w: dd, h: dd, fill: { color: 'EEF2EC' }, line: { color: INK, width: 1 } });
s.addText('Complete?', { x: d1x - 0.35, y: cy(1) - 0.39, w: 1.1, h: 0.18, fontSize: 10, color: INK, align: 'center', margin: 0 });
// no → request missing documents (officer)
line(d1x + dd, cy(1), 5.75 - d1x - dd, 0, arrow);
s.addText('no', { x: d1x + dd + 0.05, y: cy(1) - 0.2, w: 0.4, h: 0.18, fontSize: 10, color: TITLE, bold: true, margin: 0 });
box(5.75, cy(1) - 0.24, 1.25, 0.48, 'Request missing documents');
// yes ↓ score applicant (risk engine)
line(d1x + dd / 2, cy(1) + dd / 2, 0, cy(2) - 0.24 - cy(1) - dd / 2, arrow);
s.addText('yes', { x: d1x + dd / 2 + 0.05, y: cy(1) + 0.24, w: 0.4, h: 0.18, fontSize: 10, color: TITLE, bold: true, margin: 0 });
box(3.2, cy(2) - 0.24, 1.15, 0.48, 'Score applicant');
// ◇ Score sufficient? — branches without labels
const d2x = 4.6;
line(4.35, cy(2), d2x - 4.35, 0, arrow);
s.addShape(S.DIAMOND, { x: d2x, y: cy(2) - dd / 2, w: dd, h: dd, fill: { color: LIME_HI }, line: { color: RED, width: 1.75 } });
s.addText('Score sufficient?', { x: d2x - 0.45, y: cy(2) - 0.4, w: 1.3, h: 0.18, fontSize: 10, bold: true, color: RED, align: 'center', margin: 0 });
const bx = 5.55, bw = 1.3, bh = 0.3;
const tipX = d2x + dd, ya = cy(2) - 0.2, yr = cy(2) + 0.2;
line(tipX, cy(2), bx - tipX, ya - cy(2), arrow);
line(tipX, cy(2), bx - tipX, yr - cy(2), arrow);
qmark(tipX + 0.38, (cy(2) + ya) / 2 - 0.02, 0.22);
qmark(tipX + 0.38, (cy(2) + yr) / 2 + 0.02, 0.22);
box(bx, ya - bh / 2, bw, bh, 'Approve credit', { fs: 10 });
box(bx, yr - bh / 2, bw, bh, 'Reject application', { fs: 10 });
// all three → inform customer (officer)
const ix = 7.2, iw = 1.12;
line(7.0, cy(1), ix - 7.0, 0, arrow);
line(bx + bw, ya, 7.55 - bx - bw, 0, plain);
line(bx + bw, yr, 7.55 - bx - bw, 0, plain);
line(7.55, yr, 0, cy(1) + 0.24 - yr, arrow);
box(ix, cy(1) - 0.24, iw, 0.48, 'Inform customer', { fs: 10.5 });
// …and then nothing: no end node
line(ix + iw, cy(1), 0.18, 0, { color: RED, width: 1.5, dashType: 'dash' });
qmark(ix + iw + 0.27, cy(1), 0.24);
s.addText('no end', { x: ix + iw - 0.1, y: cy(1) + 0.16, w: 0.65, h: 0.18, fontSize: 10, bold: true, italic: true, color: RED, align: 'center', margin: 0 });
// key source lines
s.addText([
  { text: 'if (Score sufficient?) then', options: { highlight: LIME_HI, bold: true } }, { text: '  …  ' },
  { text: 'else', options: { highlight: LIME_HI, bold: true } }, { text: '  …  :Inform customer;  @enduml' },
  { text: '   ← no stop', options: { color: RED, bold: true } },
], { x: RX, y: 4.82, w: RW, h: 0.62, fontFace: MONO, fontSize: 11, color: INK, valign: 'middle', margin: 7, fill: { color: WHITE } });

// ---- "derived from" between the panels
const gx = (PX + PW + 9.1) / 2;
s.addShape(S.OVAL, { x: gx - 0.22, y: 4.3 - 0.22, w: 0.44, h: 0.44, fill: { color: LIME }, line: { color: WHITE, width: 2 } });
s.addText('→', { x: gx - 0.22, y: 4.3 - 0.22, w: 0.44, h: 0.44, fontSize: 18, bold: true, color: HEAD, align: 'center', valign: 'middle', margin: 0 });

// ---- Right: the sequence diagram derived from it
const QX = 9.1, QW = 3.75;
panel(QX, QW, 'credit-decision.puml', '');
s.addText('derived from the process', { x: QX + 0.15, y: 2.18, w: QW - 0.3, h: 0.2, fontSize: 10, italic: true, color: TITLE, margin: 0 });
const SX = QX + 0.15, SY = 2.42, SW = QW - 0.3, SH = 2.32;
s.addShape(S.RECTANGLE, { x: SX, y: SY, w: SW, h: SH, fill: { color: WHITE }, line: { color: ROW_LINE } });
const col = [SX + 0.42, SX + 1.6, SX + 2.85], top = SY + 0.08, pb = 0.36, lifeEnd = SY + SH - 0.05;
// actor + participants
s.addShape(S.OVAL, { x: col[0] - 0.06, y: top, w: 0.12, h: 0.12, fill: { color: WHITE }, line: { color: INK, width: 1 } });
s.addShape(S.LINE, { x: col[0], y: top + 0.12, w: 0, h: 0.12, line: plain });
s.addShape(S.LINE, { x: col[0] - 0.09, y: top + 0.16, w: 0.18, h: 0, line: plain });
s.addShape(S.LINE, { x: col[0] - 0.08, y: top + 0.24, w: 0.08, h: 0.08, flipH: true, line: plain });
s.addShape(S.LINE, { x: col[0], y: top + 0.24, w: 0.08, h: 0.08, line: plain });
s.addText('Customer', { x: col[0] - 0.45, y: top + 0.3, w: 0.9, h: 0.14, fontSize: 9, color: INK, align: 'center', margin: 0 });
[['CreditOfficer', 1], ['RiskEngine', 2]].forEach(([t, k]) => {
  s.addShape(S.RECTANGLE, { x: col[k] - 0.55, y: top, w: 1.1, h: pb, fill: { color: 'EEF2EC' }, line: { color: INK, width: 1 } });
  s.addText(t, { x: col[k] - 0.55, y: top, w: 1.1, h: pb, fontSize: 10, bold: true, color: INK, align: 'center', valign: 'middle', margin: 0 });
});
col.forEach((c, k) => s.addShape(S.LINE, { x: c, y: top + (k ? pb : 0.46), w: 0, h: lifeEnd - top - (k ? pb : 0.46), line: { color: LIFE, width: 1, dashType: 'dash' } }));
const msg = (a, b, y, t, dash) => {
  const l = Math.min(col[a], col[b]), w = Math.abs(col[b] - col[a]);
  s.addShape(S.LINE, { x: l, y, w, h: 0, flipH: b < a, line: { color: INK, width: 1, endArrowType: 'triangle', dashType: dash ? 'dash' : 'solid' } });
  s.addText(t, { x: l + 0.05, y: y - 0.17, w: w - 0.05, h: 0.15, fontSize: 9, color: INK, margin: 0 });
};
msg(0, 1, SY + 0.72, 'submitApplication()');
msg(1, 2, SY + 0.98, 'scoreApplicant()');
msg(2, 1, SY + 1.22, 'score', true);
// alt frame with no condition
const fy = SY + 1.36, fh = SH - 1.36 - 0.1, fx = SX + 0.12, fw = SW - 0.24;
s.addShape(S.RECTANGLE, { x: fx, y: fy, w: fw, h: fh, fill: { type: 'none' }, line: { color: RED, width: 1.5 } });
s.addShape(S.RECTANGLE, { x: fx, y: fy, w: 0.38, h: 0.2, fill: { color: LIME_HI }, line: { color: RED, width: 1 } });
s.addText('alt', { x: fx, y: fy, w: 0.38, h: 0.2, fontSize: 10, bold: true, color: INK, align: 'center', valign: 'middle', margin: 0 });
qmark(fx + 0.56, fy + 0.1, 0.2);
msg(1, 0, fy + 0.42, 'approveCredit()');
s.addShape(S.LINE, { x: fx, y: fy + fh / 2 + 0.06, w: fw, h: 0, line: { color: RED, width: 1, dashType: 'dash' } });
msg(1, 0, fy + fh - 0.12, 'rejectApplication()');
s.addText([
  { text: 'alt', options: { highlight: LIME_HI, bold: true } }, { text: '   ← no condition', options: { color: RED, bold: true, fontFace: 'Calibri' } },
], { x: SX, y: 4.82, w: SW, h: 0.62, fontFace: MONO, fontSize: 11, color: INK, valign: 'middle', margin: 7, fill: { color: WHITE } });

// ---- The reveal: what pumllint reports on the pair
const ry = 5.75, rh = 0.82, rw = 12.4;
s.addShape(S.RECTANGLE, { x: PX, y: ry, w: rw, h: rh, fill: { color: HEAD }, line: { color: HEAD }, objectName: 'reveal-bg' });
s.addText('pumllint, linting both files', { x: PX + 0.2, y: ry, w: 1.75, h: rh, fontSize: 14, bold: true, color: LIME, valign: 'middle', margin: 0, objectName: 'reveal-label' });
const cells = [
  ['ACT003 · minor', 'credit-application: the decision\'s branches are not labelled'],
  ['ACT002 · major', 'credit-application: the process never ends; the build fails'],
  ['SEQ007 · minor', 'credit-decision: alt without a condition; the guess, carried down'],
];
cells.forEach(([h, t], i) => {
  const x = PX + 2.05 + i * 3.45;
  s.addText([{ text: h, options: { bold: true, color: i === 1 ? LIME : WHITE, breakLine: true } }, { text: t, options: { color: WHITE } }],
    { x, y: ry, w: 3.3, h: rh, fontSize: 13, valign: 'middle', margin: 0, objectName: `reveal-cell-${i + 1}` });
});

pres.writeFile({ fileName: 'credit-flow.pptx' }).then(f => console.log('wrote', f));
