"""Give one slide a Morph transition (fallback: fade for viewers without Morph support)."""
import shutil, sys, zipfile
src, n = sys.argv[1], sys.argv[2]
name, tmp = f'ppt/slides/slide{n}.xml', src + '.tmp'
NS = ('xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
      'xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" '
      'xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" ')
MORPH = ('<mc:AlternateContent><mc:Choice Requires="p159">'
         '<p:transition spd="slow" p14:dur="1500"><p159:morph option="byObject"/></p:transition>'
         '</mc:Choice><mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback>'
         '</mc:AlternateContent>')
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == name:
            xml = data.decode('utf-8')
            assert '<p:transition' not in xml and '</p:clrMapOvr>' in xml and '<p:sld ' in xml
            xml = xml.replace('<p:sld ', '<p:sld ' + NS, 1)
            xml = xml.replace('</p:clrMapOvr>', '</p:clrMapOvr>' + MORPH, 1)
            data = xml.encode('utf-8'); print(name, 'morph transition added')
        zout.writestr(item, data)
shutil.move(tmp, src)
