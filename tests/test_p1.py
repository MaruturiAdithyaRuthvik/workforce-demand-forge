from datetime import date
from collections import defaultdict

from wdf.calendar import iso_weeks
from wdf.config import load_scale, load_settings
from wdf.masters import generate_masters
from wdf.transactions import generate_sources


def test_fixed_calendar_has_iso_week_53():
    weeks = iso_weeks()
    assert len(weeks) == 53
    assert weeks[-1]["iso_week"] == "2026W53"
    assert weeks[-1]["week_start"] == "2026-12-28"


def test_config_and_scale_values():
    assert load_settings().as_of.isoformat() == "2026-10-22"
    assert load_scale("starter").employees == 300
    assert load_scale("full").skills == 300


def test_master_generation_is_deterministic_and_referential():
    first = generate_masters(42, employees=30, skills=12, projects=4, roles=8)
    second = generate_masters(42, employees=30, skills=12, projects=4, roles=8)
    assert first == second
    employees = {row["employee_id"] for row in first["employees"]}
    assert all(row["manager_id"] is None or row["manager_id"] in employees for row in first["employees"])
    assert all(row["role_id"] in {r["role_id"] for r in first["roles"]} for row in first["employees"])


def test_baseline_skill_currency_is_expiry_derived_and_stale_rate_is_in_range():
    data = generate_masters(20261022, employees=300, skills=60, projects=30, roles=40)
    as_of = date(2026, 10, 22)
    for row in data["employee_skills"]:
        assert (row["currency_flag"] == "Current") == (date.fromisoformat(row["expiry_date"]) >= as_of)
    stale_rate = sum(row["currency_flag"] == "Stale" for row in data["employee_skills"]) / len(data["employee_skills"])
    assert 0.12 <= stale_rate <= 0.18


def test_skill_popularity_and_project_sizes_are_skewed():
    sources = generate_sources(20261022, employees=1200, skills=120, projects=100, roles=12)
    skill_counts = {}
    for row in sources["employee_skills"]:
        skill_counts[row["skill_id"]] = skill_counts.get(row["skill_id"], 0) + 1
    popularity = sorted(skill_counts.get(row["skill_id"], 0) for row in sources["skills"])
    assert popularity[-1] >= 3 * popularity[len(popularity) // 2]

    allocation_counts = {row["project_id"]: 0 for row in sources["projects"]}
    for row in sources["allocations"]:
        allocation_counts[row["project_id"]] += 1
    project_sizes = sorted(allocation_counts.values())
    assert project_sizes[-1] >= 2 * project_sizes[len(project_sizes) // 2]
    assert project_sizes[int(0.9 * (len(project_sizes) - 1))] > project_sizes[len(project_sizes) // 2]


def test_baseline_allocations_include_legal_shared_overlaps_and_sequential_work():
    sources = generate_sources(53, employees=150, skills=24, projects=20, roles=8)
    projects = {row["project_id"]: row for row in sources["projects"]}
    by_employee = defaultdict(list)
    for allocation in sources["allocations"]:
        by_employee[allocation["employee_id"]].append(allocation)

    assert len(sources["allocations"]) >= 1.5 * len(sources["employees"])
    overlapping_employees = set()
    for rows in by_employee.values():
        for index, first in enumerate(rows):
            for second in rows[index + 1:]:
                overlaps = (
                    first["start_date"] <= second["end_date"]
                    and second["start_date"] <= first["end_date"]
                )
                if not overlaps:
                    continue
                overlapping_employees.add(first["employee_id"])
                assert projects[first["project_id"]]["staffing_model"] == "Shared-Pool"
                assert projects[second["project_id"]]["staffing_model"] == "Shared-Pool"
                concurrent = [
                    row for row in rows
                    if row["start_date"] <= min(first["end_date"], second["end_date"])
                    and row["end_date"] >= max(first["start_date"], second["start_date"])
                ]
                assert sum(row["allocation_pct"] for row in concurrent) <= 1.0
    overlap_share = len(overlapping_employees) / len(sources["employees"])
    assert 0.15 <= overlap_share <= 0.25
    assert sum(len(rows) >= 2 for rows in by_employee.values()) >= 0.5 * len(sources["employees"])
    assert any(
        len(rows) >= 2 and employee_id not in overlapping_employees
        for employee_id, rows in by_employee.items()
    )
