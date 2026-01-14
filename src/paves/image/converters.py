"""
Common interface for image converters.
"""

from os import PathLike
from typing import Callable, Iterator, List, Protocol, Tuple, Union
from playa import Document, Page, PageList
from PIL import Image

from paves.exceptions import NotInstalledError


class Converter(Protocol):
    """Protocol for image to PDF converters."""

    def __call__(
        self,
        pdf: Union[str, PathLike, Document, Page, PageList],
        *,
        dpi: int = 0,
        width: int = 0,
        height: int = 0,
    ) -> Iterator[Image.Image]: ...

    __name__: str


CONVERTERS: List[Tuple[int, Converter]] = []


def converter(*, priority: int) -> Callable[[Converter], Converter]:
    """Decorator to register converter functions with priorities."""

    def register(func: Converter) -> Converter:
        CONVERTERS.append((priority, func))
        # We don't care about the inefficiency of this as there are
        # only ever going to be a few of them
        CONVERTERS.sort()
        return func

    return register


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
        Pillow `Image.Image` objects, one per page.  The original page
        width and height in default user space units are available in
        the `info` property of these images as `page_width` and
        `page_height`
    Raises:
        ValueError: Invalid arguments (e.g. both `dpi` and `width`/`height`)
        NotInstalledError: If no renderer is available

    """
    for _, convert in CONVERTERS:
        try:
            for img in convert(pdf, dpi=dpi, width=width, height=height):
                yield img
            break
        except NotInstalledError:
            continue
    else:
        raise NotInstalledError(
            "No converters available, tried: %s"
            % (", ".join(m.__name__ for _, m in CONVERTERS))
        )
