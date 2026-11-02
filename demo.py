"""AutoScan AI - Module 3 demo (Damage Comparison and Baseline Verification).

Run:  python demo.py

Builds a fresh demo database (demo.db, separate from autoscan.db), simulates one
checkout and one return inspection, runs the comparison, and prints the results.
Needs schema.sql, queries.py and compare.py in the same folder.
"""
import sqlite3
from pathlib import Path

import queries
from compare import compare_inspection, iou, IOU_THRESHOLD, DIRT_CONFIDENCE

BASE_DIR = Path(__file__).parent
DEMO_DB = BASE_DIR / "demo.db"
SCHEMA = BASE_DIR / "schema.sql"

ZONES = ["front", "left", "right", "rear", "upper"]
PANELS = [  # (zone, panel, sample replacement value in MYR)
    ("front", "front_bumper", 450.0),
    ("front", "bonnet_hood", 650.0),
    ("left", "left_front_door", 750.0),
    ("rear", "rear_bumper", 420.0),
    ("upper", "roof_panel", 950.0),
]


def setup_database():
    """Create a clean demo database with zones and body panels."""
    if DEMO_DB.exists():
        DEMO_DB.unlink()
    queries.DB_PATH = DEMO_DB  # point queries.py at the demo database
    conn = sqlite3.connect(DEMO_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.executemany("INSERT INTO zones (zone_name) VALUES (?)", [(z,) for z in ZONES])
    for zone, panel, value in PANELS:
        conn.execute(
            "INSERT INTO body_panels (zone_id, panel_name, part_value) "
            "VALUES ((SELECT zone_id FROM zones WHERE zone_name = ?), ?, ?)",
            (zone, panel, value),
        )
    conn.commit()
    conn.close()


def panel_id(name):
    with queries.get_connection() as conn:
        return conn.execute(
            "SELECT panel_id FROM body_panels WHERE panel_name = ?", (name,)
        ).fetchone()["panel_id"]


def print_table(title, headers, rows):
    print(f"\n{title}")
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(str(x).ljust(w) for x, w in zip(row, widths)))


def main():
    setup_database()
    print("=" * 60)
    print("AutoScan AI - Module 3 demo")
    print(f"Settings: IoU threshold = {IOU_THRESHOLD}, dirt confidence < {DIRT_CONFIDENCE}")
    print("=" * 60)

    # Step 1: vehicle and checkout inspection (baseline)
    vid = queries.add_vehicle("MCB 4821", "Perodua", "Myvi 1.5 AV")
    checkout = queries.create_inspection(vid, "checkout")
    queries.add_defect(checkout, panel_id("front_bumper"), "scratch",
                       (0.42, 0.65, 0.12, 0.05), 14.5, 0.89, "pre-existing")
    queries.add_defect(checkout, panel_id("left_front_door"), "dent",
                       (0.30, 0.30, 0.15, 0.15), 30.0, 0.90, "pre-existing")

    base_rows = queries.get_defects_by_inspection(checkout)
    print_table(
        "STEP 1 - Checkout inspection (baseline), vehicle MCB 4821",
        ["ID", "Zone", "Panel", "Type", "Area"],
        [(d["defect_id"], d["zone_name"], d["panel_name"], d["defect_type"],
          d["surface_area"]) for d in base_rows],
    )

    # Step 2: return inspection, as if produced by the YOLO model
    ret = queries.create_inspection(vid, "return", previous_inspection_id=checkout)
    detections = [
        ("front_bumper", "scratch", (0.43, 0.64, 0.13, 0.05), 15.1, 0.91),  # same scratch, shifted
        ("left_front_door", "dent", (0.31, 0.31, 0.15, 0.14), 29.0, 0.88),  # same dent, shifted
        ("rear_bumper", "dent", (0.55, 0.50, 0.18, 0.16), 42.8, 0.87),      # brand new
        ("bonnet_hood", "scratch", (0.20, 0.40, 0.25, 0.04), 22.0, 0.93),   # brand new
        ("left_front_door", "scratch", (0.30, 0.30, 0.15, 0.15), 18.0, 0.85),  # same spot, different type
        ("roof_panel", "dent", (0.10, 0.10, 0.05, 0.05), 3.0, 0.20),        # low confidence
    ]
    for panel, dtype, bbox, area, conf in detections:
        # saved as 'new' by default; the comparison step decides the real status
        queries.add_defect(ret, panel_id(panel), dtype, bbox, area, conf, "new")

    ret_rows = queries.get_defects_by_inspection(ret)
    print_table(
        "STEP 2 - Return inspection, detections before comparison",
        ["ID", "Zone", "Panel", "Type", "Area", "Conf"],
        [(d["defect_id"], d["zone_name"], d["panel_name"], d["defect_type"],
          d["surface_area"], d["confidence"]) for d in ret_rows],
    )

    # Step 3: run the comparison
    new_defects = compare_inspection(ret)

    base_by_id = {d["defect_id"]: d for d in base_rows}
    result_rows = []
    for d in queries.get_defects_by_inspection(ret):
        if d["matched_defect_id"]:
            base = base_by_id[d["matched_defect_id"]]
            note = f"matches checkout #{base['defect_id']} (IoU {iou(d, base):.2f})"
        elif d["status"] == "dirt":
            note = "low confidence, treated as dirt/noise"
        else:
            note = "no matching baseline defect"
        result_rows.append((d["defect_id"], d["panel_name"], d["defect_type"],
                            d["status"], note))
    print_table(
        "STEP 3 - Comparison result",
        ["ID", "Panel", "Type", "Status", "Reason"],
        result_rows,
    )

    # Step 4: what Module 4 receives
    print_table(
        "STEP 4 - New defects sent to Module 4 (fuzzy cost estimation)",
        ["ID", "Panel", "Type", "Area", "Part value (MYR)"],
        [(d["defect_id"], d["panel_name"], d["defect_type"], d["surface_area"],
          d["part_value"]) for d in new_defects],
    )
    print(f"\nSummary: {len(new_defects)} new defect(s) out of {len(ret_rows)} detected at return.")


if __name__ == "__main__":
    main()
