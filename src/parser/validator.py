"""
Comprehensive validation implementation for millwork room specifications.

Implements the IValidator interface with all validation categories:
- Type & Domain validation (tech_specs.md section 4.1)
- Geometric Consistency validation (tech_specs.md section 4.2)
- Referential Integrity validation (tech_specs.md section 4.3)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

from .schema import ParsedRoomData
from ..core.interfaces import IValidator, ValidationResult


@dataclass
class BatchValidationSummary:
    """Summary of batch validation results."""
    total_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    validation_errors: List[str] = None
    error_reasons: Dict[str, int] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.error_reasons is None:
            self.error_reasons = {}


class RoomValidator(IValidator):
    """
    Comprehensive validator for millwork room specifications.
    
    Implements all validation categories as defined in tech_specs.md section 4:
    - Type & Domain validation (4.1)
    - Geometric Consistency validation (4.2) 
    - Referential Integrity validation (4.3)
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, treat warnings as errors
        """
        self.strict_mode = strict_mode
    
    def validate_type_and_domain(self, data: Dict[str, Any], 
                                config: Dict[str, Any]) -> ValidationResult:
        """
        Validate data types and domain constraints (tech_specs.md section 4.1).
        
        This is typically handled by the CSV parser, but this method provides
        additional domain-specific validations.
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Additional domain validations beyond basic type checking
        
        # Validate room_id format and uniqueness (handled at batch level)
        room_id = data.get("room_id")
        if room_id is not None:
            if not isinstance(room_id, str) or len(room_id.strip()) == 0:
                result.add_error("room_id", "Room ID must be non-empty string", room_id)
            elif len(room_id) > 50:
                result.add_error("room_id", "Room ID too long (max 50 characters)", room_id)
        
        # Validate num_modules consistency with module_widths length
        num_modules = data.get("num_modules")
        module_widths = data.get("module_widths", [])
        
        if num_modules is not None and module_widths is not None:
            if len(module_widths) != num_modules:
                result.add_error(
                    "module_widths", 
                    f"Module widths count ({len(module_widths)}) does not match num_modules ({num_modules})",
                    module_widths
                )
        
        # Validate material codes format (if configuration defines valid codes)
        material_codes = config.get("MATERIALS", {})
        if material_codes:
            for material_field in ["material_top", "material_casework"]:
                material_code = data.get(material_field)
                if material_code and material_code not in material_codes:
                    if self.strict_mode:
                        result.add_error(
                            material_field,
                            f"Unknown material code: {material_code}",
                            material_code
                        )
                    else:
                        result.add_warning(
                            material_field,
                            f"Material code not in configuration: {material_code}",
                            material_code
                        )
        
        # Validate boolean fields are properly parsed
        for bool_field in ["has_sink", "has_ref"]:
            value = data.get(bool_field)
            if value is not None and not isinstance(value, bool):
                result.add_error(bool_field, f"Expected boolean, got {type(value)}", value)
        
        return result
    
    def validate_geometric_consistency(self, data: Dict[str, Any],
                                     config: Dict[str, Any]) -> ValidationResult:
        """
        Validate geometric relationships and tolerances (tech_specs.md section 4.2).
        
        Key validations:
        - Module width sum vs total_length_in within tolerance
        - ADA compliance for counter heights
        - Reasonable filler dimensions
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Get tolerance settings from configuration
        tolerances = config.get("TOLERANCES", {})
        length_tolerance = tolerances.get("LENGTH_SUM", 0.125)  # Default 1/8"
        
        # Validate module width sum
        total_length = data.get("total_length_in")
        module_widths = data.get("module_widths", [])
        left_filler = data.get("left_filler_in", 0.0)
        right_filler = data.get("right_filler_in", 0.0)
        
        if total_length is not None and module_widths:
            # Calculate total module width + fillers
            module_sum = sum(module_widths)
            total_with_fillers = module_sum + left_filler + right_filler
            
            # Check if within tolerance
            difference = abs(total_with_fillers - total_length)
            if difference > length_tolerance:
                result.add_error(
                    "total_length_in",
                    f"Module sum + fillers ({total_with_fillers:.3f}\") does not match total length ({total_length:.3f}\") within tolerance ({length_tolerance:.3f}\")",
                    {
                        "total_length": total_length,
                        "module_sum": module_sum,
                        "left_filler": left_filler,
                        "right_filler": right_filler,
                        "calculated_total": total_with_fillers,
                        "difference": difference,
                        "tolerance": length_tolerance
                    }
                )
        
        # Validate individual module widths are reasonable
        if module_widths:
            for i, width in enumerate(module_widths):
                if width <= 0:
                    result.add_error(
                        "module_widths",
                        f"Module {i+1} width must be positive: {width}",
                        width
                    )
                elif width < 6:  # Less than 6" is unusual
                    result.add_warning(
                        "module_widths",
                        f"Module {i+1} width is very small: {width}\"",
                        width
                    )
                elif width > 60:  # Greater than 60" is unusual
                    result.add_warning(
                        "module_widths",
                        f"Module {i+1} width is very large: {width}\"",
                        width
                    )
        
        # Validate ADA compliance for counter heights
        counter_height = data.get("counter_height_in")
        ada_config = config.get("ADA", {})
        
        if counter_height is not None and ada_config:
            counter_range = ada_config.get("COUNTER_RANGE", [28, 34])
            if isinstance(counter_range, list) and len(counter_range) == 2:
                min_height, max_height = counter_range
                if counter_height < min_height or counter_height > max_height:
                    result.add_warning(
                        "counter_height_in",
                        f"Counter height {counter_height}\" outside ADA range [{min_height}\", {max_height}\"]",
                        counter_height
                    )
        
        # Validate filler dimensions are reasonable
        for filler_field in ["left_filler_in", "right_filler_in"]:
            filler_width = data.get(filler_field, 0.0)
            if filler_width < 0:
                result.add_error(filler_field, "Filler width cannot be negative", filler_width)
            elif filler_width > 6:  # More than 6" filler is unusual
                result.add_warning(
                    filler_field,
                    f"Large filler width: {filler_width}\" (consider adjusting module sizes)",
                    filler_width
                )
        
        return result
    
    def validate_referential_integrity(self, data: Dict[str, Any],
                                      config: Dict[str, Any]) -> ValidationResult:
        """
        Validate references to configuration keys and enums (tech_specs.md section 4.3).
        
        Key validations:
        - edge_rule references valid CFG.EDGE_RULES
        - hardware_defaults references valid CFG.HW.DEFAULTS
        - Material codes reference valid materials (if configured)
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate edge_rule against configuration
        edge_rule = data.get("edge_rule")
        if edge_rule is not None and edge_rule != "":
            edge_rules = config.get("EDGE_RULES", [])
            if edge_rules and edge_rule not in edge_rules:
                result.add_error(
                    "edge_rule",
                    f"Invalid edge rule '{edge_rule}'. Valid options: {edge_rules}",
                    edge_rule
                )
        
        # Validate hardware_defaults against configuration
        hardware_defaults = data.get("hardware_defaults")
        if hardware_defaults is not None and hardware_defaults != "":
            hw_config = config.get("HW", {})
            hw_defaults = hw_config.get("DEFAULTS", {})
            if hw_defaults and hardware_defaults not in hw_defaults:
                result.add_error(
                    "hardware_defaults",
                    f"Invalid hardware defaults '{hardware_defaults}'. Valid options: {list(hw_defaults.keys())}",
                    hardware_defaults
                )
        
        # Validate material codes against configuration (if material catalog is defined)
        materials_config = config.get("MATERIALS", {})
        if materials_config:
            for material_field in ["material_top", "material_casework"]:
                material_code = data.get(material_field)
                if material_code and material_code not in materials_config:
                    if self.strict_mode:
                        result.add_error(
                            material_field,
                            f"Material code '{material_code}' not found in configuration",
                            material_code
                        )
                    else:
                        result.add_warning(
                            material_field,
                            f"Material code '{material_code}' not in configuration catalog",
                            material_code
                        )
        
        return result
    
    def validate_room_data(self, room_data: ParsedRoomData, 
                          config: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single room's data using all validation categories.
        
        Args:
            room_data: Parsed room data
            config: Configuration dictionary
            
        Returns:
            ValidationResult with all validation errors and warnings
        """
        combined_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Convert room data to dictionary for validation methods
        data_dict = room_data.to_dict()
        
        # Run all validation categories
        type_result = self.validate_type_and_domain(data_dict, config)
        geometric_result = self.validate_geometric_consistency(data_dict, config)
        referential_result = self.validate_referential_integrity(data_dict, config)
        
        # Combine results
        combined_result.merge(type_result)
        combined_result.merge(geometric_result)
        combined_result.merge(referential_result)
        
        return combined_result
    
    def validate_batch(self, rooms_data: List[ParsedRoomData],
                      config: Dict[str, Any]) -> tuple[List[ParsedRoomData], BatchValidationSummary]:
        """
        Validate a batch of rooms with fail-fast behavior.
        
        Continues processing even if individual rooms fail validation,
        as specified in tech_specs.md section 4.4.
        
        Args:
            rooms_data: List of parsed room data
            config: Configuration dictionary
            
        Returns:
            Tuple of (valid_rooms, batch_summary)
        """
        valid_rooms = []
        summary = BatchValidationSummary()
        summary.total_rows = len(rooms_data)
        
        # Track room IDs for uniqueness validation
        room_ids = set()
        
        for room_data in rooms_data:
            # Check room ID uniqueness across batch
            if room_data.room_id in room_ids:
                summary.failed_rows += 1
                error_msg = f"Duplicate room_id: {room_data.room_id}"
                summary.validation_errors.append(error_msg)
                summary.error_reasons["duplicate_room_id"] = summary.error_reasons.get("duplicate_room_id", 0) + 1
                continue
            
            room_ids.add(room_data.room_id)
            
            # Validate individual room
            validation_result = self.validate_room_data(room_data, config)
            
            if validation_result.is_valid or (not self.strict_mode and not validation_result.errors):
                valid_rooms.append(room_data)
                summary.successful_rows += 1
            else:
                summary.failed_rows += 1
                
                # Collect error reasons for summary
                for error in validation_result.errors:
                    summary.validation_errors.append(f"{room_data.room_id}: {error.message}")
                    error_category = error.field or "general"
                    summary.error_reasons[error_category] = summary.error_reasons.get(error_category, 0) + 1
        
        return valid_rooms, summary


class ErrorReporter:
    """
    Error reporting system for validation results.
    
    Implements JSON error reports as specified in tech_specs.md section 4.4:
    - Per-room error reports: output/logs/{room_id}.errors.json
    - Batch summary: output/logs/summary.json
    """
    
    def __init__(self, output_dir: Path):
        """Initialize error reporter with output directory."""
        self.output_dir = Path(output_dir)
        self.logs_dir = self.output_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def write_room_errors(self, room_id: str, validation_result: ValidationResult) -> None:
        """Write per-room error report."""
        if not validation_result.errors and not validation_result.warnings:
            return  # No errors to report
        
        error_report = {
            "room_id": room_id,
            "validation_status": "failed" if validation_result.errors else "warning",
            "errors": [
                {
                    "field": error.field,
                    "message": error.message,
                    "value": error.value,
                    "row_number": error.row_number
                }
                for error in validation_result.errors
            ],
            "warnings": [
                {
                    "field": warning.field,
                    "message": warning.message,
                    "value": warning.value,
                    "row_number": warning.row_number
                }
                for warning in validation_result.warnings
            ]
        }
        
        error_file = self.logs_dir / f"{room_id}.errors.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_report, f, indent=2, default=str)
    
    def write_batch_summary(self, summary: BatchValidationSummary, 
                           input_file: str, config_file: str) -> None:
        """Write batch validation summary."""
        summary_report = {
            "input_file": input_file,
            "config_file": config_file,
            "validation_summary": {
                "total_rows": summary.total_rows,
                "successful_rows": summary.successful_rows,
                "failed_rows": summary.failed_rows,
                "success_rate": summary.successful_rows / summary.total_rows if summary.total_rows > 0 else 0.0
            },
            "error_breakdown": summary.error_reasons,
            "validation_errors": summary.validation_errors[:50]  # Limit to first 50 errors
        }
        
        summary_file = self.logs_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, indent=2, default=str)