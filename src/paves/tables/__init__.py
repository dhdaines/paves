"""
Simple and not at all Java-damaged interface for table detection.
"""

from paves.tables.detectors import lookup as detector
from paves.tables.detectors import tables, tables_orelse
from paves.tables.detr import docling_heron as tables_detr
from paves.tables.detr import table_transformer as tables_tatr
from paves.tables.structure import structure as tables_structure

__all__ = [
    "tables",
    "tables_orelse",
    "detector",
    "tables_structure",
    "tables_tatr",
    "tables_detr",
]
