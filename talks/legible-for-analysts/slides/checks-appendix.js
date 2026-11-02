// Appendix: every check behind the scoring wheel, by dimension. global.PAGE (1-4)
// picks the slide; the data is pumllint's own catalogue (export_checks.py).
const path = require('path');
const pptxgen = require('pptxgenjs');
const { C, header } = require('./style.js');
const { OUT } = require('../config.js');
const CHECKS = require(path.join(OUT, 'checks.json'));
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;

// Four pages, about fifteen rows each
const PAGES = [['DIM-CMP'], ['DIM-AMB', 'DIM-TRC'], ['DIM-SEM', 'DIM-RDB'], ['DIM-CON']];
const COL = { 'DIM-SEM': '3E6B48', 'DIM-CMP': '42687D', 'DIM-AMB': 'B07A2E', 'DIM-CON': '7E5470', 'DIM-TRC': '6E7B4B', 'DIM-RDB': '5B6770' };
const TYPES = { '*': 'all', activity: 'activity', class: 'class', sequence: 'sequence', state: 'state', usecase: 'use case' };
const byId = Object.fromEntries(CHECKS.dimensions.map(d => [d.id, d]));
const W = [0.75, 2.65, 6.0, 0.95, 1.3, 0.7];
const X = W.map((_, i) => 0.5 + W.slice(0, i).reduce((a, b) => a + b, 0));

function page(n) {
  const dims = PAGES[n - 1].map(id => byId[id]);
  const s = pres.addSlide();
  s.background = { color: C.BG };
  header(s, `Appendix · every check behind the score (${n} of ${PAGES.length})`,
    dims.map(d => `${d.label}, ${Math.round(d.weight * 100)}%`).join(' · '));
  let y = 1.62;
  ['Check', 'Name', 'What it looks for', 'Severity', 'Diagrams', 'When'].forEach((h, i) => {
    s.addShape(S.RECTANGLE, { x: X[i], y, w: W[i], h: 0.3, fill: { color: C.HEAD }, line: { color: C.BG, width: 0.5 } });
    s.addText(h, { x: X[i] + 0.06, y, w: W[i] - 0.08, h: 0.3, fontSize: 11, bold: true, color: C.WHITE, valign: 'middle', margin: 0 });
  });
  y += 0.3;
  dims.forEach(d => {
    s.addShape(S.RECTANGLE, { x: 0.5, y, w: 12.35, h: 0.32, fill: { color: COL[d.id] }, line: { color: COL[d.id] } });
    s.addText([{ text: d.label, options: { bold: true } }, { text: `   ${d.rules.length} checks · ${Math.round(d.weight * 100)}% of the score` }],
      { x: 0.6, y, w: 12.1, h: 0.32, fontSize: 12, color: C.WHITE, valign: 'middle', margin: 0 });
    y += 0.32;
    d.rules.forEach((r, k) => {
      const h = r.description.length > 84 ? 0.4 : 0.24;
      const when = r.profiles.length ? 'codegen' : r.dormant ? 'if set' : '';
      const cells = [
        { text: r.id, options: { bold: true, fontFace: 'Consolas' } },
        { text: r.name, options: { fontFace: 'Consolas', fontSize: r.name.length > 31 ? 8.5 : 9.5 } },
        { text: r.description },
        { text: r.severity, options: { bold: /blocker|critical|major/.test(r.severity), color: /blocker|critical|major/.test(r.severity) ? C.RED : C.INK } },
        { text: r.applies_to.map(t => TYPES[t] || t).join(', '), options: { fontSize: 9.5 } },
        { text: when, options: { color: C.MUTED } },
      ];
      cells.forEach((c, i) => {
        s.addShape(S.RECTANGLE, { x: X[i], y, w: W[i], h, fill: { color: k % 2 ? C.ROW2 : C.ROW }, line: { color: C.BG, width: 0.5 } });
        s.addText([c], { x: X[i] + 0.06, y, w: W[i] - 0.08, h, fontSize: 10.5, color: C.INK, valign: 'middle', margin: 0 });
      });
      y += h;
    });
  });
  s.addText(`When: "codegen" runs only with the code-generation profile; "if set" stays off until a team configures its convention. From pumllint ${CHECKS.version}'s rule catalogue.`,
    { x: 0.5, y: y + 0.06, w: 12.35, h: 0.3, fontSize: 10.5, italic: true, color: C.MUTED, margin: 0 });
  console.log('bottom', n, (y + 0.36).toFixed(2));
}

if (global.PAGE) page(global.PAGE);
else { [1, 2, 3, 4].forEach(page); pres.writeFile({ fileName: 'checks-appendix.pptx' }).then(f => console.log('wrote', f)); }
