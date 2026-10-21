import sqlite3
from pathlib import Path

DB_PATH = Path("autoscan.db")
SCHEMA_PATH = Path("schema.sql")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Execute Schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # 2. Seed 5 Vehicle Zones
    zones = [("front",), ("left",), ("right",), ("rear",), ("upper",)]
    cursor.executemany(
        "INSERT OR IGNORE INTO zones (zone_name) VALUES (?);",
        zones
    )

    # Fetch zone_id mapping
    cursor.execute("SELECT zone_name, zone_id FROM zones;")
    zone_map = dict(cursor.fetchall())

    # 3. Seed Body Panels with Malaysian Market Part Replacement Values (MYR)
    # Feeds into Module 4 Mamdani FIS (Car Part Value input)
    body_panels = [
        # Front Zone
        (zone_map["front"], "front_bumper", 450.00),
        (zone_map["front"], "bonnet_hood", 650.00),
        (zone_map["front"], "front_grille", 280.00),
        (zone_map["front"], "headlight_assembly", 550.00),
        # Left Zone
        (zone_map["left"], "left_front_fender", 380.00),
        (zone_map["left"], "left_front_door", 750.00),
        (zone_map["left"], "left_rear_door", 720.00),
        (zone_map["left"], "left_rear_quarter_panel", 680.00),
        # Right Zone
        (zone_map["right"], "right_front_fender", 380.00),
        (zone_map["right"], "right_front_door", 750.00),
        (zone_map["right"], "right_rear_door", 720.00),
        (zone_map["right"], "right_rear_quarter_panel", 680.00),
        # Rear Zone
        (zone_map["rear"], "rear_bumper", 420.00),
        (zone_map["rear"], "boot_trunk_lid", 600.00),
        (zone_map["rear"], "taillight_assembly", 350.00),
        # Upper Zone
        (zone_map["upper"], "roof_panel", 950.00),
        (zone_map["upper"], "front_windshield", 650.00),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO body_panels (zone_id, panel_name, part_value)
        VALUES (?, ?, ?);
        """,
        body_panels
    )

    # 4. Seed Sample Malaysian Rental Fleet Vehicles
    vehicles = [
        ("MCB 4821", "Perodua", "Myvi 1.5 AV"),
        ("VKL 9104", "Proton", "Saga 1.3 Premium"),
        ("WYY 3382", "Honda", "City 1.5 RS"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO vehicles (plate_number, make, model) VALUES (?, ?, ?);",
        vehicles
    )

    # 5. Seed a Sample CHECKOUT and RETURN Inspection for Testing Module 3
    cursor.execute("SELECT vehicle_id FROM vehicles WHERE plate_number = 'MCB 4821';")
    vehicle_id = cursor.fetchone()[0]

    cursor.execute("SELECT panel_id FROM body_panels WHERE panel_name = 'front_bumper';")
    front_bumper_id = cursor.fetchone()[0]

    cursor.execute("SELECT panel_id FROM body_panels WHERE panel_name = 'left_front_door';")
    left_door_id = cursor.fetchone()[0]

    # Insert Baseline Checkout Inspection
    cursor.execute(
        """
        INSERT INTO inspections (vehicle_id, previous_inspection_id, inspection_type, inspected_at)
        VALUES (?, NULL, 'checkout', '2026-10-18 09:00:00');
        """,
        (vehicle_id,)
    )
    checkout_id = cursor.lastrowid

    # Insert Pre-existing Defect recorded at Checkout (Scratch on Front Bumper)
    cursor.execute(
        """
        INSERT INTO defects (
            inspection_id, panel_id, defect_type,
            bbox_x, bbox_y, bbox_w, bbox_h,
            surface_area, keyframe_path, mask_path,
            confidence, status, matched_defect_id
        ) VALUES (?, ?, 'scratch', 0.42, 0.65, 0.12, 0.05, 14.5,
                  'frames/chk_1_front.jpg', 'masks/chk_1_front_mask.png',
                  0.89, 'pre-existing', NULL);
        """,
        (checkout_id, front_bumper_id)
    )
    checkout_defect_id = cursor.lastrowid

    # Insert Return Inspection linked to Checkout Inspection
    cursor.execute(
        """
        INSERT INTO inspections (vehicle_id, previous_inspection_id, inspection_type, inspected_at)
        VALUES (?, ?, 'return', '2026-10-21 17:30:00');
        """,
        (vehicle_id, checkout_id)
    )
    return_id = cursor.lastrowid

    # Defect 1 at Return: Same scratch on Front Bumper (Slightly shifted bbox due to camera angle -> matched as 'pre-existing')
    cursor.execute(
        """
        INSERT INTO defects (
            inspection_id, panel_id, defect_type,
            bbox_x, bbox_y, bbox_w, bbox_h,
            surface_area, keyframe_path, mask_path,
            confidence, status, matched_defect_id
        ) VALUES (?, ?, 'scratch', 0.43, 0.64, 0.13, 0.05, 15.1,
                  'frames/ret_2_front.jpg', 'masks/ret_2_front_mask.png',
                  0.91, 'pre-existing', ?);
        """,
        (return_id, front_bumper_id, checkout_defect_id)
    )

    # Defect 2 at Return: Brand new dent on Left Front Door (No match in checkout -> flagged as 'new' for Module 4 FIS)
    cursor.execute(
        """
        INSERT INTO defects (
            inspection_id, panel_id, defect_type,
            bbox_x, bbox_y, bbox_w, bbox_h,
            surface_area, keyframe_path, mask_path,
            confidence, status, matched_defect_id
        ) VALUES (?, ?, 'dent', 0.55, 0.48, 0.18, 0.16, 42.8,
                  'frames/ret_2_left.jpg', 'masks/ret_2_left_mask.png',
                  0.87, 'new', NULL);
        """,
        (return_id, left_door_id)
    )

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Initialized {DB_PATH} with 5 zones, 17 body panels, sample vehicles, and test inspections.")

if __name__ == "__main__":
    init_database()