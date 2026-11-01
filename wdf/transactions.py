from __future__ import annotations

from datetime import date, timedelta

from wdf.calendar import iso_weeks
from wdf.ids import allocation_id, demand_id, entity_id
from wdf.masters import generate_masters, rng_for


HOLIDAYS = [
    "2026-01-01", "2026-05-25", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"
]


def _week_for(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}W{iso.week:02d}"


def _event(entity_type: str, entity_id_value: str, state: str, effective_date: str, reason: str) -> dict:
    return {
        "event_id": "",
        "entity_type": entity_type,
        "entity_id": entity_id_value,
        "from_state": None,
        "to_state": state,
        "effective_date": effective_date,
        "reason": reason,
    }


def generate_sources(
    seed: int,
    employees: int,
    skills: int,
    projects: int,
    roles: int,
) -> dict[str, list[dict]]:
    data = generate_masters(seed, employees, skills, projects, roles)
    demand_rng, leave_rng, alloc_rng, training_rng = (rng_for(seed, 10 + i) for i in range(4))
    weeks = iso_weeks()
    role_skills: dict[str, list[dict]] = {}
    for row in data["role_skills"]:
        role_skills.setdefault(row["role_id"], []).append(row)
    skills_by_employee: dict[str, list[dict]] = {}
    for row in data["employee_skills"]:
        skills_by_employee.setdefault(row["employee_id"], []).append(row)

    demand_headers: list[dict] = []
    demand_lines: list[dict] = []
    line_counter = 1
    for project in data["projects"]:
        start, end = date.fromisoformat(project["start_date"]), date.fromisoformat(project["end_date"])
        for week in weeks:
            week_start = date.fromisoformat(str(week["week_start"]))
            if week_start > end or week_start + timedelta(days=6) < start:
                continue
            if demand_rng.random() < 0.22:
                continue
            did = demand_id(project["project_id"], str(week["iso_week"]))
            demand_headers.append({
                "demand_id": did,
                "project_id": project["project_id"],
                "iso_week": week["iso_week"],
                "week_start": week["week_start"],
            })
            count = int(demand_rng.integers(1, 3))
            seen_keys: set[tuple[str, str]] = set()
            for _ in range(count):
                for _attempt in range(10):
                    role = data["roles"][int(demand_rng.integers(0, len(data["roles"])))]
                    eligible = role_skills.get(role["role_id"], [])
                    bridge = eligible[int(demand_rng.integers(0, len(eligible)))] if eligible else None
                    skill = bridge["skill_id"] if bridge else data["skills"][int(demand_rng.integers(0, skills))]["skill_id"]
                    if (role["role_id"], skill) not in seen_keys:
                        break
                else:
                    continue
                seen_keys.add((role["role_id"], skill))
                created = max(date(2025, 1, 1), week_start - timedelta(days=int(demand_rng.integers(1, 91))))
                demand_lines.append({
                    "demand_line_id": entity_id("DEML", line_counter),
                    "demand_id": did,
                    "project_id": project["project_id"],
                    "iso_week": week["iso_week"],
                    "role_id": role["role_id"],
                    "skill_id": skill,
                    "required_fte": round(float(demand_rng.uniform(0.25, 2.0)), 4),
                    "min_proficiency": int(bridge["min_proficiency"]) if bridge else 2,
                    "source": str(demand_rng.choice(["PlanTool", "ResourceRequest"])),
                    "created_on": created.isoformat(),
                    "supersedes_line_id": None,
                    "status": "Approved",
                })
                line_counter += 1

    # Append-only revisions: the original line remains present but is no longer approved.
    for original in demand_lines[::max(1, len(demand_lines) // 25 or 1)][:25]:
        revision = dict(original)
        revision["demand_line_id"] = entity_id("DEML", line_counter)
        revision["required_fte"] = round(float(original["required_fte"]) * 1.1, 4)
        header = next(row for row in demand_headers if row["demand_id"] == original["demand_id"])
        revision["created_on"] = max(original["created_on"], str(header["week_start"]))
        revision["supersedes_line_id"] = original["demand_line_id"]
        revision["status"] = "Approved"
        original["status"] = "Superseded"
        demand_lines.append(revision)
        line_counter += 1

    leave_rows = []
    for index, employee in enumerate(data["employees"], start=1):
        if leave_rng.random() < 0.12:
            season = int(leave_rng.choice([0, 1, 2, 3]))
            start_day = date(2026, [2, 5, 7, 12][season], int(leave_rng.integers(1, 22)))
            length = int(leave_rng.choice([1, 2, 3, 5, 10]))
            leave_rows.append({
                "leave_id": entity_id("LEAVE", index),
                "employee_id": employee["employee_id"],
                "start_date": start_day.isoformat(),
                "end_date": (start_day + timedelta(days=length - 1)).isoformat(),
                "leave_type": str(leave_rng.choice(["Annual", "Sick", "Care", "Other"])),
                "status": "Approved",
            })

    allocations = []
    project_weights = alloc_rng.lognormal(mean=0.0, sigma=0.8, size=len(data["projects"]))
    project_probabilities = project_weights / project_weights.sum()
    if employees >= projects:
        project_assignments = list(range(projects))
        project_assignments.extend(
            int(value) for value in alloc_rng.choice(
                projects, size=employees - projects, replace=True, p=project_probabilities
            )
        )
    else:
        project_assignments = [
            int(value) for value in alloc_rng.choice(
                projects, size=employees, replace=True, p=project_probabilities
            )
        ]
    alloc_rng.shuffle(project_assignments)
    for index, employee in enumerate(data["employees"], start=1):
        project = data["projects"][project_assignments[index - 1]]
        project_start = max(date(2026, 1, 5), date.fromisoformat(project["start_date"]))
        project_end = min(date(2026, 12, 31), date.fromisoformat(project["end_date"]))
        if project_end < project_start:
            project_start, project_end = date(2026, 1, 5), date(2026, 12, 31)
        span = max(1, (project_end - project_start).days)
        start_day = project_start + timedelta(days=int(alloc_rng.integers(0, span)))
        end_day = min(project_end, start_day + timedelta(days=int(alloc_rng.integers(21, 100))))
        employee_skills = [
            row for row in skills_by_employee.get(employee["employee_id"], [])
            if row["currency_flag"] == "Current"
            and date.fromisoformat(row["expiry_date"]) >= start_day
        ]
        basis = employee_skills[int(alloc_rng.integers(0, len(employee_skills)))] if employee_skills else None
        allocations.append({
            "allocation_id": allocation_id(index),
            "employee_id": employee["employee_id"],
            "project_id": project["project_id"],
            "role_id": employee["role_id"],
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "allocation_pct": round(float(alloc_rng.choice([0.25, 0.5, 0.75])), 4),
            "skill_basis_esk_id": basis["employee_skill_id"] if basis else None,
            "status": "Active" if start_day <= date(2026, 12, 31) else "Proposed",
        })

    training = []
    for index in range(1, max(2, employees // 20) + 1):
        employee = data["employees"][(index * 7 - 1) % employees]
        skill = data["skills"][(index * 11 - 1) % skills]
        start_day = date(2026, 1, 1) + timedelta(days=(index * 13) % 320)
        state = str(training_rng.choice(["Planned", "Enrolled", "Completed", "Failed", "Cancelled"]))
        training.append({
            "training_id": entity_id("TRN", index),
            "employee_id": employee["employee_id"],
            "skill_id": skill["skill_id"],
            "target_proficiency": int(training_rng.integers(2, 6)),
            "cost": round(float(training_rng.uniform(100, 2500)), 2),
            "start_date": start_day.isoformat(),
            "end_date": (start_day + timedelta(days=int(training_rng.integers(7, 45)))).isoformat(),
            "status": state,
        })

    events = []
    for row in data["employees"]:
        events.append(_event("Employee", row["employee_id"], row["status"], row["hire_date"], "Synthetic hire"))
    for row in data["projects"]:
        events.append(_event("Project", row["project_id"], row["status"], row["start_date"], "Synthetic project setup"))
    for row in allocations:
        events.append(_event("Allocation", row["allocation_id"], row["status"], row["start_date"], "Synthetic staffing"))
    for row in training:
        events.append(_event("Training", row["training_id"], row["status"], row["start_date"], "Synthetic development"))
    superseding_by_id = {
        row["supersedes_line_id"]: row for row in demand_lines if row["supersedes_line_id"]
    }
    for row in demand_lines:
        if row["status"] == "Superseded":
            events.append(_event(
                "DemandLine", row["demand_line_id"], "Approved", row["created_on"], "Synthetic approval"
            ))
            superseding = superseding_by_id[row["demand_line_id"]]
            events.append({
                "event_id": "",
                "entity_type": "DemandLine",
                "entity_id": row["demand_line_id"],
                "from_state": "Approved",
                "to_state": "Superseded",
                "effective_date": superseding["created_on"],
                "reason": "Replaced by appended demand revision",
            })
        else:
            events.append(_event("DemandLine", row["demand_line_id"], row["status"], row["created_on"], "Synthetic planning"))
    events.sort(key=lambda event: (event["entity_type"], event["entity_id"], event["effective_date"]))
    for index, event in enumerate(events, start=1):
        event["event_id"] = entity_id("EVT", index)

    data.update({
        "demand_plans": demand_headers,
        "demand_lines": demand_lines,
        "leave": leave_rows,
        "holidays": [{"holiday_date": day, "name": f"Synthetic holiday {i + 1}"} for i, day in enumerate(HOLIDAYS)],
        "allocations": allocations,
        "training": training,
        "lifecycle_events": events,
    })
    return data
