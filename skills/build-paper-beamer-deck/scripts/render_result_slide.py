"""Render a PolyU widescreen result slide from a source exhibit and model-written JSON."""
import argparse
import io
import re
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Pt

RED = '990F29'
INK = '202124'
GRAY = '555555'


def field(value, max_length, label):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise ValueError(f'{label} must contain 1 to {max_length} characters')
    return ' '.join(value.split())


def plan(path):
    text = path.read_text(encoding='utf-8-sig').strip()
    if text.startswith(('```json\n', '```\n')) and text.endswith('```'):
        text = text.split('\n', 1)[1][:-3]
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get('bullets'), list) or len(data['bullets']) not in (1, 2):
        raise ValueError('Expected a title and one or two bullets')
    title = field(data.get('title'), 65, 'title')
    bullets = []
    for item in data['bullets']:
        if not isinstance(item, dict):
            raise ValueError('Each bullet needs keyword and trend fields')
        bullets.append((field(item.get('keyword'), 26, 'keyword'), field(item.get('trend'), 90, 'trend')))
    prose = ' '.join([title, *[part for bullet in bullets for part in bullet]])
    prose = re.sub(r'Game of 24|Checkmate-in-One|GPT[- ]?4', '', prose, flags=re.I)
    if re.search(r'(?<![\w-])\d+(?:[.,]\d+)?(?:\s*%|\b)', prose):
        raise ValueError('Remove numerical results from the summary; describe the comparison in words.')
    return title, bullets


def render(args):
    title, bullets = plan(args.json)
    prs = Presentation()
    assets = Path(__file__).resolve().parents[1]/'assets'/'beamer-template'
    layout = json.loads((assets/'layout.json').read_text())
    prs.slide_width, prs.slide_height = layout['canvas_emu']
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    def strip(y, height):
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Pt(y), Pt(960), Pt(height))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(RED)
        shape.line.fill.background()
    def label(x, y, w, h, parts, size, alignment=PP_ALIGN.LEFT):
        box = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
        frame = box.text_frame
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.word_wrap = True
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = frame.paragraphs[0]
        p.alignment = alignment
        for text, color, bold in parts:
            run = p.add_run()
            run.text = text
            run.font.name = 'Arial'
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = RGBColor.from_string(color)
    strip(0, 54)
    strip(531, 9)
    slide.shapes.add_picture(str(assets/'polyu-lockup.png'), *layout['logo_emu']['body'])
    label(430, 8, 497, 37, [('Experimental results', 'FFFFFF', True)], 19, PP_ALIGN.RIGHT)
    label(33, 62, 894, 57, [(title, RED, True)], 23)
    with Image.open(args.exhibit) as im:
        w, h = im.size
        buf = io.BytesIO()
        im.convert('RGB').save(buf, format='PNG')
        buf.seek(0)
    scale = min(850 / w, 246 / h)
    width, height = w * scale, h * scale
    slide.shapes.add_picture(buf, Pt((960-width)/2), Pt(122+(246-height)/2), Pt(width), Pt(height))
    label(35, 371, 890, 32, [(args.caption, GRAY, False)], 14, PP_ALIGN.CENTER)
    for i, (keyword, trend) in enumerate(bullets):
        label(43, 407+i*48, 881, 45, [('•  '+keyword+'   ', RED, True), (trend, INK, False)], 16)
    label(30, 505, 900, 22, [(args.paper, GRAY, False)], 11)
    slide.notes_slide.notes_text_frame.text = args.paper+'\n'+args.caption
    with TemporaryDirectory(dir=args.output.parent) as folder:
        staged = Path(folder)/'slide.pptx'
        prs.save(staged)
        staged.replace(args.output)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('json', type=Path)
    parser.add_argument('exhibit', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--caption', required=True, help='Original figure/table number and concise caption')
    parser.add_argument('--paper', required=True, help='Paper title or citation')
    args = parser.parse_args()
    try:
        render(args)
    except (ValueError, OSError) as error:
        parser.exit(2, f'{error}\n')
