from __future__ import annotations

from wdf.models import TABLE_MODELS


def render_data_dictionary() -> str:
    lines = [
        "# Data dictionary",
        "",
        "Generated from the Pydantic table models in `wdf/models.py`; rerun `python scripts/update_data_dictionary.py` after schema changes.",
        "",
    ]
    for table, model in TABLE_MODELS.items():
        schema = model.model_json_schema()
        required_fields = set(schema.get("required", []))
        lines.extend([f"## `{table}`", "", "| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |",
                      "|---|---|---|---|---|---|---|"])
        for field_name, definition in schema["properties"].items():
            description = definition.get("description", "")
            details = {}
            for entry in description.split(";"):
                if "=" in entry:
                    name, value = entry.split("=", 1)
                    details[name.strip()] = value.strip()
            field_type = definition.get("type", "object")
            if "anyOf" in definition:
                field_type = " | ".join(
                    item.get("type", "object") for item in definition["anyOf"]
                )
            if field_type == "array":
                item_type = definition.get("items", {}).get("type", "object")
                field_type = f"array<{item_type}>"
            allowed = ", ".join(str(value) for value in definition.get("enum", [])) or "—"
            required = "yes" if field_name in required_fields else "no"
            cells = [
                field_name, field_type, required, allowed,
                details.get("units", "not specified"),
                details.get("uniqueness", "not specified"),
                details.get("validation", "not specified"),
            ]
            lines.append("| " + " | ".join(value.replace("|", "\\|") for value in cells) + " |")
        lines.append("")
    lines.extend([
        "## Forecast outputs (derived CSVs, not SQLite tables)",
        "",
        "`forecast.csv` is keyed by `(iso_week, role_id, method)`. `forecast_project.csv` is keyed by `(project_id, role_id, iso_week, method)`. For each role/week/method, the sum of project `predicted_fte` reconciles to role-level `forecast_demand_fte` in `forecast.csv`. Backtest metrics for both levels are stored in `metrics.json`.",
        "",
        "| Field | Type | Required | Allowed values | Units | Uniqueness | Validation |",
        "|---|---|---|---|---|---|---|",
        "| project_id | string | yes | — | none | part of composite key | references a Project. |",
        "| role_id | string | yes | — | none | part of composite key | references a Role. |",
        "| iso_week | string | yes | — | ISO week | part of composite key | valid 2026 ISO week. |",
        "| method | string | yes | `moving_average_4w`, `pipeline_adjusted`, `pipeline_realization_adjusted` | none | part of composite key | one of the three backtested forecast methods. |",
        "| predicted_fte | number | yes | — | FTE | not unique | non-negative; project sums reconcile to the role-level forecast. |",
        "",
        "Role-level `forecast.csv` uses `role_id`, `iso_week`, and `method`, with `forecast_demand_fte` as its non-negative FTE value and `(iso_week, role_id, method)` as its key.",
        "",
    ])
    return "\n".join(lines).rstrip() + "\n"
