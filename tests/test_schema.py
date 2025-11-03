"""
Tests for CSV schema definition and validation.

Tests the schema structure, field definitions, and data classes
as specified in tech_specs.md section 8.
"""

import pytest
from src.parser.schema import (
    RoomSchema, FieldDefinition, FieldType, ParsedRoomData
)


class TestFieldDefinition:
    """Test FieldDefinition class."""
    
    def test_field_definition_creation(self):
        """Test creating a field definition."""
        field_def = FieldDefinition(
            name="test_field",
            field_type=FieldType.STRING,
            required=True,
            min_length=1,
            max_length=50,
            description="Test field"
        )
        
        assert field_def.name == "test_field"
        assert field_def.field_type == FieldType.STRING
        assert field_def.required is True
        assert field_def.min_length == 1
        assert field_def.max_length == 50
        assert field_def.description == "Test field"
    
    def test_field_definition_validation(self):
        """Test field definition validation."""
        # Should raise error for invalid combination
        with pytest.raises(ValueError, match="min_value not applicable for STRING_LIST"):
            FieldDefinition(
                name="invalid_field",
                field_type=FieldType.STRING_LIST,
                min_value=10.0
            )
        
        with pytest.raises(ValueError, match="min_length not applicable for numeric"):
            FieldDefinition(
                name="invalid_field",
                field_type=FieldType.NUMBER,
                min_length=5
            )


class TestRoomSchema:
    """Test RoomSchema class."""
    
    def test_required_fields(self):
        """Test required field definitions."""
        required_fields = RoomSchema.get_required_field_names()
        
        expected_required = [
            "room_id", "total_length_in", "num_modules", 
            "module_widths", "material_top", "material_casework"
        ]
        
        assert set(required_fields) == set(expected_required)
    
    def test_optional_fields(self):
        """Test optional field definitions."""
        optional_fields = RoomSchema.get_optional_field_names()
        
        expected_optional = [
            "left_filler_in", "right_filler_in", "has_sink", "has_ref",
            "counter_height_in", "edge_rule", "hardware_defaults", 
            "notes", "references"
        ]
        
        assert set(optional_fields) == set(expected_optional)
    
    def test_all_fields(self):
        """Test getting all field definitions."""
        all_fields = RoomSchema.get_all_fields()
        
        # Check that all required and optional fields are present
        required_fields = RoomSchema.get_required_field_names()
        optional_fields = RoomSchema.get_optional_field_names()
        
        assert set(all_fields.keys()) == set(required_fields + optional_fields)
        
        # Check that each field has proper definition
        for field_name, field_def in all_fields.items():
            assert isinstance(field_def, FieldDefinition)
            assert field_def.name == field_name
            assert isinstance(field_def.field_type, FieldType)
    
    def test_field_validation(self):
        """Test field validation methods."""
        # Valid fields
        assert RoomSchema.is_valid_field("room_id")
        assert RoomSchema.is_valid_field("left_filler_in")
        
        # Invalid fields
        assert not RoomSchema.is_valid_field("invalid_field")
        assert not RoomSchema.is_valid_field("")
    
    def test_get_field_definition(self):
        """Test getting individual field definitions."""
        room_id_def = RoomSchema.get_field_definition("room_id")
        assert room_id_def is not None
        assert room_id_def.name == "room_id"
        assert room_id_def.field_type == FieldType.STRING
        assert room_id_def.required is True
        
        # Non-existent field
        invalid_def = RoomSchema.get_field_definition("invalid_field")
        assert invalid_def is None
    
    def test_field_constraints(self):
        """Test specific field constraints from schema."""
        all_fields = RoomSchema.get_all_fields()
        
        # room_id constraints
        room_id = all_fields["room_id"]
        assert room_id.field_type == FieldType.STRING
        assert room_id.required is True
        assert room_id.min_length == 1
        assert room_id.max_length == 50
        assert room_id.pattern is not None
        
        # total_length_in constraints
        total_length = all_fields["total_length_in"]
        assert total_length.field_type == FieldType.NUMBER
        assert total_length.required is True
        assert total_length.min_value == 1.0
        assert total_length.max_value == 1000.0
        
        # num_modules constraints
        num_modules = all_fields["num_modules"]
        assert num_modules.field_type == FieldType.INTEGER
        assert num_modules.required is True
        assert num_modules.min_value == 1
        assert num_modules.max_value == 50
        
        # module_widths constraints
        module_widths = all_fields["module_widths"]
        assert module_widths.field_type == FieldType.STRING_LIST
        assert module_widths.required is True
        
        # Optional field constraints
        left_filler = all_fields["left_filler_in"]
        assert left_filler.field_type == FieldType.NUMBER
        assert left_filler.required is False
        assert left_filler.min_value == 0.0
        assert left_filler.max_value == 12.0


class TestParsedRoomData:
    """Test ParsedRoomData class."""
    
    def test_parsed_room_data_creation(self):
        """Test creating ParsedRoomData."""
        room_data = ParsedRoomData(
            room_id="KITCHEN-01",
            total_length_in=144.0,
            num_modules=4,
            module_widths=[36.0, 30.0, 36.0, 42.0],
            material_top="QTZ-01",
            material_casework="PLM-WHT",
            left_filler_in=0.0,
            right_filler_in=0.0,
            has_sink=True,
            counter_height_in=36.0,
            row_number=2,
            source_file="test.csv"
        )
        
        assert room_data.room_id == "KITCHEN-01"
        assert room_data.total_length_in == 144.0
        assert room_data.num_modules == 4
        assert room_data.module_widths == [36.0, 30.0, 36.0, 42.0]
        assert room_data.has_sink is True
        assert room_data.counter_height_in == 36.0
        assert room_data.row_number == 2
        assert room_data.source_file == "test.csv"
    
    def test_parsed_room_data_defaults(self):
        """Test default values in ParsedRoomData."""
        room_data = ParsedRoomData(
            room_id="BATH-01",
            total_length_in=72.0,
            num_modules=2,
            module_widths=[36.0, 36.0],
            material_top="LAM-01",
            material_casework="PLM-WHT"
        )
        
        # Check defaults
        assert room_data.left_filler_in == 0.0
        assert room_data.right_filler_in == 0.0
        assert room_data.has_sink is False
        assert room_data.has_ref is False
        assert room_data.counter_height_in is None
        assert room_data.edge_rule is None
        assert room_data.hardware_defaults is None
        assert room_data.notes is None
        assert room_data.references is None
        assert room_data.row_number == 0
        assert room_data.source_file is None
    
    def test_to_dict(self):
        """Test converting ParsedRoomData to dictionary."""
        room_data = ParsedRoomData(
            room_id="OFFICE-01",
            total_length_in=96.0,
            num_modules=3,
            module_widths=[24.0, 48.0, 24.0],
            material_top="LAM-02",
            material_casework="OAK-NAT",
            notes="Special requirements"
        )
        
        data_dict = room_data.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict["room_id"] == "OFFICE-01"
        assert data_dict["total_length_in"] == 96.0
        assert data_dict["num_modules"] == 3
        assert data_dict["module_widths"] == [24.0, 48.0, 24.0]
        assert data_dict["material_top"] == "LAM-02"
        assert data_dict["material_casework"] == "OAK-NAT"
        assert data_dict["notes"] == "Special requirements"
        assert data_dict["left_filler_in"] == 0.0  # Default value
    
    def test_from_dict(self):
        """Test creating ParsedRoomData from dictionary."""
        data_dict = {
            "room_id": "TEST-01",
            "total_length_in": 120.0,
            "num_modules": 3,
            "module_widths": [36.0, 48.0, 36.0],
            "material_top": "QTZ-02",
            "material_casework": "PLM-GRY",
            "has_sink": True,
            "counter_height_in": 34.0,
            "row_number": 3,
            "source_file": "test_data.csv"
        }
        
        room_data = ParsedRoomData.from_dict(data_dict)
        
        assert room_data.room_id == "TEST-01"
        assert room_data.total_length_in == 120.0
        assert room_data.num_modules == 3
        assert room_data.module_widths == [36.0, 48.0, 36.0]
        assert room_data.material_top == "QTZ-02"
        assert room_data.material_casework == "PLM-GRY"
        assert room_data.has_sink is True
        assert room_data.counter_height_in == 34.0
        assert room_data.row_number == 3
        assert room_data.source_file == "test_data.csv"
        
        # Check defaults for missing fields
        assert room_data.left_filler_in == 0.0
        assert room_data.has_ref is False
        assert room_data.edge_rule is None