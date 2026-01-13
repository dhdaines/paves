"""
Various somewhat-more-heuristic ways of guessing, getting, and
processing text in PDFs.
"""

import operator
from dataclasses import dataclass
from functools import singledispatch
from os import PathLike
from typing import Iterator, List, Union, cast

import playa
from playa.content import ContentObject, GlyphObject, TextBase, TextObject
from playa.document import Document, PageList
from playa.page import Page
from playa.pdftypes import Point, Matrix

# For convenience in grouping word/text/glyph objects
line = operator.attrgetter("line")
font = operator.attrgetter("font")
fontname = operator.attrgetter("fontname")
fontbase = operator.attrgetter("fontbase")
size = operator.attrgetter("size")
textfont = operator.attrgetter("textfont")
chars = operator.attrgetter("chars")


@dataclass
class WordObject(TextBase):
    """
    "Word" in a PDF.

    This is heuristically determined, either by explicit whitespace
    (if you're lucky enough to have a Tagged PDF) or by a sufficient
    gap between adjacent glyphs (otherwise).

    It otherwise behaves just like a `TextObject`.  You can iterate
    over its glyphs, etc.  But, as a treat, these glyphs are
    "finalized" so you don't have to worry about inconsistent graphics
    states and so forth, and you also get some convenience properties.

    The origin of the curent (logical) line is also available, to
    facilitate grouping words into lines, if you so desire (simply
    use `itertools.groupby(words, paves.text.line)`)
    """

    _glyphs: List[GlyphObject]
    _next_origin: Point
    line: Point

    def __iter__(self) -> Iterator["ContentObject"]:
        return iter(self._glyphs)

    @property
    def matrix(self) -> Matrix:
        return self._glyphs[0].matrix

    @property
    def chars(self) -> str:
        return "".join(g.text for g in self._glyphs if g.text is not None)

    @property
    def origin(self) -> Point:
        return self._glyphs[0].origin

    @property
    def displacement(self) -> Point:
        ax, ay = self.origin
        bx, by = self._next_origin
        return bx - ax, by - ay


def word_break(
    glyph: GlyphObject, predicted_origin: Point, prev_displacement: Point
) -> bool:
    """Heuristically predict a word break based on the predicted origin
    from the previous glyph."""
    if glyph.text == " ":
        return True
    x, y = glyph.origin
    px, py = predicted_origin
    if glyph.font.vertical:
        glyph_offset = y - py
        _, displacement = prev_displacement
        if glyph.page.space == "screen":
            glyph_offset = -glyph_offset
            displacement = -displacement
    else:
        glyph_offset = x - px
        displacement, _ = prev_displacement
    # If there's a space, *or* if we are before the prev glyph
    return glyph_offset > 0.5 or glyph_offset < -displacement


def line_break(glyph: GlyphObject, predicted_origin: Point) -> bool:
    """Heuristically predict a line break based on the predicted origin
    from the previous glyph."""
    x, y = glyph.origin
    px, py = predicted_origin
    if glyph.font.vertical:
        line_offset = x - px
    else:
        line_offset = y - py
        if glyph.page.space == "screen":
            line_offset = -line_offset
    return line_offset < 0 or line_offset > 100  # FIXME: arbitrary!


@singledispatch
def text_objects(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[TextObject]:
    """Iterate over all text objects in a PDF, page, or pages"""
    raise NotImplementedError


@text_objects.register(str)
@text_objects.register(PathLike)
def text_objects_path(pdf: Union[str, PathLike]) -> Iterator[TextObject]:
    with playa.open(pdf) as doc:
        # NOTE: This *must* be `yield from` or else we will return a
        # useless iterator (as the document will go out of scope)
        yield from text_objects_doc(doc)


@text_objects.register
def text_objects_doc(pdf: Document) -> Iterator[TextObject]:
    return text_objects_pagelist(pdf.pages)


@text_objects.register
def text_objects_pagelist(pagelist: PageList) -> Iterator[TextObject]:
    for page in pagelist:
        yield from text_objects_page(page)


@text_objects.register
def text_objects_page(page: Page) -> Iterator[TextObject]:
    return page.texts


def _add_point(a: Point, b: Point) -> Point:
    return a[0] + b[0], a[1] + b[1]


def words(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[WordObject]:
    """Extract "words" (i.e. whitespace-separated text cells) from a
    PDF or one of its pages.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Yields:
        `WordObject` objects, which can be visualized with `paves.image`
        functions, or you can do various other things with them too.
    """
    glyphs: List[GlyphObject] = []
    predicted_origin: Union[None, Point] = None
    prev_disp: Union[None, Point] = None
    line_origin: Union[None, Point] = None
    for obj in text_objects(pdf):
        for glyph in obj:
            if line_origin is None:
                line_origin = glyph.origin
            if predicted_origin and prev_disp:
                new_word = word_break(glyph, predicted_origin, prev_disp)
                new_line = line_break(glyph, predicted_origin)
                if glyphs and (new_word or new_line):
                    yield WordObject(
                        _pageref=glyphs[0]._pageref,
                        _parentkey=glyphs[0]._parentkey,
                        gstate=glyphs[0].gstate,  # Not necessarily correct!
                        ctm=glyphs[0].ctm,  # Not necessarily correct!
                        mcstack=glyphs[0].mcstack,  # Not necessarily correct!
                        _glyphs=glyphs,
                        _next_origin=predicted_origin,
                        line=line_origin,
                    )
                    glyphs = []
                if new_line:
                    line_origin = glyph.origin
            if glyph.text is not None and glyph.text != " ":
                glyphs.append(cast(GlyphObject, glyph.finalize()))
            prev_disp = glyph.displacement
            predicted_origin = _add_point(glyph.origin, prev_disp)
    if predicted_origin and line_origin and glyphs:
        yield WordObject(
            _pageref=glyphs[0]._pageref,
            _parentkey=glyphs[0]._parentkey,
            gstate=glyphs[0].gstate,  # Not necessarily correct!
            ctm=glyphs[0].ctm,  # Not necessarily correct!
            mcstack=glyphs[0].mcstack,  # Not necessarily correct!
            _glyphs=glyphs,
            _next_origin=predicted_origin,
            line=line_origin,
        )
