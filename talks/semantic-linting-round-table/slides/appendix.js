// Appendix: pumllint hand-out for the PoC team. global.APPENDIX (1–3) picks the slide;
// run standalone, it builds all three.
const pptxgen = require('pptxgenjs');
const { VERSION } = require('../config.js');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5, as the deck
pres.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
const S = pres.shapes;
const TITLE = '3E6B48', HEAD = '1E2B22', ROW = 'D5DDD0', ROW2 = 'C3CDBD', ROW_LINE = 'B4C0AD', INK = '1E2B22',
      LIME = '9BD12E', WHITE = 'FFFFFF', MUTED = '4A5A4E', GREY_BG = 'ECECEA', CODE_C = 'A9B8A4', BG = 'F7F8F5';
const MONO = 'Consolas';
const head = (s, sub, title) => {
  s.background = { color: BG };
  s.addText('Appendix · pumllint for the PoC · ' + sub, { x: 0.55, y: 0.35, w: 12.2, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
  s.addText(title, { x: 0.55, y: 0.75, w: 12.2, h: 0.75, fontSize: 40, bold: true, color: TITLE, margin: 0 });
};
const label = (s, t, x, y, w) => s.addText(t, { x, y, w, h: 0.3, fontSize: 13, bold: true, color: TITLE, charSpacing: 2.5, margin: 0 });
const code = (s, lines, x, y, w, h, fs = 13) => {
  s.addShape(S.RECTANGLE, { x, y, w, h, fill: { color: HEAD }, line: { color: HEAD } });
  s.addText(lines.map(([c, cm], i) => [
    { text: c, options: { color: WHITE } },
    ...(cm ? [{ text: cm, options: { color: CODE_C } }] : []),
  ]).flatMap((runs, i, a) => i < a.length - 1 ? [...runs.slice(0, -1), { ...runs[runs.length - 1], options: { ...runs[runs.length - 1].options, breakLine: true } }] : runs),
  { x: x + 0.2, y, w: w - 0.4, h, fontFace: MONO, fontSize: fs, valign: 'middle', margin: 0, paraSpaceAfter: 3 });
};
const card = (s, x, y, w, h, t, body, fill = ROW) => {
  s.addShape(S.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: ROW_LINE, width: 0.75 } });
  s.addShape(S.RECTANGLE, { x, y, w: 0.09, h, fill: { color: LIME }, line: { color: LIME } });
  s.addText([{ text: t, options: { bold: true, fontSize: 15, breakLine: true } }, { text: body, options: { fontSize: 13, color: MUTED } }],
    { x: x + 0.25, y, w: w - 0.35, h, color: INK, valign: 'middle', margin: 0 });
};
const footer = (s, runs) => s.addText(runs, { x: 0.5, y: 6.08, w: 12.35, h: 0.45, fontSize: 12.5, color: MUTED, valign: 'middle', margin: 0 });

const slides = {
  1: () => {
    const s = pres.addSlide();
    head(s, 'install and first run', 'Get started in ten minutes');
    label(s, 'SIX COMMANDS', 0.5, 1.72, 7);
    code(s, [
      ['$ pip install pumllint            ', '# or pipx / uv tool install'],
      ['$ pumllint diagrams/              ', '# findings, with severity'],
      ['$ pumllint score diagrams/        ', '# maturity level per diagram'],
      ['$ pumllint score diagrams/ -f html -o report.html'],
      ['$ pumllint --list-rules           ', '# everything it checks'],
      ['$ pumllint lsp                    ', '# findings in your editor'],
    ], 0.5, 2.08, 7.25, 3.75, 13);
    label(s, 'WHAT YOU GET BACK', 8.0, 1.72, 4.85);
    [
      ['Findings', 'rule, severity and line, e.g. ACT002 · major'],
      ['A maturity level', 'per diagram and per set, with what it takes to reach the next one'],
      ['An HTML report', 'one self-contained page, to share or attach to a review'],
      ['Exit codes for CI', '0 clean · 1 findings at or above --fail-on (default major) · 2 usage error'],
    ].forEach(([t, b], i) => card(s, 8.0, 2.08 + i * 0.96, 4.85, 0.86, t, b));
    footer(s, [
      { text: 'Python 3.11 or later · no runtime dependencies (PyYAML only for a YAML config).  ', options: { bold: true, color: INK } },
      { text: 'Read more in the repository: README · docs/findings-and-scores.md · docs/rule-map.md · docs/business-processes.md' },
    ]);
  },
  2: () => {
    const s = pres.addSlide();
    head(s, 'configure, automate, connect', 'Fit it to your team');
    const W = 3.98, X = i => 0.5 + i * (W + 0.2), Y = 1.75, H = 3.45, HB = 0.45;
    const col = (i, t) => {
      s.addShape(S.RECTANGLE, { x: X(i), y: Y, w: W, h: H, fill: { color: ROW }, line: { color: ROW_LINE, width: 0.75 } });
      s.addShape(S.RECTANGLE, { x: X(i), y: Y, w: W, h: HB, fill: { color: HEAD }, line: { color: HEAD } });
      s.addText(t, { x: X(i) + 0.18, y: Y, w: W - 0.36, h: HB, fontSize: 16, bold: true, color: WHITE, valign: 'middle', margin: 0 });
    };
    const txt = (i, y, h, runs) => s.addText(runs, { x: X(i) + 0.18, y, w: W - 0.36, h, fontSize: 13, color: INK, valign: 'top', margin: 0 });
    col(0, 'Configure');
    txt(0, Y + 0.55, 0.45, [{ text: 'pumllint.yaml (or .toml / .json) is picked up automatically:' }]);
    code(s, [['rules:'], ['  unnamed-diagram: false'], ['  participant-naming:'], ['    severity: major'], ['  requirement-link:'], ['    pattern: "REQ-\\d+"']],
      X(0) + 0.18, Y + 1.02, W - 0.36, 1.68, 11.5);
    txt(0, Y + 2.8, 0.6, [{ text: 'One exception in one diagram: ', options: { bold: true } }, { text: "' pumllint: disable=SEQ006", options: { fontFace: MONO, fontSize: 11.5 } }]);
    col(1, 'Automate');
    txt(1, Y + 0.55, 0.45, [{ text: 'GitHub Actions, pinned to a release:' }]);
    code(s, [[`- uses: fdurieux/pumllint@v${VERSION}`], ['  with:'], ['    command: score'], ['    paths: docs/diagrams'], ['    baseline: maturity.json'], ['    min-level: "2"']],
      X(1) + 0.18, Y + 1.02, W - 0.36, 1.68, 11.5);
    txt(1, Y + 2.8, 0.6, [{ text: 'Or per commit: ', options: { bold: true } }, { text: 'the pre-commit hooks pumllint and pumllint-score.' }]);
    col(2, 'Connect');
    const items = [
      ['SonarQube', '-f sonar writes SonarQube\'s import format: findings on the same dashboard and in pull requests.'],
      ['ARIS', 'the separate aris2puml tool converts processes to PlantUML; they pass the same gate.'],
      ['Editors', 'pumllint lsp in any editor that supports LSP; no editor-specific plugins.'],
    ];
    items.forEach(([t, b], k) => txt(2, Y + 0.6 + k * 0.92, 0.9, [{ text: t, options: { bold: true, breakLine: true } }, { text: b }]));
    // Roll-out mapped to commands
    const RY = 5.4, RH = 0.62, RW = 4.2, RX = [0.5, 4.57, 8.64];
    [['Advise', 'report only, no gate'], ['Ratchet', '--baseline maturity.json'], ['Floor', '--min-level 2']].forEach(([t, c], i) => {
      s.addShape(i ? S.CHEVRON : S.PENTAGON, { x: RX[i], y: RY, w: i === 2 ? 4.21 : RW, h: RH, fill: { color: [ROW, ROW2, TITLE][i] }, line: { color: BG, width: 1.5 } });
      s.addText([{ text: `Step ${i + 1} · ${t.toUpperCase()}   `, options: { bold: true, fontFace: 'Calibri' } }, { text: c, options: i ? { fontFace: MONO, fontSize: 10.5 } : {} }],
        { x: RX[i] + (i ? 0.4 : 0.18), y: RY, w: RW - 0.75, h: RH, fontSize: 12.5, color: i === 2 ? WHITE : INK, valign: 'middle', margin: 0 });
    });
  },
  3: () => {
    const s = pres.addSlide();
    head(s, 'a suggested plan', 'A four-week PoC, and what to measure');
    const weeks = [
      ['Week 1 · Baseline', 'One team and its diagrams. Score them, publish the HTML report, record maturity.json.'],
      ['Week 2 · Advise', 'pumllint lsp in the editors; authors fix as they go. Nothing fails.'],
      ['Week 3 · Ratchet', 'In CI with --baseline: no diagram may get worse.'],
      ['Week 4 · Review', 'Compare with the baseline; agree the floor and the next step.'],
    ];
    const W = 2.93, Y = 1.75;
    weeks.forEach(([t, b], i) => {
      const x = 0.5 + i * (W + 0.16);
      s.addShape(i ? S.CHEVRON : S.PENTAGON, { x, y: Y, w: W + 0.12, h: 0.5, fill: { color: [ROW, ROW2, ROW2, TITLE][i] }, line: { color: BG, width: 1.5 } });
      s.addText(t, { x: x + (i ? 0.3 : 0.15), y: Y, w: W - 0.35, h: 0.5, fontSize: 14, bold: true, color: i === 3 ? WHITE : INK, valign: 'middle', margin: 0 });
      s.addText(b, { x: x + 0.1, y: Y + 0.58, w: W - 0.15, h: 0.95, fontSize: 13, color: INK, valign: 'top', margin: 0 });
    });
    // What to measure
    const MY = 3.5, MH = 2.45, MW = 8.25;
    s.addShape(S.RECTANGLE, { x: 0.5, y: MY, w: MW, h: MH, fill: { color: ROW }, line: { color: ROW_LINE, width: 0.75 } });
    s.addShape(S.RECTANGLE, { x: 0.5, y: MY, w: MW, h: 0.45, fill: { color: HEAD }, line: { color: HEAD } });
    s.addText('What to measure', { x: 0.68, y: MY, w: MW - 0.4, h: 0.45, fontSize: 16, bold: true, color: WHITE, valign: 'middle', margin: 0 });
    const m = [
      'Findings per dimension, week 1 against week 4',
      'Sequence and state diagrams at Level 4; processes without a major finding',
      'Time to fix a finding, as the authors report it',
      'Noise: findings the team disagrees with, and the config changes they lead to',
      'Feedback from authors and reviewers',
      'Rework found downstream: the expected benefit, measured here for the first time',
    ];
    s.addText(m.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < m.length - 1 } })),
      { x: 0.7, y: MY + 0.55, w: MW - 0.4, h: MH - 0.65, fontSize: 14, color: INK, valign: 'top', margin: 0, paraSpaceAfter: 4 });
    // Success criteria pointer
    const SX = 8.95, SW = 3.9;
    s.addShape(S.RECTANGLE, { x: SX, y: MY, w: SW, h: MH, fill: { color: LIME }, line: { color: LIME } });
    s.addText([
      { text: 'Success criteria', options: { bold: true, fontSize: 16, breakLine: true } },
      { text: 'Agreed on the closing slide: what must the PoC show? Write them here before week 1, so week 4 compares against them.', options: { fontSize: 14 } },
    ], { x: SX + 0.2, y: MY + 0.1, w: SW - 0.4, h: MH - 0.2, color: HEAD, valign: 'middle', margin: 0 });
    footer(s, [{ text: 'A proposal to adapt: ', options: { bold: true, color: INK } }, { text: 'the length, the team and the measures are the PoC owner\'s call.' }]);
  },
};
if (global.APPENDIX) slides[global.APPENDIX]();
else { [1, 2, 3].forEach(n => slides[n]()); pres.writeFile({ fileName: 'appendix.pptx' }).then(f => console.log('wrote', f)); }
