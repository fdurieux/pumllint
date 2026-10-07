const pptxgen = require('pptxgenjs');
const { PRESENTER, EMAIL, REPLY_BY } = require('../config.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', MUTED = '4A5A4E', BG = 'F7F8F5';
const s = pres.addSlide();
s.background = { color: BG };

// Title and subtitle in the style of the appendix slides that follow
s.addText('Appendix · pumllint for the PoC · what we decide',
  { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
s.addText('A PoC on semantic linting: go or no-go?',
  { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });
const label = (t, x, y, w) => s.addText(t, { x, y, w, h: 0.3, fontSize: 13, bold: true, color: TITLE, charSpacing: 2.5, margin: 0 });
const input = (x, y, w, h, hint) => {
  s.addShape(S.RECTANGLE, { x, y, w, h, fill: { color: WHITE }, line: { color: ROW_LINE, width: 1 } });
  s.addText(hint, { x: x + 0.1, y, w: w - 0.2, h, fontSize: 13, italic: true, color: MUTED, valign: 'middle', margin: 0 });
};

// Why, in three lines: for a reader who was not in the room
const LX = 0.5, LW = 6.65, RY = 1.95, RH = 0.62, RG = 0.06, CW0 = 2.0;
label('WHY, IN THREE LINES', LX, 1.6, LW);
[
  ['1', 'The problem', 'Diagrams render, but not all make sense; every reader downstream, human or AI, fills the gaps.'],
  ['2', 'The contribution', 'A semantic linter finds model smells, gives each diagram a maturity level and gates the hand-off, in the editor and in CI.'],
  ['3', 'Measured', 'AI code from Level 1 sequence diagrams fails ~1 in 3 intended behaviours; from Level 2 up, ~1 in 10.'],
].forEach(([n, h, t], i) => {
  const y = RY + i * (RH + RG), d = 0.4;
  s.addShape(S.RECTANGLE, { x: LX, y, w: LW, h: RH, fill: { color: i % 2 ? ROW2 : ROW }, line: { color: BG } });
  s.addShape(S.RECTANGLE, { x: LX, y, w: CW0, h: RH, fill: { color: HEAD }, line: { color: HEAD } });
  s.addShape(S.OVAL, { x: LX + 0.12, y: y + RH / 2 - d / 2, w: d, h: d, fill: { color: LIME }, line: { color: LIME } });
  s.addText(n, { x: LX + 0.12, y: y + RH / 2 - d / 2, w: d, h: d, fontSize: 16, bold: true, color: HEAD, align: 'center', valign: 'middle', margin: 0 });
  s.addText(h, { x: LX + 0.62, y, w: CW0 - 0.66, h: RH, fontSize: 13.5, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(t, { x: LX + CW0 + 0.12, y, w: LW - CW0 - 0.22, h: RH, fontSize: 13, color: INK, valign: 'middle', margin: 0 });
});

// Your team: fields to fill in
const FX = 7.45, FW = 5.4, FH = 0.48, FG = (3 * (RH + RG) - RG - 4 * FH) / 3, LBW = 1.85;
label('YOUR TEAM', FX, 1.6, FW);
[
  ['Team / squad', '…'],
  ['Team contact', 'name, role'],
  ['Raised by', 'round-table attendee'],
  ['Date', '…'],
].forEach(([h, hint], i) => {
  const y = RY + i * (FH + FG);
  s.addShape(S.RECTANGLE, { x: FX, y, w: LBW, h: FH, fill: { color: i % 2 ? ROW2 : ROW }, line: { color: ROW_LINE, width: 1 } });
  s.addText(h, { x: FX + 0.12, y, w: LBW - 0.2, h: FH, fontSize: 13.5, bold: true, color: INK, valign: 'middle', margin: 0 });
  input(FX + LBW, y, FW - LBW, FH, hint);
});

// Your answer: the vote, as the team's decision
const AY = RY + 3 * (RH + RG) - RG + 0.14, AH = 0.52, AW = 12.35;
s.addShape(S.RECTANGLE, { x: LX, y: AY, w: AW, h: AH, fill: { color: ROW }, line: { color: ROW } });
s.addShape(S.RECTANGLE, { x: LX, y: AY, w: CW0, h: AH, fill: { color: HEAD }, line: { color: HEAD } });
s.addText('Your answer', { x: LX + 0.15, y: AY, w: CW0 - 0.2, h: AH, fontSize: 14, bold: true, color: WHITE, valign: 'middle', margin: 0 });
['Go', 'No-go', 'Not yet'].forEach((t, i) => {
  const x = LX + CW0 + 0.3 + i * 1.3, b = 0.24;
  s.addShape(S.RECTANGLE, { x, y: AY + AH / 2 - b / 2, w: b, h: b, fill: { color: WHITE }, line: { color: HEAD, width: 1.25 } });
  s.addText(t, { x: x + 0.34, y: AY, w: 0.9, h: AH, fontSize: 14, bold: true, color: INK, valign: 'middle', margin: 0 });
});
s.addText('What would change our mind?', { x: 6.5, y: AY, w: 2.6, h: AH, fontSize: 13.5, bold: true, color: INK, valign: 'middle', margin: 0 });
input(9.1, AY + 0.07, LX + AW - 9.1 - 0.07, AH - 0.14, '…');

// If go: the same four agreements as on the closing slide
const GY = AY + AH + 0.42, GH = 0.9;
label('IF GO, WE AGREE ON', LX, GY - 0.33, AW);
const cells = [
  ['Scope', 'which team, which diagrams'],
  ['Success criteria', 'what must the PoC show?'],
  ['Owner & timebox', 'who leads, how many weeks'],
  ['Next check-in', 'when you look at the results'],
];
const CW = (AW - 3 * 0.15) / 4;
cells.forEach(([h, q], i) => {
  const x = LX + i * (CW + 0.15);
  s.addShape(S.RECTANGLE, { x, y: GY, w: CW, h: GH, fill: { color: WHITE }, line: { color: ROW_LINE, width: 1 } });
  s.addShape(S.RECTANGLE, { x, y: GY, w: CW, h: 0.38, fill: { color: HEAD }, line: { color: HEAD } });
  s.addText(h, { x: x + 0.15, y: GY, w: CW - 0.3, h: 0.38, fontSize: 14, bold: true, color: WHITE, valign: 'middle', margin: 0 });
  s.addText(q, { x: x + 0.15, y: GY + 0.43, w: CW - 0.3, h: 0.4, fontSize: 13, italic: true, color: MUTED, valign: 'top', margin: 0 });
});

// Return strip: the way back to the presenter
const BY = GY + GH + 0.12, BH = 0.5;
s.addShape(S.RECTANGLE, { x: LX, y: BY, w: AW, h: BH, fill: { color: LIME }, line: { color: LIME } });
s.addText([
  { text: 'Return to: ' }, { text: PRESENTER, options: { bold: true } }, { text: ' · ' },
  { text: EMAIL, options: { bold: true } }, { text: ' · by ' }, { text: REPLY_BY, options: { bold: true } },
], { x: LX + 0.2, y: BY, w: 7.2, h: BH, fontSize: 15, color: HEAD, valign: 'middle', margin: 0 });
s.addText('Getting started: the three pumllint slides that follow',
  { x: LX + 7.4, y: BY, w: AW - 7.6, h: BH, fontSize: 13.5, italic: true, color: HEAD, align: 'right', valign: 'middle', margin: 0 });
console.log('bottom', (BY + BH).toFixed(2));

pres.writeFile({ fileName: 'team-handout.pptx' }).then(f => console.log('wrote', f));
