from pathlib import Path

import playa
import paves.tables as pb

THISDIR = Path(__file__).parent


def test_tables() -> None:
    path = THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    with playa.open(path) as pdf:
        assert len(list(pb.tables(pdf.pages[300]))) == 2


def test_no_tables() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        assert len(list(pb.tables(pdf))) == 0
