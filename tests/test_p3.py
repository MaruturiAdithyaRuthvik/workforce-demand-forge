from wdf.config import load_settings
from wdf.derived import compute_derived
from wdf.transactions import generate_sources


def test_derived_availability_and_gap_rows_reconcile_to_sources():
    sources = generate_sources(23, employees=24, skills=12, projects=4, roles=8)
    derived = compute_derived(sources, load_settings().thresholds.model_dump())
    assert len(derived["availability"]) == 24 * 53
    for row in derived["availability"]:
        assert abs(row["available_hours"] - (
            row["capacity_hours"] - row["leave_hours"] - row["holiday_hours"]
        )) < 0.0001
    approved = [row for row in sources["demand_lines"] if row["status"] == "Approved"]
    assert {line_id for gap in derived["gap_analysis"] for line_id in gap["source_demand_line_ids"]} == {
        row["demand_line_id"] for row in approved
    }


def test_part_time_utilization_uses_available_hours_and_zero_flag():
    sources = generate_sources(29, employees=16, skills=8, projects=2, roles=8)
    derived = compute_derived(sources, load_settings().thresholds.model_dump())
    part_time_ids = {row["employee_id"] for row in sources["employees"] if row["fte"] < 1}
    assert any(row["employee_id"] in part_time_ids for row in derived["utilization"])
    assert all(row["flag"] == "ZERO_AVAILABILITY" for row in derived["utilization"] if row["utilization_available"] is None)
