"""Benchmark table detection with logical structure."""

import time
from pathlib import Path

import playa
import paves.tables as pb


def benchmark(path: Path):
    with playa.open(path) as doc:
        for table in pb.tables_structure(doc):
            print(table.page.page_idx, table.bbox)


def benchmark_pagelist(path: Path):
    with playa.open(path) as doc:
        for table in pb.tables_structure(doc.pages):
            print(table.page.page_idx, table.bbox)


def benchmark_pages(path: Path):
    with playa.open(path) as doc:
        for page in doc.pages:
            for table in pb.tables_structure(page):
                print(page.page_idx, table.bbox)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--over", choices=["doc", "page", "pagelist"])
    args = parser.parse_args()

    if args.over == "doc":
        start = time.time()
        benchmark(args.pdf)
        multi_time = time.time() - start
        print("Full document took %.2fs" % multi_time)
    elif args.over == "pagelist":
        start = time.time()
        benchmark_pagelist(args.pdf)
        multi_time = time.time() - start
        print("PageList took %.2fs" % multi_time)
    elif args.over == "page":
        start = time.time()
        benchmark_pages(args.pdf)
        multi_time = time.time() - start
        print("Page took %.2fs" % multi_time)
