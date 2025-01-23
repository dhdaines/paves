"""
Various ways of converting PDFs to images for feeding them to
models and/or visualisation.`
"""

import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import Iterator, Union
from playa.document import Document
from PIL import Image


def popple(
    pdf: Union[Document, PathLike],
    *,
    dpi: int = 72,
    width: int = 0,
    height: int = 0,
    **kwargs
) -> Iterator[Image.Image]:
    """Convert a PDF to images using Poppler's pdftoppm.

    Args:
        pdf: PLAYA-PDF document or path to a PDF.
        dpi: Render to this resolution.
        width: Render to this width in pixels.
        height: Render to this height in pixels.
    Yields:
        Pillow `Image.Image` objects, one per page.
    """
    with tempfile.TemporaryDirectory() as tempdir:
        temppath = Path(tempdir)
        if isinstance(pdf, Document):
            path = temppath / "pdf.pdf"
            with open(path, "wb") as outfh:
                outfh.write(pdf.buffer)
        else:
            path = pdf
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
        subprocess.run(
            [
                "pdftoppm",
                *args,
                str(path),
                temppath / "ppm",
            ],
            check=True,
        )
        for ppm in sorted(temppath.iterdir()):
            if ppm.suffix == ".ppm":
                yield Image.open(ppm)
