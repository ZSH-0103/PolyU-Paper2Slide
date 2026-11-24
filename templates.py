from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from io import BytesIO
import hashlib, json, os, shutil, subprocess
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE as Shape
from pptx.oxml.ns import qn
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
LIB = ROOT/'library'
SKILL = Path(os.getenv('PAPER_STUDIO_SKILL',ROOT/'skills/build-paper-beamer-deck'))
RUNTIME = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'
RED = 'polyu-transcope'

def catalog():
    return [json.loads(f.read_text()) for f in sorted(LIB.glob('*/template.json'),key=lambda p:(p.parent.name!=RED,p.parent.name)) if not f.parent.name.startswith('.')]

def red_asset():
    assets=SKILL/'assets/beamer-template'
    return json.loads((assets/'layout.json').read_text()),assets/'polyu-lockup.png'

def init_red(refresh=False):
    folder=LIB/RED
    if not refresh and (folder/'template.json').exists(): return
    folder.mkdir(exist_ok=True,parents=True)
    _,logo=red_asset()
    w,h=12192000,6858000
    for label,band,box in [('cover',2952750,(419100,266700,2324100,561975)),('body',685800,(381000,114886,1885950,456029))]:
        im=Image.new('RGB',(1600,900),'white')
        d=ImageDraw.Draw(im)
        d.rectangle((0,0,1599,round(band/h*900)-1),fill='#990F29')
        d.rectangle((0,round((h-114300)/h*900),1599,899),fill='#990F29')
        x,y,sw,sh=box
        pic=Image.open(logo).convert('RGBA').resize((round(sw/w*1600),round(sh/h*900)),Image.Resampling.LANCZOS)
        im.paste(pic,(round(x/w*1600),round(y/h*900)),pic)
        im.save(folder/(label+'.png'))
    save_meta(folder, RED, 'PolyU Red', w,h,[.05,.17,.9,.22],[.05,.52,.9,.16],[.213,.012,.75,.08])

def save_meta(folder, key, name,w,h,cover,sub,body):
    data=dict(id=key,name=name[:90],width=w,height=h,cover=cover,subtitle=sub,body=body)
    (folder/'template.json').write_text(json.dumps(data,ensure_ascii=False))
    return data

def import_template(data,name):
    key=hashlib.sha256(data).hexdigest()[:24]
    dest=LIB/key
    if (dest/'template.json').exists(): return json.loads((dest/'template.json').read_text())
    with ZipFile(BytesIO(data)) as z:
        if len(z.infolist())>7000 or sum(a.file_size for a in z.infolist())>240_000_000: raise ValueError('模板解压后过大。')
        if 'ppt/presentation.xml' not in z.namelist(): raise ValueError('请选择 PowerPoint .pptx 文件。')
        # External media and linked objects are unnecessary for a reusable background.
        from lxml import etree
        for f in z.namelist():
            if f.endswith('.rels'):
                for rel in etree.fromstring(z.read(f)):
                    if rel.get('TargetMode')=='External' and not rel.get('Type','').endswith('/hyperlink'):
                        raise ValueError('模板含外部资源，请先在 PowerPoint 中嵌入图片再导入。')
    p=Presentation(BytesIO(data))
    if not len(p.slides): raise ValueError('模板没有幻灯片。')
    w,h=p.slide_width,p.slide_height
    if not .45<w/h<3: raise ValueError('暂不支持此页面宽高比。')
    cover,sub,body=[.08,.29,.84,.24],[.08,.56,.84,.15],[.065,.055,.87,.13]
    for i,s in enumerate(list(p.slides)[:2]):
        for sh in list(s.shapes):
            coords=[sh.left,sh.top,sh.width,sh.height]
            box=[v/l for v,l in zip(coords,[w,h,w,h])] if all(v is not None for v in coords) else None
            if sh.is_placeholder and box:
                kind=sh.placeholder_format.type.name
                if kind in ('TITLE','CENTER_TITLE'):
                    if i==0: cover=box
                    else: body=box
                if i==0 and kind=='SUBTITLE': sub=box
            keep=False
            if box and not sh.is_placeholder:
                x,y,sw,shh=box
                if sh.shape_type==Shape.PICTURE:
                    keep=(sw>=.9 and shh>=.9) or (sw<.3 and shh<.19 and (y<.13 or y+shh>.89))
                elif sh.shape_type in (Shape.AUTO_SHAPE,Shape.FREEFORM,Shape.LINE):
                    keep=not getattr(sh,'text','').strip()
            if not keep: sh._element.getparent().remove(sh._element)
        if s.has_notes_slide: s.notes_slide.notes_text_frame.clear()
    for sid in list(p.slides._sldIdLst)[2:]:
        p.part.drop_rel(sid.rId)
        p.slides._sldIdLst.remove(sid)
    with TemporaryDirectory(dir=LIB,prefix='.import-') as tmp:
        stage=Path(tmp)
        clean=stage/'style.pptx'
        p.save(clean)
        office=shutil.which('soffice') or shutil.which('libreoffice')
        if office:
            import pypdfium2 as pdfium
            with TemporaryDirectory() as profile:
                subprocess.run([office,'-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',tmp,str(clean)],capture_output=True,timeout=90,check=True)
            pdf=pdfium.PdfDocument(stage/'style.pdf')
            try:
                for i,label in enumerate(('cover','body')):
                    page=pdf[min(i,len(pdf)-1)]
                    page.render(scale=1.65).to_pil().save(stage/(label+'.png'))
                    page.close()
            finally: pdf.close()
            (stage/'style.pdf').unlink()
        elif (RUNTIME/'node/bin/node').is_file():
            subprocess.run([str(RUNTIME/'node/bin/node'),str(ROOT/'render.mjs'),str(clean),tmp],capture_output=True,timeout=90,check=True)
        else:
            raise ValueError('Install LibreOffice and add soffice to PATH to import a new template.')
        clean.unlink()
        meta=save_meta(stage,key,name,w,h,cover,sub,body)
        try: os.rename(stage,dest)
        except OSError:
            if not (dest/'template.json').exists(): raise
        return meta
