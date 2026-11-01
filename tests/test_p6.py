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


def test_validator_accepts_structural_integrity_and_reconciles_derived():
    sources, _truth, derived, settings = _case(59)
    report = validate_data(sources, derived, settings.thresholds.model_dump())
    assert report["status"] == "PASS", report["errors"]
    assert report["checks"]["capacity_weeks_reconciled"] == 53
    assert report["checks"]["derived_tables_recomputed"]
    assert report["checks"]["approved_demand_business_key_duplicates"] == 1


def test_hard_negative_shared_pool_overlap_is_not_detected():
    sources, truth, _derived, _settings = _case(61)
    detected_ids = {row["record_id"] for row in detect_anomalies(sources)}
    positive_ids = {row["record_id"] for row in truth}
    assert positive_ids <= detected_ids
    hard_negative_allocs = [
        row for row in sources["allocations"]
        if row["allocation_pct"] < 1 and row["status"] == "Active"
    ]
    assert hard_negative_allocs
