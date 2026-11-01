from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from wdf.calendar import AS_OF, add_months
from wdf.config import load_settings
from wdf.ids import entity_id, project_id


FAMILIES = ["Engineering", "Data", "QA", "Design", "PM", "DevOps", "Security", "Support"]
SKILL_CATEGORIES = ["Technical", "Domain", "Leadership", "Platform", "Compliance"]
PROFICIENCY_SCALE = [
    {"proficiency": 1, "definition": "Awareness"},
    {"proficiency": 2, "definition": "Basic"},
    {"proficiency": 3, "definition": "Working"},
    {"proficiency": 4, "definition": "Advanced"},
    {"proficiency": 5, "definition": "Expert"},
]
ROLE_TITLES = [
    "Associate", "Analyst", "Engineer", "Senior Engineer", "Lead", "Principal"
]


def rng_for(seed: int, stream: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(stream,)))


def generate_masters(seed: int, employees: int, skills: int, projects: int, roles: int) -> dict[str, list[dict]]:
    generation = load_settings().master_generation
    role_rng, skill_rng, employee_rng, project_rng, bridge_rng, esk_rng = (
        rng_for(seed, index) for index in range(6)
    )
    role_rows = []
    for index in range(1, roles + 1):
        family = FAMILIES[(index - 1) % len(FAMILIES)]
        title = ROLE_TITLES[(index - 1) % len(ROLE_TITLES)]
        role_rows.append(
            {"role_id": f"ROLE-{index:04d}", "title": f"{title} {family} {index:02d}", "family": family}
        )

    skill_rows = []
    for index in range(1, skills + 1):
        skill_rows.append({
            "skill_id": entity_id("SKL", index),
            "name": f"Synthetic Skill {index:04d}",
            "category": SKILL_CATEGORIES[(index - 1) % len(SKILL_CATEGORIES)],
            "validity_months": int(skill_rng.choice(generation.skill_validity_months)),
        })

    role_skill_rows = []
    for role in role_rows:
        selected = bridge_rng.choice(
            skills,
            size=min(
                skills,
                int(bridge_rng.integers(
                    generation.role_skill_count_min, generation.role_skill_count_max + 1
                )),
            ),
            replace=False,
        )
        for skill_index in sorted(int(value) for value in selected):
            role_skill_rows.append({
                "role_skill_id": f"RS-{role['role_id']}-{skill_index + 1:06d}",
                "role_id": role["role_id"],
                "skill_id": entity_id("SKL", skill_index + 1),
                "min_proficiency": int(bridge_rng.integers(
                    generation.role_skill_min_proficiency,
                    generation.role_skill_max_proficiency + 1,
                )),
                "importance": round(float(bridge_rng.uniform(
                    generation.role_skill_importance_min,
                    generation.role_skill_importance_max,
                )), 4),
            })

    employee_rows = []
    for index in range(1, employees + 1):
        hire_offset = int(employee_rng.integers(0, generation.hire_lookback_days))
        hire_date = AS_OF - timedelta(days=hire_offset)
        fte = float(employee_rng.choice(
            generation.fte_values, p=generation.fte_probabilities
        ))
        employee_rows.append({
            "employee_id": entity_id("EMP", index),
            "role_id": role_rows[(index - 1) % roles]["role_id"],
            "manager_id": entity_id("EMP", max(1, index // 8)) if index > 8 else None,
            "employment_type": "FT" if fte == 1.0 else "PT",
            "fte": fte,
            "hire_date": hire_date.isoformat(),
            "status": "Active",
        })

    employee_skill_rows = []
    skill_weights = np.power(
        np.arange(1, skills + 1, dtype=float), -generation.skill_popularity_exponent
    )
    skill_weights /= skill_weights.sum()
    skill_probabilities = np.empty(skills, dtype=float)
    skill_probabilities[esk_rng.permutation(skills)] = skill_weights
    esk_index = 1
    for employee in employee_rows:
        count = min(
            skills,
            max(generation.employee_skill_count_min, int(esk_rng.zipf(
                generation.employee_skill_zipf_shape
            ))),
        )
        selected = esk_rng.choice(skills, size=count, replace=False, p=skill_probabilities)
        for skill_index in sorted(int(value) for value in selected):
            skill = skill_rows[skill_index]
            is_stale = bool(esk_rng.random() < generation.stale_skill_rate)
            validity = int(skill["validity_months"])
            verified = (
                add_months(AS_OF, -validity) - timedelta(days=int(esk_rng.integers(
                    generation.stale_verification_min_days,
                    generation.stale_verification_max_days + 1,
                )))
                if is_stale
                else AS_OF - timedelta(days=int(esk_rng.integers(
                    0, validity * generation.current_verification_days_per_month + 1
                )))
            )
            expiry = add_months(verified, validity)
            employee_skill_rows.append({
                "employee_skill_id": entity_id("ESK", esk_index),
                "employee_id": employee["employee_id"],
                "skill_id": skill["skill_id"],
                "proficiency": int(esk_rng.choice(
                    generation.proficiency_values, p=generation.proficiency_probabilities
                )),
                "last_verified_date": verified.isoformat(),
                "expiry_date": expiry.isoformat(),
                "currency_flag": "Current" if expiry >= AS_OF else "Stale",
            })
            esk_index += 1

    project_rows = []
    for index in range(1, projects + 1):
        if index <= min(2, projects):
            start, end = date(2026, 1, 5), date(2026, 12, 31)
            staffing_model = "Shared-Pool"
        elif index <= min(4, projects):
            start, end = date(2026, 1, 5), date(2026, 12, 31)
            staffing_model = "Dedicated-Team"
        else:
            start = date(2026, 1, 5) + timedelta(days=int(project_rng.integers(
                0, generation.project_start_max_offset_days
            )))
            duration_days = int(np.clip(
                project_rng.lognormal(
                    mean=generation.project_duration_log_mean,
                    sigma=generation.project_duration_log_sigma,
                ),
                generation.project_duration_min_days,
                generation.project_duration_max_days,
            ))
            end = start + timedelta(days=duration_days)
            staffing_model = str(project_rng.choice(
                generation.project_staffing_models,
                p=generation.project_staffing_probabilities,
            ))
        status = "Planned" if start > AS_OF else ("Completed" if end < AS_OF else "Active")
        project_rows.append({
            "project_id": project_id(index),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "priority": str(project_rng.choice(
                generation.project_priorities,
                p=generation.project_priority_probabilities,
            )),
            "staffing_model": staffing_model,
            "status": status,
        })

    return {
        "roles": role_rows,
        "skills": skill_rows,
        "proficiency_scale": PROFICIENCY_SCALE,
        "role_skills": sorted(role_skill_rows, key=lambda row: row["role_skill_id"]),
        "employees": employee_rows,
        "employee_skills": employee_skill_rows,
        "projects": project_rows,
    }
