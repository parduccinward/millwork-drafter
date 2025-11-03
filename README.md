# Millwork Drafter

A parametric, CSV-driven pipeline that generates vector PDFs for millwork shop drawings.

## Overview

Millwork Drafter implements a professional shop drawing generation system based on industry standards and ADA compliance requirements. The system follows the **Right-Sized Full Spec** approach with **Anti-Over-Engineering Guardrails** as defined in the project memory banks.

## Features

- ✅ **Parametric Configuration**: YAML-based `[CFG.*]` system for project customization
- ✅ **CSV-Driven Input**: Simple spreadsheet-based room specifications
- ✅ **Vector PDF Output**: Professional-quality shop drawings
- ✅ **ADA Compliance**: Automated compliance checking and documentation
- ✅ **Robust Validation**: Type, domain, geometric, and referential integrity checks
- ✅ **Audit Trails**: Complete reproducibility with configuration and input hashing
- 🚧 **DXF-Ready Architecture**: Future DXF export capability via adapter pattern

## Project Status

**Phase 1 Complete**: Foundation & Core Infrastructure
- ✅ Repository structure and Python packages
- ✅ Core interfaces (IRenderer, IValidator, ILayoutEngine)
- ✅ Configuration system with YAML loading and validation
- ✅ CLI framework with Click
- ✅ Testing infrastructure with pytest
- ✅ Default configuration with industry standards

**Phase 2 Complete**: Data Pipeline & Validation
- ✅ CSV schema definition with comprehensive field validation
- ✅ Robust CSV parser with type checking (string, numeric, boolean, JSON arrays)
- ✅ Multi-level validation system:
  - Type & Domain validation (field types, ranges, patterns)
  - Geometric Consistency validation (module sums, tolerances, ADA compliance)
  - Referential Integrity validation (config references, material codes)
- ✅ Error reporting system with JSON logs per room and batch summaries
- ✅ Fail-fast processing with detailed validation feedback
- ✅ Integration with CLI pipeline and dry-run support

**Next Phase**: Core Layout Engine (Phase 3)

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd millwork-drafter

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Generate PDFs with default configuration
python generate.py --input input/rooms.csv

# Use custom configuration
python generate.py --input input/rooms.csv --config config/project.yaml

# Validate only (dry run)
python generate.py --input input/rooms.csv --dry-run --verbose

# Strict validation mode
python generate.py --input input/rooms.csv --strict

# Validate configuration only
python generate.py validate-config config/project.yaml

# Create new configuration file
python generate.py init-config --output config/my_project.yaml
```

### CSV Input Format

Room specifications use a simple CSV format with comprehensive validation:

```csv
room_id,total_length_in,num_modules,module_widths,material_top,material_casework,has_sink,counter_height_in
KITCHEN-01,144.0,4,"[36,30,36,42]",QTZ-01,PLM-WHT,true,36.0
BATH-01,72.0,2,"[36,36]",LAM-01,PLM-WHT,false,34.0
OFFICE-01,96.0,3,"[24,48,24]",LAM-02,OAK-NAT,false,30.0
```

**Required Fields:**
- `room_id`: Unique identifier (e.g., "KITCHEN-01")
- `total_length_in`: Total length in inches (positive number)
- `num_modules`: Number of cabinet modules (positive integer)
- `module_widths`: JSON array of module widths (e.g., "[36,30,36,42]")
- `material_top`: Top material code
- `material_casework`: Casework material code

**Optional Fields:**
- `left_filler_in`, `right_filler_in`: Filler widths in inches
- `has_sink`, `has_ref`: Boolean flags for fixtures
- `counter_height_in`: Custom counter height
- `edge_rule`: Edge treatment rule
- `hardware_defaults`: Hardware specification key
- `notes`, `references`: Documentation fields

### Validation Features

Phase 2 implements comprehensive validation:

- **Type Validation**: Data type checking with proper error messages
- **Domain Validation**: Range checks, pattern matching, enum validation
- **Geometric Consistency**: Module width sums vs. total length within tolerance
- **ADA Compliance**: Counter height and accessibility checking
- **Referential Integrity**: Configuration key validation
- **Error Reporting**: JSON logs per room plus batch summaries

Example validation output:
```bash
Validation Summary:
  Total rooms: 5
  Valid rooms: 4
  Failed rooms: 1
  Success rate: 80.0%
### Configuration

The system uses YAML configuration files with parametric `[CFG.*]` placeholders:

```yaml
# Basic settings
SCALE_PLAN: 0.25          # 1/4" = 1'-0" scale
COUNTER_HEIGHT: 36.0      # Standard counter height (inches)
BASE_DEPTH: 24.0         # Standard base cabinet depth

# ADA compliance
ADA:
  KNEE_CLEAR: "27\" H x 30\" W x 17\" D"
  TOE_CLEAR: "9\" H x 6\" D"
  COUNTER_RANGE: [28.0, 34.0]

# Edge treatment options
EDGE_RULES: ["MATCH_FACE", "PVC_EDGE", "SOLID_LUMBER", "RADIUS"]

# Hardware specifications
HW:
  DEFAULTS:
    HINGE: "BLUM-110"
    PULL: "SS-128"
    SLIDE: "BLUM-563"

# Validation tolerances
TOLERANCES:
  LENGTH_SUM: 0.125       # 1/8" tolerance for length calculations

# Output settings
PDF:
  SIZE: "letter"
  MARGINS: [0.5, 0.5, 0.5, 0.5]
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit      # Unit tests only
pytest -m integration  # Integration tests only
```

### Code Quality

```bash
# Format code
black src tests

# Type checking
mypy src

# Linting
flake8 src tests
```

### Project Structure

```
millwork-drafter/
├── src/
│   ├── core/           # Core interfaces and configuration
│   ├── parser/         # CSV parsing and validation
│   ├── renderer/       # PDF rendering (DXF-ready)
│   └── utils/          # Utility functions
├── tests/              # Test suite with fixtures
├── config/             # Configuration files
├── input/              # Input CSV files
├── output/
│   ├── pdfs/          # Generated PDF outputs
│   └── logs/          # Audit logs and error reports
├── memory-banks/       # Project specifications
└── generate.py         # Main CLI entry point
```

## Architecture

The system implements a clean pipeline architecture:

```
CSV → Parser/Validator → Parametric Layout → PDF Renderer → Artifacts
```

### Key Components

- **ConfigLoader**: YAML configuration with validation and hashing
- **IValidator**: Abstract validation interface with multiple implementations
- **ILayoutEngine**: Geometric layout computation from CSV data
- **IRenderer**: Abstract rendering interface (PDF implemented, DXF-ready)

### Design Principles

1. **Parametric**: No hard-coded dimensions, all values from configuration
2. **Validated**: Comprehensive type, domain, and geometric validation
3. **Reproducible**: Configuration and input hashing for audit trails
4. **Extensible**: Clean interfaces for future enhancements
5. **Professional**: Industry-standard shop drawing conventions

## Documentation

- [`memory-banks/millwork_spec_memory_bank.md`](memory-banks/millwork_spec_memory_bank.md): Shop drawing specifications
- [`memory-banks/tech_specs.md`](memory-banks/tech_specs.md): Technical implementation details
- [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md): Complete development roadmap

## Contributing

1. Follow the development plan phases
2. Maintain test coverage >90%
3. Use type hints and docstrings
4. Follow the Anti-Over-Engineering Guardrails

## License

[Your License Here]

## Support

For questions or issues, please refer to the memory banks documentation or create an issue in the repository.