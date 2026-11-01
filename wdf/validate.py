from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from wdf.calendar import AS_OF, add_months
from wdf.config import load_settings

ID_PATTERNS = {
    "roles": (r"ROLE-\d{4}", "role_id"),
    "skills": (r"SKL-\d{6}", "skill_id"),
    "employees": (r"EMP-\d{6}", "employee_id"),
    "projects": (r"PRJ-2026-\d{6}", "project_id"),
    "employee_skills": (r"ESK-\d{6}", "employee_skill_id"),
    "demand_lines": (r"DEML-\d{6}", "demand_line_id"),
    "allocations": (r"ALLOC-2026-\d{6}", "allocation_id"),
    "availability": (r"AVL-\d{6}", "availability_id"),
    "leave": (r"LEAVE-\d{6}", "leave_id"),
    "training": (r"TRN-\d{6}", "training_id"),
    "gap_analysis": (r"GAP-2026W\d{2}-\d{6}", "gap_id"),
    "gap_actions": (r"GACT-\d{6}", "gap_action_id"),
    "lifecycle_events": (r"EVT-\d{6}", "event_id"),
}

ENUMS = {
    ("roles", "family"): {"Engineering", "Data", "QA", "Design", "PM", "DevOps", "Security", "Support"},
    ("skills", "category"): {"Technical", "Domain", "Leadership", "Platform", "Compliance"},
    ("employees", "employment_type"): {"FT", "PT"},
    ("employees", "status"): {"Active", "Inactive"},
    ("employee_skills", "currency_flag"): {"Current", "Stale"},
    ("projects", "priority"): {"Low", "Medium", "High", "Critical"},
    ("projects", "staffing_model"): {"Shared-Pool", "Dedicated-Team"},
    ("projects", "demand_profile"): {"ramp_up", "steady", "ramp_down"},
    ("projects", "status"): {"Planned", "Active", "Completed", "Cancelled"},
    ("demand_lines", "source"): {"PlanTool", "ResourceRequest"},
    ("demand_lines", "status"): {"Draft", "Approved", "Superseded"},
    ("leave", "leave_type"): {"Annual", "Sick", "Care", "Other"},
    ("leave", "status"): {"Approved", "Pending", "Rejected"},
    ("allocations", "status"): {"Proposed", "Active", "Completed", "Cancelled"},
    ("training", "status"): {"Planned", "Enrolled", "Completed", "Failed", "Cancelled"},
    ("gap_analysis", "risk_level"): {"Covered", "Low", "Medium", "High"},
    ("gap_actions", "action_type"): {"Reverify", "Train", "Hire", "Reallocate", "Contract"},
    ("gap_actions", "owner_actor"): {"Employee", "Manager", "HR Partner", "IT/Ops Partner", "System Admin"},
    ("gap_actions", "status"): {"Proposed", "Approved", "InProgress", "Done", "Rejected", "Escalated"},
    ("lifecycle_events", "entity_type"): {"Employee", "Project", "Allocation", "Training", "DemandLine"},
}


def _transition_allowed(entity_type: str, previous: str | None, current: str) -> bool:
    if previous is None:
        return True
    transitions = {
        "Employee": {"Active": {"Inactive"}, "Inactive": {"Active"}},
        "Project": {"Planned": {"Active", "Cancelled"}, "Active": {"Completed", "Cancelled"}},
        "Allocation": {"Proposed": {"Active", "Cancelled"}, "Active": {"Completed", "Cancelled"}},
        "Training": {
            "Planned": {"Enrolled", "Cancelled"}, "Enrolled": {"Completed", "Failed", "Cancelled"}
        },
        "DemandLine": {"Draft": {"Approved", "Superseded"}, "Approved": {"Superseded"}},
    }
    return current in transitions.get(entity_type, {}).get(previous, set())


def validate_data(
    sources: dict[str, list[dict]],
    derived: dict[str, list[dict]] | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict:
    settings = load_settings()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}
    tables = {**sources, **(derived or {})}
    primary_keys = {
        "roles": "role_id", "skills": "skill_id", "employees": "employee_id",
        "projects": "project_id", "role_skills": "role_skill_id",
        "employee_skills": "employee_skill_id", "demand_plans": "demand_id",
        "demand_lines": "demand_line_id", "leave": "leave_id", "allocations": "allocation_id",
        "training": "training_id", "lifecycle_events": "event_id", "availability": "availability_id",
        "utilization": "utilization_id", "supply": None, "gap_analysis": "gap_id",
        "gap_actions": "gap_action_id",
    }
    for table, rows in tables.items():
        key = primary_keys.get(table)
        if key:
            values = [row.get(key) for row in rows]
            if len(values) != len(set(values)):
                errors.append(f"{table}.{key} contains duplicates")
        if table in ID_PATTERNS:
            pattern, key = ID_PATTERNS[table]
            if any(not isinstance(row.get(key), str) or re.fullmatch(pattern, row[key]) is None for row in rows):
                errors.append(f"{table}.{key} has invalid identifier format")
        for (enum_table, field), values in ENUMS.items():
            if enum_table == table and any(row.get(field) not in values for row in rows):
                errors.append(f"{table}.{field} contains an unsupported enum value")
    if any(
        float(row["fte"]) not in settings.master_generation.fte_values
        for row in sources["employees"]
    ):
        errors.append("employees.fte contains a value outside the supported FTE set")
    checks["primary_key_tables"] = len(primary_keys)
    checks["row_counts"] = {name: len(rows) for name, rows in sorted(tables.items())}

    def fk(source: str, field: str, target: str, target_field: str) -> None:
        available = {row.get(target_field) for row in tables.get(target, [])}
        missing = [row.get(field) for row in tables.get(source, []) if row.get(field) is not None and row.get(field) not in available]
        if missing:
            errors.append(f"{source}.{field} has {len(missing)} invalid {target}.{target_field} references")

    relationships = [
        ("role_skills", "role_id", "roles", "role_id"), ("role_skills", "skill_id", "skills", "skill_id"),
        ("employees", "role_id", "roles", "role_id"), ("employees", "manager_id", "employees", "employee_id"),
        ("employee_skills", "employee_id", "employees", "employee_id"),
        ("employee_skills", "skill_id", "skills", "skill_id"),
        ("demand_plans", "project_id", "projects", "project_id"),
        ("demand_lines", "demand_id", "demand_plans", "demand_id"),
        ("demand_lines", "project_id", "projects", "project_id"),
        ("demand_lines", "role_id", "roles", "role_id"),
        ("demand_lines", "skill_id", "skills", "skill_id"),
        ("demand_lines", "supersedes_line_id", "demand_lines", "demand_line_id"),
        ("leave", "employee_id", "employees", "employee_id"),
        ("allocations", "employee_id", "employees", "employee_id"),
        ("allocations", "project_id", "projects", "project_id"),
        ("allocations", "role_id", "roles", "role_id"),
        ("allocations", "skill_basis_esk_id", "employee_skills", "employee_skill_id"),
        ("training", "employee_id", "employees", "employee_id"),
        ("training", "skill_id", "skills", "skill_id"),
        ("availability", "employee_id", "employees", "employee_id"),
        ("utilization", "employee_id", "employees", "employee_id"),
        ("supply", "role_id", "roles", "role_id"), ("supply", "skill_id", "skills", "skill_id"),
        ("gap_analysis", "role_id", "roles", "role_id"), ("gap_analysis", "skill_id", "skills", "skill_id"),
        ("gap_actions", "gap_id", "gap_analysis", "gap_id"),
        ("gap_actions", "source_utilization_id", "utilization", "utilization_id"),
    ]
    for source, field, target, target_field in relationships:
        fk(source, field, target, target_field)
    allocation_ids = {row["allocation_id"] for row in sources["allocations"]}
    if any(
        allocation_id not in allocation_ids
        for action in (derived or {}).get("gap_actions", [])
        for allocation_id in action.get("source_allocation_ids", [])
    ):
        errors.append("gap_actions.source_allocation_ids has invalid allocation references")

    demand_keys = Counter(
        (row["demand_id"], row["role_id"], row["skill_id"])
        for row in sources["demand_lines"] if row["status"] == "Approved"
    )
    duplicate_count = sum(count - 1 for count in demand_keys.values() if count > 1)
    if duplicate_count:
        warnings.append(f"{duplicate_count} approved demand business-key duplicate(s), surfaced for anomaly detection")
    checks["approved_demand_business_key_duplicates"] = duplicate_count
    skills_by_id = {row["skill_id"]: row for row in sources["skills"]}
    currency_mismatches = 0
    for row in sources["employee_skills"]:
        verified = date.fromisoformat(row["last_verified_date"])
        expected_expiry = add_months(
            verified, int(skills_by_id[row["skill_id"]]["validity_months"])
        )
        if expected_expiry.isoformat() != row["expiry_date"]:
            errors.append(f"employee skill expiry does not match validity for {row['employee_skill_id']}")
        expected_flag = "Current" if date.fromisoformat(row["expiry_date"]) >= AS_OF else "Stale"
        currency_mismatches += row["currency_flag"] != expected_flag
    if currency_mismatches:
        warnings.append(
            f"{currency_mismatches} employee skill currency flag(s) disagree with expiry and are detector cases"
        )
    checks["employee_skill_currency_flag_mismatches"] = currency_mismatches

    for table in ("allocations", "leave", "training", "projects", "employee_skills", "demand_lines"):
        for row in sources.get(table, []):
            for start_field, end_field in [
                ("start_date", "end_date"),
                ("last_verified_date", "expiry_date"),
            ]:
                if start_field in row and end_field in row and date.fromisoformat(row[start_field]) > date.fromisoformat(row[end_field]):
                    errors.append(f"{table} has reversed dates for {row}")
                    break

    employees = {row["employee_id"]: row for row in sources["employees"]}
    capacity_by_week: dict[str, float] = defaultdict(float)
    for row in (derived or {}).get("availability", []):
        capacity_by_week[row["iso_week"]] += float(row["capacity_hours"])
        if abs(float(row["available_hours"]) - (
            float(row["capacity_hours"]) - float(row["leave_hours"]) - float(row["holiday_hours"])
        )) > 0.0001:
            errors.append(f"availability arithmetic mismatch at {row['availability_id']}")
    expected_capacity = sum(
        float(row["fte"]) * settings.work_calendar.weekly_hours
        for row in employees.values()
    )
    if any(abs(value - expected_capacity) > 0.0001 for value in capacity_by_week.values()):
        errors.append("weekly capacity does not reconcile to employee FTE")
    checks["capacity_weeks_reconciled"] = len(capacity_by_week)

    if derived and thresholds:
        from wdf.derived import compute_derived

        recomputed = compute_derived(sources, thresholds)
        derived_keys = {
            "availability": "availability_id", "utilization": "utilization_id",
            "supply": ("iso_week", "role_id", "skill_id"), "gap_analysis": "gap_id",
            "gap_actions": "gap_action_id",
        }
        for table in ("availability", "utilization", "supply", "gap_analysis", "gap_actions"):
            expected_rows = derived.get(table, [])
            actual_rows = recomputed.get(table, [])
            key = derived_keys[table]

            def key_values(row: dict) -> Any:
                return tuple(row[field] for field in key) if isinstance(key, tuple) else row[key]

            if len(expected_rows) != len(actual_rows):
                errors.append(f"{table} row count does not recompute")
            elif {key_values(row): row for row in actual_rows} != {key_values(row): row for row in expected_rows}:
                errors.append(f"{table} does not reconcile to source tables")
        checks["derived_tables_recomputed"] = True

    current_state = {}
    state_tables = {
        "Employee": ("employees", "employee_id"), "Project": ("projects", "project_id"),
        "Allocation": ("allocations", "allocation_id"), "Training": ("training", "training_id"),
        "DemandLine": ("demand_lines", "demand_line_id"),
    }
    for event in sources["lifecycle_events"]:
        key = (event["entity_type"], event["entity_id"])
        if event["entity_type"] in state_tables:
            target_table, target_field = state_tables[event["entity_type"]]
            if event["entity_id"] not in {row[target_field] for row in sources[target_table]}:
                errors.append(f"lifecycle event references missing entity {key}")
        previous = current_state.get(key)
        if event["from_state"] != previous:
            errors.append(f"lifecycle from_state mismatch for {key}")
        if not _transition_allowed(event["entity_type"], previous, event["to_state"]):
            errors.append(f"illegal lifecycle transition for {key}: {previous} -> {event['to_state']}")
        current_state[key] = event["to_state"]
    for entity_type, (table, field) in state_tables.items():
        for row in sources[table]:
            if current_state.get((entity_type, row[field])) != row["status"]:
                errors.append(f"current lifecycle state mismatch for {entity_type} {row[field]}")
    checks["lifecycle_entities_reconciled"] = len(current_state)
    checks["foreign_key_relationships_checked"] = len(relationships)
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }
