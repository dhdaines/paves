"""Reimplementation of PLAYA 0.2 `page.layout` in a more appropriate location.

Creates dictionaries appropriate for feeding to bears of different
sorts (pandas or polars, your choice).
"""

import logging
import multiprocessing
from functools import singledispatch
from multiprocessing.context import BaseContext
from pathlib import Path
from typing import Iterator, List, Tuple, TypedDict, Union, cast

import playa
from playa import DeviceSpace
from playa.color import ColorSpace
from playa.page import (
    ContentObject,
    ImageObject,
    Page,
    PathObject,
    TextObject,
    XObjectObject,
)
from playa.utils import Point, apply_matrix_norm, apply_matrix_pt, get_bound

# Stub out Polars if not present
try:
    import polars as pl
except ImportError:

    class pl:  # type: ignore
        def Array(*args, **kwargs): ...
        def List(*args, **kwargs): ...
        def Object(*args, **kwargs): ...


LOG = logging.getLogger(__name__)


class LayoutDict(TypedDict, total=False):
    """Dictionary-based layout objects.

    These closely match the dictionaries returned by pdfplumber.  The
    type of coordinates returned are determined by the `space`
    argument passed to `Document`.  By default, `(0, 0)` is
    the top-left corner of the page, with 72 units per inch.

    All values can be converted to strings in some meaningful fashion,
    such that you can simply write one of these to a CSV.  You can access
    the field names through the `__annotations__` property:

        writer = DictWriter(fieldnames=LayoutDict.__annotations__.keys())
        dictwriter.write_rows(writer)

    Attributes:
      page_index: Index (0-based) of page.
      page_label: Page label if any.
      object_type: Type of object as a string.
      mcid: Containing marked content section ID (or None if marked
        content has no ID, such as artifacts or if there is no logical
        structure).
      tag: Containing marked content tag name (or None if not in a marked
        content section).
      xobjid: String name of containing Form XObject, if any.
      cid: Integer character ID of glyph, if `object_type == "char"`.
      text: Unicode mapping for glyph, if any.
      fontname: str
      size: Font size in device space.
      glyph_offset_x: Horizontal offset (in device space) of glyph
        from start of line.
      glyph_offset_y: Vertical offset (in device space) of glyph from
        start of line.
      render_mode: Text rendering mode.
      upright: FIXME: Not really sure what this means.  pdfminer.six?
      x0: Minimum x coordinate of bounding box (top or bottom
        depending on device space).
      x1: Maximum x coordinate of bounding box (top or bottom
        depending on device space).
      y0: Minimum y coordinate of bounding box (left or right
        depending on device space).
      x1: Minimum x coordinate of bounding box (left or right
        depending on device space).
      stroking_colorspace: String name of colour space for stroking
        operations.
      stroking_color: Numeric parameters for stroking color.
      stroking_pattern: Name of stroking pattern, if any.
      non_stroking_colorspace: String name of colour space for non-stroking
        operations.
      non_stroking_color: Numeric parameters for non-stroking color.
      non_stroking_pattern: Name of stroking pattern, if any.
      path_ops: Sequence of path operations (e.g. `"mllh"` for a
        triangle or `"mlllh"` for a quadrilateral)
      dash_pattern: Sequence of user space units for alternating
        stroke and non-stroke segments of dash pattern, `()` for solid
        line. (Cannot be in device space because this would depend on
        which direction the line or curve is drawn).
      dash_phase: Initial position in `dash_pattern` in user space
        units.  (see above for why it's in user space)
      evenodd: Was this path filled with Even-Odd (if `True`) or
        Nonzero-Winding-Number rule (if `False`)?  Note that this is
        **meaningless** for determining if a path is actually filled
        since subpaths have already been decomposed.  If you really
        care then use the lazy API instead.
      stroke: Is this path stroked?
      fill: Is this path filled?
      linewidth: Line width in user space units (again, not possible
        to transform to device space).
      pts_x: X coordinates of path endpoints, one for each character
        in `path_ops`.  This is optimized for CSV/DataFrame output, if
        you care about the control points then use the lazy API.
      pts_y: Y coordinates of path endpoints, one for each character
        in `path_ops`.  This is optimized for CSV/DataFrame output, if
        you care about the control points then use the lazy API.
      stream: Object number and generation number for the content
        stream associated with an image, or `None` for inline images.
        If you want image data then use the lazy API.
      imagemask: Is this image a mask?
      image_colorspace: String description of image colour space, or
        `None` if irrelevant/forbidden,
      srcsize: Source dimensions of image in pixels.
      bits: Number of bits per channel of image.
    """

    page_index: int
    page_label: Union[str, None]
    object_type: str
    mcid: Union[int, None]
    tag: Union[str, None]
    xobjid: Union[str, None]
    cid: int
    text: Union[str, None]
    fontname: str
    size: float
    glyph_offset_x: float
    glyph_offset_y: float
    render_mode: int
    upright: bool
    x0: float
    y0: float
    x1: float
    y1: float
    stroking_colorspace: str
    stroking_color: Tuple[float, ...]
    stroking_pattern: Union[str, None]
    non_stroking_colorspace: str
    non_stroking_color: Tuple[float, ...]
    non_stroking_pattern: Union[str, None]
    path_ops: str
    dash_pattern: Tuple[float, ...]
    dash_phase: float
    evenodd: bool
    stroke: bool
    fill: bool
    linewidth: float
    pts_x: List[float]
    pts_y: List[float]
    stream: Union[Tuple[int, int], None]
    imagemask: bool
    image_colorspace: Union[ColorSpace, None]
    srcsize: Tuple[int, int]
    bits: int


fieldnames = LayoutDict.__annotations__.keys()
schema = {
    "page_index": int,
    "page_label": str,
    "object_type": str,
    "mcid": int,
    "tag": str,
    "xobjid": str,
    "text": str,
    "cid": int,
    "fontname": str,
    "size": float,
    "glyph_offset_x": float,
    "glyph_offset_y": float,
    "render_mode": int,
    "upright": bool,
    "x0": float,
    "x1": float,
    "y0": float,
    "y1": float,
    "stroking_colorspace": str,
    "non_stroking_colorspace": str,
    "stroking_color": pl.List(float),
    "non_stroking_color": pl.List(float),
    "path_ops": str,
    "dash_pattern": pl.List(float),
    "dash_phase": float,
    "evenodd": bool,
    "stroke": bool,
    "fill": bool,
    "linewidth": float,
    "pts_x": pl.List(float),
    "pts_y": pl.List(float),
    "stream": pl.Array(int, 2),
    "imagemask": bool,
    "image_colorspace": str,
    "srcsize": pl.Array(int, 2),
    "bits": int,
}


@singledispatch
def process_object(obj: ContentObject) -> Iterator[LayoutDict]:
    """Handle obj according to its type"""
    yield from ()


def make_path(
    obj: PathObject,
    *,
    object_type: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    path_ops: str,
    pts: List[Point],
) -> LayoutDict:
    """Make a `LayoutDict` for a path."""
    return LayoutDict(
        object_type=object_type,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        mcid=None if obj.mcs is None else obj.mcs.mcid,
        tag=None if obj.mcs is None else obj.mcs.tag,
        path_ops=path_ops,
        pts_x=[x for x, y in pts],
        pts_y=[y for x, y in pts],
        stroke=obj.stroke,
        fill=obj.fill,
        evenodd=obj.evenodd,
        linewidth=obj.gstate.linewidth,
        dash_pattern=obj.gstate.dash.dash,
        dash_phase=obj.gstate.dash.phase,
        stroking_colorspace=obj.gstate.scs.name,
        stroking_color=obj.gstate.scolor.values,
        stroking_pattern=obj.gstate.scolor.pattern,
        non_stroking_colorspace=obj.gstate.ncs.name,
        non_stroking_color=obj.gstate.ncolor.values,
        non_stroking_pattern=obj.gstate.ncolor.pattern,
        page_index=0,
        page_label="0",
    )


@process_object.register
def _(obj: PathObject) -> Iterator[LayoutDict]:
    for path in obj:
        ops = []
        pts: List[Point] = []
        for seg in path.raw_segments:
            ops.append(seg.operator)
            if seg.operator == "h":
                pts.append(pts[0])
            else:
                pts.append(apply_matrix_pt(obj.ctm, seg.points[-1]))
        # Drop a redundant "l" on a path closed with "h"
        shape = "".join(ops)
        if len(ops) > 3 and shape[-2:] == "lh" and pts[-2] == pts[0]:
            shape = shape[:-2] + "h"
            pts.pop()
        if shape in {"mlh", "ml"}:
            # single line segment ("ml" is a frequent anomaly)
            (x0, y0), (x1, y1) = pts[0:2]
            if x0 > x1:
                (x1, x0) = (x0, x1)
            if y0 > y1:
                (y1, y0) = (y0, y1)
            yield make_path(
                obj,
                object_type="line",
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                path_ops=shape,
                pts=pts,
            )
        elif shape in {"mlllh", "mllll"}:
            (x0, y0), (x1, y1), (x2, y2), (x3, y3), _ = pts
            is_closed_loop = pts[0] == pts[4]
            has_square_coordinates = (
                x0 == x1 and y1 == y2 and x2 == x3 and y3 == y0
            ) or (y0 == y1 and x1 == x2 and y2 == y3 and x3 == x0)
            if is_closed_loop and has_square_coordinates:
                if x0 > x2:
                    (x2, x0) = (x0, x2)
                if y0 > y2:
                    (y2, y0) = (y0, y2)
                yield make_path(
                    obj,
                    object_type="rect",
                    x0=x0,
                    y0=y0,
                    x1=x2,
                    y1=y2,
                    path_ops=shape,
                    pts=pts,
                )
            else:
                x0, y0, x1, y1 = get_bound(pts)
                yield make_path(
                    obj,
                    object_type="curve",
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    path_ops=shape,
                    pts=pts,
                )
        else:
            x0, y0, x1, y1 = get_bound(pts)
            yield make_path(
                obj,
                object_type="curve",
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                path_ops=shape,
                pts=pts,
            )


@process_object.register
def _(obj: ImageObject) -> Iterator[LayoutDict]:
    x0, y0, x1, y1 = obj.bbox
    if (
        obj.stream is not None
        and obj.stream.objid is not None
        and obj.stream.genno is not None
    ):
        stream_id = (obj.stream.objid, obj.stream.genno)
    else:
        stream_id = None
    yield LayoutDict(
        object_type="image",
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        xobjid=obj.xobjid,
        mcid=None if obj.mcs is None else obj.mcs.mcid,
        tag=None if obj.mcs is None else obj.mcs.tag,
        srcsize=obj.srcsize,
        imagemask=obj.imagemask,
        bits=obj.bits,
        image_colorspace=obj.colorspace,
        stream=stream_id,
        page_index=0,
        page_label="0",
    )


@process_object.register
def _(obj: TextObject) -> Iterator[LayoutDict]:
    for glyph in obj:
        x0, y0, x1, y1 = glyph.bbox
        tstate = glyph.textstate
        gstate = glyph.gstate
        # apparently we can assert this?
        font = tstate.font
        assert font is not None
        glyph_x, glyph_y = apply_matrix_norm(glyph.ctm, tstate.glyph_offset)
        (a, b, c, d, e, f) = glyph.matrix
        if font.vertical:
            size = abs(tstate.fontsize * a)
        else:
            size = abs(tstate.fontsize * d)
        scaling = tstate.scaling * 0.01  # FIXME: unnecessary?
        upright = a * d * scaling > 0 and b * c <= 0

        yield LayoutDict(
            object_type="char",
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            size=size,
            upright=upright,
            text=glyph.text,
            cid=glyph.cid,
            fontname=font.fontname,
            glyph_offset_x=glyph_x,
            glyph_offset_y=glyph_y,
            render_mode=tstate.render_mode,
            dash_pattern=gstate.dash.dash,
            dash_phase=gstate.dash.phase,
            stroking_colorspace=gstate.scs.name,
            stroking_color=gstate.scolor.values,
            stroking_pattern=gstate.scolor.pattern,
            non_stroking_colorspace=gstate.ncs.name,
            non_stroking_color=gstate.ncolor.values,
            non_stroking_pattern=gstate.ncolor.pattern,
            mcid=None if obj.mcs is None else obj.mcs.mcid,
            tag=None if obj.mcs is None else obj.mcs.tag,
            page_index=0,
            page_label="0",
        )


@process_object.register
def _(obj: XObjectObject) -> Iterator[LayoutDict]:
    for child in obj:
        for layout in process_object(child):
            layout["xobjid"] = obj.xobjid
            yield layout


def extract_page(page: Page) -> List[LayoutDict]:
    """Extract LayoutDict items from a Page."""
    page_layout = []
    for obj in page:
        for dic in process_object(obj):
            dic = cast(LayoutDict, dic)  # ugh
            dic["page_index"] = page.page_idx
            dic["page_label"] = page.label
            page_layout.append(dic)
    return page_layout


def extract(
    path: Path,
    space: DeviceSpace = "screen",
    max_workers: Union[int, None] = 1,
    mp_context: Union[BaseContext, None] = None,
) -> Iterator[LayoutDict]:
    """Extract LayoutDict items from a document."""
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    with playa.open(
        path,
        max_workers=max_workers,
        mp_context=mp_context,
    ) as pdf:
        for page in pdf.pages.map(extract_page):
            yield from page
