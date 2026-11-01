from collections import defaultdict

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
