// Run every slide script against one shared presentation, in storyline order.
const Module = require('module');
const path = require('path');
const real = require('pptxgenjs');
const shared = new real();
shared.layout = 'LAYOUT_WIDE';
shared.theme = { headFontFace: 'Calibri', bodyFontFace: 'Calibri' };
shared.title = 'Semantic linting of PlantUML diagrams: a round table';
shared.writeFile = () => Promise.resolve('(merged)');
function Shared() { return shared; }
const load = Module._load;
Module._load = function (req, ...rest) { return req === 'pptxgenjs' ? Shared : load.call(this, req, ...rest); };
const order = [
  'slides/promise.js',            //  1 The round-table promise
  'slides/three-questions.js',            //  2 Three questions
  'slides/semantic-correctness.js',    //  3 What we mean by semantic correctness
  'slides/credit-flow.js',      //  4 Both render. Which branch approves? (credit flow)
  'slides/order-service.js',            //  5 Both render. Which one is right? (OrderService)
  'slides/the-chain.js',            //  6 Semantic quality: why it matters now (the chain)
  'slides/before.js',            //  7 Today: reviewed by eye, found late
  'slides/linter-to-model-analysis.js',            //  8 From linter to static model analysis
  'slides/model-smells.js',            //  9 Code smells, model smells
  'slides/detect-measure-govern.js',            // 10 Detect, measure, govern
  'slides/evidence.js',    // 11 Does the level matter? Measured: yes
  'slides/sonarqube.js',           // 12 The same pattern you already trust on code
  'RECAP:slides/before.js',      // 13 Recap of the before picture, for the Morph
  'slides/after.js',           // 14 Shift left: checked before it is built on
  'slides/workflow.js',           // 15 Diagram quality, built into the workflow
  'slides/go-no-go.js',       // 16 Closing: recap and the PoC vote
  'slides/team-handout.js',     // 17 Hand-out: does your team want a PoC?
  'APPX1:slides/appendix.js',    // 18 Appendix: get started in ten minutes
  'APPX2:slides/appendix.js',    // 19 Appendix: fit it to your team
  'APPX3:slides/appendix.js',    // 20 Appendix: a four-week PoC
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
real.prototype.writeFile.call(shared, { fileName: path.join(OUT, 'semantic-linting-round-table.pptx') }).then(f => console.log('wrote', f));
