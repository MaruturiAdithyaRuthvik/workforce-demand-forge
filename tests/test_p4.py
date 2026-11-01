from copy import deepcopy
from datetime import date

from wdf.calendar import iso_weeks
from wdf.forecast import _predictions, forecast_data
from wdf.transactions import generate_sources


def test_forecast_outputs_weeks_after_fixed_as_of_and_scores_all_horizons():
    sources = generate_sources(31, employees=30, skills=12, projects=4, roles=8)
    rows, metrics = forecast_data(sources, {"Planned": 0.45, "Active": 0.8, "Completed": 0.0})
    assert rows
    assert {row["iso_week"] for row in rows} == {f"2026W{week:02d}" for week in range(44, 54)}
    for method in metrics["methods"].values():
        assert [row["horizon_weeks"] for row in method] == [4, 8, 12]


def test_backtest_pipeline_excludes_lines_created_after_origin():
    sources = generate_sources(37, employees=25, skills=10, projects=4, roles=8)
    weeks = iso_weeks()
    projects = {row["project_id"]: row for row in sources["projects"]}
    origin = date(2026, 3, 1)
    target_week = "2026W15"
    confidence = {"Planned": 0.45, "Active": 0.8, "Completed": 0.0}
    changed = deepcopy(sources["demand_lines"])
    for line in changed:
        if line["iso_week"] == target_week and line["created_on"] > origin.isoformat():
            line["created_on"] = "2026-06-01"
    before = _predictions(sources["demand_lines"], projects, weeks, origin, [target_week], confidence)
    after = _predictions(changed, projects, weeks, origin, [target_week], confidence)
    assert before == after
