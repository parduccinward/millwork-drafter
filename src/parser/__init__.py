"""
CSV parsing and validation for millwork specifications.

This module implements the complete data pipeline for Phase 2:
- CSV schema definition and validation
- Robust CSV parsing with type checking
- Comprehensive validation (type, domain, geometric, referential)
- Error reporting and batch processing
"""

from .schema import RoomSchema, FieldDefinition, FieldType, ParsedRoomData
from .csv_parser import CSVParser, FieldParser, ParsedValue
from .validator import RoomValidator, ErrorReporter, BatchValidationSummary

__all__ = [
    "RoomSchema",
    "FieldDefinition", 
    "FieldType",
    "ParsedRoomData",
    "CSVParser",
    "FieldParser",
    "ParsedValue",
    "RoomValidator",
    "ErrorReporter",
    "BatchValidationSummary",
]