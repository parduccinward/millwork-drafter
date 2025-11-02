# Memory Bank v2: Standard Content for Millwork Shop Drawings (Parametric)

This reference is split into two parts:
- **A. Right-Sized Full Spec** – comprehensive but pragmatic  
- **B. Lean Spec (MVSD)** – minimum viable, avoids over-engineering

> **Notation**: Any former hard-coded numbers now appear as **configurable parameters**, e.g. `[CFG.COUNTER_HEIGHT]`, `[CFG.BASE_DEPTH]`, `[CFG.ADA.KNEE_CLEAR]`. Provide them via a config file (YAML/JSON) per project/manufacturer.

---

## A) Right-Sized Full Spec (Comprehensive, Practical)

### 1) Project & Submission Metadata
- **Project name & location** (client/site/city/state or country)
- **Millwork contractor/manufacturer** (name, address, contact). Logo/seal *if contract requires*
- **Drawing/Package ID** and **Submittal number**
- **Issue date** and **revision history** (rev code, date, description)
- **Review status fields** (Approved / Approved as Noted / Revise & Resubmit) and **approver names**

### 2) Views & Organization
- **Plan, Elevations, Sections, Details** as applicable
- Each view includes **scale** `[CFG.SCALE_PLAN]`, **callouts**, and **room/area reference**
- **Keyed references** to base drawings (e.g., A-sheets) for coordination

### 3) Room / Quantity Schedule
- **Room list** where the millwork repeats
- **Quantity per room** and **total quantity**

### 4) Dimensions & Levels
- **Overall dimensions** (W×D×H) per assembly
- **Critical modules**: base height `[CFG.COUNTER_HEIGHT]`, base depth `[CFG.BASE_DEPTH]`, wall-cab depth `[CFG.WALL_CAB_DEPTH]`
- **AFF levels** for counters, shelves, equipment centerlines; add **VIF** only when dependency is field-driven

### 5) Accessibility (ADA or Local Code)
- **Clearances & heights** are driven by config:  
  - Knee/toe clearances `[CFG.ADA.KNEE_CLEAR]`, `[CFG.ADA.TOE_CLEAR]`  
  - Counter height range `[CFG.ADA.COUNTER_RANGE]`  
  - Approach widths `[CFG.ADA.CLEAR_WIDTHS]`
- **Code basis label**: “ADA 2010” and/or local amendments `[CFG.CODE.BASIS]`

### 6) Materials & Finishes
- **Finish schedule** with:
  - Finish code(s) (e.g., `PL-xx`, `SLD-xx`, `INT-x`) – *names come from your finish database*
  - **Description/color** and **manufacturer/code** (if specified)
  - **Edge treatment** rule (e.g., “match face” / PVC / solid banding) `[CFG.EDGE_RULE]`
  - **Application mapping** (faces/doors/drawers/interiors/tops/scribes)
- **Substitutions policy** (approved equal) `[CFG.SUBSTITUTIONS]`

### 7) Hardware
- **Hardware schedule** keyed by `HW-xx` labels: hinges, pulls, slides, catches, locks, supports
- Default hardware set per family `[CFG.HW.DEFAULTS]`; per-unit **finish/model/qty**
- Exceptions keyed at callouts

### 8) Equipment & Fixtures (By Others vs By Millwork)
- **Fixtures/equipment list** (sink, faucet, appliances) with **supply/installation responsibility**
- **Rough-in** data required from MEP (power, water, waste, ventilation) + **cutout** rules
- Responsibility tags follow `[CFG.RESPONSIBILITY_SCHEMA]` (BY MILLWORK / BY OTHERS)

### 9) Construction & Installation Notes
- **Carcass** (core, thicknesses, joinery, backs, cleats) – from `[CFG.CARCASS]`
- **Countertops** (build-ups, seams, backsplashes, scribe limits) – `[CFG.TOP]`
- **Tolerances** and **field scribing** guidance – `[CFG.TOLERANCES]`
- **Wall backing/blocking** requirements – `[CFG.BACKING]`

### 10) Coordination References
- Sheet refs to **Architecture/MEP** for centerlines, rough-ins, clearances
- **Field coordination** notes restricted to items not determinable off-site

### 11) Deliverables & Format
- **PDF set** sized per contract (ANSI/ARCH) `[CFG.PDF.SIZE]`
- CAD model/layers only if required `[CFG.CAD.DELIVERABLES]`
- **BOM** + **Hardware schedule** (on-sheet or CSV/Excel) `[CFG.SCHEDULE.FORMAT]`

---

## B) Lean Spec (Minimum Viable Shop Drawing – MVSD)

Use for typical, low-risk casework.

1) **Title block** with project, contractor, drawing ID, date, submittal  
2) **One plan + one elevation** (add a section only if thickness/build-up affects fit)  
3) **Overall W×D×H** + **2–3 critical modules** (e.g., `[CFG.COUNTER_HEIGHT]`, `[CFG.BASE_DEPTH]`, `[CFG.WALL_CAB_DEPTH]`)  
4) **One ADA box** with the **exact limits from config** (no generic diagrams)  
5) **One-line finishes** per surface group (faces/interiors/tops) with an **edge inheritance rule**  
6) **One-line hardware defaults** (hinge/pull/slide), with keyed exceptions  
7) **By-Others list** + **cutout dims** if millwork performs cuts  
8) **Single coordination note** to governing A/MEP sheet; avoid blanket “VIF”  
9) **BOM row** (qty per room, total units) on-sheet

---

## C) Anti-Over-Engineering Guardrails
- Include only **views that change fabrication/installation**; reference standard details otherwise
- Replace boilerplate notes with **one precise code citation** `[CFG.CODE.BASIS]`
- **Consolidate finishes** via inheritance; only call out deviations
- **Hardware defaults** once; key exceptions only
- Use **VIF** solely when geometry depends on field conditions
- Deliver **one PDF package**; CAD/BIM only when contractually requested

---

## D) Ready-to-Use Checklists

**Full Spec Quick Check (10):**
1. Metadata complete (project/contractor/ID/date/submittal/revs)  
2. Required views present with scales and references  
3. Room/qty schedule consistent with notes  
4. Overall + critical dims + AFF levels dimensioned  
5. Accessibility limits shown and **config/code basis** stated  
6. Finish schedule complete (codes, manufacturer, edge rules, applications)  
7. Hardware schedule keyed and quantified (defaults + exceptions)  
8. By-Others list + cutouts/rough-ins clear  
9. Construction/installation notes limited to build/fit drivers  
10. Deliverables match contract (PDF; schedules on-sheet or CSV)

**Lean MVSD Quick Check (6):**
1. Title block + IDs + date + submittal  
2. Plan & elevation with overall + 2–3 critical dims  
3. Single ADA box with **configured** limits  
4. One-line finishes + edge inheritance rule  
5. One-line hardware defaults + exceptions keyed  
6. By-Others list + any cutout; reference governing A/MEP sheet

---

## E) Data Contracts for Automation (General, No Fixed Values)

### E1. Architectural Input (extracted fields)
- `room_id`  
- `bounding_span` (usable length/height/width derived from walls/openings)  
- `references` (sheet/callout IDs)  
- `fixtures_symbols` (e.g., sink, fridge, coffee equipment)  
- `dimension_annotations` (raw strings + parsed numeric values)  
- `context_notes` (e.g., room function)

### E2. Spec Input (CSV/JSON)
- `material_top`, `material_casework`, `edge_rule`  
- `hardware_defaults` (hinge/pull/slide families)  
- `module_grid` (module size / rules)  
- `filler_policy` (min/max; left/right strategy)  
- `ada_profile` (keys map to `[CFG.ADA.*]`)  
- `responsibility_map` (BY MILLWORK / BY OTHERS)  
- `quantity`, `naming_convention`, `deliverable_profile`

### E3. Output (Drawing + Data)
- `drawing_package` (PDF; optional DWG/DXF)  
- `schedules` (BOM, hardware; CSV/Excel/on-sheet)  
- `metadata` (drawing/package ID, revision, approval status)  
- `audit` (config snapshot used for generation)

---

## F) Config Layer (Project/Manufacturer)
Provide a single config file to resolve **all** placeholders:
```yaml
SCALE_PLAN: ...
COUNTER_HEIGHT: ...
BASE_DEPTH: ...
WALL_CAB_DEPTH: ...
ADA:
  KNEE_CLEAR: ...
  TOE_CLEAR: ...
  COUNTER_RANGE: ...
  CLEAR_WIDTHS: ...
CODE:
  BASIS: "ADA 2010 + Local Amendment ..."
EDGE_RULE: ...
HW:
  DEFAULTS: ...
TOLERANCES: ...
BACKING: ...
PDF:
  SIZE: ...
CAD:
  DELIVERABLES: false
SCHEDULE:
  FORMAT: "on-sheet"
```

---

**Purpose:** A reusable, parameter-driven template for fabrication/review that avoids hard-coded values. Choose **Full Spec** for complex/high-risk scopes and **Lean MVSD** for standard, repetitive casework.
