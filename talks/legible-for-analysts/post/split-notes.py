"""Turn each notes slide's single text run into one paragraph per line, headings in bold."""
import re, shutil, sys, zipfile
src = sys.argv[1]; tmp = src + '.tmp'
pat = re.compile(r'<a:p><a:r><a:rPr lang="en-US" dirty="0"/><a:t>(.*?)</a:t></a:r><a:endParaRPr lang="en-US" dirty="0"/></a:p>', re.S)
def para(line):
    if not line.strip():
        return '<a:p><a:endParaRPr lang="en-US" dirty="0"/></a:p>'
    b = ' b="1"' if line in ('TIME', 'SAY', 'ASK', 'TIP', 'NEXT') else ''
    return f'<a:p><a:r><a:rPr lang="en-US"{b} dirty="0"/><a:t>{line}</a:t></a:r></a:p>'
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    n = 0
    for item in zin.infolist():
        data = zin.read(item.filename)
        if re.match(r'ppt/notesSlides/notesSlide\d+\.xml$', item.filename):
            xml = data.decode('utf-8')
            xml, k = pat.subn(lambda m: ''.join(para(l) for l in re.split(r'\r?\n', m.group(1))), xml, count=1)
            n += k; data = xml.encode('utf-8')
        zout.writestr(item, data)
shutil.move(tmp, src); print('split notes on', n, 'slides')
