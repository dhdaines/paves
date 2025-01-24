import sys
from pathlib import Path

import pytest

import playa
from paves.image import popple

THISDIR = Path(__file__).parent


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Poppler Probably not Present on Proprietary Platforms",
)
def test_popple():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        images = list(popple(path))
        assert len(images) == len(pdf.pages)
        images = list(popple(pdf))
        assert len(images) == len(pdf.pages)
        images = list(popple(pdf.pages[1:6]))
        assert len(images) == 5
        images = list(popple(pdf.pages[[3, 4, 5, 9, 10]]))
        assert len(images) == 5
        images = list(popple(pdf.pages[1]))
        assert len(images) == 1
