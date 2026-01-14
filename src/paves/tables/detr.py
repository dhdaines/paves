"""
Detect tables using RT-DETR models from IBM Docling project, or
Microsoft Table Transformer (which is also DETR).
"""

import logging
from functools import singledispatch
from os import PathLike
from typing import Any, Iterator, List, Tuple, Union

import paves.image as pi
import playa
from paves.tables.detectors import detector
from paves.tables.table import TableObject
from playa import Document, Page, PageList, Rect

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


def make_rect(box: List[Union[int, float]]) -> Rect:
    """Verify and create a bounding box as tuple of ints."""
    rect = tuple(round(x) for x in box)
    if len(rect) != 4:
        raise TypeError(f"Rectangle does not have 4 corners: {box}")
    return rect


def detect_objects(
    pdf: Union[str, PathLike, Document, Page, PageList],
    model_name: str,
    *,
    model_kwargs: dict[str, Any] | None = None,
    threshold: float = 0.5,
) -> Iterator[Tuple[int, List[Tuple[str, Rect]]]]:
    """Iterate over all text objects in a PDF, page, or pages"""
    import torch
    from transformers import AutoImageProcessor, AutoModelForObjectDetection

    processor = AutoImageProcessor.from_pretrained(model_name, use_fast=True)
    # FIXME: sorry, AMD owners, and everybody else, this will get fixed
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_device = torch.device(device)
    if model_kwargs is None:
        model_kwargs = {}
    model = AutoModelForObjectDetection.from_pretrained(model_name, **model_kwargs).to(
        torch_device
    )

    # Concoct some arguments for pi.convert (FIXME: should be able to
    # pass it processor.size directly)
    dpi = 0
    if "width" in processor.size or "height" in processor.size:
        width = processor.size["width"]
        height = processor.size["height"]
    elif "longest_edge" in processor.size:
        # FIXME: This isn't really what it means, but it works anyway
        width = height = processor.size["longest_edge"]
    else:
        # Render it big and let the model figure it out
        dpi = 144

    # We could do this in a batch, but that easily runs out of memory
    with torch.inference_mode():
        for image in pi.convert(pdf, dpi=dpi, width=width, height=height):
            inputs = processor(images=[image], return_tensors="pt").to(torch_device)
            outputs = model(**inputs)
            results = processor.post_process_object_detection(
                outputs,
                target_sizes=[(image.info["page_height"], image.info["page_width"])],
                threshold=threshold,
            )
            boxes: List[Tuple[str, Rect]] = []
            for label, box in zip(results[0]["labels"], results[0]["boxes"]):
                name = model.config.id2label[label.item()]
                bbox = make_rect(box.tolist())
                boxes.append((name, bbox))
            yield image.info["page_index"], boxes


@detector(priority=10)
def docling_heron(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages using Docling Project
    layout model.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
      An iterator over `TableObject`, or `None`, if the model can't be used

    """
    try:
        detected = detect_objects(pdf, "docling-project/docling-layout-heron")
    except ImportError:
        return None

    def itor() -> Iterator[TableObject]:
        for page, (page_idx, objects) in zip(_get_pages(pdf), detected):
            assert page.page_idx == page_idx
            for label, bbox in objects:
                if label == "Table":
                    yield TableObject.from_bbox(page, bbox)

    return itor()


@detector(priority=20)
def table_transformer(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Union[Iterator[TableObject], None]:
    """Identify tables in a PDF or one of its pages using Microsoft Table
    Transformer model.

    Args:
        pdf: PLAYA-PDF document, page, pages, or path to a PDF.

    Returns:
      An iterator over `TableObject`, or `None`, if the model can't be used

    """
    try:
        detected = detect_objects(
            pdf,
            "microsoft/table-transformer-detection",
            model_kwargs={"revision": "no_timm"},
            threshold=0.9,
        )
    except ImportError:
        return None

    def itor() -> Iterator[TableObject]:
        for page, (page_idx, objects) in zip(_get_pages(pdf), detected):
            assert page.page_idx == page_idx
            for label, bbox in objects:
                yield TableObject.from_bbox(page, bbox)

    return itor()
