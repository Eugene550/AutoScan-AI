from queries import (
    get_connection,
    get_checkout_for_return,
    get_defects_by_inspection,
)

# bbox_x, bbox_y in the database are assumed to be the TOP-LEFT corner.
# If Member 2 outputs the box CENTRE instead, change this to "center".
BBOX_FORMAT = "topleft"

IOU_THRESHOLD = 0.3       # minimum overlap to treat two defects as the same
DIRT_CONFIDENCE = 0.4     # unmatched defects below this confidence are marked 'dirt'


def _to_corners(defect):
    """Return (x1, y1, x2, y2) for a defect row."""
    x, y, w, h = (defect["bbox_x"], defect["bbox_y"],
                  defect["bbox_w"], defect["bbox_h"])
    if BBOX_FORMAT == "center":
        x, y = x - w / 2, y - h / 2
    return x, y, x + w, y + h


def iou(defect_a, defect_b):
    """Intersection over Union of two defects' bounding boxes (0 to 1)."""
    ax1, ay1, ax2, ay2 = _to_corners(defect_a)
    bx1, by1, bx2, by2 = _to_corners(defect_b)

    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h

    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


def compare_inspection(return_inspection_id,
                       iou_threshold=IOU_THRESHOLD,
                       dirt_confidence=DIRT_CONFIDENCE):
    """Classify every defect of a return inspection and save the result.

    Matching rules:
      - a return defect is only compared with checkout defects on the
        same panel and of the same defect type
      - the pair must have IoU >= iou_threshold
      - each checkout defect can be matched only once (best IoU first)

    Result per return defect:
      matched                          -> 'pre-existing' (+ matched_defect_id)
      unmatched, confidence < cutoff   -> 'dirt'
      unmatched                        -> 'new'

    Returns the list of defects with status 'new' (the input for Module 4).
    """
    checkout = get_checkout_for_return(return_inspection_id)
    if checkout is None:
        raise ValueError(
            f"Inspection {return_inspection_id} has no linked checkout inspection."
        )

    baseline = get_defects_by_inspection(checkout["inspection_id"])
    current = get_defects_by_inspection(return_inspection_id)

    # 1. Build all valid candidate pairs with their IoU score.
    pairs = []
    for cur in current:
        for base in baseline:
            if (cur["panel_id"] == base["panel_id"]
                    and cur["defect_type"] == base["defect_type"]):
                score = iou(cur, base)
                if score >= iou_threshold:
                    pairs.append((score, cur["defect_id"], base["defect_id"]))

    # 2. Greedy one-to-one matching, best overlap first.
    pairs.sort(reverse=True)
    matched = {}            # return defect_id -> checkout defect_id
    used_baseline = set()
    for score, cur_id, base_id in pairs:
        if cur_id not in matched and base_id not in used_baseline:
            matched[cur_id] = base_id
            used_baseline.add(base_id)

    # 3. Save the status of every return defect.
    with get_connection() as conn:
        for cur in current:
            cur_id = cur["defect_id"]
            if cur_id in matched:
                status, match_id = "pre-existing", matched[cur_id]
            elif cur["confidence"] < dirt_confidence:
                status, match_id = "dirt", None
            else:
                status, match_id = "new", None
            conn.execute(
                "UPDATE defects SET status = ?, matched_defect_id = ? WHERE defect_id = ?",
                (status, match_id, cur_id),
            )

    # 4. Return only the new defects for Module 4.
    return [d for d in get_defects_by_inspection(return_inspection_id)
            if d["status"] == "new"]
