from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from wdf.calendar import AS_OF


def detect_anomalies(sources: dict[str, list[dict]]) -> list[dict]:
    found: dict[tuple[str, str], dict] = {}
    projects = {row["project_id"]: row for row in sources["projects"]}
    allocations = [
        row for row in sources["allocations"]
        if row["status"] in {"Proposed", "Active"}
    ]

    allocation_weeks: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in allocations:
        start, end = date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])
        monday = start - timedelta(days=start.weekday())
        while monday <= end:
            iso = monday.isocalendar()
            week = f"{iso.year}W{iso.week:02d}"
            allocation_weeks[(row["employee_id"], week)].append(row)
            monday += timedelta(days=7)

    for (employee_id, week), rows in allocation_weeks.items():
        shared = [row for row in rows if projects[row["project_id"]]["staffing_model"] == "Shared-Pool"]
        if sum(float(row["allocation_pct"]) for row in shared) > 1.0:
            for row in shared:
                found[(row["allocation_id"], "ALLOC_EXCEEDS_AVAILABILITY")] = {
                    "record_id": row["allocation_id"], "entity": "Allocation",
                    "issue_type": "ALLOC_EXCEEDS_AVAILABILITY", "issue_subtype": None,
                    "detection_rule": "ALLOC_WEEKLY_PCT_GT_1", "iso_week": week,
                }

    esk_by_id = {row["employee_skill_id"]: row for row in sources["employee_skills"]}
    for row in sources["employee_skills"]:
        if row["currency_flag"] == "Current" and date.fromisoformat(row["expiry_date"]) < AS_OF:
            found[(row["employee_skill_id"], "STALE_SKILL_TREATED_CURRENT")] = {
                "record_id": row["employee_skill_id"], "entity": "EmployeeSkill",
                "issue_type": "STALE_SKILL_TREATED_CURRENT", "issue_subtype": "FLAG_WRONG",
                "detection_rule": "SKILL_FLAG_EXPIRY_MISMATCH",
            }
    for allocation in allocations:
        basis = allocation["skill_basis_esk_id"]
        if basis and date.fromisoformat(esk_by_id[basis]["expiry_date"]) < date.fromisoformat(allocation["start_date"]):
            found[(allocation["allocation_id"], "STALE_SKILL_TREATED_CURRENT")] = {
                "record_id": allocation["allocation_id"], "entity": "Allocation",
                "issue_type": "STALE_SKILL_TREATED_CURRENT", "issue_subtype": "USED_WHILE_STALE",
                "detection_rule": "ALLOCATION_USES_STALE_SKILL",
            }

    duplicate_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in sources["demand_lines"]:
        if row["status"] == "Approved":
            duplicate_groups[(row["demand_id"], row["role_id"], row["skill_id"])].append(row)
    for rows in duplicate_groups.values():
        if len(rows) > 1:
            for row in sorted(rows, key=lambda item: item["demand_line_id"])[1:]:
                found[(row["demand_line_id"], "DEMAND_DOUBLE_COUNTED")] = {
                    "record_id": row["demand_line_id"], "entity": "DemandLine",
                    "issue_type": "DEMAND_DOUBLE_COUNTED", "issue_subtype": None,
                    "detection_rule": "DEMAND_APPROVED_BUSINESS_KEY_DUPLICATE",
                }

    for (employee_id, week), rows in allocation_weeks.items():
        if sum(float(row["allocation_pct"]) for row in rows) > 1.0:
            continue
        dedicated = [row for row in rows if projects[row["project_id"]]["staffing_model"] == "Dedicated-Team"]
        if not dedicated or len({row["project_id"] for row in rows}) < 2:
            continue
        dedicated_ids = {row["allocation_id"] for row in dedicated}
        for row in rows:
            if row["allocation_id"] not in dedicated_ids:
                found[(row["allocation_id"], "OVERLAPPING_PROJECT_ASSIGNMENT")] = {
                    "record_id": row["allocation_id"], "entity": "Allocation",
                    "issue_type": "OVERLAPPING_PROJECT_ASSIGNMENT", "issue_subtype": None,
                    "detection_rule": "DEDICATED_ASSIGNMENT_OVERLAP", "iso_week": week,
                }
    return sorted(found.values(), key=lambda row: (row["issue_type"], row["record_id"]))
