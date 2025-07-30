"""
Various somewhat-more-heuristic ways of guessing, getting, and
processing text in PDFs.
"""

from dataclasses import dataclass
from os import PathLike
from typing import (
    Iterator,
    List,
    Union,
)

from playa.content import GlyphObject
from playa.document import Document, PageList
from playa.page import Page
from playa.pdftypes import BBOX_NONE, Point, Rect


@dataclass
class Word:
    text: str
    origin: Point
    displacement: Point
    glyphs: List[GlyphObject]

    @property
    def bbox(self) -> Rect:
        return BBOX_NONE


def words(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[Word]:
    """Extract "words" (i.e. whitespace-separated text cells) from a
    PDF or one of its pages.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Yields:
        `Word` objects, which can be visualized with `paves.image`
        functions, or you can do various other things with them too.
    """
    yield from ()
