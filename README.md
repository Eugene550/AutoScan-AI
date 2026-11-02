# AutoScan AI: Module 3 Backend

**Damage Comparison and Baseline Verification Module**
Part of *AutoScan AI: A YOLO-Fuzzy Intelligent Framework for Vehicle Damage Inspection and Cost Estimation* (BAXU3923 Workshop 2, Group 5).

## What this module does

When a rental car comes back, this module answers one question: **which damage is new?**

It stores the defects found at **checkout** (the baseline) and at **return**, compares them, and labels each return defect as:

| Status | Meaning |
|---|---|
| `pre-existing` | Already on the car at checkout, so the customer is not responsible |
| `new` | Not recorded at checkout, so it was caused during the rental |
| `dirt` | A weak detection (low confidence), treated as dirt or noise |

Only `new` defects are passed on to Module 4 (fuzzy cost estimation and PDF report).

## Where it fits

```
Module 1: Guided capture  ->  Module 2: YOLO segmentation  ->  Module 3: Comparison (this project)  ->  Module 4: Fuzzy cost + PDF
```

- **Input from Module 2:** detected defects (zone, type, bounding box, mask, surface area, confidence).
- **Output to Module 4:** new defects only, with panel, defect type, surface area and the panel's part value.

## Quick start for the reviewer

Requirements: Python 3. No extra packages are needed (only the built-in `sqlite3`).

Put all files in one folder, open a terminal in that folder and run:

```bash
# 1. Demo: shows the module working, step by step
python demo.py

# 2. Tests: checks that the comparison logic gives the correct results
python test_compare.py
```

Expected result: `demo.py` prints a checkout inspection, a return inspection, the comparison result for each defect and the new defects sent to Module 4. `test_compare.py` prints `All comparison tests passed.`

## Files

| File | Purpose |
|---|---|
| `schema.sql` | SQLite table definitions (vehicles, zones, body_panels, inspections, defects) and indexes |
| `db.py` | Creates `autoscan.db` from `schema.sql` and seeds zones, body panels and synthetic test data |
| `queries.py` | Insert and fetch functions (add vehicle, create inspection, add defect, get defects, get linked checkout) |
| `compare.py` | Comparison logic: classifies each return defect as `pre-existing`, `new` or `dirt` |
| `test_compare.py` | Automatic tests for the comparison logic, using a temporary database |
| `demo.py` | Demonstration that runs a checkout and a return through the module and prints readable results |

How they fit together: `schema.sql` defines the data, `db.py` creates the database, `queries.py` reads and writes it, `compare.py` applies the matching rules, and `test_compare.py` and `demo.py` run `compare.py` to check it and show it.

`autoscan.db` is not included. It is created by running `db.py`. `demo.py` builds its own temporary `demo.db`, so it never changes `autoscan.db`.

## What the demo shows

`demo.py` uses made-up data in a separate demo database:

1. **Checkout:** a car is recorded with two existing defects (a bumper scratch and a door dent).
2. **Return:** six detections are saved, as the YOLO model would output them.
3. **Comparison:** `compare_inspection` labels each one. The two old defects (slightly shifted between the two inspections) are matched as pre-existing, three are new (including a scratch on the spot where the old defect was a dent, because the type differs), and one low-confidence detection is marked as dirt.
4. **Output to Module 4:** the three new defects are listed with their panel, area and part value.

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
- `confidence`: the model's certainty (0 to 1)
- `status`: `pre-existing`, `new` or `dirt`
- `matched_defect_id`: the checkout defect a return defect was matched to (empty if new)

## Comparison logic (`compare.py`)

`compare_inspection(return_inspection_id)` works as follows:

1. Find the checkout inspection linked to the return inspection.
2. Compare a return defect only with checkout defects on the **same panel** and of the **same defect type**.
3. Score the match by bounding box overlap (IoU, from 0 for no overlap to 1 for identical boxes). A pair counts as the same defect if IoU >= `0.3`.
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

## Resetting the database

To reset `autoscan.db`, delete it and run `python db.py` again. Running `db.py` twice without deleting it duplicates the sample inspections and defects.

## Notes

- All data in `db.py` and `demo.py` (vehicles, inspections, defects) is synthetic and for testing only.
- The part values in `body_panels` are sample estimates in MYR for a reference car, not sourced prices. They will be replaced with researched values.
- Module 2 labels may use different class names from `defect_type`, so a class mapping will be needed.
