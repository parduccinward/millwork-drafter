"""
Unit tests for configuration system.

Tests the YAML loading, validation, and hash generation functionality
as specified in Phase 1 of the development plan.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.core.config import MillworkConfig, ConfigLoader, load_default_config
from src.core.interfaces import ValidationResult


class TestMillworkConfig:
    """Test the MillworkConfig dataclass."""
    
    def test_default_config_creation(self):
        """Test creating a default configuration."""
        config = MillworkConfig()
        
        assert config.scale_plan == 0.25
        assert config.counter_height == 36.0
        assert config.base_depth == 24.0
        assert config.wall_cab_depth == 12.0
        assert config.edge_rule == "MATCH_FACE"
        assert config.ada.knee_clear == "27\" H x 30\" W x 17\" D"
        assert config.ada.counter_range == [28.0, 34.0]
        assert config.tolerances.length_sum == 0.125
        assert config.pdf.size == "letter"
    
    def test_config_to_dict(self, sample_millwork_config):
        """Test converting config to dictionary."""
        config_dict = sample_millwork_config.to_dict()
        
        assert "SCALE_PLAN" in config_dict
        assert "COUNTER_HEIGHT" in config_dict
        assert "ADA" in config_dict
        assert "KNEE_CLEAR" in config_dict["ADA"]
        assert "TOLERANCES" in config_dict
        assert "PDF" in config_dict
    
    def test_config_from_dict(self, sample_config_dict):
        """Test creating config from dictionary."""
        config = MillworkConfig.from_dict(sample_config_dict)
        
        assert config.scale_plan == 0.25
        assert config.counter_height == 36.0
        assert config.ada.knee_clear == "27\" H x 30\" W x 17\" D"
        assert config.ada.counter_range == [28.0, 34.0]
        assert config.tolerances.length_sum == 0.125
    
    def test_config_roundtrip(self, sample_millwork_config):
        """Test converting to dict and back preserves data."""
        original = sample_millwork_config
        config_dict = original.to_dict()
        restored = MillworkConfig.from_dict(config_dict)
        
        assert original.scale_plan == restored.scale_plan
        assert original.counter_height == restored.counter_height
        assert original.ada.knee_clear == restored.ada.knee_clear
        assert original.tolerances.length_sum == restored.tolerances.length_sum


class TestConfigLoader:
    """Test the ConfigLoader implementation."""
    
    def test_load_valid_config(self, config_loader, temp_config_file):
        """Test loading a valid configuration file."""
        config_dict = config_loader.load_config(str(temp_config_file))
        
        assert "SCALE_PLAN" in config_dict
        assert config_dict["SCALE_PLAN"] == 0.25
        assert "ADA" in config_dict
        assert config_dict["ADA"]["COUNTER_RANGE"] == [28.0, 34.0]
    
    def test_load_nonexistent_config(self, config_loader):
        """Test loading a non-existent configuration file."""
        with pytest.raises(ValueError, match="Error loading configuration"):
            config_loader.load_config("nonexistent.yaml")
    
    def test_load_invalid_yaml(self, config_loader):
        """Test loading invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = Path(f.name)
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            config_loader.load_config(str(invalid_file))
    
    def test_validate_valid_config(self, config_loader, sample_config_dict):
        """Test validating a valid configuration."""
        result = config_loader.validate_config(sample_config_dict)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_invalid_scale(self, config_loader):
        """Test validation with invalid scale value."""
        invalid_config = {"SCALE_PLAN": -1.0}
        result = config_loader.validate_config(invalid_config)
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "SCALE_PLAN"
    
    def test_validate_invalid_ada_range(self, config_loader):
        """Test validation with invalid ADA counter range."""
        invalid_config = {
            "ADA": {
                "COUNTER_RANGE": [34.0, 28.0]  # min > max
            }
        }
        result = config_loader.validate_config(invalid_config)
        
        assert not result.is_valid
        assert any(err.field == "ADA.COUNTER_RANGE" for err in result.errors)
    
    def test_validate_invalid_pdf_size(self, config_loader):
        """Test validation with invalid PDF size."""
        invalid_config = {
            "PDF": {
                "SIZE": "invalid_size"
            }
        }
        result = config_loader.validate_config(invalid_config)
        
        assert not result.is_valid
        assert any(err.field == "PDF.SIZE" for err in result.errors)
    
    def test_config_hash_consistency(self, config_loader, sample_config_dict):
        """Test that config hash is consistent for same data."""
        hash1 = config_loader.get_config_hash(sample_config_dict)
        hash2 = config_loader.get_config_hash(sample_config_dict)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length
    
    def test_config_hash_different_for_different_data(self, config_loader, sample_config_dict):
        """Test that different configs produce different hashes."""
        modified_config = sample_config_dict.copy()
        modified_config["SCALE_PLAN"] = 0.5
        
        hash1 = config_loader.get_config_hash(sample_config_dict)
        hash2 = config_loader.get_config_hash(modified_config)
        
        assert hash1 != hash2
    
    def test_load_empty_yaml_file(self, config_loader):
        """Test loading YAML file that contains None."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("# Empty file with just comments\n")
            empty_file = Path(f.name)
        
        try:
            config_dict = config_loader.load_config(str(empty_file))
            # Should load defaults when file is empty
            assert isinstance(config_dict, dict)
        finally:
            empty_file.unlink()
    
    def test_validate_config_multiple_errors(self, config_loader):
        """Test validation with multiple errors to trigger error message joining."""
        invalid_config = {
            "SCALE_PLAN": -1.0,  # Invalid: negative
            "COUNTER_HEIGHT": "not_a_number",  # Invalid: not numeric
            "ADA": {
                "COUNTER_RANGE": [35.0, 30.0]  # Invalid: wrong order
            },
            "PDF": {
                "SIZE": "invalid_size"  # Invalid: not in allowed list
            }
        }
        
        # Create a temporary file with invalid config to test the error path
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            invalid_file = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                config_loader.load_config(str(invalid_file))
        finally:
            invalid_file.unlink()
    
    def test_validate_counter_height_invalid(self, config_loader):
        """Test validation of COUNTER_HEIGHT with invalid values."""
        # Test negative value
        result = config_loader.validate_config({"COUNTER_HEIGHT": -10.0})
        assert not result.is_valid
        assert any(err.field == "COUNTER_HEIGHT" for err in result.errors)
        
        # Test non-numeric value
        result = config_loader.validate_config({"COUNTER_HEIGHT": "not_a_number"})
        assert not result.is_valid
        assert any(err.field == "COUNTER_HEIGHT" for err in result.errors)
    
    def test_validate_base_depth_invalid(self, config_loader):
        """Test validation of BASE_DEPTH with invalid values."""
        # Test negative value
        result = config_loader.validate_config({"BASE_DEPTH": -5.0})
        assert not result.is_valid
        assert any(err.field == "BASE_DEPTH" for err in result.errors)
        
        # Test non-numeric value
        result = config_loader.validate_config({"BASE_DEPTH": "invalid"})
        assert not result.is_valid
        assert any(err.field == "BASE_DEPTH" for err in result.errors)
    
    def test_validate_wall_cab_depth_invalid(self, config_loader):
        """Test validation of WALL_CAB_DEPTH with invalid values."""
        # Test negative value
        result = config_loader.validate_config({"WALL_CAB_DEPTH": 0})
        assert not result.is_valid
        assert any(err.field == "WALL_CAB_DEPTH" for err in result.errors)
        
        # Test non-numeric value
        result = config_loader.validate_config({"WALL_CAB_DEPTH": "invalid"})
        assert not result.is_valid
        assert any(err.field == "WALL_CAB_DEPTH" for err in result.errors)
    
    def test_validate_ada_counter_range_edge_cases(self, config_loader):
        """Test ADA COUNTER_RANGE validation edge cases."""
        # Test not a list
        invalid_config = {
            "ADA": {
                "COUNTER_RANGE": "not_a_list"
            }
        }
        result = config_loader.validate_config(invalid_config)
        assert not result.is_valid
        assert any(err.field == "ADA.COUNTER_RANGE" for err in result.errors)
        
        # Test wrong length (not 2 elements)
        invalid_config = {
            "ADA": {
                "COUNTER_RANGE": [28.0, 34.0, 36.0]  # 3 elements instead of 2
            }
        }
        result = config_loader.validate_config(invalid_config)
        assert not result.is_valid
        assert any(err.field == "ADA.COUNTER_RANGE" for err in result.errors)
        
        # Test non-numeric values in range
        invalid_config = {
            "ADA": {
                "COUNTER_RANGE": ["28.0", 34.0]  # String instead of number
            }
        }
        result = config_loader.validate_config(invalid_config)
        assert not result.is_valid
        assert any(err.field == "ADA.COUNTER_RANGE" for err in result.errors)
        
        # Test wrong order (first >= second)
        invalid_config = {
            "ADA": {
                "COUNTER_RANGE": [35.0, 30.0]
            }
        }
        result = config_loader.validate_config(invalid_config)
        assert not result.is_valid
        assert any(err.field == "ADA.COUNTER_RANGE" for err in result.errors)
    
    def test_validate_pdf_margins_invalid(self, config_loader):
        """Test PDF MARGINS validation with invalid values."""
        # Test wrong structure (not 4 values)
        invalid_config = {
            "PDF": {
                "MARGINS": [0.5, 0.5]  # Only 2 values instead of 4
            }
        }
        result = config_loader.validate_config(invalid_config)
        assert not result.is_valid
        assert any(err.field == "PDF.MARGINS" for err in result.errors)
        
        # Test negative values
        invalid_config = {
            "PDF": {
                "MARGINS": [0.5, -0.5, 0.5, 0.5]  # Negative margin
            }
        }
        result = config_loader.validate_config(invalid_config)
        assert not result.is_valid
        assert any(err.field == "PDF.MARGINS" for err in result.errors)
    
    def test_validate_tolerances_invalid(self, config_loader):
        """Test TOLERANCES validation with invalid values."""
        # Test LENGTH_SUM invalid
        result = config_loader.validate_config({
            "TOLERANCES": {
                "LENGTH_SUM": -0.5  # Negative value
            }
        })
        assert not result.is_valid
        assert any(err.field == "TOLERANCES.LENGTH_SUM" for err in result.errors)
        
        # Test LENGTH_ROUNDING invalid
        result = config_loader.validate_config({
            "TOLERANCES": {
                "LENGTH_ROUNDING": -1  # Negative integer
            }
        })
        assert not result.is_valid
        assert any(err.field == "TOLERANCES.LENGTH_ROUNDING" for err in result.errors)
        
        # Test non-integer LENGTH_ROUNDING
        result = config_loader.validate_config({
            "TOLERANCES": {
                "LENGTH_ROUNDING": 2.5  # Float instead of int
            }
        })
        assert not result.is_valid
        assert any(err.field == "TOLERANCES.LENGTH_ROUNDING" for err in result.errors)
    
    def test_validate_edge_rules_invalid(self, config_loader):
        """Test EDGE_RULES validation with invalid values."""
        # Test non-list value
        result = config_loader.validate_config({
            "EDGE_RULES": "not_a_list"
        })
        assert not result.is_valid
        assert any(err.field == "EDGE_RULES" for err in result.errors)
        
        # Test list with non-string values
        result = config_loader.validate_config({
            "EDGE_RULES": ["MATCH_FACE", 123, "EDGE_BAND"]  # Number in list
        })
        assert not result.is_valid
        assert any(err.field == "EDGE_RULES" for err in result.errors)


class TestConfigIntegration:
    """Integration tests for the complete configuration system."""
    
    def test_load_default_config(self):
        """Test loading the default configuration."""
        config = load_default_config()
        
        assert isinstance(config, MillworkConfig)
        assert config.scale_plan > 0
        assert config.counter_height > 0
        assert len(config.ada.counter_range) == 2
    
    def test_full_config_pipeline(self, sample_config_dict):
        """Test the complete configuration pipeline."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config_dict, f)
            config_file = Path(f.name)
        
        try:
            # Load and validate
            loader = ConfigLoader()
            config_dict = loader.load_config(str(config_file))
            config_hash = loader.get_config_hash(config_dict)
            
            # Verify loaded correctly
            assert config_dict["SCALE_PLAN"] == 0.25
            assert isinstance(config_hash, str)
            assert len(config_hash) == 64
            
            # Create typed config
            typed_config = MillworkConfig.from_dict(config_dict)
            assert typed_config.scale_plan == 0.25
            assert typed_config.ada.counter_range == [28.0, 34.0]
            
        finally:
            config_file.unlink()  # Clean up
    
    def test_save_config_to_yaml(self, sample_millwork_config):
        """Test saving configuration to YAML file."""
        from src.core.config import save_config_to_yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            output_file = Path(f.name)
        
        try:
            # Save config to file
            save_config_to_yaml(sample_millwork_config, str(output_file))
            
            # Verify file was created and contains valid YAML
            assert output_file.exists()
            
            with open(output_file, 'r', encoding='utf-8') as f:
                loaded_data = yaml.safe_load(f)
            
            # Verify the data is correct
            assert loaded_data["SCALE_PLAN"] == sample_millwork_config.scale_plan
            assert loaded_data["COUNTER_HEIGHT"] == sample_millwork_config.counter_height
            assert "ADA" in loaded_data
            assert "PDF" in loaded_data
            
        finally:
            if output_file.exists():
                output_file.unlink()