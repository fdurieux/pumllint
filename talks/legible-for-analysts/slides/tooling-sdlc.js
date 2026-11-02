const pptxgen = require('pptxgenjs');
const { C, header } = require('./style.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const s = pres.addSlide();
s.background = { color: C.BG };
header(s, '② The contribution · the gates that exist, and where pumllint sits', 'Tooling across the delivery pipeline');

// Artefact -> deterministic gate, per aspect: docs/positioning-quadrant.md §6 (fellow gates)
// and the artefact table on fdurieux.github.io. `true` marks pumllint's own rows.
const cols = [
  ['Continuous Exploration', C.CE, [
    ['requirements and prose', 'vale, markdownlint'],
    ['architecture diagrams (PlantUML)', 'pumllint', true],
    ['ARIS processes (EPC)', 'aris2puml, then pumllint', true],
    ['API contracts', 'Spectral'],
    ['BPMN processes · C4 models', 'bpmnlint · Structurizr validate'],
  ], ['open', 'ADRs, ArchiMate, SysML, stories']],
  ['Continuous Integration', C.CI, [
    ['source code', 'ESLint, ruff, SonarQube'],
    ['commits · containers', 'commitlint · hadolint'],
    ['CI workflows', 'actionlint'],
    ['diagrams, on every change', 'pumllint: CI and pre-commit', true],
  ], ['open', 'diagram-versus-code drift']],
  ['Continuous Deployment', C.CD, [
    ['infrastructure as code', 'tflint, checkov'],
    ['Kubernetes manifests', 'kubeconform'],
    ['policy as code', 'OPA conftest'],
  ], null],
  ['Release on Demand', C.ROD, [
    ['licences · SBOMs', 'REUSE lint · NTIA checker'],
    ['design-governance evidence', 'pumllint badge and HTML report', true],
  ], ['planned', 'process design vs event logs']],
];
const X0 = 0.5, W = (12.35 - 3 * 0.14) / 4, Y0 = 1.62, HH = 0.46, RH = 0.58, RG = 0.05;
let bottom = 0;
cols.forEach(([name, color, rows, gap], i) => {
  const x = X0 + i * (W + 0.14);
  s.addShape(S.RECTANGLE, { x, y: Y0, w: W, h: HH, fill: { color }, line: { color } });
  s.addText(name, { x: x + 0.14, y: Y0, w: W - 0.24, h: HH, fontSize: 16, bold: true, color: C.WHITE, valign: 'middle', margin: 0 });
  let y = Y0 + HH + 0.1;
  rows.forEach(([artefact, gate, ours]) => {
    s.addShape(S.RECTANGLE, { x, y, w: W, h: RH, fill: { color: ours ? 'E3F3C2' : 'FFFFFF' }, line: { color: ours ? C.LIME : C.ROW_LINE, width: ours ? 1.75 : 1 } });
    s.addText([{ text: artefact, options: { color: C.MUTED, fontSize: 12.5, breakLine: true } }, { text: gate, options: { bold: true, color: C.INK, fontSize: 14.5 } }],
      { x: x + 0.12, y, w: W - 0.22, h: RH, valign: 'middle', margin: 0 });
    y += RH + RG;
  });
  if (gap) {
    const [kind, what] = gap;
    s.addShape(S.RECTANGLE, { x, y, w: W, h: RH, fill: { color: kind === 'open' ? C.RED_BG : 'FFFFFF' },
      line: { color: kind === 'open' ? C.RED : C.MUTED, width: 1.25, dashType: 'dash' } });
    s.addText([{ text: kind === 'open' ? 'open gap' : 'planned', options: { bold: true, color: kind === 'open' ? C.RED : C.MUTED, fontSize: 12.5, breakLine: true } },
      { text: what, options: { color: C.INK, fontSize: 13 } }],
      { x: x + 0.12, y, w: W - 0.22, h: RH, valign: 'middle', margin: 0 });
    y += RH + RG;
  }
  bottom = Math.max(bottom, y);
});

// Legend and the reading the positioning note draws from this table
const LY = 1.2, LX = 9.25; // legend, right of the title
s.addShape(S.RECTANGLE, { x: LX, y: LY, w: 0.32, h: 0.24, fill: { color: 'E3F3C2' }, line: { color: C.LIME, width: 1.75 } });
s.addText('pumllint', { x: LX + 0.42, y: LY - 0.03, w: 1.3, h: 0.3, fontSize: 13, color: C.MUTED, margin: 0 });
s.addShape(S.RECTANGLE, { x: LX + 1.6, y: LY, w: 0.32, h: 0.24, fill: { color: C.RED_BG }, line: { color: C.RED, width: 1.25, dashType: 'dash' } });
s.addText('no gate yet', { x: LX + 2.02, y: LY - 0.03, w: 1.6, h: 0.3, fontSize: 13, color: C.MUTED, margin: 0 });
const BY = bottom + 0.04;
s.addShape(S.RECTANGLE, { x: X0, y: BY, w: 12.35, h: 0.46, fill: { color: C.LIME }, line: { color: C.LIME } });
s.addText([{ text: 'Downstream artefacts are gated; the upstream one mostly is not. ', options: { bold: true } },
  { text: 'pumllint brings the pattern the pipeline already trusts to the design.' }],
  { x: X0 + 0.2, y: BY, w: 12.0, h: 0.46, fontSize: 15, color: C.HEAD, valign: 'middle', margin: 0 });
console.log('bottom', (BY + 0.46).toFixed(2));

pres.writeFile({ fileName: 'tooling-sdlc.pptx' }).then(f => console.log('wrote', f));
