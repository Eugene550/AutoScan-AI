# AutoScan AI: Module 3 Backend

**Damage Comparison and Baseline Verification Module**
Part of *AutoScan AI: A YOLO-Fuzzy Intelligent Framework for Vehicle Damage Inspection and Cost Estimation* (BAXU3923 Workshop 2, Group 5).

This module stores inspection data and decides whether each defect found at **return** was already present at **checkout** (pre-existing) or is newly caused (new). Only new defects are passed on to Module 4 (fuzzy cost estimation and PDF report).

## Where it fits

```
Module 1: Guided capture  ->  Module 2: YOLO segmentation  ->  Module 3: Comparison (this repo)  ->  Module 4: Fuzzy cost + PDF
```

- **Input from Module 2:** detected defects (zone, type, bounding box, mask, surface area, confidence).
- **Output to Module 4:** new defects only, with panel, defect type, surface area and the panel's part value.

## Files

| File | Purpose |
|---|---|
| `schema.sql` | SQLite table definitions (vehicles, zones, body_panels, inspections, defects) and indexes |
| `db.py` | Creates `autoscan.db` from `schema.sql` and seeds zones, body panels and synthetic test data |
| `queries.py` | Insert and fetch functions (add vehicle, create inspection, add defect, get defects, get linked checkout) |
| `compare.py` | Comparison logic: classifies each return defect as `pre-existing`, `new` or `dirt` |
| `test_compare.py` | Tests for the comparison logic, using a temporary database |
| `autoscan.db` | The SQLite database file |

(Download all the files except autoscan.db file)
## Requirements

Python 3. No extra packages are needed (only the built-in `sqlite3`).

## How to run

```bash
# 1. Create the database and seed the data (run from the folder containing schema.sql)
python db.py

# 2. Run the comparison tests (uses a temporary database, autoscan.db is not changed)
python test_compare.py
```

To reset the database, delete `autoscan.db` and run `python db.py` again. Running `db.py` twice without deleting it duplicates the sample inspections and defects.

## Database design

| Table | Description |
|---|---|
| `vehicles` | Plate number, make, model |
| `zones` | The 5 capture zones: front, left, right, rear, upper |
| `body_panels` | Panels per zone, with replacement value in MYR (`part_value`) used by Module 4 |
| `inspections` | A `checkout` or `return` inspection of a vehicle. A return links to its baseline checkout through `previous_inspection_id` |
| `defects` | One row per detected defect: panel, type, bounding box, surface area, mask and keyframe paths, confidence, status |

Defect fields:

- `defect_type`: `scratch`, `dent` or `crack`
- `bbox_x, bbox_y, bbox_w, bbox_h`: bounding box, assumed top-left corner plus width and height
- `surface_area`: defect size from the segmentation mask
- `status`: `pre-existing`, `new` or `dirt`
- `matched_defect_id`: the checkout defect a return defect was matched to (empty if new)

## Comparison logic (`compare.py`)

`compare_inspection(return_inspection_id)` works as follows:

1. Find the checkout inspection linked to the return inspection.
2. Compare a return defect only with checkout defects on the **same panel** and of the **same defect type**.
3. Score the match by bounding box overlap (IoU). A pair counts as the same defect if IoU >= `0.3`.
4. Each checkout defect can be matched only once (best overlap first).
5. Set the result:
   - matched: `pre-existing`
   - unmatched with confidence below `0.4`: `dirt`
   - unmatched: `new`
6. Return the list of `new` defects for Module 4.

Settings at the top of `compare.py`:

| Setting | Default | Meaning |
|---|---|---|
| `BBOX_FORMAT` | `"topleft"` | Set to `"center"` if YOLO outputs the box centre |
| `IOU_THRESHOLD` | `0.3` | Minimum overlap to treat two defects as the same |
| `DIRT_CONFIDENCE` | `0.4` | Unmatched defects below this confidence are marked as dirt |

The thresholds are starting values and will be tuned with real YOLO output.

## Status

- [x] Database schema and seed data
- [x] Insert and fetch functions
- [x] Comparison logic with tests on synthetic data
- [ ] Agree the defect data format with Module 2 and Module 4 (bounding box format, normalised or pixels, field names)
- [ ] Panel mapping from zone and defect position (currently `panel_id` is set manually in tests)
- [ ] Ingest function for Module 2 output
- [ ] Output function for Module 4
- [ ] Tune thresholds with real YOLO output
- [ ] Integration testing with all modules

## Notes

- All data in `db.py` (vehicles, inspections, defects, part values) is synthetic and for testing only.
- Module 2 labels may use different class names from `defect_type`, so a class mapping will be needed.
