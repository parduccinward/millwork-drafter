"""
PDF Renderer implementation for millwork shop drawings.

This module implements the IRenderer interface using ReportLab to generate
professional-quality vector PDFs for millwork shop drawings.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import math

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, A3, TABLOID
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfutils
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from ..core.interfaces import IRenderer, RenderStyle, Point, DrawingMetadata


class PDFRenderer(IRenderer):
    """
    ReportLab-based PDF renderer implementing the IRenderer interface.
    
    Generates professional-quality vector PDFs for millwork shop drawings
    with proper scaling, styling, and metadata integration.
    """
    
    # Page size mapping
    PAGE_SIZES = {
        "letter": letter,
        "tabloid": TABLOID,
        "ansi-d": (34 * inch, 22 * inch),
        "ansi-e": (44 * inch, 34 * inch),
        "a4": A4,
        "a3": A3
    }
    
    # Style definitions for shop drawings
    STYLE_DEFINITIONS = {
        RenderStyle.THIN_LINE: {
            "line_width": 0.25,
            "color": colors.black,
            "dash_pattern": None
        },
        RenderStyle.MEDIUM_LINE: {
            "line_width": 0.5,
            "color": colors.black,
            "dash_pattern": None
        },
        RenderStyle.THICK_LINE: {
            "line_width": 1.0,
            "color": colors.black,
            "dash_pattern": None
        },
        RenderStyle.HIDDEN_LINE: {
            "line_width": 0.25,
            "color": colors.grey,
            "dash_pattern": [2, 2]
        },
        RenderStyle.CENTER_LINE: {
            "line_width": 0.25,
            "color": colors.black,
            "dash_pattern": [6, 2, 2, 2]
        },
        RenderStyle.DIMENSION_LINE: {
            "line_width": 0.25,
            "color": colors.black,
            "dash_pattern": None
        },
        RenderStyle.TEXT_SMALL: {
            "font_name": "Helvetica",
            "font_size": 8,
            "color": colors.black
        },
        RenderStyle.TEXT_MEDIUM: {
            "font_name": "Helvetica",
            "font_size": 10,
            "color": colors.black
        },
        RenderStyle.TEXT_LARGE: {
            "font_name": "Helvetica-Bold",
            "font_size": 12,
            "color": colors.black
        },
        RenderStyle.HATCH_WOOD: {
            "line_width": 0.25,
            "color": colors.brown,
            "spacing": 3.0
        },
        RenderStyle.HATCH_INSULATION: {
            "line_width": 0.25,
            "color": colors.pink,
            "spacing": 2.0
        }
    }
    
    def __init__(self, scale: float = 0.25, margins: Optional[List[float]] = None):
        """
        Initialize PDF renderer.
        
        Args:
            scale: Drawing scale (e.g., 0.25 for 1/4" = 1')
            margins: Page margins [left, bottom, right, top] in inches
        """
        self.scale = scale
        self.margins = margins or [0.5, 0.5, 0.5, 0.5]  # Default 0.5" margins
        self.canvas: Optional[canvas.Canvas] = None
        self.page_width = 0.0
        self.page_height = 0.0
        self.drawing_origin_x = 0.0
        self.drawing_origin_y = 0.0
        self.current_metadata: Optional[DrawingMetadata] = None
        self.current_output_path: Optional[str] = None
        
    def begin_page(self, metadata: DrawingMetadata, page_size: str = "letter", output_path: str = None) -> None:
        """Initialize a new drawing page with metadata."""
        # Use provided output path or create default
        if output_path is None:
            output_path = f"output/pdfs/{metadata.room_id}.pdf"
        
        # Create output directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Get page dimensions
        if page_size.lower() not in self.PAGE_SIZES:
            raise ValueError(f"Unsupported page size: {page_size}")
        
        page_dimensions = self.PAGE_SIZES[page_size.lower()]
        self.page_width, self.page_height = page_dimensions
        
        # Initialize canvas
        self.canvas = canvas.Canvas(output_path, pagesize=page_dimensions)
        self.current_metadata = metadata
        self.current_output_path = output_path
        
        # Calculate drawing area origin (bottom-left of drawing area)
        self.drawing_origin_x = self.margins[0] * inch
        self.drawing_origin_y = self.margins[1] * inch
        
        # Set up PDF metadata
        self._setup_pdf_metadata()
        
        # Draw title block and border
        self._draw_title_block()
        self._draw_page_border()
        
    def draw_rect(self, x: float, y: float, width: float, height: float, 
                  style: RenderStyle = RenderStyle.THIN_LINE) -> None:
        """Draw a rectangle with specified coordinates and style."""
        if not self.canvas:
            raise RuntimeError("Canvas not initialized. Call begin_page() first.")
        
        # Apply coordinate transformation
        pdf_x, pdf_y = self._transform_coordinates(x, y)
        pdf_width = width * inch * self.scale
        pdf_height = height * inch * self.scale
        
        # Apply style
        self._apply_line_style(style)
        
        # Draw rectangle
        self.canvas.rect(pdf_x, pdf_y, pdf_width, pdf_height, stroke=1, fill=0)
        
    def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                  style: RenderStyle = RenderStyle.THIN_LINE) -> None:
        """Draw a line between two points with specified style."""
        if not self.canvas:
            raise RuntimeError("Canvas not initialized. Call begin_page() first.")
        
        # Apply coordinate transformation
        pdf_x1, pdf_y1 = self._transform_coordinates(x1, y1)
        pdf_x2, pdf_y2 = self._transform_coordinates(x2, y2)
        
        # Apply style
        self._apply_line_style(style)
        
        # Draw line
        self.canvas.line(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
        
    def draw_text(self, x: float, y: float, text: str, 
                  style: RenderStyle = RenderStyle.TEXT_MEDIUM,
                  rotation: float = 0.0) -> None:
        """Draw text at specified location with style and rotation."""
        if not self.canvas:
            raise RuntimeError("Canvas not initialized. Call begin_page() first.")
        
        # Apply coordinate transformation
        pdf_x, pdf_y = self._transform_coordinates(x, y)
        
        # Apply text style
        self._apply_text_style(style)
        
        # Handle rotation
        if rotation != 0.0:
            self.canvas.saveState()
            self.canvas.translate(pdf_x, pdf_y)
            self.canvas.rotate(rotation)
            self.canvas.drawString(0, 0, text)
            self.canvas.restoreState()
        else:
            self.canvas.drawString(pdf_x, pdf_y, text)
    
    def draw_dimension(self, x1: float, x2: float, y_base: float, 
                      dimension_text: str,
                      style: RenderStyle = RenderStyle.DIMENSION_LINE) -> None:
        """Draw a dimension line with text between two X coordinates."""
        if not self.canvas:
            raise RuntimeError("Canvas not initialized. Call begin_page() first.")
        
        # Calculate dimension line positioning
        offset = 6.0  # 6 inches above the base line
        arrow_size = 1.0  # 1 inch arrow size
        
        # Draw extension lines
        self.draw_line(x1, y_base, x1, y_base + offset, style)
        self.draw_line(x2, y_base, x2, y_base + offset, style)
        
        # Draw dimension line
        dim_y = y_base + offset
        self.draw_line(x1, dim_y, x2, dim_y, style)
        
        # Draw arrows
        self._draw_dimension_arrow(x1, dim_y, arrow_size, True)
        self._draw_dimension_arrow(x2, dim_y, arrow_size, False)
        
        # Draw dimension text at center
        center_x = (x1 + x2) / 2
        text_y = dim_y + 1.0  # 1 inch above dimension line
        self.draw_text(center_x, text_y, dimension_text, RenderStyle.TEXT_SMALL)
    
    def draw_polyline(self, points: List[Point], 
                     style: RenderStyle = RenderStyle.THIN_LINE,
                     closed: bool = False) -> None:
        """Draw a polyline through the specified points."""
        if not self.canvas:
            raise RuntimeError("Canvas not initialized. Call begin_page() first.")
        
        if len(points) < 2:
            return
        
        # Apply style
        self._apply_line_style(style)
        
        # Create path
        path = self.canvas.beginPath()
        
        # Start at first point
        first_point = self._transform_coordinates(points[0].x, points[0].y)
        path.moveTo(*first_point)
        
        # Add lines to subsequent points
        for point in points[1:]:
            pdf_point = self._transform_coordinates(point.x, point.y)
            path.lineTo(*pdf_point)
        
        # Close path if requested
        if closed:
            path.close()
        
        # Draw path
        self.canvas.drawPath(path, stroke=1, fill=0)
    
    def end_page(self) -> None:
        """Finalize the current page."""
        if self.canvas:
            self.canvas.showPage()
    
    def save(self, output_path: str) -> None:
        """Save the drawing to the specified file path."""
        if not self.canvas:
            raise RuntimeError("Canvas not initialized. Call begin_page() first.")
        
        self.canvas.save()
        
    # Private helper methods
    
    def _setup_pdf_metadata(self) -> None:
        """Set up PDF document metadata."""
        if not self.canvas or not self.current_metadata:
            return
        
        self.canvas.setTitle(f"Millwork Shop Drawing - {self.current_metadata.room_id}")
        self.canvas.setAuthor("Millwork Drafter")
        self.canvas.setSubject(f"Shop drawing for {self.current_metadata.room_id}")
        self.canvas.setCreator(f"Millwork Drafter v{self.current_metadata.app_version}")
        
        # Add custom metadata
        info = self.canvas._doc.info
        info.config_sha256 = self.current_metadata.config_sha256
        info.csv_sha256 = self.current_metadata.csv_sha256
        info.spec_version = self.current_metadata.spec_version
        
    def _draw_title_block(self) -> None:
        """Draw the title block with project information."""
        if not self.canvas or not self.current_metadata:
            return
        
        # Title block dimensions (bottom-right corner)
        title_width = 4.0 * inch
        title_height = 2.0 * inch
        title_x = self.page_width - self.margins[2] * inch - title_width
        title_y = self.margins[1] * inch
        
        # Draw title block border
        self.canvas.setLineWidth(0.5)
        self.canvas.rect(title_x, title_y, title_width, title_height, stroke=1, fill=0)
        
        # Add title block text
        self.canvas.setFont("Helvetica-Bold", 12)
        self.canvas.drawString(title_x + 6, title_y + title_height - 20, 
                              f"MILLWORK SHOP DRAWING")
        
        self.canvas.setFont("Helvetica", 10)
        self.canvas.drawString(title_x + 6, title_y + title_height - 40, 
                              f"Room: {self.current_metadata.room_id}")
        self.canvas.drawString(title_x + 6, title_y + title_height - 55, 
                              f"Date: {self.current_metadata.timestamp[:10]}")
        self.canvas.drawString(title_x + 6, title_y + title_height - 70, 
                              f"Scale: {self.scale}\" = 1'")
        
        if self.current_metadata.drawing_id:
            self.canvas.drawString(title_x + 6, title_y + title_height - 85,
                                  f"Drawing: {self.current_metadata.drawing_id}")
        
    def _draw_page_border(self) -> None:
        """Draw page border around drawing area."""
        if not self.canvas:
            return
        
        # Calculate border coordinates
        border_x = self.margins[0] * inch
        border_y = self.margins[1] * inch
        border_width = self.page_width - (self.margins[0] + self.margins[2]) * inch
        border_height = self.page_height - (self.margins[1] + self.margins[3]) * inch
        
        # Draw border
        self.canvas.setLineWidth(1.0)
        self.canvas.setStrokeColor(colors.black)
        self.canvas.rect(border_x, border_y, border_width, border_height, 
                        stroke=1, fill=0)
        
    def _transform_coordinates(self, x: float, y: float) -> Tuple[float, float]:
        """Transform drawing coordinates to PDF coordinates."""
        pdf_x = self.drawing_origin_x + (x * inch * self.scale)
        pdf_y = self.drawing_origin_y + (y * inch * self.scale)
        return pdf_x, pdf_y
        
    def _apply_line_style(self, style: RenderStyle) -> None:
        """Apply line style to canvas."""
        if not self.canvas:
            return
        
        style_def = self.STYLE_DEFINITIONS.get(style, self.STYLE_DEFINITIONS[RenderStyle.THIN_LINE])
        
        self.canvas.setLineWidth(style_def["line_width"])
        self.canvas.setStrokeColor(style_def["color"])
        
        # Apply dash pattern if specified
        if style_def.get("dash_pattern"):
            self.canvas.setDash(style_def["dash_pattern"])
        else:
            self.canvas.setDash([])  # Solid line
            
    def _apply_text_style(self, style: RenderStyle) -> None:
        """Apply text style to canvas."""
        if not self.canvas:
            return
        
        style_def = self.STYLE_DEFINITIONS.get(style, self.STYLE_DEFINITIONS[RenderStyle.TEXT_MEDIUM])
        
        self.canvas.setFont(style_def["font_name"], style_def["font_size"])
        self.canvas.setFillColor(style_def["color"])
        
    def _draw_dimension_arrow(self, x: float, y: float, size: float, pointing_right: bool) -> None:
        """Draw a dimension arrow."""
        if not self.canvas:
            return
        
        pdf_x, pdf_y = self._transform_coordinates(x, y)
        arrow_size = size * self.scale * inch
        
        # Create arrow path
        path = self.canvas.beginPath()
        path.moveTo(pdf_x, pdf_y)
        
        if pointing_right:
            path.lineTo(pdf_x - arrow_size, pdf_y + arrow_size/3)
            path.lineTo(pdf_x - arrow_size, pdf_y - arrow_size/3)
        else:
            path.lineTo(pdf_x + arrow_size, pdf_y + arrow_size/3)
            path.lineTo(pdf_x + arrow_size, pdf_y - arrow_size/3)
        
        path.close()
        
        # Draw filled arrow
        self.canvas.drawPath(path, stroke=1, fill=1)