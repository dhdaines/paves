"""
Convert PDFs to images using pypdfium2.
"""

import contextlib
import functools
from io import BytesIO
from os import PathLike
from typing import (
    TYPE_CHECKING,
    Iterator,
    Tuple,
    Union,
)

from PIL import Image
from playa.document import Document, PageList
from playa.page import Page

from paves.image.converters import converter
from paves.image.exceptions import NotInstalledError

if TYPE_CHECKING:
    import pypdfium2  # types: ignore


@functools.singledispatch
def _get_pdfium_pages(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[Tuple[int, "pypdfium2.PdfPage"]]:
    import pypdfium2

    doc = pypdfium2.PdfDocument(pdf)
    for idx, page in enumerate(doc):
        yield idx, page
        page.close()
    doc.close()


@contextlib.contextmanager
def _get_pdfium_doc(pdf: Document) -> Iterator["pypdfium2.PdfDocument"]:
    import pypdfium2

    if pdf._fp is None:
        # Yes, you can actually wrap a BytesIO around an mmap!
        with BytesIO(pdf.buffer) as fp:
            doc = pypdfium2.PdfDocument(fp)
            yield doc
            doc.close()
    else:
        doc = pypdfium2.PdfDocument(pdf._fp)
        yield doc
        doc.close()


@_get_pdfium_pages.register(Document)
def _get_pdfium_pages_doc(pdf: Document) -> Iterator[Tuple[int, "pypdfium2.PdfPage"]]:
    with _get_pdfium_doc(pdf) as doc:
        for idx, page in enumerate(doc):
            yield idx, page
            page.close()


@_get_pdfium_pages.register(Page)
def _get_pdfium_pages_page(page: Page) -> Iterator[Tuple[int, "pypdfium2.PdfPage"]]:
    pdf = page.doc
    assert pdf is not None
    with _get_pdfium_doc(pdf) as doc:
        pdfium_page = doc[page.page_idx]
        yield page.page_idx, pdfium_page
        pdfium_page.close()


@_get_pdfium_pages.register(PageList)
def _get_pdfium_pages_pagelist(
    pages: PageList,
) -> Iterator[Tuple[int, "pypdfium2.PdfPage"]]:
    pdf = pages.doc
    assert pdf is not None
    with _get_pdfium_doc(pdf) as doc:
        for page in pages:
            pdfium_page = doc[page.page_idx]
            yield page.page_idx, pdfium_page
            pdfium_page.close()


@converter(priority=20)
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
        Pillow `Image.Image` objects, one per page.  Page width and height are
        available in the `info` property of the images.
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
    for idx, page in _get_pdfium_pages(pdf):
        page_width = page.get_width()
        page_height = page.get_height()
        if width == 0 and height == 0:
            scale = (dpi or 72) / 72
            img = page.render(scale=scale).to_pil()
        else:
            if width and height:
                # Scale to longest side (since pypdfium2 doesn't
                # appear to allow non-1:1 aspect ratio)
                scale = max(width / page_width, height / page_height)
                img = page.render(scale=scale).to_pil()
                # Resize down to desired size
                img = img.resize(size=(width, height))
            elif width:
                scale = width / page.get_width()
                img = page.render(scale=scale).to_pil()
            elif height:
                scale = height / page.get_height()
                img = page.render(scale=scale).to_pil()
        img.info["page_index"] = idx
        img.info["page_width"] = page_width
        img.info["page_height"] = page_height
        yield img
