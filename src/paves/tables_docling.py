"""
Totally optional Docling-based detection of tables.

Also uses pypdfium2 since that's not too much more trouble if you've
already got docling-ibm-models and the ton of c++ junk it pulls in.
"""

import logging
from functools import singledispatch
from os import PathLike
from pathlib import Path
from typing import Iterator, Tuple, Union, TYPE_CHECKING

from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor
from huggingface_hub import hf_hub_download
from pypdfium2 import PdfPage  # type: ignore

from paves.image import _get_pdfium_pages
from playa import Document, Page, PageList

if TYPE_CHECKING:
    from playa.pdftypes import Rect

LOGGER = logging.getLogger(__name__)


def scale_to_model(page: PdfPage, modeldim: Union[float, dict]):
    """Find scaling factor for model dimension."""
    if isinstance(modeldim, dict):
        width = modeldim.get("width", 640)
        height = modeldim.get("height", 640)
        return min(page.get_width() / width,
                   page.get_height() / height)
    mindim = min(page.get_width(), page.get_height())
    return modeldim / mindim


def load_model_from_hub() -> Path:
    hf_hub_download(
        repo_id="ds4sd/docling-models",
        filename="model_artifacts/layout/preprocessor_config.json",
        revision="v2.2.0",
    )
    hf_hub_download(
        repo_id="ds4sd/docling-models",
        filename="model_artifacts/layout/config.json",
        revision="v2.2.0",
    )
    weights_path = hf_hub_download(
        repo_id="ds4sd/docling-models",
        filename="model_artifacts/layout/model.safetensors",
        revision="v2.2.0",
    )
    return Path(weights_path).parent


class ObjetsDocling:
    """Détecteur d'objects textuels utilisant RT-DETR."""

    def __init__(
        self,
        model_path: Union[str, PathLike, None] = None,
        torch_device: str = "cpu",
        num_threads: int = 4,
        base_threshold: float = 0.3,
    ) -> None:
        if model_path is None:
            model_path = load_model_from_hub()
        else:
            model_path = Path(model_path)
        self.model = LayoutPredictor(
            str(model_path),
            device=torch_device,
            num_threads=num_threads,
            base_threshold=base_threshold,
        )
        self.model_info = self.model.info()

    def detect(self, page: PdfPage) -> Iterator["Rect"]:
        scale = scale_to_model(page, self.model_info["image_size"])
        image = page.render(scale=scale).to_pil()

        def boxsort(box):
            """Sort by topmost-leftmost-tallest-widest."""
            return (
                box["t"],
                box["l"],
                -(box["b"] - box["t"]),
                -(box["r"] - box["l"]),
            )

        boxes = sorted(self.model.predict(image), key=boxsort)
        for box in boxes:
            if box["label"] == "Table":
                yield tuple(
                    x / scale
                    for x in (box["l"], box["t"], box["r"], box["b"])
                )


DETECTOR: Union[ObjetsDocling, None] = None


@singledispatch
def table_bounds(
    pdf: Union[str, PathLike, Document, Page, PageList],
) -> Iterator[Tuple[int, "Rect"]]:
    """Iterate over all text objects in a PDF, page, or pages"""
    global DETECTOR
    if DETECTOR is None:
        # Fail fast if we can't get it...
        DETECTOR = ObjetsDocling()
    for idx, page in _get_pdfium_pages(pdf):
        for box in DETECTOR.detect(page):
            yield idx, box
