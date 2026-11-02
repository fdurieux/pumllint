// Shared look of this talk's own slides: the round table's palette and header.
module.exports = {
  C: {
    TITLE: '3E6B48', HEAD: '1E2B22', ROW: 'D5DDD0', ROW2: 'C3CDBD', ROW_LINE: 'B4C0AD', INK: '1E2B22',
    LIME: '9BD12E', WHITE: 'FFFFFF', MUTED: '4A5A4E', BG: 'F7F8F5', RED: 'B03A2E', RED_BG: 'F6E3E0',
    CE: '6E7B4B', CI: '42687D', CD: '7E5470', ROD: 'B07A2E',
  },
  header(s, subtitle, title, width = 12.2) {
    const { INK, TITLE } = module.exports.C;
    s.addText(subtitle, { x: 0.55, y: 0.35, w: width, h: 0.4, fontSize: 18, bold: true, color: INK, margin: 0 });
    s.addText(title, { x: 0.55, y: 0.75, w: width, h: 0.75, fontSize: 38, bold: true, color: TITLE, margin: 0 });
  },
  label(s, t, x, y, w, color) {
    s.addText(t, { x, y, w, h: 0.3, fontSize: 13, bold: true, color: color || module.exports.C.TITLE, charSpacing: 2.5, margin: 0 });
  },
};
