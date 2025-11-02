"""
Configuration management for Millwork Drafter.

Implements the parametric [CFG.*] system from the memory banks,
providing YAML loading, validation, and hash generation for reproducibility.
"""

import hashlib
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from .interfaces import IConfigLoader, ValidationResult, ValidationError


@dataclass
class ToleranceConfig:
    """Tolerance configuration settings."""
    length_sum: float = 0.125  # inches
    length_rounding: int = 2   # decimal places


@dataclass
class ADAConfig:
    """ADA compliance configuration."""
    knee_clear: str = "27\" H x 30\" W x 17\" D"
    toe_clear: str = "9\" H x 6\" D"
    counter_range: List[float] = field(default_factory=lambda: [28.0, 34.0])
    clear_widths: float = 32.0  # inches


@dataclass
class PDFConfig:
    """PDF output configuration."""
    size: str = "letter"  # letter, tabloid, ANSI-A, ANSI-B, etc.
    margins: List[float] = field(default_factory=lambda: [0.5, 0.5, 0.5, 0.5])  # top, right, bottom, left


@dataclass
class HardwareDefaults:
    """Default hardware specifications."""
    hinge: str = "BLUM-110"
    pull: str = "SS-128"
    slide: str = "BLUM-563"


@dataclass
class HardwareConfig:
    """Hardware configuration."""
    defaults: HardwareDefaults = field(default_factory=HardwareDefaults)


@dataclass
class CodeConfig:
    """Code compliance configuration."""
    basis: str = "ADA 2010"


@dataclass
class MillworkConfig:
    """
    Complete millwork configuration matching the memory bank specifications.
    
    This class implements the parametric [CFG.*] system, providing
    type-safe access to all configuration parameters.
    """
    
    # Drawing and scale settings
    scale_plan: float = 0.25  # 1/4" = 1' scale
    
    # Standard dimensions (inches)
    counter_height: float = 36.0
    base_depth: float = 24.0
    wall_cab_depth: float = 12.0
    
    # Edge and finish settings
    edge_rule: str = "MATCH_FACE"
    
    # Nested configuration objects
    ada: ADAConfig = field(default_factory=ADAConfig)
    tolerances: ToleranceConfig = field(default_factory=ToleranceConfig)
    pdf: PDFConfig = field(default_factory=PDFConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    code: CodeConfig = field(default_factory=CodeConfig)
    
    # Schedule and deliverable settings
    schedule_format: str = "on-sheet"  # "on-sheet" or "csv"
    cad_deliverables: bool = False
    
    # Validation lists
    edge_rules: List[str] = field(default_factory=lambda: [
        "MATCH_FACE", "PVC_EDGE", "SOLID_LUMBER", "RADIUS"
    ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "SCALE_PLAN": self.scale_plan,
            "COUNTER_HEIGHT": self.counter_height,
            "BASE_DEPTH": self.base_depth,
            "WALL_CAB_DEPTH": self.wall_cab_depth,
            "EDGE_RULE": self.edge_rule,
            "ADA": {
                "KNEE_CLEAR": self.ada.knee_clear,
                "TOE_CLEAR": self.ada.toe_clear,
                "COUNTER_RANGE": self.ada.counter_range,
                "CLEAR_WIDTHS": self.ada.clear_widths,
            },
            "TOLERANCES": {
                "LENGTH_SUM": self.tolerances.length_sum,
                "LENGTH_ROUNDING": self.tolerances.length_rounding,
            },
            "PDF": {
                "SIZE": self.pdf.size,
                "MARGINS": self.pdf.margins,
            },
            "HW": {
                "DEFAULTS": {
                    "HINGE": self.hardware.defaults.hinge,
                    "PULL": self.hardware.defaults.pull,
                    "SLIDE": self.hardware.defaults.slide,
                }
            },
            "CODE": {
                "BASIS": self.code.basis,
            },
            "SCHEDULE": {
                "FORMAT": self.schedule_format,
            },
            "CAD": {
                "DELIVERABLES": self.cad_deliverables,
            },
            "EDGE_RULES": self.edge_rules,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MillworkConfig":
        """Create configuration from dictionary."""
        config = cls()
        
        # Update basic fields
        config.scale_plan = data.get("SCALE_PLAN", config.scale_plan)
        config.counter_height = data.get("COUNTER_HEIGHT", config.counter_height)
        config.base_depth = data.get("BASE_DEPTH", config.base_depth)
        config.wall_cab_depth = data.get("WALL_CAB_DEPTH", config.wall_cab_depth)
        config.edge_rule = data.get("EDGE_RULE", config.edge_rule)
        
        # Update nested configurations
        if "ADA" in data:
            ada_data = data["ADA"]
            config.ada.knee_clear = ada_data.get("KNEE_CLEAR", config.ada.knee_clear)
            config.ada.toe_clear = ada_data.get("TOE_CLEAR", config.ada.toe_clear)
            config.ada.counter_range = ada_data.get("COUNTER_RANGE", config.ada.counter_range)
            config.ada.clear_widths = ada_data.get("CLEAR_WIDTHS", config.ada.clear_widths)
        
        if "TOLERANCES" in data:
            tol_data = data["TOLERANCES"]
            config.tolerances.length_sum = tol_data.get("LENGTH_SUM", config.tolerances.length_sum)
            config.tolerances.length_rounding = tol_data.get("LENGTH_ROUNDING", config.tolerances.length_rounding)
        
        if "PDF" in data:
            pdf_data = data["PDF"]
            config.pdf.size = pdf_data.get("SIZE", config.pdf.size)
            config.pdf.margins = pdf_data.get("MARGINS", config.pdf.margins)
        
        if "HW" in data and "DEFAULTS" in data["HW"]:
            hw_data = data["HW"]["DEFAULTS"]
            config.hardware.defaults.hinge = hw_data.get("HINGE", config.hardware.defaults.hinge)
            config.hardware.defaults.pull = hw_data.get("PULL", config.hardware.defaults.pull)
            config.hardware.defaults.slide = hw_data.get("SLIDE", config.hardware.defaults.slide)
        
        if "CODE" in data:
            config.code.basis = data["CODE"].get("BASIS", config.code.basis)
        
        if "SCHEDULE" in data:
            config.schedule_format = data["SCHEDULE"].get("FORMAT", config.schedule_format)
        
        if "CAD" in data:
            config.cad_deliverables = data["CAD"].get("DELIVERABLES", config.cad_deliverables)
        
        if "EDGE_RULES" in data:
            config.edge_rules = data["EDGE_RULES"]
        
        return config


class ConfigLoader(IConfigLoader):
    """
    Concrete implementation of configuration loading.
    
    Handles YAML loading, validation, and hash generation
    as specified in the tech specs.
    """
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file with validation."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            if raw_config is None:
                raw_config = {}
            
            # Validate and merge with defaults
            validation_result = self.validate_config(raw_config)
            if not validation_result.is_valid:
                error_messages = [f"{err.field}: {err.message}" for err in validation_result.errors]
                raise ValueError(f"Configuration validation failed: {'; '.join(error_messages)}")
            
            # Create typed configuration object
            config = MillworkConfig.from_dict(raw_config)
            return config.to_dict()
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration structure and values."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate numeric ranges
        if "SCALE_PLAN" in config:
            scale = config["SCALE_PLAN"]
            if not isinstance(scale, (int, float)) or scale <= 0:
                result.add_error("SCALE_PLAN", "Must be a positive number", scale)
        
        if "COUNTER_HEIGHT" in config:
            height = config["COUNTER_HEIGHT"]
            if not isinstance(height, (int, float)) or height <= 0:
                result.add_error("COUNTER_HEIGHT", "Must be a positive number", height)
        
        if "BASE_DEPTH" in config:
            depth = config["BASE_DEPTH"]
            if not isinstance(depth, (int, float)) or depth <= 0:
                result.add_error("BASE_DEPTH", "Must be a positive number", depth)
        
        if "WALL_CAB_DEPTH" in config:
            depth = config["WALL_CAB_DEPTH"]
            if not isinstance(depth, (int, float)) or depth <= 0:
                result.add_error("WALL_CAB_DEPTH", "Must be a positive number", depth)
        
        # Validate ADA configuration
        if "ADA" in config:
            ada_config = config["ADA"]
            if "COUNTER_RANGE" in ada_config:
                counter_range = ada_config["COUNTER_RANGE"]
                if not isinstance(counter_range, list) or len(counter_range) != 2:
                    result.add_error("ADA.COUNTER_RANGE", "Must be a list of two numbers", counter_range)
                elif not all(isinstance(x, (int, float)) for x in counter_range):
                    result.add_error("ADA.COUNTER_RANGE", "Must contain only numbers", counter_range)
                elif counter_range[0] >= counter_range[1]:
                    result.add_error("ADA.COUNTER_RANGE", "First value must be less than second", counter_range)
        
        # Validate PDF configuration
        if "PDF" in config:
            pdf_config = config["PDF"]
            if "SIZE" in pdf_config:
                valid_sizes = ["letter", "tabloid", "ANSI-A", "ANSI-B", "ANSI-C", "ANSI-D"]
                if pdf_config["SIZE"] not in valid_sizes:
                    result.add_error("PDF.SIZE", f"Must be one of: {', '.join(valid_sizes)}", pdf_config["SIZE"])
            
            if "MARGINS" in pdf_config:
                margins = pdf_config["MARGINS"]
                if not isinstance(margins, list) or len(margins) != 4:
                    result.add_error("PDF.MARGINS", "Must be a list of four numbers", margins)
                elif not all(isinstance(x, (int, float)) and x >= 0 for x in margins):
                    result.add_error("PDF.MARGINS", "Must contain only non-negative numbers", margins)
        
        # Validate tolerances
        if "TOLERANCES" in config:
            tol_config = config["TOLERANCES"]
            if "LENGTH_SUM" in tol_config:
                length_sum = tol_config["LENGTH_SUM"]
                if not isinstance(length_sum, (int, float)) or length_sum <= 0:
                    result.add_error("TOLERANCES.LENGTH_SUM", "Must be a positive number", length_sum)
            
            if "LENGTH_ROUNDING" in tol_config:
                rounding = tol_config["LENGTH_ROUNDING"]
                if not isinstance(rounding, int) or rounding < 0:
                    result.add_error("TOLERANCES.LENGTH_ROUNDING", "Must be a non-negative integer", rounding)
        
        # Validate edge rules
        if "EDGE_RULES" in config:
            edge_rules = config["EDGE_RULES"]
            if not isinstance(edge_rules, list):
                result.add_error("EDGE_RULES", "Must be a list of strings", edge_rules)
            elif not all(isinstance(rule, str) for rule in edge_rules):
                result.add_error("EDGE_RULES", "Must contain only strings", edge_rules)
        
        return result
    
    def get_config_hash(self, config: Dict[str, Any]) -> str:
        """Generate SHA256 hash of configuration for reproducibility."""
        # Sort keys recursively for consistent hashing
        sorted_config = self._sort_dict_recursively(config)
        config_json = json.dumps(sorted_config, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(config_json.encode('utf-8')).hexdigest()
    
    def _sort_dict_recursively(self, obj: Any) -> Any:
        """Recursively sort dictionary keys for consistent hashing."""
        if isinstance(obj, dict):
            return {k: self._sort_dict_recursively(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [self._sort_dict_recursively(item) for item in obj]
        else:
            return obj


def load_default_config() -> MillworkConfig:
    """Load the default configuration."""
    return MillworkConfig()


def save_config_to_yaml(config: MillworkConfig, output_path: str) -> None:
    """Save configuration to YAML file."""
    config_dict = config.to_dict()
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False, indent=2)