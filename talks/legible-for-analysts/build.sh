#!/bin/sh
# Build the Legible-for-analysts deck and its hand-outs into out/ (see README.md).
# It reuses the round table's slide scripts (../semantic-linting-round-table/slides),
# so run `npm install` in this folder only.
#
#   npm install && sh build.sh
#
# Always produced:  out/legible-for-analysts.pptx
# With LibreOffice (soffice) and poppler-utils (pdftoppm, pdfseparate, pdfunite):
#                   out/legible-for-analysts.pdf, out/team-handout.pdf
# Also with a Chromium-based browser ($CHROME): out/speaker-notes.pdf
# Also with ImageMagick (montage):               out/overview.jpg
#
# Personalise through the environment (config.js): INTRO_SLIDES, PRESENTER_NAME,
# PRESENTER_EMAIL, REPLY_BY. Slide positions below are this deck's own (1-22).
#
#   sh build.sh --publish   also copies the neutral build to the GitHub Pages
#                           folder docs/talks/legible-for-analysts/;
#                           refused when any personalisation is set
set -eu
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
SOFFICE=${SOFFICE:-soffice}
CHROME=${CHROME:-chromium}
OUT=out
DECK=$OUT/legible-for-analysts.pptx
have() { command -v "$1" >/dev/null 2>&1; }

# The published copy is public: never publish a personalised build
if [ "${1:-}" = "--publish" ] && [ -n "${INTRO_SLIDES:-}${PRESENTER_NAME:-}${PRESENTER_EMAIL:-}${REPLY_BY:-}" ]; then
  echo "refusing to publish a personalised build: unset INTRO_SLIDES, PRESENTER_NAME, PRESENTER_EMAIL and REPLY_BY" >&2
  exit 1
fi

rm -rf "$OUT"
node merge-deck.js
$PY post/split-notes.py "$DECK"
$PY post/add-appear.py "$DECK" 5 6     # findings strips reveal on a click

if have "$SOFFICE" && have pdftoppm; then
  # LibreOffice leaves hidden slides out of a PDF, so export before hiding them
  "$SOFFICE" --headless --convert-to pdf --outdir "$OUT" "$DECK" >/dev/null
  PDF=$OUT/legible-for-analysts.pdf
  pdfseparate -f 19 -l 22 "$PDF" "$OUT/part-%d.pdf"
  pdfunite "$OUT/part-19.pdf" "$OUT/part-20.pdf" "$OUT/part-21.pdf" "$OUT/part-22.pdf" "$OUT/team-handout.pdf"
  rm -f "$OUT"/part-*.pdf
  mkdir -p "$OUT/handout"
  pdftoppm -jpeg -r 110 "$PDF" "$OUT/handout/s"
  node make-handout.js
  if have "$CHROME"; then
    "$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
      --print-to-pdf="$OUT/speaker-notes.pdf" "file://$PWD/$OUT/handout/handout.html" 2>/dev/null
  else
    echo "no browser at \$CHROME: open $OUT/handout/handout.html and print it to PDF"
  fi
  if have montage; then
    pdftoppm -jpeg -r 40 "$PDF" "$OUT/ov"
    montage "$OUT"/ov-*.jpg -tile 5x5 -geometry +6+6 -background '#dddddd' "$OUT/overview.jpg"
    rm -f "$OUT"/ov-*.jpg
  fi
else
  echo "LibreOffice or poppler-utils missing: built the .pptx only"
fi

$PY post/hide-slides.py "$DECK" 19 20 21 22   # the team hand-out and the appendix
echo "done: $OUT/"

if [ "${1:-}" = "--publish" ]; then
  for f in "$OUT/legible-for-analysts.pdf" "$OUT/speaker-notes.pdf" "$OUT/team-handout.pdf" "$OUT/overview.jpg"; do
    [ -f "$f" ] || { echo "cannot publish: $f was not built (see the tool list at the top)" >&2; exit 1; }
  done
  SITE=../../docs/talks/legible-for-analysts
  VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' ../../pyproject.toml)
  mkdir -p "$SITE"
  cp "$DECK" "$SITE/deck.pptx"
  cp "$OUT/legible-for-analysts.pdf" "$SITE/deck.pdf"
  cp "$OUT/speaker-notes.pdf" "$OUT/team-handout.pdf" "$OUT/overview.jpg" "$SITE/"
  sed -e "s/{{VERSION}}/$VERSION/g" -e "s/{{DATE}}/$(date +%Y-%m-%d)/g" site/index.html > "$SITE/index.html"
  echo "published: $SITE/ (live on GitHub Pages after the merge to main)"
fi
