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
    return "\n".join(lines).rstrip() + "\n"
