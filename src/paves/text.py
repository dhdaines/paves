"""
Various somewhat-more-heuristic ways of guessing, getting, and
processing text in PDFs.
"""

from dataclasses import dataclass
from functools import singledispatch
from os import PathLike
from typing import (
    Iterator,
    List,
    Union,
)

import playa
from playa.content import ContentObject, GlyphObject, TextObject
from playa.document import Document, PageList
from playa.font import Font
from playa.page import Page
from playa.pdftypes import Point


@dataclass
class WordObject(ContentObject):
    _glyphs: List[GlyphObject]
    _next_origin: Point

    @property
    def text(self) -> str:
        return "".join(g.text for g in self._glyphs if g.text is not None)

    @property
    def origin(self) -> Point:
        return self._glyphs[0].origin

    @property
    def displacement(self) -> Point:
        ax, ay = self.origin
        bx, by = self._next_origin
        return bx - ax, by - ay

    @property
    def font(self) -> Font:
        """Initial font for this word.

        If there are multiple fonts in the word (it could happen) then
        you don't get them, so if you care about that, use:

            fonts = [glyph.font for glyph in word]
        """
        return self._glyphs[0].font

    @property
    def fontbase(self) -> str:
        """Original font name for this word.

        Fonts in PDF files are usually "subsetted", meaning only the
        glyphs actually used in the document are included.  In this
        case the font's `fontname` property usually consists of an
        arbitrary "tag", plus (literally, a `+`) and the original
        name.  This is a convenience property to get that original
        name.

        This is not the same as `WordObject.font.basefont` which
        usually also includes the subset tag.

        """
        fontname = self._glyphs[0].font.fontname
        subset, _, base = fontname.partition("+")
        if base:
            return base
        return fontname

    @property
    def size(self) -> float:
        """Initial font size for this word.

        This is the actual font size in device space, which is **not**
        the same as `WordObject.gstate.fontsize`.  That's the font
        size in text space which is not a very useful number (it's
        usually 1).

        If there are multiple fonts in the word (it could happen) then
        you don't get them, so if you care about that, use:

            sizes = [glyph.size for glyph in word]

        """
        return self._glyphs[0].size

    @property
    def textfont(self) -> str:
        """Convenient short form of the font name and size.

        To make labeling simple when using `paves.image`, here's a
        convenience property for you combining `fontbase` and `size`,
        for example, "Helvetica 12".
        """
        return f"{self.fontbase} {round(self.size)}"

    def __iter__(self) -> Iterator["ContentObject"]:
        return iter(self._glyphs)


def word_break(glyph: GlyphObject, origin: Point) -> bool:
    """Heuristically predict a word break based on the predicted origin
    from the previous glyph."""
    if glyph.text == " ":
        return True
    x, y = glyph.origin
    px, py = origin
    if glyph.font.vertical:
        off = y
        poff = py
    else:
        off = x
        poff = px
    return off - poff > 0.5


def line_break(glyph: GlyphObject, origin: Point) -> bool:
    """Heuristically predict a line break based on the predicted origin
    from the previous glyph."""
    x, y = glyph.origin
    px, py = origin
    if glyph.font.vertical:
        line_offset = x - px
    else:
        dy = y - py
        if glyph.page.space == "screen":
            line_offset = -dy
        else:
            line_offset = dy
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
def text_objects_pagelist(pdf: PageList) -> Iterator[TextObject]:
    for page in pdf:
        yield from text_objects_page(page)


@text_objects.register
def text_objects_page(pdf: Page) -> Iterator[TextObject]:
    return pdf.texts


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
    next_origin: Union[None, Point] = None
    for obj in text_objects(pdf):
        for glyph in obj:
            if (
                next_origin is not None
                and glyphs
                and (word_break(glyph, next_origin) or line_break(glyph, next_origin))
            ):
                yield WordObject(
                    _pageref=glyphs[0]._pageref,
                    _parentkey=glyphs[0]._parentkey,
                    gstate=glyphs[0].gstate,  # Not necessarily correct!
                    ctm=glyphs[0].ctm,  # Not necessarily correct!
                    mcstack=glyphs[0].mcstack,  # Not necessarily correct!
                    _glyphs=glyphs, _next_origin=next_origin
                )
                glyphs = []
            if glyph.text is not None and glyph.text != " ":
                glyphs.append(glyph.finalize())
            x, y = glyph.origin
            dx, dy = glyph.displacement
            next_origin = (x + dx, y + dy)
    if next_origin is not None and glyphs:
        yield WordObject(
            _pageref=glyphs[0]._pageref,
            _parentkey=glyphs[0]._parentkey,
            gstate=glyphs[0].gstate,  # Not necessarily correct!
            ctm=glyphs[0].ctm,  # Not necessarily correct!
            mcstack=glyphs[0].mcstack,  # Not necessarily correct!
            _glyphs=glyphs, _next_origin=next_origin
        )
