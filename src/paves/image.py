"""
Various ways of converting PDFs to images for feeding them to
models and/or visualisation.`
"""

import functools
import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import Dict, Iterable, Iterator, Union, List, TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFont
from playa.document import Document, PageList
from playa.page import ContentObject, Page


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


def box(
    objs: Iterable[ContentObject],
    *,
    color: Union[str, Dict[str, str]] = "red",
    label: bool = True,
    label_color: str = "white",
    label_size: int = 9,
    label_margin: int = 1,
    image: Union[Image.Image, None] = None,
) -> Union[Image.Image, None]:
    """Draw boxes around things in a page of a PDF."""
    draw: ImageDraw.ImageDraw
    font = ImageFont.load_default(label_size)
    for obj in objs:
        if image is None:
            image = show(obj.page)
        left, top, right, bottom = obj.bbox
        draw = ImageDraw.ImageDraw(image)
        obj_color = (
            color if isinstance(color, str) else color.get(obj.object_type, "red")
        )
        draw.rectangle((left, top, right, bottom), outline=obj_color)
        if label:
            text = obj.object_type
            tl, tt, tr, tb = font.getbbox(text)
            draw.rectangle(
                (left, top - tb - label_margin * 2, left + tr + label_margin * 2, top),
                outline=obj_color,
                fill=obj_color,
            )
            draw.text(
                xy=(left + label_margin, top - label_margin),
                text=obj.object_type,
                font=font,
                fill="white",
                anchor="ld",
            )
    return image


def mark(
    objs: Iterable[ContentObject],
    *,
    color: Union[str, Dict[str, str]] = "red",
    transparency: float = 0.75,
    label: bool = False,
    label_color: str = "white",
    label_size: int = 9,
    label_margin: int = 1,
    image: Union[Image.Image, None] = None,
) -> Union[Image.Image, None]:
    """Highlight things in a page of a PDF."""
    overlay: Image.Image
    mask: Image.Image
    draw: ImageDraw.ImageDraw
    font = ImageFont.load_default(label_size)
    alpha = min(255, int(transparency * 255))
    for obj in objs:
        if image is None:
            image = show(obj.page)
            overlay = Image.new("RGB", image.size)
            mask = Image.new("L", image.size, 255)
        left, top, right, bottom = obj.bbox
        draw = ImageDraw.ImageDraw(overlay)
        obj_color = (
            color if isinstance(color, str) else color.get(obj.object_type, "red")
        )
        draw.rectangle((left, top, right, bottom), fill=obj_color)
        if label:
            text = obj.object_type
            tl, tt, tr, tb = font.getbbox(text)
            draw.rectangle(
                (left, top - tb - label_margin * 2, left + tr + label_margin * 2, top),
                outline=obj_color,
                fill=obj_color,
            )
            draw.text(
                xy=(left + label_margin, top - label_margin),
                text=obj.object_type,
                font=font,
                fill="white",
                anchor="ld",
            )
        draw = ImageDraw.ImageDraw(mask)
        draw.rectangle((left, top, right, bottom), fill=alpha)
        if label:
            draw.rectangle(
                (left, top - tb - label_margin * 2, left + tr + label_margin * 2, top),
                fill=alpha,
            )
    if image is None:
        return None
    return Image.composite(image, overlay, mask)
