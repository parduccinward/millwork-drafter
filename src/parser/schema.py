"""
CSV schema definition for millwork room specifications.

Implements the schema defined in tech_specs.md section 3.1 with comprehensive
field definitions, types, and validation constraints.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class FieldType(Enum):
    """Field type enumeration for schema validation."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    STRING_LIST = "string_list"  # JSON array as string, e.g., "[36,30,36,30]"


@dataclass
class FieldDefinition:
    """Definition of a CSV field with validation constraints."""
    name: str
    field_type: FieldType
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[str]] = None
    description: str = ""
    
    def __post_init__(self):
        """Validate field definition consistency."""
        if self.field_type == FieldType.STRING_LIST and self.min_value is not None:
            raise ValueError(f"min_value not applicable for STRING_LIST field {self.name}")
        
        if self.field_type in [FieldType.NUMBER, FieldType.INTEGER] and self.min_length is not None:
            raise ValueError(f"min_length not applicable for numeric field {self.name}")


class RoomSchema:
    """
    CSV schema for millwork room specifications.
    
    Based on tech_specs.md section 3.1, defines the structure and validation
    constraints for room specification CSV files.
    """
    
    # Required fields (tech_specs.md section 3.1)
    REQUIRED_FIELDS = [
        FieldDefinition(
            name="room_id",
            field_type=FieldType.STRING,
            required=True,
            min_length=1,
            max_length=50,
            pattern=r'^[A-Z0-9][A-Z0-9\-_]*$',
            description="Unique room identifier (e.g., 'KITCHEN-01')"
        ),
        FieldDefinition(
            name="total_length_in",
            field_type=FieldType.NUMBER,
            required=True,
            min_value=1.0,
            max_value=1000.0,
            description="Total length in inches (e.g., 144.0)"
        ),
        FieldDefinition(
            name="num_modules",
            field_type=FieldType.INTEGER,
            required=True,
            min_value=1,
            max_value=50,
            description="Number of modules (e.g., 4)"
        ),
        FieldDefinition(
            name="module_widths",
            field_type=FieldType.STRING_LIST,
            required=True,
            description="Module widths as JSON array string (e.g., '[36,30,36,30]')"
        ),
        FieldDefinition(
            name="material_top",
            field_type=FieldType.STRING,
            required=True,
            min_length=1,
            max_length=20,
            pattern=r'^[A-Z0-9\-_]+$',
            description="Top material code (e.g., 'QTZ-01')"
        ),
        FieldDefinition(
            name="material_casework",
            field_type=FieldType.STRING,
            required=True,
            min_length=1,
            max_length=20,
            pattern=r'^[A-Z0-9\-_]+$',
            description="Casework material code (e.g., 'PLM-WHT')"
        ),
    ]
    
    # Optional fields (tech_specs.md section 3.1)
    OPTIONAL_FIELDS = [
        FieldDefinition(
            name="left_filler_in",
            field_type=FieldType.NUMBER,
            required=False,
            min_value=0.0,
            max_value=12.0,
            description="Left filler width in inches (e.g., 1.5)"
        ),
        FieldDefinition(
            name="right_filler_in",
            field_type=FieldType.NUMBER,
            required=False,
            min_value=0.0,
            max_value=12.0,
            description="Right filler width in inches (e.g., 1.5)"
        ),
        FieldDefinition(
            name="has_sink",
            field_type=FieldType.BOOLEAN,
            required=False,
            description="Whether room has sink (true/false)"
        ),
        FieldDefinition(
            name="has_ref",
            field_type=FieldType.BOOLEAN,
            required=False,
            description="Whether room has refrigerator (true/false)"
        ),
        FieldDefinition(
            name="counter_height_in",
            field_type=FieldType.NUMBER,
            required=False,
            min_value=24.0,
            max_value=48.0,
            description="Counter height in inches (e.g., 36.0)"
        ),
        FieldDefinition(
            name="edge_rule",
            field_type=FieldType.STRING,
            required=False,
            description="Edge treatment rule (validated against CFG.EDGE_RULES)"
        ),
        FieldDefinition(
            name="hardware_defaults",
            field_type=FieldType.STRING,
            required=False,
            description="Hardware defaults key (validated against CFG.HW.DEFAULTS)"
        ),
        FieldDefinition(
            name="notes",
            field_type=FieldType.STRING,
            required=False,
            max_length=500,
            description="Free text notes"
        ),
        FieldDefinition(
            name="references",
            field_type=FieldType.STRING,
            required=False,
            max_length=100,
            description="Sheet/callout IDs (e.g., 'A3.1/2')"
        ),
    ]
    
    @classmethod
    def get_all_fields(cls) -> Dict[str, FieldDefinition]:
        """Get all field definitions as a dictionary."""
        all_fields = {}
        
        for field_def in cls.REQUIRED_FIELDS + cls.OPTIONAL_FIELDS:
            all_fields[field_def.name] = field_def
        
        return all_fields
    
    @classmethod
    def get_required_field_names(cls) -> List[str]:
        """Get list of required field names."""
        return [field_def.name for field_def in cls.REQUIRED_FIELDS]
    
    @classmethod
    def get_optional_field_names(cls) -> List[str]:
        """Get list of optional field names."""
        return [field_def.name for field_def in cls.OPTIONAL_FIELDS]
    
    @classmethod
    def get_all_field_names(cls) -> List[str]:
        """Get list of all field names."""
        return cls.get_required_field_names() + cls.get_optional_field_names()
    
    @classmethod
    def is_valid_field(cls, field_name: str) -> bool:
        """Check if field name is valid in schema."""
        return field_name in cls.get_all_field_names()
    
    @classmethod
    def get_field_definition(cls, field_name: str) -> Optional[FieldDefinition]:
        """Get field definition by name."""
        all_fields = cls.get_all_fields()
        return all_fields.get(field_name)


@dataclass
class ParsedRoomData:
    """
    Parsed and validated room data from CSV.
    
    Represents a single room row after successful validation,
    with typed fields for downstream processing.
    """
    # Required fields
    room_id: str
    total_length_in: float
    num_modules: int
    module_widths: List[float]
    material_top: str
    material_casework: str
    
    # Optional fields with defaults
    left_filler_in: float = 0.0
    right_filler_in: float = 0.0
    has_sink: bool = False
    has_ref: bool = False
    counter_height_in: Optional[float] = None
    edge_rule: Optional[str] = None
    hardware_defaults: Optional[str] = None
    notes: Optional[str] = None
    references: Optional[str] = None
    
    # Metadata
    row_number: int = 0
    source_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "room_id": self.room_id,
            "total_length_in": self.total_length_in,
            "num_modules": self.num_modules,
            "module_widths": self.module_widths,
            "material_top": self.material_top,
            "material_casework": self.material_casework,
            "left_filler_in": self.left_filler_in,
            "right_filler_in": self.right_filler_in,
            "has_sink": self.has_sink,
            "has_ref": self.has_ref,
            "counter_height_in": self.counter_height_in,
            "edge_rule": self.edge_rule,
            "hardware_defaults": self.hardware_defaults,
            "notes": self.notes,
            "references": self.references,
            "row_number": self.row_number,
            "source_file": self.source_file,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParsedRoomData":
        """Create from dictionary."""
        return cls(
            room_id=data["room_id"],
            total_length_in=data["total_length_in"],
            num_modules=data["num_modules"],
            module_widths=data["module_widths"],
            material_top=data["material_top"],
            material_casework=data["material_casework"],
            left_filler_in=data.get("left_filler_in", 0.0),
            right_filler_in=data.get("right_filler_in", 0.0),
            has_sink=data.get("has_sink", False),
            has_ref=data.get("has_ref", False),
            counter_height_in=data.get("counter_height_in"),
            edge_rule=data.get("edge_rule"),
            hardware_defaults=data.get("hardware_defaults"),
            notes=data.get("notes"),
            references=data.get("references"),
            row_number=data.get("row_number", 0),
            source_file=data.get("source_file"),
        )