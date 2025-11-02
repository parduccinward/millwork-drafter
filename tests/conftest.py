"""
Test configuration module for Millwork Drafter tests.

Provides test fixtures, mock data, and common test utilities.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any

from src.core.config import MillworkConfig, ConfigLoader


@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Sample configuration dictionary for testing."""
    return {
        "SCALE_PLAN": 0.25,
        "COUNTER_HEIGHT": 36.0,
        "BASE_DEPTH": 24.0,
        "WALL_CAB_DEPTH": 12.0,
        "EDGE_RULE": "MATCH_FACE",
        "ADA": {
            "KNEE_CLEAR": "27\" H x 30\" W x 17\" D",
            "TOE_CLEAR": "9\" H x 6\" D",
            "COUNTER_RANGE": [28.0, 34.0],
            "CLEAR_WIDTHS": 32.0,
        },
        "TOLERANCES": {
            "LENGTH_SUM": 0.125,
            "LENGTH_ROUNDING": 2,
        },
        "PDF": {
            "SIZE": "letter",
            "MARGINS": [0.5, 0.5, 0.5, 0.5],
        },
        "HW": {
            "DEFAULTS": {
                "HINGE": "BLUM-110",
                "PULL": "SS-128",
                "SLIDE": "BLUM-563",
            }
        },
        "CODE": {
            "BASIS": "ADA 2010",
        },
        "SCHEDULE": {
            "FORMAT": "on-sheet",
        },
        "CAD": {
            "DELIVERABLES": False,
        },
        "EDGE_RULES": ["MATCH_FACE", "PVC_EDGE", "SOLID_LUMBER", "RADIUS"],
    }


@pytest.fixture
def sample_millwork_config() -> MillworkConfig:
    """Sample MillworkConfig object for testing."""
    return MillworkConfig()


@pytest.fixture
def temp_config_file(sample_config_dict) -> Path:
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config_dict, f)
        return Path(f.name)


@pytest.fixture
def config_loader() -> ConfigLoader:
    """ConfigLoader instance for testing."""
    return ConfigLoader()


@pytest.fixture
def sample_csv_data() -> str:
    """Sample CSV data for testing."""
    return """room_id,total_length_in,num_modules,module_widths,material_top,material_casework,left_filler_in,right_filler_in,has_sink,counter_height_in
KITCHEN-01,144.0,4,"[36,30,36,42]",QTZ-01,PLM-WHT,0.0,0.0,true,36.0
BATH-01,72.0,2,"[36,36]",LAM-01,PLM-WHT,0.0,0.0,false,34.0"""


@pytest.fixture
def temp_csv_file(sample_csv_data) -> Path:
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_data)
        return Path(f.name)


@pytest.fixture
def sample_room_data() -> Dict[str, Any]:
    """Sample room data dictionary for testing."""
    return {
        "room_id": "KITCHEN-01",
        "total_length_in": 144.0,
        "num_modules": 4,
        "module_widths": [36, 30, 36, 42],
        "material_top": "QTZ-01",
        "material_casework": "PLM-WHT",
        "left_filler_in": 0.0,
        "right_filler_in": 0.0,
        "has_sink": True,
        "counter_height_in": 36.0,
    }