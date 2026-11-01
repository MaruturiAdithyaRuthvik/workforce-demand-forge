from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy
import pandas

from wdf import __version__


PRIMARY_KEYS = {
    "roles": "role_id", "skills": "skill_id", "proficiency_scale": "proficiency",
    "role_skills": "role_skill_id", "employees": "employee_id", "employee_skills": "employee_skill_id",
    "projects": "project_id", "demand_plans": "demand_id", "demand_lines": "demand_line_id",
    "leave": "leave_id", "holidays": "holiday_date", "allocations": "allocation_id",
    "training": "training_id", "lifecycle_events": "event_id", "availability": "availability_id",
    "utilization": "utilization_id", "supply": ("iso_week", "role_id", "skill_id"),
    "gap_analysis": "gap_id", "gap_actions": "gap_action_id",
}

FOREIGN_KEYS = {
    "role_skills": [("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id")],
    "employees": [("role_id", "roles", "role_id"), ("manager_id", "employees", "employee_id")],
    "employee_skills": [("employee_id", "employees", "employee_id"), ("skill_id", "skills", "skill_id")],
    "demand_plans": [("project_id", "projects", "project_id")],
    "demand_lines": [
        ("demand_id", "demand_plans", "demand_id"), ("project_id", "projects", "project_id"),
        ("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id"),
        ("supersedes_line_id", "demand_lines", "demand_line_id"),
    ],
    "leave": [("employee_id", "employees", "employee_id")],
    "allocations": [
        ("employee_id", "employees", "employee_id"), ("project_id", "projects", "project_id"),
        ("role_id", "roles", "role_id"), ("skill_basis_esk_id", "employee_skills", "employee_skill_id"),
    ],
    "training": [("employee_id", "employees", "employee_id"), ("skill_id", "skills", "skill_id")],
    "availability": [("employee_id", "employees", "employee_id")],
    "utilization": [("employee_id", "employees", "employee_id")],
    "supply": [("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id")],
    "gap_analysis": [("role_id", "roles", "role_id"), ("skill_id", "skills", "skill_id")],
    "gap_actions": [
        ("gap_id", "gap_analysis", "gap_id"), ("candidate_employee_id", "employees", "employee_id"),
        ("candidate_skill_id", "skills", "skill_id"),
    ],
}

ENUMS = {
    ("employees", "employment_type"): ["FT", "PT"],
    ("employees", "status"): ["Active", "Inactive"],
    ("projects", "priority"): ["Low", "Medium", "High", "Critical"],
    ("projects", "staffing_model"): ["Shared-Pool", "Dedicated-Team"],
    ("projects", "status"): ["Planned", "Active", "Completed", "Cancelled"],
    ("employee_skills", "currency_flag"): ["Current", "Stale"],
    ("demand_lines", "source"): ["PlanTool", "ResourceRequest"],
    ("demand_lines", "status"): ["Draft", "Approved", "Superseded"],
    ("leave", "status"): ["Approved", "Pending", "Rejected"],
    ("allocations", "status"): ["Proposed", "Active", "Completed", "Cancelled"],
    ("training", "status"): ["Planned", "Enrolled", "Completed", "Failed", "Cancelled"],
    ("gap_actions", "action_type"): ["Reverify", "Train", "Hire", "Reallocate", "Contract"],
    ("gap_actions", "owner_actor"): ["Employee", "Manager", "HR Partner", "IT/Ops Partner", "System Admin"],
    ("gap_actions", "status"): ["Proposed", "Approved", "InProgress", "Done", "Rejected", "Escalated"],
}

INSERT_ORDER = [
    "roles", "skills", "proficiency_scale", "projects", "employees", "role_skills",
    "employee_skills", "demand_plans", "demand_lines", "leave", "holidays", "training",
    "allocations", "lifecycle_events", "availability", "utilization", "supply",
    "gap_analysis", "gap_actions",
]


def _json_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_sha256(path: Path) -> str:
    if path.suffix == ".db":
        return hashlib.sha256(logical_database_dump(path).encode("utf-8")).hexdigest()
    return sha256(path)


def _sql_literal(value: Any) -> str:
    value = _json_value(value)
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def _table_columns(rows: list[dict]) -> list[str]:
    if rows:
        return list(rows[0])
    return []


def _column_type(rows: list[dict], column: str) -> str:
    values = [row.get(column) for row in rows if row.get(column) is not None]
    if values and all(isinstance(value, bool) or isinstance(value, int) for value in values):
        return "INTEGER"
    if values and all(isinstance(value, (int, float)) for value in values):
        return "REAL"
    return "TEXT"


def _sort_key(table: str, rows: list[dict]) -> list[dict]:
    key = PRIMARY_KEYS.get(table)
    if isinstance(key, tuple):
        return sorted(rows, key=lambda row: tuple(row[column] for column in key))
    if key:
        return sorted(rows, key=lambda row: row[key])
    return sorted(rows, key=lambda row: tuple(str(row.get(column, "")) for column in sorted(row)))


def _schema_sql(tables: dict[str, list[dict]]) -> str:
    statements = ["PRAGMA foreign_keys = ON;"]
    for table in sorted(tables):
        rows = tables[table]
        columns = _table_columns(rows)
        definitions = []
        key = PRIMARY_KEYS.get(table)
        key_fields = key if isinstance(key, tuple) else (key,) if key else ()
        for column in columns:
            definitions.append(f'"{column}" {_column_type(rows, column)}')
        if key_fields:
            definitions.append("PRIMARY KEY (" + ", ".join(f'"{field}"' for field in key_fields) + ")")
        for field, target, target_field in FOREIGN_KEYS.get(table, []):
            definitions.append(f'FOREIGN KEY ("{field}") REFERENCES "{target}"("{target_field}")')
        for (enum_table, field), values in ENUMS.items():
            if enum_table == table and field in columns:
                literals = ", ".join(_sql_literal(value) for value in values)
                definitions.append(f'CHECK ("{field}" IN ({literals}))')
        statements.append(f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(definitions) + "\n);")
    return "\n\n".join(statements) + "\n"


def _seed_sql(tables: dict[str, list[dict]]) -> str:
    statements = ["PRAGMA foreign_keys = ON;", "BEGIN TRANSACTION;"]
    ordered_names = [name for name in INSERT_ORDER if name in tables]
    ordered_names.extend(sorted(set(tables) - set(ordered_names)))
    for table in ordered_names:
        rows = _sort_key(table, tables[table])
        if not rows:
            continue
        columns = _table_columns(rows)
        column_sql = ", ".join(f'"{column}"' for column in columns)
        for row in rows:
            values = ", ".join(_sql_literal(row.get(column)) for column in columns)
            statements.append(f'INSERT INTO "{table}" ({column_sql}) VALUES ({values});')
    statements.append("COMMIT;")
    return "\n".join(statements) + "\n"


def _write_rows_csv(path: Path, rows: list[dict]) -> None:
    columns = _table_columns(rows)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in _sort_key(path.stem, rows):
            writer.writerow({column: _json_value(row.get(column)) for column in columns})


def _logical_dump(connection: sqlite3.Connection) -> str:
    tables = [
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    lines = []
    for table in tables:
        columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
        key = PRIMARY_KEYS.get(table)
        sort_columns = key if isinstance(key, tuple) else (key,) if key else tuple(columns)
        order_by = ", ".join(f'"{column}"' for column in sort_columns)
        for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY {order_by}'):
            values = ", ".join(_sql_literal(value) for value in row)
            names = ", ".join(f'"{column}"' for column in columns)
            lines.append(f'INSERT INTO "{table}" ({names}) VALUES ({values});')
    return "\n".join(lines) + "\n"


def write_exports(
    output: Path,
    sources: dict[str, list[dict]],
    derived: dict[str, list[dict]],
    ground_truth: list[dict],
    forecast_rows: list[dict],
    metrics: dict,
    validation_report: dict,
    seed: int,
    scale: str,
    command: str,
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    tables = {**sources, **derived}
    for name in sorted(tables):
        rows = _sort_key(name, tables[name])
        _write_rows_csv(output / f"{name}.csv", rows)
        (output / f"{name}.json").write_text(canonical_json(rows), encoding="utf-8", newline="\n")

    (output / "schema.sql").write_text(_schema_sql(tables), encoding="utf-8", newline="\n")
    (output / "seed.sql").write_text(_seed_sql(tables), encoding="utf-8", newline="\n")
    database = output / "workforce.db"
    connection = sqlite3.connect(database)
    try:
        connection.executescript((output / "schema.sql").read_text(encoding="utf-8"))
        connection.executescript((output / "seed.sql").read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()

    (output / "ground_truth").mkdir(exist_ok=True)
    gt_path = output / "ground_truth"
    gt_sorted = sorted(ground_truth, key=lambda row: row["record_id"])
    _write_rows_csv(gt_path / "ground_truth.csv", gt_sorted)
    (gt_path / "ground_truth.json").write_text(canonical_json(gt_sorted), encoding="utf-8", newline="\n")
    _write_rows_csv(output / "forecast.csv", forecast_rows)
    (output / "metrics.json").write_text(canonical_json(metrics), encoding="utf-8", newline="\n")
    (output / "validation_report.json").write_text(canonical_json(validation_report), encoding="utf-8", newline="\n")
    (output / "SOURCE_MANIFEST.md").write_text(
        "All records were generated synthetically. No external data or network requests are used.\n",
        encoding="utf-8", newline="\n",
    )

    entries = []
    for path in sorted(
        item for item in output.rglob("*")
        if item.is_file() and item.name != "manifest.json" and item.name != "repro_report.json"
    ):
        relative = path.relative_to(output).as_posix()
        entries.append({
            "file": relative,
            "rows": _csv_row_count(path) if path.suffix == ".csv" else None,
            "sha256": artifact_sha256(path),
            "hash_method": "logical_sql_dump" if path.suffix == ".db" else "file",
            "generator_version": __version__,
            "seed": seed,
            "command": command,
            "scale": scale,
        })
    manifest = {
        "generator_version": __version__, "seed": seed, "command": command,
        "scale": scale, "python_version": __import__("platform").python_version(),
        "numpy_version": numpy.__version__, "pandas_version": pandas.__version__,
        "files": entries,
    }
    (output / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8", newline="\n")
    return manifest


def refresh_manifest(output: Path) -> None:
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = []
    for path in sorted(
        item for item in output.rglob("*")
        if item.is_file() and item.name not in {"manifest.json", "repro_report.json"}
    ):
        entries.append({
            "file": path.relative_to(output).as_posix(),
            "rows": _csv_row_count(path) if path.suffix == ".csv" else None,
            "sha256": artifact_sha256(path),
            "hash_method": "logical_sql_dump" if path.suffix == ".db" else "file",
            "generator_version": manifest["generator_version"],
            "seed": manifest["seed"],
            "command": manifest["command"],
            "scale": manifest["scale"],
        })
    manifest["files"] = entries
    manifest_path.write_text(canonical_json(manifest), encoding="utf-8", newline="\n")


def _csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as file:
        return max(0, sum(1 for _ in csv.reader(file)) - 1)


def canonical_file_hashes(output: Path) -> dict[str, str]:
    return {
        path.relative_to(output).as_posix(): sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".sql"}
        and path.name not in {"repro_report.json"}
    }


def logical_database_dump(database: Path) -> str:
    connection = sqlite3.connect(database)
    try:
        return _logical_dump(connection)
    finally:
        connection.close()
