"""Tests for compare.py. Uses a temporary database, so autoscan.db is untouched.

Run:  python test_compare.py
"""
import sqlite3
import tempfile
from pathlib import Path

import queries
from compare import compare_inspection

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def make_test_db():
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    queries.DB_PATH = tmp  # point queries.py at the temp database
    conn = sqlite3.connect(tmp)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO zones (zone_name) VALUES ('front'), ('left')")
    conn.execute(
        "INSERT INTO body_panels (zone_id, panel_name, part_value) VALUES "
        "(1, 'front_bumper', 450), (2, 'left_front_door', 750)"
    )
    conn.commit()
    conn.close()


def run():
    make_test_db()
    vid = queries.add_vehicle("TEST 1234", "Perodua", "Myvi")
    bumper, door = 1, 2

    chk = queries.create_inspection(vid, "checkout")
    # Baseline defects at checkout
    base_scratch = queries.add_defect(chk, bumper, "scratch", (0.42, 0.65, 0.12, 0.05),
                                      14.5, 0.89, "pre-existing")
    base_dent = queries.add_defect(chk, door, "dent", (0.30, 0.30, 0.15, 0.15),
                                   30.0, 0.90, "pre-existing")

    ret = queries.create_inspection(vid, "return", previous_inspection_id=chk)
    # Case 1: same scratch, slightly shifted -> pre-existing
    c1 = queries.add_defect(ret, bumper, "scratch", (0.43, 0.64, 0.13, 0.05),
                            15.1, 0.91, "new")
    # Case 2: second scratch overlapping the same baseline scratch -> only one match allowed
    c2 = queries.add_defect(ret, bumper, "scratch", (0.42, 0.65, 0.10, 0.05),
                            12.0, 0.80, "new")
    # Case 3: same spot as the baseline dent but different type -> new
    c3 = queries.add_defect(ret, door, "scratch", (0.30, 0.30, 0.15, 0.15),
                            20.0, 0.85, "new")
    # Case 4: brand-new dent far from anything -> new
    c4 = queries.add_defect(ret, door, "dent", (0.70, 0.70, 0.10, 0.10),
                            40.0, 0.88, "new")
    # Case 5: same location as baseline scratch but on a different panel -> new
    c5 = queries.add_defect(ret, door, "scratch", (0.42, 0.65, 0.12, 0.05),
                            14.0, 0.88, "new")
    # Case 6: unmatched and low confidence -> dirt
    c6 = queries.add_defect(ret, door, "dent", (0.10, 0.10, 0.05, 0.05),
                            3.0, 0.20, "new")

    new_defects = compare_inspection(ret)

    def status_of(defect_id):
        with queries.get_connection() as conn:
            row = conn.execute(
                "SELECT status, matched_defect_id FROM defects WHERE defect_id = ?",
                (defect_id,),
            ).fetchone()
        return row["status"], row["matched_defect_id"]

    s1, s2 = status_of(c1), status_of(c2)
    # Exactly one of c1/c2 takes the baseline scratch; the other is new.
    assert {s1[0], s2[0]} == {"pre-existing", "new"}, (s1, s2)
    matched = s1 if s1[0] == "pre-existing" else s2
    assert matched[1] == base_scratch

    assert status_of(c3) == ("new", None), "different type must not match"
    assert status_of(c4) == ("new", None), "far away defect must be new"
    assert status_of(c5) == ("new", None), "different panel must not match"
    assert status_of(c6) == ("dirt", None), "low confidence unmatched must be dirt"

    new_ids = {d["defect_id"] for d in new_defects}
    assert c3 in new_ids and c4 in new_ids and c5 in new_ids
    assert c6 not in new_ids
    assert base_dent not in new_ids

    print("All comparison tests passed.")
    print("New defects sent to Module 4:", sorted(new_ids))


if __name__ == "__main__":
    run()
