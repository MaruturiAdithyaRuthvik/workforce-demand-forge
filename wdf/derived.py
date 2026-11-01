from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from wdf.calendar import AS_OF, iso_weeks
from wdf.ids import entity_id


ACTORS = ["Employee", "Manager", "HR Partner", "IT/Ops Partner", "System Admin"]


def _week_days(week_start: date) -> list[date]:
    return [week_start + timedelta(days=offset) for offset in range(7)]


def compute_derived(
    sources: dict[str, list[dict]],
    thresholds: dict[str, float],
) -> dict[str, list[dict]]:
    weeks = iso_weeks()
    employee_by_id = {row["employee_id"]: row for row in sources["employees"]}
    leave_by_employee: dict[str, list[dict]] = defaultdict(list)
    for row in sources["leave"]:
        leave_by_employee[row["employee_id"]].append(row)
    holidays = {date.fromisoformat(row["holiday_date"]) for row in sources["holidays"]}

    availability = []
    avail_by_key: dict[tuple[str, str], dict] = {}
    availability_counter = 1
    for employee in sources["employees"]:
        fte = employee["fte"]
        capacity = 40.0 * fte
        for week in weeks:
            start = date.fromisoformat(str(week["week_start"]))
            days = _week_days(start)
            leave_days = set()
            for leave in leave_by_employee[employee["employee_id"]]:
                leave_start, leave_end = date.fromisoformat(leave["start_date"]), date.fromisoformat(leave["end_date"])
                leave_days.update(day for day in days if leave_start <= day <= leave_end and day.weekday() < 5)
            holiday_days = {day for day in days if day in holidays and day.weekday() < 5}
            leave_hours = min(capacity, len(leave_days) * 8.0 * fte)
            holiday_hours = min(max(0.0, capacity - leave_hours), len(holiday_days) * 8.0 * fte)
            row = {
                "availability_id": entity_id("AVL", availability_counter),
                "employee_id": employee["employee_id"],
                "iso_week": week["iso_week"],
                "capacity_hours": round(capacity, 4),
                "leave_hours": round(leave_hours, 4),
                "holiday_hours": round(holiday_hours, 4),
                "available_hours": round(max(0.0, capacity - leave_hours - holiday_hours), 4),
            }
            availability.append(row)
            availability_counter += 1
            avail_by_key[(employee["employee_id"], str(week["iso_week"]))] = row

    employee_skills_by_employee: dict[str, list[dict]] = defaultdict(list)
    skilled_employees: dict[tuple[str, str], list[tuple[dict, dict]]] = defaultdict(list)
    for row in sources["employee_skills"]:
        employee_skills_by_employee[row["employee_id"]].append(row)
        employee = employee_by_id[row["employee_id"]]
        skilled_employees[(employee["role_id"], row["skill_id"])].append((employee, row))
    allocations_by_employee: dict[str, list[dict]] = defaultdict(list)
    for row in sources["allocations"]:
        allocations_by_employee[row["employee_id"]].append(row)

    utilization = []
    for employee in sources["employees"]:
        for week in weeks:
            week_start = date.fromisoformat(str(week["week_start"]))
            week_end = week_start + timedelta(days=6)
            applicable = [
                allocation for allocation in allocations_by_employee[employee["employee_id"]]
                if allocation["status"] in {"Proposed", "Active"}
                and date.fromisoformat(allocation["start_date"]) <= week_end
                and date.fromisoformat(allocation["end_date"]) >= week_start
            ]
            pct = sum(float(row["allocation_pct"]) for row in applicable)
            avail = avail_by_key[(employee["employee_id"], str(week["iso_week"]))]
            hours = pct * float(avail["available_hours"])
            available_hours = float(avail["available_hours"])
            utilization.append({
                "utilization_id": f"UTL-{employee['employee_id'][4:]}-{week['iso_week']}",
                "employee_id": employee["employee_id"],
                "iso_week": week["iso_week"],
                "allocation_pct_sum": round(pct, 4),
                "allocated_hours": round(hours, 4),
                "utilization_available": round(hours / available_hours, 6) if available_hours else None,
                "utilization_capacity": round(hours / float(avail["capacity_hours"]), 6)
                if float(avail["capacity_hours"]) else None,
                "flag": "ZERO_AVAILABILITY" if available_hours == 0 else None,
            })

    approved_demand = [row for row in sources["demand_lines"] if row["status"] == "Approved"]
    group_demand: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in approved_demand:
        group_demand[(row["iso_week"], row["role_id"], row["skill_id"])].append(row)
    skill_supply_rows = []
    supply_by_key = {}
    for (week, role_id, skill_id), lines in sorted(group_demand.items()):
        minimum = min(int(row["min_proficiency"]) for row in lines)
        matched: list[str] = []
        hours = 0.0
        for employee, skill_row in skilled_employees[(role_id, skill_id)]:
            if skill_row["proficiency"] >= minimum and skill_row["currency_flag"] == "Current" and date.fromisoformat(skill_row["expiry_date"]) >= AS_OF:
                matched.append(skill_row["employee_skill_id"])
                hours += float(avail_by_key[(employee["employee_id"], week)]["available_hours"])
        supply_row = {
            "iso_week": week, "role_id": role_id, "skill_id": skill_id,
            "supply_fte": round(hours / 40.0, 4),
            "supporting_esk_ids": sorted(matched),
        }
        skill_supply_rows.append(supply_row)
        supply_by_key[(week, role_id, skill_id)] = supply_row

    gaps = []
    actions = []
    action_counter = 1
    hire_count = 0
    for index, (key, lines) in enumerate(sorted(group_demand.items()), start=1):
        week, role_id, skill_id = key
        demand_fte = sum(float(row["required_fte"]) for row in lines)
        supplied = supply_by_key[key]
        gap_fte = demand_fte - float(supplied["supply_fte"])
        if gap_fte >= float(thresholds["medium_gap_fte"]):
            risk = "High"
        elif gap_fte >= float(thresholds["low_gap_fte"]):
            risk = "Medium"
        elif gap_fte > 0:
            risk = "Low"
        else:
            risk = "Covered"
        gap_id = f"GAP-{week}-{index:06d}"
        gaps.append({
            "gap_id": gap_id, "iso_week": week, "role_id": role_id, "skill_id": skill_id,
            "demand_fte": round(demand_fte, 4), "supply_fte": supplied["supply_fte"],
            "gap_fte": round(gap_fte, 4), "risk_level": risk,
            "source_demand_line_ids": sorted(row["demand_line_id"] for row in lines),
            "supporting_esk_ids": supplied["supporting_esk_ids"],
        })
        if gap_fte <= 0:
            continue
        candidate_employee_id = None
        candidate_skill_id = None
        action_type, rule_id, actor = "", "", ""
        if gap_fte >= float(thresholds["medium_gap_fte"]):
            action_type, rule_id, actor = "Hire", "GAP_HIRE_LARGE", "HR Partner"
            assumptions = f"GAP_HIRE_LARGE: gap_fte={gap_fte:.4f} >= medium_gap_fte={thresholds['medium_gap_fte']}."
        elif gap_fte >= float(thresholds["low_gap_fte"]):
            adjacent = next(
                ((employee, skill_row) for employee in sources["employees"]
                 if employee["role_id"] == role_id
                 for skill_row in employee_skills_by_employee[employee["employee_id"]]
                 if skill_row["skill_id"] != skill_id and skill_row["proficiency"] >= 2),
                None,
            )
            if adjacent:
                employee, adjacent_skill = adjacent
                candidate_employee_id, candidate_skill_id = employee["employee_id"], adjacent_skill["skill_id"]
                action_type, rule_id, actor = "Train", "GAP_TRAIN_MEDIUM", "Manager"
                assumptions = f"GAP_TRAIN_MEDIUM: gap_fte={gap_fte:.4f}; adjacent skill {candidate_skill_id}; thresholds low={thresholds['low_gap_fte']}, medium={thresholds['medium_gap_fte']}."
        else:
            stale = next(
                ((employee, skill_row) for employee in sources["employees"]
                 if employee["role_id"] == role_id
                 for skill_row in employee_skills_by_employee[employee["employee_id"]]
                 if skill_row["skill_id"] == skill_id and skill_row["proficiency"] >= min(
                     int(row["min_proficiency"]) for row in lines
                 ) and skill_row["currency_flag"] == "Stale"),
                None,
            )
            if stale:
                employee, _skill_row = stale
                candidate_employee_id = employee["employee_id"]
                action_type, rule_id, actor = "Reverify", "GAP_REVERIFY_SMALL", "Employee"
                assumptions = f"GAP_REVERIFY_SMALL: qualified stale skill; gap_fte={gap_fte:.4f} < low_gap_fte={thresholds['low_gap_fte']}."
        if not action_type:
            continue
        failed_training = any(
            training["employee_id"] == candidate_employee_id
            and training["skill_id"] == skill_id
            and training["status"] == "Failed"
            for training in sources["training"]
        )
        if action_type == "Train" and failed_training:
            prior_rule = rule_id
            rule_id, action_type, actor = "TRAIN_FAILED_FALLBACK", "Hire", "HR Partner"
            assumptions = f"TRAIN_FAILED_FALLBACK: employee {candidate_employee_id} failed skill {skill_id}; original rule {prior_rule}."
        if action_type == "Hire":
            hire_count += 1
        status = "Escalated" if action_type == "Hire" and hire_count > int(thresholds["headcount_budget"]) else "Proposed"
        actions.append({
            "gap_action_id": entity_id("GACT", action_counter),
            "gap_id": gap_id,
            "action_type": action_type,
            "candidate_employee_id": candidate_employee_id,
            "candidate_skill_id": candidate_skill_id,
            "rule_id": rule_id,
            "owner_actor": actor,
            "status": status,
            "lead_time_weeks": 8 if action_type == "Hire" else (2 if action_type == "Reverify" else 3),
            "estimated_cost": round(gap_fte * (12000 if action_type == "Hire" else 1800), 2),
            "assumptions": assumptions,
        })
        action_counter += 1

    for row in utilization:
        if row["utilization_available"] is not None and row["utilization_available"] > float(thresholds["over_utilization"]):
            actions.append({
                "gap_action_id": entity_id("GACT", action_counter),
                "gap_id": None,
                "action_type": "Reallocate",
                "rule_id": "UTIL_OVER_AVAILABLE",
                "candidate_employee_id": row["employee_id"],
                "candidate_skill_id": None,
                "owner_actor": "Manager",
                "status": "Proposed",
                "lead_time_weeks": 1,
                "estimated_cost": 0.0,
                "assumptions": f"UTIL_OVER_AVAILABLE: utilization={row['utilization_available']:.4f} > over_utilization={thresholds['over_utilization']}.",
            })
            action_counter += 1

    return {
        "availability": availability,
        "utilization": utilization,
        "supply": skill_supply_rows,
        "gap_analysis": gaps,
        "gap_actions": actions,
    }
