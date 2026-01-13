"""
Detect tables using RT-DETR models from IBM Docling project.
"""

import logging
from functools import singledispatch
from os import PathLike
from typing import Iterable, Iterator, List, Tuple, Union, cast

import playa
from playa import Document, Page, PageList, Rect

import paves.image as pi
from paves.tables.detectors import detector
from paves.tables.table import TableObject

LOGGER = logging.getLogger(__name__)


@singledispatch
def _get_pages(pdf: Union[str, PathLike, Document, Page, PageList]) -> Iterator[Page]:
    raise NotImplementedError


@_get_pages.register(str)
@_get_pages.register(PathLike)
def _get_pages_path(pdf: Union[str, PathLike]) -> Iterator[Page]:
    with playa.open(pdf) as doc:
        yield from doc.pages


@_get_pages.register
def _get_pages_pagelist(pagelist: PageList) -> Iterator[Page]:
    yield from pagelist


@_get_pages.register
def _get_pages_doc(doc: Document) -> Iterator[Page]:
    yield from doc.pages


@_get_pages.register
def _get_pages_page(page: Page) -> Iterator[Page]:
    yield page


def table_bounds_to_objects(
    pdf: Union[str, PathLike, Document, Page, PageList],
    bounds: Iterable[Tuple[int, Iterable[Rect]]],
) -> Iterator[TableObject]:
    """Create TableObjects from detected bounding boxes."""
    for page, (page_idx, tables) in zip(_get_pages(pdf), bounds):
        assert page.page_idx == page_idx
        for bbox in tables:
            yield TableObject.from_bbox(page, bbox)


def table_bounds(
    pdf: Union[str, PathLike, Document, Page, PageList]
) -> Iterator[Tuple[int, List[Rect]]]:
    """Iterate over all text objects in a PDF, page, or pages"""
    import torch
    from transformers import AutoImageProcessor, AutoModelForObjectDetection

    processor = AutoImageProcessor.from_pretrained(
        "ds4sd/docling-layout-old", use_fast=True
    )
    # FIXME: sorry, AMD owners, and everybody else, this will get fixed
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_device = torch.device(device)
    model = AutoModelForObjectDetection.from_pretrained("ds4sd/docling-layout-old").to(
        torch_device
    )
    width = processor.size["width"]
    height = processor.size["height"]
    # Labels are off-by-one for no good reason
    table_label = int(model.config.label2id["Table"]) - 1
    # We could do this in a batch, but that easily runs out of memory
    with torch.inference_mode():
        for image in pi.convert(pdf, width=width, height=height):
            inputs = processor(images=[image], return_tensors="pt").to(torch_device)
            outputs = model(**inputs)
            results = processor.post_process_object_detection(
                outputs,
                target_sizes=[(image.info["page_height"], image.info["page_width"])],
            )
            boxes: List[Rect] = []
            for label, box in zip(results[0]["labels"], results[0]["boxes"]):
                if label.item() != table_label:
                    continue
                bbox = tuple(round(x) for x in box.tolist())
                assert len(bbox) == 4
                boxes.append(cast(Rect, bbox))
            yield image.info["page_index"], boxes


@detector(priority=50)
def detr(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages using IBM's
    RT-DETR layout detection model

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
      An iterator over `TableObject`, or `None`, if the model can't be used
    """
    try:
        return table_bounds_to_objects(pdf, table_bounds(pdf))
    except ImportError:
        return None
