"""
Test PLAYA functionality.
"""

from pathlib import Path

import playa
from paves.playa import extract_page

THISDIR = Path(__file__).parent


def test_playa_extract():
    with playa.open(THISDIR / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf") as pdf:
        for page in pdf.pages:
            layout = list(extract_page(page))
            playa_layout = list(page.layout)
            for i, (x, y) in enumerate(zip(layout, playa_layout)):
                if x != y:
                    print(f"paves[{page.label}][{i}]: {x}")
                    print(f"playa[{page.label}][{i}]: {y}")
                    print()


if __name__ == '__main__':
    test_playa_extract()
