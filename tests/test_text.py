from itertools import groupby
from pathlib import Path

import playa
import paves.text as px

THISDIR = Path(__file__).parent


def test_words_pdf() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        list(px.words(pdf))


def test_words_page() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        texts = [w.text for w in px.words(pdf.pages[0])]
        assert texts == [
            "Réserve",
            "de",
            "biodiversité",
            "projetée",
            "de",
            "la",
            "Station-de-",
            "Biologie-des-",
            "Laurentides",
            "Février",
            "2009",
        ]


def test_words_pagelist() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        list(px.words(pdf.pages[0:4]))


def test_words_path() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    list(px.words(path))


def test_lines() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        lines = [
            " ".join(w.text for w in words)
            for line, words in groupby(px.words(pdf.pages[0]), px.line)
        ]
        assert lines == [
            "Réserve de",
            "biodiversité",
            "projetée de la",
            "Station-de-",
            "Biologie-des-",
            "Laurentides",
            "Février 2009",
        ]
