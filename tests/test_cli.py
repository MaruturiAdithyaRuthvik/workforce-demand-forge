from typer.testing import CliRunner

from wdf.cli import app


def test_generate_cli_smoke(tmp_path):
    output = tmp_path / "generated"
    result = CliRunner().invoke(
        app,
        [
            "generate",
            "--scale", "starter",
            "--seed", "20261022",
            "--out", str(output),
        ],
    )

    assert result.exit_code == 0, (result.output, result.exception)
    assert "Validation: PASS" in result.output
    assert (output / "manifest.json").is_file()
