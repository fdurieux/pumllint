"""Add a one-click Appear animation for every shape named reveal-* on the given slides."""
import re, shutil, sys, zipfile
src, slides = sys.argv[1], {f'ppt/slides/slide{n}.xml' for n in sys.argv[2:]}
tmp = src + '.tmp'

def timing(ids):
    n = iter(range(5, 1000))
    effects = []
    for k, spid in enumerate(ids):
        a, b = next(n), next(n)
        kind = 'clickEffect' if k == 0 else 'withEffect'
        effects.append(
            f'<p:par><p:cTn id="{a}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" nodeType="{kind}">'
            '<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:set><p:cBhvr>'
            f'<p:cTn id="{b}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
            '</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set></p:childTnLst></p:cTn></p:par>')
    return ('<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
            '<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            + ''.join(effects) +
            '</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
            '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
            '</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst><p:bldLst>'
            + ''.join(f'<p:bldP spid="{i}" grpId="0" animBg="1"/>' for i in ids) +
            '</p:bldLst></p:timing>')

with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename in slides:
            xml = data.decode('utf-8')
            ids = re.findall(r'<p:cNvPr id="(\d+)" name="reveal-[^"]*"', xml)
            assert ids and '<p:timing>' not in xml and '</p:clrMapOvr>' in xml, item.filename
            xml = xml.replace('</p:clrMapOvr>', '</p:clrMapOvr>' + timing(ids), 1)
            print(item.filename, 'appear on click for shapes', ids)
            data = xml.encode('utf-8')
        zout.writestr(item, data)
shutil.move(tmp, src)
