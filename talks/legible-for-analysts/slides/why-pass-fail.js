const pptxgen = require('pptxgenjs');
const { C, header } = require('./style.js');
const DEMO = require('../demo-findings.json');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, '③ In practice · the compliant versions pass; here is what the others get wrong', 'Valid or not, and why');

// One row per diagram of the non-compliant set. The rule column is generated from
// demo-findings.json (checked against a live pumllint run by the test suite).
const ko = DEMO['non-compliant'];
const rules = file => ko.findings[file].map(([id, sev, n]) => `${id}${n > 1 ? ' ×' + n : ''} · ${sev}`).join('\n');
const rows = [
  ['Business process', 'credit-application.puml',
    'The score decision does not name its branches, and the flow never reaches an end.',
    'Which branch approves? When is an application finished?'],
  ['Decision', 'credit-decision.puml',
    'An “alt” with no condition; a typo, “Custmer”, quietly adds a second customer.',
    'When does each branch apply? Who is the second customer?'],
  ['Scoring', 'credit-scoring.puml',
    'RiskEngine is a <<gateway>> here and a <<service>> in the decision diagram.',
    'Does the risk engine hold the logic, or only pass calls on?'],
  ['Status', 'application-status.puml',
    'Nothing says what makes an application Approved; nothing leads to Withdrawn; no owner is named.',
    'What triggers approval? Can an application be withdrawn? Whom do I ask?'],
  ['Requirements', null,
    `${ko.uncovered.join(', ')} (“the customer is informed”) is drawn nowhere; ${ko.unknown.join(', ')} is cited but does not exist.`,
    'Is informing the customer designed at all? Typo, or a missing requirement?'],
];
const X = [0.5, 2.6, 7.25, 9.55], W = [2.1, 4.65, 2.3, 3.3], Y0 = 1.68, HH = 0.42, RH = 0.74;
['Diagram', 'What is wrong in the non-compliant version', 'Rule · severity', 'What the next reader has to guess'].forEach((h, i) => {
  s.addShape(S.RECTANGLE, { x: X[i], y: Y0, w: W[i], h: HH, fill: { color: C.HEAD }, line: { color: C.BG, width: 1 } });
  s.addText(h, { x: X[i] + 0.1, y: Y0, w: W[i] - 0.15, h: HH, fontSize: 13.5, bold: true, color: C.WHITE, valign: 'middle', margin: 0 });
});
rows.forEach(([name, file, wrong, guess], r) => {
  const y = Y0 + HH + r * RH, fill = r % 2 ? C.ROW2 : C.ROW;
  const cells = [
    [{ text: name, options: { bold: true, breakLine: !!file } }, ...(file ? [{ text: file, options: { fontFace: 'Consolas', fontSize: 11, color: C.MUTED } }] : [])],
    [{ text: wrong }],
    [{ text: file ? rules(file) : 'trace', options: { fontFace: 'Consolas', bold: true, color: file && /critical|major|blocker/.test(rules(file)) ? C.RED : C.INK } }],
    [{ text: guess, options: { italic: true } }],
  ];
  cells.forEach((runs, i) => {
    s.addShape(S.RECTANGLE, { x: X[i], y, w: W[i], h: RH, fill: { color: fill }, line: { color: C.BG, width: 1 } });
    s.addText(runs, { x: X[i] + 0.1, y, w: W[i] - 0.18, h: RH, fontSize: i === 2 ? 12.5 : 13.5, color: C.INK, valign: 'middle', margin: 0 });
  });
});

// Level versus gate: the point analysts ask about first
const NY = Y0 + HH + rows.length * RH + 0.12;
s.addShape(S.RECTANGLE, { x: 0.5, y: NY, w: 12.35, h: 0.62, fill: { color: C.LIME }, line: { color: C.LIME } });
s.addText([{ text: 'Every non-compliant diagram still scores Level 4. ', options: { bold: true } },
  { text: 'The level says how complete and precise a drawing is overall; the gate looks at how serious each finding is. One critical or major finding stops the hand-off.' }],
  { x: 0.7, y: NY, w: 12.0, h: 0.62, fontSize: 14, color: C.HEAD, valign: 'middle', margin: 0 });
console.log('bottom', (NY + 0.62).toFixed(2));

pres.writeFile({ fileName: 'why-pass-fail.pptx' }).then(f => console.log('wrote', f));
