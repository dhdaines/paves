"""
Test PLAYA-Bear functionality.
"""

import warnings
from pathlib import Path

import playa
from paves.bears import extract_page, extract

THISDIR = Path(__file__).parent


def test_playa_extract():
    path = THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    with playa.open(path) as pdf:
        for page in pdf.pages:
            if page.page_idx == 20:  # do not take forever
                break
            layout = list(extract_page(page))
            with warnings.catch_warnings():
                playa_layout = list(page.layout)
            # Fill in missing information
            for dic in playa_layout:
                dic["page_index"] = page.page_idx
                dic["page_label"] = page.label
            assert layout == playa_layout


def test_extract():
    path = THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    for idx, dic in enumerate(extract(path)):
        if idx == 10000:
            break


if __name__ == "__main__":
    test_extract()
