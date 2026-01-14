"""
Common interface for table detectors.
"""

from os import PathLike
from typing import Callable, Iterator, List, Protocol, Tuple, Union
from playa import Document, Page, PageList

from paves.tables.table import TableObject


class Detector(Protocol):
    """Protocol for table detectors."""

    def __call__(
        self,
        pdf: Union[str, PathLike, Document, Page, PageList],
    ) -> Union[Iterator[TableObject], None]: ...

    __name__: str


DETECTORS: List[Tuple[int, Detector]] = []


def detector(*, priority: int) -> Callable[[Detector], Detector]:
    """Decorator to register detector functions with priorities."""

    def register(func: Detector) -> Detector:
        DETECTORS.append((priority, func))
        # We don't care about the inefficiency of this as there are
        # only ever going to be a few of them
        DETECTORS.sort()
        return func

    return register


def lookup(name: str) -> Union[Detector, None]:
    """Look up a detector by name."""
    for _, d in DETECTORS:
        if d.__name__ == name:
            return d
    return None


def tables_orelse(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages, or fail.

    This works like `tables` but forces you (if you use type checking)
    to detect the case where tables cannot be detected by any known
    method.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
        An iterator over `TableObject`, or `None`, if there is no
        method available to detect tables.  This will cause a
        `TypeError` if you try to iterate over it anyway.

    """
    for _, method in DETECTORS:
        itor = method(pdf)
        if itor is not None:
            return itor
    else:
        return None


def tables(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[TableObject]:
    """Identify tables in a PDF or one of its pages.

    This will always try to use logical structure (via PLAYA-PDF)
    first to identify tables.

    For the moment, this only works on tagged and accessible PDFs.
    So, like `paves.image`, it can also use Machine Learning Models™
    to do so, which involves nasty horrible dependencyses (we hates
    them, they stole the precious) like `cudnn-10-gigabytes-of-c++`.

    If you'd like to try that, then you can do so by installing the
    `transformers[torch]` package (if you don't have a GPU, try adding
    `--extra-index-url https://download.pytorch.org/whl/cpu` to pip's
    command line).

    Note: These tables cannot span multiple pages.
        Often, a table will span multiple pages.  With PDF logical
        structure, this can be represented (and sometimes is), but if
        there is no logical structure, this is not possible, since
        tables are detected from the rendered image of a page.
        Reconstructing this information is both extremely important
        and also very difficult with current models (perhaps very big
        VLMs can do it?).  Since we also want to visualize tables with
        `paves.image`, we don't return multi-page tables here.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
        An iterator over `TableObject`.  If no method is available to
        detect tables, this will return an iterator over an empty
        list.  You may wish to use `tables_orelse` to ensure that
        tables can be detected.

    """
    itor = tables_orelse(pdf)
    if itor is None:
        return iter(())
    return itor
