from __future__ import annotations

from itertools import combinations
from math import ceil
from datetime import date, timedelta

import numpy as np

from wdf.calendar import iso_weeks
from wdf.config import load_settings
from wdf.ids import allocation_id, demand_id, entity_id
from wdf.masters import generate_masters, rng_for


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


def _project_window(project: dict) -> tuple[date, date] | None:
    start = max(date(2026, 1, 1), date.fromisoformat(project["start_date"]))
    end = min(date(2026, 12, 31), date.fromisoformat(project["end_date"]))
    return (start, end) if end >= start else None


def generate_sources(
    seed: int,
    employees: int,
    skills: int,
    projects: int,
    roles: int,
) -> dict[str, list[dict]]:
    settings = load_settings()
    data = generate_masters(seed, employees, skills, projects, roles)
    demand_rng, leave_rng, alloc_rng, training_rng = (rng_for(seed, 10 + i) for i in range(4))
    demand_config = settings.demand_curves
    profile_names = ("ramp_up", "steady", "ramp_down")
    if set(demand_config.profile_weights) != set(profile_names):
        raise ValueError(f"Demand curve weights must define exactly: {', '.join(profile_names)}")
    profile_weights = np.asarray(
        [demand_config.profile_weights[name] for name in profile_names], dtype=float
    )
    if np.any(profile_weights < 0) or not np.any(profile_weights > 0):
        raise ValueError("Demand curve weights must be non-negative with positive total")
    profile_weights /= profile_weights.sum()
    long_lived_project_count = min(3, len(data["projects"]))
    assigned_profiles = list(demand_rng.choice(
        profile_names, size=long_lived_project_count, replace=False, p=profile_weights
    ))
    assigned_profiles.extend(
        str(demand_rng.choice(profile_names, p=profile_weights))
        for _ in range(len(data["projects"]) - long_lived_project_count)
    )
    for project, profile in zip(data["projects"], assigned_profiles):
        project["demand_profile"] = str(profile)
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
            if demand_rng.random() < demand_config.zero_demand_probability:
                continue
            did = demand_id(project["project_id"], str(week["iso_week"]))
            demand_headers.append({
                "demand_id": did,
                "project_id": project["project_id"],
                "iso_week": week["iso_week"],
                "week_start": week["week_start"],
            })
            count = int(demand_rng.integers(
                demand_config.minimum_lines_per_week,
                demand_config.maximum_lines_per_week + 1,
            ))
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
                created = max(
                    date(2025, 1, 1),
                    week_start - timedelta(days=int(demand_rng.integers(
                        demand_config.minimum_creation_lead_days,
                        demand_config.maximum_creation_lead_days + 1,
                    ))),
                )
                progress = min(
                    1.0,
                    max(0.0, (week_start - start).days / max(1, (end - start).days)),
                )
                if project["demand_profile"] == "ramp_up":
                    profile_factor = demand_config.ramp_start_factor + (
                        1.0 - demand_config.ramp_start_factor
                    ) * progress
                elif project["demand_profile"] == "ramp_down":
                    profile_factor = 1.0 - (
                        1.0 - demand_config.ramp_end_factor
                    ) * progress
                else:
                    profile_factor = 1.0
                demand_lines.append({
                    "demand_line_id": entity_id("DEML", line_counter),
                    "demand_id": did,
                    "project_id": project["project_id"],
                    "iso_week": week["iso_week"],
                    "role_id": role["role_id"],
                    "skill_id": skill,
                    "required_fte": round(
                        float(demand_rng.uniform(
                            demand_config.minimum_required_fte,
                            demand_config.maximum_required_fte,
                        )) * profile_factor, 4
                    ),
                    "min_proficiency": int(bridge["min_proficiency"]) if bridge else 2,
                    "source": str(demand_rng.choice(["PlanTool", "ResourceRequest"])),
                    "created_on": created.isoformat(),
                    "supersedes_line_id": None,
                    "status": "Approved",
                })
                line_counter += 1

    # Append-only revisions: the original line remains present but is no longer approved.
    revision_count = demand_config.revision_count
    revision_targets = (
        demand_lines[::max(1, len(demand_lines) // revision_count or 1)][:revision_count]
        if revision_count else []
    )
    for original in revision_targets:
        revision = dict(original)
        revision["demand_line_id"] = entity_id("DEML", line_counter)
        revision["required_fte"] = round(
            float(original["required_fte"]) * demand_config.revision_multiplier, 4
        )
        header = next(row for row in demand_headers if row["demand_id"] == original["demand_id"])
        revision["created_on"] = max(original["created_on"], str(header["week_start"]))
        revision["supersedes_line_id"] = original["demand_line_id"]
        revision["status"] = "Approved"
        original["status"] = "Superseded"
        demand_lines.append(revision)
        line_counter += 1

    if projects >= 2:
        near_miss_project = data["projects"][0]
        near_miss_weeks = ("2026W30", "2026W31")
        plan_by_key = {
            (row["project_id"], row["iso_week"]): row for row in demand_headers
        }
        near_miss_plans = []
        for week_id in near_miss_weeks:
            plan = plan_by_key.get((near_miss_project["project_id"], week_id))
            if plan is None:
                week_number = int(week_id[-2:])
                week_start = date.fromisocalendar(2026, week_number, 1)
                plan = {
                    "demand_id": demand_id(near_miss_project["project_id"], week_id),
                    "project_id": near_miss_project["project_id"],
                    "iso_week": week_id,
                    "week_start": week_start.isoformat(),
                }
                demand_headers.append(plan)
                plan_by_key[(near_miss_project["project_id"], week_id)] = plan
            near_miss_plans.append(plan)
        existing_keys = {
            (row["demand_id"], row["role_id"], row["skill_id"])
            for row in demand_lines if row["status"] == "Approved"
        }
        candidate_pairs = [
            (role_skill["role_id"], role_skill["skill_id"])
            for role_skill in data["role_skills"]
            if all(
                (plan["demand_id"], role_skill["role_id"], role_skill["skill_id"])
                not in existing_keys
                for plan in near_miss_plans
            )
        ]
        if not candidate_pairs:
            raise ValueError("No unused role/skill pair for adjacent-week demand fixture")
        role_id, skill_id = candidate_pairs[0]
        min_proficiency = next(
            row["min_proficiency"] for row in data["role_skills"]
            if row["role_id"] == role_id and row["skill_id"] == skill_id
        )
        for plan in near_miss_plans:
            week_start = date.fromisoformat(plan["week_start"])
            demand_lines.append({
                "demand_line_id": entity_id("DEML", line_counter),
                "demand_id": plan["demand_id"],
                "project_id": near_miss_project["project_id"],
                "iso_week": plan["iso_week"],
                "role_id": role_id,
                "skill_id": skill_id,
                "required_fte": round(float(demand_rng.uniform(
                    demand_config.minimum_required_fte,
                    demand_config.maximum_required_fte,
                )), 4),
                "min_proficiency": min_proficiency,
                "source": "PlanTool",
                "created_on": max(date(2025, 1, 1), week_start - timedelta(days=14)).isoformat(),
                "supersedes_line_id": None,
                "status": "Approved",
            })
            line_counter += 1

    leave_config = settings.leave_realism
    eligible_count = min(
        employees, max(1, round(employees * leave_config.employee_share))
    )
    leave_employee_indices = set(
        int(value) for value in leave_rng.choice(employees, size=eligible_count, replace=False)
    )
    week_starts: dict[int, list[date]] = {month: [] for month in range(1, 13)}
    for week in weeks:
        week_start = date.fromisoformat(str(week["week_start"]))
        if (
            week_start.year == 2026
            and week_start + timedelta(days=settings.work_calendar.workdays_per_week - 1)
            <= date(2026, 12, 31)
        ):
            week_starts[week_start.month].append(week_start)

    month_weights = np.asarray(leave_config.month_weights, dtype=float)
    if np.any(month_weights <= 0):
        raise ValueError("Leave month weights must all be positive")
    month_probabilities = month_weights / month_weights.sum()
    leave_rows = []

    def leave_month() -> int:
        return int(leave_rng.choice(np.arange(1, 13), p=month_probabilities))

    def append_leave(employee: dict, start_day: date, length: int) -> None:
        leave_rows.append({
            "leave_id": entity_id("LEAVE", len(leave_rows) + 1),
            "employee_id": employee["employee_id"],
            "start_date": start_day.isoformat(),
            "end_date": (start_day + timedelta(days=length - 1)).isoformat(),
            "leave_type": str(leave_rng.choice(["Annual", "Sick", "Care", "Other"])),
            "status": "Approved",
        })

    for employee_index, employee in enumerate(data["employees"]):
        if employee_index not in leave_employee_indices:
            continue
        used_weeks = set()
        for _ in range(leave_config.full_week_records_per_employee):
            available_months = [
                month for month in range(1, 13)
                if any(start.isocalendar().week not in used_weeks for start in week_starts[month])
            ]
            weights = np.asarray(
                [month_weights[month - 1] for month in available_months], dtype=float
            )
            weights /= weights.sum()
            month = int(leave_rng.choice(available_months, p=weights))
            candidates = [
                start for start in week_starts[month]
                if start.isocalendar().week not in used_weeks
            ]
            start_day = candidates[int(leave_rng.integers(0, len(candidates)))]
            used_weeks.add(start_day.isocalendar().week)
            append_leave(employee, start_day, leave_config.full_week_days)

        for _ in range(leave_config.short_records_per_employee):
            for _attempt in range(leave_config.short_leave_attempts):
                month = leave_month()
                start_day = date(2026, month, int(leave_rng.integers(1, 29)))
                length = int(leave_rng.choice(leave_config.short_leave_days))
                if not any(
                    start_day <= date.fromisoformat(row["end_date"])
                    and date.fromisoformat(row["start_date"]) <= start_day + timedelta(days=length - 1)
                    for row in leave_rows if row["employee_id"] == employee["employee_id"]
                ):
                    break
            else:
                raise ValueError(f"Unable to place non-overlapping short leave for {employee['employee_id']}")
            append_leave(employee, start_day, length)

    allocation_targets = settings.allocation_realism
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

    project_by_id = {row["project_id"]: row for row in data["projects"]}
    shared_projects = [
        row for row in data["projects"] if row["staffing_model"] == "Shared-Pool"
        and _project_window(row) is not None
    ]
    shared_pairs = []
    for first, second in combinations(shared_projects, 2):
        first_window, second_window = _project_window(first), _project_window(second)
        assert first_window is not None and second_window is not None
        start = max(first_window[0], second_window[0])
        end = min(first_window[1], second_window[1])
        if (end - start).days >= allocation_targets.minimum_duration_days - 1:
            shared_pairs.append((first, second, start, end))
    if not shared_pairs:
        raise ValueError("No intersecting Shared-Pool project windows support legal overlaps")

    overlap_count = ceil(employees * allocation_targets.shared_overlap_employee_share)
    required_extras = ceil(
        employees * (allocation_targets.minimum_allocations_per_employee - 1)
    )
    if required_extras < overlap_count:
        raise ValueError("Allocation target cannot meet the configured overlap employee share")
    overlap_indices = set(
        int(value) for value in alloc_rng.choice(employees, size=overlap_count, replace=False)
    )
    sequential_indices = set(
        int(value) for value in alloc_rng.choice(
            sorted(set(range(employees)) - overlap_indices),
            size=required_extras - overlap_count,
            replace=False,
        )
    )

    def allocation_row(employee: dict, project: dict, start_day: date, end_day: date, pct: float) -> dict:
        employee_skills = [
            row for row in skills_by_employee.get(employee["employee_id"], [])
            if row["currency_flag"] == "Current"
            and date.fromisoformat(row["expiry_date"]) >= start_day
        ]
        basis = employee_skills[int(alloc_rng.integers(0, len(employee_skills)))] if employee_skills else None
        return {
            "allocation_id": allocation_id(len(allocations) + 1),
            "employee_id": employee["employee_id"],
            "project_id": project["project_id"],
            "role_id": employee["role_id"],
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "allocation_pct": pct,
            "skill_basis_esk_id": basis["employee_skill_id"] if basis else None,
            "status": "Active",
        }

    def random_window(project: dict) -> tuple[date, date]:
        window = _project_window(project)
        if window is None:
            raise ValueError(f"Project has no 2026 allocation window: {project['project_id']}")
        project_start, project_end = window
        span = (project_end - project_start).days
        start_day = project_start + timedelta(days=int(alloc_rng.integers(0, span + 1)))
        duration = min(
            int(alloc_rng.integers(
                allocation_targets.minimum_duration_days,
                allocation_targets.maximum_duration_days + 1,
            )),
            (project_end - start_day).days + 1,
        )
        if duration < allocation_targets.minimum_duration_days:
            start_day = max(
                project_start,
                project_end - timedelta(days=allocation_targets.minimum_duration_days - 1),
            )
            duration = allocation_targets.minimum_duration_days
        return start_day, start_day + timedelta(days=duration - 1)

    for index, employee in enumerate(data["employees"]):
        if index in overlap_indices:
            first, second, intersection_start, intersection_end = shared_pairs[
                int(alloc_rng.integers(0, len(shared_pairs)))
            ]
            duration = min(
                int(alloc_rng.integers(
                    allocation_targets.minimum_duration_days,
                    allocation_targets.maximum_duration_days + 1,
                )),
                (intersection_end - intersection_start).days + 1,
            )
            latest_start = intersection_end - timedelta(days=duration - 1)
            start_day = intersection_start + timedelta(
                days=int(alloc_rng.integers(0, (latest_start - intersection_start).days + 1))
            )
            end_day = start_day + timedelta(days=duration - 1)
            allocations.append(allocation_row(
                employee, first, start_day, end_day,
                allocation_targets.shared_overlap_allocation_percentage,
            ))
            allocations.append(allocation_row(
                employee, second, start_day, end_day,
                allocation_targets.shared_overlap_allocation_percentage,
            ))
            continue

        project = project_by_id[data["projects"][project_assignments[index]]["project_id"]]
        start_day, end_day = random_window(project)
        allocations.append(allocation_row(
            employee, project, start_day, end_day,
            float(alloc_rng.choice(allocation_targets.allocation_percentages)),
        ))

        if index not in sequential_indices:
            continue

        candidates = []
        for alternate in data["projects"]:
            if alternate["project_id"] == project["project_id"]:
                continue
            window = _project_window(alternate)
            if window is None:
                continue
            before_end = min(
                window[1],
                start_day - timedelta(days=start_day.weekday() + 1),
            )
            if (before_end - window[0]).days >= allocation_targets.minimum_duration_days - 1:
                candidates.append((alternate, window[0], before_end))
            end_week_monday = end_day - timedelta(days=end_day.weekday())
            after_start = max(window[0], end_week_monday + timedelta(days=7))
            if (window[1] - after_start).days >= allocation_targets.minimum_duration_days - 1:
                candidates.append((alternate, after_start, window[1]))
        if not candidates:
            raise ValueError(
                f"No non-overlapping sequential project window for {employee['employee_id']}"
            )
        alternate, period_start, period_end = candidates[
            int(alloc_rng.integers(0, len(candidates)))
        ]
        duration = min(
            int(alloc_rng.integers(
                allocation_targets.minimum_duration_days,
                allocation_targets.maximum_duration_days + 1,
            )),
            (period_end - period_start).days + 1,
        )
        latest_start = period_end - timedelta(days=duration - 1)
        sequential_start = period_start + timedelta(
            days=int(alloc_rng.integers(0, (latest_start - period_start).days + 1))
        )
        allocations.append(allocation_row(
            employee, alternate, sequential_start, sequential_start + timedelta(days=duration - 1),
            float(alloc_rng.choice(allocation_targets.allocation_percentages)),
        ))

    if projects >= 4 and employees >= 8:
        dedicated_projects = [
            project for project in data["projects"]
            if project["staffing_model"] == "Dedicated-Team"
        ]
        first_week = date.fromisocalendar(2026, 25, 1)
        second_week = first_week + timedelta(days=7)
        employee_ids_with_weekly_allocations = {
            allocation["employee_id"]
            for allocation in allocations
            if date.fromisoformat(allocation["start_date"]) <= second_week + timedelta(days=6)
            and date.fromisoformat(allocation["end_date"]) >= first_week
        }
        eligible_employees = [
            employee for employee in data["employees"]
            if employee["employee_id"] not in employee_ids_with_weekly_allocations
        ]
        if not eligible_employees or len(dedicated_projects) < 2:
            raise ValueError("Cannot place adjacent Dedicated-Team near-miss allocations")
        employee = eligible_employees[0]
        for project, start_day in zip(dedicated_projects[:2], (first_week, second_week)):
            allocations.append({
                "allocation_id": allocation_id(len(allocations) + 1),
                "employee_id": employee["employee_id"],
                "project_id": project["project_id"],
                "role_id": employee["role_id"],
                "start_date": start_day.isoformat(),
                "end_date": (start_day + timedelta(days=6)).isoformat(),
                "allocation_pct": allocation_targets.shared_overlap_allocation_percentage,
                "skill_basis_esk_id": None,
                "status": "Active",
            })

    training = []
    training_config = settings.training_generation
    for index in range(
        1,
        max(
            training_config.minimum_records,
            employees // training_config.employee_count_divisor,
        ) + 1,
    ):
        employee = data["employees"][
            (index * training_config.employee_index_multiplier - 1) % employees
        ]
        skill = data["skills"][
            (index * training_config.skill_index_multiplier - 1) % skills
        ]
        start_day = date(2026, 1, 1) + timedelta(
            days=(index * training_config.start_day_multiplier)
            % training_config.start_day_modulus
        )
        state = str(training_rng.choice(["Planned", "Enrolled", "Completed", "Failed", "Cancelled"]))
        training.append({
            "training_id": entity_id("TRN", index),
            "employee_id": employee["employee_id"],
            "skill_id": skill["skill_id"],
            "target_proficiency": int(training_rng.integers(
                training_config.minimum_target_proficiency,
                training_config.maximum_target_proficiency + 1,
            )),
            "cost": round(float(training_rng.uniform(
                training_config.minimum_cost,
                training_config.maximum_cost,
            )), 2),
            "start_date": start_day.isoformat(),
            "end_date": (
                start_day + timedelta(days=int(training_rng.integers(
                    training_config.minimum_duration_days,
                    training_config.maximum_duration_days + 1,
                )))
            ).isoformat(),
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
        "holidays": [
            {"holiday_date": day.isoformat(), "name": f"Synthetic holiday {i + 1}"}
            for i, day in enumerate(settings.holidays)
        ],
        "allocations": allocations,
        "training": training,
        "lifecycle_events": events,
    })
    return data
