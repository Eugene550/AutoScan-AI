import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "autoscan.db"


def get_connection():
    """Open a connection with foreign keys enforced and dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def add_vehicle(plate_number, make, model):
    """Insert a vehicle and return its vehicle_id."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO vehicles (plate_number, make, model) VALUES (?, ?, ?)",
            (plate_number, make, model),
        )
        return cur.lastrowid


def create_inspection(vehicle_id, inspection_type, previous_inspection_id=None):
    """Create a 'checkout' or 'return' inspection and return its inspection_id.

    A return inspection should pass the checkout inspection it is compared against.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO inspections (vehicle_id, previous_inspection_id, inspection_type)
            VALUES (?, ?, ?)
            """,
            (vehicle_id, previous_inspection_id, inspection_type),
        )
        return cur.lastrowid


def add_defect(
    inspection_id,
    panel_id,
    defect_type,
    bbox,
    surface_area,
    confidence,
    status,
    keyframe_path=None,
    mask_path=None,
    matched_defect_id=None,
):
    """Insert a detected defect and return its defect_id.

    bbox is a tuple (x, y, w, h). status must be set explicitly
    ('pre-existing', 'new' or 'dirt') so checkout defects are not
    mislabelled by the table default.
    """
    bbox_x, bbox_y, bbox_w, bbox_h = bbox
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO defects (
                inspection_id, panel_id, defect_type,
                bbox_x, bbox_y, bbox_w, bbox_h,
                surface_area, keyframe_path, mask_path,
                confidence, status, matched_defect_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inspection_id, panel_id, defect_type,
                bbox_x, bbox_y, bbox_w, bbox_h,
                surface_area, keyframe_path, mask_path,
                confidence, status, matched_defect_id,
            ),
        )
        return cur.lastrowid


def get_defects_by_inspection(inspection_id):
    """Return all defects of an inspection, with panel and zone names."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT d.*, p.panel_name, p.part_value, z.zone_name
            FROM defects d
            JOIN body_panels p ON d.panel_id = p.panel_id
            JOIN zones z ON p.zone_id = z.zone_id
            WHERE d.inspection_id = ?
            """,
            (inspection_id,),
        ).fetchall()


def get_checkout_for_return(return_inspection_id):
    """Return the baseline checkout inspection linked to a return inspection.

    Returns None if the inspection has no previous_inspection_id.
    """
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT c.*
            FROM inspections r
            JOIN inspections c ON r.previous_inspection_id = c.inspection_id
            WHERE r.inspection_id = ?
            """,
            (return_inspection_id,),
        ).fetchone()
