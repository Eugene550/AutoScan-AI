-- schema.sql (Updated for AutoScan AI - Module 3)
PRAGMA foreign_keys = ON;

-- 1. VEHICLES TABLE
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number  TEXT NOT NULL UNIQUE,
    make          TEXT NOT NULL,
    model         TEXT NOT NULL
);

-- 2. ZONES TABLE (5 Guided Orthogonal Capture Views)
CREATE TABLE IF NOT EXISTS zones (
    zone_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_name  TEXT NOT NULL UNIQUE CHECK (zone_name IN ('front', 'left', 'right', 'rear', 'upper'))
);

-- 3. BODY PANELS TABLE (Mapped to Zones with Baseline Replacement Value in MYR)
CREATE TABLE IF NOT EXISTS body_panels (
    panel_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id     INTEGER NOT NULL,
    panel_name  TEXT NOT NULL,
    part_value  REAL NOT NULL CHECK (part_value >= 0),
    FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE RESTRICT,
    UNIQUE (zone_id, panel_name)
);

-- 4. INSPECTIONS TABLE (Links 'return' inspection to baseline 'checkout' inspection)
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id              INTEGER NOT NULL,
    previous_inspection_id  INTEGER,
    inspection_type         TEXT NOT NULL CHECK (inspection_type IN ('checkout', 'return')),
    inspected_at            TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (vehicle_id)             REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    FOREIGN KEY (previous_inspection_id) REFERENCES inspections(inspection_id) ON DELETE SET NULL
);

-- 5. DEFECTS TABLE (Stores YOLO instance segmentation outputs & Module 3 verification status)
CREATE TABLE IF NOT EXISTS defects (
    defect_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id      INTEGER NOT NULL,
    panel_id           INTEGER NOT NULL,
    defect_type        TEXT NOT NULL CHECK (defect_type IN ('scratch', 'dent', 'crack')),
    bbox_x             REAL NOT NULL CHECK (bbox_x >= 0),
    bbox_y             REAL NOT NULL CHECK (bbox_y >= 0),
    bbox_w             REAL NOT NULL CHECK (bbox_w > 0),
    bbox_h             REAL NOT NULL CHECK (bbox_h > 0),
    surface_area       REAL NOT NULL CHECK (surface_area >= 0),
    keyframe_path      TEXT,
    mask_path          TEXT,
    confidence         REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    status             TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('pre-existing', 'new', 'dirt')),
    matched_defect_id  INTEGER,
    FOREIGN KEY (inspection_id)     REFERENCES inspections(inspection_id) ON DELETE CASCADE,
    FOREIGN KEY (panel_id)          REFERENCES body_panels(panel_id) ON DELETE RESTRICT,
    FOREIGN KEY (matched_defect_id) REFERENCES defects(defect_id) ON DELETE SET NULL
);

-- Performance Indexes for Module 3 Baseline Comparison Queries
CREATE INDEX IF NOT EXISTS idx_inspections_vehicle ON inspections(vehicle_id, inspection_type);
CREATE INDEX IF NOT EXISTS idx_defects_inspection_panel ON defects(inspection_id, panel_id, defect_type);