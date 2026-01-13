"""
Various ways of converting PDFs to images for feeding them to
models and/or visualisation.`
"""

import functools
import itertools
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Protocol,
    Tuple,
    Union,
    cast,
)

from PIL import Image, ImageDraw, ImageFont
from playa.page import ContentObject, Page, Annotation
from playa.structure import Element
from playa.utils import Rect, transform_bbox

from paves.image.converters import convert
from paves.image.poppler import popple
from paves.image.pdfium import pdfium

__all__ = ["convert", "popple", "pdfium", "show", "box", "mark"]


def show(page: Page, dpi: int = 72) -> Image.Image:
    """Show a single page with some reasonable defaults."""
    return next(convert(page, dpi=dpi))


class HasBbox(Protocol):
    bbox: Rect


class HasPage(Protocol):
    page: Page


Boxable = Union[Annotation, ContentObject, Element, HasBbox, Rect]
"""Object for which we can get a bounding box."""
LabelFunc = Callable[[Boxable], Any]
"""Function to get a label for a Boxable."""
BoxFunc = Callable[[Boxable], Rect]
"""Function to get a bounding box for a Boxable."""


@functools.singledispatch
def get_box(obj) -> Rect:
    """Default function to get the bounding box for an object."""
    if hasattr(obj, "bbox"):
        return obj.bbox
    raise RuntimeError(f"Don't know how to get the box for {obj!r}")


@get_box.register(tuple)
def get_box_rect(obj: Rect) -> Rect:
    """Get the bounding box of a ContentObject"""
    return obj


@get_box.register(ContentObject)
@get_box.register(Element)
def get_box_content(obj: Union[ContentObject, Element]) -> Rect:
    """Get the bounding box of a ContentObject"""
    return obj.bbox


@get_box.register(Annotation)
def get_box_annotation(obj: Annotation) -> Rect:
    """Get the bounding box of an Annotation"""
    return transform_bbox(obj.page.ctm, obj.rect)


@functools.singledispatch
def get_label(obj: Boxable) -> str:
    """Default function to get the label text for an object."""
    return str(obj)


@get_label.register(ContentObject)
def get_label_content(obj: ContentObject) -> str:
    """Get the label text for a ContentObject."""
    return obj.object_type


@get_label.register(Annotation)
def get_label_annotation(obj: Annotation) -> str:
    """Get the default label text for an Annotation.

    Note: This is just a default.
        This is one of many possible options, so you may wish to
        define your own custom LabelFunc.
    """
    return obj.subtype


@get_label.register(Element)
def get_label_element(obj: Element) -> str:
    """Get the default label text for an Element.

    Note: This is just a default.
        This is one of many possible options, so you may wish to
        define your own custom LabelFunc.
    """
    return obj.type


def _make_boxes(
    obj: Union[
        Annotation,
        ContentObject,
        Element,
        Rect,
        HasBbox,
        Iterable[Union[Boxable, None]],
    ],
) -> Iterable[Union[Boxable, None]]:
    """Put a box into a list of boxes if necessary."""
    # Is it a single Rect? (mypy is incapable of understanding the
    # runtime check here so we need the cast among other things)
    if isinstance(obj, tuple):
        if len(obj) == 4 and all(isinstance(x, (int, float)) for x in obj):
            return [cast(Rect, obj)]
        # This shouldn't be necessary... but mypy needs it
        return list(obj)
    if isinstance(obj, (Annotation, ContentObject, Element)):
        return [obj]
    if hasattr(obj, "bbox"):
        # Ugh, we have to cast
        return [cast(HasBbox, obj)]
    return obj


def _getpage(
    obj: Boxable,
    page: Union[Page, None] = None,
) -> Page:
    if page is None:
        if not hasattr(obj, "page"):
            raise ValueError("Must explicitly specify page or image to show rectangles")
        page = cast(HasPage, obj).page
    if page is None:
        raise ValueError("No page found in object: %r" % (obj,))
    return page


Color = Union[str, Tuple[int, int, int], Tuple[float, float, float]]
"""Type alias for things that can be used as colors."""
Colors = Union[Color, List[Color], Dict[str, Color]]
"""Type alias for colors or collections of colors."""
PillowColor = Union[str, Tuple[int, int, int]]
"""Type alias for things Pillow accepts as colors."""
ColorMaker = Callable[[str], PillowColor]
"""Function that makes a Pillow color for a string label."""
DEFAULT_COLOR_CYCLE: Colors = [
    "blue",
    "orange",
    "green",
    "red",
    "purple",
    "brown",
    "pink",
    "gray",
    "olive",
    "cyan",
]
"""Default color cycle (same as matplotlib)"""


def pillow_color(color: Color) -> PillowColor:
    """Convert colors to a form acceptable to Pillow."""
    if isinstance(color, str):
        return color
    r, g, b = color
    # Would sure be nice if MyPy understood all()
    if isinstance(r, int) and isinstance(g, int) and isinstance(b, int):
        return (r, g, b)
    r, g, b = (int(x * 255) for x in color)
    return (r, g, b)


@functools.singledispatch
def color_maker(spec: Colors, default: Color = "red") -> ColorMaker:
    """Create a function that makes colors."""
    return lambda _: pillow_color(default)


@color_maker.register(str)
@color_maker.register(tuple)
def _color_maker_string(spec: Color, default: Color = "red") -> ColorMaker:
    return lambda _: pillow_color(spec)


@color_maker.register(dict)
def _color_maker_dict(spec: Dict[str, Color], default: Color = "red") -> ColorMaker:
    colors: Dict[str, PillowColor] = {k: pillow_color(v) for k, v in spec.items()}
    pdefault: PillowColor = pillow_color(default)

    def maker(label: str) -> PillowColor:
        return colors.get(label, pdefault)

    return maker


@color_maker.register(list)
def _color_maker_list(spec: List[Color], default: Color = "UNUSED") -> ColorMaker:
    itor = itertools.cycle(spec)
    colors: Dict[str, PillowColor] = {}

    def maker(label: str) -> PillowColor:
        if label not in colors:
            colors[label] = pillow_color(next(itor))
        return colors[label]

    return maker


def box(
    objs: Union[
        Boxable,
        Iterable[Union[Boxable, None]],
    ],
    *,
    color: Colors = DEFAULT_COLOR_CYCLE,
    label: bool = True,
    label_color: Color = "white",
    label_size: float = 9,
    label_margin: float = 1,
    label_fill: bool = True,
    image: Union[Image.Image, None] = None,
    labelfunc: LabelFunc = get_label,
    boxfunc: BoxFunc = get_box,
    dpi: int = 72,
    page: Union[Page, None] = None,
) -> Union[Image.Image, None]:
    """Draw boxes around things in a page of a PDF."""
    draw: ImageDraw.ImageDraw
    scale = dpi / 72
    font = ImageFont.load_default(label_size * scale)
    label_margin *= scale
    make_color = color_maker(color)
    image_page: Union[Page, None] = None
    for obj in _make_boxes(objs):
        if obj is None:
            continue
        if image_page is not None:
            if hasattr(obj, "page"):
                if cast(HasPage, obj).page != image_page:
                    break
        if image is None:
            image_page = _getpage(obj, page)
            image = show(image_page, dpi)
        try:
            left, top, right, bottom = (x * scale for x in boxfunc(obj))
        except ValueError:  # it has no content and no box
            continue
        draw = ImageDraw.ImageDraw(image)
        text = str(labelfunc(obj))
        obj_color = make_color(text)
        draw.rectangle((left, top, right, bottom), outline=obj_color)
        if label:
            tl, tt, tr, tb = font.getbbox(text)
            label_box = (
                left,
                top - tb - label_margin * 2,
                left + tr + label_margin * 2,
                top,
            )
            draw.rectangle(
                label_box,
                outline=obj_color,
                fill=obj_color if label_fill else None,
            )
            draw.text(
                xy=(left + label_margin, top - label_margin),
                text=text,
                font=font,
                fill="white" if label_fill else obj_color,
                anchor="ld",
            )
    return image


def mark(
    objs: Union[
        Boxable,
        Iterable[Union[Boxable, None]],
    ],
    *,
    color: Colors = DEFAULT_COLOR_CYCLE,
    transparency: float = 0.75,
    label: bool = False,
    label_color: Color = "white",
    label_size: float = 9,
    label_margin: float = 1,
    outline: bool = False,
    image: Union[Image.Image, None] = None,
    labelfunc: LabelFunc = get_label,
    boxfunc: BoxFunc = get_box,
    dpi: int = 72,
    page: Union[Page, None] = None,
) -> Union[Image.Image, None]:
    """Highlight things in a page of a PDF."""
    overlay: Union[Image.Image, None] = None
    mask: Union[Image.Image, None] = None
    draw: ImageDraw.ImageDraw
    scale = dpi / 72
    font = ImageFont.load_default(label_size * scale)
    alpha = min(255, int(transparency * 255))
    label_margin *= scale
    make_color = color_maker(color)
    image_page: Union[Page, None] = None
    for obj in _make_boxes(objs):
        if obj is None:
            continue
        if image_page is not None:
            if hasattr(obj, "page"):
                if cast(HasPage, obj).page != image_page:
                    break
        if image is None:
            image_page = _getpage(obj, page)
            image = show(image_page, dpi)
        if overlay is None:
            overlay = Image.new("RGB", image.size)
        if mask is None:
            mask = Image.new("L", image.size, 255)
        try:
            left, top, right, bottom = (x * scale for x in boxfunc(obj))
        except ValueError:  # it has no content and no box
            continue
        draw = ImageDraw.ImageDraw(overlay)
        text = str(labelfunc(obj))
        obj_color = make_color(text)
        draw.rectangle((left, top, right, bottom), fill=obj_color)
        mask_draw = ImageDraw.ImageDraw(mask)
        mask_draw.rectangle((left, top, right, bottom), fill=alpha)
        if outline:
            draw.rectangle((left, top, right, bottom), outline="black")
            mask_draw.rectangle((left, top, right, bottom), outline=0)
        if label:
            tl, tt, tr, tb = font.getbbox(text)
            label_box = (
                left,
                top - tb - label_margin * 2,
                left + tr + label_margin * 2,
                top,
            )
            draw.rectangle(
                label_box,
                outline=obj_color,
                fill=obj_color,
            )
            mask_draw.rectangle(
                label_box,
                fill=alpha,
            )
            if outline:
                draw.rectangle(
                    label_box,
                    outline="black",
                )
                mask_draw.rectangle(
                    label_box,
                    outline=0,
                )
                draw.text(
                    xy=(left + label_margin, top - label_margin),
                    text=text,
                    font=font,
                    fill="black",
                    anchor="ld",
                )
                mask_draw.text(
                    xy=(left + label_margin, top - label_margin),
                    text=text,
                    font=font,
                    fill=0,
                    anchor="ld",
                )
            else:
                draw.text(
                    xy=(left + label_margin, top - label_margin),
                    text=text,
                    font=font,
                    fill="white",
                    anchor="ld",
                )
    if image is None:
        return None
    if overlay is not None and mask is not None:
        return Image.composite(image, overlay, mask)
    else:
        return image
