# -*- coding: utf-8 -*-
"""Build six exposition figures, mechanism table T5 and appendix A1-A2 for the Informe de Etapa 2.

Derived from ../diagramas-corregidos/build_diagrams.py (the audit set), which is
left untouched. Differences: Palatino (the thesis body font), concise internal scope labels, functional labels first with routines and flags in a smaller
size, one question per figure, width 135 mm and height at most 190 mm.

Every text that goes into a box is measured; a string wider than its box raises
instead of overflowing. Run with the Codex Python that has reportlab:

  C:/Users/cow/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe build_figuras.py
"""
from pathlib import Path
from html import escape
import hashlib
import json
import math

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parent
MM = 72 / 25.4
W = 135 * MM            # 382.68 pt
HMAX = 190 * MM         # 538.58 pt
FONT_DIR = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Pala', str(FONT_DIR / 'pala.ttf')))
pdfmetrics.registerFont(TTFont('PalaB', str(FONT_DIR / 'palab.ttf')))
pdfmetrics.registerFont(TTFont('PalaI', str(FONT_DIR / 'palai.ttf')))
FONT = {'r': 'Pala', 'b': 'PalaB', 'i': 'PalaI'}
SVG_FAMILY = "'Palatino Linotype', Palatino, 'Book Antiqua', serif"

TITLE = 9.5     # box titles and primary labels
BODY = 9        # attribute lines, relation labels, action text
SECOND = 8      # routine names, flags, stereotypes: secondary evidence
LEGEND = 8.5    # legend and notes

FIGURES = []


def sw(text, style='r', size=BODY):
    return pdfmetrics.stringWidth(text, FONT[style], size)


class Fig:
    def __init__(self, stem, height, caption, key, number, question, expected):
        if height > HMAX + 0.01:
            raise ValueError(f'{stem}: height {height:.1f} pt exceeds 190 mm')
        self.stem, self.height = stem, height
        self.caption, self.key = caption, key
        self.number, self.question, self.expected = number, question, expected
        self.ops = []
        self.errors = []

    def fail(self, message):
        self.errors.append(f'{self.stem}: {message}')

    # ---- primitives -------------------------------------------------------
    def text(self, x, y, value, size=BODY, style='r', align='left', maxw=None):
        value = str(value)
        if maxw is not None and sw(value, style, size) > maxw + 0.01:
            self.fail(f'"{value}" is {sw(value, style, size):.1f} pt, wider than {maxw:.1f} pt')
        self.ops.append(('text', x, y, value, size, style, align))

    def paragraph(self, x, y, value, width, size=BODY, leading=None, style='r',
                  align='left'):
        """Wrap on words; a single word wider than the column raises."""
        leading = leading or round(size * 1.22, 1)
        for hardline in str(value).split('\n'):
            line = ''
            for word in hardline.split():
                if sw(word, style, size) > width + 0.01:
                    self.fail(f'word "{word}" wider than {width:.1f} pt')
                candidate = (line + ' ' + word).strip()
                if sw(candidate, style, size) > width + 0.01 and line:
                    self._put(x, y, line, size, style, align, width)
                    y += leading
                    line = word
                else:
                    line = candidate
            self._put(x, y, line, size, style, align, width)
            y += leading
        return y

    def _put(self, x, y, line, size, style, align, width):
        if align == 'center':
            self.ops.append(('text', x + width / 2, y, line, size, style, 'center'))
        else:
            self.ops.append(('text', x, y, line, size, style, 'left'))

    def rect(self, x, y, w, h, fill='white', radius=0, dashed=False):
        self.ops.append(('rect', x, y, w, h, fill, radius, dashed))

    def mask(self, x, y, w, h):
        self.ops.append(('mask', x, y, w, h))

    def ellipse(self, x, y, w, h, fill='white'):
        self.ops.append(('ellipse', x, y, w, h, fill))

    def polygon(self, points, fill='white'):
        self.ops.append(('polygon', points, fill))

    def line(self, points, dashed=False, end=None, width=0.7, gray=0.12):
        self.ops.append(('line', points, dashed, end, width, gray))

    # ---- compound shapes --------------------------------------------------
    def box(self, x, y, w, h, title, lines=(), kind='', title_size=TITLE,
            line_size=BODY, leading=None, radius=0, sep=True, title_style='b'):
        """Rectangle with a centred title and optional wrapped lines.

        Each line is a string or a (string, size) pair. Content that does not
        fit in h raises, so no figure is produced with overflowing text."""
        self.rect(x, y, w, h, radius=radius)
        inner = w - 12
        if kind:
            self.text(x + w / 2, y + 10, kind, SECOND, 'r', 'center', maxw=inner)
            ty = y + 22
        else:
            ty = y + 14
        for k, t in enumerate(title.split('\n')):
            self.text(x + w / 2, ty + k * (title_size + 2), t, title_size, title_style,
                      'center', maxw=inner)
        ty += (title.count('\n')) * (title_size + 2)
        bottom = ty + 3
        if lines:
            yy = ty + 5
            if sep:
                self.line([(x, yy), (x + w, yy)])
            yy += 11
            for item in lines:
                if isinstance(item, (int, float)):
                    yy += item          # vertical gap between paragraphs
                    continue
                if item == '---':
                    self.line([(x, yy - 7.5), (x + w, yy - 7.5)])
                    yy += 3
                    continue
                t, s = (item, line_size) if isinstance(item, str) else item
                ld = leading or round(s * 1.22, 1)
                yy = self.paragraph(x + 6, yy, t, inner, size=s, leading=ld)
            bottom = yy - ld + 3
        if bottom > y + h + 0.01:
            self.fail(f'box "{title}" needs {bottom - y:.0f} pt, has {h:.0f}')

    def action(self, x, y, w, h, title, lines=(), size=TITLE):
        """Activity action: rounded rectangle, regular weight, centred text."""
        self.rect(x, y, w, h, radius=7)
        inner = w - 12
        rows = [(t, size) for t in title.split('\n')]
        rows += [(it, SECOND) if isinstance(it, str) else it for it in lines]
        total = sum(s * 1.2 for _, s in rows)
        yy = y + (h - total) / 2 + rows[0][1] * 0.95
        for t, s in rows:
            self.text(x + w / 2, yy, t, s, 'r', 'center', maxw=inner)
            yy += s * 1.2
        if yy - rows[-1][1] * 1.2 + 3 > y + h:
            self.fail(f'action "{title}" overflows')

    def actor(self, x, y, name):
        self.ellipse(x - 5, y, 10, 10)
        self.line([(x, y + 10), (x, y + 30)])
        self.line([(x - 10, y + 18), (x + 10, y + 18)])
        self.line([(x - 9, y + 42), (x, y + 30), (x + 9, y + 42)])
        self.text(x, y + 56, name, BODY, align='center')

    def note(self, x, y, w, text, size=LEGEND):
        start = len(self.ops)
        bottom = self.paragraph(x + 7, y + 14, text, w - 17, size=size)
        texts = self.ops[start:]
        del self.ops[start:]
        h = bottom - y - 2
        self.polygon([(x, y), (x + w - 8, y), (x + w, y + 8), (x + w, y + h), (x, y + h)])
        self.line([(x + w - 8, y), (x + w - 8, y + 8), (x + w, y + 8)])
        self.ops.extend(texts)
        return y + h

    def legend(self, text, y):
        self.line([(8, y - 8), (W - 8, y - 8)])
        return self.paragraph(8, y + 2, text, W - 16, size=LEGEND, leading=10.5)

    def label(self, x, y, text, size=BODY, align='left', maxw=None):
        """One or more short label lines (split on newline), no wrapping."""
        for k, t in enumerate(text.split('\n')):
            self.text(x, y + k * (size + 1.5), t, size, 'r', align, maxw=maxw)

    def frame_tab(self, x, y, w, h, name, guard=None, fill='white'):
        """Combined-fragment style frame: rectangle with a name tab.

        fill=None leaves the frame transparent (alt, loop: the lifelines they
        cover stay visible); 'white' makes it opaque (ref hides the lifeline)."""
        self.rect(x, y, w, h, fill=fill)
        tw = sw(name, 'b', SECOND) + 10
        self.polygon([(x, y), (x + tw, y), (x + tw, y + 10), (x + tw - 5, y + 15),
                      (x, y + 15)])
        self.text(x + 5, y + 11, name, SECOND, 'b')
        if guard:
            self.text(x + tw + 6, y + 11, guard, SECOND)

    # ---- rendering ----------------------------------------------------------
    @staticmethod
    def arrow_points(points, end):
        x, y = points[-1]
        px, py = points[-2]
        a = math.atan2(y - py, x - px)
        ux, uy = math.cos(a), math.sin(a)
        if end == 'diamond':
            return [(x, y), (x - 5 * ux + 3 * uy, y - 5 * uy - 3 * ux),
                    (x - 10 * ux, y - 10 * uy), (x - 5 * ux - 3 * uy, y - 5 * uy + 3 * ux)]
        if end == 'triangle':
            return [(x - 9 * ux + 5 * uy, y - 9 * uy - 5 * ux), (x, y),
                    (x - 9 * ux - 5 * uy, y - 9 * uy + 5 * ux)]
        return [(x - 7 * ux + 3 * uy, y - 7 * uy - 3 * ux), (x, y),
                (x - 7 * ux - 3 * uy, y - 7 * uy + 3 * ux)]

    def render(self, c, ox=0, oy=0):
        H = self.height

        def xy(x, y):
            return ox + x, oy + H - y
        for op in self.ops:
            tag = op[0]
            c.setLineWidth(.7)
            c.setStrokeColorRGB(.12, .12, .12)
            c.setFillColorRGB(0, 0, 0)
            c.setDash()
            if tag == 'text':
                _, x, y, t, size, style, align = op
                c.setFont(FONT[style], size)
                fn = {'left': c.drawString, 'center': c.drawCentredString,
                      'right': c.drawRightString}[align]
                fn(*xy(x, y), t)
            elif tag == 'rect':
                _, x, y, w, h, fill, radius, dashed = op
                c.setFillColorRGB(*((.93, .93, .93) if fill == 'shade' else (1, 1, 1)))
                if dashed:
                    c.setDash(3, 2)
                xx, yy = xy(x, y + h)
                f = 0 if fill is None else 1
                if radius:
                    c.roundRect(xx, yy, w, h, radius, stroke=1, fill=f)
                else:
                    c.rect(xx, yy, w, h, stroke=1, fill=f)
            elif tag == 'mask':
                _, x, y, w, h = op
                c.setFillColorRGB(1, 1, 1)
                xx, yy = xy(x, y + h)
                c.rect(xx, yy, w, h, stroke=0, fill=1)
            elif tag == 'ellipse':
                _, x, y, w, h, fill = op
                c.setFillColorRGB(*((0, 0, 0) if fill == 'black' else (1, 1, 1)))
                c.ellipse(*xy(x, y + h), *xy(x + w, y), stroke=1, fill=1)
            elif tag == 'polygon':
                _, points, fill = op
                c.setFillColorRGB(*((0, 0, 0) if fill == 'black' else
                                    (.93, .93, .93) if fill == 'shade' else (1, 1, 1)))
                p = c.beginPath()
                p.moveTo(*xy(*points[0]))
                for v in points[1:]:
                    p.lineTo(*xy(*v))
                p.close()
                c.drawPath(p, stroke=1, fill=1)
            elif tag == 'line':
                _, points, dashed, end, width, gray = op
                c.setLineWidth(width)
                c.setStrokeColorRGB(gray, gray, gray)
                if dashed:
                    c.setDash(3, 2)
                p = c.beginPath()
                p.moveTo(*xy(*points[0]))
                for v in points[1:]:
                    p.lineTo(*xy(*v))
                c.drawPath(p)
                if end:
                    c.setDash()
                    c.setLineWidth(.7)
                    c.setStrokeColorRGB(.12, .12, .12)
                    vs = self.arrow_points(points, end)
                    p = c.beginPath()
                    p.moveTo(*xy(*vs[0]))
                    for v in vs[1:]:
                        p.lineTo(*xy(*v))
                    if end in ('filled', 'triangle', 'diamond'):
                        p.close()
                        c.setFillColorRGB(*((1, 1, 1) if end == 'triangle' else (0, 0, 0)))
                        c.drawPath(p, stroke=1, fill=1)
                    else:
                        c.drawPath(p, stroke=1, fill=0)

    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="135mm" '
               f'height="{self.height / MM:.3f}mm" viewBox="0 0 {W:.3f} {self.height}">',
               '<rect width="100%" height="100%" fill="white"/>',
               f'<title>{escape(self.number)}</title>', f'<desc>{escape(self.caption)}</desc>']
        for op in self.ops:
            tag = op[0]
            if tag == 'text':
                _, x, y, t, size, style, align = op
                anchor = dict(left='start', center='middle', right='end')[align]
                weight = 700 if style == 'b' else 400
                fs = ' font-style="italic"' if style == 'i' else ''
                out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{SVG_FAMILY}" '
                           f'font-size="{size}" font-weight="{weight}"{fs} '
                           f'text-anchor="{anchor}">{escape(t)}</text>')
            elif tag == 'rect':
                _, x, y, w, h, fill, r, dash = op
                fc = '#ededed' if fill == 'shade' else 'none' if fill is None else 'white'
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
                           f'fill="{fc}" '
                           f'stroke="#202020" stroke-width=".7"'
                           + (' stroke-dasharray="3 2"' if dash else '') + '/>')
            elif tag == 'mask':
                _, x, y, w, h = op
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white"/>')
            elif tag == 'ellipse':
                _, x, y, w, h, fill = op
                out.append(f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" '
                           f'fill="{"black" if fill == "black" else "white"}" '
                           f'stroke="#202020" stroke-width=".7"/>')
            elif tag == 'polygon':
                _, points, fill = op
                col = 'black' if fill == 'black' else '#ededed' if fill == 'shade' else 'white'
                out.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}" '
                           f'fill="{col}" stroke="#202020" stroke-width=".7"/>')
            elif tag == 'line':
                _, points, dash, end, width, gray = op
                col = f'rgb({int(gray * 255)},{int(gray * 255)},{int(gray * 255)})'
                out.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in points)}" '
                           f'fill="none" stroke="{col}" stroke-width="{width}"'
                           + (' stroke-dasharray="3 2"' if dash else '') + '/>')
                if end:
                    vs = self.arrow_points(points, end)
                    closed = end in ('filled', 'triangle', 'diamond')
                    fillc = 'black' if end in ('filled', 'diamond') else 'white' if closed else 'none'
                    out.append(f'<{"polygon" if closed else "polyline"} '
                               f'points="{" ".join(f"{x},{y}" for x, y in vs)}" '
                               f'fill="{fillc}" stroke="#202020" stroke-width=".7"/>')
        out.append('</svg>')
        return '\n'.join(out) + '\n'

    def save(self):
        if self.errors:
            raise ValueError(chr(10).join(self.errors))
        (ROOT / (self.stem + '.svg')).write_text(self.svg(), encoding='utf-8')
        c = canvas.Canvas(str(ROOT / (self.stem + '.pdf')), pagesize=(W, self.height),
                          initialFontName='Pala')
        c.setTitle(self.number)
        c.setAuthor('Roberto Nieves / figuras E2')
        self.render(c)
        c.showPage()
        c.save()
        (ROOT / (self.stem + '.caption.txt')).write_text(
            self.caption + '\n\n' + self.key + '\n', encoding='utf-8')
        FIGURES.append(self)


def flow(d, points, label=None, at=None, align='left', size=BODY):
    """Information flow: dashed line, open head, one operative label."""
    d.line(points, True, 'open')
    if label:
        d.label(at[0], at[1], label, size, align)


# =============================================================================
# F1  Contexto y alcance del instrumento
# =============================================================================
def f1():
    d = Fig('F1-contexto', 320,
            'Contexto lógico del instrumento de investigación y sus entradas externas. '
            'Ruta común verificada: portal R, ejecutables y comprobación de archivos.',
            'Flecha discontinua: flujo de información. LL: log-verosimilitud.',
            'F1', '¿Quién usa el instrumento y qué intercambia con su entorno?',
            'El portal R conecta preparación, motores y verificación con fuentes y referencia.')
    d.box(8, 10, 160, 42, 'Fuentes de paneles', ['repositorios de votaciones nominales'],
          kind='«actor»', line_size=SECOND)
    d.box(215, 10, 160, 42, 'Servicio de semillas', ['W-NOMINATE en R'],
          kind='«actor»', line_size=SECOND)
    # red team 2, N-2: only accepted runs are stamped (dwnom.R:380-391 stop before,
    # :436 RUN-STAMP after)
    d.box(112, 96, 150, 172, 'Instrumento DW-NOMINATE',
          ['ámbito lógico de investigación', 5,
           'preparación, motores C++ y verificación', 5,
           'portal R invoca ejecutables; valida archivos y sella corridas aceptadas'],
          kind='«component»', line_size=SECOND, sep=False)
    d.box(284, 148, 92, 64, 'Referencia wmay', ['Fortran; evaluador común'],
          kind='«actor»', line_size=SECOND)
    d.actor(26, 96, 'Analista')
    d.actor(26, 214, 'Verificador')
    # external sources and seeds
    flow(d, [(88, 52), (88, 78), (136, 78), (136, 96)], 'entrega panel', (93, 74))
    flow(d, [(226, 96), (226, 52)], 'envía votos', (221, 76), 'right')
    flow(d, [(248, 52), (248, 96)], 'devuelve semillas', (253, 76))
    # analyst: the engine (and lineage) is a caller choice of the portal
    flow(d, [(44, 126), (112, 126)], 'declara panel,\nsemillas\ny motor', (48, 99))
    # red team 2, N-2: the portal returns coordinates and bill parameters (dwnom.R:439-442)
    flow(d, [(112, 160), (44, 160)], 'devuelve\ncoordenadas\ny parámetros', (48, 172))
    # verifier
    flow(d, [(44, 236), (112, 236)], 'solicita\ncomparación', (48, 219))
    flow(d, [(112, 258), (44, 258)], 'devuelve\ncomparación', (56, 270))
    # reference
    flow(d, [(262, 126), (330, 126), (330, 148)])
    flow(d, [(330, 212), (330, 270), (262, 270)])
    d.paragraph(284, 91, 'panel, semillas o estado', 92, size=BODY, leading=10.5)
    d.paragraph(276, 235, 'coordenadas o LL', 48, size=8.2, leading=10.5)
    d.legend('Flecha discontinua: flujo de información. LL: log-verosimilitud.', 303)
    d.save()


# =============================================================================
# F2  Objetivos de los usuarios (casos de uso)
# =============================================================================
def f2():
    d = Fig('F2-casos-de-uso', 447,
            'Objetivos dentro del instrumento de investigación: estimación, validación chilena '
            'y comparación. Los roles pueden ser ejercidos por la misma persona.',
            'UML casos de uso: participación, especialización e inclusión.',
            'F2', '¿Qué metas cubre el instrumento de investigación?',
            'Estimación y validación pertenecen al sujeto, aunque involucren varios scripts.')
    SX, SW_ = 110, 266
    d.rect(SX, 10, SW_, 394)
    d.text(SX + SW_ / 2, 25, 'Instrumento de investigación DW-NOMINATE', TITLE, 'b', 'center')
    d.text(SX + SW_ / 2, 37, 'estimación, validación y comparación', BODY, align='center')
    d.actor(30, 112, 'Analista')
    d.actor(30, 318, 'Verificador')

    def case(x, y, w, h, title, rf, extra=None, italic=False):
        d.ellipse(x, y, w, h)
        mid = y + h / 2
        style = 'i' if italic else 'r'
        if extra:
            d.text(x + w / 2, mid - 5, title, TITLE, style, 'center', maxw=w - 20)
            d.text(x + w / 2, mid + 6, rf, SECOND, 'r', 'center', maxw=w - 20)
            d.text(x + w / 2, mid + 16, extra, SECOND, 'r', 'center', maxw=w - 20)
        else:
            d.text(x + w / 2, mid - 1, title, TITLE, style, 'center', maxw=w - 20)
            d.text(x + w / 2, mid + 10, rf, SECOND, 'r', 'center', maxw=w - 20)
    # red team 2, N-12: RF01 (ingesta y validación) happens inside the estimation, as
    # the caption says, so it is listed there and not under the declaration
    case(158, 44, 170, 40, 'Declarar panel y semillas', 'RF02')
    case(153, 108, 180, 56, 'Estimar posiciones', 'RF01, RF03 a RF07',
         'con motor fiel o moderno (RF05, RF06)', italic=True)
    case(127, 190, 112, 38, 'Estimar estático', 'RF03')
    case(247, 190, 112, 38, 'Estimar dinámico', 'RF04')
    case(133, 262, 210, 48, 'Validar con el caso chileno', 'RF10 a RF12',
         'flujo de investigación')
    case(158, 340, 170, 48, 'Verificar y comparar', 'RF08, RF09',
         'contra la referencia wmay')
    # specialisation
    d.line([(183, 190), (183, 172), (219, 172), (219, 163)], False, 'triangle')
    d.line([(303, 190), (303, 172), (267, 172), (267, 163)], False, 'triangle')
    # inclusion: validation reuses estimation (bootstrap refits any model)
    d.line([(343, 286), (368, 286), (368, 136), (333, 136)], True, 'open')
    d.text(364, 250, '«include»', SECOND, 'r', 'right')
    # participation
    d.line([(44, 120), (158, 62)])
    d.line([(44, 128), (153, 136)])
    d.line([(44, 138), (62, 138), (62, 286), (133, 286)])
    d.line([(44, 326), (158, 364)])
    d.legend('Línea: participación. Triángulo hueco: especialización. Cursiva: caso abstracto. '
             '«include»: inclusión. RF: requisito funcional.', 420)
    d.save()


# =============================================================================
# F3  Del Fortran al C++: organización
# =============================================================================
def f3():
    d = Fig('F3-fortran-a-cpp', 421,
            'Correspondencia de responsabilidades entre los dos antecedentes Fortran y el '
            'motor fiel C++. Catálogo de rutinas y variantes en el anexo de correspondencia.',
            'Línea horizontal: correspondencia de responsabilidad; no es dependencia UML.',
            'F3', '¿Dónde quedó cada responsabilidad del instrumento heredado?',
            'Se preservan responsabilidades numéricas; se explicitan entrada, configuración y estado.')
    lx, rx, bw = 8, 205, 170
    d.text(W/2, 14, 'Correspondencia de responsabilidades', TITLE, 'b', 'center')
    d.text(lx+bw/2, 35, 'Antecedentes Fortran', TITLE, 'b', 'center')
    d.text(rx+bw/2, 35, 'Motor fiel C++', TITLE, 'b', 'center')
    rows = [
        ('Entrada y ejecución', ['2004: programa con archivos', 'wmay: dwnom y envoltorio R/CLI'],
         'Entrada y orquestación', ['CLI y CSVLoader; ciclo en DWNominate']),
        ('Configuración y estado', ['2004: COMMON; wmay: módulos', 'parámetros y arreglos compartidos'],
         'Configuración y estado', ['DWNominateConfig explícita', 'estado retenido en DWNominate']),
        ('Búsquedas de parámetros', ['WINT, SIGMAS, RCINT2, XINT', 'GRID: presente solo en 2004'],
         'Búsquedas fieles', ['escalares, votaciones y legisladores', 'GRID con interruptor de linaje']),
        ('Geometría de cortes', ['CUTPLANE, SEARCH, JAN11PT', '2004: LSVRR; wmay: DGESDD'],
         'Geometría de cortes', ['cutting_plane, cutting_point', 'DGESDD en el perfil comparado']),
        ('Verosimilitud', ['PLOG; derivadas PROLLC2, PROX'],
         'Verosimilitud y derivadas', ['likelihood; módulos de derivadas']),
        ('Soporte numérico', ['RSORT, REGA; normal tabulada'],
         'Soporte numérico', ['sort_utils, simple_ols, normal_cdf']),
    ]
    for k, (lt, ll, rt, rr) in enumerate(rows):
        y = 48 + 56*k
        d.box(lx, y, bw, 48, lt, ll, line_size=SECOND, leading=10)
        d.box(rx, y, bw, 48, rt, rr, line_size=SECOND, leading=10)
        d.line([(lx+bw, y+24), (rx, y+24)], width=1.8, gray=.5)
    d.legend('Línea horizontal: correspondencia de responsabilidad. Las dependencias de módulos '
             'y la propiedad del estado se documentan por separado en el anexo.', 396)
    d.save()


# =============================================================================
# F4  Ciclo de estimación compartido
# =============================================================================
def f4():
    d = Fig('F4-ciclo-estimacion', 482,
            'Ciclo de estimación compartido por wmay y el motor fiel. Cada ciclo ajusta los '
            'parámetros globales, actualiza las posiciones de las votaciones, evalúa la '
            'verosimilitud, actualiza las posiciones de los legisladores y vuelve a evaluar; '
            'el número de ciclos es fijo y no hay prueba de convergencia. El estado terminal es '
            'el conjunto de parámetros al terminar el último ciclo. El resumen fiel mezcla '
            'la LL terminal con clasificación de la fase previa (M-02, pendiente de I2). Compartir este flujo no '
            'garantiza cifras iguales entre implementaciones. Perfil de la vista: dos '
            'dimensiones y cuatro ciclos.',
            'Clave de notación: UML actividad; rectángulo redondeado, acción; rombo, unión o '
            'decisión; círculo lleno, inicio; círculo con anillo, fin. Nombres de rutinas '
            'Fortran en tipo menor.',
            'F4', '¿Qué hace un ciclo y en qué orden modifica el estado?',
            'Un ciclo actualiza bloques de parámetros en un orden fijo y vuelve a evaluar la '
            'verosimilitud; compartir este flujo no garantiza cifras iguales.')
    cx = W / 2
    bx, bw = 60, 263
    AH, STEP = 36, 46        # action height and pitch (compacted 2026-10-08: 182 -> 170 mm)
    d.ellipse(cx - 4, 6, 8, 8, 'black')
    d.line([(cx, 14), (cx, 22)], False, 'filled')
    d.action(bx, 22, bw, AH, 'Cargar panel y semillas; inicializar el estado',
             ['marcar las votaciones válidas; ciclo := 1'])
    d.line([(cx, 22 + AH), (cx, 66)], False, 'filled')
    d.polygon([(cx, 66), (cx + 7, 71), (cx, 76), (cx - 7, 71)])
    steps = [('Ajustar los parámetros globales',
              'peso de la segunda dimensión y beta: WINT, SIGMAS'),
             ('Actualizar las posiciones de las votaciones',
              'corte: CUTPLANE (2D) o JAN11PT (1D); búsqueda: RCINT2'),
             ('Evaluar la verosimilitud', 'PLOG'),
             ('Actualizar las posiciones de los legisladores',
              'trayectoria en tiempo servido: XINT'),
             ('Evaluar la verosimilitud', 'PLOG; ciclo := ciclo + 1')]
    prev = 76
    y = 86
    for title, sub in steps:
        d.line([(cx, prev), (cx, y)], False, 'filled')
        d.action(bx, y, bw, AH, title, [sub])
        prev = y + AH
        y += STEP
    dy = prev + 12           # decision diamond top
    d.line([(cx, prev), (cx, dy)], False, 'filled')
    d.polygon([(cx, dy), (cx + 44, dy + 18), (cx, dy + 36), (cx - 44, dy + 18)])
    d.text(cx, dy + 21, '¿ciclo ≤ T?', BODY, align='center')
    d.line([(cx - 44, dy + 18), (30, dy + 18), (30, 71), (cx - 7, 71)], False, 'filled')
    d.text(36, dy + 11, '[sí]', BODY)
    ey = dy + 50             # export action top
    d.line([(cx, dy + 36), (cx, ey)], False, 'filled')
    d.text(cx + 8, dy + 46, '[no]', BODY)
    d.action(bx, ey, bw, 34, 'Exportar parámetros terminales',
             ['y resumen (fiel: estado mixto, M-02)'])
    d.line([(cx, ey + 34), (cx, ey + 44)], False, 'filled')
    d.ellipse(cx - 6, ey + 44, 12, 12)
    d.ellipse(cx - 3.5, ey + 46.5, 7, 7, 'black')
    d.legend('wmay / fiel en modo wmay: 2D, T = 4, sin parada por convergencia. '
             'Rutinas en tipo menor; el alcance 1D se documenta en el perfil de ejecución.', ey + 72)
    d.save()


# =============================================================================
# F5  Intervención moderna
# =============================================================================
def t5():
    d = Fig('T5-mecanismos-modernos', 336,
            'Mecanismos de búsqueda fieles y modernos en el perfil controlado. '
            'La tabla separa implementación y restricciones de los controles de medición.',
            'Tabla de mecanismos; no usa relaciones UML.',
            'T5', '¿Qué búsqueda cambia en cada actualización?',
            'BOBYQA escalar y COBYLA de bloques sustituyen búsquedas heredadas con restricciones explícitas.')
    d.text(W/2, 15, 'Mecanismos: fiel y moderno', TITLE, 'b', 'center')
    d.text(W/2, 29, 'Perfil: replicación Fortran, precisión estricta, escalar local, COBYLA', SECOND, align='center')
    xs = [6, 59, 147, 222, 310, W-6]
    widths = [xs[i+1]-xs[i] for i in range(5)]
    headers = ['Parámetro', 'Fiel', 'Moderno', 'Restricción', 'Activo']
    data = [
        ['Peso de la segunda dimensión', 'Rejilla WINT', 'BOBYQA escalar', 'Intervalo local de WINT; solo en 2D', 'Local'],
        ['Beta', 'Rejilla SIGMAS', 'BOBYQA escalar', 'Intervalo local de SIGMAS', 'Local'],
        ['Votación', 'Búsqueda por término RCINT2', 'COBYLA de bloque', 'Norma del punto medio ≤ 1', 'COBYLA'],
        ['Legislador', 'Búsqueda por término XINT', 'COBYLA de bloque', 'Norma del término constante ≤ 1', 'COBYLA'],
    ]
    y=43
    for row, h, bold in [(headers, 35, True)] + [(r, 54, False) for r in data]:
        for i, cell in enumerate(row):
            d.rect(xs[i], y, widths[i], h, fill='shade' if bold else 'white')
            bottom=d.paragraph(xs[i]+4, y+14, cell, widths[i]-8,
                               size=SECOND if bold else BODY, leading=11, style='b' if bold else 'r')
            if bottom-11+3 > y+h: d.fail('Table cell too tall: '+cell)
        y+=h
    d.paragraph(6, y+16, 'Opcionales fuera del perfil: escalar global; bloques SLSQP o híbridos. '
                'Las cotas globales de peso y beta se retiran en replicación; persiste el intervalo local.',
                W-12, size=LEGEND, leading=10.5)
    d.save()


# =============================================================================
# F6  Datos y tiempo servido
# =============================================================================
def f6():
    d = Fig('F6-datos-tiempo-servido', 480,
            'Modelo conceptual de los datos y del tiempo servido. Un legislador tiene una fila '
            'por periodo servido; cada fila contiene las celdas de voto de las votaciones '
            'válidas de ese periodo. La semilla por legislador y la semilla por fila son '
            'contratos distintos. Cada legislador con al menos un periodo servido tiene una '
            'trayectoria, que se evalúa solo en los periodos servidos con un tiempo local que '
            'recorre ese intervalo; el término lineal exige al menos cinco periodos servidos '
            '(el cuadrático seis y el cúbico siete) y con menos el modelo efectivo es '
            'constante. Es un modelo conceptual, no una base de datos.',
            'Clave de notación: diagrama de clases UML, nivel conceptual; línea continua con '
            'multiplicidades, asociación; atributo con barra, derivado; flecha discontinua '
            '«Derive», derivación. Archivos, columnas y la variante de signos corregidos '
            'están en el cuadro de contratos del anexo.',
            'F6', '¿Qué significa cada fila y cómo se reconstruyen sus coordenadas?',
            'Un legislador tiene varias filas servidas; cada fila contiene varias celdas de '
            'voto y sus coordenadas se evalúan sobre los periodos efectivamente servidos.')
    # Columns shifted 2026-10-08 so the Fila servida - Semilla por fila gap is
    # 28 pt and its two multiplicities no longer overlap horizontally.
    L, LW = 4, 118     # left column: seed per legislator, Legislador, Trayectoria
    C, CW = 158, 88    # centre column: Fila servida, Celda de voto (Panel is wider)
    R, RW = 274, 104   # right column: Periodo, seed per row, Votación
    PW = 94            # Panel width ("periodos, votaciones" needs 82 pt)
    VX = 372           # Periodo - Votación association, right of Semilla por fila
    d.box(L, 10, LW, 46, 'Semilla por legislador', ['una coordenada inicial por legislador'])
    d.box(C, 10, PW, 38, 'Panel', ['periodos, votaciones'])
    d.box(L, 80, LW, 38, 'Legislador', ['identificador único'])
    d.box(R, 72, RW, 38, 'Periodo', ['índice en el panel'])
    d.box(L, 142, LW, 58, 'Trayectoria',
          ['coeficientes por legislador', 'evaluada en los periodos servidos'])
    d.box(C, 142, CW, 66, 'Fila servida',
          ['legislador, periodo', '/ tiempo local', '/ coordenadas'])
    d.box(R, 142, 90, 60, 'Semilla por fila', ['por legislador y periodo; opcional'])
    d.box(C, 232, CW, 58, 'Celda de voto', ['fila y votación', 'sí, no o ausente'])
    d.box(R, 232, RW, 58, 'Votación', ['periodo y columna', 'válida: margen de la minoría ≥ 2,5 %'])
    # associations
    d.line([(176, 48), (176, 88), (L + LW, 88)])                    # Panel 1 - * Legislador
    d.text(180, 60, '1', BODY); d.text(L + LW + 4, 85, '*', BODY)
    d.line([(C + PW, 29), (324, 29), (324, 72)])                    # Panel 1 - * Periodo
    d.text(C + PW + 4, 26, '1', BODY); d.text(320, 69, '*', BODY, align='right')
    d.line([(L + LW, 108), (196, 108), (196, 142)])                 # Legislador 1 - * Fila
    d.text(L + LW + 4, 105, '1', BODY); d.text(200, 139, '*', BODY)
    d.line([(R, 92), (232, 92), (232, 142)])                        # Periodo 1 - * Fila
    d.text(R - 4, 89, '1', BODY, align='right'); d.text(228, 139, '*', BODY, align='right')
    d.line([(62, 56), (62, 80)])                                    # Semilla 0..1 - 1 Legislador
    d.text(66, 66, '0..1', BODY); d.text(66, 77, '1', BODY)
    d.line([(62, 118), (62, 142)])                                  # Legislador 1 - 0..1 Trayectoria
    d.text(66, 128, '1', BODY); d.text(66, 139, '0..1', BODY)
    d.line([(VX, 110), (VX, 232)])                                  # Periodo 1 - * Votación
    d.text(VX - 4, 120, '1', BODY, align='right'); d.text(VX - 4, 229, '*', BODY, align='right')
    d.line([(208, 208), (208, 232)])                                # Fila 1 - * Celda
    d.text(212, 217, '1', BODY); d.text(212, 229, '*', BODY)
    d.line([(R, 257), (C + CW, 257)])                               # Celda * - 1 Votación
    d.text(R - 3, 254, '1', BODY, align='right'); d.text(C + CW + 3, 254, '*', BODY)
    d.line([(C + CW, 172), (R, 172)])                               # Fila 1 - 0..1 Semilla por fila
    d.text(C + CW + 3, 169, '1', BODY); d.text(R - 2, 184, '0..1', BODY, align='right')
    # derived coordinates come from the trajectory and the local time
    d.line([(C, 172), (L + LW, 172)], True, 'open')
    d.text((C + L + LW) / 2, 168, '«Derive»', SECOND, 'r', 'center', maxw=36)
    # worked example: one legislator present in two periods
    d.text(L, 312, 'Ejemplo: un legislador presente en los periodos 2 y 4 de un panel de cinco',
           TITLE, 'b', maxw=W - 12)
    for k in range(5):
        x = 6 + k * 74
        served = k in (1, 3)
        d.rect(x, 322, 70, 24, 'shade' if served else 'white')
        d.text(x + 35, 337, f'periodo {k + 1}', BODY, 'b' if served else 'r', 'center')
        if served:
            d.text(x + 35, 360, 'fila servida', LEGEND, align='center')
            d.text(x + 35, 371, 't = −1' if k == 1 else 't = +1', LEGEND, align='center')
        else:
            d.text(x + 35, 360, 'sin fila', LEGEND, align='center')
            d.text(x + 35, 371, 'no se evalúa', LEGEND, align='center')
    d.paragraph(L, 390, 'Dos filas servidas, (L, 2) y (L, 4), cada una con sus celdas de voto. '
                'El tiempo local recorre solo esos dos periodos; las coordenadas se evalúan y '
                'se exportan en esas dos filas, no en el periodo 3. Modelo efectivo: '
                'constante, porque el término lineal exige al menos 5 periodos servidos '
                '(cuadrático 6, cúbico 7); ambas filas reciben las mismas coordenadas.',
                W - 12, size=LEGEND, leading=10.5)
    d.legend('Línea continua con multiplicidades: asociación (0..1, opcional). Barra inicial: '
             'atributo derivado. Flecha discontinua «Derive»: las coordenadas de la fila se '
             'derivan de la trayectoria y del tiempo local. Archivos, columnas y signos '
             'corregidos en el cuadro de contratos del anexo.', 442)
    d.save()


# =============================================================================
# F7  Proceso de verificación
# =============================================================================
def f7():
    d = Fig('F7-verificacion', 462,
            'Protocolo wmay: puntuación del estado con evaluador común y comparación de mapas. '
            'La cobertura y el marco se declaran con cada medida.',
            'Clave de notación: UML actividad con flujo de objetos; rectángulo redondeado, '
            'acción; rectángulo, objeto de datos; región rotulada (a), (b), partición de '
            'actividad (la pestaña es una marca propia). LL, r1, r2 y amplitud se definen en '
            'el texto; nombres de guiones en tipo menor.',
            'F7', '¿Qué comprobación permite confiar en la reimplementación y qué limita esa '
            'conclusión?',
            'Podemos comparar tanto el estado bajo un evaluador común como las coordenadas de '
            'corridas controladas; ninguna comparación autoriza a confundir original 2004 con '
            'wmay.')
    d.box(8, 10, 367, 50, 'Corridas controladas',
          ['estado terminal del motor C++ y corrida wmay ajustada con el mismo panel, la '
           'misma semilla por legislador y el mismo horizonte de ciclos'], title_style='r')
    d.frame_tab(4, 76, 180, 322, '(a) reevaluar')
    d.frame_tab(199, 76, 180, 322, '(b) comparar')
    ax, aw = 10, 168
    bxx, bw = 205, 168
    d.action(ax, 104, aw, 42, 'Preparar el estado', ['stage_terminal_state.py'])
    d.action(ax, 164, aw, 54, 'Evaluar con la referencia wmay',
             [('sin volver a ajustar: cero ciclos', BODY), 'standalone, modo evaluate'])
    d.box(ax, 236, aw, 40, 'LL del estado C++', ['bajo el evaluador de wmay'], title_style='r')
    d.action(ax, 294, aw, 42, 'Comparar con la LL\nde la corrida wmay',
             ['LL de su resumen: summary.csv'])
    d.box(ax, 354, aw, 38, 'Diferencia de LL', ['bajo evaluador común'], title_style='r')
    d.action(bxx, 104, bw, 78, 'Comparar coordenadas',
             [('emparejar por (legislador, periodo)', BODY),
              ('centrar y alinear sin reescalar', BODY),
              'alineación ortogonal; map_agreement.py'])
    d.box(bxx, 236, bw, 52, 'Medidas de acuerdo',
          ['n emparejados, r1, r2,', 'amplitud y distancia media'], title_style='r')
    d.note(bxx, 306, bw, 'Declarar cobertura por lado y marco global o por periodo. '
           'Claves únicas y cobertura completa: I5, pendiente.')
    for a, b in [((94, 60), (94, 104)), ((94, 146), (94, 164)), ((94, 218), (94, 236)),
                 ((94, 276), (94, 294)), ((94, 336), (94, 354)),
                 ((289, 60), (289, 104)), ((289, 182), (289, 236))]:
        d.line([a, b], False, 'filled')
    d.legend('Rectángulo redondeado: acción. Rectángulo: objeto de datos. Flecha continua: '
             'flujo de objetos. LL: log-verosimilitud; r1 y r2: correlación por dimensión tras '
             'alinear; amplitud: razón de tamaños. Alineación ortogonal: rotación o reflexión, '
             'sin reescalar. Ambas corridas usan la semilla por legislador. El referente de '
             'corridas es wmay, no el original 2004.', 418)
    d.save()


# =============================================================================
# A1  Clases y propiedad del estado del motor fiel
# =============================================================================
def a1():
    d = Fig('A1-clases-estado', 492,
            'Clases y propiedad del estado del motor fiel. CSVLoader crea la entrada; '
            'DWNominate copia de ella lo que necesita en el constructor (votos, coordenadas, '
            'puntos medios y dispersiones) y no retiene el objeto DWNominateInput; posee por '
            'valor la configuración, los metadatos de periodos y la presencia de '
            'legisladores, usa las búsquedas como funciones libres y crea el resultado, que '
            'lleva el estado terminal, al terminar. La CLI construye la configuración y deja '
            'apagados sus tres modos de validación, que fijan un bloque de parámetros para la '
            'verificación por componente (solo el motor moderno los expone como banderas). '
            'use2004GridSafeguard activa la salvaguarda GRID de 2004: encendida por defecto, '
            '--wmay-replication la apaga. Se muestran miembros seleccionados, ordenados por fase.',
            'Clave de notación: UML clases; rombo lleno, composición (propiedad por valor; '
            'multiplicidad en el extremo de la parte); flecha discontinua, dependencia '
            '(«Create», «use»); «Utility», funciones libres agrupadas.',
            'A1', 'Anexo: ¿quién posee cada parte del estado del motor fiel?',
            'DWNominate posee la configuración y el estado numérico, copia de la entrada lo '
            'que necesita sin retener el objeto y crea el resultado.')
    L, LW = 8, 152
    R, RW = 220, 155
    d.box(L, 10, LW, 56, 'CSVLoader',
          ['+ loadInput(periodos, inicialización)', '    : DWNominateInput'])
    d.box(R, 10, RW, 78, 'DWNominateInput',
          ['+ votes : VoteMatrix', '+ legislatorCoords : MatrixXd',
           '+ rollCallMidpoints', '+ rollCallSpreads', '+ congressMetadata'])
    d.line([(L + LW, 36), (R, 36)], True, 'open')
    d.text(190, 31, '«Create»', SECOND, 'r', 'center')
    d.box(L, 96, LW, 94, 'DWNominateConfig',
          ['+ numDimensions, temporalModel', '+ firstIteration, lastIteration',
           '+ marginThreshold', '+ use2004GridSafeguard',
           '+ fixGlobalParams, fixRollCalls,', '+ fixLegislators (validación)'])
    d.box(R, 104, RW, 196, 'DWNominate',
          ['− config_ : DWNominateConfig', '− votes_, weights_',
           '− legislatorCoords_', '− rollCallMidpoints_', '− rollCallSpreads_',
           '− temporalCoefficients_', '− servedPeriodsByLeg_', '---',
           '+ DWNominate(config, input)', '+ run() : DWNominateResult',
           '− executeWeightPhase()', '− executeBetaPhase()',
           '− executeRollCallPhase(ciclo)', '− computeLogLikelihood()',
           '− executeLegislatorPhase()'])
    d.line([(297, 104), (297, 88)], True, 'open')
    d.text(302, 99, '«use»', SECOND)
    # red team 2, N-11: the role name names the part end, so it sits at that end with
    # the multiplicity (multiplicity above the line, role name below), clear of the
    # diamond at the whole end
    d.line([(L + LW, 132), (R, 132)], False, 'diamond')
    d.text(L + LW + 4, 128, '1', SECOND)
    d.text(L + LW + 4, 143, 'config_', SECOND, maxw=R - L - LW - 14)
    d.box(L, 200, LW, 50, 'CongressInfo',
          ['+ numLegislators, numRollCalls', '+ legislatorOffset, rollCallOffset'])
    d.line([(L + LW, 225), (R, 225)], False, 'diamond')
    d.text(L + LW + 4, 221, '*', SECOND)
    d.text(L + LW + 4, 237, 'congressInfo_', SECOND, maxw=R - L - LW - 6)
    d.box(L, 262, 112, 52, 'LegislatorPresence',
          ['+ uniqueId', '+ congressToDataIndex'])
    # composition raised to y = 280 so the «use» dependency below it leaves the
    # DWNominate box clear of the diamond and of the role name
    d.line([(L + 112, 280), (R, 280)], False, 'diamond')
    d.text(L + 116, 276, '*', SECOND)
    d.text(L + 116, 291, 'legislatorPresence_', SECOND, maxw=74)
    d.box(L, 330, LW, 72, 'Búsquedas', kind='«Utility»',
          lines=['optimizeWeight2(), optimizeBeta()', 'optimizeRollCall(...)',
                 'optimizeLegislator(...)'])
    d.line([(R, 297), (200, 297), (200, 372), (L + LW, 372)], True, 'open')
    d.text(196, 350, '«use»', SECOND, 'r', 'right')
    d.box(R, 330, RW, 78, 'DWNominateResult',
          ['+ finalLogLikelihood', '+ temporalCoefficients : map',
           '+ servedPeriodsByLegislator', '+ getCoordinatesAtPeriod(id, periodo)'])
    d.line([(340, 300), (340, 330)], True, 'open')
    d.text(344, 318, '«Create»', SECOND)
    d.legend('Rombo lleno: composición; la parte es un valor propiedad de DWNominate, con la '
             'multiplicidad (sobre la línea) y el nombre de rol (bajo ella) en el extremo de la '
             'parte. Flecha discontinua: dependencia, no propiedad; el constructor copia de la '
             'entrada los votos, las coordenadas y los parámetros de votación, y no la retiene. '
             'El parámetro inicialización de loadInput lleva semillas, beta y W2 (peso de la '
             'segunda dimensión). La CLI construye DWNominateConfig y deja apagados '
             'los modos de validación (fixGlobalParams, fixRollCalls, fixLegislators), que fijan '
             'un bloque. «Utility»: funciones libres agrupadas, no una clase del código.', 424)
    d.save()


# =============================================================================
# A2  Secuencia de una estimación
# =============================================================================
def a2():
    d = Fig('A2-secuencia-estimacion', 510,
            'Secuencia de una estimación con el motor fiel desde el portal R. La CLI carga y '
            'valida las entradas (inicialización: semillas, beta y W2, el peso de la segunda '
            'dimensión), crea el motor con la configuración y los datos, ejecuta los ciclos y '
            'exporta parámetros terminales y un resumen mixto (M-02); si loadInput o run() lanzan una excepción, termina con '
            'código 1 y sin salidas (el constructor y la exportación están fuera de esos '
            'bloques try). El '
            'portal acepta el resultado solo si el código de salida es cero y las coordenadas, '
            'los parámetros y el resumen existen y se pueden leer; no valida su cobertura '
            'completa ni todo su esquema. En la llamada, faithful_mode = "wmay" '
            'añade --wmay-replication (linaje wmay, salvaguarda GRID apagada). El paralelismo '
            'con OpenMP es una capacidad del motor; la corrida comparativa usa un hilo.',
            'Clave de notación: UML secuencia; flecha continua con punta llena, mensaje '
            'síncrono; flecha discontinua, respuesta o creación; marco alt, alternativas; '
            'nota, referencia documental a la actividad interna F4; rectángulo redondeado, estado de '
            'la CLI; X, destrucción de los objetos al terminar el proceso de la CLI.',
            'A2','Anexo: ¿qué ocurre, paso a paso, en una estimación aceptada o rechazada?',
            'El portal ejecuta la CLI, el motor corre los ciclos y el resultado se acepta solo '
            'con salida cero y CSV requeridos legibles; su cobertura completa queda por verificar.')
    # Re-laid out 2026-10-08: every message label fits between its two lifelines;
    # guards sit beside the lifeline of the operand's first event; alt and loop
    # are transparent (the lifelines they cover stay visible) and ref is opaque;
    # the CLI's objects end with a destruction mark when the process exits, so
    # the acceptance fragment and the note cover only the portal lifeline.
    p, c, l, e = 46, 136, 270, 334          # portal, CLI, CSVLoader, DWNominate
    HEAD_Y, HEAD_H = 8, 26
    top = HEAD_Y + HEAD_H
    EH_Y = 127                              # DWNominate head (created)
    X_OBJ = 340                             # loader and engine destroyed
    RET_Y = 356                             # exit code returned to the portal
    A1_TOP, A1_SEP, A1_BOT = 66, 295, 332
    A2_TOP, A2_BOT = 368, 452
    LIFE_END = A2_BOT + 6

    def destroy(x, y):
        d.line([(x - 4.5, y - 4.5), (x + 4.5, y + 4.5)], False, None, 1.0)
        d.line([(x - 4.5, y + 4.5), (x + 4.5, y - 4.5)], False, None, 1.0)

    # 1. heads and lifelines first, so frames and labels are drawn over them
    for x, wd, name in [(p, 60, ':portal R'), (c, 50, ':CLI'), (l, 66, ':CSVLoader')]:
        d.rect(x - wd / 2, HEAD_Y, wd, HEAD_H)
        d.text(x, HEAD_Y + 17, name, BODY, align='center', maxw=wd - 6)
    d.line([(p, top), (p, LIFE_END)], True)
    d.line([(c, top), (c, RET_Y + 6)], True)
    d.line([(l, top), (l, X_OBJ)], True)
    d.line([(e, EH_Y + HEAD_H), (e, X_OBJ)], True)

    def masked(x, y, text, size, right=None):
        d.mask(x - 1.5, y - size * 0.8, sw(text, 'r', size) + 3, size * 1.05)
        d.text(x, y, text, size, maxw=(right - 3 - x) if right else W - 6 - x)

    def msg(x1, x2, y, label, sub=None, reply=False, right=None):
        """Message with its label (and optional 8 pt second line) above the
        arrow, measured against `right` (default: the far lifeline)."""
        d.line([(x1, y), (x2, y)], reply, 'open' if reply else 'filled')
        x, right = min(x1, x2) + 4, right or max(x1, x2)
        masked(x, y - (14 if sub else 4), label, BODY, right)
        if sub:
            masked(x, y - 4, sub, SECOND, right)

    def self_msg(x, y, first, second=None, right=None):
        d.line([(x, y), (x + 14, y), (x + 14, y + 12), (x, y + 12)], False, 'filled')
        masked(x + 20, y + 4, first, BODY, right)
        if second:
            masked(x + 20, y + 14, second, BODY, right)

    msg(p, c, 58, 'ejecuta la CLI', 'system2(exe, args)')
    # one alt covers both failure paths: loadInput (main_cli.cpp:539-547) and
    # run() (main_cli.cpp:579-587) are each wrapped in catch ... return 1. Red team 2
    # (A2-1, N-9a): the guards name exactly those two calls; the constructor (:576)
    # and the exports (:613-630, void) are outside any try
    FX0, FX1 = 8, 376                       # alt frames; nested fragments stay inside
    d.frame_tab(FX0, A1_TOP, FX1 - FX0, A1_BOT - A1_TOP, 'alt', fill=None)
    d.text(c + 6, A1_TOP + 11, '[loadInput y run() sin excepción]', SECOND, maxw=l - c - 10)
    msg(c, l, 104, 'carga y valida las entradas', 'loadInput(periodos, inicialización)')
    msg(l, c, 120, 'entrada validada', reply=True)
    # engine creation: the head sits on the «Create» arrow
    d.rect(e - 37, EH_Y, 74, HEAD_H)
    d.text(e, EH_Y + 17, ':DWNominate', BODY, align='center')
    d.line([(c, EH_Y + 13), (e - 37, EH_Y + 13)], True, 'open')
    masked(c + 4, EH_Y + 9, '«Create»', BODY, l)
    masked(c + 4 + sw('«Create»', 'r', BODY) + 2.5, EH_Y + 9, '(configuración, entrada)',
           SECOND, l)
    msg(c, e, 176, 'ejecuta los ciclos', 'run()', right=l)
    d.note(232, 193, 140, 'Actividad interna: F4. run() ejecuta T ciclos y devuelve el estado '
           'terminal; la carga y construcción inicializan antes.', size=SECOND)
    msg(e, c, 264, 'parámetros terminales', reply=True, right=l)
    self_msg(c, 274, 'exporta parámetros', right=l)
    masked(c + 20, 288, 'y resumen mixto (M-02)', SECOND, l)
    d.line([(FX0, A1_SEP), (FX1, A1_SEP)], True)
    d.text(c + 6, A1_SEP + 11, '[excepción en loadInput o run()]', SECOND,
           maxw=l - c - 10)
    # red team 2, N-9b: no reply inside the alt (the CLI answers the portal's one
    # call once, after the alt); the exception path ends in a state of the CLI
    st = 'termina: código 1, sin salidas'
    stw = sw(st, 'r', BODY) + 12
    d.rect(c - stw / 2, A1_SEP + 16, stw, 16, radius=6)
    d.text(c, A1_SEP + 27.5, st, BODY, align='center')
    # the process ends: its objects are destroyed, then the CLI returns
    destroy(l, X_OBJ)
    destroy(e, X_OBJ)
    msg(c, p, RET_Y, 'código de salida', 'y archivos, si los hay', reply=True)
    destroy(c, RET_Y + 6)
    # acceptance by the portal: only the portal lifeline remains
    A2X1 = 203                              # acceptance alt right edge
    d.frame_tab(FX0, A2_TOP, A2X1 - FX0, A2_BOT - A2_TOP, 'alt', fill=None)
    d.text(p + 6, A2_TOP + 11, '[salida 0; CSV requeridos legibles]', SECOND, maxw=150)
    self_msg(p, A2_TOP + 20, 'acepta: escribe DROPPED y', 'RUN-STAMP; devuelve el estado',
             right=A2X1)
    d.line([(FX0, A2_TOP + 42), (A2X1, A2_TOP + 42)], True)
    d.text(p + 6, A2_TOP + 53, '[otro caso]', SECOND)
    self_msg(p, A2_TOP + 58, 'rechaza: stop; las salidas', 'no se aceptan', right=A2X1)
    # red team 2, N-10: three OpenMP regions (grid_optimizer.cpp:39 ->
    # likelihood.cpp:277, pragmas :330, :338; dwnominate.cpp:762, :1478); the
    # cycle's own likelihood evaluation (dwnominate.cpp:1628 -> likelihood.cpp:115)
    # is serial
    bottom = d.note(A2X1 + 6, A2_TOP, FX1 - A2X1 - 6,
                    'OpenMP en la búsqueda de los parámetros globales (su verosimilitud) y en '
                    'las fases de votaciones y de legisladores; la corrida comparativa fija '
                    'un hilo. El mapa de periodos servidos se escribe en paralelo sin '
                    'sincronizar (P-01, pendiente).')
    if bottom > LIFE_END:
        d.fail(f'parallelism note reaches {bottom:.0f} pt, below {LIFE_END} pt')
    d.legend('Llamada del portal, con argumentos nombrados: dwnom_run(input_dir, engine = '
             '"faithful", faithful_mode = "wmay", engines = <ruta a los binarios>, runs_dir = '
             '<ruta>, panel = "<etiqueta>", model = 0, niter = 4, start = <semillas.csv>). '
             'X: el objeto termina con el proceso de la CLI.', LIFE_END + 18)
    d.save()


# =============================================================================
def review_pdf():
    c = canvas.Canvas(str(ROOT / 'figuras-e2-revision.pdf'), pagesize=A4, initialFontName='Pala')
    c.setTitle('Figuras E2: revisión')
    c.setAuthor('Roberto Nieves / figuras E2')
    margin = 48
    width = A4[0] - 2 * margin

    def wrap(text, size, font='Pala'):
        lines, line = [], ''
        for word in text.split():
            cand = (line + ' ' + word).strip()
            if pdfmetrics.stringWidth(cand, font, size) > width and line:
                lines.append(line)
                line = word
            else:
                line = cand
        lines.append(line)
        return lines
    for i, d in enumerate(FIGURES, 1):
        y = A4[1] - 40
        c.setFont('PalaB', 11)
        c.drawString(margin, y, f'{"Cuadro" if d.number == "T5" else "Figura"} {d.number}')
        y -= 16
        c.setFont('Pala', 9.5)
        for label, text in [('Pregunta', d.question), ('Frase esperada (FIGURAS.md §3)', d.expected)]:
            c.setFont('PalaB', 9.5)
            c.drawString(margin, y, label + ':')
            y -= 12
            c.setFont('Pala', 9.5)
            for line in wrap(text, 9.5):
                c.drawString(margin, y, line)
                y -= 12
            y -= 4
        top = y - 6
        ox = (A4[0] - W) / 2
        c.setStrokeColorRGB(.8, .8, .8)
        c.rect(ox - 1, top - d.height - 1, W + 2, d.height + 2, stroke=1, fill=0)
        d.render(c, ox, top - d.height)
        y = top - d.height - 18
        c.setFont('PalaB', 9)
        c.drawString(margin, y, 'Pie propuesto:')
        y -= 12
        c.setFont('Pala', 9)
        for text in [d.caption, d.key]:
            for line in wrap(text, 9):
                if y < 40:
                    # a long caption (F3 after the 2026-10-08 fixes) continues on
                    # the next page rather than overflowing the A4 sheet
                    c.setFont('Pala', 8)
                    c.drawRightString(A4[0] - margin, 24, f'{i} / {len(FIGURES)}')
                    c.showPage()
                    y = A4[1] - 40
                    c.setFont('PalaB', 9)
                    c.drawString(margin, y, f'Figura {d.number}, pie propuesto (continuación):')
                    y -= 14
                    c.setFont('Pala', 9)
                c.drawString(margin, y, line)
                y -= 11.5
            y -= 4
        c.setFont('Pala', 8)
        c.drawRightString(A4[0] - margin, 24, f'{i} / {len(FIGURES)}')
        c.showPage()
    c.save()


if __name__ == '__main__':
    errors = []
    for build in [f1, f2, f3, f4, t5, f6, f7, a1, a2]:
        try:
            build()
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        for e in errors:
            print('ERROR', e)
        raise SystemExit(1)
    review_pdf()
    manifest = {
        'date': '2026-10-08',
        'width_mm': 135,
        'font': 'Palatino Linotype (C:/Windows/Fonts/pala.ttf, palab.ttf, palai.ttf)',
        'height_pt': {d.stem: d.height for d in FIGURES},
        'pdf_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [ROOT / (d.stem + '.pdf') for d in FIGURES] + [ROOT / 'figuras-e2-revision.pdf']},
        'figures': [d.stem for d in FIGURES if d.number != 'T5'],
        'tables': [d.stem for d in FIGURES if d.number == 'T5'],
        'items': [d.stem for d in FIGURES],
    }
    (ROOT / 'generated-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n',
                                                  encoding='utf-8')
    print('Generated', len(FIGURES), 'figures, the review PDF and the manifest.')
