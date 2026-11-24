"""Insert the official white lockup with SVG geometry and a transparent PNG fallback."""
from lxml import etree
from pptx.opc.package import Part
from pptx.opc.packuri import PackURI
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn

def add_logo(slide, assets, rectangle):
    picture=slide.shapes.add_picture(str(assets/'polyu-lockup.png'),*rectangle)
    package=slide.part.package
    name=PackURI('/ppt/media/polyu-lockup.svg')
    vector=next((part for part in package.iter_parts() if part.partname==name),None)
    if vector is None:
        vector=Part(name,'image/svg+xml',package,(assets/'polyu-lockup.svg').read_bytes())
    rid=slide.part.relate_to(vector,RT.IMAGE)
    blip=picture._element.xpath('.//a:blip')[0]
    extensions=etree.SubElement(blip,qn('a:extLst'))
    ext=etree.SubElement(extensions,qn('a:ext'),uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}')
    uri='http://schemas.microsoft.com/office/drawing/2016/SVG/main'
    svg=etree.SubElement(ext,'{'+uri+'}svgBlip',nsmap={'asvg':uri})
    svg.set(qn('r:embed'),rid)
    return picture
