// Speaker notes, one entry per slide, in deck order (see merge-deck.js). Slides
// reused from the round table reuse its notes, looked up by title, with this
// talk's own part, timing and bridge; slide numbers go through S(n) (config.js).
// part: the run-sheet section · min: minutes on the slide · discuss: of which room discussion
// say / ask / tip / next: as in the round table. `from` is computed below.
const { S } = require('./config.js');
const RT = require('../semantic-linting-round-table/notes.js');
const rt = (title, extra) => {
  const n = RT.find(x => x.title === title);
  if (!n) throw new Error(`round-table note not found: ${title}`);
  return { ...n, ...extra };
};

const notes = [
  { part: 'Opening', title: 'Legible: checked before it is handed on', min: 3, discuss: 0,
    say: [
      'This session sits in a wider programme, Legible: everything written before code (requirements, processes, models, decisions, contracts) made query-able for humans and AI, and checked before anyone builds on it.',
      'Two halves. Legible: one identity per entity, stable IDs, machine-readable, traceable both ways. Checked: a gate before hand-off, with a severity, a threshold, a baseline and a score.',
      'Code has had those gates for twenty years. The information code is built from has had none, and AI now builds code from it at near-zero cost.',
      'pumllint is the programme’s reference gate. Today is about that gate, from an analyst’s point of view.'],
    tip: 'The QR code opens the programme’s map; leave it up a few seconds for phones.',
    next: 'Three questions frame the next forty minutes.' },
  rt('Three questions for this round table', { part: 'Opening', min: 2, discuss: 1,
    next: 'First: what actually goes wrong before code?' }),
  { part: '① The problem', title: 'Problems to solve, across the delivery pipeline', min: 4, discuss: 1,
    room: 'Which of these do you see in your own work?',
    say: [
      'The four aspects of the delivery pipeline, as SAFe names them; used as vocabulary only.',
      'Continuous Exploration is where analysts work: requirements, processes, models. Every problem in that column is something that renders, reads well, and still leaves the next person guessing.',
      'Continuous Integration is where checks run today: on code, for twenty years. The design the code comes from is not checked, so its gaps are found late, or filled by an AI guess. The one measured number: from Level 1 sequence diagrams, about 1 in 3 intended behaviours fail.',
      'Deployment carries no claim; Release on Demand is about evidence and learning.',
      'The bottom line is the programme’s: the artefacts are written on the left, the gates on them run in the middle.'],
    ask: 'Which column do you recognise? Where did a gap in a diagram last cost you time?',
    next: 'What do we mean by "makes sense"?' },
  rt('What we mean by semantic correctness', { part: '① The problem', min: 2, discuss: 0,
    next: 'Two examples. First, a credit flow.' }),
  rt('Both render. Which branch approves?', { part: '① The problem', min: 3, discuss: 1,
    next: 'A second kind of problem only shows across diagrams.' }),
  rt('Both render. Which one is right?', { part: '① The problem', min: 2, discuss: 1,
    next: 'Why this matters: someone builds on every diagram.' }),
  rt('Semantic quality: why it matters now', { part: '① The problem', min: 2, discuss: 0,
    next: 'Which tools gate which artefact today?' }),
  { part: '② The contribution', title: 'Tooling across the delivery pipeline', min: 4, discuss: 1,
    room: 'Which gates already run in your pipeline?',
    say: [
      'The same four columns, now with the deterministic gates that exist for each artefact.',
      'Everything downstream has one: code, commits, containers, infrastructure, licences. CI runs them without debate.',
      'Upstream, the gates are patchy: prose and API contracts have them, most models do not. Red boxes are open gaps: ADRs, ArchiMate, SysML, user stories, the glossary.',
      'The green boxes are pumllint: PlantUML diagrams, ARIS processes converted by aris2puml, the same check on every change, and the evidence for governance.'],
    ask: 'Which of these gates already runs in your pipeline, and who looks at its results?',
    next: 'How a semantic linter works.' },
  rt('From linter to static model analysis', { part: '② The contribution', min: 2, discuss: 0,
    say: [
      'A conventional linter matches patterns in text: line too long, unused variable.',
      `pumllint first turns each diagram into a model (who talks to whom, which flows, which states) and reasons over it, inside one diagram and across the whole set. Slide ${S(6)}’s finding only exists across files.`,
      'Detect, findings with a severity, is what any linter does. pumllint goes two steps further: measure (a maturity level per diagram and per set) and govern (a gate the team sets).',
      'Hence "static model analysis" rather than just a linter.'],
    next: 'What do those findings look like?' }),
  rt('Code smells, model smells', { part: '② The contribution', min: 1, discuss: 0,
    next: 'What does each severity do?' }),
  rt('Detect, measure, govern', { part: '② The contribution', min: 2, discuss: 0,
    say: [
      'Detect: blocker, critical and major fail the build; minor and info are reported and lower the score.',
      'Measure: the findings add up to a level per diagram. Level 4, Precise, is the hand-off bar: the next step can build on it without guessing.',
      'Govern: the team picks the bar and the gate enforces it. For business processes, gate on findings: no ambiguity rule covers activity diagrams yet, so their level can look better than it is.',
      `The demo in a minute shows exactly that: every broken diagram still reaches Level 4, and the gate still fails.`],
    next: 'Does the level actually matter?' }),
  rt('Does the level matter? Measured: yes', { part: '② The contribution', min: 1, discuss: 0,
    next: 'Enough slides: one business case, drawn right and drawn wrong.' }),
  { part: '③ In practice', title: 'The demo: a credit application', min: 1, discuss: 0,
    say: [
      'One business case, four linked diagrams: the requirements, the business process, the decision as a sequence diagram, one step in detail, and the application status as a state chart.',
      'They share names and requirement IDs, as a real set would, so pumllint can check them together.',
      'Each diagram exists twice: compliant and with deliberate defects. All eight render.'],
    next: 'What is wrong with the second version, and why it matters.' },
  { part: '③ In practice', title: 'Valid or not, and why', min: 2, discuss: 0,
    say: [
      'Read the right-hand column aloud: every defect is a question the next reader has to answer by guessing.',
      'The rule column is what pumllint reports; the test suite checks it against a live run, so this slide cannot drift from the tool.',
      'The bottom line answers the first question analysts ask: the level summarises, the gate judges severity.'],
    next: 'Now the same set, live.' },
  { part: '③ In practice', title: 'Live demo: localhost:8000', min: 9, discuss: 3,
    room: 'Who would have found these, and when?',
    say: [
      'Switch to the browser. Follow WALKTHROUGH.md in the sandbox folder: every diagram renders; the compliant set; the non-compliant set; fix one live; levels, gates and requirements.',
      'Let the room spot defects in the pictures before you scroll to the findings.',
      'The live fix is the moment that lands: label the two branches, add "stop", save, reload, and three findings disappear.'],
    ask: 'Who downstream would have found these, and when?',
    tip: 'Start docker compose up before the session. If anything fails, slides 13 and 14 carry the same results.',
    next: 'Where would this run in our work?' },
  rt('Diagram quality, built into the workflow', { part: '③ In practice', min: 2, discuss: 0,
    next: 'Time to decide.' }),
  rt('A PoC on semantic linting: go or no-go?', { part: 'Closing', min: 2, discuss: 1,
    next: 'Where to read more.' }),
  { part: 'Closing', title: 'pumllint on GitHub: where to read more', min: 0, discuss: 0,
    say: [
      'Leave this slide up while people leave: the QR code opens the repository; Legible and the demo sandbox are in the first column.'] },
  rt('Appendix · A PoC on semantic linting: go or no-go?', { part: 'Hand-out',
    tip: `Send slides ${S(19)} to ${S(22)} as one PDF (team-handout.pdf), or print them.` }),
  rt('Appendix · Get started in ten minutes', { part: 'Appendix' }),
  rt('Appendix · Fit it to your team', { part: 'Appendix' }),
  rt('Appendix · A four-week PoC, and what to measure', { part: 'Appendix' }),
];

let clock = 0;
for (const n of notes) { n.from = clock; if (!n.appendix) clock += n.min; }
module.exports = notes;
