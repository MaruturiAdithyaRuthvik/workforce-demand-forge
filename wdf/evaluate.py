from __future__ import annotations

from collections import Counter


def evaluate_detections(detections: list[dict], ground_truth: list[dict]) -> dict:
    issue_types = sorted({row["issue_type"] for row in ground_truth} | {row["issue_type"] for row in detections})
    per_type = {}
    for issue_type in issue_types:
        expected = {
            (row["record_id"], issue_type) for row in ground_truth if row["issue_type"] == issue_type
        }
        actual = {
            (row["record_id"], issue_type) for row in detections if row["issue_type"] == issue_type
        }
        true_positive = len(expected & actual)
        false_positive = len(actual - expected)
        false_negative = len(expected - actual)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_type[issue_type] = {
            "true_positive": true_positive, "false_positive": false_positive, "false_negative": false_negative,
            "precision": round(precision, 6), "recall": round(recall, 6), "f1": round(f1, 6),
        }
    confusion: Counter = Counter()
    truth_by_id = {row["record_id"]: row["issue_type"] for row in ground_truth}
    for row in detections:
        expected_type = truth_by_id.get(row["record_id"], "UNLABELED")
        confusion[(expected_type, row["issue_type"])] += 1
    return {
        "per_issue_type": per_type,
        "cross_type_confusion": [
            {"expected": expected, "detected": detected, "count": count}
            for (expected, detected), count in sorted(confusion.items())
        ],
    }
