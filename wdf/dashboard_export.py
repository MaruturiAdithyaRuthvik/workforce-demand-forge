from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAX_EXPORT_BYTES = 5_000_000
METHODS = (
    "moving_average_4w",
    "pipeline_adjusted",
    "pipeline_realization_adjusted",
)
ISSUE_TYPES = (
    "ALLOC_EXCEEDS_AVAILABILITY",
    "STALE_SKILL_TREATED_CURRENT",
    "DEMAND_DOUBLE_COUNTED",
    "OVERLAPPING_PROJECT_ASSIGNMENT",
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required dashboard input is missing: {path}")
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required dashboard input is missing: {path}")
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _number(row: dict[str, str], field: str) -> float:
    value = row.get(field, "")
    return float(value) if value else 0.0


def _ids(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("Expected a JSON string array in a dashboard trace field")
    return parsed


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _compact_analytics(analytics: dict[str, Any]) -> dict[str, Any]:
    role_index = {
        row["role_id"]: index
        for index, row in enumerate(analytics["selectors"]["roles"])
    }
    project_index = {
        row["project_id"]: index
        for index, row in enumerate(analytics["selectors"]["projects"])
    }
    methods = analytics["selectors"]["methods"]
    analytics["forecast"]["series_columns"] = [
        "role_index", "project_index", "week", "actual", *methods
    ]
    analytics["forecast"]["series"] = [
        [
            role_index[row["role_id"]],
            project_index[row["project_id"]] if row["project_id"] is not None else None,
            row["week"],
            row["actual"],
            *[row[method] for method in methods],
        ]
        for row in analytics["forecast"]["series"]
    ]

    gaps = analytics["skill_gaps"]
    gaps["heatmap_columns"] = ["role_family", "week", "gap_fte"]
    gaps["heatmap"] = [
        [row["role_family"], row["week"], row["gap_fte"]]
        for row in gaps["heatmap"]
    ]
    gaps["trace_columns"] = [
        "gap_id", "iso_week", "role_id", "role_title", "role_family", "skill_id",
        "skill_name", "demand_fte", "supply_fte", "gap_fte", "risk_level",
        "demand_lines", "supporting_skills", "candidate_action_ids",
    ]
    gaps["demand_line_columns"] = [
        "demand_line_id", "project_id", "required_fte", "min_proficiency",
    ]
    gaps["support_columns"] = [
        "employee_skill_id", "skill_id", "skill_name", "proficiency",
    ]
    gaps["traces"] = [
        [
            *[row[field] for field in gaps["trace_columns"][:11]],
            [
                [
                    line["demand_line_id"],
                    line["project_id"],
                    line["required_fte"],
                    line["min_proficiency"],
                ]
                for line in row["demand_lines"]
            ],
            [
                [
                    skill["employee_skill_id"],
                    skill["skill_id"],
                    skill["skill_name"],
                    skill["proficiency"],
                ]
                for skill in row["supporting_skills"]
            ],
            [action["gap_action_id"] for action in row["candidate_actions"]],
        ]
        for row in gaps["traces"]
    ]

    action_columns = [
        "gap_action_id", "gap_id", "action_type", "candidate_employee_id",
        "candidate_skill_id", "owner", "status", "rule_id", "estimated_cost",
        "assumptions",
    ]
    analytics["decisions"] = {
        "action_columns": action_columns,
        "actions": [
            [
                row[field]
                if field != "assumptions" or not row["assumptions"].startswith(row["rule_id"] + ": ")
                else row["assumptions"][len(row["rule_id"]) + 2:]
                for field in action_columns
            ]
            for row in analytics["decisions"]["actions"]
        ],
        "owners": analytics["decisions"]["owners"],
        "statuses": analytics["decisions"]["statuses"],
        "rules": analytics["decisions"]["rules"],
    }
    return analytics


def _week_key(week: str) -> tuple[int, int]:
    year, number = week.split("W", maxsplit=1)
    return int(year), int(number)


def _week_labels() -> list[str]:
    return [f"2026W{week:02d}" for week in range(1, 54)]


def _near_miss_counts(
    source: dict[str, list[dict[str, str]]],
    detections: set[tuple[str, str]],
    as_of: date,
) -> list[dict[str, Any]]:
    projects = {row["project_id"]: row for row in source["projects"]}
    allocation_weeks: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for allocation in source["allocations"]:
        if allocation["status"] not in {"Proposed", "Active"}:
            continue
        start = date.fromisoformat(allocation["start_date"])
        end = date.fromisoformat(allocation["end_date"])
        monday = start - timedelta(days=start.weekday())
        while monday <= end:
            iso = monday.isocalendar()
            week = f"{iso.year}W{iso.week:02d}"
            allocation_weeks[(allocation["employee_id"], week)].append(allocation)
            monday += timedelta(days=7)

    exact_capacity_ids = {
        row["allocation_id"]
        for rows in allocation_weeks.values()
        if (shared := [
            row for row in rows
            if projects[row["project_id"]]["staffing_model"] == "Shared-Pool"
        ])
        and len(shared) >= 2
        and sum(_number(row, "allocation_pct") for row in shared) == 1.0
        for row in shared
    }
    expiry_boundary_ids = {
        row["employee_skill_id"]
        for row in source["employee_skills"]
        if row["expiry_date"] == as_of.isoformat() and row["currency_flag"] == "Current"
    }

    demand_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in source["demand_lines"]:
        if row["status"] == "Approved":
            demand_groups[(row["project_id"], row["role_id"], row["skill_id"])].append(row)
    adjacent_demand_ids: set[str] = set()
    for rows in demand_groups.values():
        ordered = sorted(rows, key=lambda row: row["iso_week"])
        for first, second in zip(ordered, ordered[1:]):
            first_year, first_week = _week_key(first["iso_week"])
            second_year, second_week = _week_key(second["iso_week"])
            if first_year == second_year and second_week == first_week + 1:
                adjacent_demand_ids.update((first["demand_line_id"], second["demand_line_id"]))

    dedicated_by_employee: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source["allocations"]:
        if projects[row["project_id"]]["staffing_model"] == "Dedicated-Team":
            dedicated_by_employee[row["employee_id"]].append(row)
    adjacent_dedicated_ids: set[str] = set()
    for rows in dedicated_by_employee.values():
        for first in rows:
            for second in rows:
                first_end = date.fromisoformat(first["end_date"])
                if (
                    first["project_id"] != second["project_id"]
                    and first_end.weekday() == 6
                    and first_end + timedelta(days=1) == date.fromisoformat(second["start_date"])
                ):
                    adjacent_dedicated_ids.update((first["allocation_id"], second["allocation_id"]))

    groups = (
        ("ALLOC_EXCEEDS_AVAILABILITY", exact_capacity_ids),
        ("STALE_SKILL_TREATED_CURRENT", expiry_boundary_ids),
        ("DEMAND_DOUBLE_COUNTED", adjacent_demand_ids),
        ("OVERLAPPING_PROJECT_ASSIGNMENT", adjacent_dedicated_ids),
    )
    return [
        {
            "issue_type": issue_type,
            "records": len(record_ids),
            "detected": sum((record_id, issue_type) in detections for record_id in record_ids),
        }
        for issue_type, record_ids in groups
    ]


def _evaluation_data(
    input_dir: Path,
    metrics: dict[str, Any],
    manifest: dict[str, Any],
    as_of: date,
) -> dict[str, Any]:
    truth_rows = _read_rows(input_dir / "ground_truth" / "ground_truth.csv")
    detection_rows = _read_rows(input_dir / "detections.csv")
    truth_counts: dict[str, int] = defaultdict(int)
    detection_counts: dict[str, int] = defaultdict(int)
    detections: set[tuple[str, str]] = set()
    for row in truth_rows:
        truth_counts[row["issue_type"]] += 1
    for row in detection_rows:
        detection_counts[row["issue_type"]] += 1
        detections.add((row["record_id"], row["issue_type"]))

    by_issue_type = []
    for issue_type in sorted(set(truth_counts) | set(detection_counts)):
        injected = truth_counts[issue_type]
        detected = detection_counts[issue_type]
        true_positive = sum(
            (row["record_id"], issue_type) in detections
            for row in truth_rows
            if row["issue_type"] == issue_type
        )
        false_positive = detected - true_positive
        false_negative = injected - true_positive
        precision = true_positive / detected if detected else 0.0
        recall = true_positive / injected if injected else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        by_issue_type.append({
            "issue_type": issue_type,
            "injected": injected,
            "detected": detected,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        })

    source = {
        table: _read_rows(input_dir / f"{table}.csv")
        for table in (
            "projects",
            "allocations",
            "employee_skills",
            "demand_lines",
        )
    }
    evaluations = metrics.get("evaluation", {})
    return {
        "evaluation_only": True,
        "label": "Evaluation only — synthetic ground-truth comparison",
        "seed": manifest["seed"],
        "by_issue_type": by_issue_type,
        "held_out": evaluations.get("held_out_seed"),
        "near_misses": _near_miss_counts(source, detections, as_of),
    }


def _reproducibility(input_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    report_path = input_dir.parent / "repro_report.json"
    versions = {
        "python": manifest.get("python_version"),
        "numpy": manifest.get("numpy_version"),
        "pandas": manifest.get("pandas_version"),
    }
    if not report_path.is_file():
        return {
            "hash_match": None,
            "status": "Not verified",
            "seed": manifest["seed"],
            "versions": versions,
        }

    report = _read_json(report_path)
    expected_hashes = {
        entry["file"]: entry["sha256"]
        for entry in manifest["files"]
    }
    report_hashes = report.get("sha256", {})
    hash_match = (
        report.get("same_seed_hashes_match") is True
        and report.get("same_seed_row_counts_match") is True
        and report_hashes == expected_hashes
    )
    return {
        "hash_match": hash_match,
        "status": "Verified" if hash_match else "No matching same-seed proof",
        "seed": manifest["seed"],
        "versions": versions,
        "file_count": len(expected_hashes),
        "logical_database_hash_match": (
            report.get("same_seed_logical_database_match") is True if hash_match else None
        ),
    }


def build_dashboard_data(input_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    input_dir = input_dir.resolve()
    manifest = _read_json(input_dir / "manifest.json")
    metrics = _read_json(input_dir / "metrics.json")
    validation = _read_json(input_dir / "validation_report.json")
    as_of = date.fromisoformat(metrics["forecast"]["as_of"])

    role_rows = _read_rows(input_dir / "roles.csv")
    project_rows = _read_rows(input_dir / "projects.csv")
    demand_rows = _read_rows(input_dir / "demand_lines.csv")
    supply_rows = _read_rows(input_dir / "supply.csv")
    gap_rows = _read_rows(input_dir / "gap_analysis.csv")
    action_rows = _read_rows(input_dir / "gap_actions.csv")
    utilization_rows = _read_rows(input_dir / "utilization.csv")
    role_forecasts = _read_rows(input_dir / "forecast.csv")
    project_forecasts = _read_rows(input_dir / "forecast_project.csv")

    roles = {
        row["role_id"]: {
            "role_id": row["role_id"],
            "title": row["title"],
            "family": row["family"],
        }
        for row in role_rows
    }
    projects = {
        row["project_id"]: {
            "project_id": row["project_id"],
            "label": row["project_id"],
        }
        for row in project_rows
    }
    skills = {
        row["skill_id"]: row["name"]
        for row in _read_rows(input_dir / "skills.csv")
    }
    employee_skills = {
        row["employee_skill_id"]: row
        for row in _read_rows(input_dir / "employee_skills.csv")
    }

    actual_role: dict[tuple[str, str], float] = defaultdict(float)
    actual_project: dict[tuple[str, str, str], float] = defaultdict(float)
    approved_demand_rows = 0
    for row in demand_rows:
        if row["status"] != "Approved" or date.fromisoformat(row["created_on"]) > as_of:
            continue
        if _week_key(row["iso_week"]) > (as_of.isocalendar().year, as_of.isocalendar().week):
            continue
        amount = _number(row, "required_fte")
        actual_role[(row["role_id"], row["iso_week"])] += amount
        actual_project[(row["project_id"], row["role_id"], row["iso_week"])] += amount
        approved_demand_rows += 1

    role_forecast_values: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in role_forecasts:
        role_forecast_values[(row["role_id"], row["iso_week"])][row["method"]] = _number(
            row, "forecast_demand_fte"
        )
    project_forecast_values: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
    for row in project_forecasts:
        project_forecast_values[(row["project_id"], row["role_id"], row["iso_week"])][row["method"]] = _number(
            row, "predicted_fte"
        )

    role_weeks = set(actual_role) | set(role_forecast_values)
    forecast_series = [
        {
            "role_id": role_id,
            "project_id": None,
            "week": week,
            "actual": round(actual_role.get((role_id, week), 0.0), 6)
            if (role_id, week) in actual_role else None,
            **{
                method: round(role_forecast_values.get((role_id, week), {}).get(method, 0.0), 6)
                if method in role_forecast_values.get((role_id, week), {}) else None
                for method in METHODS
            },
        }
        for role_id, week in sorted(role_weeks, key=lambda key: (key[0], _week_key(key[1])))
    ]
    project_weeks = set(actual_project) | set(project_forecast_values)
    forecast_series.extend(
        {
            "role_id": role_id,
            "project_id": project_id,
            "week": week,
            "actual": round(actual_project.get((project_id, role_id, week), 0.0), 6)
            if (project_id, role_id, week) in actual_project else None,
            **{
                method: round(
                    project_forecast_values.get((project_id, role_id, week), {}).get(method, 0.0),
                    6,
                )
                if method in project_forecast_values.get((project_id, role_id, week), {}) else None
                for method in METHODS
            },
        }
        for project_id, role_id, week in sorted(
            project_weeks,
            key=lambda key: (key[1], key[0], _week_key(key[2])),
        )
    )

    demand_by_week: dict[str, float] = defaultdict(float)
    supply_by_week: dict[str, float] = defaultdict(float)
    for (role_id, week), amount in actual_role.items():
        demand_by_week[week] += amount
    for row in supply_rows:
        supply_by_week[row["iso_week"]] += _number(row, "supply_fte")
    future_pipeline: dict[str, float] = defaultdict(float)
    for (role_id, week), values in role_forecast_values.items():
        if _week_key(week) > (as_of.isocalendar().year, as_of.isocalendar().week):
            future_pipeline[week] += values.get("pipeline_realization_adjusted", 0.0)
    overview_series = [
        {
            "week": week,
            "actual_demand": round(demand_by_week[week], 4)
            if _week_key(week) <= (as_of.isocalendar().year, as_of.isocalendar().week)
            else None,
            "forecast_demand": round(future_pipeline[week], 4)
            if _week_key(week) > (as_of.isocalendar().year, as_of.isocalendar().week)
            else None,
            "supply": round(supply_by_week[week], 4),
        }
        for week in _week_labels()
    ]

    demand_by_id = {row["demand_line_id"]: row for row in demand_rows}
    project_label = {key: value["label"] for key, value in projects.items()}
    actions_by_gap: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actions = []
    for row in action_rows:
        action = {
            "gap_action_id": row["gap_action_id"],
            "gap_id": row["gap_id"] or None,
            "action_type": row["action_type"],
            "candidate_employee_id": row["candidate_employee_id"] or None,
            "candidate_skill_id": row["candidate_skill_id"] or None,
            "source_utilization_id": row["source_utilization_id"] or None,
            "source_allocation_ids": _ids(row["source_allocation_ids"]),
            "owner": {
                "HR Partner": "HR Partner",
                "IT/Ops Partner": "IT/Ops",
                "System Admin": "Admin",
            }.get(row["owner_actor"], row["owner_actor"]),
            "status": row["status"],
            "rule_id": row["rule_id"],
            "lead_time_weeks": int(row["lead_time_weeks"]),
            "estimated_cost": round(_number(row, "estimated_cost"), 2),
            "assumptions": row["assumptions"],
        }
        actions.append(action)
        if action["gap_id"] is not None:
            actions_by_gap[action["gap_id"]].append(action)

    heatmap_values: dict[tuple[str, str], float] = defaultdict(float)
    gap_traces = []
    for row in gap_rows:
        role = roles[row["role_id"]]
        heatmap_values[(role["family"], row["iso_week"])] += _number(row, "gap_fte")
        line_details = []
        for line_id in _ids(row["source_demand_line_ids"]):
            line = demand_by_id[line_id]
            line_details.append({
                "demand_line_id": line_id,
                "project_id": project_label[line["project_id"]],
                "required_fte": round(_number(line, "required_fte"), 4),
                "min_proficiency": int(line["min_proficiency"]),
            })
        supporting_skills = []
        for esk_id in _ids(row["supporting_esk_ids"]):
            skill_row = employee_skills[esk_id]
            supporting_skills.append({
                "employee_skill_id": esk_id,
                "employee_id": skill_row["employee_id"],
                "skill_id": skill_row["skill_id"],
                "skill_name": skills[skill_row["skill_id"]],
                "proficiency": int(skill_row["proficiency"]),
                "expiry_date": skill_row["expiry_date"],
            })
        gap_traces.append({
            "gap_id": row["gap_id"],
            "iso_week": row["iso_week"],
            "role_id": row["role_id"],
            "role_title": role["title"],
            "role_family": role["family"],
            "skill_id": row["skill_id"],
            "skill_name": skills[row["skill_id"]],
            "demand_fte": round(_number(row, "demand_fte"), 4),
            "supply_fte": round(_number(row, "supply_fte"), 4),
            "gap_fte": round(_number(row, "gap_fte"), 4),
            "risk_level": row["risk_level"],
            "demand_lines": line_details,
            "supporting_skills": supporting_skills,
            "candidate_actions": actions_by_gap.get(row["gap_id"], []),
        })
    families = sorted({row["family"] for row in role_rows})
    heatmap = [
        {
            "role_family": family,
            "week": week,
            "gap_fte": round(heatmap_values.get((family, week), 0.0), 4),
        }
        for family in families
        for week in _week_labels()
    ]

    report_checks = validation.get("checks", {})
    warnings = validation.get("warnings", [])
    error_count = len(validation.get("errors", []))
    overutilized_weeks = sum(row["risk_level"] == "Overutilized" for row in utilization_rows)
    open_gaps = sum(_number(row, "gap_fte") > 0 for row in gap_rows)
    escalations = sum(row["status"] == "Escalated" for row in actions)
    detection_count = int(metrics["detection_count"])
    row_counts = {
        entry["file"].removesuffix(".csv"): entry["rows"]
        for entry in manifest["files"]
        if entry["file"].endswith(".csv")
        and "/" not in entry["file"]
        and entry["file"] != "detections.csv"
    }
    validation_checks = [
        {"name": "Validation status", "value": validation["status"], "status": validation["status"].lower()},
        {"name": "Structural errors", "value": error_count, "status": "pass" if error_count == 0 else "fail"},
        {"name": "Warnings", "value": len(warnings), "status": "review" if warnings else "pass"},
        {
            "name": "Capacity weeks reconciled",
            "value": report_checks.get("capacity_weeks_reconciled", 0),
            "status": "pass" if report_checks.get("capacity_weeks_reconciled") == 53 else "fail",
        },
        {
            "name": "Derived tables recomputed",
            "value": report_checks.get("derived_tables_recomputed", False),
            "status": "pass" if report_checks.get("derived_tables_recomputed") is True else "fail",
        },
        {
            "name": "Role forecast rows reconciled",
            "value": report_checks.get("forecast_role_rows_reconciled", 0),
            "status": "pass" if report_checks.get("forecast_role_rows_reconciled", 0) > 0 else "fail",
        },
        {
            "name": "Project forecast rows",
            "value": len(project_forecasts),
            "status": "pass" if project_forecasts else "fail",
        },
    ]
    attention = []
    if open_gaps:
        attention.append({"label": "Open skill gaps", "count": open_gaps, "detail": "Positive demand gaps need review."})
    if escalations:
        attention.append({"label": "Escalated actions", "count": escalations, "detail": "Review budget and ownership."})
    if overutilized_weeks:
        attention.append({
            "label": "Over-utilized employee-weeks",
            "count": overutilized_weeks,
            "detail": "Reallocation and contract actions are available.",
        })
    if warnings:
        attention.append({"label": "Validation warnings", "count": len(warnings), "detail": "Synthetic anomaly fixtures are expected."})

    analytics = {
        "metadata": {
            "dataset_scale": manifest["scale"],
            "seed": manifest["seed"],
            "as_of": as_of.isoformat(),
            "generator_version": manifest["generator_version"],
            "versions": {
                "python": manifest.get("python_version"),
                "numpy": manifest.get("numpy_version"),
                "pandas": manifest.get("pandas_version"),
            },
            "record_counts": row_counts,
        },
        "overview": {
            "open_gaps": open_gaps,
            "candidate_actions": len(actions),
            "overutilized_weeks": overutilized_weeks,
            "anomalies_found": detection_count,
            "data_health": validation["status"],
            "attention": attention,
            "series": overview_series,
        },
        "selectors": {
            "roles": sorted(roles.values(), key=lambda row: row["role_id"]),
            "projects": sorted(projects.values(), key=lambda row: row["project_id"]),
            "methods": list(METHODS),
        },
        "forecast": {
            "as_of": as_of.isoformat(),
            "series": forecast_series,
            "backtest": metrics["forecast"],
        },
        "skill_gaps": {
            "weeks": _week_labels(),
            "families": families,
            "heatmap": heatmap,
            "traces": gap_traces,
        },
        "decisions": {
            "actions": actions,
            "owners": ["Manager", "HR Partner", "IT/Ops", "Admin"],
            "statuses": sorted({row["status"] for row in actions}),
            "rules": sorted({row["rule_id"] for row in actions}),
        },
        "data_health": {
            "status": validation["status"],
            "checks": validation_checks,
            "warnings": warnings,
            "reproducibility": _reproducibility(input_dir, manifest),
        },
    }
    evaluation = _evaluation_data(input_dir, metrics, manifest, as_of)
    return analytics, evaluation


def export_dashboard(input_dir: Path, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or ROOT / "dashboard" / "public" / "data"
    analytics, evaluation = build_dashboard_data(input_dir)
    analytics = _compact_analytics(analytics)
    files = {
        "analytics.json": _canonical_json(analytics),
        "evaluation.json": _canonical_json(evaluation),
    }
    total_bytes = sum(len(content) for content in files.values())
    if total_bytes >= MAX_EXPORT_BYTES:
        raise ValueError(
            f"Dashboard data is {total_bytes} bytes; combined export must be below "
            f"{MAX_EXPORT_BYTES} bytes"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        temporary = output_dir / f".{name}.tmp"
        temporary.write_bytes(content)
        temporary.replace(output_dir / name)
    return {
        "files": sorted(files),
        "bytes": total_bytes,
        "sha256": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in sorted(files.items())
        },
    }
