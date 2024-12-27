"""
Test PLAYA functionality.
"""

from pathlib import Path

import playa
from paves.playa import extract_page

THISDIR = Path(__file__).parent


def test_playa_extract():
    with playa.open(
        THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    ) as pdf:
        for idx in range(50):  # FIXME: PLAYA bug
            layout = list(extract_page(pdf.pages[idx]))
            playa_layout = list(pdf.pages[idx].layout)
            assert layout == playa_layout


if __name__ == "__main__":
    test_playa_extract()
