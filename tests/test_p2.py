from collections import defaultdict
from datetime import date

from wdf.config import load_settings
from wdf.derived import compute_derived
from wdf.transactions import generate_sources


def test_source_generation_is_deterministic_and_foreign_keys_resolve():
    first = generate_sources(11, employees=30, skills=12, projects=4, roles=8)
    assert first == generate_sources(11, employees=30, skills=12, projects=4, roles=8)
    employee_ids = {row["employee_id"] for row in first["employees"]}
    project_ids = {row["project_id"] for row in first["projects"]}
    skill_ids = {row["skill_id"] for row in first["skills"]}
    assert all(row["employee_id"] in employee_ids for row in first["leave"])
    assert all(row["project_id"] in project_ids for row in first["demand_plans"])
    assert all(row["skill_id"] in skill_ids for row in first["demand_lines"])


def test_approved_demand_business_key_is_unique_except_revisions():
    data = generate_sources(17, employees=40, skills=16, projects=5, roles=8)
    keys = [(row["demand_id"], row["role_id"], row["skill_id"])
            for row in data["demand_lines"] if row["status"] == "Approved"]
    assert len(keys) == len(set(keys))
    assert any(row["status"] == "Superseded" for row in data["demand_lines"])


def test_lifecycle_events_cover_current_transaction_states():
    data = generate_sources(19, employees=20, skills=10, projects=3, roles=8)
    states = defaultdict(list)
    for event in data["lifecycle_events"]:
        states[(event["entity_type"], event["entity_id"])].append(event["to_state"])
    for entity_type, table, key in [
        ("Allocation", "allocations", "allocation_id"),
        ("Training", "training", "training_id"),
        ("DemandLine", "demand_lines", "demand_line_id"),
    ]:
        assert all(states[(entity_type, row[key])][-1] == row["status"] for row in data[table])
    superseded_line = next(row for row in data["demand_lines"] if row["status"] == "Superseded")
    revision_history = [
        row for row in data["lifecycle_events"]
        if row["entity_type"] == "DemandLine" and row["entity_id"] == superseded_line["demand_line_id"]
    ]
    assert [row["to_state"] for row in revision_history] == ["Approved", "Superseded"]


def test_leave_covers_all_months_has_seasonality_and_creates_full_weeks_off():
    sources = generate_sources(59, employees=300, skills=24, projects=20, roles=8)
    employee_count = len(sources["employees"])
    employees_with_leave = {row["employee_id"] for row in sources["leave"]}
    assert 0.7 <= len(employees_with_leave) / employee_count <= 0.9

    month_counts = defaultdict(int)
    durations = defaultdict(int)
    for row in sources["leave"]:
        month_counts[int(row["start_date"][5:7])] += 1
        duration = (
            date.fromisoformat(row["end_date"]) - date.fromisoformat(row["start_date"])
        ).days + 1
        durations[duration] += 1
    assert set(month_counts) == set(range(1, 13))
    assert (month_counts[7] + month_counts[8] + month_counts[12]) / len(sources["leave"]) > 0.3
    assert any(duration <= 3 for duration in durations)
    assert durations[5] > 0

    derived = compute_derived(sources, load_settings().thresholds.model_dump())
    zero_share = sum(row["available_hours"] == 0 for row in derived["availability"]) / len(
        derived["availability"]
    )
    assert 0.02 <= zero_share <= 0.04


def test_project_demand_profiles_shape_fte_without_removing_zero_demand_weeks():
    sources = generate_sources(61, employees=150, skills=36, projects=80, roles=8)
    projects = sources["projects"]
    assert {row["demand_profile"] for row in projects} == {"ramp_up", "steady", "ramp_down"}
    lines_by_project = defaultdict(list)
    for row in sources["demand_lines"]:
        if row["status"] == "Approved":
            lines_by_project[row["project_id"]].append(row)

    averages = {}
    for profile in ("ramp_up", "steady", "ramp_down"):
        candidates = [
            row for row in projects
            if row["demand_profile"] == profile
            and (date.fromisoformat(row["end_date"]) - date.fromisoformat(row["start_date"])).days >= 180
        ]
        project = max(
            candidates,
            key=lambda row: date.fromisoformat(row["end_date"]) - date.fromisoformat(row["start_date"]),
        )
        start = date.fromisoformat(project["start_date"])
        duration = (date.fromisoformat(project["end_date"]) - start).days
        thirds = [[], [], []]
        for line in lines_by_project[project["project_id"]]:
            week = int(line["iso_week"][-2:])
            week_start = date.fromisocalendar(2026, week, 1)
            third = min(2, max(0, 3 * (week_start - start).days // max(duration, 1)))
            thirds[third].append(line["required_fte"])
        assert all(third for third in thirds)
        averages[profile] = [sum(third) / len(third) for third in thirds]

    assert averages["ramp_up"][0] < averages["ramp_up"][2]
    assert averages["ramp_down"][0] > averages["ramp_down"][2]
    assert any(row["status"] == "Superseded" for row in sources["demand_lines"])
    assert any(row["status"] == "Approved" and row["supersedes_line_id"]
               for row in sources["demand_lines"])
    possible_project_weeks = sum(
        (date.fromisoformat(project["end_date"]) - date.fromisoformat(project["start_date"])).days // 7 + 1
        for project in projects
    )
    assert len(sources["demand_plans"]) < possible_project_weeks
