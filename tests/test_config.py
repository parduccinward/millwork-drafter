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