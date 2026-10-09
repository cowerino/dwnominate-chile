# -*- coding: utf-8 -*-
"""QA for the exposition figures: page size, embedded fonts, raster images,
text inside the page, text-text overlaps, minimum font size, PNG renders.

Run with a Python that has PyMuPDF (the system `python` does):
  python qa_figuras.py
Writes qa-results.json next to the figures and PNG renders into qa/.
"""
from pathlib import Path
import json
import sys

import fitz

ROOT = Path(__file__).resolve().parent
QA = ROOT / 'qa'
QA.mkdir(exist_ok=True)
W_PT = 135 * 72 / 25.4
HMAX_PT = 190 * 72 / 25.4
DPI = 220

STEMS = ['F1-contexto', 'F2-casos-de-uso', 'F3-fortran-a-cpp', 'F4-ciclo-estimacion',
         'T5-mecanismos-modernos', 'F6-datos-tiempo-servido', 'F7-verificacion',
         'A1-clases-estado', 'A2-secuencia-estimacion']


def overlaps(a, b, tol=0.6):
    return not (a.x1 - tol <= b.x0 or b.x1 - tol <= a.x0 or
                a.y1 - tol <= b.y0 or b.y1 - tol <= a.y0)


def check(path):
    doc = fitz.open(path)
    page = doc[0]
    rect = page.rect
    result = {
        'pages': len(doc),
        'width_pt': round(rect.width, 2),
        'height_pt': round(rect.height, 2),
        'width_ok': abs(rect.width - W_PT) < 0.05,
        'height_ok': rect.height <= HMAX_PT + 0.05,
        'raster_images': len(page.get_images(full=True)),
        'fonts': sorted({f[3] for f in page.get_fonts(full=True)}),
        'fonts_embedded': all(f[3] and page.get_fonts(full=True) for f in page.get_fonts(full=True)),
        'out_of_page_text': [],
        'text_overlaps': [],
        'minimum_font_pt': None,
        'glyph_notdef': 0,
    }
    # embedded check: PyMuPDF returns (xref, ext, type, basefont, name, encoding, referencer);
    # an embedded TrueType subset has ext 'ttf' / 'cff' rather than 'n/a'.
    result['fonts_embedded'] = all(f[1] != 'n/a' for f in page.get_fonts(full=True))
    spans = []
    sizes = []
    for block in page.get_text('dict')['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            for span in line['spans']:
                text = span['text'].strip()
                if not text:
                    continue
                bb = fitz.Rect(span['bbox'])
                sizes.append(round(span['size'], 2))
                if '�' in text:
                    result['glyph_notdef'] += 1
                if bb.x0 < -0.5 or bb.y0 < -0.5 or bb.x1 > rect.width + 0.5 or bb.y1 > rect.height + 0.5:
                    result['out_of_page_text'].append(text)
                spans.append((text, bb))
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            if overlaps(spans[i][1], spans[j][1]):
                result['text_overlaps'].append([spans[i][0], spans[j][0]])
    result['minimum_font_pt'] = min(sizes) if sizes else None
    pix = page.get_pixmap(dpi=DPI)
    png = QA / (Path(path).stem + '.png')
    pix.save(str(png))
    result['png'] = str(png.relative_to(ROOT)).replace('\\', '/')
    doc.close()
    return result


def main():
    results = {}
    for stem in STEMS:
        results[stem + '.pdf'] = check(ROOT / (stem + '.pdf'))
    review = ROOT / 'figuras-e2-revision.pdf'
    if review.exists():
        doc = fitz.open(review)
        results[review.name] = {'pages': len(doc),
                                'raster_images': sum(len(p.get_images()) for p in doc),
                                'fonts_embedded': all(f[1] != 'n/a' for p in doc for f in p.get_fonts(full=True))}
        doc.close()
    (ROOT / 'qa-results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n',
                                          encoding='utf-8')
    bad = 0
    for name, r in results.items():
        if name == review.name:
            continue
        flags = []
        if not r['width_ok']:
            flags.append('WIDTH')
        if not r['height_ok']:
            flags.append('HEIGHT')
        if r['raster_images']:
            flags.append('RASTER')
        if not r['fonts_embedded']:
            flags.append('FONT')
        if r['out_of_page_text']:
            flags.append('OUT:' + '; '.join(r['out_of_page_text']))
        if r['text_overlaps']:
            flags.append('OVERLAP:' + ' | '.join(' / '.join(p) for p in r['text_overlaps']))
        if r['minimum_font_pt'] is not None and r['minimum_font_pt'] < 7.95:
            flags.append(f'MINFONT {r["minimum_font_pt"]}')
        if r['glyph_notdef']:
            flags.append('NOTDEF')
        status = 'ok' if not flags else 'FLAGS ' + ' ; '.join(flags)
        bad += bool(flags)
        print(f'{name}: {r["width_pt"]}x{r["height_pt"]} pt, min {r["minimum_font_pt"]} pt, {status}')
    print('figures with flags:', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
