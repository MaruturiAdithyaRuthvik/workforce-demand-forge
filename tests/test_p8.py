from pathlib import Path

from wdf.dictionary import render_data_dictionary
from wdf.models import TABLE_MODELS
from wdf.pipeline import DERIVED_TABLES, SOURCE_TABLES, build_data


ROOT = Path(__file__).resolve().parents[1]


def test_pydantic_data_dictionary_is_current_and_covers_all_tables():
    actual = (ROOT / "docs" / "DATA_DICTIONARY.md").read_text(encoding="utf-8")
    assert actual == render_data_dictionary()
    assert set(TABLE_MODELS) == SOURCE_TABLES | DERIVED_TABLES
    for column in ("Type", "Required", "Allowed values", "Units", "Uniqueness", "Validation"):
        assert column in actual


def test_traceability_and_architecture_docs_exist():
    assert (ROOT / "docs" / "TRACEABILITY.md").is_file()
    assert (ROOT / "docs" / "ERD.md").is_file()


def test_training_failure_fallback_and_headcount_escalation_exist():
    sources, _truth, derived, _forecast, _metrics, validation = build_data("starter", 20261022)
    failed_training = [
        row for row in sources["training"] if row["status"] == "Failed"
    ]
    fallback_actions = [
        row for row in derived["gap_actions"] if row["rule_id"] == "TRAIN_FAILED_FALLBACK"
    ]
    assert failed_training and fallback_actions
    assert any(row["status"] == "Escalated" for row in derived["gap_actions"])
    assert validation["status"] == "PASS"
    assert all(
        any(
            training["employee_id"] == action["candidate_employee_id"]
            and training["skill_id"] == next(
                gap["skill_id"] for gap in derived["gap_analysis"] if gap["gap_id"] == action["gap_id"]
            )
            for training in failed_training
        )
        for action in fallback_actions
    )
