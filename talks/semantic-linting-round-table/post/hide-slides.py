"""Mark slides as hidden in the slide show (show="0"); they stay in the file and in exports."""
import re, shutil, sys, zipfile
src, nums = sys.argv[1], sys.argv[2:]
names, tmp = {f'ppt/slides/slide{n}.xml' for n in nums}, src + '.tmp'
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename in names:
            xml = data.decode('utf-8')
            assert ' show="0"' not in xml.split('>', 2)[1]
            xml, k = re.subn(r'<p:sld ', '<p:sld show="0" ', xml, count=1)
            assert k == 1; data = xml.encode('utf-8'); print(item.filename, 'hidden')
        zout.writestr(item, data)
shutil.move(tmp, src)
