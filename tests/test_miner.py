"""
Test pdfminer.six replacement functionality.
"""

from pathlib import Path

import playa
from paves.miner import extract_page
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage

THISDIR = Path(__file__).parent


def test_miner_extract():
    path = THISDIR / "contrib" / "Rgl-1314-2021-Z-en-vigueur-20240823.pdf"
    with playa.open(path, space="page") as pdf:
        # OMFG as usual
        resource_manager = PDFResourceManager()
        device = PDFPageAggregator(resource_manager)
        interpreter = PDFPageInterpreter(resource_manager, device)
        for idx, (playa_page, pdfminer_page) in enumerate(
            zip(pdf.pages, PDFPage.get_pages(pdf._fp))
        ):
            # Otherwise pdfminer.six is just too darn slow
            if idx == 20:
                break
            paves_ltpage = extract_page(playa_page)
            interpreter.process_page(pdfminer_page)
            pdfminer_ltpage = device.get_result()
            for pv, pm in zip(paves_ltpage, pdfminer_ltpage):
                # Because in its infinite wisdom these have no __eq__
                assert str(pv) == str(pm)


if __name__ == "__main__":
    test_miner_extract()
