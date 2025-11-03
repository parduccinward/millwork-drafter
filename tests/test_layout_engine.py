"""
Test suite for the layout engine components.

Tests the ParametricLayoutEngine, GeometryUtils, and related functionality
with comprehensive coverage of layout computation scenarios.
"""

import pytest
from typing import Dict, Any
from unittest.mock import patch
import time

from src.layout.parametric_engine import ParametricLayoutEngine
from src.layout.geometry import GeometryUtils
from src.parser.schema import ParsedRoomData
from src.core.interfaces import (
    Rectangle, Point, LayoutResult, ModuleLayout, FillerLayout,
    CountertopLayout, LayoutMetadata, ValidationResult
)


class TestGeometryUtils:
    """Test suite for GeometryUtils class."""
    
    @pytest.fixture
    def config(self) -> Dict[str, Any]:
        """Sample configuration for testing."""
        return {
            "SCALE_PLAN": 0.25,
            "COUNTER_HEIGHT": 36.0,
            "BASE_DEPTH": 24.0,
            "TOLERANCES": {
                "LENGTH_SUM": 0.125,
                "LENGTH_ROUNDING": 2
            },
            "ADA": {
                "KNEE_CLEAR": "27\" H x 30\" W x 17\" D",
                "TOE_CLEAR": "9\" H x 6\" D",
                "COUNTER_RANGE": [28, 34],
                "CLEAR_WIDTHS": 32
            },
            "CODE": {
                "BASIS": "ADA 2010"
            }
        }
    
    @pytest.fixture
    def geometry_utils(self, config) -> GeometryUtils:
        """GeometryUtils instance for testing."""
        return GeometryUtils(config)
    
    def test_inches_to_points_conversion(self, geometry_utils):
        """Test inches to PostScript points conversion."""
        assert geometry_utils.inches_to_points(1.0) == 72.0
        assert geometry_utils.inches_to_points(0.5) == 36.0
        assert geometry_utils.inches_to_points(0) == 0
        assert geometry_utils.inches_to_points(2.5) == 180.0
    
    def test_points_to_inches_conversion(self, geometry_utils):
        """Test PostScript points to inches conversion."""
        assert geometry_utils.points_to_inches(72.0) == 1.0
        assert geometry_utils.points_to_inches(36.0) == 0.5
        assert geometry_utils.points_to_inches(0) == 0
        assert geometry_utils.points_to_inches(180.0) == 2.5
    
    def test_apply_scale(self, geometry_utils):
        """Test scale application."""
        # Use config scale
        assert geometry_utils.apply_scale(100.0) == 25.0  # 100 * 0.25
        
        # Override scale
        assert geometry_utils.apply_scale(100.0, 0.5) == 50.0
        assert geometry_utils.apply_scale(144.0, 0.25) == 36.0
    
    def test_round_to_tolerance(self, geometry_utils):
        """Test tolerance-based rounding."""
        # Use config tolerance (2 decimal places)
        assert geometry_utils.round_to_tolerance(1.2345) == 1.23
        assert geometry_utils.round_to_tolerance(5.6789) == 5.68
        
        # Override tolerance
        assert geometry_utils.round_to_tolerance(1.2345, 1) == 1.2
        assert geometry_utils.round_to_tolerance(1.2345, 0) == 1.0
    
    def test_calculate_bounding_box_empty(self, geometry_utils):
        """Test bounding box calculation with empty list."""
        result = geometry_utils.calculate_bounding_box([])
        assert result == Rectangle(0, 0, 0, 0)
    
    def test_calculate_bounding_box_single_rectangle(self, geometry_utils):
        """Test bounding box calculation with single rectangle."""
        rect = Rectangle(10, 20, 30, 40)
        result = geometry_utils.calculate_bounding_box([rect])
        assert result == rect
    
    def test_calculate_bounding_box_multiple_rectangles(self, geometry_utils):
        """Test bounding box calculation with multiple rectangles."""
        rectangles = [
            Rectangle(0, 0, 10, 10),
            Rectangle(5, 5, 10, 10),  # Overlapping
            Rectangle(20, 15, 5, 5)   # Separate
        ]
        
        result = geometry_utils.calculate_bounding_box(rectangles)
        
        # Should span from (0,0) to (25,20)
        assert result.x == 0
        assert result.y == 0
        assert result.width == 25  # 0 to 25 (20+5)
        assert result.height == 20  # 0 to 20 (15+5)
    
    def test_validate_length_sum_within_tolerance(self, geometry_utils):
        """Test length sum validation within tolerance."""
        module_widths = [36.0, 30.0, 36.0, 42.0]
        left_filler = 0.0
        right_filler = 0.0
        total_length = 144.0
        
        is_valid, difference = geometry_utils.validate_length_sum(
            module_widths, left_filler, right_filler, total_length
        )
        
        assert is_valid is True
        assert difference == 0.0
    
    def test_validate_length_sum_outside_tolerance(self, geometry_utils):
        """Test length sum validation outside tolerance."""
        module_widths = [36.0, 30.0, 36.0, 42.0]  # Sum = 144
        left_filler = 0.0
        right_filler = 0.0
        total_length = 144.5  # Difference = 0.5 > 0.125 tolerance
        
        is_valid, difference = geometry_utils.validate_length_sum(
            module_widths, left_filler, right_filler, total_length
        )
        
        assert is_valid is False
        assert difference == 0.5
    
    def test_validate_length_sum_with_fillers(self, geometry_utils):
        """Test length sum validation with fillers."""
        module_widths = [36.0, 36.0, 36.0]  # Sum = 108
        left_filler = 3.0
        right_filler = 3.0
        total_length = 114.0  # 108 + 3 + 3 = 114
        
        is_valid, difference = geometry_utils.validate_length_sum(
            module_widths, left_filler, right_filler, total_length
        )
        
        assert is_valid is True
        assert difference == 0.0
    
    def test_center_point(self, geometry_utils):
        """Test center point calculation."""
        rect = Rectangle(10, 20, 40, 60)
        center = geometry_utils.center_point(rect)
        
        assert center.x == 30.0  # 10 + 40/2
        assert center.y == 50.0  # 20 + 60/2
    
    def test_offset_rectangle(self, geometry_utils):
        """Test rectangle offset."""
        rect = Rectangle(10, 20, 30, 40)
        offset_rect = geometry_utils.offset_rectangle(rect, 5, -10)
        
        assert offset_rect.x == 15  # 10 + 5
        assert offset_rect.y == 10  # 20 - 10
        assert offset_rect.width == 30  # Unchanged
        assert offset_rect.height == 40  # Unchanged
    
    def test_scale_rectangle_uniform(self, geometry_utils):
        """Test uniform rectangle scaling."""
        rect = Rectangle(10, 20, 30, 40)
        scaled_rect = geometry_utils.scale_rectangle(rect, 2.0)
        
        assert scaled_rect.x == 10  # Position unchanged
        assert scaled_rect.y == 20  # Position unchanged
        assert scaled_rect.width == 60  # 30 * 2
        assert scaled_rect.height == 80  # 40 * 2
    
    def test_scale_rectangle_non_uniform(self, geometry_utils):
        """Test non-uniform rectangle scaling."""
        rect = Rectangle(10, 20, 30, 40)
        scaled_rect = geometry_utils.scale_rectangle(rect, 2.0, 0.5)
        
        assert scaled_rect.x == 10  # Position unchanged
        assert scaled_rect.y == 20  # Position unchanged
        assert scaled_rect.width == 60  # 30 * 2
        assert scaled_rect.height == 20  # 40 * 0.5
    
    def test_parse_clearance_string_full(self, geometry_utils):
        """Test parsing full clearance string."""
        clearance = "27\" H x 30\" W x 17\" D"
        dimensions = geometry_utils._parse_clearance_string(clearance)
        
        assert dimensions["height"] == 27.0
        assert dimensions["width"] == 30.0
        assert dimensions["depth"] == 17.0
    
    def test_parse_clearance_string_partial(self, geometry_utils):
        """Test parsing partial clearance string."""
        clearance = "9\" H x 6\" D"
        dimensions = geometry_utils._parse_clearance_string(clearance)
        
        assert dimensions["height"] == 9.0
        assert dimensions["width"] == 0  # Not specified
        assert dimensions["depth"] == 6.0
    
    def test_get_ada_clearance_dimensions(self, geometry_utils):
        """Test ADA clearance dimensions extraction."""
        ada_dims = geometry_utils.get_ada_clearance_dimensions()
        
        assert ada_dims["knee"]["height"] == 27.0
        assert ada_dims["knee"]["width"] == 30.0
        assert ada_dims["knee"]["depth"] == 17.0
        assert ada_dims["toe"]["height"] == 9.0
        assert ada_dims["toe"]["depth"] == 6.0
        assert ada_dims["counter_range"] == [28, 34]
        assert ada_dims["clear_widths"] == 32
        assert ada_dims["code_basis"] == "ADA 2010"
    
    def test_create_ada_boxes(self, geometry_utils):
        """Test ADA clearance box creation."""
        countertop_rect = Rectangle(0, 36, 144, 24)  # Standard countertop
        counter_height = 36.0
        
        knee_box, toe_box = geometry_utils.create_ada_boxes(countertop_rect, counter_height)
        
        # Knee box should be positioned below counter
        assert knee_box.x == 0
        assert knee_box.y == 9  # 36 - 27 (knee height)
        assert knee_box.width == 30  # From ADA config
        assert knee_box.height == 27  # From ADA config
        
        # Toe box should be positioned below knee box
        assert toe_box.x == 0
        assert toe_box.y == 0  # 9 - 9 (toe height)
        assert toe_box.width == 144  # Full countertop width
        assert toe_box.height == 9  # From ADA config


class TestParametricLayoutEngine:
    """Test suite for ParametricLayoutEngine class."""
    
    @pytest.fixture
    def config(self) -> Dict[str, Any]:
        """Sample configuration for testing."""
        return {
            "SCALE_PLAN": 0.25,
            "COUNTER_HEIGHT": 36.0,
            "BASE_DEPTH": 24.0,
            "TOLERANCES": {
                "LENGTH_SUM": 0.125,
                "LENGTH_ROUNDING": 2
            },
            "ADA": {
                "KNEE_CLEAR": "27\" H x 30\" W x 17\" D",
                "TOE_CLEAR": "9\" H x 6\" D",
                "COUNTER_RANGE": [28, 34],
                "CLEAR_WIDTHS": 32
            },
            "CODE": {
                "BASIS": "ADA 2010"
            }
        }
    
    @pytest.fixture
    def layout_engine(self, config) -> ParametricLayoutEngine:
        """ParametricLayoutEngine instance for testing."""
        return ParametricLayoutEngine(config)
    
    @pytest.fixture
    def sample_room_data(self) -> ParsedRoomData:
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
            has_ref=False,
            counter_height_in=None,  # Use config default
            edge_rule=None,
            hardware_defaults=None,
            notes=None,
            references=None,
            row_number=1,
            source_file="test.csv"
        )
    
    def test_compute_layout_basic(self, layout_engine, config, sample_room_data):
        """Test basic layout computation without fillers."""
        result = layout_engine.compute_layout(sample_room_data, config)
        
        # Verify basic result structure
        assert isinstance(result, LayoutResult)
        assert result.room_id == "KITCHEN-01"
        assert result.validation_result.is_valid is True
        
        # Verify modules
        assert len(result.modules) == 4
        assert result.modules[0].width == 36.0
        assert result.modules[1].width == 30.0
        assert result.modules[2].width == 36.0
        assert result.modules[3].width == 42.0
        
        # Verify module positioning
        assert result.modules[0].x == 0.0  # No left filler
        assert result.modules[1].x == 36.0  # After first module
        assert result.modules[2].x == 66.0  # After second module
        assert result.modules[3].x == 102.0  # After third module
        
        # Verify no fillers
        assert len(result.fillers) == 0
        
        # Verify countertop
        assert result.countertop.width == 144.0  # Total width
        assert result.countertop.material_code == "QTZ-01"
        
        # Verify total dimensions
        assert result.total_width == 144.0
    
    def test_compute_layout_with_fillers(self, layout_engine, config):
        """Test layout computation with filler strips."""
        room_data = ParsedRoomData(
            room_id="KITCHEN-02",
            total_length_in=150.0,
            num_modules=3,
            module_widths=[36.0, 36.0, 36.0],  # 108 total
            material_top="QTZ-01",
            material_casework="PLM-WHT",
            left_filler_in=3.0,
            right_filler_in=3.0,  # 108 + 3 + 3 = 114, not 150 - should cause validation error
            has_sink=False,
            has_ref=False,
            row_number=1
        )
        
        result = layout_engine.compute_layout(room_data, config)
        
        # Should have validation error due to length mismatch
        assert result.validation_result.is_valid is False
        assert len(result.validation_result.errors) > 0
        
        # But layout should still be computed
        assert len(result.modules) == 3
        assert len(result.fillers) == 2
        
        # Verify filler positions
        left_filler = next(f for f in result.fillers if f.side == "left")
        right_filler = next(f for f in result.fillers if f.side == "right")
        
        assert left_filler.x == 0.0
        assert left_filler.width == 3.0
        assert right_filler.x == 111.0  # 3 + 36 + 36 + 36
        assert right_filler.width == 3.0
        
        # Verify module positions (after left filler)
        assert result.modules[0].x == 3.0
        assert result.modules[1].x == 39.0
        assert result.modules[2].x == 75.0
    
    def test_compute_layout_with_custom_counter_height(self, layout_engine, config):
        """Test layout computation with custom counter height."""
        room_data = ParsedRoomData(
            room_id="BATH-01",
            total_length_in=72.0,
            num_modules=2,
            module_widths=[36.0, 36.0],
            material_top="LAM-01",
            material_casework="PLM-WHT",
            counter_height_in=34.0,  # Custom height
            row_number=1
        )
        
        result = layout_engine.compute_layout(room_data, config)
        
        # Verify custom counter height is used
        assert result.countertop.y == 34.0  # Custom height, not config default
        
        # Verify modules use config height (base cabinet height)
        assert all(module.height == 36.0 for module in result.modules)
    
    def test_compute_layout_with_ada(self, layout_engine, config, sample_room_data):
        """Test layout computation with ADA compliance boxes."""
        result = layout_engine.compute_layout(sample_room_data, config)
        
        # Should have ADA layout since config includes ADA parameters
        assert result.ada_layout is not None
        assert result.ada_layout.code_basis == "ADA 2010"
        assert result.ada_layout.approach_width == 32
        
        # Verify clearance boxes exist
        assert result.ada_layout.knee_clear_box is not None
        assert result.ada_layout.toe_clear_box is not None
    
    def test_compute_layout_without_ada(self, layout_engine, sample_room_data):
        """Test layout computation without ADA configuration."""
        config_no_ada = {
            "COUNTER_HEIGHT": 36.0,
            "BASE_DEPTH": 24.0,
            "TOLERANCES": {"LENGTH_SUM": 0.125}
        }
        
        result = layout_engine.compute_layout(sample_room_data, config_no_ada)
        
        # Should not have ADA layout
        assert result.ada_layout is None
    
    def test_validate_geometry_valid(self, layout_engine, config, sample_room_data):
        """Test geometry validation with valid layout."""
        result = layout_engine.compute_layout(sample_room_data, config)
        
        # Validate the computed layout
        validation = layout_engine.validate_geometry(result, config["TOLERANCES"])
        
        assert validation.is_valid is True
        assert len(validation.errors) == 0
    
    def test_validate_geometry_invalid_width(self, layout_engine, config):
        """Test geometry validation with invalid module width."""
        # Create layout with invalid module width
        invalid_layout = LayoutResult(
            room_id="TEST-01",
            modules=[
                ModuleLayout(0, 0, 0, -10, 36, 24, "PLM-WHT")  # Negative width
            ],
            fillers=[],
            countertop=CountertopLayout(0, 36, 0, 24, 1.5, "QTZ-01"),
            ada_layout=None,
            total_width=0,
            total_depth=24,
            bounding_box=Rectangle(0, 0, 0, 60),
            metadata=LayoutMetadata("TEST-01", "2024-01-01", "hash123"),
            validation_result=ValidationResult(True, [], [])
        )
        
        validation = layout_engine.validate_geometry(invalid_layout, config["TOLERANCES"])
        
        assert validation.is_valid is False
        assert len(validation.errors) > 0
        assert any("invalid width" in error.message for error in validation.errors)
    
    def test_error_handling(self, layout_engine, config):
        """Test error handling in layout computation."""
        # Create malformed room data that should cause an error
        with patch.object(layout_engine, '_compute_module_positions', side_effect=Exception("Test error")):
            room_data = ParsedRoomData(
                room_id="ERROR-01",
                total_length_in=144.0,
                num_modules=4,
                module_widths=[36.0, 30.0, 36.0, 42.0],
                material_top="QTZ-01",
                material_casework="PLM-WHT",
                row_number=1
            )
            
            result = layout_engine.compute_layout(room_data, config)
            
            # Should return error result
            assert result.validation_result.is_valid is False
            assert len(result.validation_result.errors) > 0
            assert "Layout computation failed" in result.validation_result.errors[0].message
            
            # Should have empty layout
            assert len(result.modules) == 0
            assert len(result.fillers) == 0
    
    def test_metadata_generation(self, layout_engine, config, sample_room_data):
        """Test layout metadata generation."""
        result = layout_engine.compute_layout(sample_room_data, config)
        
        assert result.metadata.room_id == "KITCHEN-01"
        assert result.metadata.layout_version == "1.0"
        assert result.metadata.config_sha256 is not None
        assert len(result.metadata.config_sha256) == 16  # First 16 chars of SHA256
        assert result.metadata.computation_time_ms is not None
        assert result.metadata.computation_time_ms > 0
        assert result.metadata.tolerance_used == 0.125


class TestLayoutIntegration:
    """Integration tests for the complete layout system."""
    
    def test_end_to_end_layout_computation(self):
        """Test complete end-to-end layout computation."""
        # Configuration
        config = {
            "SCALE_PLAN": 0.25,
            "COUNTER_HEIGHT": 36.0,
            "BASE_DEPTH": 24.0,
            "TOLERANCES": {"LENGTH_SUM": 0.125, "LENGTH_ROUNDING": 2},
            "ADA": {
                "KNEE_CLEAR": "27\" H x 30\" W x 17\" D",
                "TOE_CLEAR": "9\" H x 6\" D",
                "COUNTER_RANGE": [28, 34],
                "CLEAR_WIDTHS": 32
            },
            "CODE": {"BASIS": "ADA 2010"}
        }
        
        # Room data
        room_data = ParsedRoomData(
            room_id="OFFICE-01",
            total_length_in=96.0,
            num_modules=3,
            module_widths=[24.0, 48.0, 24.0],
            material_top="LAM-02",
            material_casework="OAK-NAT",
            left_filler_in=0.0,
            right_filler_in=0.0,
            has_sink=False,
            has_ref=False,
            counter_height_in=30.0,
            row_number=1
        )
        
        # Compute layout
        engine = ParametricLayoutEngine(config)
        result = engine.compute_layout(room_data, config)
        
        # Comprehensive validation
        assert result.validation_result.is_valid is True
        assert result.room_id == "OFFICE-01"
        assert len(result.modules) == 3
        assert len(result.fillers) == 0
        assert result.ada_layout is not None
        assert result.total_width == 96.0
        assert result.countertop.material_code == "LAM-02"
        assert result.countertop.y == 30.0  # Custom height
        
        # Verify geometric consistency
        module_total = sum(m.width for m in result.modules)
        assert module_total == 96.0
        
        # Verify ADA compliance
        assert result.ada_layout.counter_height == 30.0
        assert result.ada_layout.code_basis == "ADA 2010"