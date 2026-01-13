"""
Simple and not at all Java-damaged interface for table detection.
"""

from paves.tables.detectors import tables, tables_orelse
from paves.tables.logical_structure import tables_structure
try:
    from paves.tables.detr import tables_detr
except ImportError:
    pass

__all__ = ["tables", "tables_orelse", "tables_structure", "tables_detr"]
