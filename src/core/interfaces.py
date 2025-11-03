"""
Core interfaces for the Millwork Drafter system.

These interfaces define the contracts for rendering, validation, and layout
components, enabling the DXF-ready architecture through the adapter pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RenderStyle(Enum):
    """Standard rendering styles for shop drawings."""
    THIN_LINE = "thin"
    MEDIUM_LINE = "medium"
    THICK_LINE = "thick"
    HIDDEN_LINE = "hidden"
    CENTER_LINE = "center"
    DIMENSION_LINE = "dimension"
    TEXT_SMALL = "text_small"
    TEXT_MEDIUM = "text_medium"
    TEXT_LARGE = "text_large"
    HATCH_WOOD = "hatch_wood"
    HATCH_INSULATION = "hatch_insulation"


@dataclass
class Point:
    """2D point in drawing coordinates."""
    x: float
    y: float


@dataclass
class Rectangle:
    """Rectangle defined by origin point and dimensions."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class DrawingMetadata:
    """Metadata for drawing generation."""
    room_id: str
    app_version: str
    spec_version: str
    config_sha256: str
    csv_sha256: str
    timestamp: str
    drawing_id: Optional[str] = None
    submittal_number: Optional[str] = None


class IRenderer(ABC):
    """
    Abstract interface for rendering shop drawings.
    
    This interface enables the adapter pattern for future DXF support
    while providing immediate PDF rendering capability.
    """
    
    @abstractmethod
    def begin_page(self, metadata: DrawingMetadata, page_size: str = "letter") -> None:
        """Initialize a new drawing page with metadata."""
        pass
    
    @abstractmethod
    def draw_rect(self, x: float, y: float, width: float, height: float, 
                  style: RenderStyle = RenderStyle.THIN_LINE) -> None:
        """Draw a rectangle with specified coordinates and style."""
        pass
    
    @abstractmethod
    def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                  style: RenderStyle = RenderStyle.THIN_LINE) -> None:
        """Draw a line between two points with specified style."""
        pass
    
    @abstractmethod
    def draw_text(self, x: float, y: float, text: str, 
                  style: RenderStyle = RenderStyle.TEXT_MEDIUM,
                  rotation: float = 0.0) -> None:
        """Draw text at specified location with style and rotation."""
        pass
    
    @abstractmethod
    def draw_dimension(self, x1: float, x2: float, y_base: float, 
                      dimension_text: str,
                      style: RenderStyle = RenderStyle.DIMENSION_LINE) -> None:
        """Draw a dimension line with text between two X coordinates."""
        pass
    
    @abstractmethod
    def draw_polyline(self, points: List[Point], 
                     style: RenderStyle = RenderStyle.THIN_LINE,
                     closed: bool = False) -> None:
        """Draw a polyline through the specified points."""
        pass
    
    @abstractmethod
    def end_page(self) -> None:
        """Finalize the current page."""
        pass
    
    @abstractmethod
    def save(self, output_path: str) -> None:
        """Save the drawing to the specified file path."""
        pass


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    field: str
    message: str
    value: Any
    row_id: Optional[str] = None
    row_number: Optional[int] = None
    error_type: str = "validation"


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
    def add_error(self, field: str, message: str, value: Any, 
                  row_id: Optional[str] = None, row_number: Optional[int] = None) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, value, row_id, row_number, "error"))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, value: Any,
                   row_id: Optional[str] = None, row_number: Optional[int] = None) -> None:
        """Add a validation warning."""
        self.warnings.append(ValidationError(field, message, value, row_id, row_number, "warning"))
    
    def merge(self, other: 'ValidationResult') -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class IValidator(ABC):
    """
    Abstract interface for validation operations.
    
    Handles type checking, domain validation, geometric consistency,
    and referential integrity as defined in the tech specs.
    """
    
    @abstractmethod
    def validate_type_and_domain(self, data: Dict[str, Any], 
                                config: Dict[str, Any]) -> ValidationResult:
        """Validate data types and domain constraints."""
        pass
    
    @abstractmethod
    def validate_geometric_consistency(self, data: Dict[str, Any],
                                     config: Dict[str, Any]) -> ValidationResult:
        """Validate geometric relationships and tolerances."""
        pass
    
    @abstractmethod
    def validate_referential_integrity(self, data: Dict[str, Any],
                                      config: Dict[str, Any]) -> ValidationResult:
        """Validate references to configuration keys and enums."""
        pass


@dataclass
class LayoutElement:
    """Base class for layout elements."""
    element_type: str
    bounds: Rectangle
    style: RenderStyle
    metadata: Dict[str, Any]


@dataclass
class ModuleElement(LayoutElement):
    """Represents a cabinet module in the layout."""
    width: float
    depth: float
    material_code: str
    
    def __init__(self, bounds: Rectangle, style: RenderStyle, metadata: Dict[str, Any],
                 width: float, depth: float, material_code: str):
        super().__init__("module", bounds, style, metadata)
        self.width = width
        self.depth = depth
        self.material_code = material_code


@dataclass
class FillerElement(LayoutElement):
    """Represents a filler strip in the layout."""
    width: float
    position: str  # "left" or "right"
    
    def __init__(self, bounds: Rectangle, style: RenderStyle, metadata: Dict[str, Any],
                 width: float, position: str):
        super().__init__("filler", bounds, style, metadata)
        self.width = width
        self.position = position


@dataclass
class CountertopElement(LayoutElement):
    """Represents the countertop in the layout."""
    material_code: str
    thickness: float
    overhang: float
    
    def __init__(self, bounds: Rectangle, style: RenderStyle, metadata: Dict[str, Any],
                 material_code: str, thickness: float, overhang: float):
        super().__init__("countertop", bounds, style, metadata)
        self.material_code = material_code
        self.thickness = thickness
        self.overhang = overhang


@dataclass
class ADAElement(LayoutElement):
    """Represents ADA compliance visualization."""
    knee_clear: str
    toe_clear: str
    counter_range: str
    code_basis: str
    
    def __init__(self, bounds: Rectangle, style: RenderStyle, metadata: Dict[str, Any],
                 knee_clear: str, toe_clear: str, counter_range: str, code_basis: str):
        super().__init__("ada_box", bounds, style, metadata)
        self.knee_clear = knee_clear
        self.toe_clear = toe_clear
        self.counter_range = counter_range
        self.code_basis = code_basis


class ILayoutEngine(ABC):
    """
    Abstract interface for layout computation.
    
    Computes geometric layouts from CSV data and configuration,
    generating elements for rendering.
    """
    
    @abstractmethod
    def compute_layout(self, room_data: Dict[str, Any], 
                      config: Dict[str, Any]) -> List[LayoutElement]:
        """
        Compute layout elements from room data and configuration.
        
        Returns a list of layout elements ready for rendering.
        """
        pass
    
    @abstractmethod
    def validate_layout(self, elements: List[LayoutElement],
                       config: Dict[str, Any]) -> ValidationResult:
        """Validate computed layout for consistency and constraints."""
        pass


class IConfigLoader(ABC):
    """
    Abstract interface for configuration loading and validation.
    """
    
    @abstractmethod
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file with validation."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration structure and values."""
        pass
    
    @abstractmethod
    def get_config_hash(self, config: Dict[str, Any]) -> str:
        """Generate SHA256 hash of configuration for reproducibility."""
        pass