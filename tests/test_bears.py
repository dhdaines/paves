"""
Test PLAYA-Bear functionality.
"""

from pathlib import Path

import pytest

import playa
from paves.bears import extract_page, extract

THISDIR = Path(__file__).parent


# warnings.capture_warnings does not work in pytest because Reasons
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_playa_extract():
    path = THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    with playa.open(path) as pdf:
        for page in pdf.pages:
            if page.page_idx == 20:  # do not take forever
                break
            layout = list(extract_page(page))
            playa_layout = list(page.layout)
            # Fill in missing information
            for dic in playa_layout:
                dic["page_index"] = page.page_idx
                dic["page_label"] = page.label
                # Correct what is arguably a bug in PLAYA
                if "image_colorspace" in dic:
                    dic["image_colorspace"] = dic["image_colorspace"].name
            assert layout == playa_layout


def test_extract():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    for idx, dic in enumerate(extract(path)):
        if "image_colorspace" in dic:
            # No stream for you! No!
            assert dic["image_colorspace"] == "ICCBased"


if __name__ == "__main__":
    test_extract()
