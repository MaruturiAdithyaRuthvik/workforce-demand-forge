from __future__ import annotations

from collections import defaultdict
from datetime import date

from wdf.calendar import AS_OF, iso_weeks


def _actuals(lines: list[dict], cutoff: date) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for row in lines:
        if row["status"] == "Approved" and date.fromisoformat(row["created_on"]) <= cutoff:
            totals[(row["iso_week"], row["role_id"])] += float(row["required_fte"])
    return totals


def _state_at(project: dict, origin: date) -> str:
    start = date.fromisoformat(project["start_date"])
    end = date.fromisoformat(project["end_date"])
    if start > origin:
        return "Planned"
    if end < origin:
        return "Completed"
    return "Active"


def _predictions(
    lines: list[dict],
    projects: dict[str, dict],
    weeks: list[dict],
    origin: date,
    target_weeks: list[str],
    confidence: dict[str, float],
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float]]:
    visible = _actuals(lines, origin)
    historical_weeks = [str(row["iso_week"]) for row in weeks if date.fromisoformat(str(row["week_start"])) <= origin]
    trailing = historical_weeks[-4:]
    roles = sorted({row["role_id"] for row in lines})
    baseline: dict[tuple[str, str], float] = {}
    for week in target_weeks:
        for role_id in roles:
            baseline[(week, role_id)] = sum(visible.get((past_week, role_id), 0.0) for past_week in trailing) / max(1, len(trailing))

    pipeline: dict[tuple[str, str], float] = defaultdict(float)
    target_set = set(target_weeks)
    for row in lines:
        if row["status"] != "Approved" or row["iso_week"] not in target_set:
            continue
        if date.fromisoformat(row["created_on"]) > origin:
            continue
        lifecycle = _state_at(projects[row["project_id"]], origin)
        weight = float(confidence.get(lifecycle, 0.0))
        pipeline[(row["iso_week"], row["role_id"])] += float(row["required_fte"]) * weight
    for week in target_weeks:
        for role_id in roles:
            pipeline.setdefault((week, role_id), 0.0)
    return baseline, dict(pipeline)


def _metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    denominator = sum(actual)
    return {
        "wape": sum(abs(a - p) for a, p in zip(actual, predicted)) / denominator if denominator else 0.0,
        "bias": (sum(predicted) - denominator) / denominator if denominator else 0.0,
    }


def forecast_data(
    sources: dict[str, list[dict]],
    confidence: dict[str, float],
    as_of: date = AS_OF,
) -> tuple[list[dict], dict]:
    weeks = iso_weeks()
    future_weeks = [
        str(row["iso_week"]) for row in weeks
        if date.fromisoformat(str(row["week_start"])) > as_of
    ]
    projects = {row["project_id"]: row for row in sources["projects"]}
    baseline, pipeline = _predictions(
        sources["demand_lines"], projects, weeks, as_of, future_weeks, confidence
    )
    forecast_rows = []
    for method, predictions in [("moving_average_4w", baseline), ("pipeline_adjusted", pipeline)]:
        for (week, role_id), demand_fte in sorted(predictions.items()):
            forecast_rows.append({
                "iso_week": week,
                "role_id": role_id,
                "method": method,
                "forecast_demand_fte": round(demand_fte, 4),
            })

    actuals = _actuals(sources["demand_lines"], as_of)
    backtest: dict[str, list[dict]] = {"moving_average_4w": [], "pipeline_adjusted": []}
    historic_weeks = [str(row["iso_week"]) for row in weeks if date.fromisoformat(str(row["week_start"])) <= as_of]
    for horizon in (4, 8, 12):
        pairs = {"moving_average_4w": ([], []), "pipeline_adjusted": ([], [])}
        for origin_index in range(3, len(historic_weeks) - horizon):
            origin_week = historic_weeks[origin_index]
            origin_date = date.fromisocalendar(int(origin_week[:4]), int(origin_week[-2:]), 7)
            targets = historic_weeks[origin_index + 1: origin_index + horizon + 1]
            avg, adjusted = _predictions(
                sources["demand_lines"], projects, weeks, origin_date, targets, confidence
            )
            for target in targets:
                for role_id in sorted({role for _, role in actuals}):
                    actual = actuals.get((target, role_id), 0.0)
                    pairs["moving_average_4w"][0].append(actual)
                    pairs["moving_average_4w"][1].append(avg.get((target, role_id), 0.0))
                    pairs["pipeline_adjusted"][0].append(actual)
                    pairs["pipeline_adjusted"][1].append(adjusted.get((target, role_id), 0.0))
        for method, (actual, predicted) in pairs.items():
            backtest[method].append({"horizon_weeks": horizon, **_metrics(actual, predicted)})

    metrics = {
        "as_of": as_of.isoformat(),
        "forecast_weeks": len(future_weeks),
        "methods": backtest,
        "backtest_method": "rolling origin, observed weeks through W43, origin-specific created_on cutoff",
    }
    return forecast_rows, metrics
