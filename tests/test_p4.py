from copy import deepcopy
from datetime import date

from wdf.calendar import iso_weeks
from wdf.config import load_settings
from wdf.forecast import _predictions, _realization_ratio, forecast_data
from wdf.transactions import generate_sources


def test_forecast_outputs_weeks_after_fixed_as_of_and_scores_all_horizons():
    sources = generate_sources(31, employees=30, skills=12, projects=4, roles=8)
    rows, metrics = forecast_data(sources, {"Planned": 0.45, "Active": 0.8, "Completed": 0.0})
    assert rows
    assert {row["iso_week"] for row in rows} == {f"2026W{week:02d}" for week in range(44, 54)}
    assert set(metrics["methods"]) == {
        "moving_average_4w", "pipeline_adjusted", "pipeline_realization_adjusted"
    }
    for method in metrics["methods"].values():
        assert [row["horizon_weeks"] for row in method] == [4, 8, 12]
        assert all(row["origins"] > 1 for row in method)


def test_backtest_pipeline_excludes_lines_created_after_origin():
    sources = generate_sources(37, employees=25, skills=10, projects=4, roles=8)
    weeks = iso_weeks()
    projects = {row["project_id"]: row for row in sources["projects"]}
    origin = date(2026, 3, 1)
    target_week = "2026W15"
    confidence = {"Planned": 0.45, "Active": 0.8, "Completed": 0.0}
    changed = deepcopy(sources["demand_lines"])
    future_line = dict(next(line for line in changed if line["iso_week"] == target_week))
    future_line.update({
        "demand_line_id": "DEML-999999",
        "created_on": "2026-06-01",
        "required_fte": 1000.0,
    })
    changed.append(future_line)
    before = _predictions(sources["demand_lines"], projects, weeks, origin, [target_week], confidence)
    after = _predictions(changed, projects, weeks, origin, [target_week], confidence)
    assert before == after

    ratio_config = load_settings().forecast["realization_ratio"]
    before_ratio = _realization_ratio(
        sources["demand_lines"], projects, weeks, origin, confidence, ratio_config
    )
    after_ratio = _realization_ratio(
        changed, projects, weeks, origin, confidence, ratio_config
    )
    assert before_ratio == after_ratio
    assert {
        key: value * before_ratio for key, value in before[1].items()
    } == {
        key: value * after_ratio for key, value in after[1].items()
    }
