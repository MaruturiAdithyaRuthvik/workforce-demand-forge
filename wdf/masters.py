from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from wdf.calendar import AS_OF, add_months
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
            "validity_months": int(skill_rng.choice([12, 18, 24, 36])),
        })

    role_skill_rows = []
    for role in role_rows:
        selected = bridge_rng.choice(
            skills, size=min(skills, int(bridge_rng.integers(3, 8))), replace=False
        )
        for skill_index in sorted(int(value) for value in selected):
            role_skill_rows.append({
                "role_skill_id": f"RS-{role['role_id']}-{skill_index + 1:06d}",
                "role_id": role["role_id"],
                "skill_id": entity_id("SKL", skill_index + 1),
                "min_proficiency": int(bridge_rng.integers(2, 5)),
                "importance": round(float(bridge_rng.uniform(0.5, 1.0)), 4),
            })

    employee_rows = []
    for index in range(1, employees + 1):
        hire_offset = int(employee_rng.integers(0, 365 * 8))
        hire_date = AS_OF - timedelta(days=hire_offset)
        fte = float(employee_rng.choice([1.0, 0.8, 0.6, 0.5], p=[0.7, 0.12, 0.1, 0.08]))
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
    esk_index = 1
    for employee in employee_rows:
        count = min(skills, max(2, int(esk_rng.zipf(1.7))))
        selected = esk_rng.choice(skills, size=count, replace=False)
        for skill_index in sorted(int(value) for value in selected):
            skill = skill_rows[skill_index]
            verified = AS_OF - timedelta(days=int(esk_rng.integers(0, 1100)))
            expiry = add_months(verified, skill["validity_months"])
            employee_skill_rows.append({
                "employee_skill_id": entity_id("ESK", esk_index),
                "employee_id": employee["employee_id"],
                "skill_id": skill["skill_id"],
                "proficiency": int(esk_rng.choice([1, 2, 3, 4, 5], p=[0.05, 0.30, 0.38, 0.20, 0.07])),
                "last_verified_date": verified.isoformat(),
                "expiry_date": expiry.isoformat(),
                "currency_flag": "Current" if expiry >= AS_OF else "Stale",
            })
            esk_index += 1

    project_rows = []
    for index in range(1, projects + 1):
        start = date(2026, 1, 5) + timedelta(days=int(project_rng.integers(0, 320)))
        duration_days = int(np.clip(project_rng.lognormal(mean=4.0, sigma=0.65), 35, 430))
        end = start + timedelta(days=duration_days)
        status = "Planned" if start > AS_OF else ("Completed" if end < AS_OF else "Active")
        project_rows.append({
            "project_id": project_id(index),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "priority": str(project_rng.choice(["Low", "Medium", "High", "Critical"], p=[0.15, 0.4, 0.35, 0.1])),
            "staffing_model": str(project_rng.choice(["Shared-Pool", "Dedicated-Team"], p=[0.75, 0.25])),
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
