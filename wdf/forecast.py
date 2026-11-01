from __future__ import annotations

from collections import defaultdict
from datetime import date

from wdf.calendar import AS_OF, iso_weeks
from wdf.config import load_settings


def _actuals(lines: list[dict], cutoff: date) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for row in lines:
        if row["status"] == "Approved" and date.fromisoformat(row["created_on"]) <= cutoff:
            totals[(row["iso_week"], row["role_id"])] += float(row["required_fte"])
    return totals


def _project_actuals(
    lines: list[dict], cutoff: date
) -> dict[tuple[str, str, str], float]:
    totals: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in lines:
        if row["status"] == "Approved" and date.fromisoformat(row["created_on"]) <= cutoff:
            totals[(row["iso_week"], row["project_id"], row["role_id"])] += float(
                row["required_fte"]
            )
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
    roles = sorted({
        row["role_id"] for row in lines
        if date.fromisoformat(row["created_on"]) <= origin
    })
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


def _reconcile_project_predictions(
    role_predictions: dict[tuple[str, str], float],
    project_weights: dict[tuple[str, str, str], float],
) -> dict[tuple[str, str, str], float]:
    weights_by_role_week: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for (week, project_id, role_id), weight in project_weights.items():
        weights_by_role_week[(week, role_id)][project_id] = max(0.0, weight)

    reconciled: dict[tuple[str, str, str], float] = {}
    for (week, role_id), raw_total in role_predictions.items():
        total = round(raw_total, 4)
        project_weights_for_key = weights_by_role_week[(week, role_id)]
        if not project_weights_for_key:
            if total:
                raise ValueError(
                    f"Cannot reconcile nonzero role forecast for {week}/{role_id}: "
                    "no project weights are available"
                )
            continue
        weight_total = sum(project_weights_for_key.values())
        if weight_total == 0:
            if total:
                raise ValueError(
                    f"Cannot reconcile nonzero role forecast for {week}/{role_id}: "
                    "all project weights are zero"
                )
            for project_id in project_weights_for_key:
                reconciled[(week, project_id, role_id)] = 0.0
            continue
        project_values = {
            project_id: round(total * weight / weight_total, 4)
            for project_id, weight in project_weights_for_key.items()
        }
        residual = round(total - sum(project_values.values()), 4)
        recipient = min(
            project_weights_for_key,
            key=lambda project_id: (-project_weights_for_key[project_id], project_id),
        )
        project_values[recipient] = round(project_values[recipient] + residual, 4)
        for project_id, value in project_values.items():
            reconciled[(week, project_id, role_id)] = value
    return reconciled


def _project_predictions(
    lines: list[dict],
    projects: dict[str, dict],
    weeks: list[dict],
    origin: date,
    target_weeks: list[str],
    confidence: dict[str, float],
) -> tuple[
    dict[tuple[str, str], float],
    dict[tuple[str, str], float],
    dict[tuple[str, str, str], float],
    dict[tuple[str, str, str], float],
]:
    baseline, pipeline = _predictions(
        lines, projects, weeks, origin, target_weeks, confidence
    )
    historical_weeks = [
        str(row["iso_week"])
        for row in weeks
        if date.fromisoformat(str(row["week_start"])) <= origin
    ]
    trailing = set(historical_weeks[-4:])
    visible_project_actuals = _project_actuals(lines, origin)
    historical_weights: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for (week, project_id, role_id), value in visible_project_actuals.items():
        if week in trailing:
            historical_weights[(week, role_id)][project_id] += value

    target_projects: dict[tuple[str, str], set[str]] = defaultdict(set)
    target_set = set(target_weeks)
    for line in lines:
        if (
            line["status"] == "Approved"
            and line["iso_week"] in target_set
            and date.fromisoformat(line["created_on"]) <= origin
        ):
            target_projects[(line["iso_week"], line["role_id"])].add(
                line["project_id"]
            )

    project_weights: dict[tuple[str, str, str], float] = {}
    for target_week, role_id in baseline:
        project_ids = set(target_projects[(target_week, role_id)])
        for history_week in trailing:
            project_ids.update(historical_weights[(history_week, role_id)])
        for project_id in project_ids:
            project_weights[(target_week, project_id, role_id)] = sum(
                historical_weights[(history_week, role_id)].get(project_id, 0.0)
                for history_week in trailing
            )

    pipeline_weights: dict[tuple[str, str, str], float] = defaultdict(float)
    for line in lines:
        if (
            line["status"] != "Approved"
            or line["iso_week"] not in target_set
            or date.fromisoformat(line["created_on"]) > origin
        ):
            continue
        key = (line["iso_week"], line["project_id"], line["role_id"])
        pipeline_weights.setdefault(key, 0.0)
        lifecycle = _state_at(projects[line["project_id"]], origin)
        pipeline_weights[key] += float(line["required_fte"]) * float(
            confidence.get(lifecycle, 0.0)
        )
    for week, project_id, role_id in project_weights:
        pipeline_weights.setdefault((week, project_id, role_id), 0.0)

    return (
        baseline,
        pipeline,
        _reconcile_project_predictions(baseline, project_weights),
        _reconcile_project_predictions(pipeline, dict(pipeline_weights)),
    )


def _metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    denominator = sum(actual)
    return {
        "wape": round(
            sum(abs(a - p) for a, p in zip(actual, predicted)) / denominator, 8
        ) if denominator else 0.0,
        "bias": round((sum(predicted) - denominator) / denominator, 8)
        if denominator else 0.0,
    }


def _realization_ratio(
    lines: list[dict],
    projects: dict[str, dict],
    weeks: list[dict],
    origin: date,
    confidence: dict[str, float],
    config: dict[str, float | int],
) -> float:
    historical_weeks = [
        str(row["iso_week"]) for row in weeks
        if date.fromisoformat(str(row["week_start"])) <= origin
    ]
    horizon = int(config["training_horizon_weeks"])
    current_index = len(historical_weeks) - 1
    actuals = _actuals(lines, origin)
    roles = sorted({role_id for _, role_id in actuals})
    realized_total = 0.0
    predicted_total = 0.0

    for train_index in range(3, current_index - horizon + 1, horizon):
        train_origin_week = historical_weeks[train_index]
        train_origin = date.fromisocalendar(
            int(train_origin_week[:4]), int(train_origin_week[-2:]), 7
        )
        targets = historical_weeks[train_index + 1:train_index + horizon + 1]
        if not targets:
            continue
        _, pipeline = _predictions(
            lines, projects, weeks, train_origin, targets, confidence
        )
        for target in targets:
            for role_id in roles:
                realized_total += actuals.get((target, role_id), 0.0)
                predicted_total += pipeline.get((target, role_id), 0.0)

    default = float(config["default"])
    if predicted_total <= 0:
        return default
    ratio = realized_total / predicted_total
    return min(float(config["maximum"]), max(float(config["minimum"]), ratio))


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
    baseline, pipeline, project_baseline, project_pipeline = _project_predictions(
        sources["demand_lines"], projects, weeks, as_of, future_weeks, confidence
    )
    ratio_config = load_settings().forecast["realization_ratio"]
    realization_ratio = _realization_ratio(
        sources["demand_lines"], projects, weeks, as_of, confidence, ratio_config
    )
    realized_pipeline = {
        key: value * realization_ratio for key, value in pipeline.items()
    }
    realized_project_pipeline = _reconcile_project_predictions(
        realized_pipeline, project_pipeline
    )
    forecast_rows = []
    for method, predictions in [
        ("moving_average_4w", baseline),
        ("pipeline_adjusted", pipeline),
        ("pipeline_realization_adjusted", realized_pipeline),
    ]:
        for (week, role_id), demand_fte in sorted(predictions.items()):
            forecast_rows.append({
                "iso_week": week,
                "role_id": role_id,
                "method": method,
                "forecast_demand_fte": round(demand_fte, 4),
            })
    project_forecast_rows = []
    for method, predictions in [
        ("moving_average_4w", project_baseline),
        ("pipeline_adjusted", project_pipeline),
        ("pipeline_realization_adjusted", realized_project_pipeline),
    ]:
        for (week, project_id, role_id), predicted_fte in sorted(predictions.items()):
            project_forecast_rows.append({
                "project_id": project_id,
                "role_id": role_id,
                "iso_week": week,
                "method": method,
                "predicted_fte": predicted_fte,
            })

    actuals = _actuals(sources["demand_lines"], as_of)
    project_actuals = _project_actuals(sources["demand_lines"], as_of)
    method_names = (
        "moving_average_4w", "pipeline_adjusted", "pipeline_realization_adjusted"
    )
    backtest: dict[str, list[dict]] = {method: [] for method in method_names}
    project_backtest: dict[str, list[dict]] = {
        method: [] for method in method_names
    }
    historic_weeks = [str(row["iso_week"]) for row in weeks if date.fromisoformat(str(row["week_start"])) <= as_of]
    for horizon in (4, 8, 12):
        pairs = {method: ([], []) for method in method_names}
        project_pairs = {method: ([], []) for method in method_names}
        origin_count = 0
        for origin_index in range(3, len(historic_weeks) - horizon):
            origin_count += 1
            origin_week = historic_weeks[origin_index]
            origin_date = date.fromisocalendar(int(origin_week[:4]), int(origin_week[-2:]), 7)
            targets = historic_weeks[origin_index + 1: origin_index + horizon + 1]
            avg, adjusted, project_avg, project_adjusted = _project_predictions(
                sources["demand_lines"], projects, weeks, origin_date, targets, confidence
            )
            ratio = _realization_ratio(
                sources["demand_lines"], projects, weeks, origin_date, confidence,
                ratio_config,
            )
            calibrated = {key: value * ratio for key, value in adjusted.items()}
            project_calibrated = _reconcile_project_predictions(
                calibrated, project_adjusted
            )
            for target in targets:
                for role_id in sorted({role for _, role in actuals}):
                    actual = actuals.get((target, role_id), 0.0)
                    pairs["moving_average_4w"][0].append(actual)
                    pairs["moving_average_4w"][1].append(avg.get((target, role_id), 0.0))
                    pairs["pipeline_adjusted"][0].append(actual)
                    pairs["pipeline_adjusted"][1].append(adjusted.get((target, role_id), 0.0))
                    pairs["pipeline_realization_adjusted"][0].append(actual)
                    pairs["pipeline_realization_adjusted"][1].append(calibrated.get((target, role_id), 0.0))
            for target in targets:
                known_project_roles = {
                    (project_id, role_id)
                    for week, project_id, role_id in project_actuals
                    if week == target
                }
                predicted_project_roles = {
                    (project_id, role_id)
                    for week, project_id, role_id in project_avg
                    if week == target
                }
                for project_id, role_id in known_project_roles | predicted_project_roles:
                    actual = project_actuals.get((target, project_id, role_id), 0.0)
                    for method, predictions in (
                        ("moving_average_4w", project_avg),
                        ("pipeline_adjusted", project_adjusted),
                        ("pipeline_realization_adjusted", project_calibrated),
                    ):
                        project_pairs[method][0].append(actual)
                        project_pairs[method][1].append(
                            predictions.get((target, project_id, role_id), 0.0)
                        )
        for method, (actual, predicted) in pairs.items():
            backtest[method].append({
                "horizon_weeks": horizon, "origins": origin_count,
                **_metrics(actual, predicted),
            })
        for method, (actual, predicted) in project_pairs.items():
            project_backtest[method].append({
                "horizon_weeks": horizon,
                "origins": origin_count,
                **_metrics(actual, predicted),
            })

    metrics = {
        "as_of": as_of.isoformat(),
        "forecast_weeks": len(future_weeks),
        "methods": backtest,
        "project_methods": project_backtest,
        "backtest_method": "rolling origin, observed weeks through W43, origin-specific created_on cutoff",
    }
    return forecast_rows, project_forecast_rows, metrics
