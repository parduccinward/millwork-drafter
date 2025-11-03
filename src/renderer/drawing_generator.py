"""
Drawing generation engine for millwork shop drawings.

This module takes LayoutResult objects from the layout engine and generates
complete shop drawings using the PDF renderer, following memory bank specifications.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import datetime

from ..core.interfaces import (
    IRenderer, LayoutResult, DrawingMetadata, RenderStyle, Point
)


class ShopDrawingGenerator:
    """
    High-level drawing generator that creates complete shop drawings.
    
    Takes validated layout results and produces professional shop drawings
    following millwork industry standards from the memory banks.
    """
    
    def __init__(self, renderer: IRenderer, config: Dict[str, Any]):
        """
        Initialize drawing generator.
        
        Args:
            renderer: IRenderer implementation (e.g., PDFRenderer)
            config: Configuration dictionary with drawing parameters
        """
        self.renderer = renderer
        self.config = config
        
    def generate_shop_drawing(self, layout: LayoutResult, 
                            output_dir: Path = Path("output/pdfs")) -> str:
        """
        Generate complete shop drawing for a room layout.
        
        Args:
            layout: Complete geometric layout from layout engine
            output_dir: Output directory for PDF files
            
        Returns:
            Path to generated PDF file
        """
        # Create drawing metadata
        metadata = self._create_drawing_metadata(layout)
        
        # Initialize page
        page_size = self.config.get("PDF", {}).get("SIZE", "letter")
        output_path = str(output_dir / f"{layout.room_id}.pdf")
        self.renderer.begin_page(metadata, page_size, output_path)
        
        # Generate drawing content
        self._draw_plan_view(layout)
        self._draw_elevation_view(layout)
        self._draw_dimensions(layout)
        self._draw_material_labels(layout)
        self._draw_ada_compliance(layout)
        self._draw_notes_and_specifications(layout)
        
        # Finalize page
        self.renderer.end_page()
        
        # Save drawing
        output_path = str(output_dir / f"{layout.room_id}.pdf")
        self.renderer.save(output_path)
        
        return output_path
        
    def _create_drawing_metadata(self, layout: LayoutResult) -> DrawingMetadata:
        """Create drawing metadata from layout result."""
        return DrawingMetadata(
            room_id=layout.room_id,
            app_version="1.0.0",
            spec_version="1.0",
            config_sha256=layout.metadata.config_sha256,
            csv_sha256="",  # Will be set by CLI
            timestamp=datetime.datetime.now().isoformat(),
            drawing_id=f"MW-{layout.room_id}",
            submittal_number="01"
        )
        
    def _draw_plan_view(self, layout: LayoutResult) -> None:
        """Draw plan view of the millwork layout."""
        # Drawing origin for plan view (centered in available space)
        plan_origin_x = 24.0  # 2 feet from left margin
        plan_origin_y = 12.0  # 1 foot from bottom
        
        # Draw base modules
        for module in layout.modules:
            module_x = plan_origin_x + module.x
            module_y = plan_origin_y + module.y
            
            # Draw module rectangle
            self.renderer.draw_rect(
                module_x, module_y, 
                module.width, module.depth,
                RenderStyle.MEDIUM_LINE
            )
            
            # Add module number label
            label_x = module_x + module.width / 2
            label_y = module_y + module.depth / 2
            self.renderer.draw_text(
                label_x, label_y, 
                f"M{module.index + 1}",
                RenderStyle.TEXT_MEDIUM
            )
            
        # Draw fillers
        for filler in layout.fillers:
            filler_x = plan_origin_x + filler.x
            filler_y = plan_origin_y + filler.y
            
            # Draw filler rectangle with different style
            self.renderer.draw_rect(
                filler_x, filler_y,
                filler.width, filler.depth,
                RenderStyle.THIN_LINE
            )
            
            # Add filler label
            label_x = filler_x + filler.width / 2
            label_y = filler_y + filler.depth / 2
            self.renderer.draw_text(
                label_x, label_y,
                f"F-{filler.side[0].upper()}",
                RenderStyle.TEXT_SMALL
            )
            
        # Draw countertop
        if layout.countertop:
            countertop_x = plan_origin_x + layout.countertop.x
            countertop_y = plan_origin_y + layout.countertop.y
            
            # Draw countertop outline (slightly larger than base)
            overhang = 1.0  # 1 inch overhang
            counter_y_offset = layout.countertop.y + layout.modules[0].depth - overhang
            
            self.renderer.draw_rect(
                countertop_x, countertop_y + counter_y_offset,
                layout.countertop.width, layout.countertop.depth,
                RenderStyle.THICK_LINE
            )
            
            # Add countertop material label
            label_x = countertop_x + layout.countertop.width / 2
            label_y = countertop_y + counter_y_offset + layout.countertop.depth / 2
            self.renderer.draw_text(
                label_x, label_y,
                layout.countertop.material_code,
                RenderStyle.TEXT_MEDIUM
            )
    
    def _draw_elevation_view(self, layout: LayoutResult) -> None:
        """Draw elevation view showing heights and details."""
        # Elevation view position (to the right of plan view)
        elev_origin_x = 120.0  # 10 feet from left margin
        elev_origin_y = 12.0   # Same as plan view
        
        # Get configuration values
        counter_height = self.config.get("COUNTER_HEIGHT", 36.0)
        base_depth = self.config.get("BASE_DEPTH", 24.0)
        
        # Draw base cabinets in elevation
        for module in layout.modules:
            module_x = elev_origin_x + module.x
            
            # Draw base cabinet
            self.renderer.draw_rect(
                module_x, elev_origin_y,
                module.width, counter_height,
                RenderStyle.MEDIUM_LINE
            )
            
            # Draw toe kick
            toe_kick_height = 4.0  # 4 inch toe kick
            self.renderer.draw_rect(
                module_x, elev_origin_y,
                module.width, toe_kick_height,
                RenderStyle.THIN_LINE
            )
            
            # Add door/drawer representation
            door_margin = 2.0  # 2 inch margin for doors
            self.renderer.draw_rect(
                module_x + door_margin, elev_origin_y + toe_kick_height + door_margin,
                module.width - 2 * door_margin, counter_height - toe_kick_height - 2 * door_margin,
                RenderStyle.THIN_LINE
            )
        
        # Draw countertop in elevation
        if layout.countertop:
            countertop_thickness = 1.5  # 1.5 inch thick countertop
            self.renderer.draw_rect(
                elev_origin_x, elev_origin_y + counter_height,
                layout.total_width, countertop_thickness,
                RenderStyle.THICK_LINE
            )
    
    def _draw_dimensions(self, layout: LayoutResult) -> None:
        """Draw dimensions for the layout."""
        plan_origin_x = 24.0
        plan_origin_y = 12.0
        
        # Overall dimension
        overall_y = plan_origin_y - 6.0  # 6 inches below plan
        self.renderer.draw_dimension(
            plan_origin_x, 
            plan_origin_x + layout.total_width,
            overall_y,
            f"{layout.total_width:.1f}\""
        )
        
        # Individual module dimensions
        module_y = plan_origin_y - 12.0  # 12 inches below plan
        current_x = plan_origin_x
        
        for module in layout.modules:
            module_end_x = current_x + module.width
            self.renderer.draw_dimension(
                current_x,
                module_end_x,
                module_y,
                f"{module.width:.1f}\""
            )
            current_x = module_end_x
            
        # Add filler dimensions if present
        for filler in layout.fillers:
            filler_x = plan_origin_x + filler.x
            self.renderer.draw_dimension(
                filler_x,
                filler_x + filler.width,
                module_y - 6.0,  # 6 inches below module dimensions
                f"F{filler.width:.1f}\""
            )
    
    def _draw_material_labels(self, layout: LayoutResult) -> None:
        """Draw material labels and specifications."""
        # Material schedule position
        schedule_x = 12.0
        schedule_y = 60.0
        
        # Title
        self.renderer.draw_text(
            schedule_x, schedule_y,
            "MATERIAL SCHEDULE",
            RenderStyle.TEXT_LARGE
        )
        
        # Countertop material
        self.renderer.draw_text(
            schedule_x, schedule_y - 12.0,
            f"Countertop: {layout.countertop.material_code}",
            RenderStyle.TEXT_MEDIUM
        )
        
        # Base cabinet material (from first module)
        if layout.modules:
            self.renderer.draw_text(
                schedule_x, schedule_y - 24.0,
                f"Base Cabinets: {layout.modules[0].material_code}",
                RenderStyle.TEXT_MEDIUM
            )
        
        # Edge treatment
        edge_rule = self.config.get("EDGE_RULE", "MATCH_FACE")
        self.renderer.draw_text(
            schedule_x, schedule_y - 36.0,
            f"Edge Treatment: {edge_rule}",
            RenderStyle.TEXT_MEDIUM
        )
    
    def _draw_ada_compliance(self, layout: LayoutResult) -> None:
        """Draw ADA compliance elements if applicable."""
        if not layout.ada_layout:
            return
        
        # ADA diagram position
        ada_x = 120.0
        ada_y = 60.0
        
        # ADA title
        self.renderer.draw_text(
            ada_x, ada_y,
            "ADA COMPLIANCE",
            RenderStyle.TEXT_LARGE
        )
        
        # Code basis
        self.renderer.draw_text(
            ada_x, ada_y - 12.0,
            f"Code Basis: {layout.ada_layout.code_basis}",
            RenderStyle.TEXT_MEDIUM
        )
        
        # Draw knee clearance box
        knee_box = layout.ada_layout.knee_clear_box
        self.renderer.draw_rect(
            ada_x, ada_y - 36.0,
            knee_box.width, knee_box.height,
            RenderStyle.MEDIUM_LINE
        )
        
        # Knee clearance label
        self.renderer.draw_text(
            ada_x + knee_box.width / 2, ada_y - 36.0 + knee_box.height / 2,
            "KNEE CLEARANCE",
            RenderStyle.TEXT_SMALL
        )
        
        # Draw toe clearance box
        toe_box = layout.ada_layout.toe_clear_box
        self.renderer.draw_rect(
            ada_x, ada_y - 48.0,
            toe_box.width, toe_box.height,
            RenderStyle.THIN_LINE
        )
        
        # Toe clearance label
        self.renderer.draw_text(
            ada_x + toe_box.width / 2, ada_y - 48.0 + toe_box.height / 2,
            "TOE CLEARANCE",
            RenderStyle.TEXT_SMALL
        )
        
        # Counter height note
        self.renderer.draw_text(
            ada_x, ada_y - 60.0,
            f"Counter Height: {layout.ada_layout.counter_height:.1f}\"",
            RenderStyle.TEXT_MEDIUM
        )
    
    def _draw_notes_and_specifications(self, layout: LayoutResult) -> None:
        """Draw construction notes and specifications."""
        notes_x = 12.0
        notes_y = 30.0
        
        # Notes title
        self.renderer.draw_text(
            notes_x, notes_y,
            "CONSTRUCTION NOTES",
            RenderStyle.TEXT_LARGE
        )
        
        # Standard construction notes
        notes = [
            "1. All dimensions to be verified in field",
            "2. Provide backing for all wall-mounted units",
            "3. Coordinate with electrical and plumbing rough-in",
            "4. Finish exposed edges to match face material",
            "5. Install per manufacturer's recommendations"
        ]
        
        for i, note in enumerate(notes):
            self.renderer.draw_text(
                notes_x, notes_y - 12.0 - (i * 8.0),
                note,
                RenderStyle.TEXT_SMALL
            )
        
        # Tolerance note
        tolerance = self.config.get("TOLERANCES", {}).get("LENGTH_SUM", 0.125)
        self.renderer.draw_text(
            notes_x, notes_y - 60.0,
            f"Fabrication tolerance: ±{tolerance}\"",
            RenderStyle.TEXT_SMALL
        )