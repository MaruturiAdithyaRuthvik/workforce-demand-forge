from datetime import date, timedelta

from wdf.anomalies import inject_anomalies
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


def test_utilization_risk_actions_are_traceable_and_contracts_escalate_over_budget():
    settings = load_settings()
    sources, _truth = inject_anomalies(
        generate_sources(67, employees=120, skills=36, projects=30, roles=8), 67
    )
    derived = compute_derived(sources, settings.thresholds.model_dump())
    allocations = {row["allocation_id"]: row for row in sources["allocations"]}
    utilization = {row["utilization_id"]: row for row in derived["utilization"]}
    actions = [
        row for row in derived["gap_actions"]
        if row["rule_id"] in {"UTIL_OVER_AVAILABLE", "UTIL_CONTRACT_OVER_THRESHOLD"}
    ]
    reallocate = [row for row in actions if row["action_type"] == "Reallocate"]
    contracts = [row for row in actions if row["action_type"] == "Contract"]
    assert reallocate and contracts
    assert any(row["status"] == "Escalated" for row in contracts)

    for action in actions:
        source = utilization[action["source_utilization_id"]]
        assert action["candidate_employee_id"] == source["employee_id"]
        assert action["source_allocation_ids"]
        assert action["owner_actor"] in {"Manager", "HR Partner"}
        assert action["rule_id"] in action["assumptions"]
        week_start = date.fromisocalendar(2026, int(source["iso_week"][-2:]), 1)
        week_end = week_start + timedelta(days=6)
        assert all(
            allocations[allocation_id]["employee_id"] == source["employee_id"]
            and date.fromisoformat(allocations[allocation_id]["start_date"]) <= week_end
            and date.fromisoformat(allocations[allocation_id]["end_date"]) >= week_start
            for allocation_id in action["source_allocation_ids"]
        )
        if action["action_type"] == "Contract":
            assert action["status"] == (
                "Escalated"
                if action["estimated_cost"] > settings.thresholds.contract_budget_cap
                else "Proposed"
            )
