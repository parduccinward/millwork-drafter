"""
Parametric layout engine implementation for millwork shop drawings.

Implements the ILayoutEngine interface to transform validated room data
into precise geometric layouts ready for rendering.
"""

import time
from typing import Dict, Any, List, Optional
from ..core.interfaces import (
    ILayoutEngine, LayoutResult, ModuleLayout, FillerLayout, 
    CountertopLayout, ADALayout, LayoutMetadata, ValidationResult,
    Rectangle
)
from ..parser.schema import ParsedRoomData
from .geometry import GeometryUtils


class ParametricLayoutEngine(ILayoutEngine):
    """
    Parametric layout engine implementing millwork shop drawing layouts.
    
    Transforms validated ParsedRoomData into geometric layouts using
    configuration parameters for dimensions, tolerances, and standards.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the layout engine with configuration.
        
        Args:
            config: Configuration dictionary with layout parameters
        """
        self.config = config
        self.geometry_utils = GeometryUtils(config)
        
    def compute_layout(self, room_data: ParsedRoomData, 
                      config: Dict[str, Any]) -> LayoutResult:
        """
        Compute complete geometric layout for a room specification.
        
        Args:
            room_data: Validated room data from CSV parser
            config: Configuration dictionary with parameters
            
        Returns:
            LayoutResult with complete geometric layout
        """
        start_time = time.time()
        
        # Use the provided config for this computation
        self.config = config
        self.geometry_utils = GeometryUtils(config)
        
        # Create validation result for tracking layout validation
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            # 1. Compute module positions
            modules = self._compute_module_positions(room_data)
            
            # 2. Compute filler positions if present
            fillers = self._compute_filler_positions(modules, room_data)
            
            # 3. Generate countertop geometry
            countertop = self._generate_countertop(modules, fillers, room_data)
            
            # 4. Generate ADA layout if required
            ada_layout = self._generate_ada_layout(countertop, room_data)
            
            # 5. Calculate total dimensions and bounding box
            total_width, total_depth, bounding_box = self._calculate_bounds(modules, fillers, countertop)
            
            # 6. Validate geometric consistency
            layout_validation = self._validate_layout_geometry(
                modules, fillers, room_data, total_width
            )
            validation_result.merge(layout_validation)
            
            # 7. Create metadata
            computation_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            metadata = LayoutMetadata(
                room_id=room_data.room_id,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                config_sha256=self._get_config_hash(config),
                layout_version="1.0",
                computation_time_ms=computation_time,
                tolerance_used=config.get("TOLERANCES", {}).get("LENGTH_SUM", 0.125)
            )
            
            return LayoutResult(
                room_id=room_data.room_id,
                modules=modules,
                fillers=fillers,
                countertop=countertop,
                ada_layout=ada_layout,
                total_width=total_width,
                total_depth=total_depth,
                bounding_box=bounding_box,
                metadata=metadata,
                validation_result=validation_result
            )
            
        except Exception as e:
            validation_result.add_error(
                field="layout_computation",
                message=f"Layout computation failed: {str(e)}",
                value=room_data.room_id
            )
            
            # Return minimal layout result with error
            return LayoutResult(
                room_id=room_data.room_id,
                modules=[],
                fillers=[],
                countertop=CountertopLayout(0, 0, 0, 0, 0, ""),
                ada_layout=None,
                total_width=0,
                total_depth=0,
                bounding_box=Rectangle(0, 0, 0, 0),
                metadata=LayoutMetadata(
                    room_id=room_data.room_id,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    config_sha256=self._get_config_hash(config),
                    layout_version="1.0"
                ),
                validation_result=validation_result
            )
    
    def validate_geometry(self, layout: LayoutResult, 
                         tolerances: Dict[str, float]) -> ValidationResult:
        """
        Validate computed geometry against tolerances and constraints.
        
        Args:
            layout: Computed layout result
            tolerances: Tolerance specifications from config
            
        Returns:
            ValidationResult with geometric validation status
        """
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate module positioning
        for i, module in enumerate(layout.modules):
            if module.width <= 0:
                validation_result.add_error(
                    field=f"module_{i}_width",
                    message=f"Module {i} has invalid width: {module.width}",
                    value=module.width
                )
                
        # Validate total width consistency
        computed_width = sum(m.width for m in layout.modules) + sum(f.width for f in layout.fillers)
        tolerance = tolerances.get("LENGTH_SUM", 0.125)
        
        if abs(computed_width - layout.total_width) > tolerance:
            validation_result.add_error(
                field="total_width_consistency",
                message=f"Computed width {computed_width} doesn't match layout total {layout.total_width}",
                value=abs(computed_width - layout.total_width)
            )
        
        return validation_result
    
    def _compute_module_positions(self, room_data: ParsedRoomData) -> List[ModuleLayout]:
        """
        Compute geometric positions for cabinet modules.
        
        Args:
            room_data: Parsed room data with module specifications
            
        Returns:
            List of ModuleLayout objects with computed positions
        """
        modules = []
        current_x = room_data.left_filler_in  # Start after left filler
        
        # Get dimensions from configuration
        module_height = self.config.get("COUNTER_HEIGHT", 36.0)
        module_depth = self.config.get("BASE_DEPTH", 24.0)
        
        for i, width in enumerate(room_data.module_widths):
            module = ModuleLayout(
                index=i,
                x=current_x,
                y=0.0,  # Base level
                width=width,
                height=module_height,
                depth=module_depth,
                material_code=room_data.material_casework
            )
            modules.append(module)
            current_x += width
            
        return modules
    
    def _compute_filler_positions(self, modules: List[ModuleLayout], 
                                 room_data: ParsedRoomData) -> List[FillerLayout]:
        """
        Compute filler strip positions.
        
        Args:
            modules: List of positioned modules
            room_data: Parsed room data with filler specifications
            
        Returns:
            List of FillerLayout objects
        """
        fillers = []
        
        # Get dimensions from configuration
        filler_height = self.config.get("COUNTER_HEIGHT", 36.0)
        filler_depth = self.config.get("BASE_DEPTH", 24.0)
        
        # Left filler
        if room_data.left_filler_in > 0:
            left_filler = FillerLayout(
                side="left",
                x=0.0,
                y=0.0,
                width=room_data.left_filler_in,
                height=filler_height,
                depth=filler_depth
            )
            fillers.append(left_filler)
        
        # Right filler
        if room_data.right_filler_in > 0 and modules:
            # Position after the last module
            last_module = modules[-1]
            right_filler = FillerLayout(
                side="right",
                x=last_module.x + last_module.width,
                y=0.0,
                width=room_data.right_filler_in,
                height=filler_height,
                depth=filler_depth
            )
            fillers.append(right_filler)
            
        return fillers
    
    def _generate_countertop(self, modules: List[ModuleLayout], 
                           fillers: List[FillerLayout],
                           room_data: ParsedRoomData) -> CountertopLayout:
        """
        Generate countertop geometry spanning modules and fillers.
        
        Args:
            modules: List of positioned modules
            fillers: List of positioned fillers
            room_data: Parsed room data with material specifications
            
        Returns:
            CountertopLayout object
        """
        if not modules:
            return CountertopLayout(0, 0, 0, 0, 0, room_data.material_top)
        
        # Calculate countertop bounds
        all_elements = modules + fillers
        if not all_elements:
            return CountertopLayout(0, 0, 0, 0, 0, room_data.material_top)
        
        min_x = min(elem.x for elem in all_elements)
        max_x = max(elem.x + elem.width for elem in all_elements)
        
        # Get countertop dimensions from configuration
        counter_height = room_data.counter_height_in or self.config.get("COUNTER_HEIGHT", 36.0)
        counter_depth = self.config.get("BASE_DEPTH", 24.0)
        
        # Countertop sits on top of modules
        countertop_y = counter_height
        
        return CountertopLayout(
            x=min_x,
            y=countertop_y,
            width=max_x - min_x,
            depth=counter_depth,
            height=1.5,  # Standard countertop thickness
            material_code=room_data.material_top
        )
    
    def _generate_ada_layout(self, countertop: CountertopLayout, 
                           room_data: ParsedRoomData) -> Optional[ADALayout]:
        """
        Generate ADA compliance clearance boxes based on configuration.
        
        Args:
            countertop: Countertop layout for reference
            room_data: Parsed room data
            
        Returns:
            ADALayout object if ADA compliance is configured, None otherwise
        """
        ada_config = self.config.get("ADA")
        if not ada_config:
            return None
        
        # Check if ADA config has required keys
        required_keys = ["KNEE_CLEAR", "TOE_CLEAR", "CLEAR_WIDTHS"]
        if not all(key in ada_config for key in required_keys):
            return None
        
        # Get ADA clearance dimensions
        ada_dims = self.geometry_utils.get_ada_clearance_dimensions()
        
        # Create clearance boxes
        countertop_rect = Rectangle(
            x=countertop.x,
            y=countertop.y,
            width=countertop.width,
            height=countertop.depth
        )
        
        knee_box, toe_box = self.geometry_utils.create_ada_boxes(
            countertop_rect, countertop.y
        )
        
        return ADALayout(
            knee_clear_box=knee_box,
            toe_clear_box=toe_box,
            approach_width=ada_dims["clear_widths"],
            counter_height=countertop.y,
            code_basis=ada_dims["code_basis"]
        )
    
    def _calculate_bounds(self, modules: List[ModuleLayout], 
                         fillers: List[FillerLayout],
                         countertop: CountertopLayout) -> tuple[float, float, Rectangle]:
        """
        Calculate total dimensions and bounding box for the layout.
        
        Args:
            modules: List of module layouts
            fillers: List of filler layouts
            countertop: Countertop layout
            
        Returns:
            Tuple of (total_width, total_depth, bounding_box)
        """
        # Create rectangles for all elements
        rectangles = []
        
        # Add modules
        for module in modules:
            rectangles.append(Rectangle(module.x, module.y, module.width, module.height))
        
        # Add fillers
        for filler in fillers:
            rectangles.append(Rectangle(filler.x, filler.y, filler.width, filler.height))
        
        # Add countertop
        rectangles.append(Rectangle(countertop.x, countertop.y, countertop.width, countertop.depth))
        
        if not rectangles:
            return 0.0, 0.0, Rectangle(0, 0, 0, 0)
        
        # Calculate bounding box
        bounding_box = self.geometry_utils.calculate_bounding_box(rectangles)
        
        return bounding_box.width, bounding_box.height, bounding_box
    
    def _validate_layout_geometry(self, modules: List[ModuleLayout], 
                                 fillers: List[FillerLayout],
                                 room_data: ParsedRoomData,
                                 computed_width: float) -> ValidationResult:
        """
        Validate the computed layout geometry against input specifications.
        
        Args:
            modules: List of module layouts
            fillers: List of filler layouts
            room_data: Original room data for comparison
            computed_width: Computed total width
            
        Returns:
            ValidationResult with validation status
        """
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate length sum against tolerance
        module_widths = [m.width for m in modules]
        filler_widths = room_data.left_filler_in + room_data.right_filler_in
        
        is_valid, difference = self.geometry_utils.validate_length_sum(
            module_widths, room_data.left_filler_in, room_data.right_filler_in,
            room_data.total_length_in
        )
        
        if not is_valid:
            validation_result.add_error(
                field="total_length_validation",
                message=f"Length sum validation failed. Difference: {difference:.3f} inches",
                value=difference,
                row_id=room_data.room_id
            )
        
        # Validate module count
        if len(modules) != room_data.num_modules:
            validation_result.add_error(
                field="module_count",
                message=f"Module count mismatch: expected {room_data.num_modules}, got {len(modules)}",
                value=len(modules),
                row_id=room_data.room_id
            )
        
        # Validate individual module widths
        for i, (computed_width, expected_width) in enumerate(zip(module_widths, room_data.module_widths)):
            if abs(computed_width - expected_width) > 0.001:  # Small tolerance for floating point
                validation_result.add_error(
                    field=f"module_{i}_width",
                    message=f"Module {i} width mismatch: expected {expected_width}, got {computed_width}",
                    value=computed_width,
                    row_id=room_data.room_id
                )
        
        return validation_result
    
    def _get_config_hash(self, config: Dict[str, Any]) -> str:
        """
        Generate SHA256 hash of configuration for reproducibility.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            SHA256 hash string
        """
        import hashlib
        import json
        
        # Create a sorted JSON representation for consistent hashing
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]  # First 16 chars