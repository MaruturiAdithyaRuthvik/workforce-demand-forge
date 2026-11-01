from wdf.anomalies import inject_anomalies
from wdf.calendar import AS_OF, iso_weeks
from wdf.config import load_settings
from wdf.derived import compute_derived
from wdf.transactions import generate_sources


def test_injection_labels_all_four_types_without_leaking_labels_into_sources():
    baseline = generate_sources(41, employees=80, skills=24, projects=12, roles=8)
    sources, truth = inject_anomalies(baseline, 41)
    assert {row["issue_type"] for row in truth} == {
        "ALLOC_EXCEEDS_AVAILABILITY",
        "STALE_SKILL_TREATED_CURRENT",
        "DEMAND_DOUBLE_COUNTED",
        "OVERLAPPING_PROJECT_ASSIGNMENT",
    }
    assert not any("issue_type" in row or "ground_truth" in row for rows in sources.values() for row in rows)
    assert len(baseline["demand_lines"]) + 1 <= len(sources["demand_lines"])


def test_required_boundary_fixtures_are_in_sources():
    baseline = generate_sources(43, employees=100, skills=30, projects=12, roles=8)
    sources, _ = inject_anomalies(baseline, 43)
    assert any(row["expiry_date"] == AS_OF.isoformat() for row in sources["employee_skills"])
    assert any(row["allocation_pct"] == 1.0 and row["start_date"] == "2026-12-21" for row in sources["allocations"])
    assert any(row["start_date"] == "2026-05-11" and row["end_date"] == "2026-05-15" for row in sources["leave"])
    assert iso_weeks()[-1]["iso_week"] == "2026W53"
    assert any(row["status"] == "Cancelled" for row in sources["projects"])
    assert any(row["status"] == "Cancelled" for row in sources["allocations"])
    cancelled_projects = {
        row["project_id"] for row in sources["projects"] if row["status"] == "Cancelled"
    }
    assert any(
        row["project_id"] in cancelled_projects and row["status"] in {"Active", "Proposed"}
        for row in sources["allocations"]
    )
    derived = compute_derived(sources, load_settings().thresholds.model_dump())
    assert any(row["available_hours"] == 0 for row in derived["availability"])
    full_utilization = [
        row for row in derived["utilization"]
        if row["iso_week"] == "2026W52" and row["allocation_pct_sum"] == 1.0
    ]
    assert full_utilization


def test_injection_is_deterministic():
    base = generate_sources(47, employees=50, skills=18, projects=8, roles=8)
    assert inject_anomalies(base, 47) == inject_anomalies(base, 47)
