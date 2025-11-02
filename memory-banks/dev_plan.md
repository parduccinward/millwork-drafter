# Millwork Drafter - Development Plan

Based on `memory-banks/millwork_spec_memory_bank.md` and `memory-banks/tech_specs.md`

## Overview

This plan implements a **parametric, CSV-driven pipeline** that generates **vector PDFs** for millwork shop drawings. The development follows the **Right-Sized Full Spec** approach with **Anti-Over-Engineering Guardrails** from the memory banks.

---

## Phase 1: Foundation & Core Infrastructure (2-3 weeks)

### 1.1 Project Setup & Architecture
**Goal**: Establish the basic project structure and core interfaces

**Deliverables**:
- [ ] Repository structure following tech spec layout
- [ ] Core interfaces and abstract classes
- [ ] Configuration system with YAML/JSON support
- [ ] Basic CLI framework
- [ ] Unit testing infrastructure

**Key Files**:
```
millwork-drafter/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interfaces.py      # IRenderer, IValidator interfaces
│   │   └── config.py          # Config loading and validation
│   ├── parser/
│   │   ├── __init__.py
│   │   └── csv_parser.py      # CSV schema definition
│   ├── renderer/
│   │   ├── __init__.py
│   │   └── adapter.py         # IRenderer interface (DXF-ready)
│   └── utils/
│       ├── __init__.py
│       └── validation.py      # Common validation helpers
├── tests/
│   ├── __init__.py
│   ├── fixtures/              # Test CSVs and configs
│   └── test_config.py
├── config/
│   └── default.yaml           # Default configuration
├── generate.py                # Main CLI entry point
└── requirements.txt
```

**Acceptance Criteria**:
- [ ] Configuration loads from YAML with validation
- [ ] CLI accepts basic parameters (--input, --config, --output)
- [ ] Test framework runs successfully
- [ ] Code follows PEP 8 standards

### 1.2 Configuration System Implementation
**Goal**: Implement the parametric `[CFG.*]` system from memory bank

**Key Components**:
- [ ] YAML config loader with schema validation
- [ ] Parameter resolution system
- [ ] Default values and inheritance
- [ ] Config hash generation for reproducibility

**Config Structure** (from memory bank):
```yaml
SCALE_PLAN: 0.25
COUNTER_HEIGHT: 36
BASE_DEPTH: 24
WALL_CAB_DEPTH: 12
ADA:
  KNEE_CLEAR: "27\" H x 30\" W x 17\" D"
  TOE_CLEAR: "9\" H x 6\" D"
  COUNTER_RANGE: [28, 34]
  CLEAR_WIDTHS: 32
CODE:
  BASIS: "ADA 2010"
TOLERANCES:
  LENGTH_SUM: 0.125
  LENGTH_ROUNDING: 2
PDF:
  SIZE: "letter"
  MARGINS: [0.5, 0.5, 0.5, 0.5]
HW:
  DEFAULTS:
    HINGE: "BLUM-110"
    PULL: "SS-128"
    SLIDE: "BLUM-563"
EDGE_RULE: "MATCH_FACE"
```

---

## Phase 2: Data Pipeline & Validation (2-3 weeks)

### 2.1 CSV Parser & Schema Validation
**Goal**: Implement robust CSV parsing with comprehensive validation

**Components**:
- [ ] CSV schema definition (from tech spec section 3.1)
- [ ] Type validation (string, numeric, boolean, list parsing)
- [ ] Domain validation (enums, ranges, patterns)
- [ ] Geometric consistency validation
- [ ] Referential integrity checks

**CSV Schema Implementation**:
```python
class RoomSchema:
    required_fields = [
        'room_id',           # string, unique
        'total_length_in',   # number > 0
        'num_modules',       # integer >= 1
        'module_widths',     # string list "[36,30,36,30]"
        'material_top',      # string code
        'material_casework'  # string code
    ]
    
    optional_fields = [
        'left_filler_in', 'right_filler_in',  # number >= 0
        'has_sink', 'has_ref',                # boolean
        'counter_height_in',                  # number > 0
        'edge_rule',                          # enum from CFG
        'hardware_defaults',                  # key to CFG.HW.DEFAULTS
        'notes', 'references'                 # free text
    ]
```

### 2.2 Validation Rules (from tech spec section 4)
**Goal**: Implement all validation rules with clear error reporting

**Validation Categories**:
- [ ] **Type & Domain**: Field types, ranges, uniqueness
- [ ] **Geometric Consistency**: Module width sums, tolerance checks
- [ ] **Referential Integrity**: Config key existence, enum validation
- [ ] **Fail-Fast & Report**: Continue batch processing, detailed error logs

**Error Handling**:
- [ ] JSON error reports per room: `output/logs/{room_id}.errors.json`
- [ ] Batch summary: `output/logs/summary.json`
- [ ] User-friendly error messages

---

## Phase 3: Core Layout Engine (3-4 weeks)

### 3.1 Parametric Layout System
**Goal**: Implement the geometric layout engine from tech spec section 5

**Components**:
- [ ] Coordinate system (local origin, units conversion)
- [ ] Module layout calculation
- [ ] Filler positioning (left/right)
- [ ] Countertop geometry
- [ ] ADA compliance box generation
- [ ] Tolerance handling and rounding

**Layout Elements**:
```python
class LayoutEngine:
    def compute_layout(self, room_data, config):
        # Base modules: rectangles sized by module_widths × CFG.BASE_DEPTH
        # Fillers: left/right rectangles if present
        # Countertop: continuous polyline atop modules
        # ADA box: schematic with CFG.ADA.* parameters
        # Labels: material codes, dimensions
        pass
```

### 3.2 Drawing Primitives & Geometry
**Goal**: Create the geometric foundation for rendering

**Primitives** (from tech spec section 6.2):
- [ ] `draw_rect(x, y, w, h, style)`
- [ ] `draw_line(x1, y1, x2, y2, style)`
- [ ] `draw_text(x, y, text, style)`
- [ ] `draw_dim(x1, x2, y_base, format)`

**Coordinate Handling**:
- [ ] Unit conversion (inches to PostScript points: 1 in = 72 pt)
- [ ] Scale application
- [ ] Margin calculations

---

## Phase 4: PDF Rendering Engine (2-3 weeks)

### 4.1 Vector PDF Implementation
**Goal**: Generate professional-quality vector PDFs

**Components**:
- [ ] PDF library integration (ReportLab or similar)
- [ ] Page setup and scaling
- [ ] Style system (line weights, fonts, colors)
- [ ] Drawing primitive implementation
- [ ] Metadata embedding

**PDF Features**:
- [ ] Configurable page sizes (letter, tabloid, ANSI)
- [ ] Scale bars with units
- [ ] Layer organization by style
- [ ] Vector graphics (no raster images)

### 4.2 Rendering Pipeline
**Goal**: Complete the layout-to-PDF transformation

**Components**:
- [ ] Layout-to-primitives conversion
- [ ] Style application
- [ ] Text placement and sizing
- [ ] Dimension line generation
- [ ] Output file management

---

## Phase 5: Shop Drawing Compliance (2-3 weeks)

### 5.1 Millwork-Specific Features
**Goal**: Implement shop drawing requirements from memory bank

**Components** (from Section A of memory bank):
- [ ] **Project & Submission Metadata**: Title blocks, revision tracking
- [ ] **Views & Organization**: Plan views with callouts and references
- [ ] **Room/Quantity Schedule**: Multi-room support with quantities
- [ ] **Materials & Finishes**: Finish schedule with codes and descriptions
- [ ] **Hardware Schedule**: Hardware callouts with specifications
- [ ] **Construction Notes**: Build-up details and installation notes

### 5.2 ADA Compliance Integration
**Goal**: Automated ADA compliance checking and documentation

**Features**:
- [ ] ADA clearance validation
- [ ] Counter height compliance
- [ ] Clear width verification
- [ ] Code basis documentation
- [ ] Compliance reporting

---

## Phase 6: Quality Assurance & Testing (2 weeks)

### 6.1 Comprehensive Testing Suite
**Goal**: Ensure reliability and correctness

**Test Categories** (from tech spec section 8):
- [ ] **Unit Tests**: CSV parsing, validation, layout math
- [ ] **Golden Tests**: PDF audit JSON comparison
- [ ] **Fuzz Tests**: Random module width combinations
- [ ] **Integration Tests**: End-to-end pipeline testing
- [ ] **Validation Tests**: Error handling and reporting

### 6.2 Quality Metrics
**Goal**: Establish quality benchmarks

**Metrics**:
- [ ] Test coverage >90%
- [ ] Performance benchmarks
- [ ] Memory usage profiling
- [ ] Error rate tracking

---

## Phase 7: Production Readiness (1-2 weeks)

### 7.1 CLI Enhancement & Documentation
**Goal**: Production-ready command-line interface

**Features**:
- [ ] Comprehensive CLI options
- [ ] Progress reporting for large batches
- [ ] Verbose/quiet modes
- [ ] Help documentation
- [ ] Exit code standards (0: success, 1: partial failure, 2: fatal error)

**CLI Example**:
```bash
python generate.py \
  --input input/rooms.csv \
  --config config/project_alpha.yaml \
  --output output/pdfs \
  --strict \
  --units inches
```

### 7.2 Deployment & Distribution
**Goal**: Package for distribution and deployment

**Components**:
- [ ] Setup.py/pyproject.toml configuration
- [ ] Requirements management
- [ ] Docker containerization (optional)
- [ ] Documentation website
- [ ] Release process

---

## Phase 8: Future-Proofing & Extensions (1-2 weeks)

### 8.1 DXF Adapter Preparation
**Goal**: Implement DXF-ready architecture without DXF implementation

**Components** (from tech spec section 10):
- [ ] `IRenderer` interface refinement
- [ ] Adapter pattern implementation
- [ ] PDF renderer as IRenderer implementation
- [ ] DXF renderer stub for future implementation

### 8.2 Extension Points
**Goal**: Prepare for future enhancements

**Planned Extensions**:
- [ ] Image-to-CSV pipeline preparation
- [ ] Equipment library hooks
- [ ] Multi-jurisdiction ADA templates
- [ ] Custom template system

---

## Success Criteria & Milestones

### MVP Success Criteria (from tech spec section 15):
- [ ] Given valid CSV and config → generates one PDF per row
- [ ] Plan view segmented by modules with material labels
- [ ] Optional ADA box when configured
- [ ] No hard-coded dimensions (all from CSV/config)
- [ ] Audit JSON with tolerance verification
- [ ] Failed rows don't block successful ones
- [ ] Accurate summary reporting

### Quality Gates:
- [ ] All tests pass
- [ ] Documentation complete
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] User acceptance testing passed

---

## Resource Requirements

### Team Structure:
- **Lead Developer**: Architecture, core systems
- **Backend Developer**: Parser, validation, layout engine
- **Frontend/PDF Developer**: Rendering pipeline, PDF generation
- **QA Engineer**: Testing, validation, quality assurance

### Timeline Summary:
- **Total Development Time**: 14-18 weeks
- **MVP Delivery**: End of Phase 5 (10-12 weeks)
- **Production Ready**: End of Phase 7 (12-15 weeks)
- **Future-Proof**: End of Phase 8 (14-18 weeks)

### Technology Stack:
- **Python 3.9+**: Core language
- **PyYAML**: Configuration management
- **Pandas**: CSV processing
- **ReportLab**: PDF generation
- **pytest**: Testing framework
- **Click**: CLI framework

---

## Risk Mitigation

### Technical Risks:
- **PDF Complexity**: Start with simple layouts, iterate
- **Performance**: Profile early, optimize incrementally
- **Validation Complexity**: Build incrementally with comprehensive tests

### Business Risks:
- **Scope Creep**: Strict adherence to memory bank specifications
- **User Adoption**: Early user feedback integration
- **Maintenance**: Comprehensive documentation and testing

---

## Next Steps

1. **Phase 1 Kickoff**: Set up repository structure and core interfaces
2. **Stakeholder Review**: Validate plan with users and domain experts
3. **Technical Spike**: Validate PDF generation approach
4. **Resource Allocation**: Assign team members to phases
5. **Timeline Refinement**: Adjust based on team capacity and priorities

This plan implements the **Right-Sized Full Spec** approach from the memory bank while following the **Anti-Over-Engineering Guardrails** to deliver a robust, maintainable, and extensible millwork drafting system.