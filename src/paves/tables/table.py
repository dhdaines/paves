"""
Table types.
"""

from dataclasses import dataclass
from typing import Union

from playa import Page
from playa.content import ContentObject, GraphicState
from playa.pdftypes import Rect, BBOX_NONE
from playa.structure import (
    Element,
)
from playa.utils import get_bound_rects
from playa.worker import _ref_page


@dataclass
class TableObject(ContentObject):
    """Table on one page of a PDF.

    This **is** a ContentObject and can be treated as one (notably
    with `paves.image` functions).

    It could either come from a logical structure element, or it could
    simply be a bounding box (as detected by some sort of visual
    model).  While these `TableObject`s will never span multiple
    pages, the underlying logical structure element may do so.  This
    is currently the only way to detect multi-page tables through this
    interface (they will have an equivalent `parent` property).

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
