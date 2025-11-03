"""
Tests for PDF renderer implementation.

This module tests the Phase 4 PDF rendering components including
the PDFRenderer class and ShopDrawingGenerator class.
"""

import pytest
from pathlib import Path
import tempfile
import os
from datetime import datetime

from src.core.interfaces import (
    IRenderer, RenderStyle, Point, DrawingMetadata, Rectangle, 
    LayoutResult, ModuleLayout, CountertopLayout, LayoutMetadata, ValidationResult
)
from src.renderer.pdf_renderer import PDFRenderer
from src.renderer.drawing_generator import ShopDrawingGenerator


class TestPDFRenderer:
    """Test cases for PDFRenderer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.renderer = PDFRenderer(scale=0.25, margins=[0.5, 0.5, 0.5, 0.5])
        self.test_metadata = DrawingMetadata(
            room_id="TEST-01",
            app_version="1.0.0",
            spec_version="1.0",
            config_sha256="test_hash",
            csv_sha256="test_csv_hash",
            timestamp=datetime.now().isoformat(),
            drawing_id="TEST-01",
            submittal_number="01"
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_pdf_renderer_initialization(self):
        """Test PDFRenderer initialization."""
        assert self.renderer.scale == 0.25
        assert self.renderer.margins == [0.5, 0.5, 0.5, 0.5]
        assert self.renderer.canvas is None
    
    def test_page_sizes(self):
        """Test page size definitions."""
        assert "letter" in PDFRenderer.PAGE_SIZES
        assert "tabloid" in PDFRenderer.PAGE_SIZES
        assert "a4" in PDFRenderer.PAGE_SIZES
    
    def test_style_definitions(self):
        """Test style definitions."""
        assert RenderStyle.THIN_LINE in PDFRenderer.STYLE_DEFINITIONS
        assert RenderStyle.MEDIUM_LINE in PDFRenderer.STYLE_DEFINITIONS
        assert RenderStyle.TEXT_MEDIUM in PDFRenderer.STYLE_DEFINITIONS
    
    def test_begin_page(self):
        """Test page initialization."""
        # Temporarily redirect output to temp directory
        original_path = "output/pdfs/TEST-01.pdf"
        
        self.renderer.begin_page(self.test_metadata, "letter")
        
        assert self.renderer.canvas is not None
        assert self.renderer.current_metadata == self.test_metadata
        assert self.renderer.page_width > 0
        assert self.renderer.page_height > 0
    
    def test_coordinate_transformation(self):
        """Test coordinate transformation."""
        self.renderer.begin_page(self.test_metadata, "letter")
        
        # Test coordinate transformation
        pdf_x, pdf_y = self.renderer._transform_coordinates(12.0, 6.0)
        
        # Should transform inches to points with scale
        expected_x = self.renderer.drawing_origin_x + (12.0 * 72 * 0.25)
        expected_y = self.renderer.drawing_origin_y + (6.0 * 72 * 0.25)
        
        assert pdf_x == expected_x
        assert pdf_y == expected_y
    
    def test_drawing_primitives_no_crash(self):
        """Test that drawing primitives don't crash."""
        self.renderer.begin_page(self.test_metadata, "letter")
        
        # Test rectangle drawing
        self.renderer.draw_rect(0, 0, 10, 5, RenderStyle.MEDIUM_LINE)
        
        # Test line drawing
        self.renderer.draw_line(0, 0, 10, 10, RenderStyle.THIN_LINE)
        
        # Test text drawing
        self.renderer.draw_text(5, 5, "Test Text", RenderStyle.TEXT_MEDIUM)
        
        # Test dimension drawing
        self.renderer.draw_dimension(0, 10, 0, "10\"")
        
        # Test polyline drawing
        points = [Point(0, 0), Point(5, 5), Point(10, 0)]
        self.renderer.draw_polyline(points, RenderStyle.THIN_LINE)
        
        # Should not crash
        assert True
    
    def test_unsupported_page_size(self):
        """Test error handling for unsupported page size."""
        with pytest.raises(ValueError, match="Unsupported page size"):
            self.renderer.begin_page(self.test_metadata, "invalid_size")
    
    def test_canvas_not_initialized_error(self):
        """Test error when drawing without initializing canvas."""
        with pytest.raises(RuntimeError, match="Canvas not initialized"):
            self.renderer.draw_rect(0, 0, 10, 5)


class TestShopDrawingGenerator:
    """Test cases for ShopDrawingGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "SCALE_PLAN": 0.25,
            "COUNTER_HEIGHT": 36.0,
            "BASE_DEPTH": 24.0,
            "TOLERANCES": {"LENGTH_SUM": 0.125},
            "PDF": {"SIZE": "letter", "MARGINS": [0.5, 0.5, 0.5, 0.5]},
            "EDGE_RULE": "MATCH_FACE"
        }
        self.renderer = PDFRenderer()
        self.generator = ShopDrawingGenerator(self.renderer, self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        assert self.generator.renderer == self.renderer
        assert self.generator.config == self.config
    
    def test_create_drawing_metadata(self):
        """Test drawing metadata creation."""
        layout = self._create_test_layout()
        metadata = self.generator._create_drawing_metadata(layout)
        
        assert metadata.room_id == "TEST-01"
        assert metadata.app_version == "1.0.0"
        assert metadata.drawing_id == "MW-TEST-01"
        assert metadata.submittal_number == "01"
    
    def test_generate_shop_drawing(self):
        """Test complete shop drawing generation."""
        layout = self._create_test_layout()
        output_dir = Path(self.temp_dir)
        
        # Generate shop drawing
        pdf_path = self.generator.generate_shop_drawing(layout, output_dir)
        
        # Verify PDF was created
        assert Path(pdf_path).exists()
        assert pdf_path.endswith("TEST-01.pdf")
        
        # Verify file has content
        assert os.path.getsize(pdf_path) > 1000  # Should be more than 1KB
    
    def _create_test_layout(self) -> LayoutResult:
        """Create a test layout for testing."""
        modules = [
            ModuleLayout(
                index=0, x=0.0, y=0.0,
                width=36.0, height=36.0, depth=24.0,
                material_code="PLM-WHT"
            ),
            ModuleLayout(
                index=1, x=36.0, y=0.0,
                width=30.0, height=36.0, depth=24.0,
                material_code="PLM-WHT"
            )
        ]
        
        countertop = CountertopLayout(
            x=0.0, y=24.0,
            width=66.0, depth=25.0, height=1.5,
            material_code="QTZ-01"
        )
        
        metadata = LayoutMetadata(
            room_id="TEST-01",
            timestamp=datetime.now().isoformat(),
            config_sha256="test_hash"
        )
        
        return LayoutResult(
            room_id="TEST-01",
            modules=modules,
            fillers=[],
            countertop=countertop,
            ada_layout=None,
            total_width=66.0,
            total_depth=25.0,
            bounding_box=Rectangle(0, 0, 66.0, 25.0),
            metadata=metadata,
            validation_result=ValidationResult(is_valid=True, errors=[], warnings=[])
        )


class TestPDFRendererIntegration:
    """Integration tests for PDF renderer with real data."""
    
    def test_integration_with_sample_data(self):
        """Test PDF generation with sample room data."""
        # This test verifies that the PDF renderer can handle real layout data
        # without crashing and produces valid output files
        
        from src.core.config import ConfigLoader
        from src.parser.csv_parser import CSVParser
        from src.parser.validator import RoomValidator
        from src.layout.parametric_engine import ParametricLayoutEngine
        
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config("config/default.yaml")
        
        # Parse sample CSV
        csv_parser = CSVParser()
        validator = RoomValidator()
        
        try:
            parsed_rooms, parse_result = csv_parser.parse_file(Path("input/sample_rooms.csv"))
            assert parse_result.is_valid
            
            # Validate rooms
            valid_rooms, _ = validator.validate_batch(parsed_rooms, config)
            assert len(valid_rooms) > 0
            
            # Compute layouts
            layout_engine = ParametricLayoutEngine(config)
            layouts = []
            
            for room in valid_rooms[:1]:  # Test with first room only
                layout = layout_engine.compute_layout(room, config)
                layouts.append(layout)
            
            # Generate PDFs
            renderer = PDFRenderer(
                scale=config.get("SCALE_PLAN", 0.25),
                margins=config.get("PDF", {}).get("MARGINS", [0.5, 0.5, 0.5, 0.5])
            )
            generator = ShopDrawingGenerator(renderer, config)
            
            temp_dir = Path(tempfile.mkdtemp())
            try:
                pdf_path = generator.generate_shop_drawing(layouts[0], temp_dir)
                
                # Verify PDF was created and has reasonable size
                assert Path(pdf_path).exists()
                assert os.path.getsize(pdf_path) > 2000  # Should be more than 2KB
                
            finally:
                # Clean up
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    
        except FileNotFoundError:
            # Skip test if sample data not available
            pytest.skip("Sample data files not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])