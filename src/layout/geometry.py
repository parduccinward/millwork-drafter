"""
Geometry utilities for layout calculations and coordinate transforms.

Provides utility functions for geometric calculations, coordinate system
management, and tolerance handling for the millwork layout engine.
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from ..core.interfaces import Rectangle, Point


class GeometryUtils:
    """Utility functions for geometric calculations and coordinate transforms."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration parameters."""
        self.config = config
        
    def inches_to_points(self, inches: float) -> float:
        """
        Convert inches to PostScript points (1 in = 72 pt).
        
        Args:
            inches: Measurement in inches
            
        Returns:
            Measurement in PostScript points
        """
        return inches * 72.0
    
    def points_to_inches(self, points: float) -> float:
        """
        Convert PostScript points to inches (72 pt = 1 in).
        
        Args:
            points: Measurement in PostScript points
            
        Returns:
            Measurement in inches
        """
        return points / 72.0
    
    def apply_scale(self, value: float, scale: Optional[float] = None) -> float:
        """
        Apply drawing scale to a measurement.
        
        Args:
            value: Original measurement
            scale: Drawing scale ratio (defaults to config SCALE_PLAN)
            
        Returns:
            Scaled measurement
        """
        if scale is None:
            scale = self.config.get("SCALE_PLAN", 1.0)
        return value * scale
    
    def round_to_tolerance(self, value: float, tolerance: Optional[float] = None) -> float:
        """
        Round value according to tolerance specification.
        
        Args:
            value: Value to round
            tolerance: Tolerance setting (defaults to config LENGTH_ROUNDING)
            
        Returns:
            Rounded value
        """
        if tolerance is None:
            tolerance = self.config.get("TOLERANCES", {}).get("LENGTH_ROUNDING", 2)
        
        # Round to specified number of decimal places
        return round(value, int(tolerance))
    
    def calculate_bounding_box(self, rectangles: List[Rectangle]) -> Rectangle:
        """
        Calculate bounding box for a list of rectangles.
        
        Args:
            rectangles: List of Rectangle objects
            
        Returns:
            Rectangle representing the bounding box
        """
        if not rectangles:
            return Rectangle(0, 0, 0, 0)
        
        min_x = min(rect.x for rect in rectangles)
        min_y = min(rect.y for rect in rectangles)
        max_x = max(rect.x + rect.width for rect in rectangles)
        max_y = max(rect.y + rect.height for rect in rectangles)
        
        return Rectangle(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y
        )
    
    def validate_length_sum(self, module_widths: List[float], 
                           left_filler: float, 
                           right_filler: float,
                           total_length: float, 
                           tolerance: Optional[float] = None) -> Tuple[bool, float]:
        """
        Validate that sum of components matches total within tolerance.
        
        Args:
            module_widths: List of module widths
            left_filler: Left filler width
            right_filler: Right filler width
            total_length: Expected total length
            tolerance: Tolerance for comparison (defaults to config LENGTH_SUM)
            
        Returns:
            Tuple of (is_valid, actual_difference)
        """
        if tolerance is None:
            tolerance = self.config.get("TOLERANCES", {}).get("LENGTH_SUM", 0.125)
        
        computed_sum = sum(module_widths) + left_filler + right_filler
        difference = abs(computed_sum - total_length)
        
        is_valid = difference <= tolerance
        return is_valid, difference
    
    def center_point(self, rect: Rectangle) -> Point:
        """
        Calculate center point of a rectangle.
        
        Args:
            rect: Rectangle object
            
        Returns:
            Point at the center of the rectangle
        """
        return Point(
            x=rect.x + rect.width / 2.0,
            y=rect.y + rect.height / 2.0
        )
    
    def offset_rectangle(self, rect: Rectangle, offset_x: float, offset_y: float) -> Rectangle:
        """
        Create a new rectangle offset by the specified amounts.
        
        Args:
            rect: Original rectangle
            offset_x: X offset
            offset_y: Y offset
            
        Returns:
            New rectangle with offset position
        """
        return Rectangle(
            x=rect.x + offset_x,
            y=rect.y + offset_y,
            width=rect.width,
            height=rect.height
        )
    
    def scale_rectangle(self, rect: Rectangle, scale_x: float, scale_y: Optional[float] = None) -> Rectangle:
        """
        Create a new rectangle scaled by the specified factors.
        
        Args:
            rect: Original rectangle
            scale_x: X scale factor
            scale_y: Y scale factor (defaults to scale_x for uniform scaling)
            
        Returns:
            New rectangle with scaled dimensions
        """
        if scale_y is None:
            scale_y = scale_x
            
        return Rectangle(
            x=rect.x,
            y=rect.y,
            width=rect.width * scale_x,
            height=rect.height * scale_y
        )
    
    def get_ada_clearance_dimensions(self) -> Dict[str, Any]:
        """
        Extract ADA clearance dimensions from configuration.
        
        Returns:
            Dictionary with parsed ADA clearance dimensions
        """
        ada_config = self.config.get("ADA", {})
        
        # Parse knee clearance (e.g., "27\" H x 30\" W x 17\" D")
        knee_clear = ada_config.get("KNEE_CLEAR", "27\" H x 30\" W x 17\" D")
        knee_dims = self._parse_clearance_string(knee_clear)
        
        # Parse toe clearance (e.g., "9\" H x 6\" D")
        toe_clear = ada_config.get("TOE_CLEAR", "9\" H x 6\" D")
        toe_dims = self._parse_clearance_string(toe_clear)
        
        return {
            "knee": knee_dims,
            "toe": toe_dims,
            "counter_range": ada_config.get("COUNTER_RANGE", [28, 34]),
            "clear_widths": ada_config.get("CLEAR_WIDTHS", 32),
            "code_basis": self.config.get("CODE", {}).get("BASIS", "ADA 2010")
        }
    
    def _parse_clearance_string(self, clearance_str: str) -> Dict[str, float]:
        """
        Parse clearance string like "27\" H x 30\" W x 17\" D" into dimensions.
        
        Args:
            clearance_str: Clearance specification string
            
        Returns:
            Dictionary with height, width, depth dimensions
        """
        dimensions = {"height": 0, "width": 0, "depth": 0}
        
        # Extract numbers followed by dimension indicators
        import re
        
        # Match patterns like "27\" H", "30\" W", "17\" D"
        height_match = re.search(r'(\d+(?:\.\d+)?)"?\s*H', clearance_str, re.IGNORECASE)
        width_match = re.search(r'(\d+(?:\.\d+)?)"?\s*W', clearance_str, re.IGNORECASE)
        depth_match = re.search(r'(\d+(?:\.\d+)?)"?\s*D', clearance_str, re.IGNORECASE)
        
        if height_match:
            dimensions["height"] = float(height_match.group(1))
        if width_match:
            dimensions["width"] = float(width_match.group(1))
        if depth_match:
            dimensions["depth"] = float(depth_match.group(1))
            
        return dimensions
    
    def create_ada_boxes(self, countertop_rect: Rectangle, counter_height: float) -> Tuple[Rectangle, Rectangle]:
        """
        Create ADA clearance boxes based on countertop position and configuration.
        
        Args:
            countertop_rect: Rectangle representing countertop surface
            counter_height: Counter height in inches
            
        Returns:
            Tuple of (knee_clearance_box, toe_clearance_box)
        """
        ada_dims = self.get_ada_clearance_dimensions()
        
        # Knee clearance box (positioned below counter)
        knee_box = Rectangle(
            x=countertop_rect.x,
            y=countertop_rect.y - ada_dims["knee"]["height"],
            width=ada_dims["knee"]["width"],
            height=ada_dims["knee"]["height"]
        )
        
        # Toe clearance box (positioned below knee box)
        toe_box = Rectangle(
            x=countertop_rect.x,
            y=knee_box.y - ada_dims["toe"]["height"],
            width=countertop_rect.width,  # Toe clearance spans full width
            height=ada_dims["toe"]["height"]
        )
        
        return knee_box, toe_box