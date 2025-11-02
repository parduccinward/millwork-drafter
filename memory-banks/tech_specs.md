# Millwork Drafter — Memory Bank (Flow, Validation, and Tech Spec)

This Memory Bank defines a **parametric, CSV‑driven pipeline** that generates **vector PDFs** for millwork shop drawings. It is intentionally **value‑agnostic** (no fixed dimensions), uses **configuration placeholders**, and is **DXF‑ready** via a renderer adapter.

> Abbreviations: `CFG.*` = configuration parameter; `in` = inches; `pt` = PostScript points (1 in = 72 pt).

---

## 1) Goals & Non‑Goals
- **Goals**
  - Deterministic generation of shop‑drawing PDFs from a **single CSV input**.
  - Strong **validation** of inputs and computed geometry (tolerances, enums, types).
  - Clear **separation of concerns** (parse → layout → render), DXF‑ready.
  - Reproducibility: embed config snapshot + input hash in outputs.
- **Non‑Goals (MVP)**
  - No OCR/CV; no image parsing in this phase.
  - No interactive editing; no AutoCAD authoring (DXF export is deferred).

---

## 2) High‑Level Pipeline
```
CSV → Parser/Validator → Parametric Layout → PDF Renderer → Artifacts (PDF + audit)
```
- **Parser/Validator**: Reads CSV, enforces schema and constraints.
- **Parametric Layout**: Computes cabinet modules, fillers, labels, ADA box, callouts.
- **PDF Renderer**: Vector PDF; scale, layers-by-style, page template.
- **Artifacts**: `output/pdfs/*.pdf`, `output/logs/*.json` (audit).

---

## 3) Data Contracts (Abstract, No Fixed Values)

### 3.1 CSV Schema (columns)
Required:
- `room_id` *(string, unique, e.g., "KITCHEN-01")*
- `total_length_in` *(number > 0, e.g., 144.0)*
- `num_modules` *(integer ≥ 1, e.g., 4)*
- `module_widths` *(string list, e.g., "[36,30,36,30]")*
- `material_top` *(string code, e.g., "QTZ-01")*
- `material_casework` *(string code, e.g., "PLM-WHT")*

Optional (recommended):
- `left_filler_in`, `right_filler_in` *(number ≥ 0, e.g., 1.5)*
- `has_sink`, `has_ref` *(boolean, e.g., true)*
- `counter_height_in` *(number > 0, e.g., 36.0)*
- `edge_rule` *(enum from CFG, e.g., "MATCH_FACE")*
- `hardware_defaults` *(key to CFG.HW.DEFAULTS, e.g., "STANDARD")*
- `notes` *(free text)*
- `references` *(sheet/callout IDs, e.g., "A3.1/2")*

### 3.2 Config (YAML/JSON)
- `SCALE_PLAN` *(drawing scale ratio, e.g., 0.25 for 1/4"=1')*
- `COUNTER_HEIGHT`, `BASE_DEPTH`, `WALL_CAB_DEPTH` *(in inches)*
- `ADA`: `KNEE_CLEAR`, `TOE_CLEAR`, `COUNTER_RANGE`, `CLEAR_WIDTHS`
- `CODE.BASIS` *(e.g., "ADA 2010 + local amendment")*
- `EDGE_RULE`, `HW.DEFAULTS`, `TOLERANCES`, `BACKING`
- `PDF.SIZE` *(e.g., "letter", "tabloid", "ANSI-D")*, `SCHEDULE.FORMAT`

Example structure:
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
TOLERANCES:
  LENGTH_SUM: 0.125
  LENGTH_ROUNDING: 2
PDF:
  SIZE: "letter"
  MARGINS: [0.5, 0.5, 0.5, 0.5]
```

---

## 4) Validation Rules (MVP)

### 4.1 Type & Domain
- `room_id`: non‑empty, unique.
- `total_length_in`: numeric, > 0.
- `num_modules`: integer ≥ 1.
- `module_widths`: parse to list of numbers; length must equal `num_modules`.
- `material_top`, `material_casework`: non‑empty strings; if CFG restricts, enforce allowed set.
- `left_filler_in`, `right_filler_in`: numeric ≥ 0 when present.
- `has_sink`, `has_ref`: boolean if present.

### 4.2 Geometric Consistency
- `sum(module_widths) + left_filler_in + right_filler_in` ≈ `total_length_in` within `CFG.TOLERANCES.LENGTH_SUM`.
- If `counter_height_in` present, ensure it lies within `CFG.ADA.COUNTER_RANGE` (inclusive).
- If ADA profile present: ensure `CFG.ADA.KNEE_CLEAR`, `CFG.ADA.TOE_CLEAR`, `CFG.ADA.CLEAR_WIDTHS` are defined in config.

### 4.3 Referential Integrity
- `edge_rule` ∈ `CFG.EDGE_RULES` (if provided).
- `hardware_defaults` key exists under `CFG.HW.DEFAULTS`.
- `references` should match a simple pattern (e.g., `\d+\/[A-Z]\d+\.\d+`), if used.

### 4.4 Fail‑Fast & Report
- On any hard error → **fail the record** and continue batch; write a JSON error report in `output/logs/room_id.errors.json`.
- Summaries written to `output/logs/summary.json` (counts: ok, failed; reasons).

---

## 5) Parametric Layout (Abstract)

### 5.1 Coordinate System
- Local origin at left finished face; X grows to the right, Y grows upward.
- Units: **in** internally; renderer converts: `pt = in * 72`.
- Margins: `[CFG.PDF.MARGINS]` reserve printable area.

### 5.2 Elements
- **Base modules**: rectangles sized by `module_widths` × `CFG.BASE_DEPTH` (visualized in plan).
- **Fillers**: left/right rectangles if present.
- **Countertop**: continuous polyline/rect atop modules; label uses `material_top`.
- **Casework label & materials**: label near plan bar; `material_casework`.
- **ADA box**: schematic box with labels driven by `CFG.ADA.*` (no fixed values).
- **Callouts/Notes**: `notes`, `references` rendered in a dedicated area.
- **BOM row** (optional): if `SCHEDULE.FORMAT = on-sheet`.

### 5.3 Tolerances & Rounding
- Apply `CFG.TOLERANCES.LENGTH_ROUNDING` when displaying numeric labels (no data loss in computation, only display).

---

## 6) PDF Renderer (Vector)

### 6.1 Page & Scale
- Page size: `CFG.PDF.SIZE` (e.g., letter/tabloid/ANSI).
- Scale bar: optional; **text labels** must include units (in/mm based on CFG).
- Line weights, hatches, fonts defined by `CFG.PDF.STYLES`.

### 6.2 Drawing Primitives (API)
- `draw_rect(x, y, w, h, style)`
- `draw_line(x1, y1, x2, y2, style)`
- `draw_text(x, y, text, style)`
- `draw_dim(x1, x2, y_base, format)` (simple dimension baseline)

### 6.3 Metadata & Audit
- Embed **PDF meta**: `room_id`, generator version, `config_sha256`, `csv_sha256`, timestamp.
- Write sidecar `output/logs/room_id.audit.json` with: resolved CFG, CSV row, computed sums, tolerance deltas.

### 6.4 Determinism
- Avoid non‑deterministic ordering; sort modules by X; fix random seeds if used.

---

## 7) CLI & Execution

### 7.1 Command
```
python generate.py --input input/rooms.csv --config config/default.yaml --output output/pdfs
```
Optional flags:
- `--strict` (treat warnings as errors)
- `--units mm|in` (format labels only)

### 7.2 Exit Codes
- `0`: all rows successful
- `1`: some rows failed (see logs)
- `2`: fatal config/input error

---

## 8) Testing Strategy (MVP)
- **Unit tests** for: CSV parsing, schema validation, layout sum check, tolerance logic.
- **Golden test**: generate one PDF and compare its **audit JSON** (not the binary PDF).
- **Fuzz test**: random `module_widths` whose sum equals total (within tolerance).

Folder:
```
tests/
  ├─ test_schema.py
  ├─ test_layout_math.py
  ├─ test_renderer_stub.py
  └─ fixtures/ (tiny CSVs + CFGs)
```

---

## 9) Repo Layout (MVP)
```
millwork-drafter/
├─ input/
├─ config/
├─ output/
│  ├─ pdfs/
│  └─ logs/
├─ src/
│  ├─ parser/         # CSV reader/validator
│  ├─ core/           # layout math
│  ├─ renderer/
│  │  ├─ pdf_renderer.py
│  │  └─ adapter.py   # IRenderer interface (DXF-ready)
│  └─ utils/
├─ tests/
├─ generate.py
└─ README.md
```

---

## 10) DXF‑Ready (Without Implementing DXF Yet)
- Define `IRenderer` in `renderer/adapter.py`:
  - `begin_page(meta)`, `draw_rect`, `draw_line`, `draw_text`, `draw_dim`, `end_page()`.
- `pdf_renderer.py` implements `IRenderer` now.
- Future `dxf_renderer.py` will implement the same interface — **no changes** in core.

---

## 11) Error Handling & Messaging
- Clear, user‑facing messages:
  - Missing column → identify column.
  - Length sum mismatch → show both sums and allowed tolerance.
  - Enum mismatch → list allowed values from CFG.
- Continue processing other rows; aggregate results in summary.

---

## 12) Naming, Versioning, and Reproducibility
- Output filename: `{room_id}.pdf`
- Version tag in PDF meta: `app_version`, `spec_version`.
- Store `config_sha256` and `csv_sha256` in the audit JSON and PDF metadata.

---

## 13) Security/Privacy
- CSV must not include PII beyond project identifiers.
- Logs should omit environment variables; keep only spec‑relevant data.

---

## 14) Future Extensions (Not in MVP)
- Image → CSV (`image_to_csv.py`) using OCR; emits the same schema.
- Equipment libraries → auto‑placement rules.
- ADA template variants by jurisdiction.

---

## 15) Acceptance Criteria (MVP)
- Given a valid CSV and CFG, the system **generates one PDF per row** with:
  - Plan bar segmented by modules,
  - Material labels (top/casework),
  - (Optional) ADA box if CFG enables it,
  - No hard‑coded dimensions; all labels come from CSV/CFG,
  - Audit JSON written and sums within tolerance.
- Failing rows do **not** block successful ones; summary counts are correct.

---

**Purpose:** This Memory Bank serves as the **canonical, implementation‑ready spec** for the CSV→PDF pipeline, ensuring consistency, testability, and future‑proofing (DXF‑ready via adapter) without over‑engineering the MVP.
