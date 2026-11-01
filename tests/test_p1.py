from wdf.calendar import iso_weeks
from wdf.config import load_scale, load_settings
from wdf.masters import generate_masters


def test_fixed_calendar_has_iso_week_53():
    weeks = iso_weeks()
    assert len(weeks) == 53
    assert weeks[-1]["iso_week"] == "2026W53"
    assert weeks[-1]["week_start"] == "2026-12-28"


def test_config_and_scale_values():
    assert load_settings().as_of.isoformat() == "2026-10-22"
    assert load_scale("starter").employees == 300
    assert load_scale("full").skills == 300


def test_master_generation_is_deterministic_and_referential():
    first = generate_masters(42, employees=30, skills=12, projects=4, roles=8)
    second = generate_masters(42, employees=30, skills=12, projects=4, roles=8)
    assert first == second
    employees = {row["employee_id"] for row in first["employees"]}
    assert all(row["manager_id"] is None or row["manager_id"] in employees for row in first["employees"])
    assert all(row["role_id"] in {r["role_id"] for r in first["roles"]} for row in first["employees"])
