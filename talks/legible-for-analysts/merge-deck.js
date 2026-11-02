// Run every slide script against one shared presentation, in storyline order.
// Slides marked RT come unchanged from the round-table talk next door.
const Module = require('module');
const path = require('path');
const real = require('pptxgenjs');
const shared = new real();
shared.layout = 'LAYOUT_WIDE';
shared.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
shared.title = 'Legible for analysts: semantic linting of PlantUML diagrams';
shared.writeFile = () => Promise.resolve('(merged)');
function Shared() { return shared; }
const load = Module._load;
Module._load = function (req, ...rest) { return req === 'pptxgenjs' ? Shared : load.call(this, req, ...rest); };
const RT = '../semantic-linting-round-table/slides/';
const order = [
  'slides/legible.js',                      //  1 Legible: checked before it is handed on
  RT + 'three-questions.js',                //  2 Three questions
  'slides/problems-sdlc.js',                //  3 Problems to solve, across the delivery pipeline
  RT + 'semantic-correctness.js',           //  4 What we mean by semantic correctness
  RT + 'credit-flow.js',                    //  5 Both render. Which branch approves? (credit flow)
  RT + 'order-service.js',                  //  6 Both render. Which one is right? (OrderService)
  RT + 'the-chain.js',                      //  7 Semantic quality: why it matters now
  'slides/tooling-sdlc.js',                 //  8 Tooling across the delivery pipeline
  RT + 'linter-to-model-analysis.js',       //  9 From linter to static model analysis
  'slides/score-wheel.js',                  // 10 What the score is made of (the wheel)
  RT + 'model-smells.js',                   // 11 Code smells, model smells
  RT + 'detect-measure-govern.js',          // 12 Detect, measure, govern
  RT + 'evidence.js',                       // 13 Does the level matter? Measured: yes
  'slides/demo-set.js',                     // 14 The demo: a credit application
  'slides/why-pass-fail.js',                // 15 Valid or not, and why
  'slides/live-demo.js',                    // 16 Live demo: localhost:8000
  RT + 'workflow.js',                       // 17 Diagram quality, built into the workflow
  RT + 'go-no-go.js',                       // 18 A PoC on semantic linting: go or no-go?
  'slides/read-more.js',                    // 19 pumllint on GitHub: where to read more
  RT + 'team-handout.js',                   // 20 Hand-out: does your team want a PoC? (hidden)
  'APPX1:' + RT + 'appendix.js',            // 21 Appendix: get started in ten minutes (hidden)
  'APPX2:' + RT + 'appendix.js',            // 22 Appendix: fit it to your team (hidden)
  'APPX3:' + RT + 'appendix.js',            // 23 Appendix: a four-week PoC (hidden)
  'PAGE1:slides/checks-appendix.js',        // 24 Appendix: every check, completeness (hidden)
  'PAGE2:slides/checks-appendix.js',        // 25 Appendix: ambiguity, traceability (hidden)
  'PAGE3:slides/checks-appendix.js',        // 26 Appendix: logical correctness, readability (hidden)
  'PAGE4:slides/checks-appendix.js',        // 27 Appendix: consistency (hidden)
];
const notes = require('./notes.js');
const { OUT } = require('./config.js');
require('fs').mkdirSync(OUT, { recursive: true });
const clock = m => `0:${String(m).padStart(2, '0')}`;
const asText = n => [
  'SAY', ...n.say.map(t => '• ' + t),
  ...(n.ask ? ['', 'ASK', n.ask] : []),
  ...(n.tip ? ['', 'TIP', n.tip] : []),
  ...(n.next ? ['', 'NEXT', n.next] : []),
].join('\n');
order.forEach((f, i) => {
  if (f.startsWith('APPX')) {
    const file = path.resolve(__dirname, f.split(':')[1]);
    delete require.cache[file];
    global.APPENDIX = Number(f[4]); require(file); global.APPENDIX = 0;
  } else if (f.startsWith('PAGE')) {
    const file = path.resolve(__dirname, f.split(':')[1]);
    delete require.cache[file];
    global.PAGE = Number(f[4]); require(file); global.PAGE = 0;
  } else if (f.startsWith('RECAP:')) {
    const file = path.resolve(__dirname, f.slice(6));
    delete require.cache[file];
    global.RECAP_BEFORE = true; require(file); global.RECAP_BEFORE = false;
  } else require(path.resolve(__dirname, f));
  const slide = shared.slides[shared.slides.length - 1];
  slide._slideObjects = slide._slideObjects.filter(o => o._type !== 'notes');
  slide.addNotes(asText(notes[i]));
});
Module._load = load;
real.prototype.writeFile.call(shared, { fileName: path.join(OUT, 'legible-for-analysts.pptx') }).then(f => console.log('wrote', f));
