"""
Detect tables using RT-DETR models from IBM Docling project.
"""

import logging
from os import PathLike
from typing import Iterator, List, Tuple, Union, cast

import torch
from playa import Document, Page, PageList, Rect
from transformers import AutoImageProcessor, AutoModelForObjectDetection

import paves.image as pi

LOGGER = logging.getLogger(__name__)


def table_bounds(
    pdf: Union[str, PathLike, Document, Page, PageList],
    device: str = "cpu",
) -> Iterator[Tuple[int, List[Rect]]]:
    """Iterate over all text objects in a PDF, page, or pages"""
    processor = AutoImageProcessor.from_pretrained(
        "ds4sd/docling-layout-old", use_fast=True
    )
    device = torch.device(device)
    model = AutoModelForObjectDetection.from_pretrained("ds4sd/docling-layout-old").to(
        device
    )
    width = processor.size["width"]
    height = processor.size["height"]
    # Labels are off-by-one for no good reason
    table_label = int(model.config.label2id["Table"]) - 1
    # We could do this in a batch, but that easily runs out of memory
    with torch.inference_mode():
        for image in pi.convert(pdf, width=width, height=height):
            inputs = processor(images=[image], return_tensors="pt").to(device)
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
