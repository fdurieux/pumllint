const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', INK = '1E2B22', LIME = '9BD12E',
      WHITE = 'FFFFFF', MUTED = '4A5A4E', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('③ The value · from advice to gate, step by step, without a big-bang cleanup',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('Diagram quality, built into the workflow',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// Two "When | How" tables, as on the original slide
const H = t => ({ text: t, options: { bold: true, color: WHITE, fill: { color: HEAD } } });
const table = (x, w, colW, caption, rows) => {
  s.addText(caption, { x, y: 1.68, w, h: 0.3, fontSize: 15, italic: true, color: MUTED, margin: 0 });
  s.addTable([[H('When'), H('How')], ...rows.map((r, i) => {
    const fill = { color: i % 2 ? ROW2 : ROW };
    return [{ text: r[0], options: { bold: true, fill } }, { text: r[1], options: { fill } }];
  })], { x, y: 2.02, w, colW, rowH: 0.36, fontSize: 13, color: INK, valign: 'middle', margin: 0.07,
    border: { type: 'solid', pt: 1, color: BG } });
};
table(0.5, 5.9, [1.45, 4.45], 'On your own machine (with or without Git)', [
  ['While writing', 'In any editor that supports LSP: one language server, no editor-specific plugins'],
  ['On demand', 'From the command line: check a whole folder at once, with each diagram\'s findings and maturity level, plus an HTML maturity report'],
]);
table(6.6, 6.25, [1.65, 4.6], 'In the delivery pipeline (diagrams stored in Git)', [
  ['On every change', 'A CI gate checks every changed diagram, whoever authored it; the severity of its findings decides whether the build passes'],
  ['From existing tools', 'Business processes modelled in ARIS are converted to PlantUML and pass the same gate'],
  ['Over time', 'Dashboards (SonarQube), a maturity report, and a badge per repository showing its weakest diagram\'s level'],
]);

// Roll-out: three steps, no big-bang cleanup
const RY = 4.5, RH = 0.8, RW = 4.3, RX = [0.5, 4.5, 8.5];
const steps = [
  ['Step 1 · ADVISE', 'report only; nothing fails'],
  ['Step 2 · RATCHET', 'record today\'s levels; fail only when a diagram gets worse'],
  ['Step 3 · FLOOR', 'require a minimum level, e.g. Level 2 everywhere, Level 4 before hand-off'],
];
steps.forEach(([t, d], i) => {
  const fill = [ROW, ROW2, TITLE][i], col = i === 2 ? WHITE : INK;
  s.addShape(i ? S.CHEVRON : S.PENTAGON, { x: RX[i], y: RY, w: i === 2 ? 4.35 : RW, h: RH, fill: { color: fill }, line: { color: BG, width: 1.5 } });
  s.addText([{ text: t, options: { bold: true, charSpacing: 1, breakLine: true } }, { text: d }],
    { x: RX[i] + (i ? 0.45 : 0.18), y: RY, w: RW - (i ? 0.85 : 0.6), h: RH, fontSize: 13, color: col, valign: 'middle', margin: 0 });
});

// Closing questions: the PoC decision
const QY = 5.5;
s.addShape(S.RECTANGLE, { x: 0.5, y: QY, w: 12.35, h: 1.0, fill: { color: LIME }, line: { color: LIME } });
s.addText([
  { text: 'Questions', options: { bold: true, breakLine: true } },
  { text: '1. What would a PoC need to show to convince you?', options: { breakLine: true } },
  { text: '2. Where should the gate sit, and which level for which diagrams?' },
], { x: 0.75, y: QY, w: 11.85, h: 1.0, fontSize: 18, color: HEAD, valign: 'middle', margin: 0 });


pres.writeFile({ fileName: 'workflow.pptx' }).then(f => console.log('wrote', f));
