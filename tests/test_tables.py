from pathlib import Path

import playa
import paves.tables as pb

THISDIR = Path(__file__).parent


def test_tables() -> None:
    path = THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    with playa.open(path) as pdf:
        tables = pb.tables(pdf.pages[300])
        assert tables is not None
        assert len(list(tables)) == 2


def test_no_tables() -> None:
    path = THISDIR / "contrib" / "PSC_Station.pdf"
    with playa.open(path) as pdf:
        tables = pb.tables(pdf)
        assert tables is not None
        assert len(list(tables)) == 0


def test_multi_page_tables() -> None:
    path = THISDIR / "data" / "multi-page-table.pdf"
    with playa.open(path) as pdf:
        itor = pb.tables_orelse(pdf)
        assert itor is not None
        tables = list(itor)
        assert len(tables) == 2
        assert tables[0].parent == tables[1].parent
        table1 = next(pb.tables(pdf.pages[0]))
        table2 = next(pb.tables(pdf.pages[1]))
        assert table1.page == pdf.pages[0]
        assert table2.page == pdf.pages[1]
        assert table1.bbox != table2.bbox
