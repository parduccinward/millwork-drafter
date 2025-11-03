"""
Tests for CSV parser implementation.

Tests CSV parsing functionality including type validation, error handling,
and integration with schema as specified in tech_specs.md section 8.
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.parser.csv_parser import CSVParser, FieldParser, ParsedValue
from src.parser.schema import FieldDefinition, FieldType, RoomSchema
from src.core.interfaces import ValidationResult


class TestFieldParser:
    """Test FieldParser utility class."""
    
    def test_parse_string_valid(self):
        """Test parsing valid string values."""
        field_def = FieldDefinition(
            name="test_string",
            field_type=FieldType.STRING,
            min_length=2,
            max_length=10,
            pattern=r'^[A-Z][A-Z0-9\-]*$'
        )
        
        result = FieldParser.parse_string("ABC-123", field_def)
        assert result.is_valid
        assert result.value == "ABC-123"
        assert result.error_message is None
    
    def test_parse_string_invalid(self):
        """Test parsing invalid string values."""
        field_def = FieldDefinition(
            name="test_string",
            field_type=FieldType.STRING,
            min_length=5,
            max_length=10,
            pattern=r'^[A-Z]+$'
        )
        
        # Too short
        result = FieldParser.parse_string("AB", field_def)
        assert not result.is_valid
        assert "String too short" in result.error_message
        
        # Too long
        result = FieldParser.parse_string("ABCDEFGHIJK", field_def)
        assert not result.is_valid
        assert "String too long" in result.error_message
        
        # Pattern mismatch
        result = FieldParser.parse_string("ABC123", field_def)
        assert not result.is_valid
        assert "does not match pattern" in result.error_message
    
    def test_parse_number_valid(self):
        """Test parsing valid number values."""
        field_def = FieldDefinition(
            name="test_number",
            field_type=FieldType.NUMBER,
            min_value=10.0,
            max_value=100.0
        )
        
        result = FieldParser.parse_number("36.5", field_def)
        assert result.is_valid
        assert result.value == 36.5
        
        result = FieldParser.parse_number("10", field_def)
        assert result.is_valid
        assert result.value == 10.0
    
    def test_parse_number_invalid(self):
        """Test parsing invalid number values."""
        field_def = FieldDefinition(
            name="test_number",
            field_type=FieldType.NUMBER,
            min_value=10.0,
            max_value=100.0
        )
        
        # Too small
        result = FieldParser.parse_number("5.0", field_def)
        assert not result.is_valid
        assert "Value too small" in result.error_message
        
        # Too large
        result = FieldParser.parse_number("150.0", field_def)
        assert not result.is_valid
        assert "Value too large" in result.error_message
        
        # Invalid format
        result = FieldParser.parse_number("not_a_number", field_def)
        assert not result.is_valid
        assert "Invalid number format" in result.error_message
    
    def test_parse_integer_valid(self):
        """Test parsing valid integer values."""
        field_def = FieldDefinition(
            name="test_integer",
            field_type=FieldType.INTEGER,
            min_value=1,
            max_value=10
        )
        
        result = FieldParser.parse_integer("5", field_def)
        assert result.is_valid
        assert result.value == 5
    
    def test_parse_integer_invalid(self):
        """Test parsing invalid integer values."""
        field_def = FieldDefinition(
            name="test_integer",
            field_type=FieldType.INTEGER,
            min_value=1,
            max_value=10
        )
        
        # Decimal number
        result = FieldParser.parse_integer("5.5", field_def)
        assert not result.is_valid
        assert "Expected integer, got decimal" in result.error_message
        
        # Out of range
        result = FieldParser.parse_integer("15", field_def)
        assert not result.is_valid
        assert "Value too large" in result.error_message
    
    def test_parse_boolean_valid(self):
        """Test parsing valid boolean values."""
        field_def = FieldDefinition(
            name="test_boolean",
            field_type=FieldType.BOOLEAN
        )
        
        # True values
        for value in ["true", "TRUE", "1", "yes", "y"]:
            result = FieldParser.parse_boolean(value, field_def)
            assert result.is_valid
            assert result.value is True
        
        # False values
        for value in ["false", "FALSE", "0", "no", "n"]:
            result = FieldParser.parse_boolean(value, field_def)
            assert result.is_valid
            assert result.value is False
    
    def test_parse_boolean_invalid(self):
        """Test parsing invalid boolean values."""
        field_def = FieldDefinition(
            name="test_boolean",
            field_type=FieldType.BOOLEAN
        )
        
        result = FieldParser.parse_boolean("maybe", field_def)
        assert not result.is_valid
        assert "Invalid boolean value" in result.error_message
    
    def test_parse_string_list_valid(self):
        """Test parsing valid string list values."""
        field_def = FieldDefinition(
            name="test_list",
            field_type=FieldType.STRING_LIST
        )
        
        result = FieldParser.parse_string_list("[36, 30, 42]", field_def)
        assert result.is_valid
        assert result.value == [36.0, 30.0, 42.0]
        
        result = FieldParser.parse_string_list("[24.5, 48.0]", field_def)
        assert result.is_valid
        assert result.value == [24.5, 48.0]
    
    def test_parse_string_list_invalid(self):
        """Test parsing invalid string list values."""
        field_def = FieldDefinition(
            name="test_list",
            field_type=FieldType.STRING_LIST
        )
        
        # Invalid JSON
        result = FieldParser.parse_string_list("[36, 30,", field_def)
        assert not result.is_valid
        assert "Invalid JSON array format" in result.error_message
        
        # Not an array
        result = FieldParser.parse_string_list("36", field_def)
        assert not result.is_valid
        assert "Expected JSON array" in result.error_message
        
        # Negative value
        result = FieldParser.parse_string_list("[36, -30]", field_def)
        assert not result.is_valid
        assert "must be positive" in result.error_message
        
        # Non-numeric value
        result = FieldParser.parse_string_list("[36, 'abc']", field_def)
        assert not result.is_valid
        assert "Invalid JSON array format" in result.error_message


class TestCSVParser:
    """Test CSVParser class."""
    
    def create_temp_csv(self, content: str) -> Path:
        """Create temporary CSV file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_parse_valid_csv(self):
        """Test parsing a valid CSV file."""
        csv_content = """room_id,total_length_in,num_modules,module_widths,material_top,material_casework
KITCHEN-01,144.0,4,"[36,30,36,42]",QTZ-01,PLM-WHT
BATH-01,72.0,2,"[36,36]",LAM-01,PLM-WHT"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            assert validation_result.is_valid
            assert len(parsed_data) == 2
            
            # Check first room
            room1 = parsed_data[0]
            assert room1.room_id == "KITCHEN-01"
            assert room1.total_length_in == 144.0
            assert room1.num_modules == 4
            assert room1.module_widths == [36.0, 30.0, 36.0, 42.0]
            assert room1.material_top == "QTZ-01"
            assert room1.material_casework == "PLM-WHT"
            
            # Check second room
            room2 = parsed_data[1]
            assert room2.room_id == "BATH-01"
            assert room2.total_length_in == 72.0
            assert room2.num_modules == 2
            assert room2.module_widths == [36.0, 36.0]
            
        finally:
            csv_file.unlink()  # Clean up
    
    def test_parse_csv_with_optional_fields(self):
        """Test parsing CSV with optional fields."""
        csv_content = """room_id,total_length_in,num_modules,module_widths,material_top,material_casework,has_sink,counter_height_in
KITCHEN-01,144.0,4,"[36,30,36,42]",QTZ-01,PLM-WHT,true,36.0"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            assert validation_result.is_valid
            assert len(parsed_data) == 1
            
            room = parsed_data[0]
            assert room.has_sink is True
            assert room.counter_height_in == 36.0
            
        finally:
            csv_file.unlink()
    
    def test_parse_csv_missing_required_field(self):
        """Test parsing CSV with missing required field."""
        csv_content = """room_id,total_length_in,num_modules,material_top,material_casework
KITCHEN-01,144.0,4,QTZ-01,PLM-WHT"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            assert not validation_result.is_valid
            assert len(validation_result.errors) > 0
            assert any("Missing required fields" in error.message for error in validation_result.errors)
            
        finally:
            csv_file.unlink()
    
    def test_parse_csv_invalid_data_types(self):
        """Test parsing CSV with invalid data types."""
        csv_content = """room_id,total_length_in,num_modules,module_widths,material_top,material_casework
KITCHEN-01,not_a_number,4,"[36,30,36,42]",QTZ-01,PLM-WHT
BATH-01,72.0,not_an_integer,"[36,36]",LAM-01,PLM-WHT"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            assert not validation_result.is_valid
            assert len(validation_result.errors) > 0
            
            # Check that specific errors are reported
            error_messages = [error.message for error in validation_result.errors]
            assert any("Invalid number format" in msg for msg in error_messages)
            assert any("Invalid integer format" in msg for msg in error_messages)
            
        finally:
            csv_file.unlink()
    
    def test_parse_csv_duplicate_room_ids(self):
        """Test parsing CSV with duplicate room IDs."""
        csv_content = """room_id,total_length_in,num_modules,module_widths,material_top,material_casework
KITCHEN-01,144.0,4,"[36,30,36,42]",QTZ-01,PLM-WHT
KITCHEN-01,72.0,2,"[36,36]",LAM-01,PLM-WHT"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            # First room should parse successfully, second should fail due to duplicate ID
            assert not validation_result.is_valid
            assert len(parsed_data) == 1  # Only first room is valid
            assert any("Duplicate room_id" in error.message for error in validation_result.errors)
            
        finally:
            csv_file.unlink()
    
    def test_parse_csv_unknown_fields(self):
        """Test parsing CSV with unknown fields (should warn, not error)."""
        csv_content = """room_id,total_length_in,num_modules,module_widths,material_top,material_casework,unknown_field
KITCHEN-01,144.0,4,"[36,30,36,42]",QTZ-01,PLM-WHT,some_value"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            # Should succeed with warning
            assert validation_result.is_valid  # Warnings don't make it invalid
            assert len(validation_result.warnings) > 0
            assert any("Unknown fields will be ignored" in warning.message for warning in validation_result.warnings)
            assert len(parsed_data) == 1
            
        finally:
            csv_file.unlink()
    
    def test_parse_nonexistent_file(self):
        """Test parsing a nonexistent file."""
        parser = CSVParser()
        parsed_data, validation_result = parser.parse_file(Path("nonexistent.csv"))
        
        assert not validation_result.is_valid
        assert len(parsed_data) == 0
        assert any("File not found" in error.message for error in validation_result.errors)
    
    def test_parse_tab_delimited_csv(self):
        """Test parsing tab-delimited CSV file."""
        csv_content = """room_id\ttotal_length_in\tnum_modules\tmodule_widths\tmaterial_top\tmaterial_casework
KITCHEN-01\t144.0\t4\t[36,30,36,42]\tQTZ-01\tPLM-WHT"""
        
        csv_file = self.create_temp_csv(csv_content)
        try:
            parser = CSVParser()
            parsed_data, validation_result = parser.parse_file(csv_file)
            
            assert validation_result.is_valid
            assert len(parsed_data) == 1
            
            room = parsed_data[0]
            assert room.room_id == "KITCHEN-01"
            assert room.total_length_in == 144.0
            
        finally:
            csv_file.unlink()