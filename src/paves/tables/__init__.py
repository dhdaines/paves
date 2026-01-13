"""
Simple and not at all Java-damaged interface for table detection.
"""

from paves.tables.detectors import tables, tables_orelse
from paves.tables.detectors import lookup as detector
from paves.tables.structure import structure as tables_structure
from paves.tables.detr import detr as tables_detr

__all__ = ["tables", "tables_orelse", "detector", "tables_structure", "tables_detr"]
