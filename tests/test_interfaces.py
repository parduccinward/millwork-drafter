"""
Unit tests for core interfaces.

Tests the abstract interfaces and data structures defined in the core module.
"""

import pytest
from src.core.interfaces import (
    Point, Rectangle, DrawingMetadata, ValidationResult, ValidationError,
    LayoutElement, ModuleElement, FillerElement, CountertopElement, ADAElement,
    RenderStyle
)


class TestDataStructures:
    """Test core data structures."""
    
    def test_point_creation(self):
        """Test Point dataclass creation."""
        point = Point(x=10.5, y=20.3)
        assert point.x == 10.5
        assert point.y == 20.3
    
    def test_rectangle_creation(self):
        """Test Rectangle dataclass creation."""
        rect = Rectangle(x=0, y=0, width=36, height=24)
        assert rect.x == 0
        assert rect.y == 0
        assert rect.width == 36
        assert rect.height == 24
    
    def test_drawing_metadata_creation(self):
        """Test DrawingMetadata creation."""
        metadata = DrawingMetadata(
            room_id="KITCHEN-01",
            app_version="0.1.0",
            spec_version="1.0",
            config_sha256="abc123",
            csv_sha256="def456",
            timestamp="2025-11-02T10:00:00Z"
        )
        assert metadata.room_id == "KITCHEN-01"
        assert metadata.app_version == "0.1.0"
        assert metadata.drawing_id is None  # Optional field


class TestValidationResult:
    """Test ValidationResult functionality."""
    
    def test_empty_validation_result(self):
        """Test creating empty validation result."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_add_error(self):
        """Test adding validation error."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_error("field1", "Error message", "invalid_value")
        
        assert not result.is_valid  # Should become invalid
        assert len(result.errors) == 1
        assert result.errors[0].field == "field1"
        assert result.errors[0].message == "Error message"
        assert result.errors[0].value == "invalid_value"
        assert result.errors[0].error_type == "error"
    
    def test_add_warning(self):
        """Test adding validation warning."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_warning("field1", "Warning message", "suspect_value")
        
        assert result.is_valid  # Should remain valid
        assert len(result.warnings) == 1
        assert result.warnings[0].field == "field1"
        assert result.warnings[0].message == "Warning message"
        assert result.warnings[0].error_type == "warning"
    
    def test_multiple_errors_and_warnings(self):
        """Test adding multiple errors and warnings."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        result.add_error("field1", "Error 1", "value1")
        result.add_error("field2", "Error 2", "value2")
        result.add_warning("field3", "Warning 1", "value3")
        
        assert not result.is_valid
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


class TestLayoutElements:
    """Test layout element data structures."""
    
    def test_module_element_creation(self):
        """Test ModuleElement creation."""
        bounds = Rectangle(x=0, y=0, width=36, height=24)
        module = ModuleElement(
            bounds=bounds,
            style=RenderStyle.THIN_LINE,
            metadata={},
            width=36.0,
            depth=24.0,
            material_code="PLM-WHT"
        )
        
        assert module.element_type == "module"
        assert module.width == 36.0
        assert module.depth == 24.0
        assert module.material_code == "PLM-WHT"
    
    def test_filler_element_creation(self):
        """Test FillerElement creation."""
        bounds = Rectangle(x=0, y=0, width=2, height=24)
        filler = FillerElement(
            bounds=bounds,
            style=RenderStyle.THIN_LINE,
            metadata={},
            width=2.0,
            position="left"
        )
        
        assert filler.element_type == "filler"
        assert filler.width == 2.0
        assert filler.position == "left"
    
    def test_countertop_element_creation(self):
        """Test CountertopElement creation."""
        bounds = Rectangle(x=0, y=24, width=144, height=1.5)
        countertop = CountertopElement(
            bounds=bounds,
            style=RenderStyle.MEDIUM_LINE,
            metadata={},
            material_code="QTZ-01",
            thickness=1.5,
            overhang=1.0
        )
        
        assert countertop.element_type == "countertop"
        assert countertop.material_code == "QTZ-01"
        assert countertop.thickness == 1.5
        assert countertop.overhang == 1.0
    
    def test_ada_element_creation(self):
        """Test ADAElement creation."""
        bounds = Rectangle(x=0, y=-27, width=30, height=27)
        ada_box = ADAElement(
            bounds=bounds,
            style=RenderStyle.HIDDEN_LINE,
            metadata={},
            knee_clear="27\" H x 30\" W x 17\" D",
            toe_clear="9\" H x 6\" D",
            counter_range="28\"-34\" AFF",
            code_basis="ADA 2010"
        )
        
        assert ada_box.element_type == "ada_box"
        assert ada_box.knee_clear == "27\" H x 30\" W x 17\" D"
        assert ada_box.code_basis == "ADA 2010"


class TestRenderStyle:
    """Test RenderStyle enumeration."""
    
    def test_render_style_values(self):
        """Test RenderStyle enum values."""
        assert RenderStyle.THIN_LINE.value == "thin"
        assert RenderStyle.MEDIUM_LINE.value == "medium"
        assert RenderStyle.THICK_LINE.value == "thick"
        assert RenderStyle.DIMENSION_LINE.value == "dimension"
        assert RenderStyle.TEXT_MEDIUM.value == "text_medium"
    
    def test_render_style_membership(self):
        """Test RenderStyle enum membership."""
        styles = list(RenderStyle)
        assert RenderStyle.THIN_LINE in styles
        assert RenderStyle.HATCH_WOOD in styles
        assert len(styles) >= 10  # Should have at least 10 styles defined