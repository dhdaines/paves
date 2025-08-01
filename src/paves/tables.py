"""
Simple and not at all Java-damaged interface for table detection
and structure prediction.
"""

from copy import copy
from dataclasses import dataclass
from functools import singledispatch
from itertools import groupby
from typing import Any, Callable, Iterable, Iterator, List, Tuple, Union
from operator import attrgetter
from os import PathLike

import playa
from playa import Document, Page, PageList
from playa.content import ContentObject, GraphicState, MarkedContent
from playa.page import Annotation
from playa.pdftypes import Matrix, Rect, BBOX_NONE
from playa.structure import Element, ContentItem, ContentObject as StructContentObject
from playa.utils import get_bound_rects
from playa.worker import _ref_page


@dataclass
class TableObject(ContentObject):
    """Table on one page of a PDF.

    This **is** a ContentObject and can be treated as one (notably
    with `paves.image` functions).

    It could either come from a logical structure element, or it could
    simply be a bounding box (as detected by some sort of visual
    model).  Do not assume one or the other, because notably, a
    logical structure element can span multiple pages.

    """

    _el: Union[Element, None]
    _bbox: Union[Rect, None]
    _parent: Union[Element, None]

    @property
    def bbox(self) -> Rect:
        # _bbox takes priority as we *could* have both (in the case of
        # a multi-page table, in which case _el.bbox will be BBOX_NONE)
        if self._bbox is not None:
            return self._bbox
        elif self._el is not None:
            # Try to get it from the element first
            bbox = self._el.bbox
            if bbox is not BBOX_NONE:
                return bbox
            # We always have a page even if self._el doesn't
            return get_bound_rects(
                item.bbox
                for item in self._el.contents
                if item.page is self.page and item.bbox is not BBOX_NONE
            )
        else:
            # This however should never happen
            return BBOX_NONE

    @classmethod
    def from_bbox(cls, page: Page, bbox: Rect) -> "TableObject":
        # Use default values
        return cls(
            _pageref=_ref_page(page),
            _parentkey=None,
            gstate=GraphicState(),
            ctm=page.ctm,
            mcstack=(),
            _el=None,
            _bbox=bbox,
            _parent=None,
        )

    @classmethod
    def from_element(
        cls,
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
        return cls(
            _pageref=_ref_page(page),
            _parentkey=None,
            gstate=gstate,
            ctm=ctm,
            mcstack=mcstack,
            _el=el,
            _bbox=bbox,
            _parent=el,
        )


@singledispatch
def table_elements(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[Element]:
    """Iterate over all text objects in a PDF, page, or pages"""
    raise NotImplementedError


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
        raise TypeError
    return structure.find_all("Table")


@table_elements.register
def table_elements_pagelist(pages: PageList) -> Iterator[Element]:
    structure = pages.doc.structure
    if structure is None:
        raise TypeError
    # FIXME: Accelerate this with the ParentTree too
    return (table for table in structure.find_all("Table") if table.page in pages)


@table_elements.register
def table_elements_page(page: Page) -> Iterator[Element]:
    # FIXME: Accelerate this with the ParentTree
    pagelist = page.doc.pages[(page.page_idx,)]
    return table_elements_pagelist(pagelist)


def table_elements_to_objects(
    elements: Iterable[Element], page: Union[Page, None] = None
) -> Iterator[TableObject]:
    """Make TableObjects from Elements."""
    for el in elements:
        # It might have a page
        if el.page is not None:
            table = TableObject.from_element(el, el.page)
            if table is not None:
                yield table
        elif page is not None:
            table = TableObject.from_element(el, page)
            if table is not None:
                yield table
        else:
            # Alert! We have a multi-page table! So we have to go
            # through all of the marked content items for this element
            # and group them by pages, then yield separate
            # TableObjects for each of them.  This may be hard to test.
            for page, kids in groupby(el.contents, attrgetter("page")):
                if page is None:
                    continue
                table = TableObject.from_element(el, page, kids)
                if table is not None:
                    yield table


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


@singledispatch
def _get_pages(pdf: Union[str, PathLike, Document, Page, PageList]) -> Iterator[Page]:
    raise NotImplementedError


@_get_pages.register(str)
@_get_pages.register(PathLike)
def _get_pages_path(pdf: Union[str, PathLike]) -> Iterator[Page]:
    with playa.open(pdf) as doc:
        yield from doc.pages


@_get_pages.register
def _get_pages_pagelist(pagelist: PageList) -> Iterator[Page]:
    yield from pagelist


@_get_pages.register
def _get_pages_doc(doc: Document) -> Iterator[Page]:
    yield from doc.pages


@_get_pages.register
def _get_pages_page(page: Page) -> Iterator[Page]:
    yield page


def table_bounds_to_objects(
    pdf: Union[str, PathLike, Document, Page, PageList],
    bounds: Iterable[Tuple[int, Iterable[Rect]]],
) -> Iterator[TableObject]:
    """Create TableObjects from detected bounding boxes."""
    for page, (page_idx, tables) in zip(_get_pages(pdf), bounds):
        assert page.page_idx == page_idx
        for bbox in tables:
            yield TableObject.from_bbox(page, bbox)


def tables_detr(
    pdf: Union[str, PathLike, Document, Page, PageList],
    device: str = "cpu",
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages using IBM's
    RT-DETR layout detection model

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.
        device: Torch device for running the model.

    Returns:
      An iterator over `TableObject`, or `None`, if the model can't be used
    """
    try:
        from paves.tables_detr import table_bounds
    except ImportError:
        return None
    return table_bounds_to_objects(pdf, table_bounds(pdf, device=device))


METHODS: List[Callable] = [tables_structure, tables_detr]


def tables(
    pdf: Union[str, PathLike, Document, Page, PageList], **kwargs: Any
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages.

    This will always try to use logical structure (via PLAYA-PDF)
    first to identify tables.

    For the moment, this only works on tagged and accessible PDFs.
    So, like `paves.image`, it can also use Machine Learning Models™
    to do so, which involves nasty horrible dependencyses (we hates
    them, they stole the precious) like `cudnn-10-gigabytes-of-c++`.

    If you'd like to try that, then you can do so by installing the
    `transformers` package (if you don't have a GPU, try adding
    `--extra-index-url https://download.pytorch.org/whl/cpu` to pip's
    command line).

    Note: These tables cannot span multiple pages.
        Often, a table will span multiple pages.  With PDF logical
        structure, this can be represented (and sometimes is), but if
        there is no logical structure, this is not possible, since
        tables are detected from the rendered image of a page.
        Reconstructing this information is both extremely important
        and also very difficult with current models (perhaps very big
        VLMs can do it?).  Since we also want to visualize tables with
        `paves.image`, we don't return multi-page tables here.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
        An iterator over `TableObject`, or `None`, if there is no
        method available to detect tables.  This will cause a
        `TypeError` if you try to iterate over it anyway.
    """
    for method in METHODS:
        itor = method(pdf, **kwargs)
        if itor is not None:
            return itor
    else:
        return None
