"""
Tests for validation implementation.

Tests the comprehensive validation system including type & domain,
geometric consistency, and referential integrity validation
as specified in tech_specs.md section 8.
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.parser.validator import RoomValidator, ErrorReporter, BatchValidationSummary
from src.parser.schema import ParsedRoomData
from src.core.interfaces import ValidationResult


class TestRoomValidator:
    """Test RoomValidator class."""
    
    @pytest.fixture
    def sample_room_data(self):
        """Sample room data for testing."""
        return ParsedRoomData(
            room_id="KITCHEN-01",
            total_length_in=144.0,
            num_modules=4,
            module_widths=[36.0, 30.0, 36.0, 42.0],
            material_top="QTZ-01",
            material_casework="PLM-WHT",
            left_filler_in=0.0,
            right_filler_in=0.0,
            has_sink=True,
            counter_height_in=36.0
        )
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            "TOLERANCES": {
                "LENGTH_SUM": 0.125
            },
            "ADA": {
                "COUNTER_RANGE": [28, 34]
            },
            "EDGE_RULES": ["MATCH_FACE", "PVC_EDGE", "SOLID_LUMBER"],
            "HW": {
                "DEFAULTS": {
                    "STANDARD": {"HINGE": "BLUM-110", "PULL": "SS-128"},
                    "PREMIUM": {"HINGE": "BLUM-120", "PULL": "SS-256"}
                }
            },
            "MATERIALS": {
                "QTZ-01": "Quartz - White",
                "PLM-WHT": "Plywood - White",
                "LAM-01": "Laminate - White"
            }
        }
    
    def test_validate_type_and_domain_valid(self, sample_room_data, sample_config):
        """Test type and domain validation with valid data."""
        validator = RoomValidator()
        result = validator.validate_type_and_domain(sample_room_data.to_dict(), sample_config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_type_and_domain_invalid_room_id(self, sample_room_data, sample_config):
        """Test type and domain validation with invalid room ID."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["room_id"] = ""  # Empty room ID
        
        result = validator.validate_type_and_domain(data, sample_config)
        
        assert not result.is_valid
        assert any("Room ID must be non-empty" in error.message for error in result.errors)
    
    def test_validate_type_and_domain_module_mismatch(self, sample_room_data, sample_config):
        """Test type and domain validation with module count mismatch."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["num_modules"] = 3  # But module_widths has 4 elements
        
        result = validator.validate_type_and_domain(data, sample_config)
        
        assert not result.is_valid
        assert any("does not match num_modules" in error.message for error in result.errors)
    
    def test_validate_geometric_consistency_valid(self, sample_room_data, sample_config):
        """Test geometric consistency validation with valid data."""
        validator = RoomValidator()
        result = validator.validate_geometric_consistency(sample_room_data.to_dict(), sample_config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_geometric_consistency_tolerance_error(self, sample_room_data, sample_config):
        """Test geometric consistency validation with tolerance error."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        # Module widths sum to 144, but total_length_in is 150 (difference > tolerance)
        data["total_length_in"] = 150.0
        
        result = validator.validate_geometric_consistency(data, sample_config)
        
        assert not result.is_valid
        assert any("does not match total length" in error.message for error in result.errors)
    
    def test_validate_geometric_consistency_ada_warning(self, sample_room_data, sample_config):
        """Test geometric consistency validation with ADA warning."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["counter_height_in"] = 38.0  # Outside ADA range [28, 34]
        
        result = validator.validate_geometric_consistency(data, sample_config)
        
        assert result.is_valid  # Warnings don't make it invalid
        assert len(result.warnings) > 0
        assert any("outside ADA range" in warning.message for warning in result.warnings)
    
    def test_validate_geometric_consistency_negative_filler(self, sample_room_data, sample_config):
        """Test geometric consistency validation with negative filler."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["left_filler_in"] = -1.0
        
        result = validator.validate_geometric_consistency(data, sample_config)
        
        assert not result.is_valid
        assert any("cannot be negative" in error.message for error in result.errors)
    
    def test_validate_geometric_consistency_module_warnings(self, sample_room_data, sample_config):
        """Test geometric consistency validation with module width warnings."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["module_widths"] = [3.0, 80.0, 36.0, 25.0]  # Very small and very large modules
        data["total_length_in"] = 144.0  # Adjust total to match
        
        result = validator.validate_geometric_consistency(data, sample_config)
        
        assert result.is_valid  # Warnings don't make it invalid
        assert len(result.warnings) >= 2
        warning_messages = [w.message for w in result.warnings]
        assert any("very small" in msg for msg in warning_messages)
        assert any("very large" in msg for msg in warning_messages)
    
    def test_validate_referential_integrity_valid(self, sample_room_data, sample_config):
        """Test referential integrity validation with valid data."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["edge_rule"] = "MATCH_FACE"
        data["hardware_defaults"] = "STANDARD"
        
        result = validator.validate_referential_integrity(data, sample_config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_referential_integrity_invalid_edge_rule(self, sample_room_data, sample_config):
        """Test referential integrity validation with invalid edge rule."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["edge_rule"] = "INVALID_RULE"
        
        result = validator.validate_referential_integrity(data, sample_config)
        
        assert not result.is_valid
        assert any("Invalid edge rule" in error.message for error in result.errors)
    
    def test_validate_referential_integrity_invalid_hardware(self, sample_room_data, sample_config):
        """Test referential integrity validation with invalid hardware defaults."""
        validator = RoomValidator()
        data = sample_room_data.to_dict()
        data["hardware_defaults"] = "INVALID_HARDWARE"
        
        result = validator.validate_referential_integrity(data, sample_config)
        
        assert not result.is_valid
        assert any("Invalid hardware defaults" in error.message for error in result.errors)
    
    def test_validate_referential_integrity_unknown_material_strict(self, sample_room_data, sample_config):
        """Test referential integrity validation with unknown material in strict mode."""
        validator = RoomValidator(strict_mode=True)
        data = sample_room_data.to_dict()
        data["material_top"] = "UNKNOWN-01"
        
        result = validator.validate_referential_integrity(data, sample_config)
        
        assert not result.is_valid
        assert any("not found in configuration" in error.message for error in result.errors)
    
    def test_validate_referential_integrity_unknown_material_non_strict(self, sample_room_data, sample_config):
        """Test referential integrity validation with unknown material in non-strict mode."""
        validator = RoomValidator(strict_mode=False)
        data = sample_room_data.to_dict()
        data["material_top"] = "UNKNOWN-01"
        
        result = validator.validate_referential_integrity(data, sample_config)
        
        assert result.is_valid  # Warnings don't make it invalid in non-strict mode
        assert len(result.warnings) > 0
        assert any("not in configuration catalog" in warning.message for warning in result.warnings)
    
    def test_validate_room_data_comprehensive(self, sample_room_data, sample_config):
        """Test comprehensive room data validation."""
        validator = RoomValidator()
        result = validator.validate_room_data(sample_room_data, sample_config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_batch_all_valid(self, sample_config):
        """Test batch validation with all valid rooms."""
        rooms = [
            ParsedRoomData(
                room_id="KITCHEN-01",
                total_length_in=144.0,
                num_modules=4,
                module_widths=[36.0, 30.0, 36.0, 42.0],
                material_top="QTZ-01",
                material_casework="PLM-WHT"
            ),
            ParsedRoomData(
                room_id="BATH-01",
                total_length_in=72.0,
                num_modules=2,
                module_widths=[36.0, 36.0],
                material_top="LAM-01",
                material_casework="PLM-WHT"
            )
        ]
        
        validator = RoomValidator()
        valid_rooms, summary = validator.validate_batch(rooms, sample_config)
        
        assert len(valid_rooms) == 2
        assert summary.total_rows == 2
        assert summary.successful_rows == 2
        assert summary.failed_rows == 0
    
    def test_validate_batch_duplicate_room_ids(self, sample_config):
        """Test batch validation with duplicate room IDs."""
        rooms = [
            ParsedRoomData(
                room_id="KITCHEN-01",
                total_length_in=144.0,
                num_modules=4,
                module_widths=[36.0, 30.0, 36.0, 42.0],
                material_top="QTZ-01",
                material_casework="PLM-WHT"
            ),
            ParsedRoomData(
                room_id="KITCHEN-01",  # Duplicate ID
                total_length_in=72.0,
                num_modules=2,
                module_widths=[36.0, 36.0],
                material_top="LAM-01",
                material_casework="PLM-WHT"
            )
        ]
        
        validator = RoomValidator()
        valid_rooms, summary = validator.validate_batch(rooms, sample_config)
        
        assert len(valid_rooms) == 1  # Only first room is valid
        assert summary.total_rows == 2
        assert summary.successful_rows == 1
        assert summary.failed_rows == 1
        assert "duplicate_room_id" in summary.error_reasons
    
    def test_validate_batch_mixed_results(self, sample_config):
        """Test batch validation with mixed valid/invalid rooms."""
        rooms = [
            ParsedRoomData(
                room_id="KITCHEN-01",
                total_length_in=144.0,
                num_modules=4,
                module_widths=[36.0, 30.0, 36.0, 42.0],
                material_top="QTZ-01",
                material_casework="PLM-WHT"
            ),
            ParsedRoomData(
                room_id="INVALID-01",
                total_length_in=100.0,  # This won't match module sum
                num_modules=2,
                module_widths=[36.0, 36.0],  # Sum = 72, not 100
                material_top="LAM-01",
                material_casework="PLM-WHT"
            )
        ]
        
        validator = RoomValidator()
        valid_rooms, summary = validator.validate_batch(rooms, sample_config)
        
        assert len(valid_rooms) == 1  # Only first room is valid
        assert summary.total_rows == 2
        assert summary.successful_rows == 1
        assert summary.failed_rows == 1


class TestErrorReporter:
    """Test ErrorReporter class."""
    
    def test_write_room_errors(self):
        """Test writing room error reports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            reporter = ErrorReporter(output_dir)
            
            # Create validation result with errors
            validation_result = ValidationResult(is_valid=False, errors=[], warnings=[])
            validation_result.add_error("total_length_in", "Value too large", 1000.0, 2)
            validation_result.add_warning("counter_height_in", "Outside ADA range", 38.0, 2)
            
            reporter.write_room_errors("KITCHEN-01", validation_result)
            
            # Check that error file was created
            error_file = output_dir / "logs" / "KITCHEN-01.errors.json"
            assert error_file.exists()
            
            # Check error file content
            with open(error_file, 'r') as f:
                error_data = json.load(f)
            
            assert error_data["room_id"] == "KITCHEN-01"
            assert error_data["validation_status"] == "failed"
            assert len(error_data["errors"]) == 1
            assert len(error_data["warnings"]) == 1
            assert error_data["errors"][0]["field"] == "total_length_in"
            assert error_data["warnings"][0]["field"] == "counter_height_in"
    
    def test_write_batch_summary(self):
        """Test writing batch validation summary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            reporter = ErrorReporter(output_dir)
            
            # Create batch summary
            summary = BatchValidationSummary()
            summary.total_rows = 5
            summary.successful_rows = 3
            summary.failed_rows = 2
            summary.validation_errors = ["Error 1", "Error 2"]
            summary.error_reasons = {"total_length_in": 1, "room_id": 1}
            
            reporter.write_batch_summary(summary, "input.csv", "config.yaml")
            
            # Check that summary file was created
            summary_file = output_dir / "logs" / "summary.json"
            assert summary_file.exists()
            
            # Check summary file content
            with open(summary_file, 'r') as f:
                summary_data = json.load(f)
            
            assert summary_data["input_file"] == "input.csv"
            assert summary_data["config_file"] == "config.yaml"
            assert summary_data["validation_summary"]["total_rows"] == 5
            assert summary_data["validation_summary"]["successful_rows"] == 3
            assert summary_data["validation_summary"]["failed_rows"] == 2
            assert summary_data["validation_summary"]["success_rate"] == 0.6
            assert summary_data["error_breakdown"] == {"total_length_in": 1, "room_id": 1}
    
    def test_no_errors_no_file(self):
        """Test that no error file is written when there are no errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            reporter = ErrorReporter(output_dir)
            
            # Create validation result with no errors
            validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
            
            reporter.write_room_errors("KITCHEN-01", validation_result)
            
            # Check that no error file was created
            error_file = output_dir / "logs" / "KITCHEN-01.errors.json"
            assert not error_file.exists()


class TestBatchValidationSummary:
    """Test BatchValidationSummary class."""
    
    def test_summary_initialization(self):
        """Test summary initialization with defaults."""
        summary = BatchValidationSummary()
        
        assert summary.total_rows == 0
        assert summary.successful_rows == 0
        assert summary.failed_rows == 0
        assert summary.validation_errors == []
        assert summary.error_reasons == {}
    
    def test_summary_with_data(self):
        """Test summary with actual data."""
        summary = BatchValidationSummary()
        summary.total_rows = 10
        summary.successful_rows = 8
        summary.failed_rows = 2
        summary.validation_errors = ["Error 1", "Error 2"]
        summary.error_reasons = {"field1": 1, "field2": 1}
        
        assert summary.total_rows == 10
        assert summary.successful_rows == 8
        assert summary.failed_rows == 2
        assert len(summary.validation_errors) == 2
        assert len(summary.error_reasons) == 2