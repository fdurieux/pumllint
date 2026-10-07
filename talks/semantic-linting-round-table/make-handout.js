// Speaker-notes handout: one A4 page per slide, slide image on top, notes below.
const fs = require('fs');
const path = require('path');
const notes = require('./notes.js');
const { OFFSET, S, OUT } = require('./config.js');
const DIR = path.join(OUT, 'handout'); // slide images s-01.jpg … are rendered here by build.sh
const lastMain = notes.map(n => !n.appendix).lastIndexOf(true);
const part = i => notes[i].handout ? 'Hand-out' : notes[i].appendix ? 'Appendix' : i < 2 ? 'Opening' : i < 7 ? '① The problem' : i < 12 ? '② The contribution' : i < lastMain ? '③ The value' : 'Closing';
const clock = m => `0:${String(m).padStart(2, '0')}`;
const span = n => `${clock(n.from)}–${clock(n.from + n.min)}`;
const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const pages = notes.map((n, i) => `
<section class="page">
  <header><span class="num">${i + 1 + OFFSET} / ${notes.length + OFFSET}</span><span class="part">${part(i)}</span></header>
  <h2>${esc(n.title)}</h2>
  <img src="s-${String(i + 1).padStart(2, '0')}.jpg" alt="Slide ${i + 1 + OFFSET}">
  <h3>Say</h3><ul>${n.say.map(t => `<li>${esc(t)}</li>`).join('')}</ul>
  ${n.ask ? `<div class="ask"><h3>Ask</h3><p>${esc(n.ask)}</p></div>` : ''}
  ${n.tip ? `<h3>Tip</h3><p>${esc(n.tip)}</p>` : ''}
  ${n.next ? `<p class="next"><b>Next →</b> ${esc(n.next)}</p>` : ''}
  <footer>Round table · semantic linting of PlantUML diagrams · speaker notes</footer>
</section>`).join('');
const parts = ['Opening', '① The problem', '② The contribution', '③ The value'];
const rows = notes.slice(0, lastMain + 1).map((n, i) => {
  const first = i === 0 || part(i) !== part(i - 1);
  const inPart = notes.filter((_, j) => part(j) === part(i));
  const total = inPart.reduce((a, x) => a + x.min, 0);
  return `<tr class="${first ? 'first' : ''}">${first ? `<td rowspan="${inPart.length}" class="p">${part(i)}<br><span>${total} min</span></td>` : ''}
    <td class="c">${span(n)}</td><td class="c">${i + 1 + OFFSET}</td><td>${esc(n.title)}</td><td class="c">${n.min}</td>
    <td class="c">${n.discuss || ''}</td><td>${n.room ? esc(n.room) : ''}</td></tr>`;
}).join('');
const used = notes.reduce((a, n) => a + n.min, 0), buf = 45 - used;
const talk = notes.reduce((a, n) => a + n.min - n.discuss, 0), disc = notes.reduce((a, n) => a + n.discuss, 0);
const runSheet = `
<section class="page">
  <header><span class="num">Run sheet</span><span class="time">45 minutes</span></header>
  <h2>Round table · semantic linting of PlantUML diagrams</h2>
  <p class="lead">${talk} min presenting, ${disc} min room discussion, ${buf} min buffer (${clock(used)}–0:45). If time runs short, take slides ${S(8)}–${S(10)} at a minute each; keep the discussion on slides ${S(7)}, ${S(12)}, ${S(15)} and the vote on ${S(16)}.${OFFSET ? ` Slide numbers count ${OFFSET} slide(s) in front of this deck, which are not timed here.` : ''}</p>
  <table class="run"><thead><tr><th>Part</th><th>Clock</th><th>#</th><th>Slide</th><th>Min</th><th>Of which discussion</th><th>Room</th></tr></thead>
  <tbody>${rows}<tr class="first"><td class="p">Buffer</td><td class="c">${clock(used)}–0:45</td><td></td><td>Overrun, questions, close</td><td class="c">${buf}</td><td></td><td></td></tr></tbody></table>
  <footer>Round table · semantic linting of PlantUML diagrams · speaker notes</footer>
</section>`;
fs.mkdirSync(DIR, { recursive: true });
fs.writeFileSync(path.join(DIR, 'handout.html'), `<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Round table: speaker notes</title><style>
@page { size: A4; margin: 14mm 15mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Carlito, Calibri, "Liberation Sans", sans-serif; color: #1E2B22; font-size: 11.5pt; line-height: 1.38; }
.page { page-break-after: always; position: relative; height: 268mm; }
.page:last-child { page-break-after: auto; }
header { display: flex; justify-content: space-between; font-size: 9.5pt; color: #3E6B48; font-weight: bold; letter-spacing: .06em; text-transform: uppercase; border-bottom: 2px solid #9BD12E; padding-bottom: 2mm; }
h2 { color: #3E6B48; font-size: 18pt; margin: 4mm 0 3mm; }
img { width: 100%; border: 1px solid #B4C0AD; display: block; }
h3 { font-size: 10pt; text-transform: uppercase; letter-spacing: .08em; color: #3E6B48; margin: 4.5mm 0 1.5mm; }
ul { margin: 0; padding-left: 5mm; } li { margin-bottom: 1.6mm; }
p { margin: 0; }
.ask { background: #E3F3C2; border-left: 4px solid #9BD12E; padding: 1mm 3mm 2.5mm; margin-top: 4mm; }
.ask h3 { margin-top: 2mm; }
.next { margin-top: 4.5mm; color: #4A5A4E; }
footer { position: absolute; bottom: 0; left: 0; right: 0; font-size: 8.5pt; color: #7A7A7A; border-top: 1px solid #D5DDD0; padding-top: 1.5mm; }
table.run { width: 100%; border-collapse: collapse; margin-top: 4mm; font-size: 10pt; }
.run th { background: #1E2B22; color: #fff; text-align: left; padding: 2mm; font-weight: bold; }
.run td { padding: 1.3mm 2mm; border-bottom: 1px solid #D5DDD0; vertical-align: top; }
.run tr.first td { border-top: 2px solid #9BD12E; }
.run td.p { font-weight: bold; color: #3E6B48; background: #F1F4EF; width: 30mm; }
.run td.p span { font-weight: normal; color: #4A5A4E; }
.run td.c { text-align: center; white-space: nowrap; }
.lead { margin-top: 1mm; color: #4A5A4E; }
</style></head><body>${runSheet}${pages}</body></html>`);
console.log('wrote', path.join(DIR, 'handout.html'));
