"""
Table detection using PDF logical structure.
"""

from copy import copy
from functools import singledispatch
from itertools import groupby
from typing import Iterable, Iterator, Tuple, Union
from operator import attrgetter
from os import PathLike

import playa
from playa import Document, Page, PageList
from playa.content import GraphicState, MarkedContent
from playa.page import Annotation
from playa.pdftypes import Matrix, Rect
from playa.structure import (
    Element,
    ContentItem,
    ContentObject as StructContentObject,
)
from playa.worker import _ref_page

from paves.tables.detectors import detector
from paves.tables.table import TableObject


def _from_element(
    el: Element,
    page: Page,
    contents: Union[Iterable[Union[ContentItem, StructContentObject]], None] = None,
) -> Union["TableObject", None]:
    if contents is None:
        contents = el.contents
    # Find a ContentObject so we can get a bbox, mcstack, ctm
    # (they might not be *correct* of course, but oh well)
    gstate: Union[GraphicState, None] = None
    ctm: Union[Matrix, None] = None
    mcstack: Union[Tuple[MarkedContent, ...], None] = None
    bbox: Union[Rect, None] = None
    for kid in contents:
        # For multi-page tables, skip any contents on a different page
        if kid.page != page:
            continue
        if isinstance(kid, StructContentObject):
            obj = kid.obj
            if obj is None:
                continue
            elif isinstance(obj, Annotation):
                # FIXME: for the moment just ignore these
                continue
            else:
                gstate = copy(obj.gstate)
                ctm = obj.ctm
                mcstack = obj.mcstack
                bbox = obj.bbox
                break
        elif isinstance(kid, ContentItem):
            # It's a ContentItem
            try:
                cobj = next(iter(kid))
            except StopIteration:
                continue
            gstate = copy(cobj.gstate)
            ctm = cobj.ctm
            mcstack = cobj.mcstack
            break
    else:
        # No contents, no table for you!
        return None
    return TableObject(
        _pageref=_ref_page(page),
        _parentkey=None,
        gstate=gstate,
        ctm=ctm,
        mcstack=mcstack,
        _bbox=bbox,
        _parent=el,
    )


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
            table = _from_element(el, kidpage, kids)
            if table is not None:
                yield table


@detector(priority=0)
def tables_structure(
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
