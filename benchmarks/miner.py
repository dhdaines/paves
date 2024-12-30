"""Benchmark pdfminer.six against PAVÉS"""

import time
from typing import Union
from pdfminer.high_level import extract_pages
from paves.miner import extract, LAParams
from pathlib import Path


def benchmark_single(path: Path):
    for page in extract_pages(path):
        pass


def benchmark_multi(path: Path, ncpu: Union[int, None]):
    for page in extract(path, laparams=LAParams(), max_workers=ncpu):
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--ncpu", type=int, default=None)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()

    start = time.time()
    benchmark_multi(args.pdf, args.ncpu)
    multi_time = time.time() - start
    print(
        "PAVÉS (%r CPUs) took %.2fs"
        % (
            "all" if args.ncpu is None else args.ncpu,
            multi_time,
        )
    )

    start = time.time()
    benchmark_single(args.pdf)
    single_time = time.time() - start
    print("pdfminer.six (single) took %.2fs" % (single_time,))
