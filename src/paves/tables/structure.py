"""
Table detection using PDF logical structure.
"""

from functools import singledispatch
from itertools import groupby
from typing import Iterable, Iterator, Union
from operator import attrgetter
from os import PathLike

import playa
from playa import Document, Page, PageList
from playa.structure import (
    Element,
)

from paves.tables.detectors import detector
from paves.tables.table import TableObject


@singledispatch
def table_elements(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[Element]:
    """Iterate over all text objects in a PDF, page, or pages"""
    raise NotImplementedError(f"Not implemented for {type(pdf)}")


@table_elements.register(str)
@table_elements.register(PathLike)
def table_elements_path(pdf: Union[str, PathLike]) -> Iterator[Element]:
    with playa.open(pdf) as doc:
        # NOTE: This *must* be `yield from` or else we will return a
        # useless iterator (as the document will go out of scope)
        yield from table_elements_doc(doc)


@table_elements.register
def table_elements_doc(pdf: Document) -> Iterator[Element]:
    structure = pdf.structure
    if structure is None:
        raise TypeError("Document has no logical structure")
    return structure.find_all("Table")


@table_elements.register
def table_elements_pagelist(pages: PageList) -> Iterator[Element]:
    if pages.doc.structure is None:
        raise TypeError("Document has no logical structure")
    for page in pages:
        yield from table_elements_page(page)


@table_elements.register
def table_elements_page(page: Page) -> Iterator[Element]:
    # page.structure can actually never be None (why?)
    if page.structure is None:
        raise TypeError("Page has no ParentTree")
    if len(page.structure) == 0:
        raise TypeError("Page has no marked content")
    return page.structure.find_all("Table")


def table_elements_to_objects(
    elements: Iterable[Element], page: Union[Page, None] = None
) -> Iterator[TableObject]:
    """Make TableObjects from Elements."""
    for el in elements:
        # It usually has a page, but it can also span multiple pages
        # if this is the case.  So a page passed explicitly here
        # should take precedence.
        for kidpage, kids in groupby(el.contents, attrgetter("page")):
            if kidpage is None:
                continue
            if page is not None and kidpage is not page:
                continue
            table = TableObject.from_element(el, kidpage, kids)
            if table is not None:
                yield table


@detector(priority=0)
def structure(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages using logical structure.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
      An iterator over `TableObject`, or `None`, if there is no
      logical structure (this will cause a TypeError, if you don't
      check for it).
    """
    page = pdf if isinstance(pdf, Page) else None
    try:
        return table_elements_to_objects(table_elements(pdf), page)
    except TypeError:  # means that structure is None
        return None
