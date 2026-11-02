import json
from pathlib import Path

from typer.testing import CliRunner

from wdf.cli import app
from wdf.dashboard_export import MAX_EXPORT_BYTES, export_dashboard


ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "output" / "starter"


def test_dashboard_export_is_aggregated_deterministic_and_separates_evaluation(tmp_path):
    output = tmp_path / "dashboard-data"
    first = export_dashboard(STARTER, output)
    first_files = {
        path.name: path.read_bytes()
        for path in output.iterdir()
    }
    second = export_dashboard(STARTER, output)
    second_files = {
        path.name: path.read_bytes()
        for path in output.iterdir()
    }

    assert first["files"] == ["analytics.json", "evaluation.json"]
    assert first["bytes"] == second["bytes"] < MAX_EXPORT_BYTES
    assert first["sha256"] == second["sha256"]
    assert first_files == second_files

    analytics = json.loads(first_files["analytics.json"])
    evaluation = json.loads(first_files["evaluation.json"])
    assert analytics["overview"]["data_health"] == "PASS"
    assert analytics["overview"]["candidate_actions"] > 0
    assert analytics["skill_gaps"]["traces"]
    assert "evaluation_only" not in analytics
    assert "ground_truth" not in json.dumps(analytics).lower()
    assert evaluation["evaluation_only"] is True
    assert "record_id" not in json.dumps(evaluation)
    assert evaluation["by_issue_type"]
    assert all(row["records"] > 0 for row in evaluation["near_misses"])


def test_export_dashboard_cli_only_writes_dashboard_data(monkeypatch, tmp_path):
    import wdf.dashboard_export as exporter

    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    result = CliRunner().invoke(
        app,
        ["export-dashboard", "--input", str(STARTER)],
    )

    assert result.exit_code == 0, (result.output, result.exception)
    assert "aggregated dashboard files" in result.output
    assert (tmp_path / "dashboard" / "public" / "data" / "analytics.json").is_file()
    assert (tmp_path / "dashboard" / "public" / "data" / "evaluation.json").is_file()
    assert not (tmp_path / "output").exists()
