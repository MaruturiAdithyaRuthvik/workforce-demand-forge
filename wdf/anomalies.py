from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import numpy as np

from wdf.calendar import AS_OF, add_months
from wdf.ids import allocation_id, entity_id


def _next_number(rows: list[dict], key: str, prefix: str) -> int:
    return max((int(row[key].split("-")[-1]) for row in rows), default=0) + 1


def _append_event(
    sources: dict[str, list[dict]],
    entity_type: str,
    entity_id_value: str,
    from_state: str,
    to_state: str,
    effective_date: str,
    reason: str,
) -> None:
    events = sources["lifecycle_events"]
    events.append({
        "event_id": "",
        "entity_type": entity_type,
        "entity_id": entity_id_value,
        "from_state": from_state,
        "to_state": to_state,
        "effective_date": effective_date,
        "reason": reason,
    })
    events.sort(key=lambda event: (event["entity_type"], event["entity_id"], event["effective_date"]))
    for index, event in enumerate(events, start=1):
        event["event_id"] = entity_id("EVT", index)


def inject_anomalies(
    data: dict[str, list[dict]], seed: int, rate: float = 0.02
) -> tuple[dict[str, list[dict]], list[dict]]:
    if not 0 < rate <= 1:
        raise ValueError("Anomaly rate must be greater than zero and at most one")
    sources = deepcopy(data)
    truth = []
    projects = {row["project_id"]: row for row in sources["projects"]}
    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(99,)))

    def select_targets(rows: list[dict]) -> list[dict]:
        if not rows:
            return []
        count = min(len(rows), max(1, round(len(rows) * rate)))
        indices = sorted(int(value) for value in rng.choice(len(rows), size=count, replace=False))
        return [rows[index] for index in indices]

    shared_allocations = [
        row for row in sources["allocations"]
        if projects[row["project_id"]]["staffing_model"] == "Shared-Pool"
    ]
    if not shared_allocations:
        raise ValueError("No Shared-Pool allocation available for deterministic anomaly injection")
    allocation_targets = select_targets(shared_allocations)
    allocation_project_ids = set()
    for allocation in allocation_targets:
        previous_pct = allocation["allocation_pct"]
        allocation["allocation_pct"] = 1.25
        allocation_project_ids.add(allocation["project_id"])
        truth.append({
            "record_id": allocation["allocation_id"], "entity": "Allocation",
            "issue_type": "ALLOC_EXCEEDS_AVAILABILITY", "issue_subtype": None,
            "injected_field": "allocation_pct", "original_value": previous_pct,
            "injected_value": 1.25, "expected_detection_rule": "ALLOC_WEEKLY_PCT_GT_1",
            "expected_decision": "Reallocate", "affected_derived_ids": [],
        })

    stale_skills = [
        row for row in sources["employee_skills"]
        if date.fromisoformat(row["expiry_date"]) < AS_OF and row["currency_flag"] == "Stale"
    ]
    if not stale_skills:
        raise ValueError("No stale employee skill available for deterministic anomaly injection")
    stale_targets = select_targets(stale_skills)
    stale_target_ids = {row["employee_skill_id"] for row in stale_targets}
    for stale in stale_targets:
        prior_flag = stale["currency_flag"]
        stale["currency_flag"] = "Current"
        truth.append({
            "record_id": stale["employee_skill_id"], "entity": "EmployeeSkill",
            "issue_type": "STALE_SKILL_TREATED_CURRENT", "issue_subtype": "FLAG_WRONG",
            "injected_field": "currency_flag", "original_value": prior_flag,
            "injected_value": "Current", "expected_detection_rule": "SKILL_FLAG_EXPIRY_MISMATCH",
            "expected_decision": "Reverify", "affected_derived_ids": [],
        })

    approved = [row for row in sources["demand_lines"] if row["status"] == "Approved"]
    if not approved:
        raise ValueError("No approved demand line available for duplicate injection")
    demand_targets = select_targets(approved)
    for demand_target in demand_targets:
        duplicate = dict(demand_target)
        duplicate["demand_line_id"] = entity_id(
            "DEML", _next_number(sources["demand_lines"], "demand_line_id", "DEML")
        )
        duplicate["source"] = "ResourceRequest"
        duplicate["supersedes_line_id"] = None
        sources["demand_lines"].append(duplicate)
        sources["lifecycle_events"].append({
            "event_id": entity_id("EVT", _next_number(sources["lifecycle_events"], "event_id", "EVT")),
            "entity_type": "DemandLine", "entity_id": duplicate["demand_line_id"],
            "from_state": None, "to_state": "Approved", "effective_date": duplicate["created_on"],
            "reason": "Synthetic duplicate demand request",
        })
        truth.append({
            "record_id": duplicate["demand_line_id"], "entity": "DemandLine",
            "issue_type": "DEMAND_DOUBLE_COUNTED", "issue_subtype": None,
            "injected_field": "demand_line_id", "original_value": None,
            "injected_value": duplicate["demand_line_id"], "expected_detection_rule": "DEMAND_APPROVED_BUSINESS_KEY_DUPLICATE",
            "expected_decision": "System Admin correction", "affected_derived_ids": [],
        })

    dedicated = [
        row for row in sources["allocations"]
        if projects[row["project_id"]]["staffing_model"] == "Dedicated-Team"
        and float(row["allocation_pct"]) <= 0.75
    ]
    if not dedicated:
        raise ValueError("No Dedicated-Team allocation available for overlap injection")
    overlap_targets = select_targets(dedicated)
    overlap_project_ids = set()
    for primary in overlap_targets:
        alternate_project = next(
            row for row in sources["projects"]
            if row["project_id"] != primary["project_id"] and row["staffing_model"] == "Shared-Pool"
        )
        new_allocation = {
            **primary,
            "allocation_id": allocation_id(_next_number(sources["allocations"], "allocation_id", "ALLOC")),
            "project_id": alternate_project["project_id"],
            "allocation_pct": 0.1,
            "skill_basis_esk_id": None,
        }
        sources["allocations"].append(new_allocation)
        _append_event(sources, "Allocation", new_allocation["allocation_id"], None, "Active",
                      new_allocation["start_date"], "Synthetic overlapping project assignment")
        overlap_project_ids.update({primary["project_id"], alternate_project["project_id"]})
        truth.append({
            "record_id": new_allocation["allocation_id"], "entity": "Allocation",
            "issue_type": "OVERLAPPING_PROJECT_ASSIGNMENT", "issue_subtype": None,
            "injected_field": "project_id", "original_value": primary["project_id"],
            "injected_value": alternate_project["project_id"], "expected_detection_rule": "DEDICATED_ASSIGNMENT_OVERLAP",
            "expected_decision": "Reallocate", "affected_derived_ids": [],
        })

    # Hard negative: a Shared-Pool overlap whose combined weekly percentage stays within 100%.
    hard_negative_employee = next(
        row["employee_id"] for row in shared_allocations if float(row["allocation_pct"]) <= 0.75
    )
    hard_negative_base = next(
        row for row in shared_allocations
        if row["employee_id"] == hard_negative_employee and float(row["allocation_pct"]) <= 0.75
    )
    negative_allocation = {
        **hard_negative_base,
        "allocation_id": allocation_id(_next_number(sources["allocations"], "allocation_id", "ALLOC")),
        "project_id": next(
            row["project_id"] for row in sources["projects"]
            if row["project_id"] != hard_negative_base["project_id"]
            and row["staffing_model"] == "Shared-Pool"
        ),
        "allocation_pct": min(0.1, 1.0 - float(hard_negative_base["allocation_pct"])),
        "skill_basis_esk_id": None,
    }
    sources["allocations"].append(negative_allocation)
    _append_event(sources, "Allocation", negative_allocation["allocation_id"], None, "Active",
                  negative_allocation["start_date"], "Synthetic valid Shared-Pool overlap")

    # Fixed boundary cases are part of the valid baseline, not labeled anomalies.
    allocation_basis_ids = {row["skill_basis_esk_id"] for row in sources["allocations"]}
    boundary_skill = next(
        row for row in sources["employee_skills"]
        if row["employee_skill_id"] not in stale_target_ids
        and row["employee_skill_id"] not in allocation_basis_ids
    )
    skill = next(row for row in sources["skills"] if row["skill_id"] == boundary_skill["skill_id"])
    boundary_skill["expiry_date"] = AS_OF.isoformat()
    boundary_skill["last_verified_date"] = add_months(AS_OF, -int(skill["validity_months"])).isoformat()
    boundary_skill["currency_flag"] = "Current"

    employee = sources["employees"][0]
    leave_start = date.fromisocalendar(2026, 20, 1)
    sources["leave"].append({
        "leave_id": entity_id("LEAVE", _next_number(sources["leave"], "leave_id", "LEAVE")),
        "employee_id": employee["employee_id"], "start_date": leave_start.isoformat(),
        "end_date": (leave_start + timedelta(days=4)).isoformat(),
        "leave_type": "Annual", "status": "Approved",
    })

    boundary_week = date.fromisocalendar(2026, 52, 1)
    part_timer = next(
        row for row in sources["employees"]
        if row["fte"] < 1 and not any(
            allocation["employee_id"] == row["employee_id"]
            and date.fromisoformat(allocation["start_date"]) <= boundary_week + timedelta(days=6)
            and date.fromisoformat(allocation["end_date"]) >= boundary_week
            for allocation in sources["allocations"]
        )
    )
    project = next(row for row in sources["projects"] if row["staffing_model"] == "Shared-Pool")
    boundary_allocation = {
        "allocation_id": allocation_id(_next_number(sources["allocations"], "allocation_id", "ALLOC")),
        "employee_id": part_timer["employee_id"], "project_id": project["project_id"],
        "role_id": part_timer["role_id"], "start_date": boundary_week.isoformat(),
        "end_date": (boundary_week + timedelta(days=6)).isoformat(), "allocation_pct": 1.0,
        "skill_basis_esk_id": None, "status": "Active",
    }
    sources["allocations"].append(boundary_allocation)
    _append_event(sources, "Allocation", boundary_allocation["allocation_id"], None, "Active",
                  boundary_allocation["start_date"], "Synthetic full-time-equivalent boundary")

    active_project = next(
        (row for row in sources["projects"] if row["status"] == "Active"
         and row["project_id"] not in {
             *overlap_project_ids, *allocation_project_ids,
             negative_allocation["project_id"], project["project_id"]
         }
         and any(
             alloc["project_id"] == row["project_id"]
             and date.fromisoformat(alloc["start_date"]) <= AS_OF
             for alloc in sources["allocations"]
         )
         and any(alloc["project_id"] == row["project_id"] for alloc in sources["allocations"])),
        None,
    )
    if active_project is None:
         project_number = max(int(row["project_id"].split("-")[-1]) for row in sources["projects"]) + 1
         active_project = {
             "project_id": f"PRJ-2026-{project_number:06d}", "start_date": "2026-01-05",
             "end_date": "2026-12-31", "priority": "Medium", "staffing_model": "Shared-Pool",
             "status": "Active",
         }
         sources["projects"].append(active_project)
         _append_event(sources, "Project", active_project["project_id"], None, "Active",
                       active_project["start_date"], "Synthetic cancellation edge-case project")
         employee = sources["employees"][-1]
         fallback_allocation = {
             "allocation_id": allocation_id(_next_number(sources["allocations"], "allocation_id", "ALLOC")),
             "employee_id": employee["employee_id"], "project_id": active_project["project_id"],
             "role_id": employee["role_id"], "start_date": "2026-02-01", "end_date": "2026-10-01",
             "allocation_pct": 0.1, "skill_basis_esk_id": None, "status": "Active",
         }
         sources["allocations"].append(fallback_allocation)
         _append_event(sources, "Allocation", fallback_allocation["allocation_id"], None, "Active",
                       fallback_allocation["start_date"], "Synthetic cancellation edge-case staffing")
    if active_project:
        start = date.fromisoformat(active_project["start_date"])
        allocation_starts = [
            date.fromisoformat(row["start_date"]) for row in sources["allocations"]
            if row["project_id"] == active_project["project_id"]
        ]
        cancellation_day = max(start, max(allocation_starts))
        cancellation_date = cancellation_day.isoformat()
        preserved_allocation = next(
            row for row in sources["allocations"]
            if row["project_id"] == active_project["project_id"] and row["status"] == "Active"
        )
        prior_project_state = active_project["status"]
        active_project["status"] = "Cancelled"
        _append_event(sources, "Project", active_project["project_id"], prior_project_state, "Cancelled",
                      cancellation_date, "Synthetic mid-flight cancellation")
        for alloc in sources["allocations"]:
            if alloc["project_id"] == active_project["project_id"] and alloc["status"] == "Active":
                if alloc["allocation_id"] == preserved_allocation["allocation_id"]:
                    continue
                previous = alloc["status"]
                alloc["status"] = "Cancelled"
                if alloc["start_date"] <= cancellation_date:
                    alloc["end_date"] = min(alloc["end_date"], cancellation_date)
                _append_event(sources, "Allocation", alloc["allocation_id"], previous, "Cancelled",
                              cancellation_date, "Closed after project cancellation")

    sources["demand_lines"].sort(key=lambda row: row["demand_line_id"])
    sources["allocations"].sort(key=lambda row: row["allocation_id"])
    sources["lifecycle_events"].sort(key=lambda row: (row["event_id"]))
    truth.sort(key=lambda row: row["record_id"])
    return sources, truth
