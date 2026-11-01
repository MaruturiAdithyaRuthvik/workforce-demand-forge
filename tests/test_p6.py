from wdf.anomalies import inject_anomalies
from wdf.config import load_settings
from wdf.derived import compute_derived
from wdf.detect import detect_anomalies
from wdf.evaluate import evaluate_detections
from wdf.transactions import generate_sources
from wdf.validate import validate_data


def _case(seed=53):
    baseline = generate_sources(seed, employees=120, skills=30, projects=16, roles=8)
    sources, truth = inject_anomalies(baseline, seed)
    settings = load_settings()
    derived = compute_derived(sources, settings.thresholds.model_dump())
    return sources, truth, derived, settings


def test_all_injected_issue_types_detect_and_evaluate():
    sources, truth, _derived, _settings = _case()
    detections = detect_anomalies(sources)
    metrics = evaluate_detections(detections, truth)["per_issue_type"]
    for issue_type in {row["issue_type"] for row in truth}:
        assert metrics[issue_type]["recall"] == 1.0
        assert metrics[issue_type]["precision"] == 1.0


def test_detection_rules_hold_on_second_seed():
    for seed in (20261022, 20261023):
        sources, truth, _derived, _settings = _case(seed)
        metrics = evaluate_detections(detect_anomalies(sources), truth)["per_issue_type"]
        assert all(
            values["precision"] == values["recall"] == values["f1"] == 1.0
            for values in metrics.values()
        ), (seed, metrics)


def test_validator_accepts_structural_integrity_and_reconciles_derived():
    sources, _truth, derived, settings = _case(59)
    report = validate_data(sources, derived, settings.thresholds.model_dump())
    assert report["status"] == "PASS", report["errors"]
    assert report["checks"]["capacity_weeks_reconciled"] == 53
    assert report["checks"]["derived_tables_recomputed"]
    assert report["checks"]["approved_demand_business_key_duplicates"] >= 1


def test_hard_negative_shared_pool_overlap_is_not_detected():
    sources, truth, _derived, _settings = _case(61)
    detections = detect_anomalies(sources)
    detected_ids = {row["record_id"] for row in detections}
    positive_ids = {row["record_id"] for row in truth}
    assert positive_ids <= detected_ids
    projects = {row["project_id"]: row for row in sources["projects"]}
    hard_negative_allocs = [
        row for row in sources["allocations"]
        if row["allocation_pct"] < 1 and row["status"] == "Active"
        and projects[row["project_id"]]["staffing_model"] == "Shared-Pool"
    ]
    valid_overlap = next(
        (row, other) for row in hard_negative_allocs for other in hard_negative_allocs
        if row["employee_id"] == other["employee_id"] and row["project_id"] != other["project_id"]
        and row["allocation_id"] != other["allocation_id"]
        and row["allocation_pct"] + other["allocation_pct"] <= 1
    )
    detection_ids = {
        row["record_id"] for row in detections
        if row["issue_type"] in {"ALLOC_EXCEEDS_AVAILABILITY", "OVERLAPPING_PROJECT_ASSIGNMENT"}
    }
    assert all(row["allocation_id"] not in detection_ids for row in valid_overlap)
