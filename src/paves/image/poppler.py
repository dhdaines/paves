"""
Convert PDFs to images using poppler command-line tools.
"""

import functools
import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import (
    Iterator,
    List,
    Tuple,
    Union,
)

import playa
from PIL import Image
from playa.document import Document, PageList
from playa.page import Page

from paves.exceptions import NotInstalledError
from paves.image.converters import converter


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
def _popple(pdf, tempdir: Path, args: List[str]) -> List[Tuple[int, float, float]]:
    raise NotImplementedError


@_popple.register(str)
@_popple.register(PathLike)
def _popple_path(
    pdf: Union[str, PathLike], tempdir: Path, args: List[str]
) -> List[Tuple[int, float, float]]:
    subprocess.run(
        [
            "pdftoppm",
            *args,
            str(pdf),
            tempdir / "ppm",
        ],
        check=True,
    )
    with playa.open(pdf) as doc:
        return [(page.page_idx, page.width, page.height) for page in doc.pages]


@_popple.register(Document)
def _popple_doc(
    pdf: Document, tempdir: Path, args: List[str]
) -> List[Tuple[int, float, float]]:
    pdfpdf = tempdir / "pdf.pdf"
    # FIXME: This is... not great (can we popple in a pipeline please?)
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
    pdfpdf.unlink()
    return [(page.page_idx, page.width, page.height) for page in pdf.pages]


@_popple.register(Page)
def _popple_page(
    pdf: Page, tempdir: Path, args: List[str]
) -> List[Tuple[int, float, float]]:
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
    pdfpdf.unlink()
    return [(pdf.page_idx, pdf.width, pdf.height)]


@_popple.register(PageList)
def _popple_pages(
    pdf: PageList, tempdir: Path, args: List[str]
) -> List[Tuple[int, float, float]]:
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
    pdfpdf.unlink()
    return [(page.page_idx, page.width, page.height) for page in pdf]


@converter(priority=10)
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
        # FIXME: Possible to Popple in a Parallel Pipeline
        page_sizes = _popple(pdf, temppath, args)
        for (page_idx, page_width, page_height), ppm in zip(
            page_sizes,
            (path for path in sorted(temppath.iterdir()) if path.suffix == ".ppm"),
        ):
            img = Image.open(ppm)
            img.info["page_index"] = page_idx
            img.info["page_width"] = page_width
            img.info["page_height"] = page_height
            yield img
