const path = require('path');
const pptxgen = require('pptxgenjs');
const { C, header, label } = require('./style.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, '③ In practice · the same set, live, on this laptop', 'Live demo: localhost:8000');

// Left: how to start it (sandbox/credit-application/README.md)
const LX = 0.5, LW = 5.9;
label(s, 'START IT', LX, 1.7, LW);
s.addShape(S.RECTANGLE, { x: LX, y: 2.05, w: LW, h: 1.7, fill: { color: C.HEAD }, line: { color: C.HEAD } });
s.addText([
  { text: '$ cd sandbox/credit-application', options: { breakLine: true } },
  { text: '$ docker compose up', options: { breakLine: true } },
  { text: '  → open http://localhost:8000', options: { color: C.LIME } },
], { x: LX + 0.25, y: 2.05, w: LW - 0.4, h: 1.7, fontSize: 17, fontFace: 'Consolas', color: C.WHITE, valign: 'middle', margin: 0 });
s.addText([
  { text: 'Two containers on this computer: ', options: { bold: true } },
  { text: 'a PlantUML server that draws the diagrams, and a page that shows pumllint’s findings next to each one. ' },
  { text: 'The first start downloads them; after that it runs offline.' },
], { x: LX, y: 3.9, w: LW, h: 1.05, fontSize: 14, color: C.INK, valign: 'top', margin: 0 });
const QS = 1.35;
s.addShape(S.RECTANGLE, { x: LX, y: 5.05, w: QS, h: QS, fill: { color: C.WHITE }, line: { color: C.ROW_LINE, width: 1 } });
const SANDBOX = 'https://github.com/fdurieux/pumllint/tree/main/sandbox/credit-application';
s.addImage({ path: path.join(__dirname, '..', 'assets', 'qr-sandbox.png'), x: LX + 0.04, y: 5.09, w: QS - 0.08, h: QS - 0.08, hyperlink: { url: SANDBOX } });
s.addText([{ text: 'Run it yourself', options: { bold: true, breakLine: true } },
  { text: 'sandbox/credit-application in the pumllint repository: the diagrams, the README, and a 15-minute walkthrough. Without Docker, pip install pumllint gives the same findings, without the pictures.', options: { color: C.MUTED, fontSize: 13 } }],
  { x: LX + QS + 0.2, y: 5.05, w: LW - QS - 0.2, h: QS, fontSize: 14, color: C.INK, valign: 'middle', margin: 0 });

// Right: the five steps of WALKTHROUGH.md
const RX = 6.75, RW = 6.1;
label(s, 'FIFTEEN MINUTES, FIVE STEPS', RX, 1.7, RW);
const steps = [
  ['Every diagram renders', 'Which of these eight would you sign off?'],
  ['The compliant set', 'Gate passes, Level 4, every requirement drawn.'],
  ['The non-compliant set', 'Read the finding, then point at the picture.'],
  ['Fix one, live', 'Name the branches, add “stop”, save, reload: the findings disappear.'],
  ['Levels, gates, requirements', 'Why Level 4 still fails, and the requirement drawn nowhere.'],
];
steps.forEach(([t, d], i) => {
  const y = 2.05 + i * 0.86, dd = 0.46;
  s.addShape(S.RECTANGLE, { x: RX, y, w: RW, h: 0.76, fill: { color: i % 2 ? C.ROW2 : C.ROW }, line: { color: C.BG } });
  s.addShape(S.OVAL, { x: RX + 0.14, y: y + 0.15, w: dd, h: dd, fill: { color: C.LIME }, line: { color: C.LIME } });
  s.addText(String(i + 1), { x: RX + 0.14, y: y + 0.15, w: dd, h: dd, fontSize: 17, bold: true, color: C.HEAD, align: 'center', valign: 'middle', margin: 0 });
  s.addText([{ text: t, options: { bold: true, breakLine: true } }, { text: d, options: { color: C.MUTED, fontSize: 13 } }],
    { x: RX + 0.8, y, w: RW - 0.95, h: 0.76, fontSize: 15, color: C.INK, valign: 'middle', margin: 0 });
});

pres.writeFile({ fileName: 'live-demo.pptx' }).then(f => console.log('wrote', f));
