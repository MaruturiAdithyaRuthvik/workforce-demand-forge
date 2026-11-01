from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from wdf.anomalies import inject_anomalies
from wdf.config import load_scale, load_settings
from wdf.derived import compute_derived
from wdf.detect import detect_anomalies
from wdf.evaluate import evaluate_detections
from wdf.exports import canonical_file_hashes, logical_database_dump, refresh_manifest, write_exports
from wdf.forecast import forecast_data
from wdf.transactions import generate_sources
from wdf.validate import validate_data


SOURCE_TABLES = {
    "roles", "skills", "proficiency_scale", "role_skills", "employees", "employee_skills",
    "projects", "demand_plans", "demand_lines", "leave", "holidays", "allocations",
    "training", "lifecycle_events",
}
DERIVED_TABLES = {"availability", "utilization", "supply", "gap_analysis", "gap_actions"}


def build_data(scale: str, seed: int) -> tuple[dict, list[dict], dict, list[dict], dict, dict]:
    settings = load_settings()
    sizes = load_scale(scale)
    sources = generate_sources(seed, **sizes.model_dump())
    sources, ground_truth = inject_anomalies(sources, seed, settings.anomaly_rate)
    _ensure_failed_training_fixture(sources, settings.thresholds.model_dump())
    derived = compute_derived(sources, settings.thresholds.model_dump())
    _attach_derived_trace_ids(sources, ground_truth, derived)
    forecast_rows, forecast_metrics = forecast_data(sources, settings.forecast["confidence"], settings.as_of)
    detections = detect_anomalies(sources)
    evaluation = evaluate_detections(detections, ground_truth)
    validation = validate_data(sources, derived, settings.thresholds.model_dump())
    return sources, ground_truth, derived, forecast_rows, {
        "forecast": forecast_metrics,
        "evaluation": {"seed": seed, **evaluation},
        "detection_count": len(detections),
    }, validation


def _attach_derived_trace_ids(
    sources: dict[str, list[dict]], ground_truth: list[dict], derived: dict[str, list[dict]]
) -> None:
    line_by_id = {row["demand_line_id"]: row for row in sources["demand_lines"]}
    skill_by_id = {row["employee_skill_id"]: row for row in sources["employee_skills"]}
    employee_by_id = {row["employee_id"]: row for row in sources["employees"]}
    allocation_by_id = {row["allocation_id"]: row for row in sources["allocations"]}
    for truth in ground_truth:
        record_id = truth["record_id"]
        affected = set()
        if record_id in line_by_id:
            line = line_by_id[record_id]
            affected.update(
                row["gap_id"] for row in derived["gap_analysis"]
                if row["iso_week"] == line["iso_week"] and row["role_id"] == line["role_id"]
                and row["skill_id"] == line["skill_id"]
            )
        elif record_id in skill_by_id:
            skill = skill_by_id[record_id]
            role_id = employee_by_id[skill["employee_id"]]["role_id"]
            affected.update(
                row["gap_id"] for row in derived["gap_analysis"]
                if row["role_id"] == role_id and row["skill_id"] == skill["skill_id"]
            )
        elif record_id in allocation_by_id:
            allocation = allocation_by_id[record_id]
            start = date.fromisoformat(allocation["start_date"])
            end = date.fromisoformat(allocation["end_date"])
            affected.update(
                row["utilization_id"] for row in derived["utilization"]
                if row["employee_id"] == allocation["employee_id"]
                and start <= date.fromisocalendar(2026, int(row["iso_week"][-2:]), 1) + timedelta(days=6)
                and end >= date.fromisocalendar(2026, int(row["iso_week"][-2:]), 1)
            )
        truth["affected_derived_ids"] = sorted(affected)
        if not affected:
            truth["affected_derived_ids"] = []


def _ensure_failed_training_fixture(sources: dict[str, list[dict]], thresholds: dict) -> None:
    preview = compute_derived(sources, thresholds)
    train_action = next(
        (row for row in preview["gap_actions"] if row["action_type"] == "Train"), None
    )
    if train_action is None:
        return
    gap = next(row for row in preview["gap_analysis"] if row["gap_id"] == train_action["gap_id"])
    week_start = date.fromisocalendar(2026, int(gap["iso_week"][-2:]), 1)
    training_number = max(
        (int(row["training_id"].split("-")[-1]) for row in sources["training"]), default=0
    ) + 1
    training_id = f"TRN-{training_number:06d}"
    sources["training"].append({
        "training_id": training_id,
        "employee_id": train_action["candidate_employee_id"],
        "skill_id": gap["skill_id"],
        "target_proficiency": 3,
        "cost": 900.0,
        "start_date": week_start.isoformat(),
        "end_date": (week_start + timedelta(days=14)).isoformat(),
        "status": "Failed",
    })
    sources["lifecycle_events"].append({
        "event_id": "",
        "entity_type": "Training",
        "entity_id": training_id,
        "from_state": None,
        "to_state": "Failed",
        "effective_date": week_start.isoformat(),
        "reason": "Synthetic failed training exception fixture",
    })
    sources["lifecycle_events"].sort(
        key=lambda event: (event["entity_type"], event["entity_id"], event["effective_date"])
    )
    from wdf.ids import entity_id

    for index, event in enumerate(sources["lifecycle_events"], start=1):
        event["event_id"] = entity_id("EVT", index)


def run_generate(output: Path, scale: str, seed: int, include_heldout: bool = True) -> dict:
    sources, ground_truth, derived, forecast_rows, metrics, validation = build_data(scale, seed)
    if include_heldout:
        heldout_seed = seed + 1
        heldout_sources = generate_sources(heldout_seed, **load_scale(scale).model_dump())
        heldout_sources, heldout_truth = inject_anomalies(
            heldout_sources, heldout_seed, load_settings().anomaly_rate
        )
        _ensure_failed_training_fixture(
            heldout_sources, load_settings().thresholds.model_dump()
        )
        heldout_evaluation = evaluate_detections(
            detect_anomalies(heldout_sources), heldout_truth
        )
        metrics["evaluation"]["held_out_seed"] = {
            "seed": heldout_seed, **heldout_evaluation,
        }
    manifest = write_exports(
        output, sources, derived, ground_truth, forecast_rows, metrics, validation,
        seed, scale, f"wdf generate --scale {scale} --seed {seed}",
    )
    return {"manifest": manifest, "metrics": metrics, "validation": validation}


def read_source_tables(path: Path) -> dict[str, list[dict]]:
    import json

    sources = {}
    for table in sorted(SOURCE_TABLES):
        table_path = path / f"{table}.json"
        if not table_path.is_file():
            raise FileNotFoundError(f"Required table export not found: {table_path}")
        sources[table] = json.loads(table_path.read_text(encoding="utf-8"))
    return sources


def read_output(path: Path) -> tuple[dict[str, list[dict]], dict[str, list[dict]], list[dict]]:
    import json

    sources = read_source_tables(path)
    derived = {}
    for table in sorted(DERIVED_TABLES):
        table_path = path / f"{table}.json"
        if not table_path.is_file():
            raise FileNotFoundError(f"Required table export not found: {table_path}")
        derived[table] = json.loads(table_path.read_text(encoding="utf-8"))
    truth_path = path / "ground_truth" / "ground_truth.json"
    ground_truth = json.loads(truth_path.read_text(encoding="utf-8"))
    return sources, derived, ground_truth


def run_validation(path: Path) -> dict:
    sources, derived, _truth = read_output(path)
    settings = load_settings()
    report = validate_data(sources, derived, settings.thresholds.model_dump())
    from wdf.exports import canonical_json

    (path / "validation_report.json").write_text(canonical_json(report), encoding="utf-8", newline="\n")
    refresh_manifest(path)
    return report


def run_detection(path: Path) -> list[dict]:
    sources = read_source_tables(path)
    detections = detect_anomalies(sources)
    from wdf.exports import canonical_json

    (path / "detections.json").write_text(canonical_json(detections), encoding="utf-8", newline="\n")
    from wdf.exports import _write_rows_csv

    _write_rows_csv(path / "detections.csv", detections)
    refresh_manifest(path)
    return detections


def run_evaluation(path: Path) -> dict:
    sources, _derived, ground_truth = read_output(path)
    from wdf.exports import canonical_json

    detections = detect_anomalies(sources)
    main = evaluate_detections(detections, ground_truth)
    import json

    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    heldout_seed = int(manifest["seed"]) + 1
    heldout_sources = generate_sources(heldout_seed, **load_scale(manifest["scale"]).model_dump())
    heldout_sources, heldout_truth = inject_anomalies(
        heldout_sources, heldout_seed, load_settings().anomaly_rate
    )
    heldout = evaluate_detections(detect_anomalies(heldout_sources), heldout_truth)
    metrics_path = path / "metrics.json"
    current_metrics: dict[str, Any] = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    current_metrics["evaluation"] = {
        "seed": int(manifest["seed"]), **main,
        "held_out_seed": {"seed": heldout_seed, **heldout},
    }
    metrics_path.write_text(canonical_json(current_metrics), encoding="utf-8", newline="\n")
    refresh_manifest(path)
    return current_metrics["evaluation"]


def run_forecast(path: Path) -> dict:
    import json

    sources, _derived, _truth = read_output(path)
    settings = load_settings()
    rows, metrics = forecast_data(sources, settings.forecast["confidence"], settings.as_of)
    from wdf.exports import _write_rows_csv, canonical_json

    _write_rows_csv(path / "forecast.csv", rows)
    metrics_path = path / "metrics.json"
    current = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    current["forecast"] = metrics
    metrics_path.write_text(canonical_json(current), encoding="utf-8", newline="\n")
    refresh_manifest(path)
    return metrics


def run_repro(output: Path, scale: str, seed: int) -> dict:
    import hashlib
    import platform
    import tempfile

    import numpy
    import pandas

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wdf-repro-a-", dir=output) as temp_a:
        with tempfile.TemporaryDirectory(prefix="wdf-repro-b-", dir=output) as temp_b:
            path_a, path_b = Path(temp_a), Path(temp_b)
            manifest_a = run_generate(path_a, scale, seed, include_heldout=False)["manifest"]
            manifest_b = run_generate(path_b, scale, seed, include_heldout=False)["manifest"]
            hashes_a, hashes_b = canonical_file_hashes(path_a), canonical_file_hashes(path_b)
            dump_a = logical_database_dump(path_a / "workforce.db")
            dump_b = logical_database_dump(path_b / "workforce.db")
            row_counts_a = {
                entry["file"]: entry["rows"] for entry in manifest_a["files"]
                if entry["file"].endswith(".csv")
            }
            row_counts_b = {
                entry["file"]: entry["rows"] for entry in manifest_b["files"]
                if entry["file"].endswith(".csv")
            }

    with tempfile.TemporaryDirectory(prefix="wdf-repro-seed-", dir=output) as temp_seed:
        seed_path = Path(temp_seed)
        run_generate(seed_path, scale, seed + 1, include_heldout=False)
        hashes_different_seed = canonical_file_hashes(seed_path)

    same = hashes_a == hashes_b and dump_a == dump_b
    different = hashes_a != hashes_different_seed
    same_rows = row_counts_a == row_counts_b
    report = {
        "status": "PASS" if same and different and same_rows else "FAIL",
        "same_seed_hashes_match": hashes_a == hashes_b,
        "same_seed_logical_database_match": dump_a == dump_b,
        "same_seed_logical_database_sha256": {
            "run_a": hashlib.sha256(dump_a.encode("utf-8")).hexdigest(),
            "run_b": hashlib.sha256(dump_b.encode("utf-8")).hexdigest(),
        },
        "same_seed_file_sha256": {
            name: {"run_a": hashes_a[name], "run_b": hashes_b[name]}
            for name in sorted(hashes_a.keys() | hashes_b.keys())
        },
        "same_seed_row_counts_match": same_rows,
        "same_seed_csv_row_counts": {
            name: {"run_a": row_counts_a.get(name), "run_b": row_counts_b.get(name)}
            for name in sorted(row_counts_a.keys() | row_counts_b.keys())
        },
        "different_seed_hashes_differ": different,
        "different_seed_sha256": hashes_different_seed,
        "different_seed_changed_files": sorted(
            name for name in hashes_a.keys() | hashes_different_seed.keys()
            if hashes_a.get(name) != hashes_different_seed.get(name)
        ),
        "file_count": len(hashes_a),
        "sha256": hashes_a,
        "python_version": platform.python_version(),
        "numpy_version": numpy.__version__,
        "pandas_version": pandas.__version__,
    }
    from wdf.exports import canonical_json

    (output / "repro_report.json").write_text(canonical_json(report), encoding="utf-8", newline="\n")
    return report
