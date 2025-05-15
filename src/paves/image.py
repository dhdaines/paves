"""
Various ways of converting PDFs to images for feeding them to
models and/or visualisation.`
"""

import functools
import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Union,
    cast,
)

from PIL import Image, ImageDraw, ImageFont
from playa.document import Document, PageList
from playa.page import ContentObject, Page, Annotation
from playa.structure import Element
from playa.utils import Rect, get_transformed_bound

if TYPE_CHECKING:
    import pypdfium2  # types: ignore


class NotInstalledError(RuntimeError):
    """Exception raised if the dependencies for a particular PDF to
    image backend are not installed."""


def make_poppler_args(dpi: int, width: int, height: int) -> List[str]:
    args = []
    if width or height:
        args.extend(
            [
                "-scale-to-x",
                str(width or -1),  # -1 means use aspect ratio
                "-scale-to-y",
                str(height or -1),
            ]
        )
    if not args:
        args.extend(["-r", str(dpi or 72)])
    return args


@functools.singledispatch
def _popple(pdf, tempdir: Path, args: List[str]) -> None:
    subprocess.run(
        [
            "pdftoppm",
            *args,
            str(pdf),
            tempdir / "ppm",
        ],
        check=True,
    )


@_popple.register(Document)
def _popple_doc(pdf: Document, tempdir: Path, args: List[str]) -> None:
    pdfpdf = tempdir / "pdf.pdf"
    with open(pdfpdf, "wb") as outfh:
        outfh.write(pdf.buffer)
    subprocess.run(
        [
            "pdftoppm",
            *args,
            str(pdfpdf),
            tempdir / "ppm",
        ],
        check=True,
    )


@_popple.register(Page)
def _popple_page(pdf: Page, tempdir: Path, args: List[str]) -> None:
    assert pdf.doc is not None  # bug in PLAYA-PDF, oops, it cannot be None
    pdfpdf = tempdir / "pdf.pdf"
    with open(pdfpdf, "wb") as outfh:
        outfh.write(pdf.doc.buffer)
    page_number = pdf.page_idx + 1
    subprocess.run(
        [
            "pdftoppm",
            *args,
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdfpdf),
            tempdir / "ppm",
        ],
        check=True,
    )


@_popple.register(PageList)
def _popple_pages(pdf: PageList, tempdir: Path, args: List[str]) -> None:
    pdfpdf = tempdir / "pdf.pdf"
    assert pdf[0].doc is not None  # bug in PLAYA-PDF, oops, it cannot be None
    with open(pdfpdf, "wb") as outfh:
        outfh.write(pdf[0].doc.buffer)
    pages = sorted(page.page_idx + 1 for page in pdf)
    itor = iter(pages)
    first = last = next(itor)
    spans = []
    while True:
        try:
            next_last = next(itor)
        except StopIteration:
            spans.append((first, last))
            break
        if next_last > last + 1:
            spans.append((first, last))
            first = last = next_last
        else:
            last = next_last
    for first, last in spans:
        subprocess.run(
            [
                "pdftoppm",
                *args,
                "-f",
                str(first),
                "-l",
                str(last),
                str(pdfpdf),
                tempdir / "ppm",
            ],
            check=True,
        )


def popple(
    pdf: Union[str, PathLike, Document, Page, PageList],
    *,
    dpi: int = 0,
    width: int = 0,
    height: int = 0,
) -> Iterator[Image.Image]:
    """Convert a PDF to images using Poppler's pdftoppm.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.
        dpi: Render to this resolution (default is 72 dpi).
        width: Render to this width in pixels.
        height: Render to this height in pixels.
    Yields:
        Pillow `Image.Image` objects, one per page.
    Raises:
        ValueError: Invalid arguments (e.g. both `dpi` and `width`/`height`)
        NotInstalledError: If Poppler is not installed.
    """
    if dpi and (width or height):
        raise ValueError("Cannot specify both `dpi` and `width` or `height`")
    try:
        subprocess.run(["pdftoppm", "-h"], capture_output=True)
    except FileNotFoundError as e:
        raise NotInstalledError("Poppler does not seem to be installed") from e
    args = make_poppler_args(dpi, width, height)
    with tempfile.TemporaryDirectory() as tempdir:
        temppath = Path(tempdir)
        _popple(pdf, temppath, args)
        for ppm in sorted(temppath.iterdir()):
            if ppm.suffix == ".ppm":
                yield Image.open(ppm)


@functools.singledispatch
def _get_pdfium_pages(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator["pypdfium2.PdfPage"]:
    import pypdfium2

    doc = pypdfium2.PdfDocument(pdf)
    for page in doc:
        yield page
        page.close()
    doc.close()


@_get_pdfium_pages.register(Document)
def _get_pdfium_pages_doc(pdf: Document) -> Iterator["pypdfium2.PdfPage"]:
    import pypdfium2

    doc = pypdfium2.PdfDocument(pdf._fp)
    for page in doc:
        yield page
        page.close()
    doc.close()


@_get_pdfium_pages.register(Page)
def _get_pdfium_pages_page(page: Page) -> Iterator["pypdfium2.PdfPage"]:
    import pypdfium2

    pdf = page.doc
    assert pdf is not None
    doc = pypdfium2.PdfDocument(pdf._fp)
    pdfium_page = doc[page.page_idx]
    yield pdfium_page
    pdfium_page.close()
    doc.close()


@_get_pdfium_pages.register(PageList)
def _get_pdfium_pages_pagelist(pages: PageList) -> Iterator["pypdfium2.PdfPage"]:
    import pypdfium2

    pdf = pages.doc
    assert pdf is not None
    doc = pypdfium2.PdfDocument(pdf._fp)
    for page in pages:
        pdfium_page = doc[page.page_idx]
        yield pdfium_page
        pdfium_page.close()
    doc.close()


def pdfium(
    pdf: Union[str, PathLike, Document, Page, PageList],
    *,
    dpi: int = 0,
    width: int = 0,
    height: int = 0,
) -> Iterator[Image.Image]:
    """Convert a PDF to images using PyPDFium2

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.
        dpi: Render to this resolution (default is 72 dpi).
        width: Render to this width in pixels.
        height: Render to this height in pixels.
    Yields:
        Pillow `Image.Image` objects, one per page.
    Raises:
        ValueError: Invalid arguments (e.g. both `dpi` and `width`/`height`)
        NotInstalledError: If PyPDFium2 is not installed.
    """
    if dpi and (width or height):
        raise ValueError("Cannot specify both `dpi` and `width` or `height`")
    try:
        import pypdfium2  # noqa: F401
    except ImportError as e:
        raise NotInstalledError("PyPDFium2 does not seem to be installed") from e
    for page in _get_pdfium_pages(pdf):
        if width == 0 and height == 0:
            scale = (dpi or 72) / 72
            yield page.render(scale=scale).to_pil()
        else:
            if width and height:
                # Scale to longest side (since pypdfium2 doesn't
                # appear to allow non-1:1 aspect ratio)
                scale = max(width / page.get_width(), height / page.get_height())
                img = page.render(scale=scale).to_pil()
                # Resize down to desired size
                yield img.resize(size=(width, height))
            elif width:
                scale = width / page.get_width()
                yield page.render(scale=scale).to_pil()
            elif height:
                scale = height / page.get_height()
                yield page.render(scale=scale).to_pil()


METHODS = [popple, pdfium]


def convert(
    pdf: Union[str, PathLike, Document, Page, PageList],
    *,
    dpi: int = 0,
    width: int = 0,
    height: int = 0,
) -> Iterator[Image.Image]:
    """Convert a PDF to images.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.
        dpi: Render to this resolution (default is 72 dpi).
        width: Render to this width in pixels (0 to keep aspect ratio).
        height: Render to this height in pixels (0 to keep aspect ratio).
    Yields:
        Pillow `Image.Image` objects, one per page.
    Raises:
        ValueError: Invalid arguments (e.g. both `dpi` and `width`/`height`)
        NotInstalledError: If no renderer is available
    """
    for method in METHODS:
        try:
            for img in method(pdf, dpi=dpi, width=width, height=height):
                yield img
            break
        except NotInstalledError:
            continue
    else:
        raise NotInstalledError(
            "No renderers available, tried: %s"
            % (", ".join(m.__name__ for m in METHODS))
        )


def show(page: Page, dpi: int = 72) -> Image.Image:
    """Show a single page with some reasonable defaults."""
    return next(convert(page, dpi=dpi))


LabelFunc = Callable[[Union[Annotation, ContentObject, Element, Rect]], str]
BoxFunc = Callable[[Union[Annotation, ContentObject, Element, Rect]], Rect]


@functools.singledispatch
def get_box(obj: Union[Annotation, ContentObject, Element, Rect]) -> Rect:
    """Default function to get the bounding box for an object."""
    raise RuntimeError(f"Don't know how to get the box for {obj!r}")


@get_box.register(tuple)
def get_box_rect(obj: Rect) -> Rect:
    """Get the bounding box of a ContentObject"""
    return obj


@get_box.register
def get_box_content(obj: Union[ContentObject, Element]) -> Rect:
    """Get the bounding box of a ContentObject"""
    return obj.bbox


@get_box.register(Annotation)
def get_box_annotation(obj: Annotation) -> Rect:
    """Get the bounding box of an Annotation"""
    return get_transformed_bound(obj.page.ctm, obj.rect)


@functools.singledispatch
def get_label(obj: Union[Annotation, ContentObject, Element, Rect]) -> str:
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
        Iterable[Union[Annotation, ContentObject, Element, Rect]],
    ],
) -> Iterable[Union[Annotation, ContentObject, Element, Rect]]:
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
    return obj


def _render(
    obj: Union[Annotation, ContentObject, Element, Rect],
    page: Union[Page, None] = None,
    dpi: int = 72,
) -> Image.Image:
    if page is None:
        if isinstance(obj, tuple):
            raise ValueError("Must explicitly specify page or image to show rectangles")
        page = obj.page
    if page is None:
        raise ValueError("No page found in object: %r" % (obj,))
    return show(page, dpi=dpi)


def box(
    objs: Union[
        Annotation,
        ContentObject,
        Element,
        Rect,
        Iterable[Union[Annotation, ContentObject, Element, Rect]],
    ],
    *,
    color: Union[str, Dict[str, str]] = "red",
    label: bool = True,
    label_color: str = "white",
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
    for obj in _make_boxes(objs):
        if image is None:
            image = _render(obj, page, dpi)
        try:
            left, top, right, bottom = (x * scale for x in boxfunc(obj))
        except ValueError:  # it has no content and no box
            continue
        draw = ImageDraw.ImageDraw(image)
        obj_color = (
            color if isinstance(color, str) else color.get(labelfunc(obj), "red")
        )
        draw.rectangle((left, top, right, bottom), outline=obj_color)
        if label:
            text = labelfunc(obj)
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
        Annotation,
        ContentObject,
        Element,
        Rect,
        Iterable[Union[Annotation, ContentObject, Element, Rect]],
    ],
    *,
    color: Union[str, Dict[str, str]] = "red",
    transparency: float = 0.75,
    label: bool = False,
    label_color: str = "white",
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
    for obj in _make_boxes(objs):
        if image is None:
            image = _render(obj, page, dpi)
        if overlay is None:
            overlay = Image.new("RGB", image.size)
        if mask is None:
            mask = Image.new("L", image.size, 255)
        try:
            left, top, right, bottom = (x * scale for x in boxfunc(obj))
        except ValueError:  # it has no content and no box
            continue
        draw = ImageDraw.ImageDraw(overlay)
        obj_color = (
            color if isinstance(color, str) else color.get(labelfunc(obj), "red")
        )
        draw.rectangle((left, top, right, bottom), fill=obj_color)
        mask_draw = ImageDraw.ImageDraw(mask)
        mask_draw.rectangle((left, top, right, bottom), fill=alpha)
        if outline:
            draw.rectangle((left, top, right, bottom), outline="black")
            mask_draw.rectangle((left, top, right, bottom), outline=0)
        if label:
            text = labelfunc(obj)
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
