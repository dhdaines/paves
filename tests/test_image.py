import sys
from dataclasses import dataclass
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
    images = list(pi.popple(path))
    assert len(images) == 15
    assert all("page_width" in image.info for image in images)
    with playa.open(path) as pdf:
        images = list(pi.popple(pdf))
        assert len(images) == len(pdf.pages)
        assert all("page_height" in image.info for image in images)
        images = list(pi.popple(pdf.pages[1:6]))
        assert len(images) == 5
        assert all("page_width" in image.info for image in images)
        images = list(pi.popple(pdf.pages[[3, 4, 5, 9, 10]]))
        assert len(images) == 5
        assert all("page_height" in image.info for image in images)
        images = list(pi.popple(pdf.pages[1]))
        assert len(images) == 1
        assert all("page_width" in image.info for image in images)


def test_pdfium():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        images = list(pi.pdfium(path))
        assert len(images) == len(pdf.pages)
        assert all("page_width" in image.info for image in images)
        images = list(pi.pdfium(pdf))
        assert len(images) == len(pdf.pages)
        assert all("page_height" in image.info for image in images)
        images = list(pi.pdfium(pdf.pages[1:6]))
        assert len(images) == 5
        assert all("page_width" in image.info for image in images)
        images = list(pi.pdfium(pdf.pages[[3, 4, 5, 9, 10]]))
        assert len(images) == 5
        assert all("page_height" in image.info for image in images)
        images = list(pi.pdfium(pdf.pages[1]))
        assert len(images) == 1
        assert all("page_width" in image.info for image in images)


def test_box():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        page = pdf.pages[0]
        img = pi.box(page)
        assert img
        img = pi.box(page, color="red")
        assert img
        img = pi.box(page, color=["green", "orange", "purple"])
        assert img
        img = pi.box(page, dpi=100, color={"text": "red", "image": "green"})
        assert img

        @dataclass
        class PagyThing:
            bbox: playa.Rect
            page: playa.Page

        img = pi.box(PagyThing(bbox=(1, 2, 3, 4), page=page))
        assert img
        img = pi.box([(1, 2, 3, 4), (4, 5, 6, 7)], image=pi.show(page))
        assert img
        img = pi.box(iter([(1, 2, 3, 4), (4, 5, 6, 7)]), image=pi.show(page))
        assert img
        img = pi.box(((1, 2, 3, 4), (4, 5, 6, 7)), image=pi.show(page))
        assert img

        @dataclass
        class BoxyThing:
            bbox: playa.Rect

        img = pi.box(BoxyThing(bbox=(1, 2, 3, 4)), image=pi.show(page))
        assert img
        img = pi.box(
            [BoxyThing(bbox=(1, 2, 3, 4)), BoxyThing(bbox=(4, 5, 6, 7))],
            image=pi.show(page),
        )
        assert img


def test_mark():
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        page = pdf.pages[0]
        img = pi.mark(page)
        assert img
        img = pi.mark(page, color="red")
        assert img
        img = pi.mark(page, color=["green", "orange", "purple"])
        assert img
        img = pi.mark(page, dpi=100, color={"text": "red", "image": "green"})
        assert img
