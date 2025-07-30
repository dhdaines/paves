from pathlib import Path

import playa
import paves.text as pt

THISDIR = Path(__file__).parent


def test_words_pdf() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        list(pt.words(pdf))


def test_words_page() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        list(pt.words(pdf.pages[0]))


def test_words_pagelist() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        list(pt.words(pdf.pages[0:4]))


def test_words_path() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    list(pt.words(path))
