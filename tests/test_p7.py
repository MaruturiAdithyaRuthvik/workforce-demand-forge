import sqlite3

from wdf.pipeline import run_generate, run_repro


def test_exports_load_into_sqlite_with_foreign_keys_and_no_ground_truth_input(tmp_path):
    output = tmp_path / "starter"
    result = run_generate(output, "starter", 67, include_heldout=False)
    assert result["validation"]["status"] == "PASS"
    with sqlite3.connect(output / "workforce.db") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        table_names = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert "ground_truth" not in table_names
    assert (output / "ground_truth" / "ground_truth.csv").is_file()
    assert (output / "schema.sql").is_file()
    assert (output / "seed.sql").is_file()


def test_repro_report_checks_same_and_different_seed_outputs(tmp_path):
    report = run_repro(tmp_path, "starter", 71)
    assert report["status"] == "PASS"
    assert report["same_seed_logical_database_match"]
    assert report["different_seed_hashes_differ"]
