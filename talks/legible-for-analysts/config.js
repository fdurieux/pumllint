// Presenter settings. The committed deck is neutral; a presenter personalises
// their build through the environment instead of editing the slides:
//   INTRO_SLIDES     slides the presenter puts in front of this deck (default 0);
//                    the speaker notes, run sheet and one slide cite slide numbers
//   PRESENTER_NAME   PRESENTER_EMAIL   REPLY_BY   the team hand-out's return strip
const fs = require('fs');
const path = require('path');
const env = process.env;
const OFFSET = Number(env.INTRO_SLIDES || 0);
// The release the appendix pins, read from the package so the deck never lags it
const VERSION = fs.readFileSync(path.join(__dirname, '..', '..', 'pyproject.toml'), 'utf8')
  .match(/^version = "([^"]+)"/m)[1];
module.exports = {
  VERSION,
  OFFSET,
  S: n => n + OFFSET, // slide n of this deck, as numbered in the presenter's full deck
  PRESENTER: env.PRESENTER_NAME || '[presenter name]',
  EMAIL: env.PRESENTER_EMAIL || '[email]',
  REPLY_BY: env.REPLY_BY || '[reply-by date]',
  OUT: path.join(__dirname, 'out'),
};
