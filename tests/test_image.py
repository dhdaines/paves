import sys
from pathlib import Path

import pytest

import playa
import paves.image as pi

THISDIR = Path(__file__).parent


@pytest.mark.skipif(
    sys.platform.startswith("win") or sys.platform.startswith("darwin"),
    reason="Poppler Probably not Present on Proprietary Platforms",
)
def test_popple():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        images = list(pi.popple(path))
        assert len(images) == len(pdf.pages)
        images = list(pi.popple(pdf))
        assert len(images) == len(pdf.pages)
        images = list(pi.popple(pdf.pages[1:6]))
        assert len(images) == 5
        images = list(pi.popple(pdf.pages[[3, 4, 5, 9, 10]]))
        assert len(images) == 5
        images = list(pi.popple(pdf.pages[1]))
        assert len(images) == 1


def test_pdfium():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        images = list(pi.pdfium(path))
        assert len(images) == len(pdf.pages)
        images = list(pi.pdfium(pdf))
        assert len(images) == len(pdf.pages)
        images = list(pi.pdfium(pdf.pages[1:6]))
        assert len(images) == 5
        images = list(pi.pdfium(pdf.pages[[3, 4, 5, 9, 10]]))
        assert len(images) == 5
        images = list(pi.pdfium(pdf.pages[1]))
        assert len(images) == 1


def test_box():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        page = pdf.pages[0]
        img = pi.box(page)
        assert img


def test_mark():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        page = pdf.pages[0]
        img = pi.mark(page)
        assert img
