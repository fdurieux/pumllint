const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', INK = '1E2B22', LIME = '9BD12E',
      WHITE = 'FFFFFF', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('Every diagram renders. Does it make sense?',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('The round-table promise',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });

// The programme text, one paragraph per row, each tagged with the part of the session it opens
const K = t => ({ text: t, options: { bold: true, color: TITLE } });
const P = t => ({ text: t });
const rows = [
  ['1', 'THE PROBLEM', [
    P('PlantUML is being used in the organisation for creating different types of diagrams; the syntactic correctness of these diagrams can be validated using IDE plugins; however, '),
    K('maintaining semantic correctness is important but challenging, and very much uncharted terrain.')]],
  ['2', 'THE CONTRIBUTION', [
    P('This roundtable invites engineers to discuss the value of introducing '), K('linting rules for PlantUML diagrams'),
    P(', helping ensure diagrams are not only syntactically correct, but also adhere to a defined semantic quality.')]],
  ['3', 'THE VALUE', [
    P('Together, we will explore which conventions and quality checks deliver the most value, how diagram standards can be '),
    K('integrated into engineering workflows'), P(', and how well-structured diagrams can benefit both developers and AI-powered tools.')]],
  ['', 'YOUR VIEW', [
    P('Join the discussion to '), K('share your experiences, identify common pain points'),
    P(', and help define practical guidelines that improve collaboration, documentation quality, and automation across the software delivery lifecycle.')]],
];
const X0 = 0.5, TW = 2.3, W = 12.35, Y0 = 1.75, RH = 1.02, GAP = 0.1;
rows.forEach(([n, tag, runs], i) => {
  const y = Y0 + i * (RH + GAP), you = !n;
  s.addShape(S.RECTANGLE, { x: X0, y, w: W, h: RH, fill: { color: i % 2 ? ROW2 : ROW }, line: { color: BG } });
  s.addShape(S.RECTANGLE, { x: X0, y, w: TW, h: RH, fill: { color: you ? LIME : HEAD }, line: { color: you ? LIME : HEAD } });
  if (n) {
    const d = 0.42;
    s.addShape(S.OVAL, { x: X0 + 0.15, y: y + RH / 2 - d / 2, w: d, h: d, fill: { color: LIME }, line: { color: LIME } });
    s.addText(n, { x: X0 + 0.15, y: y + RH / 2 - d / 2, w: d, h: d, fontSize: 18, bold: true, color: HEAD,
      align: 'center', valign: 'middle', margin: 0 });
  }
  s.addText(tag, { x: X0 + (n ? 0.68 : 0.2), y, w: TW - (n ? 0.75 : 0.3), h: RH, fontSize: 13, bold: true,
    charSpacing: 1.5, color: you ? HEAD : WHITE, valign: 'middle', margin: 0 });
  s.addText(runs, { x: X0 + TW + 0.2, y, w: W - TW - 0.35, h: RH, fontSize: 16, color: INK, valign: 'middle', margin: 0 });
});


pres.writeFile({ fileName: 'promise.pptx' }).then(f => console.log('wrote', f));
