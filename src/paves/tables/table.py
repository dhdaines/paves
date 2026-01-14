"""
Table types.
"""

from copy import copy
from typing import Iterable, Iterator, Tuple, Union

from playa import Page
from playa.content import GraphicState, MarkedContent
from playa.page import Annotation
from playa.pdftypes import Matrix, Rect
from playa.structure import (
    Element,
    ContentItem,
    ContentObject as StructContentObject,
)
from playa.worker import _ref_page
from dataclasses import dataclass

from playa.content import ContentObject
from playa.pdftypes import BBOX_NONE
from playa.utils import get_bound_rects


@dataclass
class TableObject(ContentObject):
    """Table on one page of a PDF.

    This **is** a ContentObject and can be treated as one (notably
    with `paves.image` functions).

    It could either come from a logical structure element, or it could
    simply be a bounding box (as detected by some sort of visual
    model).  While these `TableObject`s will never span multiple
    pages, the underlying logical structure element may do so.

    If there is underlying logical structure it is accessible (as with
    all other `ContentObject` instances) through the `parent`
    property.  This is currently the only way to detect multi-page
    tables through this interface (they will have an equivalent
    `parent`).

    Note that the graphics state and coordinate transformation matrix
    may just be the page defaults, if Machine Learning™ was used to
    detect the table in a rendered image of the page.

    """

    _bbox: Union[Rect, None]
    _parent: Union[Element, None]

    @property
    def bbox(self) -> Rect:
        # _bbox takes priority as we *could* have both
        if self._bbox is not None:
            return self._bbox
        elif self._parent is not None:
            # Try to get it from the element but only if it has the
            # same page as us (otherwise it will be wrong!)
            if self._parent.page is self.page:
                bbox = self._parent.bbox
                if bbox is not BBOX_NONE:
                    return bbox
            # We always have a page even if self._parent doesn't
            return get_bound_rects(
                item.bbox
                for item in self._parent.contents
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
        return cls(
            _pageref=_ref_page(page),
            _parentkey=None,
            gstate=gstate,
            ctm=ctm,
            mcstack=mcstack,
            _bbox=bbox,
            _parent=el,
        )

    def __iter__(self) -> Iterator["RowObject"]:
        if self._parent is not None:
            for el in self._parent:
                if isinstance(el, Element):
                    row = RowObject.from_element(el)
                    if row is not None:
                        yield row


class RowObject(ContentObject):
    """Row in a table.

    This contains table cells and can be iterated over accordingly.
    """

    @classmethod
    def from_element(
        cls,
        el: Element,
    ) -> Union["RowObject", None]:
        return None

    def __iter__(self) -> Iterator["CellObject"]:
        if self._parent is not None:
            for el in self._parent:
                if isinstance(el, Element):
                    row = CellObject.from_element(el)
                    if row is not None:
                        yield row


class CellObject(ContentObject):
    """Cell in a table.

    This might contain structure (including other tables) if it came
    from PDF logical structure, but otherwise it probably doesn't.
    You can access this through the `parent` attribute if so.  We will
    also try to transparently extract text from it for you.

    In some cases (not always) we are able to determine if this cell
    spans multiple rows or columns.

    """

    @classmethod
    def from_element(
        cls,
        el: Element,
    ) -> Union["CellObject", None]:
        return None
