"""
Test PLAYA-Bear functionality.
"""

from pathlib import Path

from paves.bears import extract

THISDIR = Path(__file__).parent


def test_extract():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    for idx, dic in enumerate(extract(path)):
        if "image_colorspace" in dic:
            assert dic["image_colorspace"].name == "ICCBased"


if __name__ == "__main__":
    test_extract()
