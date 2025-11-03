"""
CSV parser implementation for millwork room specifications.

Implements robust CSV parsing with type validation, following the schema
defined in schema.py and validation rules from tech_specs.md section 4.
"""

import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass

from .schema import RoomSchema, FieldDefinition, FieldType, ParsedRoomData
from ..core.interfaces import ValidationResult


@dataclass
class ParsedValue:
    """Result of parsing a single field value."""
    value: Any
    is_valid: bool
    error_message: Optional[str] = None


class FieldParser:
    """Utility class for parsing individual field values based on schema."""
    
    @staticmethod
    def parse_string(value: str, field_def: FieldDefinition) -> ParsedValue:
        """Parse string field with pattern and length validation."""
        if not isinstance(value, str):
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"Expected string, got {type(value).__name__}"
            )
        
        # Check length constraints
        if field_def.min_length is not None and len(value) < field_def.min_length:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"String too short: {len(value)} < {field_def.min_length}"
            )
        
        if field_def.max_length is not None and len(value) > field_def.max_length:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"String too long: {len(value)} > {field_def.max_length}"
            )
        
        # Check pattern constraint
        if field_def.pattern is not None:
            if not re.match(field_def.pattern, value):
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message=f"String does not match pattern: {field_def.pattern}"
                )
        
        # Check enum constraint
        if field_def.enum_values is not None:
            if value not in field_def.enum_values:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message=f"Value not in allowed set: {field_def.enum_values}"
                )
        
        return ParsedValue(value=value, is_valid=True)
    
    @staticmethod
    def parse_number(value: str, field_def: FieldDefinition) -> ParsedValue:
        """Parse numeric field with range validation."""
        try:
            # Handle empty string
            if not value or value.strip() == "":
                if field_def.required:
                    return ParsedValue(
                        value=None,
                        is_valid=False,
                        error_message="Required field cannot be empty"
                    )
                else:
                    return ParsedValue(value=None, is_valid=True)
            
            numeric_value = float(value)
            
            # Check range constraints
            if field_def.min_value is not None and numeric_value < field_def.min_value:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message=f"Value too small: {numeric_value} < {field_def.min_value}"
                )
            
            if field_def.max_value is not None and numeric_value > field_def.max_value:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message=f"Value too large: {numeric_value} > {field_def.max_value}"
                )
            
            return ParsedValue(value=numeric_value, is_valid=True)
            
        except (ValueError, TypeError) as e:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"Invalid number format: {e}"
            )
    
    @staticmethod
    def parse_integer(value: str, field_def: FieldDefinition) -> ParsedValue:
        """Parse integer field with range validation."""
        try:
            # Handle empty string
            if not value or value.strip() == "":
                if field_def.required:
                    return ParsedValue(
                        value=None,
                        is_valid=False,
                        error_message="Required field cannot be empty"
                    )
                else:
                    return ParsedValue(value=None, is_valid=True)
            
            # Check if it's a valid integer (no decimal point)
            if '.' in value:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message="Expected integer, got decimal number"
                )
            
            integer_value = int(value)
            
            # Check range constraints
            if field_def.min_value is not None and integer_value < field_def.min_value:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message=f"Value too small: {integer_value} < {field_def.min_value}"
                )
            
            if field_def.max_value is not None and integer_value > field_def.max_value:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message=f"Value too large: {integer_value} > {field_def.max_value}"
                )
            
            return ParsedValue(value=integer_value, is_valid=True)
            
        except (ValueError, TypeError) as e:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"Invalid integer format: {e}"
            )
    
    @staticmethod
    def parse_boolean(value: str, field_def: FieldDefinition) -> ParsedValue:
        """Parse boolean field."""
        if not value or value.strip() == "":
            if field_def.required:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message="Required field cannot be empty"
                )
            else:
                return ParsedValue(value=None, is_valid=True)
        
        value_lower = value.lower().strip()
        
        if value_lower in ['true', '1', 'yes', 'y']:
            return ParsedValue(value=True, is_valid=True)
        elif value_lower in ['false', '0', 'no', 'n']:
            return ParsedValue(value=False, is_valid=True)
        else:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"Invalid boolean value: {value} (expected true/false)"
            )
    
    @staticmethod
    def parse_string_list(value: str, field_def: FieldDefinition) -> ParsedValue:
        """Parse JSON array string into list of numbers."""
        if not value or value.strip() == "":
            if field_def.required:
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message="Required field cannot be empty"
                )
            else:
                return ParsedValue(value=[], is_valid=True)
        
        try:
            # Parse JSON array
            parsed_list = json.loads(value)
            
            # Validate it's a list
            if not isinstance(parsed_list, list):
                return ParsedValue(
                    value=None,
                    is_valid=False,
                    error_message="Expected JSON array, got other type"
                )
            
            # Convert all items to numbers (for module_widths)
            numeric_list = []
            for i, item in enumerate(parsed_list):
                try:
                    numeric_value = float(item)
                    if numeric_value <= 0:
                        return ParsedValue(
                            value=None,
                            is_valid=False,
                            error_message=f"List item {i} must be positive: {numeric_value}"
                        )
                    numeric_list.append(numeric_value)
                except (ValueError, TypeError):
                    return ParsedValue(
                        value=None,
                        is_valid=False,
                        error_message=f"List item {i} is not a valid number: {item}"
                    )
            
            return ParsedValue(value=numeric_list, is_valid=True)
            
        except json.JSONDecodeError as e:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"Invalid JSON array format: {e}"
            )


class CSVParser:
    """
    CSV parser for millwork room specifications.
    
    Implements robust parsing with comprehensive validation following
    the schema and validation rules from tech specifications.
    """
    
    def __init__(self, schema: RoomSchema = None):
        """Initialize parser with schema."""
        self.schema = schema or RoomSchema()
        self.field_parser = FieldParser()
    
    def parse_file(self, file_path: Path) -> Tuple[List[ParsedRoomData], ValidationResult]:
        """
        Parse CSV file and return parsed data with validation results.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Tuple of (parsed_data_list, validation_result)
        """
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        parsed_data = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                delimiter = ','
                if '\t' in sample and sample.count('\t') > sample.count(','):
                    delimiter = '\t'
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                # Validate headers
                if not self._validate_headers(reader.fieldnames, validation_result):
                    return [], validation_result
                
                # Track room IDs for uniqueness validation
                room_ids = set()
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    row_result = self._parse_row(row, row_num, str(file_path))
                    
                    if row_result.is_valid:
                        parsed_room = row_result.data
                        
                        # Check room_id uniqueness
                        if parsed_room.room_id in room_ids:
                            validation_result.add_error(
                                "room_id", 
                                f"Duplicate room_id: {parsed_room.room_id}", 
                                parsed_room.room_id,
                                row_num
                            )
                        else:
                            room_ids.add(parsed_room.room_id)
                            parsed_data.append(parsed_room)
                    else:
                        # Add row-level errors to overall validation result
                        for error in row_result.errors:
                            validation_result.add_error(
                                error.field,
                                error.message,
                                error.value,
                                row_num
                            )
                
        except FileNotFoundError:
            validation_result.add_error("file", f"File not found: {file_path}", str(file_path))
        except PermissionError:
            validation_result.add_error("file", f"Permission denied: {file_path}", str(file_path))
        except Exception as e:
            validation_result.add_error("file", f"Error reading file: {e}", str(file_path))
        
        return parsed_data, validation_result
    
    def _validate_headers(self, headers: List[str], validation_result: ValidationResult) -> bool:
        """Validate CSV headers against schema."""
        if headers is None:
            validation_result.add_error("headers", "No headers found in CSV file", None)
            return False
        
        # Check for required fields
        required_fields = self.schema.get_required_field_names()
        missing_fields = []
        
        for field in required_fields:
            if field not in headers:
                missing_fields.append(field)
        
        if missing_fields:
            validation_result.add_error(
                "headers", 
                f"Missing required fields: {missing_fields}", 
                headers
            )
            return False
        
        # Check for unknown fields
        all_valid_fields = self.schema.get_all_field_names()
        unknown_fields = []
        
        for header in headers:
            if header not in all_valid_fields:
                unknown_fields.append(header)
        
        if unknown_fields:
            validation_result.add_warning(
                "headers",
                f"Unknown fields will be ignored: {unknown_fields}",
                headers
            )
        
        return True
    
    def _parse_row(self, row: Dict[str, str], row_num: int, source_file: str) -> ValidationResult:
        """Parse a single CSV row."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        parsed_values = {}
        
        # Parse each field according to schema
        all_fields = self.schema.get_all_fields()
        
        for field_name, field_def in all_fields.items():
            raw_value = row.get(field_name, "").strip()
            
            # Handle required field validation
            if field_def.required and not raw_value:
                result.add_error(field_name, "Required field is empty", raw_value, row_num)
                continue
            
            # Parse based on field type
            parsed_value = self._parse_field_value(raw_value, field_def)
            
            if not parsed_value.is_valid:
                result.add_error(field_name, parsed_value.error_message, raw_value, row_num)
            else:
                parsed_values[field_name] = parsed_value.value
        
        # If parsing succeeded, create ParsedRoomData object
        if result.is_valid:
            try:
                parsed_room = ParsedRoomData(
                    room_id=parsed_values.get("room_id"),
                    total_length_in=parsed_values.get("total_length_in"),
                    num_modules=parsed_values.get("num_modules"),
                    module_widths=parsed_values.get("module_widths", []),
                    material_top=parsed_values.get("material_top"),
                    material_casework=parsed_values.get("material_casework"),
                    left_filler_in=parsed_values.get("left_filler_in", 0.0),
                    right_filler_in=parsed_values.get("right_filler_in", 0.0),
                    has_sink=parsed_values.get("has_sink", False),
                    has_ref=parsed_values.get("has_ref", False),
                    counter_height_in=parsed_values.get("counter_height_in"),
                    edge_rule=parsed_values.get("edge_rule"),
                    hardware_defaults=parsed_values.get("hardware_defaults"),
                    notes=parsed_values.get("notes"),
                    references=parsed_values.get("references"),
                    row_number=row_num,
                    source_file=source_file,
                )
                result.data = parsed_room
            except Exception as e:
                result.add_error("row", f"Error creating parsed data: {e}", None, row_num)
        
        return result
    
    def _parse_field_value(self, value: str, field_def: FieldDefinition) -> ParsedValue:
        """Parse field value based on its type definition."""
        if field_def.field_type == FieldType.STRING:
            return self.field_parser.parse_string(value, field_def)
        elif field_def.field_type == FieldType.NUMBER:
            return self.field_parser.parse_number(value, field_def)
        elif field_def.field_type == FieldType.INTEGER:
            return self.field_parser.parse_integer(value, field_def)
        elif field_def.field_type == FieldType.BOOLEAN:
            return self.field_parser.parse_boolean(value, field_def)
        elif field_def.field_type == FieldType.STRING_LIST:
            return self.field_parser.parse_string_list(value, field_def)
        else:
            return ParsedValue(
                value=None,
                is_valid=False,
                error_message=f"Unknown field type: {field_def.field_type}"
            )