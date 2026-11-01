from collections import defaultdict
from datetime import date, timedelta

from wdf.anomalies import inject_anomalies
from wdf.calendar import AS_OF, iso_weeks
from wdf.config import load_settings
from wdf.detect import detect_anomalies
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


def test_programmatic_near_miss_fixtures_are_not_detected():
    baseline = generate_sources(71, employees=150, skills=48, projects=40, roles=12)
    sources, _truth = inject_anomalies(baseline, 71)
    projects = {row["project_id"]: row for row in sources["projects"]}
    detections = {
        (row["record_id"], row["issue_type"])
        for row in detect_anomalies(sources)
    }

    allocations_by_employee_week = defaultdict(list)
    for allocation in sources["allocations"]:
        if allocation["status"] not in {"Proposed", "Active"}:
            continue
        start = date.fromisoformat(allocation["start_date"])
        end = date.fromisoformat(allocation["end_date"])
        monday = start - timedelta(days=start.weekday())
        while monday <= end:
            allocations_by_employee_week[
                (allocation["employee_id"], f"{monday.isocalendar().year}W{monday.isocalendar().week:02d}")
            ].append(allocation)
            monday += timedelta(days=7)
    exact_capacity_ids = {
        row["allocation_id"]
        for rows in allocations_by_employee_week.values()
        if (shared := [
            row for row in rows
            if projects[row["project_id"]]["staffing_model"] == "Shared-Pool"
        ]) and len(shared) >= 2
        and sum(float(row["allocation_pct"]) for row in shared) == 1.0
        for row in shared
    }

    expiry_boundary_ids = {
        row["employee_skill_id"]
        for row in sources["employee_skills"]
        if row["expiry_date"] == AS_OF.isoformat() and row["currency_flag"] == "Current"
    }

    demand_groups = defaultdict(list)
    for row in sources["demand_lines"]:
        if row["status"] == "Approved":
            demand_groups[(row["project_id"], row["role_id"], row["skill_id"])].append(row)
    adjacent_demand_ids = set()
    for rows in demand_groups.values():
        ordered = sorted(rows, key=lambda row: row["iso_week"])
        for first, second in zip(ordered, ordered[1:]):
            if (
                first["iso_week"][:4] == second["iso_week"][:4]
                and int(second["iso_week"][-2:]) == int(first["iso_week"][-2:]) + 1
            ):
                adjacent_demand_ids.update({
                    first["demand_line_id"], second["demand_line_id"]
                })

    dedicated_by_employee = defaultdict(list)
    for row in sources["allocations"]:
        if projects[row["project_id"]]["staffing_model"] == "Dedicated-Team":
            dedicated_by_employee[row["employee_id"]].append(row)
    adjacent_dedicated_ids = set()
    for rows in dedicated_by_employee.values():
        for first in rows:
            for second in rows:
                if (
                    first["project_id"] != second["project_id"]
                    and date.fromisoformat(first["end_date"]).weekday() == 6
                    and date.fromisoformat(first["end_date"]).toordinal() + 1
                    == date.fromisoformat(second["start_date"]).toordinal()
                ):
                    adjacent_dedicated_ids.update({
                        first["allocation_id"], second["allocation_id"]
                    })

    near_misses = {
        "ALLOC_EXCEEDS_AVAILABILITY": exact_capacity_ids,
        "STALE_SKILL_TREATED_CURRENT": expiry_boundary_ids,
        "DEMAND_DOUBLE_COUNTED": adjacent_demand_ids,
        "OVERLAPPING_PROJECT_ASSIGNMENT": adjacent_dedicated_ids,
    }
    assert all(near_misses.values())
    assert all(
        (record_id, issue_type) not in detections
        for issue_type, record_ids in near_misses.items()
        for record_id in record_ids
    )
