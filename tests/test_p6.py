import shutil

from wdf.anomalies import inject_anomalies
from wdf.config import load_settings
from wdf.derived import compute_derived
from wdf.detect import detect_anomalies
from wdf.evaluate import evaluate_detections
from wdf.pipeline import _attach_derived_trace_ids, run_detection, run_generate
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


def test_detection_runs_without_ground_truth(tmp_path):
    run_generate(tmp_path, "starter", 20261022, include_heldout=False)
    shutil.rmtree(tmp_path / "ground_truth")

    detections = run_detection(tmp_path)

    assert detections
    assert (tmp_path / "detections.json").is_file()


def test_derived_trace_ids_match_line_skill_and_allocation_records():
    sources = {
        "demand_lines": [{
            "demand_line_id": "DEML-000001", "iso_week": "2026W01",
            "role_id": "ROLE-0001", "skill_id": "SKL-000001",
        }],
        "employee_skills": [{
            "employee_skill_id": "ESK-000001", "employee_id": "EMP-000001",
            "skill_id": "SKL-000001",
        }],
        "employees": [{"employee_id": "EMP-000001", "role_id": "ROLE-0001"}],
        "allocations": [{
            "allocation_id": "ALLOC-2026-000001", "employee_id": "EMP-000001",
            "start_date": "2026-01-01", "end_date": "2026-01-07",
        }],
    }
    ground_truth = [
        {"record_id": "DEML-000001"},
        {"record_id": "ESK-000001"},
        {"record_id": "ALLOC-2026-000001"},
    ]
    derived = {
        "gap_analysis": [
            {
                "gap_id": "GAP-1", "iso_week": "2026W01",
                "role_id": "ROLE-0001", "skill_id": "SKL-000001",
            },
            {
                "gap_id": "GAP-2", "iso_week": "2026W02",
                "role_id": "ROLE-0001", "skill_id": "SKL-000001",
            },
            {
                "gap_id": "GAP-3", "iso_week": "2026W01",
                "role_id": "ROLE-0001", "skill_id": "SKL-000002",
            },
        ],
        "utilization": [
            {
                "utilization_id": "UTL-EMP1-2026W01",
                "employee_id": "EMP-000001", "iso_week": "2026W01",
            },
            {
                "utilization_id": "UTL-EMP1-2026W02",
                "employee_id": "EMP-000001", "iso_week": "2026W02",
            },
            {
                "utilization_id": "UTL-EMP2-2026W01",
                "employee_id": "EMP-000002", "iso_week": "2026W01",
            },
        ],
    }

    _attach_derived_trace_ids(sources, ground_truth, derived)

    assert [row["affected_derived_ids"] for row in ground_truth] == [
        ["GAP-1"],
        ["GAP-1", "GAP-2"],
        ["UTL-EMP1-2026W01", "UTL-EMP1-2026W02"],
    ]
