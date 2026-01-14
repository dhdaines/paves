"""Benchmark table detection with logical structure."""

import time
from pathlib import Path

import playa
import paves.tables as pt


def benchmark(detector, path: Path):
    with playa.open(path) as doc:
        for table in detector(doc):
            print(table.page.page_idx, table.bbox)


def benchmark_pagelist(detector, path: Path):
    with playa.open(path) as doc:
        for table in detector(doc.pages):
            print(table.page.page_idx, table.bbox)


def benchmark_pages(detector, path: Path):
    with playa.open(path) as doc:
        for page in doc.pages:
            for table in detector(page):
                print(page.page_idx, table.bbox)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--over", choices=["doc", "page", "pagelist"], default="doc")
    parser.add_argument(
        "--detector",
        choices=["structure", "docling_heron", "table_transformer"],
        default="structure",
    )
    args = parser.parse_args()

    detector = pt.detector(args.detector)
    if detector is None:
        parser.error(f"Unknown detector {args.detector}")
    if args.over == "doc":
        start = time.time()
        benchmark(detector, args.pdf)
        multi_time = time.time() - start
        print("Full document took %.2fs" % multi_time)
    elif args.over == "pagelist":
        start = time.time()
        benchmark_pagelist(detector, args.pdf)
        multi_time = time.time() - start
        print("PageList took %.2fs" % multi_time)
    elif args.over == "page":
        start = time.time()
        benchmark_pages(detector, args.pdf)
        multi_time = time.time() - start
        print("Page took %.2fs" % multi_time)
