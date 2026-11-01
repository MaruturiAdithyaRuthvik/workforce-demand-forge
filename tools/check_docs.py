import json
import re
import sys
from pathlib import Path

from wdf.exports import artifact_sha256
from wdf.models import TABLE_MODELS


ROOT = Path(__file__).resolve().parents[1]


def check_dictionary():
    path = ROOT / "docs" / "DATA_DICTIONARY.md"
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## `([^`]+)`\s*$", text)
    documented = {}
    for index in range(1, len(sections), 2):
        table, content = sections[index], sections[index + 1]
        documented[table] = {
            field for field in re.findall(
                r"(?m)^\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|", content
            ) if field != "Field"
        }
    errors = []
    for table, model in TABLE_MODELS.items():
        expected = set(model.model_fields)
        actual = documented.get(table, set())
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append("{} missing fields: {}".format(table, ", ".join(missing)))
        if extra:
            errors.append("{} undocumented fields: {}".format(table, ", ".join(extra)))
    extra_tables = sorted(set(documented) - set(TABLE_MODELS))
    if extra_tables:
        errors.append("Unknown dictionary tables: " + ", ".join(extra_tables))
    if errors:
        raise ValueError("; ".join(errors))
    print("PASS data dictionary: {} tables, {} Pydantic fields".format(
        len(TABLE_MODELS), sum(len(model.model_fields) for model in TABLE_MODELS.values())
    ))


def check_source_manifest(dataset):
    source_manifest = (dataset / "SOURCE_MANIFEST.md").read_text(encoding="utf-8").lower()
    if "synthetic" not in source_manifest or "no external data" not in source_manifest:
        raise ValueError("SOURCE_MANIFEST.md does not explicitly state synthetic/no external data")
    print("PASS SOURCE_MANIFEST.md states synthetic records and no external data")


def check_manifest(dataset):
    manifest_path = dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_paths = set()
    errors = []
    for entry in manifest["files"]:
        relative = entry["file"]
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append("Unsafe manifest path: " + relative)
            continue
        expected_paths.add(relative.replace("\\", "/"))
        artifact = dataset / relative
        if not artifact.is_file():
            errors.append("Missing manifest artifact: " + relative)
            continue
        actual_hash = artifact_sha256(artifact)
        if actual_hash != entry["sha256"]:
            errors.append("Checksum mismatch: " + relative)
    actual_paths = {
        path.relative_to(dataset).as_posix()
        for path in dataset.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "repro_report.json"}
    }
    if expected_paths != actual_paths:
        errors.append(
            "Manifest file inventory differs: unlisted={}, missing={}".format(
                sorted(actual_paths - expected_paths)[:5],
                sorted(expected_paths - actual_paths)[:5],
            )
        )
    if errors:
        raise ValueError("; ".join(errors))
    print("PASS manifest checksums and inventory: {} files".format(len(expected_paths)))


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/check_docs.py DATASET_DIRECTORY")
        return 2
    dataset = Path(sys.argv[1])
    try:
        check_dictionary()
        check_source_manifest(dataset)
        check_manifest(dataset)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print("FAIL: " + str(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
