const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', GREY = '7A7A7A', GREY_BG = 'ECECEA', MUTED = '4A5A4E';
const s = pres.addSlide();
s.background = { color: 'F7F8F5' };

s.addText('① The problem · beyond "does it render?"',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('What we mean by semantic correctness',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// Six dimensions of the 360° rule map (docs/rule-map.md): name, tag, weight, question, examples
const dims = [
  ['Logical correctness', null, '20%', 'Is it logically sound?',
   'A block that never closes; a state machine with no starting point.'],
  ['Completeness', 'gaps', '30%', 'Is everything that should be there actually there?',
   'A process with no end; an error path nobody drew.'],
  ['Ambiguity', 'ambiguities', '25%', 'Could two readers take it two different ways?',
   'Arrows with no label; conditions like "sometimes"; "TBD".'],
  ['Consistency', null, '15%', 'One convention, here and across diagrams?',
   'One thing with two names, kinds or stereotypes.'],
  ['Traceability', null, '5%', 'Can you find it, cite it, and tell who owns it?',
   'No title, no owner, no link to the requirement.'],
  ['Readability', null, '5%', 'Is it small enough to take in?',
   'Too many lifelines or messages on one canvas.'],
];
const X0 = 0.5, CW = 4.0, CG = 0.175, Y0 = 1.75, CH = 1.92, RG = 0.15, HB = 0.5;
dims.forEach(([name, tag, wt, q, ex], i) => {
  const x = X0 + (i % 3) * (CW + CG), y = Y0 + Math.floor(i / 3) * (CH + RG);
  s.addShape(S.RECTANGLE, { x, y, w: CW, h: CH, fill: { color: ROW }, line: { color: ROW_LINE, width: 0.75 } });
  s.addShape(S.RECTANGLE, { x, y, w: CW, h: HB, fill: { color: HEAD }, line: { color: HEAD } });
  s.addText([
    { text: name, options: { bold: true, color: WHITE } },
    ...(tag ? [{ text: '  ·  ' + tag, options: { italic: true, color: LIME } }] : []),
  ], { x: x + 0.18, y, w: CW - 1.1, h: HB, fontSize: 17, valign: 'middle', margin: 0 });
  s.addShape(S.ROUNDED_RECTANGLE, { x: x + CW - 0.85, y: y + 0.1, w: 0.7, h: 0.3, rectRadius: 0.15,
    fill: { color: LIME }, line: { color: LIME } });
  s.addText(wt, { x: x + CW - 0.85, y: y + 0.1, w: 0.7, h: 0.3, fontSize: 13, bold: true, color: HEAD,
    align: 'center', valign: 'middle', margin: 0 });
  s.addText([
    { text: q, options: { bold: true, fontSize: 17, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: ex, options: { italic: true, fontSize: 15, color: MUTED } },
  ], { x: x + 0.18, y: y + HB + 0.1, w: CW - 0.36, h: CH - HB - 0.2, valign: 'top', margin: 0 });
});

// The syntax layer underneath: a solved problem, the gate before any of the above
const sy = Y0 + 2 * CH + RG + 0.15, sw = 3 * CW + 2 * CG;
s.addShape(S.RECTANGLE, { x: X0, y: sy, w: sw, h: 0.55, fill: { color: GREY_BG },
  line: { color: GREY, width: 1, dashType: 'dash' } });
s.addText([
  { text: 'Underneath: syntax  ', options: { bold: true, color: GREY } },
  { text: 'Does it render? Solved: PlantUML and its IDE plugins already check this.', options: { color: GREY } },
], { x: X0 + 0.18, y: sy, w: sw - 0.36, h: 0.55, fontSize: 15, valign: 'middle', margin: 0 });


pres.writeFile({ fileName: 'semantic-correctness.pptx' }).then(f => console.log('wrote', f));
