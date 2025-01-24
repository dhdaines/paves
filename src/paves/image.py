"""
Various ways of converting PDFs to images for feeding them to
models and/or visualisation.`
"""

import functools
import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import Iterator, Union, List
from PIL import Image
from playa.document import Document, PageList
from playa.page import Page


def make_poppler_args(dpi: int, width: int, height: int) -> List[str]:
    args = []
    if width:
        args.extend(
            [
                "-scale-to-x",
                str(width),
            ]
        )
    if height:
        args.extend(
            [
                "-scale-to-y",
                str(height),
            ]
        )
    if not args:
        args.extend(["-r", str(dpi)])
    return args


@functools.singledispatch
def _popple(pdf, args: List[str]) -> None:
    pass


@_popple.register(PathLike)
def _popple_path(pdf: PathLike, tempdir: Path, args: List[str]) -> None:
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
    pdfpdf = tempdir / "pdf.pdf"
    with open(pdfpdf, "wb") as outfh:
        outfh.write(pdf.doc.buffer)
    page_number = pdf.page_idx + 1
    subprocess.run(
        [
            "pdftoppm",
            *args,
            "-f",
            page_number,
            "-l",
            page_number,
            str(pdfpdf),
            tempdir / "ppm",
        ],
        check=True,
    )


@_popple.register(PageList)
def _popple_pages(pdf: PageList, tempdir: Path, args: List[str]) -> None:
    pdfpdf = tempdir / "pdf.pdf"
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
    pdf: Union[PathLike, Document, Page, PageList],
    *,
    dpi: int = 72,
    width: int = 0,
    height: int = 0,
    **kwargs,
) -> Iterator[Image.Image]:
    """Convert a PDF to images using Poppler's pdftoppm.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.
        dpi: Render to this resolution.
        width: Render to this width in pixels.
        height: Render to this height in pixels.
    Yields:
        Pillow `Image.Image` objects, one per page.
    """
    args = make_poppler_args(dpi, width, height)
    with tempfile.TemporaryDirectory() as tempdir:
        temppath = Path(tempdir)
        _popple(pdf, temppath, args)
        for ppm in sorted(temppath.iterdir()):
            if ppm.suffix == ".ppm":
                yield Image.open(ppm)
