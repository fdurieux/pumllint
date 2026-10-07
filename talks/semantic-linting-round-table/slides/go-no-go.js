const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', MUTED = '4A5A4E', GREY_BG = 'ECECEA', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

s.addText('Closing · what we heard, and what we decide',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('A PoC on semantic linting: go or no-go?',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });
const label = (t, x, y, w) => s.addText(t, { x, y, w, h: 0.3, fontSize: 13, bold: true, color: TITLE, charSpacing: 2.5, margin: 0 });

// What we discussed: one line per part of the session
const LX = 0.5, LW = 6.65, RY = 2.05, RH = 0.8, RG = 0.1;
label('WHAT WE DISCUSSED', LX, 1.7, LW);
[
  ['1', 'The problem', 'Diagrams render, but not all of them make sense; every reader downstream fills the gaps.'],
  ['2', 'The contribution', 'A semantic linter finds model smells, measures maturity and gates the hand-off.'],
  ['3', 'The value', 'Checked in the editor and in CI; start with advice, no big-bang cleanup.'],
].forEach(([n, h, t], i) => {
  const y = RY + i * (RH + RG), d = 0.42;
  s.addShape(S.RECTANGLE, { x: LX, y, w: LW, h: RH, fill: { color: i % 2 ? ROW2 : ROW }, line: { color: BG } });
  s.addShape(S.RECTANGLE, { x: LX, y, w: 2.3, h: RH, fill: { color: HEAD }, line: { color: HEAD } });
  s.addShape(S.OVAL, { x: LX + 0.14, y: y + RH / 2 - d / 2, w: d, h: d, fill: { color: LIME }, line: { color: LIME } });
  s.addText(n, { x: LX + 0.14, y: y + RH / 2 - d / 2, w: d, h: d, fontSize: 17, bold: true, color: HEAD, align: 'center', valign: 'middle', margin: 0 });
  s.addText(h, { x: LX + 0.66, y, w: 1.6, h: RH, fontSize: 14, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(t, { x: LX + 2.45, y, w: LW - 2.6, h: RH, fontSize: 14.5, color: INK, valign: 'middle', margin: 0 });
});

// The vote
const VX = 7.45, VW = 5.4, TW = 2.6, TH = 1.95;
label('THE VOTE', VX, 1.7, VW);
[['👍', 'GO', 'run the PoC', LIME, HEAD], ['👎', 'NO-GO', 'not now', GREY_BG, MUTED]].forEach(([icon, t, sub, fill, col], i) => {
  const x = VX + i * (TW + 0.2);
  s.addShape(S.ROUNDED_RECTANGLE, { x, y: RY, w: TW, h: TH, rectRadius: 0.12, fill: { color: fill }, line: { color: i ? ROW_LINE : LIME, width: 1.5 } });
  s.addText(icon, { x, y: RY + 0.1, w: TW, h: 0.95, fontSize: 48, fontFace: 'Segoe UI Emoji', align: 'center', valign: 'middle', margin: 0 });
  s.addText([{ text: t, options: { bold: true, fontSize: 22, breakLine: true } }, { text: sub, options: { fontSize: 13 } }],
    { x, y: RY + 1.05, w: TW, h: 0.8, color: col, align: 'center', valign: 'middle', margin: 0 });
});
s.addText([{ text: 'No-go? ', options: { bold: true } }, { text: 'Ask what would change your mind, and note it.' }],
  { x: VX, y: RY + TH + 0.12, w: VW, h: 0.5, fontSize: 14, color: MUTED, valign: 'middle', margin: 0 });

// If go: what to agree before leaving the room
const GY = 5.2, GH = 1.35;
label('IF GO, WE AGREE BEFORE WE LEAVE', LX, GY - 0.36, 12.35);
const cells = [
  ['Scope', 'which team, which diagrams'],
  ['Success criteria', 'what must the PoC show?'],
  ['Owner & timebox', 'who leads, how many weeks'],
  ['Next check-in', 'when we look at the results'],
];
const CW = (12.35 - 3 * 0.15) / 4;
cells.forEach(([h, q], i) => {
  const x = LX + i * (CW + 0.15);
  s.addShape(S.RECTANGLE, { x, y: GY, w: CW, h: GH, fill: { color: WHITE }, line: { color: ROW_LINE, width: 1 } });
  s.addShape(S.RECTANGLE, { x, y: GY, w: CW, h: 0.42, fill: { color: HEAD }, line: { color: HEAD } });
  s.addText(h, { x: x + 0.15, y: GY, w: CW - 0.3, h: 0.42, fontSize: 15, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(q, { x: x + 0.15, y: GY + 0.48, w: CW - 0.3, h: 0.3, fontSize: 13, italic: true, color: MUTED, margin: 0 });
  s.addText('…', { x: x + 0.15, y: GY + 0.8, w: CW - 0.3, h: 0.5, fontSize: 16, color: INK, valign: 'top', margin: 0 });
});

pres.writeFile({ fileName: 'go-no-go.pptx' }).then(f => console.log('wrote', f));
